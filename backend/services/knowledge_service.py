"""Knowledge item business logic service."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..events.event import AuditAction, AuditLogEvent
from ..repositories.knowledge_repository import KnowledgeItemRepository
from ..schemas.knowledge_create import KnowledgeItemCreate, KnowledgeItemUpdate

logger = logging.getLogger(__name__)


class KnowledgeItemService:
    """Business logic for knowledge item CRUD operations (API layer)."""

    def __init__(self, session: AsyncSession, event_publisher=None) -> None:
        self._repo = KnowledgeItemRepository(session)
        self._publisher = event_publisher

    async def list_knowledge_items(
        self, offset: int = 0, limit: int = 20, user_id: uuid.UUID | None = None
    ) -> list[dict[str, Any]]:
        """Return paginated knowledge items filtered by user_id if provided."""
        if user_id is not None:
            items = await self._repo.list_by_user(user_id, offset=offset, limit=limit)
        else:
            items = await self._repo.list_all(offset=offset, limit=limit)
        return [self._to_dict(item) for item in items]

    async def get_knowledge_item(
        self, item_id: str, user_id: uuid.UUID | None = None
    ) -> dict[str, Any] | None:
        """Return a single knowledge item by ID if owned by user_id, or None."""
        item = await self._repo.get_by_id(uuid.UUID(item_id))
        if item is None or item.user_id != user_id:
            return None
        return self._to_dict(item)

    async def create_knowledge_item(self, data: KnowledgeItemCreate, user_id: uuid.UUID) -> dict[str, Any]:
        """Create and persist a new knowledge item from validated schema data."""
        kwargs: dict[str, Any] = {
            "title": data.title,
            "content": data.content,
            "kind": data.kind,
            "article_id": uuid.UUID(data.article_id) if data.article_id else None,
            "tags": data.tags,
            "created_at": datetime.now(timezone.utc),
            "user_id": user_id,
        }
        item = await self._repo.create(**kwargs)
        await self._publish_audit(AuditAction.CREATE, str(item.id), user_id=user_id)
        return self._to_dict(item)

    async def update_knowledge_item(
        self, item_id: str, data: KnowledgeItemUpdate, user_id: uuid.UUID | None = None
    ) -> dict[str, Any] | None:
        """Update an existing knowledge item if owned by user_id. Returns None if not found."""
        existing = await self._repo.get_by_id(uuid.UUID(item_id))
        if existing is None or existing.user_id != user_id:
            return None
        update_data = data.model_dump(exclude_unset=True)
        updated = await self._repo.update(uuid.UUID(item_id), **update_data)
        if updated is not None:
            await self._publish_audit(AuditAction.UPDATE, item_id, user_id=user_id)
        return self._to_dict(updated)

    async def delete_knowledge_item(
        self, item_id: str, user_id: uuid.UUID | None = None
    ) -> bool:
        """Delete a knowledge item by ID if owned by user_id. Returns True if deleted."""
        existing = await self._repo.get_by_id(uuid.UUID(item_id))
        if existing is None or existing.user_id != user_id:
            return False
        success = await self._repo.delete(uuid.UUID(item_id))
        if success:
            await self._publish_audit(AuditAction.DELETE, item_id, user_id=user_id)
        return success

    async def _publish_audit(self, action: AuditAction, resource_id: str, *, user_id: uuid.UUID | None = None) -> None:
        if self._publisher is None:
            return
        try:
            from ..context_vars import ip_address as _ip_ctx, user_agent as _ua_ctx
            await self._publisher.publish(AuditLogEvent(
                action=action,
                resource_type="knowledge_item",
                resource_id=uuid.UUID(resource_id),
                user_id=user_id,
                ip_address=_ip_ctx.get(),
                user_agent=_ua_ctx.get(),
                metadata={"resource_id": resource_id},
            ))
        except Exception:
            logger.error("Failed to publish audit event for %s knowledge item %s", action.value, resource_id, exc_info=True)

    @staticmethod
    def _to_dict(item: Any) -> dict[str, Any]:
        """Convert ORM model to serializable dict."""
        return {
            "id": str(item.id),
            "title": item.title,
            "content": item.content,
            "kind": item.kind,
            "article_id": str(item.article_id) if item.article_id else None,
            "tags": item.tags,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "user_id": str(item.user_id) if item.user_id else None,
        }
