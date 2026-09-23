# Current handoff

Updated: 2026-09-23. Specs 01, 03, assigned 04 and 04b tuning are implemented.
Spec 04 H remains documentation only. Specs 03b and 05 are committed as requested
but not implemented. No Fly changes. Deadline: 18:00 Asia/Almaty.

## Final tuning (spec 04b)

- Coordinator: non-seed receiving from >=3 first-pass consolidator candidates
  (in-degree >=5). Source communities no longer qualify. The initial threshold
  of two yielded 94 coordinators; the prescribed fallback of three yields 29.
- Scatter/gather: >=3 distinct first intermediaries on simple 2-3-hop paths from
  one source to a target; every edge >=50,000 KZT. This yields 25 targets, so the
  100,000 KZT fallback is unnecessary. CLI prints both chosen thresholds.
- README rules/counts, SPEC and DECISIONS reflect the final contracts.
- All eight required out/ exports are regenerated. extension_requests.csv is
  byte-identical to its previous version. All 30 top-node reasons were reviewed:
  role evidence, finding sentences and priority drivers reflect the tuned rules.

## Verified final results

- Final make pipeline: 42.20 seconds; 2,248 nodes, 3,119 edges, 88 clusters.
  Full blocking candidate search completed without the top-100 fallback.
- Roles: coordinator 29; consolidator 38; distributor 42; transit 67;
  terminal 264; peripheral 1,808. Existing peripheral-count warning remains.
- Flags: common_counterparty 24; synchronous_inflow 38; fast_pass 89;
  scatter_gather 25; likely_legit_payouts 2; seed_hub 9.
- Skeleton: 174 nodes, 446 edges. Continuation estimates for all 444 cut-off
  nodes; 10 extension requests at the 0.5 threshold.
- Blocking 10 accounts cuts 14.3094% of observed repeated-hop exposure.
  This is a model counterfactual, not unique currency or a real blocking action.
- HTTP smoke test passes against the local service on http://localhost:8001.
- Focused findings tests: 9 pass, including first/middle/final edge amount
  boundaries, distinct intermediaries, source, hop and cycle checks.
- Full pytest -q: 60 tests pass, including two complete official-data runs,
  seven-CSV determinism, role/flag targets and viewer integration. Existing
  dependency deprecation warnings remain. Language guard and git diff checks pass.

## Contracts and limitations

- Every node is retained. Input data stays immutable; gids remain exact strings
  in browser/CSV ingestion. No dependencies, settings or external enrichment added.
- Roles/findings are hypotheses tuned on this graph, not validated labels.
  Observed inflows are incomplete, cutoff outflows unknown; timing correlation
  does not establish transfer provenance.
- Continuation uses visible depth 1-3 peer frequencies; empty cells use their
  population mean. Skeleton levels are shortest seed-hop distances, not proven rank.
- Blocking uses fixed original dilution denominators and 20 synchronous passes.
  Its cumulative share includes prevented inflow to removed nodes and downstream
  exposure; selection excludes the candidate's own inflow.
- Docker was verified in spec 01, not rebuilt here; startup/dependencies unchanged.
  No viewer code changed in this block.

## Artifact publication and next session

The repository owner explicitly authorizes committing and pushing all eight
generated out/ artifacts to the organiser repository as required case deliverables.
Include the requested 03b_VIEWER_POLISH.md, 04b_TUNING.md and
05_README_DEPLOY.md specs in the same commit.
Await the next assigned spec; do not implement others automatically.
