"""Individual agent execution instances."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...database.base import Base, _utcnow


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="running")
    input_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    output_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    stage: Mapped[str] = mapped_column(String(64), default="initializing")
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    agent = relationship("Agent", back_populates="runs", foreign_keys="AgentRun.agent_id")
    workflow = relationship("Workflow", back_populates="runs", foreign_keys="AgentRun.workflow_id")
    stages = relationship("AgentStageProgress", back_populates="run", cascade="all, delete-orphan")
    reports = relationship("IntelligenceReport", back_populates="agent_run", foreign_keys="IntelligenceReport.agent_run_id")
    tasks = relationship("Task", foreign_keys="Task.agent_run_id", back_populates="agent_run")
    user = relationship("User", back_populates="agent_runs")

    @property
    def duration(self) -> int | None:
        if self.started_at and self.finished_at:
            return int((self.finished_at - self.started_at).total_seconds() * 1000)
        return None
