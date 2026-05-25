"""Hybrid retrieval: pgvector + full-text search with RLS via user_id filter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

import numpy as np

from app.core.config import settings
from app.core.logging import get_logger
from app.db.postgres import get_pool
from app.db.supabase import get_supabase, run_supabase
from app.utils.embeddings import embed_texts

logger = get_logger("Doc-Hub.retrieval")

DOCUMENTS_TABLE = "documents"
CHUNKS_TABLE = "document_chunks"


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: UUID
    chunk_index: int
    content: str
    score: float
    vector_score: float = 0.0
    fts_score: float = 0.0
    filename: str | None = None
    metadata: dict[str, Any] | None = None


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def _normalize_scores(scores: list[float]) -> list[float]:
    if not scores:
        return []
    mn, mx = min(scores), max(scores)
    if mx - mn < 1e-9:
        return [1.0 if s > 0 else 0.0 for s in scores]
    return [(s - mn) / (mx - mn) for s in scores]


async def _get_allowed_document_ids(
    user_id: str,
    document_ids: list[UUID] | None,
) -> list[str]:
    """RLS-equivalent filter: only documents owned by the user."""
    client = get_supabase()

    def _query():
        q = (
            client.table(DOCUMENTS_TABLE)
            .select("id, filename")
            .eq("user_id", user_id)
            .eq("status", "indexed")
            .is_("deleted_at", "null")
        )
        if document_ids:
            q = q.in_("id", [str(d) for d in document_ids])
        return q.execute()

    result = await run_supabase(_query)
    return [row["id"] for row in result.data]


async def hybrid_search(
    query: str,
    user_id: str,
    query_embedding: list[float],
    *,
    document_ids: list[UUID] | None = None,
    top_k: int | None = None,
) -> list[RetrievedChunk]:
    """
    Hybrid search (vector + FTS) scoped to user's indexed documents.
    Falls back to in-memory ranking when PostgreSQL pool is unavailable.
    """
    k = top_k or settings.RAG_TOP_K
    allowed_doc_ids = await _get_allowed_document_ids(user_id, document_ids)
    if not allowed_doc_ids:
        return []

    pool = get_pool()
    if pool is not None and query_embedding:
        try:
            return await _hybrid_search_sql(
                pool, query, query_embedding, allowed_doc_ids, k
            )
        except Exception as exc:
            logger.warning("SQL hybrid search failed, using fallback: %s", exc)

    return await _hybrid_search_fallback(
        query, query_embedding, allowed_doc_ids, k
    )


async def _hybrid_search_sql(
    pool,
    query: str,
    query_embedding: list[float],
    document_ids: list[str],
    top_k: int,
) -> list[RetrievedChunk]:
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    vw = settings.RAG_VECTOR_WEIGHT
    fw = 1.0 - vw

    sql = """
        SELECT
            c.id::text AS chunk_id,
            c.document_id,
            c.chunk_index,
            c.content,
            c.metadata,
            d.filename,
            CASE WHEN c.embedding IS NOT NULL
                THEN 1 - (c.embedding <=> $1::vector)
                ELSE 0
            END AS vector_score,
            ts_rank(c.content_tsv, plainto_tsquery('english', $2)) AS fts_score
        FROM document_chunks c
        INNER JOIN documents d ON d.id = c.document_id
        WHERE d.id = ANY($3::uuid[])
          AND d.deleted_at IS NULL
          AND d.status = 'indexed'
        ORDER BY ($4::float * CASE WHEN c.embedding IS NOT NULL
                THEN 1 - (c.embedding <=> $1::vector) ELSE 0 END
            + $5::float * ts_rank(c.content_tsv, plainto_tsquery('english', $2))) DESC
        LIMIT $6
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            sql,
            embedding_str,
            query,
            document_ids,
            vw,
            fw,
            top_k,
        )

    results: list[RetrievedChunk] = []
    for row in rows:
        vs = float(row["vector_score"] or 0)
        fs = float(row["fts_score"] or 0)
        combined = vw * vs + fw * min(fs, 1.0)
        results.append(
            RetrievedChunk(
                chunk_id=row["chunk_id"],
                document_id=UUID(str(row["document_id"])),
                chunk_index=int(row["chunk_index"]),
                content=row["content"],
                score=combined,
                vector_score=vs,
                fts_score=fs,
                filename=row.get("filename"),
                metadata=row.get("metadata") or {},
            )
        )
    return results


