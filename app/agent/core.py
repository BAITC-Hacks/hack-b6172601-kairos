"""Agent loop: plan, call tools, answer.

The loop is intentionally explicit rather than framework-driven. A reviewer can
read it top to bottom in two minutes and see that tool calls are real.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from app.agent.llm import LLMClient
from app.agent.registry import REGISTRY, call_tool
from app.agent.trace import Trace
from app.core.config import get_settings
from app.core.errors import AppError

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an assistant for an AML analyst working with the Money Graph: a transaction network built
from 81 known seed customers (bottom of a drug-money chain) by following their outgoing transfers 4 hops deep.
Money flows up: seeds -> consolidators (collectors) -> coordinators (candidate organisers).

Rules:
- Use the provided tools to obtain facts. Never invent numbers, roles or identifiers that a tool did not return.
- Always cite accounts by gid (you may shorten to the last 6 digits, e.g. ...284100) and quote the figures you used.
- Phrase conclusions as hypotheses for review ("signs of consolidation"), never as statements of guilt.
- If the tools cannot answer the question, say so plainly and state what data is missing.
- Typical plan: start with get_account for any account mentioned; use its incoming/outgoing links as inputs to
  who_collects_from or money_paths; call several tools before answering when needed.
- Keep the final answer short and concrete. Reply in the language of the question.
"""


class AgentResult(dict):
    """Plain dict so FastAPI serializes it without extra models."""


async def run_agent(
    question: str,
    system_prompt: str = SYSTEM_PROMPT,
    context: dict[str, Any] | None = None,
) -> AgentResult:
    settings = get_settings()
    if not question or not question.strip():
        raise AppError("Question must not be empty.", status_code=422, code="empty_question")

    trace = Trace()
    client = LLMClient()

    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    if context:
        messages.append({"role": "system", "content": f"Context: {json.dumps(context, default=str)}"})
    messages.append({"role": "user", "content": question.strip()})

    try:
        result = await asyncio.wait_for(
            _loop(client, messages, trace, settings.agent_max_steps),
            timeout=settings.agent_timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        trace.add("error", "timeout", output=f"exceeded {settings.agent_timeout_seconds}s")
        raise AppError(
            f"Agent exceeded the {settings.agent_timeout_seconds}s time budget.",
            status_code=504,
            code="agent_timeout",
        ) from exc
    except AppError as exc:
        # Timeout and max-steps already recorded their own step; anything else
        # (an upstream provider failure, most often) would otherwise persist an
        # empty trace, which is useless exactly when diagnosis matters.
        if not any(step.kind == "error" for step in trace.steps):
            trace.add("error", exc.code, output=exc.message)
        raise
    except Exception as exc:  # noqa: BLE001 - record the failure before it propagates
        trace.add("error", type(exc).__name__, output=str(exc))
        raise
    finally:
        # A failed run is the one worth diagnosing, so the trace is written on
        # every path, not only on success.
        trace.persist()

    answer, tool_outputs = result
    return AgentResult(
        ok=True,
        answer=answer,
        # Structured output of the last successful tool call, so the UI can
        # render a table or a chart next to the text answer. None when the run
        # used no tools. This is the field static/index.html reads.
        data=tool_outputs[-1] if tool_outputs else None,
        trace=trace.to_dict(),
    )


async def _loop(
    client: LLMClient, messages: list[dict[str, Any]], trace: Trace, max_steps: int
) -> tuple[str, list[Any]]:
    """Returns the final answer and the structured output of every tool call
    that succeeded, in order."""
    schemas = REGISTRY.schemas()
    tool_outputs: list[Any] = []

    for step in range(max_steps):
        started = time.time()
        response = await client.chat(messages, tools=schemas or None)
        choice = response.choices[0]
        message = choice.message
        trace.add(
            "llm",
            client.model,
            input={"step": step, "messages": len(messages)},
            output={"content": message.content, "tool_calls": _describe(message.tool_calls)},
            duration_ms=int((time.time() - started) * 1000),
        )

        if not message.tool_calls:
            answer = (message.content or "").strip()
            trace.add("final", "answer", output=answer)
            return answer or "The agent produced no answer.", tool_outputs

        messages.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in message.tool_calls
                ],
            }
        )

        for tool_call in message.tool_calls:
            output = await _execute(tool_call, trace)
            if isinstance(output, dict) and "error" not in output:
                tool_outputs.append(output)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(output, ensure_ascii=False, default=str),
                }
            )

    trace.add("error", "max_steps", output=f"stopped after {max_steps} steps")
    raise AppError(
        f"Agent did not converge within {max_steps} steps.",
        status_code=422,
        code="agent_no_convergence",
    )


async def _execute(tool_call, trace: Trace) -> Any:
    name = tool_call.function.name
    started = time.time()
    tool = REGISTRY.get(name)
    if tool is None:
        trace.add("tool", name, output={"error": "unknown tool"})
        return {"error": f"Unknown tool: {name}"}

    try:
        arguments = json.loads(tool_call.function.arguments or "{}")
    except json.JSONDecodeError:
        trace.add("tool", name, output={"error": "invalid arguments"})
        return {"error": "Tool arguments were not valid JSON."}

    try:
        result = await call_tool(tool, arguments)
        trace.add("tool", name, input=arguments, output=result, duration_ms=int((time.time() - started) * 1000))
        return result
    except Exception as exc:  # noqa: BLE001 - a failing tool must not kill the run
        logger.exception("tool_failed name=%s", name)
        trace.add("tool", name, input=arguments, output={"error": str(exc)})
        return {"error": f"Tool {name} failed: {exc}"}


def _describe(tool_calls) -> list[dict[str, str]]:
    if not tool_calls:
        return []
    return [{"name": tc.function.name, "arguments": tc.function.arguments} for tc in tool_calls]
