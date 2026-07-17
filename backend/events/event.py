"""Base event types and domain events."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class AuditAction(str, Enum):
    """Types of auditable actions."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    AGENT_RUN = "agent_run"
    LOGIN = "login"


@dataclass
class BaseEvent:
    """Base class for all domain events in the system."""

    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = ""


@dataclass
class ArticleCreatedEvent(BaseEvent):
    """Published when a new article is successfully ingested."""

    article_id: uuid.UUID = field(default_factory=uuid.uuid4)
    title: str = ""
    url: str = ""
    language: str = "en"
    tags: list[str] = field(default_factory=list)
    metadata_: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.source = "ingestion"


@dataclass
class AuditLogEvent(BaseEvent):
    """Published when an auditable action occurs."""

    action: AuditAction = field(default=AuditAction.CREATE)
    resource_type: str = ""
    resource_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.source = "audit"
