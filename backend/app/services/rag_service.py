"""RAG chat service — retrieval, generation, citations."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from openai import OpenAI

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.chat import ChatResponse, Citation, Source
from app.services.profile_service import ProfileService
from app.services.prompt_builder import build_system_prompt
from app.utils.guardrails import is_query_allowed
from app.utils.retrieval import RetrievedChunk, compress_context, get_relevant_chunks

logger = get_logger("docmind.rag")

_RAG_CITATION_RULE = (
    "\n\nЦитуй фрагменти документів мітками [1], [2] — номери відповідають блокам контексту."
)


class RAGService:
    def __init__(self) -> None:
        self._profile_service: ProfileService | None = None

    def _get_profile_service(self) -> ProfileService:
        if self._profile_service is None:
            self._profile_service = ProfileService()
        return self._profile_service

    async def _resolve_system_prompt(self, user_id: str) -> tuple[str, float]:
        active_profile = None
        if settings.supabase_configured:
            active_profile = await self._get_profile_service().get_active_profile(user_id)
        system_prompt = build_system_prompt(active_profile) + _RAG_CITATION_RULE
        temperature = (
            active_profile.preferences.temperature
            if active_profile is not None
            else 0.3
        )
        return system_prompt, temperature
    async def query(
        self,
        *,
        query: str,
        user_id: str,
        document_ids: list[UUID] | None = None,
        top_k: int | None = None,
    ) -> ChatResponse:
        allowed, reason = is_query_allowed(query)
        if not allowed:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)

        if not settings.openai_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM service is not configured (OPENAI_API_KEY)",
            )

        chunks = await get_relevant_chunks(
            query,
            user_id,
            document_ids=document_ids,
            top_k=top_k,
        )

        if not chunks:
            return ChatResponse(
                answer="No indexed documents found for your query. Upload and ingest documents first.",
                sources=[],
                citations=[],
                model=settings.DEFAULT_LLM_MODEL,
                query=query,
            )

        compressed = compress_context(chunks)
        context_block, label_map = _build_context_block(compressed)
        sources = _chunks_to_sources(compressed)

        system_prompt, temperature = await self._resolve_system_prompt(user_id)
        answer = await self._generate_answer(
            query, context_block, system_prompt=system_prompt, temperature=temperature
        )

        citations = _extract_citations(answer, label_map, compressed)
        return ChatResponse(
            answer=answer,
            sources=sources,
            citations=citations,
            model=settings.DEFAULT_LLM_MODEL,
            query=query,
        )

    async def query_stream(
        self,
        *,
        query: str,
        user_id: str,
        document_ids: list[UUID] | None = None,
        top_k: int | None = None,
    ) -> AsyncIterator[str]:
        """SSE stream: yields `data: {...}\\n\\n` JSON events."""
        allowed, reason = is_query_allowed(query)
        if not allowed:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)

        if not settings.openai_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM service is not configured (OPENAI_API_KEY)",
            )

        chunks = await get_relevant_chunks(
            query, user_id, document_ids=document_ids, top_k=top_k
        )
        compressed = compress_context(chunks)
        sources = _chunks_to_sources(compressed)
        yield f"data: {json.dumps({'type': 'sources', 'sources': [s.model_dump(mode='json') for s in sources]})}\n\n"

        if not compressed:
            yield f"data: {json.dumps({'type': 'done', 'answer': 'No indexed documents found.', 'citations': [], 'model': settings.DEFAULT_LLM_MODEL})}\n\n"
            return

        context_block, label_map = _build_context_block(compressed)
        system_prompt, temperature = await self._resolve_system_prompt(user_id)
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        def _stream():
            return client.chat.completions.create(
                model=settings.DEFAULT_LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Context:\n{context_block}\n\nQuestion: {query}",
                    },
                ],
                stream=True,
                temperature=temperature,
            )

        stream = await asyncio.to_thread(_stream)
        full = []
        for event in stream:
            delta = event.choices[0].delta.content or ""
            if delta:
                full.append(delta)
                yield f"data: {json.dumps({'type': 'token', 'content': delta})}\n\n"

        answer = "".join(full)
        citations = _extract_citations(answer, label_map, compressed)
        yield f"data: {json.dumps({'type': 'done', 'answer': answer, 'citations': [c.model_dump(mode='json') for c in citations], 'model': settings.DEFAULT_LLM_MODEL})}\n\n"

    async def _generate_answer(
        self,
        query: str,
        context_block: str,
        *,
        system_prompt: str,
        temperature: float = 0.3,
    ) -> str:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        def _call():
            response = client.chat.completions.create(
                model=settings.DEFAULT_LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Context:\n{context_block}\n\nQuestion: {query}",
                    },
                ],
                temperature=temperature,
            )
            return response.choices[0].message.content or ""

        return await asyncio.to_thread(_call)


def _build_context_block(chunks: list[RetrievedChunk]) -> tuple[str, dict[int, RetrievedChunk]]:
    label_map: dict[int, RetrievedChunk] = {}
    parts: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        label_map[i] = chunk
        parts.append(
            f"[{i}] document_id={chunk.document_id} chunk_index={chunk.chunk_index}\n"
            f"{chunk.content}"
        )
    return "\n\n".join(parts), label_map


def _chunks_to_sources(chunks: list[RetrievedChunk]) -> list[Source]:
    def _parse_chunk_id(raw: str | None) -> UUID | None:
        if not raw:
            return None
        try:
            return UUID(raw)
        except ValueError:
            return None

    return [
        Source(
            document_id=c.document_id,
            chunk_index=c.chunk_index,
            chunk_id=_parse_chunk_id(c.chunk_id),
            snippet=c.content[:500],
            score=round(c.score, 4),
            filename=c.filename,
            vector_score=round(c.vector_score, 4) if c.vector_score else None,
            fts_score=round(c.fts_score, 4) if c.fts_score else None,
        )
        for c in chunks
    ]


def _extract_citations(
    answer: str,
    label_map: dict[int, RetrievedChunk],
    chunks: list[RetrievedChunk],
) -> list[Citation]:
    import re

    cited_labels = sorted({int(m) for m in re.findall(r"\[(\d+)\]", answer)})
    citations: list[Citation] = []
    for label in cited_labels:
        chunk = label_map.get(label)
        if chunk is None:
            continue
        citations.append(
            Citation(
                document_id=chunk.document_id,
                chunk_index=chunk.chunk_index,
                snippet=chunk.content[:300],
                label=f"[{label}]",
            )
        )

    if not citations and chunks:
        for i, chunk in enumerate(chunks[:3], start=1):
            citations.append(
                Citation(
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                    snippet=chunk.content[:300],
                    label=f"[{i}]",
                )
            )
    return citations


def get_rag_service() -> RAGService:
    return RAGService()
