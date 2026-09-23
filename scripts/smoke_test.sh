#!/usr/bin/env bash
# Verifies that a freshly started service answers on its public endpoints.
# Usage: bash scripts/smoke_test.sh [base_url]
set -euo pipefail

BASE="${1:-http://localhost:8000}"
fail() { echo "FAIL: $1" >&2; exit 1; }

echo "Checking ${BASE} ..."

code=$(curl -s -o /tmp/kairos_health.json -w '%{http_code}' "${BASE}/api/health" || true)
[ "$code" = "200" ] || fail "GET /api/health returned ${code}"
grep -q '"ok": *true' /tmp/kairos_health.json || fail "health payload is not ok"
echo "  health        OK"

code=$(curl -s -o /dev/null -w '%{http_code}' "${BASE}/" || true)
[ "$code" = "200" ] || fail "GET / returned ${code}"
echo "  static UI     OK"

for path in /app.js /api/graph /api/top /api/clusters /api/method /api/skeleton '/api/accounts?role=coordinator' /api/download/nodes_roles.csv; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "${BASE}${path}" || true)
  [ "$code" = "200" ] || fail "GET ${path} returned ${code}"
done
echo "  viewer        OK"

code=$(curl -s -o /dev/null -w '%{http_code}' "${BASE}/api/tools" || true)
[ "$code" = "200" ] || fail "GET /api/tools returned ${code}"
echo "  tools         OK"

# Invalid input must be rejected cleanly, not with a stack trace.
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "${BASE}/api/ask" \
  -H 'Content-Type: application/json' -d '{"question":""}' || true)
[ "$code" = "422" ] || fail "empty question returned ${code}, expected 422"
echo "  validation    OK"

echo "Smoke test passed."
