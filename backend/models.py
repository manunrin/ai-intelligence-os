"""Shared Pydantic models."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"


class ErrorResponse(BaseModel):
    detail: str = Field(description="Error description")
    code: str = Field(description="Machine-readable error code")


# Re-export all ORM models for Alembic
from backend.database.models import (
    Source,
    Article,
    IntelligenceReport,
    KnowledgeItem,
    Task,
    Agent,
    AgentRun,
    Workflow,
    UserPreference,
    User,
)

__all__ = [
    "HealthResponse",
    "ErrorResponse",
    "Source",
    "Article",
    "IntelligenceReport",
    "KnowledgeItem",
    "Task",
    "Agent",
    "AgentRun",
    "Workflow",
    "UserPreference",
    "User",
]
