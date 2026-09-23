# Spec 05 — README, solution diagram, disclosure, deploy, clean-clone check. Read 00_CONTEXT.md and docs/STATE.md first.
Start only after spec 04 is committed. This spec is scored directly: README & reproducibility = 25/100, and a project that
cannot be started from the README is disqualified outright (rules 5.4.16, 5.6.5). Every command written in README must be one
you actually ran. Describe only what works; partial things go to "Limitations". English only.

## A. README.md — rewrite into this exact section order
Must cover the organiser's list (5.4.15): description and purpose, architecture, technologies, installation, run,
dependencies, environment parameters, how to verify the main scenario. And the case list: one command, role criteria and
thresholds, outputs, limitations, scaling section, diagram.
1. Title + 3-line summary: what the analyst gets ("which of the 2,248 accounts to review first and why"), hypotheses not guilt.
   Live demo URL (https://kairos-astana.fly.dev) — only if F succeeded.
2. Quick start (one command): `docker compose up --build` -> http://localhost:8000. Then the local Python path:
   `make install && make pipeline && make run`. State: no API key, no account, no GPU, offline; pipeline runtime measured (N s).
3. How to verify the main scenario (jury path, 5 steps with exact commands/clicks):
   run pipeline -> check 3 CSVs (a one-liner that prints row counts: 2248 / clusters / >=20) -> open viewer ->
   search the top-1 gid by its last 6 digits -> ego view shows payers left, recipients right, node card shows evidence.
4. Solution diagram (Mermaid flowchart, GitHub renders it): parquet (edges, nodes, transactions) -> validation ->
   features + taint -> role rules -> clusters (Louvain) -> priority + findings + skeleton -> CSV exports + graph.json ->
   FastAPI -> viewer. Also save the same diagram as docs/diagram.md.
5. Role rules table generated from pipeline/config.py values: role | rule | threshold | example evidence. Order of rules matters — say so.
6. How the data caveats are handled: one row per caveat from the brief (hop-4 cut-off -> peripheral + p_continues + extension
   requests; seed inflow understated -> no pass-through for seeds; only outgoing traced; 5,000 KZT threshold; orphan seeds;
   16 components; no attributes; no ground truth).
7. Priority formula with weights and multipliers; findings list; hierarchy skeleton (two-sided trace) explained in plain words.
8. Outputs: schemas of nodes_roles.csv, clusters.csv, top_nodes.csv (+ extra files: metrics, extension_requests, blocking_plan,
   skeleton_edges, graph.json).
9. Architecture & technologies: folders (pipeline/, app/, static/, tests/, data/raw, out/), Python 3.11, pandas, pyarrow,
   networkx, numpy, FastAPI, vanilla JS canvas, Docker, Fly.io. Environment variables table (PORT, RATE_LIMIT_PER_MINUTE,
   LLM_* only if spec 06 is done — mark optional).
10. Limitations (honest): no ground truth; thresholds tuned on this one dataset; hop-4 estimate is statistical; payouts flag is a
    pattern, not a legality check; fast-pass is time correlation, not matched money.
11. Scaling to ~1M nodes (text only): igraph/graph-tool or Spark GraphFrames, Leiden instead of Louvain, approximate/sampled
    betweenness, taint as sparse matrix iterations, incremental daily recompute, viewer shows skeleton + ego networks only
    (never all nodes), precomputed layouts/tiles.
12. Development potential: analyst feedback loop (confirmed / false positive) -> re-tuned thresholds -> supervised model;
    AI assistant over graph tools; multi-bank data.
13. Tests: `pytest -q` (what they check). Provenance: pre-built scaffold imported in commit H1, see DISCLOSURE.md.
Keep it scannable: tables over prose, <= ~350 lines.

## B. DISCLOSURE.md
Update: what was prepared before the event (generic FastAPI/Docker/deploy scaffold, commit H1) vs built during the event
(everything case-specific: pipeline, roles, taint, findings, viewer). AI tools used (Codex, Claude). Data: organiser dataset,
anonymised, hackathon-only use. Open-source libraries and licences. No external data.

## C. Cleanup
Remove leftovers of the old finance scaffold (example tools, unused data, UI bits) that are not used; make sure nothing in
README mentions them. Run scripts/check_language.sh (no Cyrillic in repo).

## D. Docker
`docker compose up --build` from a clean state must: install deps, run the pipeline if out/ is missing, serve the viewer on 8000.
Health: GET /api/health returns ok.

## E. Clean-clone check (the disqualification gate)
git clone the remote repo into /tmp/clean-check, then there: `docker compose up --build -d`, wait, curl /api/health and
/api/graph, check the 3 CSVs exist; then `docker compose down`. Also the Python path in a fresh venv. Paste results into docs/STATE.md.

## F. Deploy (only after E passes)
`fly deploy -a kairos-astana` from the repo root (NEVER `fly launch`). Verify https://kairos-astana.fly.dev/api/health and that the
viewer loads. The core needs no LLM key, so rule 5.6.6 (verification without participants' accounts) is met by the public URL.
If deploy fails, do not spend more than 15 minutes — remove the URL from README and note it in STATE.md.

## Done when
README rendered on GitHub looks right, E passes, F done or documented, commit "H5: README, diagram, disclosure, deploy" and git push.
