#!/usr/bin/env sh
# Container entrypoint.
#
# Makes the Docker path self-sufficient: a reviewer with Docker and nothing else
# - no Python on the host, no .env - can start the service with one command.
set -eu

DATA_DIR="${DATA_DIR:-/app/data}"
ACCOUNTS="${DATA_DIR}/accounts.json"
TRANSACTIONS="${DATA_DIR}/transactions.json"

has_accounts=0
has_transactions=0
[ -s "$ACCOUNTS" ] && has_accounts=1
[ -s "$TRANSACTIONS" ] && has_transactions=1

if [ "$has_accounts" -eq 1 ] && [ "$has_transactions" -eq 1 ]; then
  : # A complete dataset is present. Never touched.
elif [ "$has_accounts" -eq 0 ] && [ "$has_transactions" -eq 0 ]; then
  echo "No dataset found in ${DATA_DIR}, generating the sample dataset..."
  if [ ! -w "$DATA_DIR" ]; then
    echo "ERROR: ${DATA_DIR} is not writable, so the dataset cannot be created." >&2
    echo "       Mount it read-write, or bake the dataset into the image." >&2
    exit 1
  fi
  python scripts/seed_data.py --out "$DATA_DIR"
else
  # Refusing means refusing. The host-side seeder exits 1 in this case, and a
  # container that silently served half a dataset would be worse: the service
  # would look healthy while answering from data that is not there.
  echo "ERROR: the dataset in ${DATA_DIR} is incomplete." >&2
  [ "$has_accounts" -eq 0 ] && echo "       missing: ${ACCOUNTS}" >&2
  [ "$has_transactions" -eq 0 ] && echo "       missing: ${TRANSACTIONS}" >&2
  echo "       Refusing to start rather than serve half a dataset." >&2
  echo "       Restore the missing file, or empty ${DATA_DIR} to regenerate both." >&2
  exit 1
fi

if [ -z "${LLM_API_KEY:-}" ]; then
  echo "NOTE: LLM_API_KEY is not set. The service starts and serves /api/health," >&2
  echo "      but /api/ask will return 503. See README, section Setup and run." >&2
fi

exec "$@"
