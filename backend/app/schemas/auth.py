from typing import Optional

from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    id: str
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_admin: bool = False
    pilot_member: bool = True


class PilotConfigResponse(BaseModel):
    invite_required: bool
    frontend_url: str
