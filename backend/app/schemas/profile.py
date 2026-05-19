from __future__ import annotations
from datetime import datetime
from typing import Any
from uuid import UUID
import re
from pydantic import BaseModel, Field, field_validator


DOMAIN_VALUES = {
    "general", "education", "legal", "business", "technical", "medical"
}

class ProfilePreferences(BaseModel):
    response_style: str = "balanced"    # concise | balanced | detailed
    language: str = "uk"
    forbidden_topics: list[str] = []
    temperature: float = Field(default=0.3, ge=0.0, le=1.0)
    extra: dict[str, Any] = {}

class ProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    complexity_level: int = Field(default=3, ge=1, le=5)
    domain: str = Field(default="general")
    preferences: ProfilePreferences = ProfilePreferences()

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        if v not in DOMAIN_VALUES:
            raise ValueError(f"domain must be one of {DOMAIN_VALUES}")
        return v

class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    complexity_level: int | None = Field(default=None, ge=1, le=5)
    domain: str | None = None
    preferences: ProfilePreferences | None = None

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str | None) -> str | None:
        if v is not None and v not in DOMAIN_VALUES:
            raise ValueError(f"domain must be one of {DOMAIN_VALUES}")
        return v

class ProfileRead(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    complexity_level: int
    domain: str
    is_active: bool
    preferences: ProfilePreferences
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
