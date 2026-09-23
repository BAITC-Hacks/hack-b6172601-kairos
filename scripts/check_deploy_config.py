#!/usr/bin/env python3
"""Guard against drift between deploy/fly.toml and the root fly.toml.

`fly launch` rewrites the root file: it reorders keys, changes double quotes to
single quotes and drops comments. A later edit to deploy/fly.toml therefore does
NOT reach the file `fly deploy` actually reads, and the deployment silently runs
on stale settings. That happened once already, with CLIENT_IP_HEADER.

Compares the [env] blocks by key and value, ignoring order, quoting and
comments. Exit 0 when they agree or when the root file does not exist.
"""
from __future__ import annotations

import pathlib
import re
import sys

ENV_LINE = re.compile(r"^\s*([A-Z][A-Z0-9_]*)\s*=\s*(.+?)\s*$")


def env_block(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    inside = False
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            inside = stripped == "[env]"
            continue
        if not inside or stripped.startswith("#") or not stripped:
            continue
        match = ENV_LINE.match(line)
        if match:
            key, raw = match.groups()
            values[key] = raw.strip().strip("\"'")
    return values


def main() -> int:
    source = pathlib.Path("deploy/fly.toml")
    deployed = pathlib.Path("fly.toml")

    if not source.exists():
        print("deploy/fly.toml is missing", file=sys.stderr)
        return 1
    if not deployed.exists():
        print("  no root fly.toml yet - nothing to compare")
        return 0

    want, have = env_block(source), env_block(deployed)
    problems = []
    for key, value in want.items():
        if key not in have:
            problems.append(f"{key} is missing from the root fly.toml (deploy/ has {value!r})")
        elif have[key] != value:
            problems.append(f"{key}: root has {have[key]!r}, deploy/ has {value!r}")
    for key in have.keys() - want.keys():
        problems.append(f"{key} is only in the root fly.toml ({have[key]!r})")

    if problems:
        print("FAIL: fly.toml and deploy/fly.toml disagree:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        print("  The root file is what `fly deploy` reads. Sync it.", file=sys.stderr)
        return 1

    print(f"  deploy config  OK ({len(want)} settings match)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
