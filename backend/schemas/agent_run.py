"""Agent run response schema."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AgentRunResponse(BaseModel):
    """Agent run returned by the API."""

    id: str
    agent_id: str
    workflow_id: str | None = None
    status: str = Field(default="running", max_length=16)
    input_payload: dict = Field(default_factory=dict)
    output_payload: dict | None = None
    error_message: str | None = None
    started_at: datetime
    finished_at: datetime | None = None

    model_config = {"from_attributes": True}
