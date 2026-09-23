# Spec 01 — core pipeline (MUST HAVE 1-5 data part). Read 00_CONTEXT.md first.

## Deliverable
`python -m pipeline.run --data data/raw --out out` (also `make pipeline`) writes:
out/nodes_roles.csv, out/clusters.csv, out/top_nodes.csv, out/metrics.csv (all features), out/graph.json (for the viewer).
Package layout: pipeline/{__init__,load,features,taint,roles,clusters,priority,export,run}.py. Thresholds live in ONE place:
pipeline/config.py (a dataclass), so README can quote them.

## 1. Load + validate
Read the three parquet files, assert edges == transactions aggregated by (src,dst) (sum and count), assert 2,248 nodes.
Nodes without any edge (31 seeds etc.) must still appear in every output.

## 2. Features (one row per gid -> out/metrics.csv)
in_deg, out_deg, in_kzt, out_kzt, in_tx, out_tx, depth, is_seed
pass_through = out_kzt / in_kzt (NaN if in_kzt == 0)
truncated = depth == 4 and out_deg == 0
seed_payers_direct = number of distinct seeds paying the node directly
seed_sources_2hop = number of distinct seeds that reach the node within <= 2 hops
pagerank (weighted by sum_kzt), betweenness (directed, weight = 1/sum_kzt is NOT needed — use unweighted, exact)
consolidators_linked = computed after roles (optional)
fast_pass_share = share of out_kzt sent within 2 days (0..2) after any incoming transfer to that node (NaN if no inflow)

## 3. Taint (amount-weighted, "haircut" method from blockchain AML) -> taint.py
Seeds emit 100% "case money". For non-seeds:
  taint_in(v)  = sum over edges u->v of sum_kzt(u->v) * share(u)
  share(u) = 1.0 if u is seed else min(1, taint_in(u) / max(in_kzt(u), out_kzt(u)))   (dilutes when the node sends external money)
Iterate until max change < 1 KZT or 20 passes (graph can have cycles). Output taint_kzt = taint_in, taint_share = share.
This is the main "how much case money reached this node" metric.

## 4. Roles — first matching rule wins, in this order (thresholds in config.py)
1 coordinator : not seed AND betweenness >= 99th percentile AND in_deg >= 2 AND out_deg >= 2
2 consolidator: in_deg >= 5                                   (51 candidates)
3 distributor : out_deg >= 10 AND out_deg >= 2 * max(in_deg,1) (fan-out)
4 transit     : not seed AND in_deg >= 1 AND out_deg >= 1 AND 0.8 <= pass_through <= 1.2
5 terminal    : depth <= 3 AND in_kzt > 0 AND (out_deg == 0 OR pass_through < 0.2) AND (in_deg >= 2 OR in_kzt >= 300,000)
6 peripheral  : everything else. Sub-reason recorded in metrics.csv column `peripheral_reason`:
                "cut_off_hop4" (truncated), "one_off_recipient" (single small inflow, stop observed), "isolated_seed" (no edges), "other".
For seeds never use pass_through (their inflow is understated) — the transit rule already excludes them.

role_score (0..1): how clearly the node clears its rule.
  threshold rules: 0.5 + 0.5 * min(1, (value - thr) / thr) using the rule's main metric
  (coordinator: betweenness percentile; consolidator: in_deg vs 5; distributor: out_deg vs 10;
   transit: 1 - |pass_through - 1| / 0.2 mapped to 0.5..1; terminal: in_deg vs 2 or in_kzt vs 300k, whichever is higher).
  peripheral: 0.9 for cut_off_hop4 / isolated_seed / one_off_recipient (we are confident nothing is visible), else 0.6.
Report the count per role in the run log. Expected rough sizes: coordinator 5-25, consolidator ~50, distributor ~40-60,
transit ~60-70, terminal ~100-300, rest peripheral. If a role is empty or > 500, print a warning.

