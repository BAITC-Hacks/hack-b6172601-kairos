# Current handoff

Updated: 2026-09-23. Phase: spec 01 pipeline implemented and verified for H2.
Hackathon start: 13:33 Asia/Almaty. Deadline: exactly 18:00. No Fly changes.
Work only in hack-b6172601-kairos; sibling kairos is the original scaffold reference.

## Read first

AGENTS.md, docs/SPEC.md, docs/DECISIONS.md, then docs/specs/00_CONTEXT.md and
only the assigned implementation spec. This milestone implements 01_PIPELINE.md.
Other specs, case APIs, graph viewer and LLM analyst are not implemented.

## Done and key files

- H1 scaffold import is committed and pushed as b92291c.
- data/raw/*.parquet: immutable official inputs, 2,248 nodes, 3,119 edges,
  4,840 transactions. All nodes, including isolates, participate in analysis.
- pipeline/load.py validates schema, identifiers, endpoints and aggregate sums/counts.
- pipeline/features.py computes degrees/amounts/counts, seed sources, weighted
  PageRank, exact directed betweenness and the specified temporal fast-pass share.
- pipeline/taint.py implements synchronous haircut tracing, including dilution.
- pipeline/config.py contains the role thresholds, ranking weights and runtime
  settings; role_rules_markdown() generates the README role table.
- pipeline/roles.py, clusters.py and priority.py implement first-match roles,
  deterministic weighted Louvain communities, scores and numeric explanations.
- pipeline/export.py and run.py write the four CSVs and graph JSON with exact
  string identifiers for browsers. make pipeline runs the offline CLI.
- out/: generated artifacts, including the top 30 accounts and all node metrics.
- tests/test_pipeline.py: schemas, node coverage, bounds, membership, ranking,
  cutoff handling, two-run CSV determinism, runtime, taint, timing and validation.
- scripts/entrypoint.sh computes missing outputs before the retained HTTP app starts;
  missing raw data is an error. Docker ignores local outputs and secrets.
- requirements.txt and requirements.lock.txt include the four allowed data/graph
  dependencies. Lock aligned across local Python 3.14 and Docker Python 3.11.
- Old sample finance tools and JSON datasets removed; scaffold dispatcher tests use
  test-only tools. README and clean-copy/full verification scripts updated.

## Results and verification

- Requested make pipeline completed in 35.20 seconds: 2,248 nodes and 88 clusters.
- Roles: coordinator 19; consolidator 44; distributor 42; transit 67;
  terminal 270; peripheral 1,806. The specified >500 warning fires for peripheral.
- Requested pytest -q: 44 tests passed, including two full runs with identical CSVs
  and individual runtime below 60 seconds. Only dependency deprecation warnings.
- Final full scripts/verify_all.sh: passed (exit 0), including repeated pytest,
  dependency/language checks, clean-copy pipeline and HTTP smoke checks, Docker
  build/start without a key, generated outputs and secret exclusion. Negative
  missing-input container check correctly failed. Lock installed without fallback.
  Verification log: /private/tmp/moneygraph-full-verify.log (local, not committed).
- No external LLM calls or deployments made during this milestone.

## Deviations and clarifications

- Aggregate sums use absolute tolerance 0.000001 KZT, relative tolerance zero;
  counts must match exactly. Two official sums differ only through binary float
  accumulation (about 1e-11 KZT); exact float equality falsely rejects valid input.
- NetworkX public spring_layout needs SciPy at this graph size. To preserve the
  allowed dependency list, the fallback uses NetworkX's dense NumPy
  Fruchterman-Reingold routine, seed 42, unweighted edges and 100 iterations,
  scaled to [-1000,1000]. This private API is pinned and tested end to end.
- Weighted PageRank uses NumPy power iteration because NetworkX's public version
  also depends on SciPy; the weighted random-walk definition is unchanged.
- Seeds may match terminal only through observed zero out-degree, never through
  pass-through ratio, following the spec's explicit seed exception.
- Runtime exceeds the aspirational 30-second target but meets the strict 60-second
  regression limit and five-minute task limit. No approximate betweenness used.
- fast_pass_share is temporal correlation after ANY inflow, not matched money.
  Scores and cluster narratives remain investigation hypotheses, not guilt claims.

## Next steps

This state accompanies the requested H2 pipeline commit. Await the next assigned
spec; do not implement other specs automatically. For a new session this file and
the assigned spec are sufficient; review git status before editing.
Use bounded Sol workers when useful, one writer per file; root owns integration.
Claude remains a user-coordinated reserve reviewer. No Fly changes unless requested.
