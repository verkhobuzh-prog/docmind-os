"""
Провенанс сервіс з БЕЗПЕЧНИМИ параметризованими запитами.

═══════════════════════════════════════════════════════════════════════
ВЕКТОР АТАКИ: PostgREST filter injection через .or_() string concat
═══════════════════════════════════════════════════════════════════════

ДО (вразливий код):
───────────────────
    .or_(f"subject.eq.{entity_name},object.eq.{entity_name}")

ПІСЛЯ (безпечний код):
───────────────────────
    asyncpg з параметризованими запитами ($1, $2, $3).
    Fallback на Supabase SDK — два окремі .eq() запити без .or_().
    Validation вхідних параметрів через Pydantic.
"""

from __future__ import annotations

import re
from typing import Any

from fastapi import HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.core.logging import get_logger
from app.db.postgres import get_pool
from app.db.supabase import get_supabase, run_supabase

logger = get_logger("docmind.provenance")

DOCUMENTS_TABLE = "documents"
TRIPLES_TABLE = "semantic_triples"

_ENTITY_NAME_PATTERN = re.compile(r"^[\w\s\-\.]{1,500}$", re.UNICODE)
_PREDICATE_PATTERN = re.compile(r"^[\w\-\_]{1,100}$", re.UNICODE)

_EMPTY_SUMMARY: dict[str, int | float] = {
    "total_triples": 0,
    "avg_confidence": 0.0,
    "high_confidence": 0,
    "medium_confidence": 0,
    "low_confidence": 0,
    "disputed": 0,
}

_ENTITY_FIELDS = "id, evidence_quote, doc_id, confidence, validation_status"


