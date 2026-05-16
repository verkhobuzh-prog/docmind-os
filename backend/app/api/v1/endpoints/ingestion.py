from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.core.config import settings
from app.core.security import get_current_user
from app.schemas.ingestion import IngestionResponse, IngestionStatus
from app.services.ingestion_service import IngestionService, get_ingestion_service

ingestion_router = APIRouter()


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

    background_tasks.add_task(service.start_ingestion, document_id, current_user)
    return IngestionResponse(
        document_id=document_id,
        status=IngestionStatus.PARSING,
        message="Ingestion started in background",
    )
