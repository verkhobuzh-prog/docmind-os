from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class InviteValidateRequest(BaseModel):
    code: str = Field(..., min_length=4, max_length=32)


class InviteValidateResponse(BaseModel):
    valid: bool
    label: Optional[str] = None
    message: Optional[str] = None


class InviteClaimRequest(BaseModel):
    code: str = Field(..., min_length=4, max_length=32)
    display_name: Optional[str] = Field(default=None, max_length=200)


class InviteClaimResponse(BaseModel):
    ok: bool
    message: str


class InviteCreateRequest(BaseModel):
    label: Optional[str] = Field(default=None, max_length=200)
    max_uses: int = Field(default=10, ge=1, le=500)
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=365)


class InviteCodeResponse(BaseModel):
    id: UUID
    code: str
    label: Optional[str] = None
    max_uses: int
    use_count: int
    expires_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    invite_url: Optional[str] = None


class PilotMemberResponse(BaseModel):
    id: UUID
    user_id: UUID
    email: str
    display_name: Optional[str] = None
    invite_code: Optional[str] = None
    joined_at: datetime
