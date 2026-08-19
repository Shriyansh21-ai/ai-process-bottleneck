"""
Authentication request/response schemas (Milestone 6).

Response schemas deliberately EXCLUDE ``hashed_password`` and any secret so raw
ORM ``User`` objects are never serialized to clients.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Registration payload."""
    email: EmailStr = Field(..., description="Unique login email")
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Plaintext password (min 8 chars). Never stored in plaintext.",
    )


class UserResponse(BaseModel):
    """Public user view — no password / secrets."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    is_active: bool
    is_admin: bool
    created_at: Optional[datetime] = None


class Token(BaseModel):
    """OAuth2 bearer token response."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Decoded token claims we rely on internally."""
    user_id: Optional[int] = None
