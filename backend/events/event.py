"""Base event types and ArticleCreatedEvent."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


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

    @property
    def source(self) -> str:
        return "ingestion"
