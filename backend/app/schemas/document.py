from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    filename: str = Field(..., min_length=1, max_length=1024)


class DocumentCreate(DocumentBase):
    """Manual document metadata (no file upload)."""

    org_id: Optional[UUID] = None
    mime_type: Optional[str] = None


class DocumentResponse(DocumentBase):
    id: UUID
    org_id: Optional[UUID] = None
    user_id: UUID
    storage_path: str
    mime_type: Optional[str] = None
    size_bytes: int = Field(..., ge=0)
    status: str = "uploaded"
    subject: Optional[str] = None
    document_type: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentUploadResponse(BaseModel):
    """Response after successful file upload to Storage + DB insert."""

    document: DocumentResponse
    signed_url: Optional[str] = None
    message: str = "Document uploaded successfully"


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int = Field(..., ge=0)
