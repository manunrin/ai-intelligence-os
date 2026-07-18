"""Report creation and update schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field, field_validator


class ReportCreate(BaseModel):
    """Schema for creating a new intelligence report."""

    title: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1)
    category: str | None = Field(None, max_length=64)
    importance_score: float | None = Field(None, ge=0, le=10)
    article_ids: list[str] = Field(default_factory=list)
    agent_run_id: str | None = Field(None, description="UUID of the triggering agent run")
    generated_by: str | None = Field(None, max_length=64)

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

    @field_validator("article_ids")
    @classmethod
    def validate_article_ids(cls, v: list[str]) -> list[str]:
        for item in v:
            try:
                uuid.UUID(item)
            except ValueError:
                raise ValueError(f"Each article_id must be a valid UUID string, got {item!r}")
        return v


class ReportUpdate(BaseModel):
    """Schema for updating an existing intelligence report."""

    title: str | None = Field(None, max_length=500)
    body: str | None = Field(None, max_length=500000)
    category: str | None = Field(None, max_length=64)
    importance_score: float | None = Field(None, ge=0, le=10)
    article_ids: list[str] | None = Field(None)

    @field_validator("article_ids")
    @classmethod
    def validate_article_ids(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        for item in v:
            try:
                uuid.UUID(item)
            except ValueError:
                raise ValueError(f"Each article_id must be a valid UUID string, got {item!r}")
        return v
