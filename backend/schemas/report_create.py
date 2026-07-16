"""Report creation and update schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    """Schema for creating a new intelligence report."""

    title: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1)
    category: str | None = Field(None, max_length=64)
    importance_score: float | None = Field(None, ge=0, le=10)
    article_ids: list[str] = Field(default_factory=list)
    agent_run_id: str | None = Field(None, description="UUID of the triggering agent run")
    generated_by: str | None = Field(None, max_length=64)


class ReportUpdate(BaseModel):
    """Schema for updating an existing intelligence report."""

    title: str | None = Field(None, max_length=500)
    body: str | None = Field(None, max_length=500000)
    category: str | None = Field(None, max_length=64)
    importance_score: float | None = Field(None, ge=0, le=10)
    article_ids: list[str] | None = Field(None)
