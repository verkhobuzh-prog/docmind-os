from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    auth,
    chat,
    config_public,
    documents,
    ingestion,
    invites,
    knowledge,
    reasoning,
)
from app.api.v1.endpoints.profiles import profiles_router

api_router = APIRouter()
api_router.include_router(config_public.public_router)
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
api_router.include_router(profiles_router)
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(reasoning.router, prefix="/reasoning", tags=["reasoning"])
api_router.include_router(invites.invites_router)
api_router.include_router(admin.admin_router)
