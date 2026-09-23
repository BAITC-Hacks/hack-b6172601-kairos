# Implementation and coordination plan

## Clock
User-reported actual start: 2026-09-23 13:33 Asia/Almaty (UTC+05).
Confirmed deadline: 18:00, per the user's latest correction. No extension.
Five hours from start would be 18:33, but the confirmed deadline is 18:00.
Relative checkpoints: 14:33, 15:33, 16:33, 17:33; official reporting
boundaries remain unconfirmed. Push real progress before 14:00, 15:00, 16:00,
17:00 and final deadline as a conservative safeguard.
The hourly_commit.sh script incorrectly starts the clock on first invocation
for this situation: supply the real start timestamp or explicitly label commits.
Do not commit its local .hackathon_start marker accidentally.

## Milestones (local time)
- 13:40-14:00: inspect current tree; disclose and commit scaffold separately;
  import official data; install pandas/pyarrow/networkx (+ scipy if required by
  PageRank); validate actual data and run a deterministic baseline. First push.
- 14:00-15:00: all nodes get explained role hypotheses, priorities and communities;
  generate three schema-valid CSVs; viewer renders selected neighborhoods.
- 15:00-16:00: integrate full flow, search, role/cluster filters, exports and node
  evidence; test isolates, censored boundary, missing inflows and repeatability.
- 16:00-16:45: inspect representative real nodes, tune defensible rules, finish
  mandatory gaps. Add temporal evidence only if all must-haves already pass.
- 16:45-17:30: feature freeze; clean Docker run without .env/network at runtime;
  benchmark, verify CSV schemas, README, disclosure, architecture and demo.
- 17:30-18:00: final push and platform submission, verify submission state and buffer.
Replan against real progress. Never skip a working deliverable to preserve this schedule.

## Ownership and delegation
Root owns contracts, role-method review, API integration, README/state and commits.
Use gpt-6-sol for bounded implementation tasks, with a fresh compact briefing.
Usually two workers; at most three alongside root. Never have two writers own
one file. Agree interfaces BEFORE dispatch; no worker commits or pushes.
- Worker A: app/analysis/*, pipeline CLI and its focused tests. Implements loading,
  metrics, rules, clustering, ranking and exports against the agreed contract.
- Worker B: static/* viewer. Uses an explicitly agreed graph/node/output API contract;
  graph assets must be bundled locally, not fetched from a CDN at runtime.
- Worker C when useful: independent data/rule/output review; read-only first.
Claude is available on a standard account and may already be thinking with the
user. Give it a bounded independent methodology review, no overlapping writes.
Do not start a second autonomous Claude coding process by assumption.

## Proposed architecture (confirm before workers begin)
app/analysis/ produces one serializable analysis result and three CSV files.
A Python CLI runs the pipeline independently of FastAPI. FastAPI exposes results,
node details/neighborhoods and downloads; the viewer reads the same computed result.
Batch computation happens once per dataset, not once per displayed node.
Deterministic seeds/tie-breaks and stable cluster IDs. Local storage is sufficient.
Avoid pushing the entire 2,248-node layout at a user by default: use a community
summary plus searchable ego graph, with access to all nodes including isolates.

## Starting method, subject to data validation
Use a small set of transparent directional metrics: payer/payee count, observed
amounts and transaction counts, seed reachability, PageRank, retention/pass-through
only where interpretable, and optionally time patterns. Candidate role scores can
overlap; document primary-role precedence and alternative evidence. A coordinator
hypothesis requires more than simply high PageRank. Do not hardcode any gid.
Cluster a weighted undirected projection with a fixed random seed, assigning
isolates explicitly. Do not force the eight communities mentioned in the task.

## Validation and scope control
Prioritize output schema/coverage, actual sums/counts, uncertainty handling,
determinism, budgeted runtime and successful UI search. Test computation invariants,
not prose snapshots. Existing scaffold tests/verification assume synthetic finance
accounts: adapt or remove obsolete checks honestly as those features are replaced.
Keep secret/image and clean-start protection. Full integration checks at milestones;
focused tests during individual edits. No repeated paid LLM probes.
Fly deployment is explicitly deferred by the user. Core works fully locally.
