# Current handoff

Updated: 2026-09-23. Specs 01, 03, 03b (all eight items), assigned 04 and 04b
are implemented. Spec 04 H is documentation only; spec 05 is not implemented.
Spec 05 is now authorized in order C, A, B, D, E, F, with a 17:30 Asia/Almaty
hard stop. Deploy only after the remote clean-clone gate passes.

## Viewer polish delivered

- Why this role displays failed preceding rules through the match, measured
  values and configured thresholds. The same predicates assign the role.
- Why this priority displays all five weighted components, finding bonus,
  seed/cut-off multipliers, normalization and payout adjustment. Both explanation
  structures are pipeline-generated in graph.json and JSON metrics.csv columns;
  the node API parses them and the browser does not recompute analysis.
- Selection animates to two-hop bounds; Overview fits the largest weak component
  (1,877 nodes). Drag/wheel/reselection cancel animation; reduced motion works.
- Peripheral starts unchecked (440 role-bearing accounts); role/finding lists
  discover accounts without gids. Five finding filters include 10 continuation
  requests. Selecting a hidden peripheral account reveals it.
- Hierarchy skeleton shows 174 nodes and exactly 446 retained edges, not the
  472-edge induced graph. Observed seed-hop rows put seeds below; selecting a
  member preserves the layout. Normal role filters do not hide skeleton nodes.
- Method modal serves configured rules and six conceptual stages via /api/method.
  Close/Escape preserves the selected account. No thresholds duplicated in JS.
- Ego starts at one hop, with an optional second hop and amount-sorted columns.
  Reciprocal peers occupy the payer side once; arrows preserve directions.
  Outer-column labels and vertical pan keep large neighborhoods readable.
- Added read-only /api/accounts, /api/skeleton and /api/method; no new dependency,
  setting, external service, frontend build or deployment requirement.

## Verification

- Full pytest -q: 71 pass, including two official-data pipeline runs and CSV
  determinism. Existing dependency deprecation warnings remain.
- Expanded HTTP smoke passes on http://localhost:8002. Language and diff guards
  pass. Optional `node tests/test_viewer_layout.js` checks weak components,
  deterministic ties, isolates, official count and camera bounds.
- Manual browser checks: role/priority explanations, lists (29 coordinators,
  10 extensions), hidden account selection, skeleton rows/click persistence,
  Method content/Escape, ego toggle (10 -> 63 -> 10 accounts), and overview fit.
  No browser console errors. Node VM checks also covered animation cancellation,
  ego amount ordering and filter behavior.
- Regenerated exports in 44.89 seconds. Role, top-node, cluster and blocking CSVs
  remain byte-identical to previous output; thresholds and rankings unchanged.
- All eight items committed and pushed separately (item 1 precedes item 7 as its
  click-to-zoom dependency). Raw data is immutable and identifiers stay exact.

## Analysis results and limits

- 2,248 nodes, 3,119 edges, 88 clusters. Roles: coordinator 29; consolidator 38;
  distributor 42; transit 67; terminal 264; peripheral 1,808.
- Findings: common_counterparty 24; synchronous_inflow 38; fast_pass 89;
  scatter_gather 25; likely_legit_payouts 2; seed_hub 9.
- Continuation estimates cover 444 cut-off nodes. Blocking 10 accounts cuts
  14.3094% of modeled repeated-hop exposure, not unique currency or real action.
- Hypotheses are not validated labels; incoming flows are incomplete and depth-4
  outflows unknown. Seed-hop rows are not proven organizational ranks.
- Docker was verified in spec 01, not rebuilt here; startup/dependencies unchanged.

## Spec 05 progress

- C: removed unused synthetic seeder, JSON store and legacy UI helpers plus their
  obsolete tests. Existing generic agent API remains tested infrastructure, not a
  case analyst feature. Make run now uses the installed virtual environment.
  Full tests: 65 pass; language guard passes. Pipeline rerun: 45.79 seconds.
  Removed stale deployment instructions requiring a key.

## Previous handoff

Ready for the next assigned spec. Do not start spec 05 or deploy automatically.
The updated viewer is served locally on port 8002; an older process on port 8001
needs restarting to understand the new explanation columns.
