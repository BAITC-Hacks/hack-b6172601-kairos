# Recorded runs

<!--
  Fill this in during the competition, after the main scenario works. It is
  evidence for a reviewer who has no API key: real output from real runs, with
  the command that produced it and the trace that proves the tools executed.

  This is NOT a substitute for running the project, and must never be presented
  as one. It is a recording, clearly labelled as such.
-->

These are transcripts of actual runs against this repository, recorded on
TODO-DATE with `LLM_PROVIDER=TODO` and `LLM_MODEL=TODO`.

They exist so that a reviewer without an API key can see what the system
produces. They are recordings, not a demo mode: the service does not replay them,
and without a key `/api/ask` returns 503 rather than any canned answer.

The raw traces of these runs are committed under `traces/`. Each one lists every
model call and every tool call with its arguments and result.

---

## Run 1 — the main scenario

**Command**

```bash
curl -s -X POST http://localhost:8000/api/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"TODO"}'
```

**Response** (abridged: the full body is in `traces/TODO.json`)

```json
TODO
```

**What this demonstrates:** TODO - name the case requirement it satisfies.

---

## Run 2 — TODO

---

## Run 3 — an error path

Showing that invalid input is handled rather than crashing.

```bash
curl -s -i -X POST http://localhost:8000/api/ask \
  -H 'Content-Type: application/json' -d '{"question":""}'
```

```
TODO
```
