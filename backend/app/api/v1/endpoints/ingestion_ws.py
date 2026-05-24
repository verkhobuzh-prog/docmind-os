"""WebSocket endpoint — real-time ingestion progress for Documents UI."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import DEV_USER_ID
from app.core.state_machine import DocumentState, DocumentStateMachine
from app.db.supabase import get_supabase, run_supabase
from app.services.lifecycle_service import get_lifecycle_service

logger = get_logger(__name__)

ingestion_ws_router = APIRouter()

POLL_INTERVAL_SECONDS = 1.0

STATE_PROGRESS: dict[str, int] = {
    DocumentState.UPLOADED.value: 0,
    DocumentState.VALIDATING.value: 5,
    DocumentState.QUEUED.value: 10,
    DocumentState.PARSING.value: 25,
    DocumentState.CHUNKING.value: 40,
    DocumentState.EMBEDDING.value: 60,
    DocumentState.GRAPH_ENRICHMENT.value: 80,
    DocumentState.INDEXED.value: 95,
    DocumentState.READY.value: 100,
    DocumentState.PARTIAL_SUCCESS.value: 90,
    DocumentState.RETRYING.value: 5,
    DocumentState.FAILED_PARSE.value: 100,
    DocumentState.FAILED_EMBEDDING.value: 100,
    DocumentState.FAILED_GRAPH.value: 100,
    DocumentState.FAILED_VALIDATION.value: 100,
    # Legacy statuses
    "failed": 100,
}

STATE_LABELS: dict[str, str] = {
    DocumentState.UPLOADED.value: "Uploaded",
    DocumentState.VALIDATING.value: "Validating",
    DocumentState.QUEUED.value: "Queued",
    DocumentState.PARSING.value: "Parsing",
    DocumentState.CHUNKING.value: "Chunking",
    DocumentState.EMBEDDING.value: "Embedding",
    DocumentState.GRAPH_ENRICHMENT.value: "Graph enrichment",
    DocumentState.INDEXED.value: "Indexed",
    DocumentState.READY.value: "Ready",
    DocumentState.PARTIAL_SUCCESS.value: "Partial success",
    DocumentState.RETRYING.value: "Retrying",
    DocumentState.FAILED_PARSE.value: "Parse failed",
    DocumentState.FAILED_EMBEDDING.value: "Embedding failed",
    DocumentState.FAILED_GRAPH.value: "Graph enrichment failed",
    DocumentState.FAILED_VALIDATION.value: "Validation failed",
    "failed": "Failed",
}

_DONE_STATES = frozenset(
    {
        DocumentState.READY.value,
        DocumentState.INDEXED.value,
        DocumentState.FAILED_PARSE.value,
        DocumentState.FAILED_EMBEDDING.value,
        DocumentState.FAILED_GRAPH.value,
        DocumentState.FAILED_VALIDATION.value,
        "failed",
    }
)

_state_machine = DocumentStateMachine()


class IngestionConnectionManager:
    """Track active WebSocket subscribers per document."""

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}

    async def connect(self, doc_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(doc_id, set()).add(websocket)

    def disconnect(self, doc_id: str, websocket: WebSocket) -> None:
        peers = self._connections.get(doc_id)
        if not peers:
            return
        peers.discard(websocket)
        if not peers:
            self._connections.pop(doc_id, None)

    async def broadcast(self, doc_id: str, payload: dict[str, Any]) -> None:
        for websocket in list(self._connections.get(doc_id, set())):
            try:
                await websocket.send_json(payload)
            except Exception as exc:
                logger.debug("WS broadcast failed doc=%s: %s", doc_id, exc)
                self.disconnect(doc_id, websocket)


manager = IngestionConnectionManager()


def build_progress_payload(doc_id: str, state: str, *, event: str | None = None) -> dict[str, Any]:
    try:
        enum_state = DocumentState(state)
    except ValueError:
        enum_state = None

    is_failed = (
        state == "failed"
        or state.startswith("failed_")
        or (enum_state is not None and _state_machine.is_failed(enum_state))
    )
    is_terminal = state in _DONE_STATES or (
        enum_state is not None and _state_machine.is_terminal(enum_state)
    )

    return {
        "doc_id": doc_id,
        "status": state,
        "progress": STATE_PROGRESS.get(state, 0),
        "label": STATE_LABELS.get(state, state.replace("_", " ").title()),
        "event": event,
        "is_terminal": is_terminal or is_failed,
        "is_failed": is_failed,
    }


async def _resolve_ws_user(token: str | None) -> dict[str, Any] | None:
    if settings.auth_disabled:
        return {
            "id": DEV_USER_ID,
            "email": "dev@docmind.local",
            "role": "authenticated",
        }

    if not token or not settings.supabase_configured:
        return None

    try:
        client = get_supabase()

        def _get_user():
            return client.auth.get_user(token)

        response = await run_supabase(_get_user)
        if response.user is None:
            return None

        user = response.user
        app_meta = user.app_metadata or {}
        user_meta = user.user_metadata or {}
        return {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
            "org_id": app_meta.get("org_id") or user_meta.get("org_id"),
        }
    except Exception as exc:
        logger.warning("WS auth failed: %s", exc)
        return None


async def _document_belongs_to_user(doc_id: str, user_id: str) -> bool:
    client = get_supabase()

    def _query():
        return (
            client.table("documents")
            .select("id")
            .eq("id", doc_id)
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )

    result = await run_supabase(_query)
    return bool(result.data)


async def notify_ingestion_progress(
    doc_id: str,
    *,
    status: str | None = None,
    event: str | None = None,
) -> None:
    """Push progress update to all subscribers (optional hook from lifecycle)."""
    if status is None:
        lifecycle = get_lifecycle_service()
        status = (await lifecycle.get_state(doc_id)).value
    payload = build_progress_payload(doc_id, status, event=event)
    await manager.broadcast(doc_id, payload)


@ingestion_ws_router.websocket("/{document_id}/ingestion/ws")
async def ingestion_progress_websocket(
    websocket: WebSocket,
    document_id: UUID,
    token: str | None = Query(default=None),
) -> None:
    """Stream ingestion lifecycle updates for a single document."""
    doc_id = str(document_id)
    user = await _resolve_ws_user(token)
    if user is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if not await _document_belongs_to_user(doc_id, str(user["id"])):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(doc_id, websocket)
    lifecycle = get_lifecycle_service()
    last_payload: dict[str, Any] | None = None

    try:
        while True:
            state = await lifecycle.get_state(doc_id)
            payload = build_progress_payload(doc_id, state.value)
            if payload != last_payload:
                await websocket.send_json(payload)
                last_payload = payload
                if payload["is_terminal"]:
                    break
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
    except WebSocketDisconnect:
        logger.debug("Ingestion WS disconnected doc=%s", doc_id)
    except Exception as exc:
        logger.warning("Ingestion WS error doc=%s: %s", doc_id, exc)
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass
    finally:
        manager.disconnect(doc_id, websocket)


router = ingestion_ws_router