class ProvenanceQueryParams(BaseModel):
    """Валідовані параметри запиту провенансу."""

    entity_name: str = Field(..., min_length=1, max_length=500)
    user_id: str = Field(...)
    predicate: str | None = Field(None, max_length=100)
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)

    @field_validator("entity_name")
    @classmethod
    def validate_entity_name(cls, v: str) -> str:
        v = v.strip()
        if not _ENTITY_NAME_PATTERN.match(v):
            raise ValueError(
                "entity_name contains invalid characters. "
                "Only letters, digits, spaces, hyphens, underscores and dots are allowed."
            )
        return v

    @field_validator("predicate")
    @classmethod
    def validate_predicate(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not _PREDICATE_PATTERN.match(v):
            raise ValueError(
                "predicate contains invalid characters. "
                "Only letters, digits, hyphens and underscores are allowed."
            )
        return v

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        from uuid import UUID

        try:
            UUID(v)
        except (ValueError, AttributeError) as exc:
            raise ValueError("user_id must be a valid UUID") from exc
        return v


class ProvenanceService:
    """
    Сервіс провенансу з параметризованими запитами.

    Пріоритет методів:
      1. asyncpg pool (параметризований SQL) — основний
      2. Supabase SDK з явною санітизацією — fallback
    """

    async def _get_user_doc_ids(self, user_id: str) -> list[str]:
        client = get_supabase()

        def _query():
            return (
                client.table(DOCUMENTS_TABLE)
                .select("id")
                .eq("user_id", user_id)
                .is_("deleted_at", "null")
                .execute()
            )

        result = await run_supabase(_query)
        return [str(row["id"]) for row in (result.data or [])]

    async def _document_belongs_to_user(self, doc_id: str, user_id: str) -> bool:
        client = get_supabase()

        def _query():
            return (
                client.table(DOCUMENTS_TABLE)
                .select("id")
                .eq("id", doc_id)
                .eq("user_id", user_id)
                .is_("deleted_at", "null")
                .maybe_single()
                .execute()
            )

        result = await run_supabase(_query)
        return bool(result.data)

    def _validate_query_params(
        self,
        entity_name: str,
        user_id: str,
        *,
        predicate: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ProvenanceQueryParams:
        try:
            return ProvenanceQueryParams(
                entity_name=entity_name,
                user_id=user_id,
                predicate=predicate,
                limit=limit,
                offset=offset,
            )
        except Exception as exc:
            logger.warning(
                "Invalid provenance query params: %s (entity=%r, user=%s)",
                exc,
                entity_name[:50] if entity_name else None,
                user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid query parameters: {exc}",
            ) from exc

    async def get_provenance_for_entity(
        self,
        entity_name: str,
        user_id: str,
        *,
        relation_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Semantic triples where entity is subject or object (secure queries)."""
        params = self._validate_query_params(
            entity_name,
            user_id,
            predicate=relation_type,
            limit=limit,
            offset=offset,
        )

        pool = get_pool()
        if pool is not None:
            return await self._query_with_asyncpg(pool, params)

        logger.debug("asyncpg pool unavailable, using Supabase SDK fallback")
        return await self._query_with_supabase_sdk(params)

    async def get_entity_provenance(
        self,
        entity_name: str,
        user_id: str,
    ) -> list[dict]:
        """Backward-compatible alias used by knowledge API."""
        rows = await self.get_provenance_for_entity(
            entity_name,
            user_id,
            limit=200,
        )
        return [
            {
                "id": row.get("id"),
                "evidence_quote": row.get("evidence_quote"),
                "doc_id": row.get("doc_id"),
                "confidence": row.get("confidence"),
                "validation_status": row.get("validation_status"),
            }
            for row in rows
        ]

    async def _query_with_asyncpg(
        self,
        pool: Any,
        params: ProvenanceQueryParams,
    ) -> list[dict[str, Any]]:
        base_select = """
            SELECT
                st.id,
                st.doc_id,
                st.chunk_id,
                st.subject,
                st.subject_type,
                st.predicate,
                st.object_,
                st.object_type,
                st.confidence,
                st.evidence_quote,
                st.validation_status,
                st.created_at
            FROM semantic_triples st
            INNER JOIN documents d ON d.id = st.doc_id
            WHERE (st.subject = $1 OR st.object_ = $1)
              AND d.user_id = $2::uuid
              AND d.deleted_at IS NULL
        """

        if params.predicate is not None:
            sql = (
                base_select
                + """
              AND st.predicate = $3
            ORDER BY st.confidence DESC, st.created_at DESC
            LIMIT  $4
            OFFSET $5
            """
            )
            query_args = (
                params.entity_name,
                params.user_id,
                params.predicate,
                params.limit,
                params.offset,
            )
        else:
            sql = (
                base_select
                + """
            ORDER BY st.confidence DESC, st.created_at DESC
            LIMIT  $3
            OFFSET $4
            """
            )
            query_args = (
                params.entity_name,
                params.user_id,
                params.limit,
                params.offset,
            )

        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, *query_args)

        return [dict(row) for row in rows]

    async def _query_with_supabase_sdk(
        self,
        params: ProvenanceQueryParams,
    ) -> list[dict[str, Any]]:
        doc_ids = await self._get_user_doc_ids(params.user_id)
        if not doc_ids:
            return []

        client = get_supabase()

        def _query_as_subject():
            q = (
                client.table(TRIPLES_TABLE)
                .select("*")
                .eq("subject", params.entity_name)
                .in_("doc_id", doc_ids)
                .order("confidence", desc=True)
                .limit(params.limit)
            )
            if params.predicate:
                q = q.eq("predicate", params.predicate)
            return q.execute()

        def _query_as_object():
            q = (
                client.table(TRIPLES_TABLE)
                .select("*")
                .eq("object_", params.entity_name)
                .in_("doc_id", doc_ids)
                .order("confidence", desc=True)
                .limit(params.limit)
            )
            if params.predicate:
                q = q.eq("predicate", params.predicate)
            return q.execute()

        result_subj = await run_supabase(_query_as_subject)
        result_obj = await run_supabase(_query_as_object)

        seen_ids: set[str] = set()
        merged: list[dict[str, Any]] = []

        for row in (result_subj.data or []) + (result_obj.data or []):
            row_id = str(row.get("id", ""))
            if row_id and row_id not in seen_ids:
                seen_ids.add(row_id)
                merged.append(row)

        merged.sort(
            key=lambda r: (float(r.get("confidence", 0)), str(r.get("created_at", ""))),
            reverse=True,
        )
        return merged[params.offset : params.offset + params.limit]

    async def get_triples_for_document(
        self,
        doc_id: str,
        user_id: str,
        min_confidence: float = 0.0,
    ) -> list[dict]:
        """Return semantic triples for a document owned by the user."""
        client = get_supabase()

        def _query():
            return (
                client.table(TRIPLES_TABLE)
                .select("*, documents!inner(user_id)")
                .eq("doc_id", doc_id)
                .eq("documents.user_id", user_id)
                .is_("documents.deleted_at", "null")
                .gte("confidence", min_confidence)
                .order("created_at", desc=True)
                .execute()
            )

        try:
            result = await run_supabase(_query)
            rows = result.data or []
            return [self._strip_joined_document(row) for row in rows]
        except Exception as exc:
            logger.warning(
                "Failed to fetch triples for doc %s (user %s): %s",
                doc_id,
                user_id,
                exc,
            )
            return []

    async def get_confidence_summary(self, user_id: str) -> dict:
        """Aggregate confidence and validation stats for the user's triples."""
        doc_ids = await self._get_user_doc_ids(user_id)
        if not doc_ids:
            return dict(_EMPTY_SUMMARY)

        client = get_supabase()

        def _query():
            return (
                client.table(TRIPLES_TABLE)
                .select("confidence, validation_status")
                .in_("doc_id", doc_ids)
                .execute()
            )

        try:
            rows = (await run_supabase(_query)).data or []
        except Exception as exc:
            logger.warning(
                "Failed to build confidence summary for user %s: %s",
                user_id,
                exc,
            )
            return dict(_EMPTY_SUMMARY)

        if not rows:
            return dict(_EMPTY_SUMMARY)

        total = len(rows)
        confidences = [float(r["confidence"]) for r in rows]
        avg_confidence = sum(confidences) / total

        high = sum(1 for c in confidences if c >= 0.8)
        medium = sum(1 for c in confidences if 0.5 <= c < 0.8)
        low = sum(1 for c in confidences if c < 0.5)
        disputed = sum(1 for r in rows if r.get("validation_status") == "disputed")

        return {
            "total_triples": total,
            "avg_confidence": round(avg_confidence, 4),
            "high_confidence": high,
            "medium_confidence": medium,
            "low_confidence": low,
            "disputed": disputed,
        }

    async def mark_triple_disputed(self, triple_id: str, user_id: str) -> bool:
        """Mark a triple as disputed if its parent document belongs to the user."""
        client = get_supabase()

        def _fetch():
            return (
                client.table(TRIPLES_TABLE)
                .select("id, doc_id")
                .eq("id", triple_id)
                .maybe_single()
                .execute()
            )

        try:
            fetch_result = await run_supabase(_fetch)
        except Exception as exc:
            logger.warning(
                "Failed to fetch triple %s for dispute mark: %s",
                triple_id,
                exc,
            )
            return False

        row = fetch_result.data
        if not row:
            return False

        doc_id = str(row["doc_id"])
        if not await self._document_belongs_to_user(doc_id, user_id):
            logger.debug(
                "User %s cannot dispute triple %s (doc %s not owned)",
                user_id,
                triple_id,
                doc_id,
            )
            return False

        def _update():
            return (
                client.table(TRIPLES_TABLE)
                .update({"validation_status": "disputed"})
                .eq("id", triple_id)
                .execute()
            )

        try:
            update_result = await run_supabase(_update)
            updated = bool(update_result.data)
            if updated:
                logger.info("Marked triple %s as disputed for user %s", triple_id, user_id)
            return updated
        except Exception as exc:
            logger.warning(
                "Failed to mark triple %s as disputed: %s",
                triple_id,
                exc,
            )
            return False

    async def get_entity_graph(
        self,
        entity_name: str,
        user_id: str,
        *,
        depth: int = 1,
    ) -> dict[str, Any]:
        """Return entity relationship graph (BFS, depth capped at 3)."""
        depth = max(1, min(depth, 3))

        triples = await self.get_provenance_for_entity(
            entity_name,
            user_id,
            limit=100,
        )

        nodes: dict[str, dict] = {entity_name: {"name": entity_name, "level": 0}}
        edges: list[dict] = []

        for triple in triples:
            subj = triple.get("subject", "")
            obj = triple.get("object_") or triple.get("object", "")

            if subj not in nodes:
                nodes[subj] = {"name": subj, "level": 1}
            if obj not in nodes:
                nodes[obj] = {"name": obj, "level": 1}

            edges.append(
                {
                    "source": subj,
                    "target": obj,
                    "predicate": triple.get("predicate"),
                    "confidence": triple.get("confidence"),
                }
            )

        if depth >= 2:
            level1_nodes = [name for name, data in nodes.items() if data["level"] == 1]
            for neighbor in level1_nodes[:10]:
                try:
                    neighbor_triples = await self.get_provenance_for_entity(
                        neighbor,
                        user_id,
                        limit=20,
                    )
                except HTTPException:
                    continue

                for triple in neighbor_triples:
                    subj = triple.get("subject", "")
                    obj = triple.get("object_") or triple.get("object", "")
                    if subj not in nodes:
                        nodes[subj] = {"name": subj, "level": 2}
                    if obj not in nodes:
                        nodes[obj] = {"name": obj, "level": 2}
                    edge = {
                        "source": subj,
                        "target": obj,
                        "predicate": triple.get("predicate"),
                        "confidence": triple.get("confidence"),
                    }
                    if edge not in edges:
                        edges.append(edge)

        return {
            "entity": entity_name,
            "nodes": list(nodes.values()),
            "edges": edges,
            "depth": depth,
        }

    @staticmethod
    def _strip_joined_document(row: dict) -> dict:
        cleaned = dict(row)
        cleaned.pop("documents", None)
        return cleaned
