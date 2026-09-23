#!/usr/bin/env bash
# Interactive key setup, so a reviewer does not have to read the README to run
# the project. Creates .env from .env.example and stores the key there.
#
#   bash scripts/setup_key.sh
#
# The key is never echoed, never logged, never passed in argv (where `ps` would
# expose it) and never committed: .env is excluded by .gitignore and
# .dockerignore. The terminal is restored even if the user interrupts.
set -euo pipefail

# Without this, Ctrl-C during the hidden key prompt leaves the terminal with
# echo disabled: everything the user types afterwards is invisible.
trap 'stty echo 2>/dev/null || true' EXIT INT TERM

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

echo
echo "Which provider will you use?"
echo "  1) OpenAI   (https://platform.openai.com/api-keys)"
echo "  2) NVIDIA   (https://build.nvidia.com)"
echo "  3) Other OpenAI-compatible endpoint"
printf "Choice [1]: "
read -r choice
choice="${choice:-1}"

case "$choice" in
  1) provider="openai"; model="gpt-4.1-mini"; base_url="" ;;
  2) provider="nvidia"; model="meta/llama-3.3-70b-instruct"; base_url="" ;;
  3)
    provider="custom"
    printf "Base URL (e.g. https://host/v1): "
    read -r base_url
    printf "Model identifier: "
    read -r model
    ;;
  *) echo "Unknown choice." >&2; exit 1 ;;
esac

printf "API key (input hidden): "
stty -echo 2>/dev/null || true
read -r api_key
stty echo 2>/dev/null || true
echo

if [ -z "$api_key" ]; then
  echo "No key entered, nothing was changed." >&2
  exit 1
fi

printf '%s' "$api_key" | python3 scripts/write_env_value.py "$provider" "$model" "$base_url"

unset api_key
echo "Saved to .env (mode 600). The key is not printed, not stored in shell"
echo "history, not passed on any command line, and is git-ignored."
echo
echo "Now run either of:"
echo "  docker compose up --build"
echo "  uvicorn app.main:app --port 8000"
