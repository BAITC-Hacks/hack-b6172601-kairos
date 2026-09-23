#!/usr/bin/env bash
# The rules require a verifiable result at the end of every competition hour.
# This script stages everything, runs the language guard and commits.
#
# Usage: bash scripts/hourly_commit.sh "short summary of what now works"
set -euo pipefail

MSG="${1:-}"
if [ -z "$MSG" ]; then
  echo "Usage: bash scripts/hourly_commit.sh \"short summary of what now works\"" >&2
  exit 1
fi

# grep -P does not exist on stock macOS, so the check is done in Python.
if ! python3 -c "import sys; sys.exit(1 if any(0x0400 <= ord(c) <= 0x052F for c in sys.argv[1]) else 0)" "$MSG"; then
  echo "Refusing to commit: the message contains Cyrillic characters. Write it in English." >&2
  exit 1
fi

ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"

START_FILE=".hackathon_start"
if [ ! -f "$START_FILE" ]; then
  date +%s > "$START_FILE"
  echo "Recorded competition start time."
fi
START=$(cat "$START_FILE")
NOW=$(date +%s)
HOUR=$(( (NOW - START) / 3600 + 1 ))

git add -A
if git diff --cached --quiet; then
  echo "Nothing to commit. Make a change first - an empty hour is a disqualification risk." >&2
  exit 1
fi

bash scripts/check_language.sh || { echo "Language check failed. Fix it before committing." >&2; exit 1; }

git commit -m "H${HOUR}: ${MSG}"
echo "Committed hour ${HOUR}. Push now:  git push"
