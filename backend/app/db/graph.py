"""FalkorDB client — knowledge graph store (sync SDK, asyncio.to_thread)."""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional, TypeVar

from falkordb import FalkorDB
from falkordb.graph import Graph

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

_db: Optional[FalkorDB] = None


async def run_graph(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Run sync FalkorDB SDK call without blocking the event loop."""
    return await asyncio.to_thread(fn, *args, **kwargs)


async def init_graph() -> None:
    global _db
    if not settings.graph_configured:
        return

    def _connect() -> FalkorDB:
        return FalkorDB(url=str(settings.GRAPH_DB_URL))

    try:
        _db = await run_graph(_connect)
    except Exception as exc:
        logger.warning("FalkorDB unavailable during init: %s", exc)
        _db = None
        return

    if not await ping_graph():
        logger.warning("FalkorDB ping failed after connect; graph features unavailable")
        await close_graph()


async def close_graph() -> None:
    global _db
    if _db is None:
        return

    client = _db
    _db = None

    def _close() -> None:
        client.close()

    try:
        await run_graph(_close)
    except Exception as exc:
        logger.warning("Error closing FalkorDB connection: %s", exc)


def get_graph(graph_name: str) -> Graph | None:
    if _db is None:
        if settings.graph_configured:
            logger.warning("FalkorDB not initialized; get_graph(%r) returning None", graph_name)
        return None
    try:
        return _db.select_graph(graph_name)
    except Exception as exc:
        logger.warning("Failed to select FalkorDB graph %r: %s", graph_name, exc)
        return None


async def ping_graph() -> bool:
    if not settings.graph_configured or _db is None:
        return False
    try:
        return bool(await run_graph(_db.ping))
    except Exception as exc:
        logger.warning("FalkorDB ping failed: %s", exc)
        return False
