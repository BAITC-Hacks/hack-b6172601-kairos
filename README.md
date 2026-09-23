# Kairos

**Live deployment:** https://kairos-astana.fly.dev — the repository also runs
locally; this deployment does not replace that.

<!--
  README CHECKLIST - the rubric awards 20 points for this file alone.
  It replaces a presentation. A reviewer, and an automated judge, must be able
  to answer from this file: what was built, how it works, how to run it, how to
  verify it, and what is missing. Replace every TODO before the deadline.
-->

**Track:** Finance (track 02)
**Case:** TODO — case name and identifier
**Team:** Kairos

## 2. Summary


TODO — one paragraph, written last: what problem this solves, for whom, and what
the software actually does. No marketing.

<!--
  Section numbers follow the outline the organisers published for the README:
  name, summary, what is implemented, how it works, technologies, architecture,
  installation and running, how to check, data and integrations, limitations,
  link to the deployed version. Keep them, so a reviewer can match section by
  section. Describe only what the repository can back up.
-->

## 3. What is implemented


The main scenario runs end to end: TODO — describe the path from input to
result in two or three sentences.

- TODO — capability 1
- TODO — capability 2
- TODO — capability 3

## Case requirements


<!-- Fill one row per mandatory requirement of the case, as the case words it.
     This table is the fastest way for a reviewer to award the first 20 points. -->

| # | Requirement from the case | Status | Where it is implemented | How to verify |
|---|---|---|---|---|
| 1 | TODO | Done | `app/tools/...` | `curl ...` |
| 2 | TODO | Done | `app/agent/core.py` | UI: ask "..." |
| 3 | TODO | Partial | — | see Known limitations |

## 4. How the solution works


TODO — a short architecture description. Keep the diagram in text.

## 5. Technologies


| Layer | Choice | Why |
|---|---|---|
| Backend | Python 3.11, FastAPI, Uvicorn | Fast to build, one process |
| Agent | OpenAI chat completions with function calling | Native tool use, no framework layer |
| Frontend | Static HTML, CSS and JS, no build step | Nothing to compile, nothing to break |
| Packaging | Docker, docker compose | One command on a clean machine |
| Dependencies | ranges in `requirements.txt`, exact versions in `requirements.lock.txt` | The image installs the lock when it is present |
| Tests | pytest | Fast, no API key required |

## 6. Architecture


```
Browser (static/index.html)
    |  POST /api/ask
    v
FastAPI (app/api/routes.py)
    |
    v
Agent loop (app/agent/core.py)
    |-- OpenAI chat completions with tool schemas (app/agent/llm.py)
    |-- Tool calls against the dataset (app/tools/, app/data/store.py)
    `-- Execution trace returned with the answer (app/agent/trace.py)
```

Every answer is accompanied by an execution trace listing each model call and
each tool call with its arguments and result. Open the "Execution trace" panel
in the UI, or read `trace` in the JSON response. Traces are also written to
`.traces/<run_id>.json`.

## If you are reviewing this and have no API key


The agent needs a model provider. In order of least effort:

1. **Use the deployed instance** at https://kairos-astana.fly.dev — nothing to
   install, nothing to configure, and it is rate limited.
   <!-- TODO on the day: remove the next sentence once the key is set. -->
   Until the competition key is issued it runs without one, so `/api/health`
   answers and `/api/ask` returns 503.
2. **Use your own key**, which takes about thirty seconds:

   ```bash
   bash scripts/setup_key.sh     # asks for provider and key, writes .env
   docker compose up --build
   ```

   The key is never printed and never committed. Any OpenAI-compatible endpoint
   works, including NVIDIA's — see Model provider below.
3. **Read the recorded runs** in [docs/SAMPLE_RUN.md](docs/SAMPLE_RUN.md):
   transcripts of real runs with their full execution traces, so you can see what
   the system produces and verify that the tools really executed.
   <!-- TODO on the day: fill SAMPLE_RUN.md and delete this note. -->
   That file is still a template; it is filled in once the main scenario works.

Without a key the service still starts and serves `/api/health`, and the UI says
so plainly. `/api/ask` returns 503. There is no offline demo mode and no canned
answers: an answer you see is an answer the model and the tools actually
produced.

## 7. Installation and running


### Requirements

- **Docker with Compose v2** — nothing else. No Python on the host.
- Or **Python 3.11+** if you prefer to run it directly.
- An API key for the model provider. Without one the service still starts and
  serves `/api/health`; `/api/ask` returns 503.

### Run with Docker (recommended)

```bash
docker compose up --build
```

That is the whole command. The container generates the sample dataset if `data/`
is empty, and starts without a key.

To use a model, put the key in `.env` first:

```bash
cp .env.example .env     # then edit it: set LLM_API_KEY
docker compose up --build
```

`export LLM_API_KEY=...` before the command works too.

Open http://localhost:8000

### Run without Docker

```bash
cp .env.example .env
# Edit .env and set LLM_API_KEY. Without it the service still starts and
# reports llm_configured: false, but /api/ask returns 503.
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.lock.txt || pip install -r requirements.txt
python3 scripts/seed_data.py
uvicorn app.main:app --port 8000
```

Only this path needs Python on the host. The Docker path does not: the container
seeds its own dataset when `data/` is empty. In either case, if the dataset is
already committed there is nothing to seed — `seed_data.py` keeps existing files
unless given `--force`.

### Environment variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `LLM_API_KEY` | yes | — | Model access. The service starts without it and reports `llm_configured: false` on `/api/health`. |
| `LLM_PROVIDER` | no | `openai` | `openai`, `nvidia` or `custom` |
| `LLM_MODEL` | no | provider default | Model identifier |
| `LLM_BASE_URL` | no | provider default | Only needed with `LLM_PROVIDER=custom` |
| `AGENT_MAX_STEPS` | no | `8` | Maximum tool-calling iterations per request |
| `AGENT_TIMEOUT_SECONDS` | no | `60` | Hard time budget per request |
| `RATE_LIMIT_PER_MINUTE` | no | `0` | Requests per minute per IP; `0` disables. Set on public deployments. |
| `TRUST_PROXY_HEADERS` | no | `false` | Honour `X-Forwarded-For` for rate limiting. Enable only behind a platform proxy. The last entry is used, because an edge appends to whatever the client sent. |
| `CLIENT_IP_HEADER` | no | — | Header the platform's own edge sets and a client cannot forge, e.g. `fly-client-ip`. Preferred over `X-Forwarded-For` wherever it exists. |
| `LOG_LEVEL` | no | `INFO` | Log verbosity |

### Model provider

Both providers issued at the hackathon speak the OpenAI chat-completions API, so
switching is configuration only:

Set these two lines in `.env` (they are settings, not shell commands):

```ini
# OpenAI
LLM_PROVIDER=openai
LLM_MODEL=gpt-4.1-mini

