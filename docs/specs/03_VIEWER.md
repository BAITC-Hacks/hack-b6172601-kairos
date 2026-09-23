# Spec 03 — analyst viewer (MUST HAVE 5: map with flow direction, roles, search by gid). Read 00_CONTEXT.md and docs/STATE.md first.

Goal of the demo: the jury names any gid -> within 10 seconds we find it, show its links with direction and amounts,
its role, evidence and priority. Everything must work offline: NO CDN, NO new JS dependencies. Plain HTML/CSS/JS + <canvas>.
Keep the existing FastAPI app; reuse static/ui.js helpers where it helps. Replace the old scaffold UI (question box for the
finance demo) with this viewer; keep the /api/ask endpoint working (spec 06 will reuse it).

## Backend (app/api/, read-only over out/)
GET /api/graph            -> out/graph.json as is
GET /api/node/{gid}       -> {node: nodes_roles row + metrics.csv row, cluster: clusters.csv row,
                              incoming:[{gid, role, sum_kzt, n_tx}], outgoing:[...]} sorted by sum_kzt desc
                              gid accepted as string; 404 JSON error if unknown
GET /api/search?q=...     -> up to 10 gids whose string contains q (so the last 5-6 digits are enough)
GET /api/top              -> top_nodes.csv as JSON
GET /api/clusters         -> clusters.csv as JSON
GET /api/download/{name}  -> the three CSVs (whitelist the names)
If out/ is missing -> 503 JSON {"error": "Run `make pipeline` first"}. Load files once at startup, reload if mtime changes.
gid always serialised as string in JSON.

## Frontend (static/index.html, static/app.js, static/styles.css)
Layout: left sidebar (search box, role legend with counts + checkboxes, colour-by toggle Role/Cluster, Top-30 list),
centre canvas, right panel = node card.
1. Overview map: all nodes at the precomputed x,y from graph.json. Node radius 3 + 9*priority; colour by role
   (consolidator red, coordinator purple, distributor orange, transit amber, terminal teal, peripheral light grey);
   seeds drawn with a black ring; truncated nodes hollow. Edges thin, low alpha, with small arrowheads; edge width ~ log(sum_kzt).
   Pan (drag), zoom (wheel), hover tooltip (gid, role, priority), click selects.
2. Focus mode (on select/search): highlight the node, its predecessors and successors up to 2 hops; fade everything else.
   Draw focus edges opaque with clear arrowheads and the amount label (e.g. "1.2M") on edges adjacent to the selected node.
   Button "Ego view": re-layout only the ego network: payers in a column on the left, the node in the centre,
   recipients on the right (second-hop nodes further out) — money visibly flows left -> right. Esc returns to overview.
3. Node card: gid (copy button), role + role_score, priority + rank if in top list, cluster id + hypothesis, evidence,
   key metrics (in/out payers, in/out KZT, pass-through, taint_kzt, seeds within 2 hops, fast_pass_share, depth, seed flag,
   peripheral_reason), tables of incoming and outgoing links (click a row -> jump to that gid). Wording: hypotheses, not guilt.
4. Top-30 list: rank, short gid (…last 6 digits), role chip, priority; click -> focus. Download links for the 3 CSVs.
5. Search: type full gid or last digits, Enter -> focus the first match; show "not found" politely.
Performance: 2,248 nodes / 3,119 edges on canvas must pan/zoom smoothly (draw with requestAnimationFrame, no per-frame layout).
Header line: "Money Graph — hypotheses for review, not conclusions of guilt."

## Tests
API tests in tests/test_viewer_api.py (TestClient): /api/graph node count 2248, /api/node for a known gid from top_nodes.csv
has incoming/outgoing lists, unknown gid -> 404 JSON, /api/search with last 6 digits finds it, /api/download rejects other names.

## Done when
`make pipeline && make run`, open http://localhost:8000: map renders, search by last 6 digits of the top-1 gid focuses it,
card shows links with amounts, ego view shows direction. pytest -q green. Update docs/STATE.md, commit
"H3: analyst viewer: network map, ego view, node card, search".
