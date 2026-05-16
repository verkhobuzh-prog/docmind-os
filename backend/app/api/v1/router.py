from fastapi import APIRouter

from app.api.v1.endpoints import auth, chat, documents, ingestion

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(
    documents.documents_router,
    prefix="/documents",
    tags=["documents"],
)
api_router.include_router(
    ingestion.ingestion_router,
    prefix="/documents",
    tags=["ingestion"],
)
api_router.include_router(
    chat.chat_router,
    prefix="/chat",
    tags=["chat"],
)
