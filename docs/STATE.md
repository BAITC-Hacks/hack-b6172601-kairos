# Current handoff

Updated: 2026-09-23. Specs 01, 03, 03b, assigned 04 and 04b are implemented.
Spec 04 H remains documentation only. Spec 05 is in progress in the user-requested
order C -> A -> B -> D -> E -> F. Hard stop: 17:30 Asia/Almaty; commit and push
at each completed section. Deploy is authorized only after the clean-clone gate.

## Spec 05 progress

- C complete, committed/pushed as 8d09b11: removed unused synthetic seeder,
  JSON store, legacy UI helpers and obsolete tests. Make run uses the venv.
  Stale key-required deployment instructions replaced. 65 tests pass; language
  check passes. No case-aware LLM assistant is implemented.
- A complete: README rewritten in the required 13-section order, with diagram mirrored
  in docs/diagram.md, configured role rules, observed examples, complete output
  schemas, caveats, priorities, findings and an executable five-step jury path.
  Full pytest rerun: 65 pass; language and diff guards pass; role table and
  mirrored diagram match runtime configuration and each other.
- Docker quick-start executed: recomputation took 45.91 seconds; all viewer HTTP
  smoke checks passed. Required CSV row counts: 2248 / 88 / 30.
- Exact Python quick start also passes without activation: make install && make
  pipeline && make run; HTTP smoke passes. Rerun under concurrent tests: 50.93s.
- Local pipeline: 45.79 seconds. Browser verified top-1 selection, suffix 284100
  (5 matches, correct top-1 first), measured role/priority evidence and ego view
  with 10 accounts. No URL is advertised until deployment verification passes.

- B complete: replaced disclosure TODOs and synthetic-data claims with the H1 commit
  boundary, case-specific work, AI tools, organiser-only anonymised data and
  direct library licences checked against installed package metadata.
  Full tests: 65 pass; language and diff guards pass.
- GitHub rendered README HTML retrieved through authenticated API and visually
  checked: headings, five-step list and six tables render correctly. The browser
  is signed out of the private repository; GitHub live Mermaid rendering remains
  unverified (both Mermaid sources are identical).

- D complete: startup checks all eight exports, Docker uses the exact lock
  without a silent fallback, and health checks allow the five-minute pipeline
  budget. Full tests: 65 pass; language, diff and deploy-config guards pass.
  Missing official nodes file fails clearly; image contains neither .env nor out/.
  Offline disposable container (network none, 512 MiB, 1 CPU) completes in
  54.72s at 421,220 KiB peak RSS, with expected counts.
  New image is healthy; deleting only skeleton_edges.csv triggers full
  regeneration in 42.77s and restores all eight outputs. HTTP smoke passes
  before and after regeneration.

## E: remote clean-clone gate - PASS

Verified remote commit e3d4eef in /tmp/clean-check, initially clean with no .env
or .venv. Raw Parquet files remain unchanged.

- Docker: `docker compose up --build -d` succeeds. Entrypoint pipeline: 41.83s.
  `/api/health`: ok=true, env=docker, llm_configured=false. `/api/graph`: 2,248
  nodes, 3,119 edges; all node and endpoint IDs are strings. Required CSVs exist
  inside the container with 2248 / 88 / 30 rows. No /app/.env. HTTP smoke and
  language checks pass. `docker compose down` removes container and network.
- Fresh Python 3.14 venv: `make install`, `make pipeline`, `make run` succeed.
  Pipeline: 67.62s under concurrent verification load; pip check reports no
  broken requirements. All 65 pytest tests pass. HTTP smoke passes; health
  reports llm_configured=false. Required CSV counts: 2248 / 88 / 30.
  Verification server stopped after checks.
- Docker uses Python 3.11 and resolves the committed lock without fallback.
  Network access is needed only for builds/install; offline execution was
  separately verified in D. Sandbox-local curl required network escalation.

## Current analysis and viewer

- 2,248 nodes, 3,119 edges, 4,840 transactions, 88 communities. Role counts:
  coordinator 29; consolidator 38; distributor 42; transit 67; terminal 264;
  peripheral 1,808. All original nodes, including 19 isolates, are retained.
- 35 weak components = 16 components with edges + 19 isolates. Overview fits
  the largest (1,877 nodes), while all components remain searchable.
- Findings: common counterparty 24; synchronous inflow 38; fast pass 89;
  scatter/gather 25; possible regular payouts 2; seed hubs 9.
- Continuation covers 444 cut-off accounts; 10 extension requests. Hop-4 nodes
  cannot match terminal rules but can match earlier observed-inflow rules.
- Skeleton has 174 accounts and exactly 446 retained edges. Rows show observed
  seed-hop distances, not organizational authority. Selecting a member preserves
  the layout. Ego defaults to one hop, with optional second hop and amount order.
- Pipeline-generated role/priority explanations appear in graph JSON and metrics
  CSV. APIs serve the artifacts; browser does not recompute analysis.
- Blocking 10 accounts cuts 14.3094% of modeled repeated-hop exposure, not unique
  currency. No actual blocking or other external enforcement is implemented.
- Raw data is immutable. Gids stay exact strings in UI/JSON. Thresholds and role
  rankings unchanged by spec 05. No ground-truth validation; missing flows remain
  unknown. Dense layout is unsuitable for a million-node graph.

## Remaining work

F: bounded Fly deployment is now authorized by the passing clean-clone gate.
Record failures honestly; keep the public URL out of README unless verified.
