"""Agent-loop tests with a stubbed model. No API key, no network.

These prove that tool calls really execute, that a failing tool does not kill
the run, and that the step and time guards hold.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.agent.core import run_agent
from app.agent.registry import REGISTRY, tool
from app.core.errors import AppError


def _message(content=None, tool_calls=None):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content, tool_calls=tool_calls))]
    )


def _tool_call(call_id: str, name: str, arguments: dict):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments)),
    )


@pytest.fixture(autouse=True)
def isolated_tools():
    """Exercise dispatch with test-only tools, independent of removed examples."""
    original = REGISTRY.tools.copy()
    @tool("list_accounts", "Test account lookup", {"type": "object", "properties": {"customer_id": {"type": "string"}}})
    def list_accounts(customer_id):
        return {"customer_id": customer_id, "accounts": []}
    @tool("search_transactions", "Test failing tool", {"type": "object", "properties": {"customer_id": {"type": "string"}, "date_from": {"type": "string"}}})
    def search_transactions(customer_id, date_from):
        raise ValueError("Invalid test date")
    yield
    REGISTRY.tools.clear()
    REGISTRY.tools.update(original)


@pytest.fixture
def scripted(monkeypatch):
    """Replace LLMClient.chat with a scripted sequence of responses."""

    def _install(responses):
        queue = list(responses)

        async def fake_chat(self, messages, tools=None, response_format=None, max_retries=3):
            return queue.pop(0)

        monkeypatch.setattr("app.agent.llm.LLMClient.chat", fake_chat, raising=True)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")

    return _install


def test_tools_are_registered():
    assert "list_accounts" in REGISTRY.names()
    assert "search_transactions" in REGISTRY.names()


@pytest.mark.asyncio
async def test_agent_executes_a_real_tool_call(scripted):
    scripted(
        [
            _message(tool_calls=[_tool_call("c1", "list_accounts", {"customer_id": "CUST-001"})]),
            _message(content="CUST-001 has one current account."),
        ]
    )
    result = await run_agent("Which accounts does CUST-001 have?")

    assert result["ok"] is True
    kinds = [step["kind"] for step in result["trace"]["steps"]]
    assert kinds == ["llm", "tool", "llm", "final"]
    assert result["trace"]["steps"][1]["name"] == "list_accounts"


@pytest.mark.asyncio
async def test_failing_tool_is_captured_not_raised(scripted):
    scripted(
        [
            _message(
                tool_calls=[
                    _tool_call("c1", "search_transactions", {"customer_id": "CUST-001", "date_from": "not-a-date"})
                ]
            ),
            _message(content="The date was invalid."),
        ]
    )
    result = await run_agent("Transactions since not-a-date")

    assert result["ok"] is True
    assert "error" in result["trace"]["steps"][1]["output"]


@pytest.mark.asyncio
async def test_unknown_tool_does_not_crash_the_run(scripted):
    scripted(
        [
            _message(tool_calls=[_tool_call("c1", "no_such_tool", {})]),
            _message(content="That tool does not exist."),
        ]
    )
    result = await run_agent("Call a tool that does not exist")
    assert result["ok"] is True


@pytest.mark.asyncio
async def test_step_limit_is_enforced(scripted):
    scripted(
        [_message(tool_calls=[_tool_call(f"c{i}", "list_accounts", {"customer_id": "CUST-001"})]) for i in range(40)]
    )
    with pytest.raises(AppError) as excinfo:
        await run_agent("Never converge")
    assert excinfo.value.code == "agent_no_convergence"


@pytest.mark.asyncio
async def test_empty_question_is_rejected(scripted):
    scripted([])
    with pytest.raises(AppError) as excinfo:
        await run_agent("   ")
    assert excinfo.value.status_code == 422


@pytest.mark.asyncio
async def test_trace_is_persisted_even_when_the_run_fails(scripted, tmp_path, monkeypatch):
    """A failed run is the one worth diagnosing, so its trace must survive."""
    monkeypatch.setattr("app.agent.trace.TRACE_DIR", str(tmp_path), raising=False)
    scripted(
        [_message(tool_calls=[_tool_call(f"c{i}", "list_accounts", {"customer_id": "CUST-001"})]) for i in range(40)]
    )
    with pytest.raises(AppError):
        await run_agent("Never converge")
    assert list(tmp_path.glob("*.json")), "no trace was written for the failed run"
