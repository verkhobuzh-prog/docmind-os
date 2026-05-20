from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.logging import get_logger
from app.db.redis import get_redis
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag_service import RAGService, get_rag_service

logger = get_logger(__name__)

chat_router = APIRouter()


async def check_rate_limit(user_id: str) -> None:
    """Simple rate limit: RATE_LIMIT_PER_MINUTE requests per user."""
    if not settings.redis_configured:
        return

    try:
        redis = get_redis()
    except RuntimeError:
        return

    key = f"rate_limit:chat:{user_id}"
    try:
        current = await redis.incr(key)
        if current == 1:
            await redis.expire(key, 60)
        if current > settings.RATE_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Rate limit exceeded. Max {settings.RATE_LIMIT_PER_MINUTE} "
                    "requests/minute."
                ),
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Rate limit check failed: %s", exc)


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
    await check_rate_limit(str(current_user["id"]))
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
