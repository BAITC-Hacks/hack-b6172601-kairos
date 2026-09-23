# AGENTS.md

Operating rules for AI coding agents (OpenAI Codex, Claude Code) working in this
repository. Read this file before making any change.

## Start here

Before changing anything, read in this order:

1. `docs/SPEC.md` — what the system must do, its contracts and its invariants
2. `docs/DECISIONS.md` — why it is shaped this way, and what would justify changing it
3. `docs/STATE.md` — what is done, what is verified, what is open
   (`docs/CONSTRAINTS.md` summarises the competition rules that shape all of
   this; read it when a decision turns on what the rules allow)
4. this file — how to work in this repository

These four files are written to be sufficient on their own: an agent with no
conversation history should be able to continue the work from them. When you
finish a piece of work, update `docs/STATE.md` in the same change.

## Context

This is a hackathon project built under a hard five-hour limit by a single
developer. Judges score the repository, not a live demo. Optimise for a working
scenario, a readable README and a clean first run — in that order.

## Non-negotiable rules

1. **English only.** Every identifier, comment, docstring, log message, UI
   string, commit message and branch name is in English. No Cyrillic anywhere in
   the repository. `scripts/check_language.sh` enforces this.
2. **No fake functionality.** Never satisfy a requirement with a hardcoded
   response, a stubbed return value or a pre-recorded answer presented as a real
   computation. If something cannot be implemented in the time available, leave
   it out and say so in the README under Known limitations.
3. **Every feature must run.** Do not add a code path that has never been
   executed. After each change, run `pytest -q` and, for HTTP changes,
   `bash scripts/smoke_test.sh`.
4. **Keep the clean run working.** On a machine that has Docker and nothing
   else - no Python, no `.env` - `docker compose up --build` must start the
   service. The container seeds its own sample data and runs without a key. Do
   not add a step that requires host Python to that path. Any new dependency
   goes into `requirements.txt`; any new setting goes into `.env.example` with a
   sane default, into the README environment table, and into the `environment:`
   block of `docker-compose.yml`. Anything secret goes into `.dockerignore`.
5. **Update the README as you go.** When a case requirement becomes satisfied,
   add the row to the requirement table in the README in the same change. Never
   leave README writing to the end.
6. **Small commits, English messages, present tense.** Format:
   `H<hour>: <what now works>`. Example: `H2: add transaction search tool`.

## Architecture

```
app/
  main.py            FastAPI app, middleware, static mount
  api/routes.py      HTTP endpoints (health, tools, ask)
  agent/
    core.py          the agent loop: plan -> tools -> answer
    registry.py      tool registration (@tool decorator)
    llm.py           OpenAI client with retries
    trace.py         per-run execution trace
  core/
    config.py        settings and provider presets (openai / nvidia / custom)
    errors.py        error types and global handlers
    logging.py       structured JSON logging
    ratelimit.py     per-IP limiter for the public deployment
  data/store.py      dataset access
  tools/finance.py   example tools - REPLACE with the real case tools
static/
  index.html         the page; renderResult() is the one function to adapt
  ui.js              renderers: table, kpis, barChart, keyValue, states, autoRender
  styles.css         colour roles in :root, light and dark
deploy/              Render, Fly.io and Railway configuration + DEPLOY.md
scripts/             seeding, smoke test, language guard, hourly commit
tests/               fast tests that need no API key
```

## How to show a result

`renderResult(data)` in `static/index.html` is the only place the UI knows about
the case. Build the view from the helpers in `ui.js` instead of writing markup:

```js
mount(output, UI.answer(data.answer));
append(output, UI.kpis([{label: "Total", value: 1200, format: "money"}]));
append(output, UI.barChart({data: rows, title: "Spending by category"}));
append(output, UI.table(rows, {title: "Transactions"}));
append(output, UI.autoRender(unknownPayload));   // best effort, first hour only
```

Do not add a CSS framework or a bundler. Colour roles live in `:root` in
`styles.css`; use those variables rather than raw hex.

## How to add a tool

Add a function in `app/tools/` decorated with `@tool(name, description,
parameters)`. The JSON schema in `parameters` is what the model sees, so write
the description for a reader who knows nothing about the dataset. Return a plain
dict. On bad input return `{"error": "..."}` instead of raising — the loop
records it in the trace and lets the model recover.

## What not to do

- Do not introduce a frontend build step. The UI is one HTML file on purpose.
- Do not add a database, a queue or a cache unless the case requires it.
- Do not add a framework layer (LangChain, LlamaIndex and similar). The loop in
  `agent/core.py` is 100 lines and a judge can verify it by reading.
- Do not commit `.env`, API keys or real personal data.
- Do not make a tool block the event loop with synchronous network I/O without
  giving it its own timeout. For a tool that calls the network, use
  `httpx.AsyncClient` with a timeout rather than `requests`: synchronous tools
  run in a bounded worker pool, and enough slow ones will queue each other.
- Never answer with a pre-recorded or invented result while presenting it as a
  live one. If there is no API key, the service must say so, not pretend.
- Do not refactor working code for style while the clock is running.

## Definition of done for any change

- [ ] `pytest -q` passes
- [ ] `bash scripts/smoke_test.sh` passes against a running service
- [ ] `bash scripts/check_language.sh` passes
- [ ] README requirement table updated
- [ ] committed with an English `H<hour>:` message

## Active case and efficient collaboration

The finance case in docs/SPEC.md and docs/PLAN.md overrides generic scaffold scope
and old scoring assumptions. Read these plus current STATE before implementation.
The user authorizes gpt-6-sol subagents for bounded independent implementation.
Use compact fresh briefings with goal, owned files, contracts and acceptance checks;
do not forward the entire conversation. Usually use two workers, at most three.
One writer per file. Root owns integration, shared documentation, commits and pushes.
Workers report changed files, checks, limitations and next steps concisely.
Claude is an available reserve reviewer; coordinate through user, avoid duplicate work.
Update SPEC when contracts change, DECISIONS for meaningful tradeoffs and STATE
at each completed block. Keep STATE short and replace stale facts. Use targeted
searches/reads and focused tests; repeat broad checks only after relevant changes.
Before a new session, save verified status and next steps and tell the user it is ready.
