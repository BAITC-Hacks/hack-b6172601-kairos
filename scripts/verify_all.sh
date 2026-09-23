#!/usr/bin/env bash
# End-to-end verification of the project.
#
# Runs every check a technical reviewer would run, in order, and prints a
# pass/fail summary. Exits non-zero if anything failed.
#
#   bash scripts/verify_all.sh              # everything
#   bash scripts/verify_all.sh --no-docker  # skip the Docker stage
#   bash scripts/verify_all.sh --quick      # local only: install, tests, language
#
# Requires an .env with a working LLM_API_KEY only for the optional live agent
# check; everything else runs without a key.

set -uo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"

RUN_DOCKER=1
RUN_SERVICE=1
QUICK=0
for arg in "$@"; do
  case "$arg" in
    --no-docker) RUN_DOCKER=0 ;;
    --quick) QUICK=1; RUN_DOCKER=0; RUN_SERVICE=0 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

RESULTS=()
declare -a RESULTS
FAILED=0
PORT_LOCAL=8011
PORT_DOCKER=8012

print_summary() {
  echo
  echo "================ SUMMARY ================"
  for line in ${RESULTS[@]+"${RESULTS[@]}"}; do echo "  $line"; done
  echo "========================================="
  if [ "$FAILED" -eq 0 ]; then
    echo "All checks passed."
  else
    echo "Some checks FAILED. Fix them before the competition." >&2
  fi
}

pass() { RESULTS+=("PASS  $1"); echo "  -> PASS: $1"; }
fail() { RESULTS+=("FAIL  $1"); echo "  -> FAIL: $1" >&2; FAILED=1; }
skip() { RESULTS+=("SKIP  $1"); echo "  -> SKIP: $1"; }
step() { echo; echo "=== $1 ==="; }

wait_for_health() {
  local url="$1" tries="${2:-40}"
  for _ in $(seq 1 "$tries"); do
    if curl -sf "${url}/api/health" >/dev/null 2>&1; then return 0; fi
    sleep 1
  done
  return 1
}

cleanup() {
  [ -n "${UVICORN_PID:-}" ] && kill "$UVICORN_PID" 2>/dev/null
  [ "$RUN_DOCKER" -eq 1 ] && docker compose -f docker-compose.verify.yml down -t 3 >/dev/null 2>&1
  rm -f docker-compose.verify.yml
}
trap cleanup EXIT

# ---------------------------------------------------------------- toolchain
step "Toolchain"
PY=$(command -v python3 || true)
if [ -z "$PY" ]; then
  fail "python3 is not installed"
  echo "Cannot continue without python3." >&2
  print_summary
  exit 1
