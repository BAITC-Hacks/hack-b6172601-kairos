# Finance case override (2026-09-23)

This section supersedes conflicting pre-competition decisions below.
- Core is local deterministic graph analytics, not an LLM chat agent. No key or
  paid service may be necessary to reproduce mandatory results.
- Keep FastAPI, Docker, safe errors and useful UI infrastructure. Replace example
  account tools/data/seeding; remove unused components where this reduces risk.
- Official Parquet is immutable. No synthetic fallback for missing case files.
- All nodes, including isolates, participate in exports and cluster assignments.
- Role and priority scores express heuristic evidence, not probability of guilt.
- Unobserved outgoing/incoming flows must remain unknown, never invented.
- Case-specific weights in SCORING.md replace old 20/25/20/20/15 references.
- Actual start 13:33; user confirmed deadline exactly 18:00, overriding an earlier
  18:33 reply. No Fly changes for now.
- Limited new dependencies are justified by Parquet, graph computation and viewing;
  retain a simple stack. Bundle browser dependencies locally for offline operation.

## Historical scaffold rationale (context only)

# Decisions

Why the project is shaped the way it is. Each entry states the decision, the
reason, and what would make it wrong. An agent proposing to change one of these
should read the "revisit if" line first.

## D1. Python + FastAPI, not a TypeScript full-stack framework

The case track is finance, where the work is data handling rather than interface.
One process, one language, no build step for the server.

Revisit if: the case turns out to be a pure chat interface with no data work.

## D2. The frontend is plain HTML, CSS and JS with no build step

Reproducibility is worth 20 points and a reviewer must be able to start the
project on a clean machine. Every build step is another way that fails. There are
no points for visual design, so a build pipeline buys nothing and risks a lot.

Revisit if: never, during this hackathon.

## D3. The agent loop is written out, not taken from a framework

`app/agent/core.py` is about 100 lines a reviewer can read top to bottom and
verify. A framework would hide the tool calls behind machinery the reviewer
cannot check in the time they have, which works against the 25-point criterion on
real versus imitated implementation.

Revisit if: the case requires multi-agent orchestration that would be genuinely
large to write by hand.

## D4. Every run returns an execution trace

The highest-weighted criterion punishes functionality that is faked. A claim that
tools ran is weak; a per-run list of the calls with their arguments and results is
evidence. The trace is a deliverable, not debug output.

Revisit if: never. Removing it removes the project's main defence.

## D5. Provider is configuration, not code

The hackathon issues both OpenAI and NVIDIA keys, and both speak the OpenAI
chat-completions API. Switching is three lines in `.env`. If one provider is slow
or out of quota on the day, the cost of switching is seconds.

Revisit if: the case mandates a provider-specific feature.

## D6. Dependency ranges in `requirements.txt`, exact versions in `requirements.lock.txt`

An unverified exact pin that fails to resolve on the day is a disaster; a range
that resolves differently for the reviewer is a reproducibility gap. So: ranges as
the fallback, a lock generated from a working environment as the preferred input,
and every install path falls back to the ranges if the lock does not resolve.

Known limitation: the lock carries no interpreter marker. It is generated locally
(Python 3.14) while the image is 3.11. Today every pinned version has a 3.11
wheel; that is a fact about PyPI right now, not a guarantee.

Revisit if: the fallback ever triggers, which means the tested set and the shipped
set have diverged.

## D7. The container seeds its own dataset

The README promises that Docker alone is enough. A seeding step that needs host
Python would make that false. The entrypoint seeds only when the dataset
directory is entirely empty, and refuses to start on a half-present dataset
rather than serving data that is not there.

Revisit if: the case supplies data that must never be generated, in which case
remove the seeding branch rather than weakening the refusal.

## D8. The pre-built scaffold is disclosed, and contains no case logic

The regulations revised on 22 September say it directly (5.4.4.2): pre-prepared
technical components, own libraries, templates and infrastructure are allowed,
provided they are not a finished product and not the main part of the solution,
and provided the functionality answering the task is developed during the
competitive part. 5.4.4 still requires disclosing third-party material.

So: the scaffold is imported in one labelled commit; everything case-specific is
written during the session and appears in the hourly commit history; the
placeholder tools in `app/tools/finance.py` are deleted in the commit that adds
the first real tool, so that nothing pre-built can read as the main part of the
solution.

Revisit if: never. This is a rules obligation, not a preference.

## D9. Checks must be able to fail

Three separate defects in this repository were checks that reported success while
verifying nothing: a `grep -P` language guard that stock macOS grep could not run,
a `.dockerignore` test that asserted a substring, and a dataset check satisfied by
committed data rather than by the code it was testing. A new check is not finished
until it has been seen to go red for the right reason.

Revisit if: never.

A corollary learned the hard way: a script that edits a file by string
replacement must assert that the replacement matched. Three separate silent
no-ops have happened in this project, each reporting success while changing
nothing.

## D10. Synchronous tools run off the event loop

A blocking call inside a tool would otherwise freeze every request and defeat the
per-request timeout. The worker pool is bounded, so a tool that does network I/O
should still use `httpx.AsyncClient` with its own timeout rather than `requests`.

Revisit if: the tool set becomes I/O heavy enough to exhaust the pool, at which
point the tools should be async rather than the dispatch changed.

## D11. The caller's identity comes from a header the platform vouches for

Rate limiting keys on the caller's address. Taking the first entry of
`X-Forwarded-For` is the common idiom and it is wrong on at least one real
platform: Fly.io *appends* the address its edge observed to whatever the client
sent, so the first entry is attacker-controlled. Confirmed against the live
deployment - four forged header values each received a fresh bucket while the
honest path stayed capped.

So: use `CLIENT_IP_HEADER` when the platform provides an unforgeable header
(`fly-client-ip`), otherwise the *last* entry of `X-Forwarded-For`, otherwise the
peer address.

Revisit if: moving to a platform whose edge replaces rather than appends the
header, where the last entry would then be the proxy rather than the client. Test
it against the real platform rather than reasoning about it - reasoning is what
produced the bug.

## D12. Reproducibility is a gate, not a trade-off

The revised regulations (5.4.16, restated in 5.6.5) refuse admission to further
selection when the final version cannot be started from the repository's own
instructions, and explicitly do not accept clarifications afterwards. An earlier
version allowed experts to ask the team how to set the environment up; that is
gone.

So no feature is ever worth a risk to the clean run, and the last hour belongs to
verification rather than to code. 5.6.6 extends this: the key functionality must
be checkable without the participants' personal accounts, which is why the public
deployment carries a working key rather than being a nice-to-have.

Revisit if: never, while these clauses stand.
