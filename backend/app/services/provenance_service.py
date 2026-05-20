"""Provenance audit service — read and analyze semantic triple provenance."""

from __future__ import annotations

from app.core.logging import get_logger
from app.db.supabase import get_supabase, run_supabase

logger = get_logger(__name__)

DOCUMENTS_TABLE = "documents"
TRIPLES_TABLE = "semantic_triples"

_EMPTY_SUMMARY: dict[str, int | float] = {
    "total_triples": 0,
    "avg_confidence": 0.0,
    "high_confidence": 0,
    "medium_confidence": 0,
    "low_confidence": 0,
    "disputed": 0,
}

_ENTITY_FIELDS = "id, evidence_quote, doc_id, confidence, validation_status"


class ProvenanceService:
    """Read and analyze provenance data stored in semantic_triples."""

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

    async def get_entity_provenance(
        self,
        entity_name: str,
        user_id: str,
    ) -> list[dict]:
        """Return provenance rows where the entity appears as subject or object."""
        doc_ids = await self._get_user_doc_ids(user_id)
        if not doc_ids:
            return []

        client = get_supabase()

        def _query_as_subject():
            return (
                client.table(TRIPLES_TABLE)
                .select(_ENTITY_FIELDS)
                .in_("doc_id", doc_ids)
                .eq("subject", entity_name)
                .execute()
            )

        def _query_as_object():
            return (
                client.table(TRIPLES_TABLE)
                .select(_ENTITY_FIELDS)
                .in_("doc_id", doc_ids)
                .eq("object_", entity_name)
                .execute()
            )

        try:
            result_as_subject = await run_supabase(_query_as_subject)
            result_as_object = await run_supabase(_query_as_object)
            rows = (result_as_subject.data or []) + (result_as_object.data or [])
            seen: set[str] = set()
            unique_rows: list[dict] = []
            for row in rows:
                row_id = str(row["id"])
                if row_id not in seen:
                    seen.add(row_id)
                    unique_rows.append(row)
            unique_rows.sort(key=lambda r: float(r.get("confidence", 0)), reverse=True)
            return unique_rows
        except Exception as exc:
            logger.warning(
                "Failed to fetch entity provenance for %r (user %s): %s",
                entity_name,
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

    @staticmethod
    def _strip_joined_document(row: dict) -> dict:
        """Remove embedded documents join payload from a triple row."""
        cleaned = dict(row)
        cleaned.pop("documents", None)
        return cleaned
