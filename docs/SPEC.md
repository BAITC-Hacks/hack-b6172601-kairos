# Money Graph: case specification

Selected by the user on 2026-09-23. This replaces the generic scaffold scope.
Source: https://docs.google.com/document/d/1JPLU-G6R25Ge2hVaY2J9cqvrx7FGExj87XKwJPaMz3o/edit
Original task, dataset README, archives and starter: ../case-materials/finance/.
Read SPEC.md, DECISIONS.md, STATE.md, PLAN.md and AGENTS.md before implementation.

## Goal and scenario
An AML analyst loads the supplied transaction graph, runs a reproducible local
analysis, inspects role hypotheses and communities, and finds any gid and its
connections in a directed graph. Rankings are investigation priorities, never
claims of guilt. No external enrichment or invented customer attributes.

## Inputs
- data/raw/edges.parquet: src, dst, sum_kzt, n_tx, depth; expected 3,119 rows.
- data/raw/nodes.parquet: gid, depth, is_seed; expected 2,248 rows, 81 seeds.
- data/raw/transactions.parquet: src, dst, date, sum_kzt; expected 4,840 rows.
- Period: July 2026; transfers >= 5,000 KZT; outgoing traversal to depth 4.
Counts are validation expectations for supplied data, not hardcoded output logic.

## Mandatory deliverables and acceptance
1. One documented command from raw Parquet to all three CSV outputs in under
   five minutes on a normal laptop, without API keys, paid services or manual steps.
2. nodes_roles.csv: gid, role, role_score, cluster_id, priority_score, evidence.
   Exactly one row per input node, including isolates; scores finite in [0,1];
   evidence nonempty, numeric and <=200 characters.
3. Formal, documented rules/metrics/thresholds for each role:
   consolidator, transit, distributor, terminal, coordinator, peripheral.
   Explain any arbitrary gid from actual metrics. Scores are heuristic support,
   not calibrated probabilities; there are no ground-truth role labels.
4. clusters.csv: cluster_id, n_nodes, n_seed, sum_kzt_internal, top_gids, hypothesis.
   Every node has a cluster; all clusters have explanations.
5. top_nodes.csv: rank, gid, role, priority_score, why; >=20 unique nodes in
   descending priority with deterministic tie-breaking.
6. Viewer: directed edges, roles/clusters, search by gid, node details and neighbors.
7. README: one-command launch, methods and thresholds, outputs, limitations,
   scaling to approximately one million nodes. Architecture diagram and five-minute
   demo with a live run and explanations of 2-3 nodes.

## Data interpretation invariants
- Depth-4 nodes without outgoing edges are censored, not proven terminals.
- Incoming flows are incomplete, especially for seeds. Observed net flow is not
  an account balance; pass-through >1 is not by itself suspicious.
- Add ALL nodes before edges; retain isolated seeds in metrics and outputs.
- Validate node identifiers, edge endpoints, transaction-to-edge sums AND counts,
  finite/nonnegative amounts and duplicates. Report discrepancies, do not hide them.
- Preserve direction and weights in role metrics. If clustering an undirected
  projection, sum both directional weights and document that choice.
- Do not use transfer amounts directly as path distances without justification.
- Do not infer guilt, identities, or missing transfers. Explain uncertainty.
- Real dataset is immutable. Remove synthetic seeding from the case runtime.

## Scope
Implemented milestones: docs/specs/01_PIPELINE.md, docs/specs/03_VIEWER.md, docs/specs/03b_VIEWER_POLISH.md (items 1-8), and docs/specs/04_FINDINGS.md (A-G code, H documentation only),
with threshold tuning in docs/specs/04b_TUNING.md, following 00_CONTEXT.md.
Coordinators are non-seeds receiving from >=3 first-pass consolidator candidates
(in-degree >=5); source clusters do not qualify. Scatter/gather requires >=3
distinct first intermediaries on simple 2-3-hop paths from one source to a target,
with every path edge >=50,000 KZT. The pipeline also produces extension_requests.csv, skeleton_edges.csv and
blocking_plan.csv for continuation, hierarchy and counterfactual analysis.
It produces metrics.csv and graph.json
in addition to the three required case CSVs. The read-only viewer serves these
artifacts through the six endpoints specified in 03_VIEWER.md, preserving exact
string identifiers, and provides offline canvas exploration. Spec 03b item 4 adds
pipeline-generated role_explanation (ordered failed rules through the match) and
priority_explanation (weighted components, bonus, multipliers, normalization and
score) to graph nodes and JSON-valued metrics.csv columns. Node details expose
these as structured JSON; the browser only displays them. Spec 03b item 7 adds
GET /api/accounts with exactly one validated role or flag filter, returning
gid, role, priority_score and findings in priority-descending/gid-ascending order.
Extension requests require truncated and p_continues >= the configured threshold. Spec 03b item 8 adds GET /api/skeleton for the exact retained edge list with
string source/target identifiers and sum_kzt. The viewer groups skeleton nodes
by observed seed-hop level and preserves the layout while inspecting a member.
Spec 03b item 5 adds GET /api/method with steps and ordered role rules generated
from pipeline/config.py; the header modal displays this response.
Spec 05 is authorized for cleanup, README/disclosure, clean-start verification
and Fly deployment after the remote clean-clone gate. Other specs remain out of scope.

Core: deterministic graph analysis, role hypotheses, ranking, clustering, CSV,
interactive viewer, documentation and meaningful tests. Reuse FastAPI and Docker.
Optional only after core passes: temporal indicators and an LLM analyst assistant.
No account blocking, external notifications or law-enforcement submissions.
No model training, auth platform, cloud dependency or broad framework rewrite.
