"""Task business logic service."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.task_repository import TaskRepository
from ..schemas.task_create import TaskCreate, TaskUpdate


class TaskService:
    """Business logic for task operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = TaskRepository(session)

    async def list_tasks(self, offset: int = 0, limit: int = 20) -> list[dict[str, Any]]:
        """Return paginated tasks as dicts for response serialization."""
        tasks = await self._repo.list_all(offset=offset, limit=limit)
        return [self._to_dict(t) for t in tasks]

    async def get_task(self, task_id: str) -> dict[str, Any] | None:
        """Return a single task by ID, or None if not found."""
        task = await self._repo.get_by_id(uuid.UUID(task_id))
        if task is None:
            return None
        return self._to_dict(task)

    async def create_task(self, data: TaskCreate) -> dict[str, Any]:
        """Create and persist a new task from validated schema data."""
        now = datetime.now(timezone.utc)
        kwargs: dict[str, Any] = {
            "title": data.title,
            "description": data.description,
            "priority": data.priority,
            "status": data.status,
            "external_id": data.external_id,
            "external_url": data.external_url,
            "agent_run_id": uuid.UUID(data.agent_run_id) if data.agent_run_id else None,
            "knowledge_item_id": uuid.UUID(data.knowledge_item_id) if data.knowledge_item_id else None,
            "created_at": now,
            "updated_at": now,
        }
        if data.due_date is not None:
            kwargs["due_date"] = datetime.fromisoformat(data.due_date).replace(tzinfo=timezone.utc)
        task = await self._repo.create(**kwargs)
        return self._to_dict(task)

    async def update_task(self, task_id: str, data: TaskUpdate) -> dict[str, Any] | None:
        """Update an existing task. Returns None if not found."""
        existing = await self._repo.get_by_id(uuid.UUID(task_id))
        if existing is None:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for uuid_field in ("agent_run_id", "knowledge_item_id"):
            if uuid_field in update_data and update_data[uuid_field] is not None:
                update_data[uuid_field] = uuid.UUID(update_data[uuid_field])
        if "due_date" in update_data and update_data["due_date"] is not None:
            update_data["due_date"] = datetime.fromisoformat(update_data["due_date"]).replace(tzinfo=timezone.utc)
        update_data["updated_at"] = datetime.now(timezone.utc)
        updated = await self._repo.update(uuid.UUID(task_id), **update_data)
        return self._to_dict(updated)

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task by ID. Returns True if deleted."""
        return await self._repo.delete(uuid.UUID(task_id))

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
