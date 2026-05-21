"""Document lifecycle service — state transitions and event history."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.logging import get_logger
from app.core.state_machine import (
    DocumentEvent,
    DocumentState,
    DocumentStateMachine,
    InvalidTransitionError,
)
from app.db.supabase import get_supabase, run_supabase

logger = get_logger(__name__)

DOCUMENTS_TABLE = "documents"
EVENTS_TABLE = "document_events"

_LEGACY_STATUS_MAP: dict[str, DocumentState] = {
    "failed": DocumentState.FAILED_PARSE,
}


class DocumentLifecycleService:
    """Manage document states via the lifecycle state machine."""

    def __init__(self) -> None:
        self._state_machine = DocumentStateMachine()

    @staticmethod
    def _parse_state(raw: str | None) -> DocumentState:
        if not raw:
            return DocumentState.UPLOADED
        if raw in _LEGACY_STATUS_MAP:
            return _LEGACY_STATUS_MAP[raw]
        try:
            return DocumentState(raw)
        except ValueError:
            logger.warning("Unknown document status %r, defaulting to UPLOADED", raw)
            return DocumentState.UPLOADED

    async def get_state(self, doc_id: str) -> DocumentState:
        client = get_supabase()

        def _query():
            return (
                client.table(DOCUMENTS_TABLE)
                .select("status")
                .eq("id", doc_id)
                .maybe_single()
                .execute()
            )

        result = await run_supabase(_query)
        row = result.data
        if not row:
            return DocumentState.UPLOADED
        return self._parse_state(row.get("status"))

    async def transition(
        self,
        doc_id: str,
        user_id: str,
        event: DocumentEvent,
        error_code: str | None = None,
        error_message: str | None = None,
        metadata: dict | None = None,
    ) -> DocumentState:
        current_state = await self.get_state(doc_id)

        try:
            new_state = self._state_machine.transition(current_state, event)
        except InvalidTransitionError as exc:
            logger.warning(
                "Invalid lifecycle transition for doc %s: %s",
                doc_id,
                exc,
            )
            return current_state

        now = datetime.now(timezone.utc).isoformat()
        update_payload: dict[str, Any] = {
            "status": new_state.value,
            "last_event": event.value,
            "updated_at": now,
        }
        if error_code is not None:
            update_payload["error_code"] = error_code

        event_row = {
            "document_id": doc_id,
            "user_id": user_id,
            "from_state": current_state.value,
            "to_state": new_state.value,
            "event": event.value,
            "error_code": error_code,
            "error_message": error_message,
            "metadata": metadata or {},
            "created_at": now,
        }

        client = get_supabase()

        def _update_and_log():
            client.table(DOCUMENTS_TABLE).update(update_payload).eq("id", doc_id).execute()
            return client.table(EVENTS_TABLE).insert(event_row).execute()

        await run_supabase(_update_and_log)
        return new_state

    async def get_history(self, doc_id: str, limit: int = 20) -> list[dict]:
        client = get_supabase()

        def _query():
            return (
                client.table(EVENTS_TABLE)
                .select("*")
                .eq("document_id", doc_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )

        result = await run_supabase(_query)
        return list(result.data or [])

    async def increment_retry(self, doc_id: str) -> int:
        client = get_supabase()

        def _query():
            return (
                client.table(DOCUMENTS_TABLE)
                .select("retry_count")
                .eq("id", doc_id)
                .maybe_single()
                .execute()
            )

        fetch = await run_supabase(_query)
        current = int((fetch.data or {}).get("retry_count") or 0)
        new_count = current + 1

        def _update():
            return (
                client.table(DOCUMENTS_TABLE)
                .update({"retry_count": new_count, "updated_at": datetime.now(timezone.utc).isoformat()})
                .eq("id", doc_id)
                .execute()
            )

        await run_supabase(_update)
        return new_count

    async def can_retry(self, doc_id: str, max_retries: int = 3) -> bool:
        client = get_supabase()

        def _query():
            return (
                client.table(DOCUMENTS_TABLE)
                .select("retry_count")
                .eq("id", doc_id)
                .maybe_single()
                .execute()
            )

        result = await run_supabase(_query)
        row = result.data or {}
        retry_count = int(row.get("retry_count") or 0)
        current_state = await self.get_state(doc_id)
        return retry_count < max_retries and self._state_machine.can_retry(current_state)


_lifecycle_service: DocumentLifecycleService | None = None


def get_lifecycle_service() -> DocumentLifecycleService:
    global _lifecycle_service
    if _lifecycle_service is None:
        _lifecycle_service = DocumentLifecycleService()
    return _lifecycle_service
