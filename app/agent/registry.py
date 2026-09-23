"""Tool registry.

A tool is a plain Python function plus a JSON schema. Register one with the
@tool decorator and the agent can call it; nothing else needs to change.
"""
from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    fn: Callable[..., Any]

    def to_openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class ToolRegistry:
    tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, tool: Tool) -> None:
        if tool.name in self.tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self.tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self.tools.get(name)

    def schemas(self) -> list[dict[str, Any]]:
        return [t.to_openai_schema() for t in self.tools.values()]

    def names(self) -> list[str]:
        return sorted(self.tools)


REGISTRY = ToolRegistry()


def tool(name: str, description: str, parameters: dict[str, Any]):
    """Decorator that registers a function as an agent tool."""

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        REGISTRY.register(Tool(name=name, description=description, parameters=parameters, fn=fn))
        return fn

    return decorator


async def call_tool(t: Tool, arguments: dict[str, Any]) -> Any:
    """Call a tool.

    Async tools are awaited. Synchronous tools run in a worker thread, so a
    blocking call inside one cannot freeze the event loop and cannot defeat the
    per-request timeout in the agent loop. Note that a thread cannot be killed:
    a tool doing network I/O must still set its own timeout.
    """
    if inspect.iscoroutinefunction(t.fn):
        return await t.fn(**arguments)
    return await asyncio.to_thread(t.fn, **arguments)