fi
PYVER=$("$PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])')
echo "python3 $PYVER at $PY"
if "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
  pass "python >= 3.11 ($PYVER)"
else
  fail "python is $PYVER, the Dockerfile targets 3.11 - local runs may differ"
fi

# ---------------------------------------------------------------- install
step "Dependencies"
# An existing .venv may be stale or built for another OS. Verify it, and
# rebuild it rather than failing in a confusing way later.
if [ -d .venv ]; then
  if ! (.venv/bin/python -c 'import sys' >/dev/null 2>&1 || .venv/Scripts/python.exe -c 'import sys' >/dev/null 2>&1); then
    echo "Existing .venv is not usable on this machine - rebuilding it."
    rm -rf .venv
  fi
fi
if [ ! -d .venv ]; then
  "$PY" -m venv .venv || { fail "could not create .venv"; exit 1; }
fi
VENV_PY=".venv/bin/python"
[ -x "$VENV_PY" ] || VENV_PY=".venv/Scripts/python.exe"

if [ -s requirements.lock.txt ]; then
  REQ_FILE="requirements.lock.txt"
else
  REQ_FILE="requirements.txt"
fi

if "$VENV_PY" -m pip install -q --disable-pip-version-check -r "$REQ_FILE"; then
  pass "pip install -r $REQ_FILE"
elif [ "$REQ_FILE" = "requirements.lock.txt" ] \
     && "$VENV_PY" -m pip install -q --disable-pip-version-check -r requirements.txt; then
  # A lock pinned on another Python version may not resolve here.
  fail "requirements.lock.txt does not resolve on this Python - regenerate it with 'make lock'"
  pass "fell back to requirements.txt so the rest of the checks can run"
else
  fail "pip install failed - fix $REQ_FILE before anything else"
  print_summary
  exit 1
fi

PY_TAG=$("$VENV_PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])')
if [ "$PY_TAG" != "3.11" ]; then
  RESULTS+=("NOTE  local Python is $PY_TAG while the image is 3.11 - a lock made here may not install there")
  echo "  -> NOTE: local Python is $PY_TAG, the Docker image uses 3.11"
fi

# The lock records the environment the project was actually tested in. It is
# written only when absent, so a committed lock is never silently replaced.
if [ -s requirements.lock.txt ]; then
  pass "using the committed requirements.lock.txt ($(wc -l < requirements.lock.txt | tr -d ' ') packages)"
else
  "$VENV_PY" -m pip freeze > requirements.lock.txt 2>/dev/null \
    && pass "wrote requirements.lock.txt ($(wc -l < requirements.lock.txt | tr -d ' ') packages) - commit it" \
    || fail "could not write requirements.lock.txt"
fi

# ---------------------------------------------------------------- data
step "Dataset"
SEED_TMP=$(mktemp -d)
if "$VENV_PY" scripts/seed_data.py --out "$SEED_TMP" --force >/dev/null; then
  pass "scripts/seed_data.py (into a temporary directory - your data/ is untouched)"
else
  fail "seed_data.py failed"
fi
rm -rf "$SEED_TMP"

# Only create the working dataset when it is genuinely absent.
if [ ! -s data/accounts.json ] || [ ! -s data/transactions.json ]; then
  "$VENV_PY" scripts/seed_data.py >/dev/null 2>&1 \
    && pass "created the missing sample dataset" \
    || fail "could not create the sample dataset"
fi
[ -s data/accounts.json ] && [ -s data/transactions.json ] \
  && pass "data files are present and non-empty" \
  || fail "data/accounts.json or data/transactions.json is missing or empty"

# ---------------------------------------------------------------- tests
step "Test suite"
if "$VENV_PY" -m pytest -q; then
  pass "pytest"
else
  fail "pytest - see output above"
fi

# ---------------------------------------------------------------- language
step "Language guard"
if bash scripts/check_language.sh; then
  pass "no Cyrillic in files, commits or branches"
else
  fail "Cyrillic found - see output above"
fi

# ---------------------------------------------------------------- deploy config
step "Deployment configuration"
if "$VENV_PY" scripts/check_deploy_config.py; then
  pass "fly.toml matches deploy/fly.toml"
else
  fail "the deployed fly.toml has drifted from deploy/fly.toml - see above"
fi

# ---------------------------------------------------------------- local run
if [ "$RUN_SERVICE" -eq 0 ]; then
  step "Local service"
  skip "--quick: service, clean-copy, Docker and live checks are skipped"
  print_summary
  exit "$FAILED"
fi

step "Local service on port ${PORT_LOCAL}"
"$VENV_PY" -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT_LOCAL" > /tmp/kairos_uvicorn.log 2>&1 &
UVICORN_PID=$!
if wait_for_health "http://127.0.0.1:${PORT_LOCAL}" 30; then
  pass "uvicorn starts and answers /api/health"
  if bash scripts/smoke_test.sh "http://127.0.0.1:${PORT_LOCAL}"; then
    pass "smoke test against the local service"
  else
    fail "smoke test against the local service"
  fi
else
  fail "uvicorn did not become healthy - see /tmp/kairos_uvicorn.log"
  tail -20 /tmp/kairos_uvicorn.log >&2
fi
kill "$UVICORN_PID" 2>/dev/null; UVICORN_PID=""
sleep 1

# ---------------------------------------------------------------- clean clone
if [ "$QUICK" -eq 0 ]; then
  step "Clean-clone simulation (what a reviewer actually does)"
  TMP=$(mktemp -d)
  if git rev-parse --git-dir >/dev/null 2>&1; then
    git clone -q . "$TMP/clone" 2>/dev/null && pass "git clone of the repository" || fail "git clone failed"
  else
    if "$PY" scripts/make_clean_copy.py "$TMP/clone" >/dev/null; then
      skip "not a git repository yet - copied the tree instead"
    else
      fail "could not make a clean copy - this is a bug in this script, not in the app"
      COPY_OK=0
    fi
  fi

  if [ -d "$TMP/clone" ] && [ "${COPY_OK:-1}" -eq 1 ]; then
    if [ -f "$TMP/clone/app/data/store.py" ] && [ -f "$TMP/clone/app/main.py" ]; then
      pass "the copy contains the full application tree"
    else
      fail "the copy is incomplete - this is a bug in this script, not in the app"
      COPY_OK=0
    fi
  fi

  if [ -d "$TMP/clone" ] && [ "${COPY_OK:-1}" -eq 1 ]; then
    (
      cd "$TMP/clone"
      "$PY" -m venv .venv >/dev/null 2>&1
      if [ -s requirements.lock.txt ]; then
        .venv/bin/python -m pip install -q --disable-pip-version-check -r requirements.lock.txt >/tmp/kairos_clone_pip.log 2>&1 \
          || .venv/bin/python -m pip install -q --disable-pip-version-check -r requirements.txt >/tmp/kairos_clone_pip.log 2>&1
      else
        .venv/bin/python -m pip install -q --disable-pip-version-check -r requirements.txt >/tmp/kairos_clone_pip.log 2>&1
      fi
      echo $? > /tmp/kairos_clone_pip.status
      .venv/bin/python scripts/seed_data.py >/dev/null 2>&1
      cp .env.example .env
      .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8013 > /tmp/kairos_clone.log 2>&1 &
      echo $! > /tmp/kairos_clone.pid
      sleep 1
    )
    if [ "$(cat /tmp/kairos_clone_pip.status 2>/dev/null || echo 0)" != "0" ]; then
      fail "pip install failed in the clean copy - see /tmp/kairos_clone_pip.log"
      tail -15 /tmp/kairos_clone_pip.log >&2
    fi

    if wait_for_health "http://127.0.0.1:8013" 30; then
      pass "a fresh copy starts with no manual steps beyond the README"
      curl -sf "http://127.0.0.1:8013/api/health" | grep -q '"llm_configured": *false' \
        && pass "starts without a real key and says so on /api/health" \
        || skip "could not confirm llm_configured=false"
    else
      fail "a fresh copy did not start - this is the 20-point reproducibility criterion"
      tail -20 /tmp/kairos_clone.log >&2
    fi
    [ -f /tmp/kairos_clone.pid ] && kill "$(cat /tmp/kairos_clone.pid)" 2>/dev/null
    rm -f /tmp/kairos_clone.pid
  fi
  rm -rf "$TMP"
fi

# ---------------------------------------------------------------- docker
if [ "$RUN_DOCKER" -eq 1 ]; then
  step "Docker"
  if ! command -v docker >/dev/null 2>&1; then
    skip "docker is not installed on this machine"
  elif ! docker info >/dev/null 2>&1; then
    skip "docker is installed but the daemon is not running"
  else
    # Deliberately does NOT create .env: the README promises that Docker alone
    # is enough, and this stage is what proves it.
    sed "s/8000:8000/${PORT_DOCKER}:8000/" docker-compose.yml > docker-compose.verify.yml
    if docker compose -f docker-compose.verify.yml up --build -d >/tmp/kairos_docker.log 2>&1; then
      pass "docker compose build and start"
      if wait_for_health "http://127.0.0.1:${PORT_DOCKER}" 60; then
        pass "container answers /api/health"
        bash scripts/smoke_test.sh "http://127.0.0.1:${PORT_DOCKER}" \
          && pass "smoke test against the container" \
          || fail "smoke test against the container"

        # The image ships with a dataset. NOTE: this passes whether the data was
        # committed to the repository or generated by the entrypoint, so it does
        # not on its own prove the seeder works. The next check does that.
        if docker compose -f docker-compose.verify.yml exec -T app \
             sh -c '[ -s /app/data/accounts.json ]' >/dev/null 2>&1; then
          pass "the running container has a dataset"
        else
          fail "the container started with no dataset - the Docker-only path is broken"
        fi

        # Prove the entrypoint itself seeds: mount an EMPTY directory over
        # /app/data, so nothing committed can satisfy the check, and see whether
        # a dataset appears on the host side.
        SEED_PROBE=$(mktemp -d)
        chmod 777 "$SEED_PROBE" 2>/dev/null || true
        IMAGE=$(docker compose -f docker-compose.verify.yml images -q app 2>/dev/null | head -1)
        if [ -n "$IMAGE" ]; then
          docker run --rm -d --name kairos_seed_probe \
            -v "$SEED_PROBE:/app/data" "$IMAGE" >/dev/null 2>&1 || true
          for _ in $(seq 1 20); do
            [ -s "$SEED_PROBE/accounts.json" ] && break
            sleep 1
          done
          docker rm -f kairos_seed_probe >/dev/null 2>&1 || true
          if [ -s "$SEED_PROBE/accounts.json" ] && [ -s "$SEED_PROBE/transactions.json" ]; then
            pass "the entrypoint really seeds an empty dataset directory"
          else
            fail "the entrypoint did not seed an empty dataset directory"
          fi
        else
          skip "could not resolve the built image to test entrypoint seeding"
        fi
        rm -rf "$SEED_PROBE"

        # A half-present dataset must stop the container, not be served silently.
        HALF_PROBE=$(mktemp -d)
        chmod 777 "$HALF_PROBE" 2>/dev/null || true
        printf '[]' > "$HALF_PROBE/accounts.json"
        if [ -n "$IMAGE" ]; then
          if docker run --rm -v "$HALF_PROBE:/app/data" "$IMAGE" >/dev/null 2>&1; then
            fail "the container started on an incomplete dataset instead of refusing"
          else
            pass "the container refuses to start on an incomplete dataset"
          fi
        fi
        rm -rf "$HALF_PROBE"

        # And it must start with no .env and no key, reporting that honestly.
        if curl -sf "http://127.0.0.1:${PORT_DOCKER}/api/health" | grep -q '"llm_configured": *false'; then
          pass "starts with no .env and reports llm_configured=false"
        else
          skip "could not confirm the no-key path (a key may be set in the environment)"
        fi
      else
        fail "container never became healthy"
        docker compose -f docker-compose.verify.yml logs --tail 30 >&2
      fi
      docker compose -f docker-compose.verify.yml down -t 3 >/dev/null 2>&1
    else
      fail "docker compose build failed - see /tmp/kairos_docker.log"
      tail -25 /tmp/kairos_docker.log >&2
    fi
    rm -f docker-compose.verify.yml
  fi
fi

# ---------------------------------------------------------------- live agent
step "Live agent call (optional, needs a real key)"
HAS_KEY=0
if [ -f .env ]; then
  KEY_LINE=$(grep '^LLM_API_KEY=' .env | head -1 | cut -d= -f2- | tr -d '"'"'"' ' )
  case "$KEY_LINE" in
    ""|replace-me|your-*|sk-replace*) HAS_KEY=0 ;;
    *) HAS_KEY=1 ;;
  esac
fi
if [ "$HAS_KEY" -eq 1 ]; then
  "$VENV_PY" -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT_LOCAL" > /tmp/kairos_live.log 2>&1 &
  UVICORN_PID=$!
  if wait_for_health "http://127.0.0.1:${PORT_LOCAL}" 30; then
    BODY=$(curl -s -X POST "http://127.0.0.1:${PORT_LOCAL}/api/ask" \
      -H 'Content-Type: application/json' \
      -d '{"question":"List the accounts of CUST-001."}')
    if echo "$BODY" | grep -q '"ok": *true'; then
      pass "a real agent run completed"
      echo "$BODY" | grep -q '"kind": *"tool"' \
        && pass "the run actually called a tool (visible in the trace)" \
        || fail "the run produced no tool call - the model answered from nothing"
    else
      fail "live agent call failed: $(echo "$BODY" | head -c 300)"
    fi
  else
    fail "service did not start for the live check"
  fi
  kill "$UVICORN_PID" 2>/dev/null; UVICORN_PID=""
else
  skip "no real LLM_API_KEY in .env - run this again once the key is issued"
fi

# ---------------------------------------------------------------- summary
print_summary
exit "$FAILED"
