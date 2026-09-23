# Spec 03b — small viewer fixes (<= 20 minutes). Read 00_CONTEXT.md and docs/STATE.md first. Run after spec 04.
Search, node card and top list already work. Only these three fixes, no new features:
1. Zoom to focus: when a node is selected (search, top list, click, link in the card), animate pan+zoom so the node and its
   1-2 hop neighbourhood fill ~80% of the canvas. "Overview" button zooms back to fit.
2. Initial overview = fit to the largest connected component (1,877 nodes), not to all nodes, so it is not a tiny blob.
   Small components may stay where they are.
3. Ego view: 1 hop by default (payers left, node centre, recipients right, sorted by amount), toggle "Show 2nd hop".
   Amount labels next to the column end of each edge so they do not overlap in the centre.
Done when: manual check, pytest green, STATE.md updated, commit "H4b: viewer zoom-to-focus and cleaner ego view", git push.
4. Node card block "Why this role" (for the jury question "explain this gid in one minute"): show the rule that fired with the
   node's own numbers vs thresholds from pipeline/config.py, e.g.
   "Rule 2 consolidator: payers 8 >= 5 ✓" and the rules checked before it that did NOT fire ("Rule 1 coordinator: consolidator payers 1 < 2 ✗").
   Also "Why this priority": the weighted components (taint 30% -> 0.28, seeds within 2 hops 20% -> 0.19, ...) and multipliers.
   Data comes from the pipeline (add the needed fields to graph.json / metrics.csv), no recomputation in JS.
5. Header button "Method": a modal with the pipeline steps (data -> features -> taint -> rules -> clusters -> priority) and the
   role rules table with thresholds (served from a small /api/method endpoint built from config.py).

## Addendum — finding suspects without knowing a gid (do right after item 4)
6. Default overview hides `peripheral` (checkbox unchecked) so the map shows ~440 role-bearing accounts, not a blob of 2,248.
7. Clicking a role name in the legend opens a list of that role's accounts sorted by priority (short gid, priority, first
   finding) in the sidebar; click -> focus + zoom. Same for a "Flagged" section: common_counterparty, synchronous_inflow,
   scatter_gather, likely_legit_payouts, extension requests (truncated with p_continues >= 0.5).
8. Button "Hierarchy skeleton" (graph.json already has `skeleton`/`level`): show only skeleton nodes laid out in rows by
   hierarchy_level (seeds at the bottom, coordinators at the top), edges with arrows. Click -> node card.
