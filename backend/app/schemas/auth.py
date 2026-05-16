from typing import Optional

from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    id: str
    email: Optional[EmailStr] = None
    role: Optional[str] = None
