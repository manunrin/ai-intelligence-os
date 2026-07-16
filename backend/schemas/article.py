"""Article response schema."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ArticleResponse(BaseModel):
    """Article returned by the API."""

    id: str
    title: str = Field(max_length=500)
    summary: str | None = None
    content: str | None = None
    url: str | None = None
    source: str
    language: str = Field(default="en", max_length=8)
    tags: list[str] = Field(default_factory=list)
    status: str = Field(default="raw")
    fetched_at: datetime
    published_at: datetime | None = None

    model_config = {"from_attributes": True}
