"""API rate limiting.

Fixed-window limiter keyed by client IP + scope. Uses Redis in production
(shared across workers) and falls back to an in-process window if Redis is
unavailable. Enforced only in staging/production so local dev and tests are
unaffected; can be forced on for unit tests.
"""

from __future__ import annotations

import time

from fastapi import Request

from app.core.config import settings
from app.core.exceptions import RateLimitError
from app.core.logging import get_logger

logger = get_logger(__name__)

_memory: dict[str, list[float]] = {}


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded:
        return forwarded
    return request.client.host if request.client else "anonymous"


class RateLimiter:
    """FastAPI dependency enforcing ``times`` requests per ``seconds`` window."""

    def __init__(
        self, *, times: int, seconds: int, scope: str, enabled: bool | None = None
    ) -> None:
        self.times = times
        self.seconds = seconds
        self.scope = scope
        self.enabled = (
            settings.ENVIRONMENT in {"production", "staging"} if enabled is None else enabled
        )

    async def __call__(self, request: Request) -> None:
        if not self.enabled:
            return
        key = f"rl:{self.scope}:{_client_ip(request)}"
        if not await self._allowed(key):
            raise RateLimitError(
                f"Rate limit exceeded ({self.times}/{self.seconds}s) for '{self.scope}'."
            )

    async def _allowed(self, key: str) -> bool:
        try:
            return await self._allowed_redis(key)
        except Exception:
            # Fail open to an in-process window if Redis is unavailable.
            return self._allowed_memory(key)

    async def _allowed_redis(self, key: str) -> bool:
        from app.core.redis import get_redis

        redis = get_redis()
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, self.seconds)
        return int(count) <= self.times

    def _allowed_memory(self, key: str) -> bool:
        now = time.time()
        window_start = now - self.seconds
        bucket = [t for t in _memory.get(key, []) if t > window_start]
        bucket.append(now)
        _memory[key] = bucket
        return len(bucket) <= self.times


# Sensitive-endpoint limiters (per client IP).
auth_rate_limit = RateLimiter(times=30, seconds=60, scope="auth")
ai_rate_limit = RateLimiter(times=30, seconds=60, scope="ai")
ads_rate_limit = RateLimiter(times=90, seconds=60, scope="ads")
