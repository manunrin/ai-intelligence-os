"""Intelligence report response schema."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class IntelligenceReportResponse(BaseModel):
    """Intelligence report returned by the API."""

    id: str
    topic: str = Field(max_length=500)
    created_at: datetime
    user_id: str | None = None

    model_config = {"from_attributes": True}
