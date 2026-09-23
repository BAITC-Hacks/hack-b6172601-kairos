# Current handoff

Updated: 2026-09-23. Assigned work: docs/specs/04_FINDINGS.md only.
Order: A, D, E, G, B, C, F; H is README text only.
Specs 01 (offline pipeline) and 03 (viewer) remain implemented.
Official immutable data: 2,248 nodes, 3,119 edges, 4,840 transactions.
No Fly changes. Deadline 18:00 Asia/Almaty.

## Finished sections

- A: clusters assigned before two-pass roles. Consolidator candidates use in-degree
  >=5; coordinator precedence requires a non-seed with >=2 candidate payers or
  >=2 source clusters and in-degree >=3. Betweenness only breaks score ties.
  Cluster summaries use final roles/priorities. README role rule updated.
- D: boolean common-counterparty, synchronous-inflow, fast-pass and scatter/gather
  findings; one-sentence explanations and capped pre-normalization priority bonus.
- E: empirical visible-peer continuation estimates, cut-off evidence and
  extension_requests.csv sorted by taint; empty-bin fallback is documented.
- G: two-sided hierarchy trace, small-edge filter, skeleton_edges.csv and
  boolean membership / shortest seed-hop levels in metrics and graph JSON.
- Existing user edit to 00_CONTEXT.md is included with A.

## Verification

- Section G: full pytest -q passes (54 tests); smoke, language and diff checks pass.

- Section E: full pytest -q passes (53 tests); smoke, language and diff checks pass.

- Section D: full pytest -q passes (52 tests); smoke, language and diff checks pass.

- Section A: full pytest -q passes (51 tests); language guard and local HTTP
  smoke pass. Local server started on port 8000 with approved socket access.
- Existing pipeline tests execute two official-data runs and enforce deterministic
  CSVs, all-node coverage, score bounds and runtime below 60 seconds.

## Next

Implement B, C, F in order. Test, update this file, commit and push each
section. Add H documentation only. End with make pipeline and report computed
role counts, flag counts and blocking summary.
