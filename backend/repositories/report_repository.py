"""Intelligence report repository."""

from typing import Any

from sqlalchemy import select

from ..database.models import IntelligenceReport
from .base_repository import BaseRepository


class IntelligenceReportRepository(BaseRepository[IntelligenceReport]):
    @property
    def model(self) -> type[IntelligenceReport]:
        return IntelligenceReport

    async def list_by_agent_run(self, agent_run_id: Any) -> list[IntelligenceReport]:
        stmt = select(IntelligenceReport).where(
            IntelligenceReport.agent_run_id == agent_run_id
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_user(self, user_id: Any, offset: int = 0, limit: int = 20) -> list[IntelligenceReport]:
        stmt = select(IntelligenceReport).where(IntelligenceReport.user_id == user_id).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
