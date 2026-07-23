"""Repository for agent evaluation persistence."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import AgentEvaluation


class AgentEvaluationRepository:
    """CRUD operations for agent quality evaluations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **kwargs: Any) -> AgentEvaluation:
        instance = AgentEvaluation(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def get_by_run_id(self, run_id: uuid.UUID) -> AgentEvaluation | None:
        stmt = select(AgentEvaluation).where(
            AgentEvaluation.agent_run_id == run_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_run_ids(self, run_ids: list[uuid.UUID]) -> list[AgentEvaluation]:
        if not run_ids:
            return []
        stmt = select(AgentEvaluation).where(
            AgentEvaluation.agent_run_id.in_(run_ids)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