evidence (<= 200 chars, numbers, hypothesis wording). Templates, e.g.:
 consolidator: "Signs of consolidation: receives from 11 payers (3 seeds within 2 hops), 1.1M KZT in, forwards 3%."
 distributor : "Fan-out: sends 4.9M KZT to 61 recipients after receiving from 19 payers."
 transit     : "Pass-through: forwards 97% of 420K KZT received; 85% forwarded within 2 days."
 terminal    : "Money stops here: receives 1.2M KZT from 4 payers, outgoing transfers were traced and none found."
 coordinator : "Bridge: top 1% betweenness, links 3 payers and 5 recipients across the network."
 peripheral  : "Outgoing transfers not observed: graph cut off at hop 4." / "Single inflow of 25K KZT, no further activity."
Truncate safely to 200 chars. Never empty.

## 5. Clusters
Louvain (nx.community.louvain_communities) on the undirected projection, weight = sum_kzt, seed=42, resolution=1.0.
State in README that clustering uses the undirected projection on purpose (community = who trades with whom).
Nodes without edges: each gets its own cluster. Renumber clusters by size desc starting at 0.
clusters.csv: cluster_id, n_nodes, n_seed, sum_kzt_internal (sum of edges with both ends in the cluster),
top_gids (3 highest priority, ";"-joined), hypothesis. Also add helpful extra columns: n_consolidator, n_distributor, n_transit, taint_kzt.
hypothesis templates by role mix (first match):
 >=1 consolidator and >=2 seeds -> "Collection structure: N seeds feed consolidator <gid>; check as a possible cash-collection node."
 >=1 distributor               -> "Distribution structure: funds fanned out by <gid> to N recipients."
 >=3 transit                   -> "Layering chain: N pass-through accounts."
 n_nodes <= 3                  -> "Isolated fragment, low evidence."
 else                          -> "Mixed group of N accounts, no dominant pattern."

## 6. Priority (0..1)
raw = 0.30*pct(taint_kzt) + 0.20*pct(seed_sources_2hop) + 0.15*pct(pagerank) + 0.15*pct(betweenness) + 0.20*role_weight
role_weight: coordinator 1.0, consolidator 0.9, distributor 0.7, transit 0.6, terminal 0.4, peripheral 0.1
multipliers: seed x0.6 (already known — the brief wants focus on who is above them), truncated x0.7
priority_score = raw / max(raw). pct = percentile rank 0..1.
top_nodes.csv: top 30 by priority_score: rank, gid, role, priority_score, why
 why = evidence + " Priority drivers: <two strongest components in words>, e.g. 'high case-money inflow (2.1M KZT), 3 seeds within 2 hops'."

## 7. graph.json (for spec 03 viewer)
{nodes:[{id:"<gid as string>", role, cluster, priority, seed, depth, truncated, x, y, evidence, in_kzt, out_kzt, in_deg, out_deg}],
 edges:[{source, target, sum_kzt, n_tx}], roles_count:{...}, generated_at}
x,y from nx.spring_layout(undirected, seed=42, weight=None, iterations=100) scaled to [-1000,1000].

## 8. Tests (tests/test_pipeline.py, no API key needed)
nodes_roles.csv has exactly 2,248 rows, unique gid, columns in required order, role in dictionary, role_score & priority in [0,1],
evidence non-empty and <= 200 chars; every cluster_id exists in clusters.csv; top_nodes >= 20 rows sorted by priority desc;
no truncated node has role terminal; pipeline runtime < 60 s; running twice gives identical CSVs.

## Done when
`make pipeline` prints the role counts and timing, pytest -q is green, and README has a "Role rules" table generated from config.py values.

## Dependencies
Add to requirements.txt: pandas>=2.2,<3.0 ; pyarrow>=15 ; networkx>=3.2 ; numpy>=1.26. Refresh requirements.lock.txt.
Dockerfile must still build; the container should run the pipeline at start if out/ is missing (entrypoint) so the viewer has data.
