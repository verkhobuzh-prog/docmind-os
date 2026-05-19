from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.schemas.invite import (
    InviteClaimRequest,
    InviteClaimResponse,
    InviteValidateRequest,
    InviteValidateResponse,
)
from app.services.invite_service import InviteService, get_invite_service

invites_router = APIRouter(prefix="/invites", tags=["invites"])


@invites_router.post("/validate", response_model=InviteValidateResponse)
async def validate_invite(
    body: InviteValidateRequest,
    svc: Annotated[InviteService, Depends(get_invite_service)],
):
    """Public: check if invite code is valid (no auth)."""
    return await svc.validate_code(body.code)


@invites_router.post("/claim", response_model=InviteClaimResponse)
async def claim_invite(
    body: InviteClaimRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    svc: Annotated[InviteService, Depends(get_invite_service)],
):
    """Authenticated user claims an invite after registration."""
    name = body.display_name or (current_user.get("user_metadata") or {}).get("full_name")
    return await svc.claim_invite(
        code=body.code,
        user_id=str(current_user["id"]),
        email=current_user.get("email") or "",
        display_name=name,
    )
