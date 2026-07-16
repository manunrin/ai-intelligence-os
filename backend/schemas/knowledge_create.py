"""Knowledge item creation and update schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class KnowledgeItemCreate(BaseModel):
    """Schema for creating a new knowledge item."""

    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    kind: str = Field(..., max_length=32)
    article_id: str | None = Field(None, description="UUID of the related article")
    tags: list[str] = Field(default_factory=list)


class KnowledgeItemUpdate(BaseModel):
    """Schema for updating an existing knowledge item."""

    title: str | None = Field(None, max_length=500)
    content: str | None = Field(None, max_length=500000)
    kind: str | None = Field(None, max_length=32)
    tags: list[str] | None = Field(None)
