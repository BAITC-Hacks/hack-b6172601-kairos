# Current handoff

Updated: 2026-09-23, 16:42 Asia/Almaty. Specs 01, 03, 03b, assigned 04, 04b
and 05 are implemented. Spec 04 H remains documentation only; no case-aware
LLM assistant is implemented. This task finishes before the 17:30 hard stop.

## Spec 05 delivered

Completed in the requested order, with a commit and push after each section:

| Section | Result | Commit |
|---|---|---|
| C cleanup | Removed unused synthetic seeder, JSON accessor, UI helpers and obsolete tests; make run selects its venv | 8d09b11 |
| A README | Required section order, configured role table, measured examples, caveats, schemas, five-step jury path and matching docs/diagram.md | a44831a |
| B disclosure | H1 scaffold boundary b92291c, case work, AI tools, organiser-only data and installed library licences | b6a74e7 |
| D Docker | Locked install without silent fallback, all eight artifacts required, 300-second local health grace | e3d4eef |
| E clean clone | Remote Docker and fresh Python paths pass without a key or .env | e272dc5 |
| F Fly | Public viewer deployed and verified; 1 GiB VM resolves observed 512 MiB OOM | Final H5 commit |

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
  Builds/install need network; execution was separately verified with network
  disabled, 512 MiB and 1 CPU: 54.72s, 421,220 KiB peak RSS. This container limit
  did not include Fly VM overhead, so it was insufficient evidence for Fly sizing.
- D also verified missing official input refusal, image .env/out exclusions and
  regeneration of all exports after deleting only skeleton_edges.csv (42.77s).
  HTTP smoke passed before and after regeneration.

## F: public deployment - PASS

- `fly deploy -a kairos-astana` succeeded after E. No fly launch was run.
- First 512 MiB attempt OOM-killed the computation near 399 MiB anonymous RSS.
  Retried with 1 GiB / 1 shared CPU; Fly pipeline completed in 47.59s. Fly caps
  HTTP startup grace at 60s; both config copies use that supported value.
- Verified https://kairos-astana.fly.dev: health ok=true, production,
  llm_configured=false; graph 2248 nodes / 3119 edges with exact string IDs;
  public CSV downloads 2248 / 88 / 30 rows; full HTTP smoke passes.
- Browser loads the directed viewer; suffix 284100 returns five matches with
  the correct top-1 account first, showing measured role/priority explanations.
- Image: deployment-01M370YZ10JER0MP62G3ZR8C5P. Machine: 7812345cd19d58, fra.
  Build/deploy/retry/public verification completed within the 15-minute budget.
- Live URL added to README only after the public checks passed. Final pytest:
  65 pass; language, diff and matching Fly-config checks pass.

## Current analysis and limits

- 2,248 nodes, 3,119 edges, 4,840 transactions, 88 communities. Roles:
  coordinator 29; consolidator 38; distributor 42; transit 67; terminal 264;
  peripheral 1,808. All 19 isolates remain. 35 weak components = 16 with edges
  plus 19 isolates; overview fits the largest, with 1,877 nodes.
- Findings: common counterparty 24; synchronous inflow 38; fast pass 89;
  scatter/gather 25; possible regular payouts 2; seed hubs 9.
- Continuation covers 444 cut-off accounts, with 10 extension requests.
  Skeleton: 174 accounts, exactly 446 retained directed edges. Rows show measured
  seed-hop distances, not organizational authority. Ego defaults to one hop.
- Blocking 10 accounts cuts 14.3094% of modeled repeated-hop exposure, not unique
  currency. No real blocking, external enrichment or enforcement is implemented.
- Raw data, analysis thresholds and rankings are unchanged by spec 05. Missing
  flows remain unknown; there are no ground-truth labels. Dense layout does not
  support a million-node graph; README describes that as future architecture.
- GitHub-rendered README HTML was retrieved via the authenticated API and checked
  visually: headings, ordered scenario and six tables render. The browser is
  signed out of the private repository, so live GitHub Mermaid rendering remains
  unverified; both diagram sources match and GitHub recognizes the Mermaid block.

## Next session

Ready for handoff. No remaining implementation in spec 05. Keep the verified
public instance and clean local startup working; do not start another spec
without user direction. The temporary clean clone remains in /tmp/clean-check;
its Docker/Python verification services have been stopped.
