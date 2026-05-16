from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.security import get_current_user
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag_service import RAGService, get_rag_service

chat_router = APIRouter()


@chat_router.post(
    "",
    response_model=ChatResponse,
    summary="RAG chat over user documents",
)
async def chat(
    payload: ChatRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    service: Annotated[RAGService, Depends(get_rag_service)],
):
    """
    Ask a question over indexed documents.

    - `document_ids`: optional scope; omit to search all indexed docs for the user.
    - `stream=true`: returns Server-Sent Events (SSE).
    """
    if payload.stream:
        return StreamingResponse(
            service.query_stream(
                payload.query,
                current_user,
                document_ids=payload.document_ids,
                top_k=payload.top_k,
            ),
            media_type="text/event-stream",
        )

    return await service.query(
        payload.query,
        current_user,
        document_ids=payload.document_ids,
        top_k=payload.top_k,
    )
