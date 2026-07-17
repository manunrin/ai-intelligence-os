"""Intelligence report response schema."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class IntelligenceReportResponse(BaseModel):
    """Intelligence report returned by the API."""

    id: str
    topic: str = Field(max_length=500)
    research_result: dict | None = None
    analysis_result: dict | None = None
    translation_result: dict | None = None
    knowledge_items: list[dict] = Field(default_factory=list)
    tasks: list[dict] = Field(default_factory=list)
    created_at: datetime
    user_id: str | None = None

    model_config = {"from_attributes": True}
