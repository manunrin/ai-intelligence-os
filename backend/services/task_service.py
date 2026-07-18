"""Task business logic service."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..events.event import AuditAction, AuditLogEvent
from ..repositories.task_repository import TaskRepository
from ..schemas.task_create import TaskCreate, TaskUpdate

logger = logging.getLogger(__name__)


class TaskService:
    """Business logic for task operations."""

    def __init__(self, session: AsyncSession, event_publisher=None) -> None:
        self._repo = TaskRepository(session)
        self._publisher = event_publisher

    async def list_tasks(
        self, offset: int = 0, limit: int = 20, user_id: uuid.UUID | None = None
    ) -> list[dict[str, Any]]:
        """Return paginated tasks filtered by user_id if provided."""
        if user_id is not None:
            tasks = await self._repo.list_by_user(user_id, offset=offset, limit=limit)
        else:
            tasks = await self._repo.list_all(offset=offset, limit=limit)
        return [self._to_dict(t) for t in tasks]

    async def get_task(
        self, task_id: str, user_id: uuid.UUID | None = None
    ) -> dict[str, Any] | None:
        """Return a single task by ID if owned by user_id, or None."""
        task = await self._repo.get_by_id(uuid.UUID(task_id))
        if task is None or task.user_id != user_id:
            return None
        return self._to_dict(task)

    async def create_task(self, data: TaskCreate, user_id: uuid.UUID) -> dict[str, Any]:
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
            "user_id": user_id,
        }
        if data.due_date is not None:
            kwargs["due_date"] = datetime.fromisoformat(data.due_date).replace(tzinfo=timezone.utc)
        task = await self._repo.create(**kwargs)
        await self._publish_audit(AuditAction.CREATE, str(task.id), user_id=user_id)
        return self._to_dict(task)

    async def update_task(
        self, task_id: str, data: TaskUpdate, user_id: uuid.UUID | None = None
    ) -> dict[str, Any] | None:
        """Update an existing task if owned by user_id. Returns None if not found."""
        existing = await self._repo.get_by_id(uuid.UUID(task_id))
        if existing is None or existing.user_id != user_id:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for uuid_field in ("agent_run_id", "knowledge_item_id"):
            if uuid_field in update_data and update_data[uuid_field] is not None:
                update_data[uuid_field] = uuid.UUID(update_data[uuid_field])
        if "due_date" in update_data and update_data["due_date"] is not None:
            update_data["due_date"] = datetime.fromisoformat(update_data["due_date"]).replace(tzinfo=timezone.utc)
        update_data["updated_at"] = datetime.now(timezone.utc)
        updated = await self._repo.update(uuid.UUID(task_id), **update_data)
        if updated is not None:
            await self._publish_audit(AuditAction.UPDATE, task_id, user_id=user_id)
        return self._to_dict(updated)

    async def delete_task(self, task_id: str, user_id: uuid.UUID | None = None) -> bool:
        """Delete a task by ID if owned by user_id. Returns True if deleted."""
        existing = await self._repo.get_by_id(uuid.UUID(task_id))
        if existing is None or existing.user_id != user_id:
            return False
        success = await self._repo.delete(uuid.UUID(task_id))
        if success:
            await self._publish_audit(AuditAction.DELETE, task_id, user_id=user_id)
        return success

    async def _publish_audit(self, action: AuditAction, resource_id: str, *, user_id: uuid.UUID | None = None) -> None:
        if self._publisher is None:
            return
        try:
            from ..context_vars import ip_address as _ip_ctx, user_agent as _ua_ctx
            await self._publisher.publish(AuditLogEvent(
                action=action,
                resource_type="task",
                resource_id=uuid.UUID(resource_id),
                user_id=user_id,
                ip_address=_ip_ctx.get(),
                user_agent=_ua_ctx.get(),
                metadata={"resource_id": resource_id},
            ))
        except Exception:
            logger.error("Failed to publish audit event for %s task %s", action.value, resource_id, exc_info=True)

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
            "user_id": str(task.user_id) if task.user_id else None,
        }
