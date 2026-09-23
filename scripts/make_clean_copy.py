#!/usr/bin/env python3
"""Copy the project the way a reviewer receives it.

Used by verify_all.sh when the project is not yet a git repository. Written in
Python because tar's --exclude matches a bare name at every depth: on macOS
bsdtar, "--exclude=./data" still dropped app/data, which made the verifier blame
the application for its own bug.

Usage: python3 scripts/make_clean_copy.py <destination>
Exits non-zero, with a message, if the copy is incomplete.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

# Excluded wherever they appear.
EXCLUDE_ANYWHERE = {
    ".venv", "venv", ".git", "__pycache__", ".pytest_cache",
    ".traces", "node_modules", ".DS_Store", ".env", ".hackathon_start",
}
# Excluded only at the project root, so app/data survives.
EXCLUDE_AT_ROOT = {"data"}
# Must exist in the copy, or the copy is not usable.
REQUIRED = ("app/main.py", "app/data/store.py", "requirements.txt", "scripts/seed_data.py")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: make_clean_copy.py <destination>", file=sys.stderr)
        return 2

    source = Path.cwd().resolve()
    destination = Path(sys.argv[1]).resolve()

    def ignore(directory: str, names: list[str]) -> set[str]:
        current = Path(directory).resolve()
        skipped = {n for n in names if n in EXCLUDE_ANYWHERE}
        # macOS writes AppleDouble sidecars (._name) when copying onto
        # non-native filesystems. They are binary noise and must not travel.
        skipped |= {n for n in names if n.startswith("._")}
        if current == source:
            skipped |= {n for n in names if n in EXCLUDE_AT_ROOT}
            skipped |= {n for n in names if n.startswith("audit-")}
        return skipped

    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination, ignore=ignore, symlinks=True)

    missing = [p for p in REQUIRED if not (destination / p).exists()]
    if missing:
        print("Copy is incomplete, these files are missing:", file=sys.stderr)
        for path in missing:
            print(f"  {path}", file=sys.stderr)
        return 1

    if (destination / ".env").exists():
        print("Copy unexpectedly contains .env", file=sys.stderr)
        return 1

    files = sum(1 for _ in destination.rglob("*") if _.is_file())
    print(f"Copied {files} files to {destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
