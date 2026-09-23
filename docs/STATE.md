# Current handoff

Updated: 2026-09-23. Specs 01, 03, assigned 04 and 04b tuning are implemented.
Spec 03b item 4 is implemented; remaining viewer polish is in progress with a
16:20 Asia/Almaty hard stop for this task. Spec 05 is not implemented. No Fly changes.

## Viewer polish: item 4

- Node cards show Why this role: failed preceding rules through the first match,
  with actual measurements and thresholds from pipeline/config.py.
- Why this priority exposes all five weighted contributions, finding bonus,
  seed/cut-off multipliers, global normalization and payout adjustment.
- Pipeline exports both explanations as structured graph.json values and JSON
  columns in metrics.csv. The node API parses them; JS does not recompute scores.
- Rule assignment uses the same predicates as the explanation trace. Unknown
  pass-through is shown as unknown. No analysis thresholds or scores changed.
- Regenerated official exports in 44.89 seconds. Worker verified role, top-node,
  cluster and blocking CSVs byte-identical to earlier output.
- Full pytest -q passes (64 tests); focused explanation/findings tests pass. Manual browser verification confirms
  failed coordinator + matched consolidator rules and the full priority breakdown.
- HTTP smoke passes on http://localhost:8002; language and diff guards pass.

## Verified analysis results and limits

- 2,248 nodes, 3,119 edges, 88 clusters. Roles: coordinator 29; consolidator 38;
  distributor 42; transit 67; terminal 264; peripheral 1,808.
- Flags: common_counterparty 24; synchronous_inflow 38; fast_pass 89;
  scatter_gather 25; likely_legit_payouts 2; seed_hub 9.
- Skeleton: 174 nodes, 446 edges. Continuation estimates for all 444 cut-off
  nodes; 10 extension requests at the 0.5 threshold.
- Blocking 10 accounts cuts 14.3094% of observed repeated-hop exposure, a model
  counterfactual rather than unique currency or a real blocking action.
- All nodes retained; raw data immutable; gids remain exact strings in browser.
  No new dependency, setting, external enrichment or deployment change.
- Roles/findings are hypotheses, not validated labels. Incoming flows are
  incomplete and depth-4 outgoing flows unknown. The existing peripheral-count
  warning and dependency deprecation warnings remain.
- Spec 04 H remains documentation only. Docker was verified in spec 01;
  startup/dependencies are unchanged here.

## Next steps

User confirmed the new addendum immediately after item 4: finish items 6, 7,
and 8, then return to items 1, 5, 3, 2. Item 1 camera patch is prepared in
/tmp/kairos-item1-camera.patch for later integration. Commit and push each finished
item, and commit/push working progress by 16:20. Do not start spec 05 automatically.
