from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status

from app.core.config import settings
from app.core.security import get_current_org, get_current_user
from app.services.ingestion_service import get_ingestion_service
from app.schemas.document import DocumentListResponse, DocumentResponse, DocumentUploadResponse
from app.services.document_service import DocumentService

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
    file: Annotated[UploadFile, File(description="Document file (PDF, DOCX, XLSX, TXT, images)")],
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
    if settings.INGESTION_AUTO_START:
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
