"""Agent stage progress repository."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from ..database.models import AgentStageProgress
from .base_repository import BaseRepository


class AgentStageProgressRepository(BaseRepository[AgentStageProgress]):
    @property
    def model(self) -> type[AgentStageProgress]:
        return AgentStageProgress

    async def get_by_run_id(self, run_id: uuid.UUID) -> list[AgentStageProgress]:
        stmt = select(AgentStageProgress).where(
            AgentStageProgress.agent_run_id == run_id
        ).order_by(AgentStageProgress.stage_order)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_stage(
        self,
        agent_run_id: uuid.UUID,
        stage_name: str,
        stage_order: int,
        status: str,
        input_summary: dict | None = None,
    ) -> AgentStageProgress:
        record = AgentStageProgress(
            id=uuid.uuid4(),
            agent_run_id=agent_run_id,
            stage_name=stage_name,
            stage_order=stage_order,
            status=status,
            input_summary=input_summary,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def update_stage(
        self,
        run_id: uuid.UUID,
        stage_name: str,
        *,
        status: str | None = None,
        output_summary: dict | None = None,
        error_message: str | None = None,
        duration_ms: int | None = None,
    ) -> AgentStageProgress | None:
        stmt = select(AgentStageProgress).where(
            AgentStageProgress.agent_run_id == run_id,
            AgentStageProgress.stage_name == stage_name,
        )
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        if record is None:
            return None
        if status is not None:
            record.status = status
        if output_summary is not None:
            record.output_summary = output_summary
        if error_message is not None:
            record.error_message = error_message
        if duration_ms is not None:
            record.duration_ms = duration_ms
        record.finished_at = _utcnow()
        await self.session.commit()
        await self.session.refresh(record)
        return record


def _utcnow():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)
