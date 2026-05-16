"""Async PostgreSQL pool for hybrid search (pgvector + full-text)."""

from __future__ import annotations

from typing import Optional

import asyncpg

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("docmind.postgres")

_pool: Optional[asyncpg.Pool] = None


async def init_postgres() -> None:
    global _pool
    if _pool is not None:
        return
    try:
        _pool = await asyncpg.create_pool(
            str(settings.DATABASE_URL),
            min_size=1,
            max_size=5,
            command_timeout=30,
        )
        logger.info("PostgreSQL pool initialized")
    except Exception as exc:
        logger.warning("PostgreSQL pool unavailable: %s", exc)
        _pool = None


async def close_postgres() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool | None:
    return _pool
