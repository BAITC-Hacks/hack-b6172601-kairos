# Spec 04b — threshold tuning after spec 04 (<= 15 minutes). Read 00_CONTEXT.md and docs/STATE.md first.
Spec 04 results show two rules that are too loose and make the output hard to defend in front of the jury:
- coordinator 194 vs consolidator 8: the "source clusters" clause turns most collectors into coordinators.
- scatter_gather fires on 955 nodes: with 2 branches it is almost every node in the big component — not a signal.

Changes (pipeline/config.py + rule code, nothing else):
1. Coordinator = not seed AND receives from >= 2 consolidator candidates (in_deg >= 5). Remove the source-cluster clause.
   If the result is still > 30 nodes, raise to >= 3 consolidator candidates. Print the chosen threshold.
   Target: coordinator 5-30, consolidator >= 30.
2. scatter_gather: >= 3 distinct intermediaries, each branch edge >= 50,000 KZT, source is the same account, within 3 hops.
   Target < 100 nodes; if more, raise branch amount to 100,000.
3. Re-run make pipeline, print role and flag counts; make sure top_nodes `why` still reads well; README role table and
   docs/STATE.md updated with the final thresholds and counts; pytest green.
4. The generated out/ files (nodes_roles.csv, clusters.csv, top_nodes.csv, metrics.csv, graph.json, extension_requests.csv,
   blocking_plan.csv, skeleton_edges.csv) ARE required case deliverables ("Exports: yes" in the brief) and are derived from
   the anonymised organiser dataset. The repository owner authorises committing and pushing them to the organiser repository.
Commit "H4: tune coordinator and scatter-gather thresholds; publish exports", git push.
