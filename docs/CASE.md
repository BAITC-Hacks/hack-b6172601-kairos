# Case: Money Graph — reconstructing the financial structure of an organized group (HackAlem AI, Finance track)

Source: organizer brief (Google Doc). Condensed English copy for agents. Findings must be phrased as hypotheses, never as guilt.

## Goal
Pipeline + viewer. From a transaction graph, assign each node a role, rank nodes by priority, cluster the network.
Answer the analyst's question: "which of these 2,248 customers should I look at first, and why".

User: AML analyst at a bank. Scenario: gets 81 seed gids from law enforcement -> loads 4-hop outgoing-transfer export ->
tool builds graph, computes metrics, assigns roles -> analyst sees network map (flow direction, roles, clusters) ->
opens priority top list with rationale ("receives from 11 different payers, passes on 3% of what it receives").

## Input (data/ archive given at start, starter/ code given too)
- edges.parquet (3,119): src, dst, sum_kzt, n_tx, depth — payer->recipient aggregated over period
- nodes.parquet (2,248): gid, depth (min hop), is_seed
- transactions.parquet (4,840): src, dst, date, sum_kzt
- Period 2026-07-01..2026-07-31. Hops: seed 81, h1 472, h2 462, h3 789, h4 444. Total turnover 365,890,012 KZT.

## Output (fixed schema)
nodes_roles.csv — one row per node (2,248): gid int64, role str, role_score float 0-1, cluster_id int, priority_score float 0-1, evidence str (<=200 chars, human-readable)
Roles (minimum; may extend if documented): consolidator, transit, distributor, terminal, coordinator, peripheral
clusters.csv: cluster_id, n_nodes, n_seed, sum_kzt_internal, top_gids, hypothesis
top_nodes.csv: >=20 rows: rank, gid, role, priority_score, why
Viewer: network map with flow direction, role/cluster highlight, search by gid (web page / notebook / desktop).
Full recompute from raw parquet <= 5 minutes, local laptop.

## Data caveats (accounting for them is scored)
- Cut-off at hop 4: 444 nodes depth=4 with zero outgoing = traversal artifact. "out_degree=0 => terminal" gives 444 false sinks.
- Only outgoing transfers traced; incoming from outside sample invisible -> full balance not reliable.
- Seed incoming understated; sent/received ratio wrong for seeds; 354 nodes send more than they received.
- Transactions < 5,000 KZT excluded (structuring below threshold invisible).
- 19 of 81 seeds absent from edges, 12 appear only as recipients -> 31 seeds have no outgoing.
- 16 weakly connected components: 1,877 nodes (46 seeds), 270 (1 seed), 14 of 2-17 nodes.
- No customer attributes, no ground-truth roles -> judged on how well-founded criteria are.

## MUST HAVE (all five, else not complete)
1. Reproducible pipeline: one command from raw parquet to all 3 CSVs, no manual steps, < 5 min on clean machine.
2. Every node (2,248) has role from dictionary, role_score, non-empty evidence.
3. Role criteria documented: formal rule or metric with threshold per role. Jury names 3 gids; team explains in 1 minute.
4. Clustering: clusters.csv filled; cluster_id on every node.
5. top_nodes.csv (>=20, with rationale) + map screen showing flow direction and roles; jury names a gid, team finds it and shows links.

## Optional (extra points)
- Separate true terminals from hop-4 cut-off nodes, justified method.
- Temporal patterns: pass-through within 1-2 days, bursts, synchronized transfers from several payers on same day.
- Recurring routes A->B->C and cycles returning to sender.
- Anomalies: structuring, node profiles anomalous vs their hop.
- Resilience: remove top-N nodes, does network fragment.
- AI assistant: natural-language question ("who collects money from these five?") -> graph-grounded answer with node links.
- Auto node card: role, flows, links, what to look at.
- Completeness: what data is missing, what request to make next.

## Not allowed
Hardcoded gid lists; black-box roles without explainable rule; external enrichment or invented attributes;
requiring cloud cluster / GPU / paid services to reproduce.

## Must account for
Explainability for non-ML analyst; privacy (no names/IIN); careful hypothesis wording; <=5 min local;
local-only (internet only for LLM API if used); Python pandas/networkx recommended;
README section: what changes at ~1M nodes (text only).

## Deliverables
Repo (pipeline + UI source); README (one-command run, role criteria and thresholds, outputs, limitations, scaling);
the 3 CSVs; one solution diagram (data -> metrics -> roles -> interface); 5-min demo (live run + 2-3 nodes).

## Organizer hints
Data has clear candidates: nodes receiving from 8-24 distinct payers; nodes fanning out to 60-116 recipients;
72 nodes with pass-through ratio 0.8-1.2; Louvain gives 8 stable communities with >1 seed.

## Scoring (100)
- Compliance and working main scenario: 25
- Technical implementation (approach, architecture, AI/agentic AI use, matches stated logic): 25
- README and reproducibility: 25
- Value and applicability: 15
- Development potential and originality: 10
