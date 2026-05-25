"""Embedding generation via OpenAI API."""

from __future__ import annotations

import asyncio
from typing import List

from openai import OpenAI

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("dochub.embeddings")


async def embed_texts(texts: list[str]) -> list[list[float] | None]:
    """
    Batch-embed texts. Returns None per item when OpenAI is not configured.
    """
    if not texts:
        return []

    if not settings.openai_configured:
        logger.warning("OPENAI_API_KEY not set — skipping embeddings")
        return [None] * len(texts)

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def _create():
        response = client.embeddings.create(
            model=settings.EMBEDDING_MODEL,
            input=texts,
            dimensions=settings.EMBEDDING_DIMENSIONS,
        )
        return [item.embedding for item in response.data]

    return await asyncio.to_thread(_create)
