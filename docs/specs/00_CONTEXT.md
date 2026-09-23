# Context for every spec (read this first, then only the spec you are given)

Case: "Money Graph" (HackAlem AI, finance track). Full brief: docs/CASE.md.
We build an AML analysis tool: from 81 known "seed" customers (bottom of a drug-money chain) we follow their
OUTGOING transfers 4 hops deep and find where the money converges. Output answers the analyst's question:
"which of these 2,248 customers should I look at first, and why".

Money flows UP the criminal hierarchy: seeds (couriers) -> consolidators -> transit -> organisers / final recipients.
All conclusions are hypotheses ("signs of consolidation"), never statements of guilt.

## Hard rules
- Git: after every finished spec or finished section, run tests, update docs/STATE.md, `git commit` AND `git push`.
  Never leave work unpushed at :50 of any hour (hourly checkpoints are judged on the remote repo). Never force-push.
- Everything in the repo is English (code, comments, commits, UI, docs).
- No hardcoded gids, no LLM in role assignment: roles come from explicit rules with thresholds (explainability is scored).
- Deterministic: fixed random seeds, same input -> same output.
- Pipeline must run offline, locally, in < 5 minutes (target < 30 s). Python + pandas + pyarrow + networkx + numpy only.
- Do not break the existing FastAPI app (app/), Dockerfile, scripts/. Remove app/tools/finance.py and data/accounts.json,
  data/transactions.json (old scaffold examples) when the new pipeline lands, and fix anything that imported them.

## Data (data/raw/*.parquet, committed to the repo)
edges.parquet (3,119): src, dst, sum_kzt, n_tx, depth(1-4) — aggregated payer->recipient pairs, July 2026
nodes.parquet (2,248): gid, depth (0 = seed, 1..4 = first hop seen), is_seed
transactions.parquet (4,840): src, dst, date, sum_kzt — individual transfers, all >= 5,000 KZT
gid values are ~1e17 integers: always keep them int64, and write them to CSV/JSON as strings in the UI (JS loses precision).

## Facts measured on the real data (use them to sanity-check your output)
- in_deg (non-seed): 1746 nodes have 1 payer; >=5 payers: 51 nodes (incl. seeds); >=8: 17; max 24 (a seed).
- out_deg: >=10: 64 nodes; >=30: 18; >=60: 8; max 116.
- pass-through 0.8-1.2 (non-seed): 70 nodes (brief says 72).
- depth<=3 with zero outgoing and some inflow: 1,091 nodes (outgoing WAS traced -> real stop, but most are one-off small recipients).
- depth=4 with zero outgoing: 444 nodes = traversal cut-off, NOT terminals. No depth-4 node has outgoing edges.
- Plain reachability "how many seeds can reach me" is useless: seeds are interconnected, 1,124 nodes are reachable from 7 seeds.
  Use amount-weighted taint and 2-hop seed sources instead (spec 01).
- 24 nodes receive directly from >=2 seeds. 38 nodes receive from >=3 distinct payers on the same day (max 7).
- 193 of 671 senders forward >=80% of their outflow within 2 days after an incoming transfer.
- Some seeds are hubs themselves (a seed receives from 24 payers and sends to 62) — seeds are not only couriers.
- Some nodes send far more than they received inside the graph (e.g. receives 0.98M, sends 23M to 99 recipients):
  external money we cannot see. Never interpret such ratios as laundering on their own.
- Amounts: median 30,000; 31% of transfers are multiples of 10,000 -> "round amount" alone is NOT a signal; use repeats per node.
- Starter code from the organisers: case-data/starter/starter.py (outside the repo) — same features, you may reuse ideas.
