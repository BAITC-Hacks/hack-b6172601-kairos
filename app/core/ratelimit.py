"""Per-IP rate limiting.

Purpose: the hackathon issues API keys, and a publicly deployed demo runs on
one of them. Without a limiter, a single visitor can drain it. Disabled by
default (RATE_LIMIT_PER_MINUTE=0); enable it only on the public deployment.

Deliberately in-process and dependency-free. It is a spend guard for one
instance, not a distributed rate limiter.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from app.core.errors import AppError

WINDOW_SECONDS = 60
_hits: dict[str, deque[float]] = defaultdict(deque)


class RateLimited(AppError):
    def __init__(self, limit: int, retry_after: int):
        super().__init__(
            f"Rate limit exceeded: {limit} requests per minute. Retry in {retry_after}s.",
            status_code=429,
            code="rate_limited",
        )
        self.retry_after = retry_after


def check(client_ip: str, limit: int, now: float | None = None) -> None:
    """Raise RateLimited when the caller is over the limit. No-op when limit <= 0."""
    if limit <= 0:
        return

    now = time.time() if now is None else now
    bucket = _hits[client_ip]
    cutoff = now - WINDOW_SECONDS
    while bucket and bucket[0] <= cutoff:
        bucket.popleft()

    if len(bucket) >= limit:
        retry_after = max(1, int(bucket[0] + WINDOW_SECONDS - now) + 1)
        raise RateLimited(limit, retry_after)

    bucket.append(now)

    # Keep the table from growing without bound on a long-lived instance.
    # One-shot addresses never come back, so eviction must look at age rather
    # than only dropping already-empty buckets.
    if len(_hits) > 5_000:
        stale = [k for k, v in _hits.items() if not v or v[-1] <= cutoff]
        for key in stale:
            del _hits[key]


def reset() -> None:
    """Test helper."""
    _hits.clear()
