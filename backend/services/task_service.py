"""Task business logic service."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.task_repository import TaskRepository


class TaskService:
    """Business logic for task operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = TaskRepository(session)

    async def list_tasks(self, offset: int = 0, limit: int = 20) -> list[dict[str, Any]]:
        """Return paginated tasks as dicts for response serialization."""
        tasks = await self._repo.list_all(offset=offset, limit=limit)
        return [self._to_dict(t) for t in tasks]

    @staticmethod
    def _to_dict(task: Any) -> dict[str, Any]:
        """Convert ORM model to serializable dict."""
        return {
            "id": str(task.id),
            "title": task.title,
            "description": task.description,
            "priority": task.priority,
            "status": task.status,
            "dependency": [],
            "created_at": task.created_at.isoformat() if task.created_at else None,
        }
