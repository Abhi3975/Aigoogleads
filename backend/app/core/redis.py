"""Shared Redis client + health ping."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.core.config import settings


@lru_cache
def get_redis() -> Any:
    import redis.asyncio as aioredis

    return aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=0.5,
        socket_timeout=1.0,
    )


async def ping_redis() -> bool:
    await get_redis().ping()
    return True
