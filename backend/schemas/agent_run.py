"""Agent run response schema."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AgentRunResponse(BaseModel):
    """Agent run returned by the API."""

    id: str
    agent_id: str
    workflow_id: str | None = None
    status: str = Field(default="running", max_length=32)
    stage: str = "initializing"
    input_payload: dict = Field(default_factory=dict)
    output_payload: dict | None = None
    error_message: str | None = None
    started_at: datetime
    finished_at: datetime | None = None
    duration_ms: int | None = None
    user_id: str | None = None

    model_config = {"from_attributes": True}


class StageProgressResponse(BaseModel):
    """Per-stage execution progress."""

    stage_name: str
    stage_order: int
    status: str
    input_summary: dict | None = None
    output_summary: dict | None = None
    error_message: str | None = None
    duration_ms: int | None = None
    started_at: str | None = None
    finished_at: str | None = None


class AgentRunWithStages(AgentRunResponse):
    """Agent run with embedded stage progress records."""

    stages: list[StageProgressResponse] = Field(default_factory=list)
    stream_url: str | None = None


class AgentRunRequest(BaseModel):
    """Request body for submitting an agent run."""

    agent_type: str = Field(
        description="Type of agent pipeline to execute (e.g., 'intelligence', 'autonomous')."
    )
    input_payload: dict[str, object] = Field(
        default_factory=dict,
        description="Input data for the agent workflow.",
    )
    topic: str | None = Field(
        default=None,
        description="Convenience field for research topics.",
    )
    source_id: str | None = Field(
        default=None,
        description="Source article ID for targeted runs.",
    )
