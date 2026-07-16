"""Analysis reports produced by the Analyst Agent."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...database.base import Base, _utcnow


class IntelligenceReport(Base):
    __tablename__ = "intelligence_reports"

    __table_args__ = (
        CheckConstraint("importance_score >= 0 AND importance_score <= 10", name="chk_report_score_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    importance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    article_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_runs.id"), nullable=True)
    generated_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    agent_run = relationship("AgentRun", back_populates="reports", foreign_keys="IntelligenceReport.agent_run_id")
