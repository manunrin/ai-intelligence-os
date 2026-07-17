"""Audit log schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AuditLogResponse(BaseModel):
    """Single audit log entry returned by the API."""

    id: str
    action: str = Field(max_length=32)
    resource_type: str = Field(max_length=64)
    resource_id: str | None = None
    user_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    metadata: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditStatsResponse(BaseModel):
    """Aggregated audit statistics."""

    action_counts: dict[str, int] = Field(default_factory=dict)
    top_users: list[dict[str, str | int]] = Field(default_factory=list)
    daily_trend: list[dict[str, str | int]] = Field(default_factory=list)
