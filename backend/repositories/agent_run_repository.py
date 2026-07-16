"""Agent run repository."""

from typing import Any

from sqlalchemy import select

from ..database.models import AgentRun
from .base_repository import BaseRepository


class AgentRunRepository(BaseRepository[AgentRun]):
    @property
    def model(self) -> type[AgentRun]:
        return AgentRun

    async def list_by_agent(self, agent_id: Any) -> list[AgentRun]:
        stmt = select(AgentRun).where(AgentRun.agent_id == agent_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_workflow(self, workflow_id: Any) -> list[AgentRun]:
        stmt = select(AgentRun).where(AgentRun.workflow_id == workflow_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_status(self, status: str) -> list[AgentRun]:
        stmt = select(AgentRun).where(AgentRun.status == status)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
