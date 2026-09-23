# Current handoff

Updated: 2026-09-23. Phase: spec 01 pipeline and spec 03 analyst viewer.
Hackathon start: 13:33 Asia/Almaty. Deadline: exactly 18:00. No Fly changes.
Work only in hack-b6172601-kairos; sibling kairos is the scaffold reference.

## Read first

AGENTS.md, docs/SPEC.md, docs/DECISIONS.md, docs/specs/00_CONTEXT.md and only
the assigned implementation spec. Specs 01 and 03 are implemented; other specs
remain out of scope. Review git status before editing.

## Implemented

- Official immutable data: 2,248 nodes, 3,119 directed edges, 4,840 transactions.
  Pipeline includes all nodes/isolates, validates inputs and aggregate sums/counts,
  computes metrics, synchronous haircut taint, first-match roles, weighted Louvain
  clusters, deterministic priorities, four CSVs and graph JSON. No API key needed.
- app/api/viewer.py: read-only graph, node detail, substring search, top priorities,
  clusters and three whitelisted downloads. CSV identifiers stay strings; numeric
  metrics are JSON numbers. Startup cache reloads on file mtime/size changes;
  missing/incomplete artifacts return the prescribed 503 message.
- static/index.html, app.js, styles.css: offline canvas overview, directional
  arrows, pan/zoom, role filters/counts, cluster colours, hover, two-hop focus,
  ego columns, exact-id/suffix search, Top-30, evidence/metrics/neighbor cards and
  CSV downloads. No CDN, dependencies or frontend build. /api/ask retained.
- tests/test_viewer_api.py covers official graph count/string IDs, joined node
  data, sorted links, search, unknown IDs, exports, missing files and mtime reload.
  Legacy page assertion now checks Money Graph/canvas; smoke includes viewer assets.
- README requirement coverage and launch/API instructions updated; SPEC scope
  reflects the viewer. Other implementation specs have not been implemented.

## Verification

- Requested `make pipeline`: passed in 38.71 seconds, 2,248 nodes / 3,119 edges /
  88 clusters. Existing peripheral-count warning remains (1,806 peripheral nodes).
  Regenerated graph matches the committed graph except for its timestamp; no
  generated-data changes are included in this viewer milestone.
- Requested `make run`: running at http://localhost:8000 with the local venv on
  PATH. Sandbox socket restrictions required approved local execution.
- Requested `pytest -q`: final suite passed, all 50 tests. Existing dependency
  deprecation warnings only. Log: /private/tmp/moneygraph-viewer-final-pytest.log.
- `bash scripts/smoke_test.sh`: passed against the running service, including
  /app.js and viewer graph/top/clusters/download routes. Language guard and
  `git diff --check` passed. `node --check static/app.js` passed.
- Browser verified: all graph counts load, top-1 suffix 284100 selects exact gid
  100000003115284100, card shows 8 incoming / 2 outgoing links with amounts,
  ego arrows/labels, pan/zoom, canvas click/hover, neighbor and Top-30 navigation,
  role filters, cluster colour toggle, not-found message, copy gid and Escape.
- Docker was fully verified in spec 01; not rebuilt for this milestone. No new
  dependencies, settings, build steps or changes to container startup.

## Limitations and existing pipeline clarifications

- Dense neighborhoods can overlap; use zoom and neighbor tables. The canvas is
  sized for the supplied graph, not a million-node browser view.
- No case-aware LLM analyst is implemented; retained /api/ask has no case tools.
  No external LLM calls or deployments made in this milestone.
- Roles remain hypotheses, not guilt or calibrated probabilities. Depth-4 cutoffs
  are not terminals. Inflows are incomplete, especially for seeds.
- Aggregate sums use absolute 1e-6 KZT tolerance, zero relative tolerance; counts
  match exactly. This handles official floating-point accumulation differences.
- PageRank uses NumPy iteration; spring coordinates use NetworkX dense NumPy
  fallback to preserve the prescribed dependencies without SciPy. Seed 42,
  unweighted layout, 100 iterations. The private API remains pinned/tested.
- Temporal fast-pass share is correlation after ANY inflow, not matched money.
- Runtime remains above the aspirational 30s target but below the strict 60s
  regression and five-minute case limits. No approximate betweenness used.

## Next session

Await the next assigned spec; do not implement other specs automatically.
Use bounded Sol workers when useful, one writer per file; root owns integration,
shared documentation and commits. Claude remains a user-coordinated reserve
reviewer. No Fly changes unless requested.
