#!/usr/bin/env bash
# Thin wrapper so existing commands keep working. The real check is in Python:
# stock macOS grep has no -P, and the previous shell implementation reported
# success on it instead of failing.
set -uo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PY=$(command -v python3 || command -v python || true)
if [ -z "$PY" ]; then
  echo "ERROR: python3 is required for the language check." >&2
  exit 2
fi
exec "$PY" "$ROOT/scripts/check_language.py" "$@"
