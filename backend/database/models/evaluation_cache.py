"""Evaluation cache for deduplicating repeated evaluation requests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import CHAR, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ...database.base import Base


class EvaluationCache(Base):
    __tablename__ = "evaluation_cache"

    id: Mapped[uuid.UUID] = mapped_column(
        CHAR(32), primary_key=True, default=lambda: uuid.uuid4().hex
    )
    content_hash: Mapped[str] = mapped_column(
        CHAR(64), nullable=False, unique=True, index=True
    )
    pipeline_type: Mapped[str] = mapped_column(String(32), nullable=False)
    score: Mapped[float] = mapped_column(nullable=False)
    criteria: Mapped[dict] = mapped_column(JSONB, nullable=False)
    evaluator_notes: Mapped[str | None] = mapped_column(nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(128), nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
