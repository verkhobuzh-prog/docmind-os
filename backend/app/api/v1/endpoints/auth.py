from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import settings
from app.core.security import get_current_user
from app.schemas.auth import UserResponse
from app.services.invite_service import InviteService, get_invite_service

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[dict, Depends(get_current_user)],
    invites_svc: Annotated[InviteService, Depends(get_invite_service)],
) -> UserResponse:
    email = (current_user.get("email") or "").lower()
    is_admin = email in settings.pilot_admin_emails or (
        settings.auth_disabled and email == "dev@docmind.local"
    )
    user_id = str(current_user["id"])
    is_member = await invites_svc.is_pilot_member(user_id)
    if not is_member and not is_admin:
        await invites_svc.ensure_pilot_member(current_user)
        is_member = await invites_svc.is_pilot_member(user_id)
    return UserResponse(
        id=current_user["id"],
        email=current_user.get("email"),
        role=current_user.get("role"),
        is_admin=is_admin,
        pilot_member=is_member or is_admin,
    )
