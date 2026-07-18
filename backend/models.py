"""Shared Pydantic models."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"


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