# NVIDIA
LLM_PROVIDER=nvidia
LLM_MODEL=meta/llama-3.3-70b-instruct
```

`GET /api/health` reports the provider and model actually in use.

## 8. How to check the solution


```bash
# 1. Service is up and tools are registered
curl -s http://localhost:8000/api/health | python3 -m json.tool

# 2. The main scenario, end to end
curl -s -X POST http://localhost:8000/api/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"TODO - the question that demonstrates the case"}' \
  | python3 -m json.tool

# 3. Invalid input is handled, not crashed
curl -s -i -X POST http://localhost:8000/api/ask \
  -H 'Content-Type: application/json' -d '{"question":""}'   # expects 422

# 4. Automated checks
bash scripts/smoke_test.sh
pytest -q
```

Expected result of step 2: TODO — describe what a correct answer looks like.

## API


| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Liveness, configuration and registered tool names |
| `GET` | `/api/tools` | JSON schemas of all agent tools |
| `POST` | `/api/ask` | Run the agent. Body: `{"question": str, "context": object?}` |

A successful `/api/ask` returns `{"ok": true, "answer": str, "data": object|null,
"trace": object}`. `data` is the structured output of the last successful tool
call, which the UI renders as a table or a chart; it is `null` when the run used
no tools.

Errors from these endpoints are JSON: `{"ok": false, "error": {"code": ..., "message": ...}}`.

Two cases use the framework's own error shape rather than this envelope, because
they fail before the application sees the request: an unknown route returns
`{"detail": "Not Found"}` (404), and a body that is not valid UTF-8 returns a
400. Neither leaks a traceback.

## 9. Data and integrations


TODO — state where the data comes from. If the organisers provided a dataset,
name the file and where it is placed. If the data is synthetic, say so:

Synthetic data is generated by `scripts/seed_data.py` into `data/`. It contains
no real personal or financial information.

## Reliability and safety


- Global exception handlers: no stack trace ever reaches the client.
- Request validation returns `422` with the offending fields.
- Per-request timeout and a maximum step count, so a runaway loop cannot hang.
- Retries with exponential backoff on transient model-provider failures.
- Tool failures are captured into the trace and returned to the model instead of
  aborting the run.
- The system prompt forbids inventing figures the tools did not return.
- No secrets in the repository; `.env` is git-ignored and excluded from the
  Docker build context by `.dockerignore`.
- Synchronous tools run off the event loop, so one slow tool cannot stall the
  service or defeat the request timeout.
- Every run writes an execution trace, including runs that fail.

## 10. Limitations


Stating these honestly is worth more than hiding them.

- TODO — what is not implemented and why
- TODO — what would break at scale
- TODO — what was simplified because of the five-hour limit

## 11. Deployed version


A public instance is available at: TODO — URL, or remove this section.

The repository runs locally without it; see Setup and run above. Deployment
configuration for Render, Fly.io and Railway is in [deploy/](deploy/), with
instructions in [deploy/DEPLOY.md](deploy/DEPLOY.md).

## Disclosure


See [DISCLOSURE.md](DISCLOSURE.md) for pre-existing code, dependencies, models,
datasets and AI tools used, as required by the hackathon rules.
