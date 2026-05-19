from fastapi import APIRouter

from app.core.config import settings
from app.schemas.auth import PilotConfigResponse

public_router = APIRouter(tags=["config"])


@public_router.get("/config/pilot", response_model=PilotConfigResponse)
async def pilot_config():
    return PilotConfigResponse(
        invite_required=settings.PILOT_INVITE_REQUIRED,
        frontend_url=settings.FRONTEND_URL,
    )
