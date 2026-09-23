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

## Pipeline implementation clarifications (spec 01)

- Compare aggregate KZT sums with 1e-6 absolute tolerance and zero relative
  tolerance; exact float equality rejects two valid official edge sums. Counts
  remain exact. Revisit if input switches to exact decimal arithmetic.
- Keep the prescribed dependency set: weighted PageRank uses NumPy power
  iteration; spring layout falls back to NetworkX's dense NumPy force routine
  when its public path requires SciPy. Fixed layout seed and iterations remain
  unchanged. Revisit the private fallback when upgrading NetworkX.
- Lock dependencies against both Python 3.11 (Docker) and local Python 3.14;
  initial local-only NumPy/NetworkX pins did not resolve in the image.

## Viewer implementation clarifications (spec 03)

- Ambiguous substring search matches sort by descending priority then gid, so
  the top-1 account is first even when its last six digits match other accounts.
- Ego layout assigns direct neighbors before second-hop nodes and keeps horizontal
  spacing readable; large columns use vertical pan rather than shrinking the whole
  graph. Reciprocal neighbors share one position (payer side takes precedence),
  with arrows preserving both directions and amount labels on opposite sides.
- Read-only APIs cache artifact bytes and indexed rows; file mtimes/sizes trigger
  reload. No new storage, settings, dependencies or writes through the API.

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

## Findings refinement clarifications (spec 04)

- Coordinator inputs are first-pass consolidator candidates (in-degree >=5),
  including candidates later promoted to coordinator. This avoids circular role
  dependencies. Source communities are computed independently before roles.
- Scatter/gather requires at least three simple 2-3-hop branches with distinct
  first intermediaries from one source to a target, every edge >=50,000 KZT
  (spec 04b). A lone path or cycle is insufficient.
- Finding bonuses apply before existing seed/cut-off multipliers and global
  maximum normalization, so those uncertainty discounts still apply.
- Continuation uses visible depth 1-3 quartile boundaries and empirical cell
  means. Duplicate boundaries collapse; empty cells fall back to the visible
  population mean. Missing training data yields unknown, never a fabricated rate.
- Skeleton top quartile is measured within coordinator/consolidator candidates.
  Levels use shortest forward seed-hop distance, not a claim of organizational
  rank; cyclic observed graphs need not form a strict hierarchy. Nodes must be
  endpoints of retained edges to be marked in_skeleton.
- Blocking selection maximizes marginal reduction at other surviving accounts.
  Reported cumulative cut uses the fixed original total node-taint denominator,
  including prevented inflow to removed accounts; sums represent repeated-hop
  exposure, not unique money. Keep original haircut denominators and fixed 20
  passes in every scenario for comparable, monotone counterfactuals.
- Candidate ties use priority then gid. Search restarts on the top 100 candidates
  after 60 seconds. Full pipeline regression now enforces the spec's five-minute
  limit, allowing that fallback plus layout/export time.

## Threshold tuning (spec 04b)

- Remove the source-community coordinator alternative. Two consolidator-candidate
  payers still yield 94 coordinators; the prescribed fallback of three yields 29,
  while 38 nodes retain consolidator roles. Candidates still have in-degree >=5.
- Three scatter/gather branches with every edge >=50,000 KZT yield 25 targets;
  the 100,000 KZT fallback is unnecessary. Amounts are aggregate edge totals.
- These thresholds are tuned on the supplied graph for reviewable hypotheses,
  not validated against role labels. Revisit with labelled analyst feedback.

## Viewer polish: retained hierarchy

- Skeleton view uses the 446 exported retained edges, not all 472 observed edges
  induced by its 174 nodes. This preserves the pipeline's pruning semantics.
- Rows use existing shortest seed-hop levels (seeds below). Role hypotheses do
  not override measured levels; rows do not establish organizational authority.
- Skeleton view shows every retained node, including peripheral seeds, independent
  of the normal overview filters. Clicking a member preserves this layout.

## Viewer polish: ego ordering

- Ego starts at one hop and includes peripheral neighbors despite the overview
  filter. Direct neighbors sort by total observed amounts exchanged with the
  selected account. Reciprocal neighbors occupy the payer side once; arrows
  preserve direction and offset labels distinguish amounts.
- Optional second-hop accounts appear on the side with the greater summed
  amount to direct peers, with payer-side and gid tie-breaking. Tall columns
  keep readable spacing and vertical pan rather than shrinking all labels.

## Viewer polish: overview bounds

- Initial overview and Overview fit the largest weakly connected component,
  computed from both edge directions. The supplied graph has 1,877 members.
  Peripheral visibility does not change this membership; smaller components
  retain their coordinates and remain searchable. Equal-size components choose
  the one containing the smallest string gid; isolates participate normally.

## Submission startup (spec 05)

- Docker installs the committed lockfile without a ranges fallback: failure must
  be visible instead of silently changing the tested dependency set. This
  supersedes the Docker fallback in historical D6.
- Startup checks all eight artifacts, including the hierarchy/continuation and
  counterfactual exports. Any missing/empty artifact triggers recomputation.
  The health start period covers the case's five-minute pipeline budget.

- Fly deployment is authorized after spec 05 E passes, superseding the earlier
  no-Fly deferral. Use 1 GiB / 1 shared CPU: the 512 MiB Docker check passed
  (411 MiB peak RSS, 54.72s), but the Fly VM OOM-killed the computation near
  399 MiB anonymous RSS once VM/runtime overhead was included.
  Fly's validator caps HTTP startup grace at 60 seconds, so configure that
  supported value; Docker retains its 300-second local startup grace. No
  application secrets are required for the case scenario.

## Spec 06 inspection geometry

Circle radii stay at 3 + 9 * priority screen pixels. Exported coordinates use
spatial-hash repulsion for up to 200 passes plus deterministic free-space
placement for residual collisions. Browser inspection positions are separated
at the fitted neighborhood scale and reused at higher zoom, so zooming inward
cannot recreate overlap. Zooming below that threshold returns to the base layout.
Priority-descending placement preserves important accounts first; drawing and
picking use the same priority and gid tie-break. Ego columns use incoming-only
and outgoing-only traversal; nearest displayed hop wins, then payer side.
Columns cap at 25 by flow, expand only displayed parents, and pack around parent
barycentres. Long columns remain pannable to preserve screen-size click targets.
