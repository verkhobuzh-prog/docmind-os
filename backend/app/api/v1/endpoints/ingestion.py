from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.core.security import get_admin_user, get_current_user
from app.schemas.ingestion import IngestionResponse, IngestionStatus
from app.services.ingestion_service import IngestionService, get_ingestion_service
from app.services.job_queue import get_job_queue

ingestion_router = APIRouter()


@ingestion_router.get(
    "/ingestion/queue/stats",
    summary="Ingestion queue statistics (admin)",
)
async def get_ingestion_queue_stats(
    _admin: Annotated[dict, Depends(get_admin_user)],
) -> dict:
    stats = await get_job_queue().get_queue_stats()
    if not stats.get("available"):
        return {
            "available": False,
            "queued": 0,
            "processing": 0,
            "failed": 0,
        }
    return {
        "available": True,
        "queued": int(stats.get("queued", 0)) + int(stats.get("queued_high", 0)),
        "processing": int(stats.get("processing", 0)),
        "failed": int(stats.get("failed", 0)),
    }


@ingestion_router.post(
    "/{document_id}/ingest",
    response_model=IngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start document ingestion (parse, chunk, embed)",
)
async def ingest_document(
    document_id: UUID,
    current_user: Annotated[dict, Depends(get_current_user)],
    service: Annotated[IngestionService, Depends(get_ingestion_service)],
    background_tasks: BackgroundTasks,
    sync: bool = False,
) -> IngestionResponse:
    """
    Trigger ingestion pipeline.

    - `sync=false` (default): runs in background, returns 202 immediately.
    - `sync=true`: blocks until ingestion completes (useful for dev/tests).
    """
    if sync:
        return await service.start_ingestion(document_id, current_user)

    queue = get_job_queue()
    enqueued = await queue.enqueue(
        doc_id=str(document_id),
        user_id=str(current_user["id"]),
        priority=0,
    )

    if enqueued:
        return IngestionResponse(
            document_id=document_id,
            status=IngestionStatus.PARSING,
            message="queued",
        )

    background_tasks.add_task(service.start_ingestion, document_id, current_user)
    return IngestionResponse(
        document_id=document_id,
        status=IngestionStatus.PARSING,
        message="processing",
    )
