#!/usr/bin/env bash
# Verify the current offline pipeline and retained HTTP scaffold.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$(pwd)
DOCKER=1
QUICK=0
for arg in "$@"; do
  case "$arg" in
    --no-docker) DOCKER=0 ;;
    --quick) QUICK=1; DOCKER=0 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || { echo "Run make install first." >&2; exit 1; }
PROBE=$(mktemp -d)
SERVER_PID=""
CONTAINER=""
cleanup() {
  [ -z "$SERVER_PID" ] || kill "$SERVER_PID" 2>/dev/null || true
  [ -z "$CONTAINER" ] || docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  rm -rf "$PROBE"
}
trap cleanup EXIT
"$PY" -m pip check
"$PY" -m pytest -q
bash scripts/check_language.sh
"$PY" scripts/check_deploy_config.py
"$PY" -m pipeline.run --data data/raw --out "$PROBE/outputs"
if [ "$QUICK" -eq 0 ]; then
  "$PY" scripts/make_clean_copy.py "$PROBE/clean"
  (cd "$PROBE/clean" && "$PY" -m pipeline.run --data data/raw --out out)
  (cd "$PROBE/clean" && exec "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8011) > "$PROBE/server.log" 2>&1 &
  SERVER_PID=$!
  for _ in $(seq 1 30); do
    curl -sf http://127.0.0.1:8011/api/health >/dev/null && break
    sleep 1
  done
  bash scripts/smoke_test.sh http://127.0.0.1:8011
fi
if [ "$DOCKER" -eq 1 ]; then
  docker info >/dev/null
  docker build -t kairos-pipeline-verify .
  CONTAINER="kairos-verify-$$"
  docker run -d --name "$CONTAINER" -p 127.0.0.1:8012:8000 kairos-pipeline-verify >/dev/null
  for _ in $(seq 1 90); do
    curl -sf http://127.0.0.1:8012/api/health >/dev/null && break
    sleep 1
  done
  bash scripts/smoke_test.sh http://127.0.0.1:8012
  docker exec "$CONTAINER" sh -c 'test ! -e /app/.env && test -s /app/out/graph.json && test -s /app/out/nodes_roles.csv'
  mkdir "$PROBE/empty"
  if docker run --rm -v "$PROBE/empty:/app/data/raw:ro" kairos-pipeline-verify true; then
    echo "FAIL: container accepted missing official data" >&2
    exit 1
  fi
fi
echo "All requested checks passed. No external LLM calls were made."
