# Spec 06 — extras after spec 05 (only if spec 05 E passed). Read 00_CONTEXT.md and docs/STATE.md first.
Timebox: stop, commit and push by 17:35 whatever the state. Do items in order; commit + push after each.

## 1. No overlapping circles
Nodes must never cover each other.
- Pipeline (graph.json x,y): after the layout, run an overlap-removal pass: for every pair of visible-size circles closer than
  (r_a + r_b + 2px-equivalent), push them apart along the line between centres; iterate until no overlaps or 200 passes.
  Use a grid/spatial hash so it stays fast. Radius must match the viewer formula (3 + 9*priority in screen px at zoom 1).
- Viewer: apply the same collision pass (in JS, a few iterations) for layouts computed in the browser: ego view columns
  (vertical spacing >= 2r + label height), hierarchy skeleton rows (spread wide rows into several sub-rows if needed),
  and after the zoom level changes if radii are scaled.
- Zoom rule (clarified by the owner): when zoomed IN (from the zoom level where the selected neighbourhood fills the screen
  up to max zoom) circles must not overlap, so every coordinator/consolidator is easy to click. When zoomed far OUT,
  overlap is acceptable. Simplest way: keep circle radii in screen pixels and make sure the data-space separation from the
  overlap-removal pass is enough at that zoom level; raise max zoom if needed. Clicks pick the top-most, highest-priority node.
- Labels (amounts on edges, gid tags) should not sit on top of circles; skip a label if it would overlap.

## 1b. Ego view: every hop in its own column (do together with item 1)
Today the 2nd hop is drawn as one pile. Instead lay out a layered left-to-right tree:
  ... payers-of-payers (hop -2) | payers (hop -1) | SELECTED | recipients (hop +1) | recipients-of-recipients (hop +2) | ...
- Controls: "Hops: 1 / 2 / 3 / 4" (default 1). Each hop is a separate column with equal spacing; the canvas widens/zooms to fit.
- Inside a column, order nodes next to their parent in the previous column (barycentre ordering) to minimise edge crossings;
  nodes reached from several parents are drawn once, placed at the average of their parents (this makes convergence visible).
- Column headers: "Payers of payers", "Payers", "Recipients", "Recipients of recipients", ...
- Max 25 nodes per column by amount; the rest collapse into a "+N more" chip.
- No overlaps (item 1 rules), amount label on every edge, arrows show direction.

## 2. Drag nodes
Mouse-drag a node to move it (overview, ego view, skeleton). Dragging the background still pans. Positions reset on "Overview".
Connected edges follow the node while dragging.

## 3. Finding "shared-source twins" (possible single controller)
Pairs of accounts with >= 3 shared payers and Jaccard(payers) >= 0.5 (the real data has ~45 such pairs; top-1 and top-2 share
all 4 payers of top-2). Add finding `shared_sources_twin` + column `twin_gids` in metrics.csv; group twins transitively into
`twin_group` ids; out/twin_groups.csv (group_id, gids, shared_payers, total_in_kzt, hypothesis =
"Accounts receiving from the same collectors — possibly one controller or deliberate split of proceeds; review together").
Priority bonus as other findings. Node card: "Twin accounts: …963100 (4 shared payers)" with click-through.
Update README findings list and STATE.md.

## 0. Legend order = hierarchy (2-minute fix, do first)
Role legend, filters, role lists and README tables list roles top-down by level in the money chain:
coordinator (candidate organiser) -> consolidator (collector) -> transit -> distributor -> terminal -> peripheral.
Add a one-line hint under the legend: "Money flows up: seeds -> consolidators -> coordinators."
Keep CSV column values unchanged.
