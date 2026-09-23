# Disclosure of pre-existing material

## Before the competition

A generic FastAPI/Docker application scaffold was prepared before the event and
imported in **`b92291c` — H1: import pre-built scaffold (see DISCLOSURE.md)**.
It contained no Money Graph case analysis. The source boundary is visible in the
repository history; the earlier `44ca746` is the repository's initial commit.

| Pre-built material | Current use |
|---|---|
| FastAPI application wiring, health/tools/ask endpoints | Retained infrastructure; viewer API added during the event |
| Generic tool registry, agent loop, API-client wrapper and execution traces | Retained and tested; experimental graph tools added during the event; no model required for the main scenario |
| Configuration, logging, errors and rate limiter | Retained application infrastructure |
| HTML/CSS page and generic rendering helpers | Page/styles replaced for the case viewer; unused UI helpers removed |
| Docker, Compose, Makefile, deployment configuration | Adapted to compute official Parquet artifacts and serve the graph |
| Smoke/language checks, developer helpers and scaffold tests | Retained where applicable; obsolete synthetic-data tests removed |
| Synthetic financial examples, seeder and JSON accessor | Removed; not part of the case runtime or submitted dataset |

This disclosure records pre-prepared technical components under the competition's
third-party/pre-existing-material disclosure requirement. The scaffold was an
infrastructure starting point, not a finished case solution.

## Built during the competitive session

All case-specific computation was implemented after the case was supplied:

- Official Parquet loading and consistency validation; all-node directed graph.
- Flow/centrality/timing features, haircut taint and seed-source measures.
- Ordered explainable role rules, priority weights, communities and hypotheses.
- Convergence/timing findings, payout and seed-hub flags, continuation estimates,
  extension requests, shared-source twins, hierarchy skeleton and simulated blocking plan.
- Required CSV exports, metrics and graph JSON, deterministic verification.
- Read-only graph APIs, canvas viewer, exact-gid/suffix search, ego networks,
  node evidence, role/priority breakdowns, filters, layered ego layouts, node dragging and method display.
- Experimental analyst assistant with five read-only case graph tools, authored
  by Claude and integrated after deterministic tests.
- Case documentation, runnable jury scenario and deployment verification.

The organiser's supplied brief, dataset documentation and starter example informed
the work. The starter is not a vendored runtime dependency; implementation and
case-specific changes are reviewable in the competition commit history.

## AI tools

OpenAI Codex was used for implementation, testing, documentation and coordination.
Claude / Claude Code was also used for the experimental analyst assistant and
for code generation/review recorded in the original scaffold disclosure. During the event Claude (Cowork) also acted as planning assistant: case analysis, exploratory data analysis used to calibrate thresholds, the solution design and the specs in docs/specs/, manual review of the viewer, and small README/test edits. Human direction selected the case, constraints and thresholds; generated
work was checked against executed tests and supplied data.

No model is trained or used by the role assignment, scoring, findings, pipeline
or viewer. The optional experimental analyst page uses the retained OpenAI-compatible
client and new read-only graph tools when a key is configured. No model API key
is needed to reproduce the submitted main scenario.

## Data

The three files in `data/raw/` are the organiser-supplied anonymised hackathon
dataset: July 2026 account nodes, aggregated directed edges and transactions.
They contain 2,248 accounts (81 seeds), 3,119 edges and 4,840 transactions. Use is
for the hackathon task; no broader data licence is asserted here.

Raw inputs are immutable and committed so judges can reproduce the computation.
No external datasets, enrichment, names or invented customer attributes are used.
`out/` contains computed artifacts, not pre-recorded answers substituted for a
live run. Docker excludes those artifacts and recomputes them from raw inputs.

## Open-source dependencies and licences

The table records licence metadata from the installed locked packages. Version
ranges are in `requirements.txt`; exact direct and transitive versions are in
`requirements.lock.txt`. Package distributions retain their own licence texts
and notices; this summary does not replace them.

| Library / component | Purpose | Licence |
|---|---|---|
| pandas | Tabular metrics and CSVs | BSD-3-Clause |
| PyArrow | Parquet I/O | Apache-2.0 |
| NetworkX | Graph algorithms and Louvain communities | BSD-3-Clause |
| NumPy | Numeric computation and layout | BSD-3-Clause; distribution also includes 0BSD, MIT, Zlib and CC0-1.0 components |
| FastAPI | HTTP application | MIT |
| Uvicorn | ASGI server | BSD-3-Clause |
| Pydantic, pydantic-settings | Validation and settings | MIT |
| HTTPX | HTTP client infrastructure/tests | BSD-3-Clause |
| OpenAI Python SDK | Retained generic optional client | Apache-2.0 |
| pytest | Test runner | MIT |
| pytest-asyncio | Async tests | Apache-2.0 |
| CPython 3.11 | Docker runtime | Python Software Foundation licence |

The frontend is project HTML/CSS/vanilla JavaScript Canvas; no third-party graph
bundle or CDN is loaded. Docker uses the official `python:3.11-slim` image, whose
OS/runtime components carry their respective upstream licences. Fly.io is a
hosting service, not an analysis dependency. No external model weights are
bundled with the project.
