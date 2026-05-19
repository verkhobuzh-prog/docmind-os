from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core.auth import get_current_user
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag_service import RAGService, get_rag_service

chat_router = APIRouter()


@chat_router.post(
    "",
    response_model=ChatResponse,
    summary="RAG chat over user documents",
)
async def chat_query(
    body: ChatRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    rag_service: Annotated[RAGService, Depends(get_rag_service)],
):
    """
    Ask a question over indexed documents.

    - `document_ids`: optional scope; omit to search all indexed docs for the user.
    - `stream=true`: returns Server-Sent Events (SSE).
    """
    user_id = str(current_user["id"])

    if body.stream:
        return StreamingResponse(
            rag_service.query_stream(
                query=body.query,
                user_id=user_id,
                document_ids=body.document_ids,
                top_k=body.top_k,
            ),
            media_type="text/event-stream",
        )

    return await rag_service.query(
        query=body.query,
        user_id=user_id,
        top_k=body.top_k,
        document_ids=body.document_ids,
    )
