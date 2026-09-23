#!/usr/bin/env python3
"""Guard: the repository must contain no Cyrillic text.

Checks tracked files (or the working tree when there is no git repository),
commit messages and branch names. Written in Python rather than grep because
stock macOS grep has no -P, and the previous shell version silently reported
success on it.

Exit code 0 when clean, 1 when Cyrillic is found, 2 on an internal error.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

CYRILLIC = re.compile("[" + chr(0x0400) + "-" + chr(0x052F) + "]")

SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".traces"}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz", ".whl", ".pyc"}
MAX_BYTES = 2_000_000


def run(cmd: list[str]) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return proc.returncode, proc.stdout
    except (OSError, subprocess.SubprocessError):
        return 1, ""


def in_git_repo() -> bool:
    code, _ = run(["git", "rev-parse", "--git-dir"])
    return code == 0


def candidate_files() -> list[Path]:
    if in_git_repo():
        code, out = run(["git", "ls-files", "-z"])
        if code == 0:
            return [Path(p) for p in out.split("\0") if p]
    files: list[Path] = []
    for root, dirs, names in os.walk("."):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in names:
            files.append(Path(root, name))
    return files


def scan_files() -> tuple[list[str], list[str]]:
    """Returns (files containing Cyrillic, files that could not be read)."""
    hits, unreadable = [], []
    for path in candidate_files():
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            if not path.is_file() or path.stat().st_size > MAX_BYTES:
                continue
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue  # binary file
        except OSError as exc:
            unreadable.append(f"{path}: {exc}")
            continue
        if CYRILLIC.search(text):
            for number, line in enumerate(text.splitlines(), 1):
                if CYRILLIC.search(line):
                    hits.append(f"{path}:{number}: {line.strip()[:100]}")
    return hits, unreadable


def scan_commits() -> list[str]:
    code, out = run(["git", "log", "--pretty=format:%h %s%n%b"])
    if code != 0:
        return []
    return [line for line in out.splitlines() if CYRILLIC.search(line)]


def scan_branches() -> list[str]:
    code, out = run(["git", "branch", "--all", "--format=%(refname:short)"])
    if code != 0:
        return []
    return [line for line in out.splitlines() if CYRILLIC.search(line)]


def report(title: str, problems: list[str]) -> bool:
    if problems:
        print(f"FAIL: Cyrillic found in {title}:")
        for item in problems[:40]:
            print(f"  {item}")
        if len(problems) > 40:
            print(f"  ... and {len(problems) - 40} more")
        return False
    print(f"  {title:<14} OK")
    return True


def main() -> int:
    print("Scanning for Cyrillic characters...")
    ok = True

    hits, unreadable = scan_files()
    ok &= report("files", hits)
    if unreadable:
        print("FAIL: some files could not be read:")
        for item in unreadable[:20]:
            print(f"  {item}")
        ok = False

    if in_git_repo():
        ok &= report("commits", scan_commits())
        ok &= report("branches", scan_branches())
    else:
        print("  commits        SKIP (not a git repository yet)")

    print("Language check passed." if ok else "Language check failed.")
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - a guard must never fail silently
        print(f"ERROR: language check could not run: {exc}", file=sys.stderr)
        sys.exit(2)
