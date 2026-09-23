#!/usr/bin/env python3
"""Write provider settings into .env, reading the secret from stdin.

The key deliberately does NOT travel in argv: command-line arguments are visible
to any local user through `ps` or /proc/<pid>/cmdline. Only non-secret values are
passed as arguments.

Usage: printf '%s' "$key" | python3 scripts/write_env_value.py <provider> <model> <base_url>
"""
from __future__ import annotations

import pathlib
import sys


def main() -> int:
    if len(sys.argv) != 4:
        print("Usage: write_env_value.py <provider> <model> <base_url>", file=sys.stderr)
        return 2

    provider, model, base_url = sys.argv[1:4]
    api_key = sys.stdin.read().strip()
    if not api_key:
        print("No key received on stdin, nothing was written.", file=sys.stderr)
        return 1

    path = pathlib.Path(".env")
    if not path.exists():
        print(".env does not exist.", file=sys.stderr)
        return 1

    values = {
        "LLM_PROVIDER": provider,
        "LLM_API_KEY": api_key,
        "LLM_MODEL": model,
        "LLM_BASE_URL": base_url,
    }

    out: list[str] = []
    seen: set[str] = set()
    for line in path.read_text().splitlines():
        stripped = line.lstrip()
        key = line.split("=", 1)[0].strip() if "=" in line and not stripped.startswith("#") else None
        if key in values:
            if key in seen:
                continue  # drop duplicates rather than leaving several of the same setting
            out.append(f"{key}={values[key]}")
            seen.add(key)
        else:
            out.append(line)

    for key, value in values.items():
        if key not in seen:
            out.append(f"{key}={value}")

    path.write_text("\n".join(out) + "\n")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
