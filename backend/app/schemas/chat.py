from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"] = "user"
    content: str = Field(..., min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    document_ids: Optional[list[UUID]] = Field(
        default=None,
        description="Scope search to these documents; None = all user documents",
    )
    top_k: int = Field(default=8, ge=1, le=20)
    stream: bool = False


class Source(BaseModel):
    """Retrieved chunk used as context."""

    document_id: UUID
    chunk_index: int
    chunk_id: Optional[UUID] = None
    snippet: str
    score: float = Field(..., ge=0.0, le=1.0)
    filename: Optional[str] = None
    vector_score: Optional[float] = None
    fts_score: Optional[float] = None


class Citation(BaseModel):
    """Citation returned to the client."""

    document_id: UUID
    chunk_index: int
    snippet: str
    label: Optional[str] = Field(
        default=None,
        description="Reference label in the answer, e.g. [1]",
    )


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    model: str
    query: str
