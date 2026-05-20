from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status

from app.core.config import settings
from app.core.security import get_current_org, get_current_user
from app.core.state_machine import DocumentEvent
from app.schemas.document import DocumentListResponse, DocumentResponse, DocumentUploadResponse
from app.services.document_service import DocumentService
from app.services.ingestion_service import get_ingestion_service
from app.services.lifecycle_service import get_lifecycle_service
from app.services.document_upload_policy import MAX_AUDIO_SIZE, MAX_DOCUMENT_SIZE

documents_router = APIRouter()


def get_document_service() -> DocumentService:
    return DocumentService()


@documents_router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document file",
)
async def upload_document(
    file: Annotated[
        UploadFile,
        File(
            description=(
                "Document file: PDF, TXT, MD, DOCX, PPTX, XLSX, XLS, CSV"
                "; audio MP3/M4A/WAV/WebM/OGG when OpenAI is configured. "
                f"Max {MAX_DOCUMENT_SIZE // (1024 * 1024)}MB documents, "
                f"{MAX_AUDIO_SIZE // (1024 * 1024)}MB audio."
            ),
        ),
    ],
    current_user: Annotated[dict, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
    background_tasks: BackgroundTasks,
    org_id: Annotated[Optional[UUID], Form(description="Organization ID (optional)")] = None,
    resolved_org: Annotated[Optional[str], Depends(get_current_org)] = None,
) -> DocumentUploadResponse:
    effective_org = org_id
    if effective_org is None and resolved_org:
        try:
            effective_org = UUID(resolved_org)
        except ValueError:
            pass
    result = await service.upload_document(file, current_user, org_id=effective_org)
    if settings.INGESTION_AUTO_START and await service.should_auto_ingest(
        result.document.mime_type or ""
    ):
        ingestion = get_ingestion_service()
        background_tasks.add_task(
            ingestion.start_ingestion,
            result.document.id,
            current_user,
        )
    return result


@documents_router.get(
    "",
    response_model=DocumentListResponse,
    summary="List current user's documents",
)
async def list_documents(
    current_user: Annotated[dict, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentListResponse:
    return await service.list_by_user(current_user["id"])


@documents_router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document by ID",
)
async def get_document(
    document_id: UUID,
    current_user: Annotated[dict, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentResponse:
    document = await service.get_by_id(document_id, current_user["id"])
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return document


@documents_router.get(
    "/{document_id}/history",
    summary="Get document lifecycle event history",
)
async def get_document_history(
    document_id: UUID,
    current_user: Annotated[dict, Depends(get_current_user)],
    doc_service: Annotated[DocumentService, Depends(get_document_service)],
    limit: int = 20,
) -> dict:
    document = await doc_service.get_by_id(document_id, current_user["id"])
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    lifecycle = get_lifecycle_service()
    doc_id = str(document_id)
    history = await lifecycle.get_history(doc_id, limit=limit)
    current_state = await lifecycle.get_state(doc_id)

    return {
        "doc_id": doc_id,
        "history": history,
        "current_state": current_state.value,
    }


@documents_router.post(
    "/{document_id}/retry",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Retry ingestion for a failed document",
)
async def retry_document_ingestion(
    document_id: UUID,
    current_user: Annotated[dict, Depends(get_current_user)],
    doc_service: Annotated[DocumentService, Depends(get_document_service)],
    background_tasks: BackgroundTasks,
) -> dict:
    document = await doc_service.get_by_id(document_id, current_user["id"])
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    lifecycle = get_lifecycle_service()
    doc_id = str(document_id)
    user_id = str(current_user["id"])

    if not await lifecycle.can_retry(doc_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Max retries exceeded or document not in failed state",
        )

    retry_count = await lifecycle.increment_retry(doc_id)
    await lifecycle.transition(doc_id, user_id, DocumentEvent.RETRY)
    await lifecycle.transition(doc_id, user_id, DocumentEvent.QUEUE)

    ingestion = get_ingestion_service()
    background_tasks.add_task(ingestion.start_ingestion, document_id, current_user)

    return {
        "doc_id": doc_id,
        "retry_count": retry_count,
        "status": "queued",
    }


@documents_router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete document",
)
async def delete_document(
    document_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    doc_service: Annotated[DocumentService, Depends(get_document_service)],
) -> None:
    """Soft delete документа"""
    await doc_service.delete_document(document_id, str(current_user["id"]))
