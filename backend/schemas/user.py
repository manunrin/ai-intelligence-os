"""User authentication schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """Schema for user registration."""

    username: str = Field(..., min_length=3, max_length=64)
    email: str = Field(...)
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    """Schema for user login."""

    username: str = Field(...)
    password: str = Field(...)


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """User profile returned by the API."""

    id: str
    username: str
    email: str
    role: str = Field(default="user")
    is_active: bool = True
    last_login_at: datetime | None = None
    created_at: datetime
