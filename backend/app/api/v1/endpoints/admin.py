from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security import get_admin_user
from app.schemas.invite import InviteCodeResponse, InviteCreateRequest, PilotMemberResponse
from app.services.invite_service import InviteService, get_invite_service

admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.post("/invites", response_model=InviteCodeResponse)
async def create_invite(
    body: InviteCreateRequest,
    admin: Annotated[dict, Depends(get_admin_user)],
    svc: Annotated[InviteService, Depends(get_invite_service)],
):
    return await svc.create_invite(admin, body)


@admin_router.get("/invites", response_model=list[InviteCodeResponse])
async def list_invites(
    _admin: Annotated[dict, Depends(get_admin_user)],
    svc: Annotated[InviteService, Depends(get_invite_service)],
):
    return await svc.list_invites()


@admin_router.get("/members", response_model=list[PilotMemberResponse])
async def list_members(
    _admin: Annotated[dict, Depends(get_admin_user)],
    svc: Annotated[InviteService, Depends(get_invite_service)],
):
    return await svc.list_members()
