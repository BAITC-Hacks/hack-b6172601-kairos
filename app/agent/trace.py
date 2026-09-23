"""Run trace.

Every agent run records the steps it took. The trace is returned with the
response and written to .traces/ so a reviewer can see that the tools really
ran instead of taking the answer on trust.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any

TRACE_DIR = os.getenv("TRACE_DIR", ".traces")


@dataclass
class TraceStep:
    index: int
    kind: str  # "llm" | "tool" | "final" | "error"
    name: str
    input: Any = None
    output: Any = None
    duration_ms: int = 0


@dataclass
class Trace:
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    started_at: float = field(default_factory=time.time)
    steps: list[TraceStep] = field(default_factory=list)

    def add(self, kind: str, name: str, input: Any = None, output: Any = None, duration_ms: int = 0) -> None:
        self.steps.append(
            TraceStep(
                index=len(self.steps),
                kind=kind,
                name=name,
                input=_truncate(input),
                output=_truncate(output),
                duration_ms=duration_ms,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "duration_ms": int((time.time() - self.started_at) * 1000),
            "steps": [asdict(s) for s in self.steps],
        }

    def persist(self) -> str | None:
        try:
            os.makedirs(TRACE_DIR, exist_ok=True)
            path = os.path.join(TRACE_DIR, f"{self.run_id}.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(self.to_dict(), fh, ensure_ascii=False, indent=2)
            return path
        except OSError:
            return None


def _truncate(value: Any, limit: int = 2000) -> Any:
    if value is None:
        return None
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    if len(text) > limit:
        return text[:limit] + f"... [truncated {len(text) - limit} chars]"
    return value
