from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class IngestionStatus(str, Enum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    INDEXED = "indexed"
    FAILED = "failed"


class ChunkMetadata(BaseModel):
    """Metadata stored per chunk in document_chunks.metadata."""

    chunk_index: int = 0
    page: Optional[int] = None
    sheet: Optional[str] = None
    source: Optional[str] = None
    token_count: Optional[int] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    parser: Optional[str] = None
    extra: dict[str, Any] = Field(default_factory=dict)


class IngestionResponse(BaseModel):
    document_id: UUID
    status: IngestionStatus
    chunks_created: int = Field(default=0, ge=0)
    embeddings_created: int = Field(default=0, ge=0)
    message: str = ""
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
