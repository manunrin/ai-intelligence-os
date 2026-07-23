"""Quality evaluation results for completed agent runs."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...database.base import Base


class AgentEvaluation(Base):
    __tablename__ = "agent_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pipeline_type: Mapped[str] = mapped_column(String(32), nullable=False)
    score: Mapped[float] = mapped_column(nullable=False)
    criteria: Mapped[dict] = mapped_column(JSONB, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    run = relationship("AgentRun", back_populates="evaluations")
