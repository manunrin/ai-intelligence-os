"""Task repository."""

from typing import Any

from sqlalchemy import select

from ..database.models import Task
from .base_repository import BaseRepository


class TaskRepository(BaseRepository[Task]):
    @property
    def model(self) -> type[Task]:
        return Task

    async def list_by_status(self, status: str) -> list[Task]:
        stmt = select(Task).where(Task.status == status)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_priority(self, priority: str) -> list[Task]:
        stmt = select(Task).where(Task.priority == priority)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_knowledge_item(self, knowledge_item_id: Any) -> list[Task]:
        stmt = select(Task).where(Task.knowledge_item_id == knowledge_item_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
