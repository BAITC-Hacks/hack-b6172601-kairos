# Spec 04 — role refinement + findings (optional points). Read 00_CONTEXT.md and docs/STATE.md first.
Keep it simple and explainable: every rule = one threshold in pipeline/config.py, every flag = one sentence of evidence.
Do NOT touch the viewer except adding findings to the node card and a "Findings" list if trivial.

## A. Coordinator redefined (replaces the current rule)
Money moves up: seeds -> consolidators -> coordinator. New rule, checked first:
  coordinator = not seed AND (receives from >= 2 consolidators OR receives from >= 2 different clusters with in_deg >= 3)
  Keep betweenness only as a tie-breaker in role_score (not as the rule).
  Evidence: "Signs of coordination: receives from 2 consolidators (…1234, …5678), 3.1M KZT in."
  Roles are computed in two passes (consolidators first, then coordinators). Print new role counts.

## B. Flag "likely_legit_payouts" (payroll / business pattern) -> lowers priority, does not change role
  fires if ALL: out_deg >= 10 AND share of outgoing tx on the 2 busiest dates >= 0.5 (batch payouts)
  AND coefficient of variation of outgoing amounts <= 0.5 (similar amounts) AND taint_share < 0.2.
  Effect: priority x0.5. Evidence suffix: "Pattern resembles regular payouts (salary/business) — verify before escalating."

## C. Flag "seed_hub": seed with in_deg >= 5 or out_deg >= 20.
  Evidence suffix: "Known seed acting as a hub — case may reach above street level." No priority change.

## D. Findings (boolean columns in metrics.csv + short text list column `findings`)
  common_counterparty: seed_payers_direct >= 2
  synchronous_inflow: >= 3 distinct payers on the same day
  fast_pass: fast_pass_share >= 0.8 and out_kzt >= 100,000
  scatter_gather: node C reached from the same source A through >= 2 distinct intermediaries within 2-3 hops
  Priority bonus: +0.05 per fired finding (cap +0.15) before normalisation. Mention fired findings in `why` of top_nodes.

## E. Cut-off continuation estimate (innovation for the hop-4 trap)
  Learn on depth 1-3 nodes (outgoing visible): P(out_deg > 0) by bins of in_deg (1, 2, 3-4, 5+) x in_kzt quartile.
  Apply to the 444 truncated nodes -> column p_continues. Evidence for them:
  "Outgoing not observed (cut-off at hop 4); similar visible nodes forward money in 78% of cases — extend the export from this account."
  out/extension_requests.csv: truncated nodes with p_continues >= 0.5 sorted by taint_kzt (the "next request" for the analyst).

## F. Blocking impact (resilience, value for the analyst)
  Greedy: repeat 10 times — pick the non-seed node whose removal cuts the most taint reaching other nodes
  (recompute taint without it), remove it. out/blocking_plan.csv: step, gid, role, cut_share_cumulative.
  README line: "Blocking these N accounts would cut X% of case money flow in the observed graph."
  If this takes > 60 s, limit candidates to the top 100 by priority.

## Tests
flags are booleans; coordinator rule: every coordinator has >=2 consolidator payers or >=2 source clusters;
extension_requests only contains truncated nodes; blocking_plan cut_share is non-decreasing; runtime still < 5 min.

## Done when
make pipeline prints counts of each flag and the blocking summary; pytest green; README role table updated;
docs/STATE.md updated; commit "H4: findings, coordinator rule, cut-off estimate, blocking plan".

## G. Hierarchy skeleton: trace bottom-up and top-down, keep the intersection
Idea: money is traced from both ends; the organisation is where the two traces meet.
  Bottom-up: from all seeds forward along edges (<= 4 hops) — the nodes reached by case money (taint_kzt > 0).
  Top-down: from the "top candidates" (coordinators + consolidators with taint_kzt in the top 25%) backward along edges (<= 4 hops).
  Skeleton = nodes and edges that lie on both traces, keeping only edges that carry >= 1% of the target's inflow
  (drops small everyday payments like shop purchases).
Outputs: metrics.csv column `in_skeleton` (bool) and `hierarchy_level` (0 = seed, 1 = first collector above seeds, ... top = max);
out/skeleton_edges.csv (src, dst, sum_kzt). graph.json nodes get `skeleton` and `level`.
Viewer (only if trivial): a toggle "Show hierarchy skeleton" that hides non-skeleton nodes and lays the skeleton out
by hierarchy_level top-to-bottom (seeds at the bottom, coordinators at the top).
README: one paragraph explaining the two-sided trace and why small edges are dropped.

## H. Analyst feedback loop (README only, no code)
Document as development potential: the analyst marks alerts as confirmed / false positive (e.g. "legit business"),
labels accumulate, thresholds and priority weights are re-tuned on them, later a supervised model replaces fixed weights.
