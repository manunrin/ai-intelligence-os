"""Task response schema."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TaskResponse(BaseModel):
    """Task returned by the API."""

    id: str
    title: str = Field(max_length=500)
    description: str | None = None
    priority: str = Field(default="medium", max_length=8)
    status: str = Field(default="pending", max_length=16)
    dependency: list[str] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}
