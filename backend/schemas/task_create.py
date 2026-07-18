"""Task creation and update schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field, field_validator


class TaskCreate(BaseModel):
    """Schema for creating a new task."""

    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = Field(None, max_length=50000)
    priority: str = Field(default="medium", max_length=8)
    status: str = Field(default="pending", max_length=16)
    external_id: str | None = Field(None, max_length=128)
    external_url: str | None = Field(None)
    agent_run_id: str | None = Field(None, description="UUID of the triggering agent run")
    knowledge_item_id: str | None = Field(None, description="UUID of the related knowledge item")
    due_date: str | None = Field(None, description="ISO-8601 datetime string")

    @field_validator("agent_run_id")
    @classmethod
    def validate_agent_run_id(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError(f"agent_run_id must be a valid UUID string, got {v!r}")
        return v

    @field_validator("knowledge_item_id")
    @classmethod
    def validate_knowledge_item_id(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError(f"knowledge_item_id must be a valid UUID string, got {v!r}")
        return v


class TaskUpdate(BaseModel):
    """Schema for updating an existing task."""

    title: str | None = Field(None, max_length=500)
    description: str | None = Field(None, max_length=50000)
    priority: str | None = Field(None, max_length=8)
    status: str | None = Field(None, max_length=16)
    external_id: str | None = Field(None, max_length=128)
    external_url: str | None = Field(None)
    due_date: str | None = Field(None, description="ISO-8601 datetime string")
