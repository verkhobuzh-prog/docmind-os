"""Celery tasks. Run sync wrappers around our async services."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from celery import Task
from celery.exceptions import MaxRetriesExceededError
from celery.utils.log import get_task_logger

from app.core.telemetry import traced_span
from app.services.ingestion_service import IngestionService
from app.workers.celery_app import celery_app

logger = get_task_logger(__name__)


class IngestionTask(Task):
    """Base task with structured failure tracking."""

    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True
    max_retries = 3
    acks_late = True


@celery_app.task(
    bind=True,
    base=IngestionTask,
    name="app.workers.tasks.ingest_document",
)
def ingest_document(self, document_id: str, user: dict[str, Any]) -> dict:
    """
    Run full ingestion pipeline for a document.
    On final failure (retries exhausted) → push to dead_letter queue.
    """
    logger.info(
        "Ingestion task started: doc=%s attempt=%d",
        document_id,
        self.request.retries + 1,
    )
    with traced_span(
        "celery.ingest_document",
        {
            "document.id": document_id,
            "retry.attempt": self.request.retries,
        },
    ):
        try:
            service = IngestionService()
            result = asyncio.run(service.start_ingestion(UUID(document_id), user))
            return {
                "document_id": document_id,
                "status": result.status.value,
                "chunks": result.chunks_created,
                "task_id": self.request.id,
            }
        except MaxRetriesExceededError:
            raise
        except Exception as exc:
            logger.exception(
                "Ingestion failed (attempt %d/%d)",
                self.request.retries + 1,
                self.max_retries + 1,
            )
            if self.request.retries >= self.max_retries:
                handle_dead_letter.apply_async(
                    args=[document_id, user, str(exc), self.request.id],
                    queue="dead_letter",
                )
            raise


@celery_app.task(
    name="app.workers.tasks.handle_dead_letter",
    queue="dead_letter",
    acks_late=True,
)
def handle_dead_letter(
    document_id: str,
    user: dict,
    error: str,
    original_task_id: str,
) -> None:
    """
    Persist failed ingestion for ops review.
    Updates document.status = 'failed' with full error context.
    """
    from app.db.supabase import get_supabase, run_supabase

    logger.error(
        "DEAD LETTER: doc=%s task=%s error=%s",
        document_id,
        original_task_id,
        error,
    )

    async def _persist() -> None:
        client = get_supabase()
        now = datetime.now(timezone.utc).isoformat()

        def _update_doc():
            return (
                client.table("documents")
                .update(
                    {
                        "status": "failed",
                        "updated_at": now,
                        "metadata": {
                            "ingestion_error": error,
                            "failed_task_id": original_task_id,
                            "failed_at": now,
                        },
                    }
                )
                .eq("id", document_id)
                .execute()
            )

        def _insert_dlq():
            return (
                client.table("ingestion_dead_letter")
                .insert(
                    {
                        "document_id": document_id,
                        "user_id": user.get("id"),
                        "task_id": original_task_id,
                        "error": error,
                        "created_at": now,
                    }
                )
                .execute()
            )

        await run_supabase(_update_doc)
        try:
            await run_supabase(_insert_dlq)
        except Exception as dlq_exc:
            logger.warning("DLQ table insert failed (table may not exist): %s", dlq_exc)

    asyncio.run(_persist())
