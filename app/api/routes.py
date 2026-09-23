"""HTTP API. One agent endpoint, one health endpoint, one tools endpoint."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.agent.core import run_agent
from app.agent.registry import REGISTRY
from app.core.config import get_settings
from app.core.ratelimit import check as rate_limit_check

router = APIRouter()


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    context: dict[str, Any] | None = None


@router.get("/health")
async def health() -> dict[str, Any]:
    settings = get_settings()
    return {
        "ok": True,
        "app": settings.app_name,
        "env": settings.app_env,
        "llm_configured": settings.llm_enabled,
        "provider": settings.llm_provider,
        "model": settings.model,
        "tools": REGISTRY.names(),
    }


@router.get("/tools")
async def tools() -> dict[str, Any]:
    return {"ok": True, "tools": REGISTRY.schemas()}


@router.post("/ask")
async def ask(payload: AskRequest, request: Request) -> dict[str, Any]:
    settings = get_settings()
    rate_limit_check(_client_ip(request), settings.rate_limit_per_minute)
    return await run_agent(question=payload.question, context=payload.context)


def _client_ip(request: Request) -> str:
    """Identify the caller for rate limiting.

    Order of preference:

    1. CLIENT_IP_HEADER, when configured. This names a header the platform's own
       edge sets and a client cannot forge (``fly-client-ip`` on Fly.io). Use it
       wherever the platform provides one.
    2. The LAST entry of X-Forwarded-For, when proxy headers are trusted. Not the
       first: an edge appends the address it observed to whatever the client
       sent, so the first entry is attacker-controlled and the last is the one
       the platform vouches for. Taking the first made the limiter trivially
       bypassable on the live Fly deployment - each forged value got a fresh
       bucket.
    3. The peer address, which cannot be forged but is the proxy's address when
       one is in front.
    """
    settings = get_settings()

    if settings.client_ip_header:
        value = request.headers.get(settings.client_ip_header.lower())
        if value:
            return value.split(",")[-1].strip()

    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            candidates = [part.strip() for part in forwarded.split(",") if part.strip()]
            if candidates:
                return candidates[-1]

    return request.client.host if request.client else "unknown"
