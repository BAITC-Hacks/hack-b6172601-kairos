# Current handoff

Updated: 2026-09-23. Specs 01, 03 and assigned 04 are implemented.
Spec 04 order completed: A, D, E, G, B, C, F; H is README text only.
Every section passed full pytest and was committed/pushed before the next.
The existing 00_CONTEXT.md edit was included in the first section commit.
No other specs implemented. No Fly changes. Deadline: 18:00 Asia/Almaty.

## Implemented in spec 04

- Two-pass coordinator roles using first-pass consolidator candidates or source
  clusters; clustering precedes roles, summaries use final roles and priorities.
- Boolean findings, sentence explanations and capped priority bonus; payout
  caution halves normalized priority, seed-hub flag leaves priority unchanged.
- Visible-peer continuation estimates for all 444 truncated nodes; 10 extension
  requests above the 0.5 threshold, sorted by taint.
- Two-sided hierarchy skeleton: 232 nodes, 600 edges; membership and seed-hop
  levels in metrics/graph JSON. No optional skeleton viewer toggle.
- Ten greedy counterfactual removals, fixed original dilution denominators and
  20 synchronous passes; deterministic priority/gid ties and timed top-100 fallback.
- Viewer accepts findings text and shows it on node cards. Other UI unchanged.
- README documents rules, outputs, interpretation and future analyst feedback only.

## Verified final results

- Full pytest -q: 59 tests pass. Includes two official-data pipeline runs,
  deterministic equality of all seven CSVs, output coverage, flags, coordinator
  rule, cut-off exports, monotone blocking, fallback, cycles and viewer integration.
- Final make pipeline: 47.60 seconds; 2,248 nodes, 3,119 edges, 88 clusters.
  Full blocking candidate search completed without the top-100 fallback.
- All seven refreshed CSVs match the tested artifacts byte for byte.
- Roles: coordinator 194; consolidator 8; distributor 30; transit 57;
  terminal 202; peripheral 1,757. Existing peripheral-count warning remains.
- Flags: common_counterparty 24; synchronous_inflow 38; fast_pass 89;
  scatter_gather 955; likely_legit_payouts 2; seed_hub 9.
- Blocking 10 accounts cuts 14.3094% of observed repeated-hop transfer exposure.
  This is a model counterfactual, not unique currency or a real blocking action.
- Smoke passes against regenerated outputs on http://localhost:8001.
  Browser verified full gid search, final role counts and the findings node card.
  Existing port 8000 service was left untouched.
- JavaScript syntax, language guard and git diff checks pass. Existing dependency
  deprecations and harmless sandbox CPU-cache inspection warnings remain.
- Independent read-only rule and blocking review completed; evidence wording
  corrected to distinguish first-pass candidates from final consolidator roles.

## Contracts and limitations

- Every node is retained. Input data stays immutable; gids remain exact strings
  in browser/CSV ingestion. No external enrichment, keys, dependencies or settings added.
- Roles/findings are hypotheses. Observed inflows are incomplete, cutoff outflows
  unknown; timing correlation does not establish transfer provenance.
- Continuation uses visible depth 1-3 peer frequencies; empty cells use their
  population mean. Skeleton levels are shortest seed-hop distances, not proven rank.
- Blocking cumulative share includes prevented inflow to removed nodes plus
  downstream exposure; its selection objective excludes the candidate's own inflow.
- Docker was verified in spec 01, not rebuilt here; startup and dependencies unchanged.

## Next session

Ready for handoff. Await the next assigned spec; do not implement others automatically.
User-created untracked 03b_VIEWER_POLISH.md, 04b_TUNING.md and
05_README_DEPLOY.md were left untouched.

## Artifact publication

The user explicitly approved publishing the verified regenerated out/*.csv and
out/graph.json artifacts to the existing repository after the automatic review
rejection. This artifact commit records that approval and includes all seven CSVs
and graph JSON. No code changed after the 59-test suite and final pipeline run.
