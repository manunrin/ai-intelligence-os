"""Knowledge item creation and update schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field, field_validator


class KnowledgeItemCreate(BaseModel):
    """Schema for creating a new knowledge item."""

    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    kind: str = Field(..., max_length=32)
    article_id: str | None = Field(None, description="UUID of the related article")
    tags: list[str] = Field(default_factory=list)

    @field_validator("article_id")
    @classmethod
    def validate_article_id(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError(f"article_id must be a valid UUID string, got {v!r}")
        return v


class KnowledgeItemUpdate(BaseModel):
    """Schema for updating an existing knowledge item."""

    title: str | None = Field(None, max_length=500)
    content: str | None = Field(None, max_length=500000)
    kind: str | None = Field(None, max_length=32)
    tags: list[str] | None = Field(None)
