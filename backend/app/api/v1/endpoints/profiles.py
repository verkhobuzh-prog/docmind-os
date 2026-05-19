from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.auth import get_current_user
from app.schemas.profile import ProfileCreate, ProfileRead, ProfileUpdate
from app.services.profile_service import ProfileService, get_profile_service

profiles_router = APIRouter(prefix="/profiles", tags=["profiles"])

CurrentUser = Annotated[dict, Depends(get_current_user)]
SvcDep = Annotated[ProfileService, Depends(get_profile_service)]


@profiles_router.get("", response_model=list[ProfileRead])
async def list_profiles(user: CurrentUser, svc: SvcDep):
    return await svc.list_profiles(str(user["id"]))


@profiles_router.get("/active", response_model=ProfileRead | None)
async def get_active(user: CurrentUser, svc: SvcDep):
    return await svc.get_active_profile(str(user["id"]))


@profiles_router.post("", response_model=ProfileRead, status_code=status.HTTP_201_CREATED)
async def create_profile(body: ProfileCreate, user: CurrentUser, svc: SvcDep):
    return await svc.create_profile(str(user["id"]), body)


@profiles_router.patch("/{profile_id}", response_model=ProfileRead)
async def update_profile(
    profile_id: str, body: ProfileUpdate, user: CurrentUser, svc: SvcDep
):
    return await svc.update_profile(profile_id, str(user["id"]), body)


@profiles_router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(profile_id: str, user: CurrentUser, svc: SvcDep):
    await svc.delete_profile(profile_id, str(user["id"]))


@profiles_router.post("/{profile_id}/activate", response_model=ProfileRead)
async def activate_profile(profile_id: str, user: CurrentUser, svc: SvcDep):
    return await svc.set_active(profile_id, str(user["id"]))
