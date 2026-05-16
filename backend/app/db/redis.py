"""Redis client — cache, rate limiting, session store (Phase 1)."""

from __future__ import annotations

from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings

_redis: Optional[aioredis.Redis] = None


async def init_redis() -> None:
    global _redis
    if settings.redis_configured:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


def get_redis() -> aioredis.Redis:
    if _redis is None:
        raise RuntimeError("Redis not initialized. Set REDIS_URL and start redis service.")
    return _redis


async def ping_redis() -> bool:
    if not settings.redis_configured or _redis is None:
        return False
    try:
        return bool(await _redis.ping())
    except Exception:
        return False
