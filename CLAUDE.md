# CLAUDE.md

## Start here

Before changing anything, read in this order:

1. `docs/SPEC.md` — what the system must do, its contracts and its invariants
2. `docs/DECISIONS.md` — why it is shaped this way, and what would justify changing it
3. `docs/STATE.md` — what is done, what is verified, what is open
   (`docs/CONSTRAINTS.md` summarises the competition rules that shape all of
   this; read it when a decision turns on what the rules allow)
4. this file — how to work in this repository

These four files are written to be sufficient on their own: an agent with no
conversation history should be able to continue the work from them. When you
finish a piece of work, update `docs/STATE.md` in the same change.

The rules for this repository live in [AGENTS.md](AGENTS.md). Read that file
before making any change; it is the single source of truth for both Codex and
Claude Code.

Short version, so it is never missed:

- English only, everywhere, including commit messages. `scripts/check_language.sh` enforces it.
- No fake functionality. Never satisfy a requirement with a hardcoded or canned response.
- Run `pytest -q` after each change; `bash scripts/verify_all.sh` before each commit.
- Keep `cp .env.example .env && docker compose up --build` working on a clean machine.
- Update the requirement table in README.md in the same change that makes a requirement true.
- Commit messages: `H<hour>: <what now works>`.
- Do not add dependencies, frameworks, build steps or services without being asked.
