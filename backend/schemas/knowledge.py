"""Knowledge item response schema."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgeItemResponse(BaseModel):
    """Knowledge item returned by the API."""

    id: str
    title: str = Field(max_length=500)
    content: str
    kind: str = Field(max_length=32)
    article_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    user_id: str | None = None

    model_config = {"from_attributes": True}
