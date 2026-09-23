# Current handoff

Updated: 2026-09-23, 17:27 Asia/Almaty (UTC+05). Specs 01, 03, 03b,
assigned 04, 04b, 05 and 06 are implemented. The separately authorized
experimental analyst assistant is integrated. Current documentation/verification hard stop: 17:45.

## Completed spec 06 and integration

| Work | Commit | Result |
|---|---|---|
| 0 | 77703e1 | Hierarchy legend/filter order and money-flow hint; spec 06 included |
| 1 + 1b | 933a2e3 | Collision-safe inspection, priority picking, skeleton sub-rows, directional ego depths 1–4 |
| Assistant | c9902d1 | Five read-only graph tools and experimental assistant page; exact requested H5 message |
| 2 | 3033a62 | Drag nodes in all layouts; edges follow; background pans; Overview resets |
| 3 | 75514e8 | Shared-source twins, direct-match links, priority bonus and twin_groups.csv |

Each completed block was committed and pushed, with pytest passing before each
push. Root alone edited spec 06 and committed/pushed; the cheaper subagent only
verified. Claude authored the assistant files; the user authorized their separate
integration. No unfinished assistant files remain.

## Public assistant enabled

The owner configured a spend-capped LLM_API_KEY and a limit of 5 assistant
requests per minute per client IP; the running Fly machine confirms the limit is 5.
On 2026-09-23, public health reports
llm_configured=true (OpenAI, gpt-4.1-mini). One browser question, "Why is
...284100 ranked first?", returned a substantive answer and a get_account trace
for 100000003115284100. No additional model questions were sent. README now
links the public assistant and describes its limits and experimental status.
This is a smoke check, not a model evaluation. All 76 pytest tests, the public
HTTP smoke checks and the language guard pass.

## Verification

- All 76 pytest tests pass, including two official-data pipeline regenerations,
  deterministic CSVs, twin thresholds/transitivity/IDs/bonus and viewer APIs.
- Both Node checks pass: largest-component fitting plus official/synthetic
  collision, hit priority, ego depths/caps/cycles, dragging and reset contracts.
- Browser checks pass for ego depth selection, node dragging with following edges,
  skeleton dragging and twin-account click-through. Local HTTP smoke and language
  guard pass. Exported circles have >=2 units clearance at zoom 1; the viewer
  retains >=8 screen pixels between circles at inspection fit and further zoom.
- Latest local pipeline: 47.84s. Final remote clean clone `/tmp/kairos-extras-final`
  at 75514e8: Docker build/start passed without .env, key or host Python;
  pipeline 66.02s. Smoke, language, twin CSV/filter/card, assistant HTML and honest
  no-key 503 checks pass. Initial/final clone status clean; its Compose stack is down.
- Fly deployed 933a2e3 after item 1b, then 75514e8 after all extras/assistant.
  Public smoke, exact JS/HTML hashes, twin CSV/filter/card, all-circle spacing
  and the then-unconfigured assistant's honest no-key checks passed. Browser four-hop ego and twin
  navigation passed; the earlier assistant page visibly reported the missing key.
  The later successful configured-model check is recorded above.
  Final image: deployment-01M372TSBYS6BBA3E7JCTSJY91; pipeline 150.62s.
  Existing app kairos-astana, machine 7812345cd19d58, fra, shared 1 CPU / 1 GiB.
  Keep 1 GiB: the earlier 512 MiB Fly machine OOMed. No fly launch was used.
- README describes nine outputs (eight CSVs plus graph.json), actual startup,
  measured limitations, hierarchy order, inspection controls, twins and the
  experimental assistant. Diagram sources match. GitHub Mermaid rendering itself
  was not verified in the signed-out browser; authenticated rendered README HTML
  was previously checked. DISCLOSURE records scaffold and assistant provenance.

## Verified data and boundaries

- 2,248 nodes, 3,119 edges, 4,840 transactions, 88 communities, 81 seeds.
  Roles: coordinator 29; consolidator 38; transit 67; distributor 42;
  terminal 264; peripheral 1,808. Role precedence remains coordinator,
  consolidator, distributor, transit, terminal, peripheral.
- 19 isolates; 35 weak components (16 nontrivial); largest component 1,877.
  Raw Parquet data remains unchanged.
- Findings: common counterparty 24; synchronous inflow 38; fast pass 89;
  scatter/gather 25; shared-source twins 37 accounts / 45 pairs / 9 groups
  (sizes 2–19); possible regular payouts 2; seed hubs 9.
- Accounts ending 284100 and 963100 share four payers, Jaccard 0.5. Twin bonus
  moves 818100 to rank 2 and 963100 to rank 3; 284100 remains rank 1.
  Direct twin matches and transitive group membership are explicitly distinct.
- 444 cut-off accounts; 10 extension requests. Skeleton: 174 accounts and exactly
  446 retained directed edges. Blocking 10 accounts cuts 14.3094% of modeled
  repeated-hop exposure; no real enforcement is performed.
- Close zoom guarantees separate circles; far-out overlap is allowed and clicks
  pick highest priority. Ego columns cap at 25 by flow, expand displayed parents
  only, and count omitted nodes. Long columns require pan; labels covering a
  circle are skipped. Overview clears manual positions.
- Missing flows remain unknown; no ground-truth labels or proof of common control.
  The assistant is experimental, needs a model/key, and has no evaluation set.
  Public LLM is now configured as recorded above; the main pipeline/viewer
  still needs no key.
  Minor legacy wording: its no-key error refers to README "Setup"; see
  "Quick start" and "Analyst assistant (experimental)" instead.

## Next session

No spec 06 work remains. Keep the verified public instance and clean startup
working; do not start another spec without user direction. Local verification
servers and temporary Compose services are stopped. Earlier spec 05 clean-clone
Docker/Python verification remains recorded in commits e272dc5 and e3901fe.