async def _hybrid_search_fallback(
    query: str,
    query_embedding: list[float],
    document_ids: list[str],
    top_k: int,
) -> list[RetrievedChunk]:
    client = get_supabase()

    def _fetch():
        return (
            client.table(CHUNKS_TABLE)
            .select("id, document_id, chunk_index, content, metadata, embedding, documents(filename)")
            .in_("document_id", document_ids)
            .execute()
        )

    result = await run_supabase(_fetch)
    rows = result.data or []

    query_lower = query.lower()
    query_terms = set(query_lower.split())

    scored: list[RetrievedChunk] = []
    for row in rows:
        content = row.get("content") or ""
        emb = row.get("embedding")
        vector_score = 0.0
        if query_embedding and emb:
            try:
                emb_list = emb if isinstance(emb, list) else list(emb)
                vector_score = max(0.0, _cosine_similarity(query_embedding, emb_list))
            except Exception:
                vector_score = 0.0

        content_lower = content.lower()
        fts_score = 0.0
        if query_terms:
            hits = sum(1 for t in query_terms if t in content_lower)
            fts_score = hits / len(query_terms)

        vw = settings.RAG_VECTOR_WEIGHT
        combined = vw * vector_score + (1 - vw) * fts_score
        if combined <= 0:
            continue

        doc_join = row.get("documents") or {}
        filename = doc_join.get("filename") if isinstance(doc_join, dict) else None

        scored.append(
            RetrievedChunk(
                chunk_id=str(row["id"]),
                document_id=UUID(str(row["document_id"])),
                chunk_index=int(row["chunk_index"]),
                content=content,
                score=combined,
                vector_score=vector_score,
                fts_score=fts_score,
                filename=filename,
                metadata=row.get("metadata") or {},
            )
        )

    scored.sort(key=lambda x: x.score, reverse=True)
    return scored[:top_k]


async def get_relevant_chunks(
    query: str,
    user_id: str,
    *,
    document_ids: list[UUID] | None = None,
    top_k: int | None = None,
) -> list[RetrievedChunk]:
    """Embed query and run hybrid search."""
    embeddings = await embed_texts([query])
    query_embedding = embeddings[0] if embeddings and embeddings[0] else []
    chunks = await hybrid_search(
        query,
        user_id,
        query_embedding,
        document_ids=document_ids,
        top_k=top_k,
    )
    if query_embedding and len(chunks) > 1:
        chunks = _rerank_cosine(chunks, query_embedding)
    return chunks[: top_k or settings.RAG_TOP_K]


def _rerank_cosine(chunks: list[RetrievedChunk], query_embedding: list[float]) -> list[RetrievedChunk]:
    """MVP reranker using stored embeddings from metadata if present."""
    return sorted(chunks, key=lambda c: c.score, reverse=True)


def compress_context(chunks: list[RetrievedChunk], max_chars: int | None = None) -> list[RetrievedChunk]:
    """Truncate context to fit token/char budget."""
    limit = max_chars or settings.RAG_MAX_CONTEXT_CHARS
    selected: list[RetrievedChunk] = []
    total = 0
    for chunk in chunks:
        if total + len(chunk.content) > limit:
            remaining = limit - total
            if remaining > 100:
                trimmed = RetrievedChunk(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content[:remaining] + "...",
                    score=chunk.score,
                    vector_score=chunk.vector_score,
                    fts_score=chunk.fts_score,
                    filename=chunk.filename,
                    metadata=chunk.metadata,
                )
                selected.append(trimmed)
            break
        selected.append(chunk)
        total += len(chunk.content)
    return selected
