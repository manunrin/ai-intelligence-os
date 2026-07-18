"""Article creation and update schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field, field_validator


class ArticleCreate(BaseModel):
    """Schema for creating a new article."""

    title: str = Field(..., min_length=1, max_length=500)
    summary: str | None = Field(None, max_length=50000)
    content: str | None = Field(None, max_length=500000)
    source_id: str = Field(..., description="UUID of the source")
    language: str = Field(default="en", max_length=8)
    status: str = Field(default="raw", max_length=16)
    metadata_: dict | None = Field(None, description="Additional metadata as JSON")

    @field_validator("source_id")
    @classmethod
    def validate_source_id(cls, v: str) -> str:
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError(f"source_id must be a valid UUID string, got {v!r}")
        return v


class ArticleUpdate(BaseModel):
    """Schema for updating an existing article."""

    title: str | None = Field(None, max_length=500)
    summary: str | None = Field(None, max_length=50000)
    content: str | None = Field(None, max_length=500000)
    source_id: str | None = Field(None, description="UUID of the source")
    language: str | None = Field(None, max_length=8)
    status: str | None = Field(None, max_length=16)
    metadata_: dict | None = Field(None, description="Additional metadata as JSON")

    @field_validator("source_id")
    @classmethod
    def validate_source_id(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError(f"source_id must be a valid UUID string, got {v!r}")
        return v
