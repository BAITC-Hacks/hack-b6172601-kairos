"""Thin OpenAI client wrapper with retries.

Kept deliberately small: one place to swap the provider, one place to change
retry policy. Codex-generated code should extend this file, not bypass it.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.errors import UpstreamError

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504}


class LLMClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._settings = settings
        self._client = AsyncOpenAI(
            api_key=settings.llm_api_key or "missing",
            base_url=settings.base_url,
        )

    @property
    def model(self) -> str:
        return self._settings.model

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        max_retries: int = 3,
    ):
        if not self._settings.llm_enabled:
            raise UpstreamError("LLM_API_KEY is not configured. See README, section Setup.")

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self._settings.agent_temperature,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if response_format:
            kwargs["response_format"] = response_format

        delay = 1.0
        last_error: Exception | None = None
        for attempt in range(1, max_retries + 1):
            try:
                return await self._client.chat.completions.create(**kwargs)
            except Exception as exc:  # noqa: BLE001 - provider raises many types
                status = getattr(exc, "status_code", None)
                last_error = exc
                if status is not None and status not in _RETRYABLE_STATUS:
                    raise UpstreamError(f"Model provider rejected the request: {exc}") from exc
                logger.warning("llm_retry attempt=%s error=%s", attempt, exc)
                if attempt == max_retries:
                    break
                await asyncio.sleep(delay)
                delay *= 2
        raise UpstreamError(f"Model provider failed after {max_retries} attempts: {last_error}")
