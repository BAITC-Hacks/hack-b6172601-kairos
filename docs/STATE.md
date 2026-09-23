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

B disclosure, D Docker completion checks,
E remote clean clone with Docker and a fresh Python venv, F bounded Fly deploy.
Record failures honestly; keep the public URL out of README unless verified.
