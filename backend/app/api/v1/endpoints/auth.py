from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.schemas.auth import UserResponse

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> UserResponse:
    return UserResponse(
        id=current_user["id"],
        email=current_user.get("email"),
        role=current_user.get("role"),
    )
