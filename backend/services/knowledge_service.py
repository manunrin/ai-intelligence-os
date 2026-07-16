"""Knowledge item business logic service."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.knowledge_repository import KnowledgeItemRepository
from ..schemas.knowledge_create import KnowledgeItemCreate, KnowledgeItemUpdate


class KnowledgeService:
    """Business logic for knowledge operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = KnowledgeItemRepository(session)

    async def list_knowledge_items(self, offset: int = 0, limit: int = 20) -> list[dict[str, Any]]:
        """Return paginated knowledge items as dicts for response serialization."""
        items = await self._repo.list_all(offset=offset, limit=limit)
        return [self._to_dict(item) for item in items]

    async def get_knowledge_item(self, item_id: str) -> dict[str, Any] | None:
        """Return a single knowledge item by ID, or None if not found."""
        item = await self._repo.get_by_id(uuid.UUID(item_id))
        if item is None:
            return None
        return self._to_dict(item)

    async def create_knowledge_item(self, data: KnowledgeItemCreate) -> dict[str, Any]:
        """Create and persist a new knowledge item from validated schema data."""
        kwargs: dict[str, Any] = {
            "title": data.title,
            "content": data.content,
            "kind": data.kind,
            "article_id": uuid.UUID(data.article_id) if data.article_id else None,
            "tags": data.tags,
            "created_at": datetime.now(timezone.utc),
        }
        item = await self._repo.create(**kwargs)
        return self._to_dict(item)

    async def update_knowledge_item(
        self, item_id: str, data: KnowledgeItemUpdate
    ) -> dict[str, Any] | None:
        """Update an existing knowledge item. Returns None if not found."""
        existing = await self._repo.get_by_id(uuid.UUID(item_id))
        if existing is None:
            return None
        update_data = data.model_dump(exclude_unset=True)
        updated = await self._repo.update(uuid.UUID(item_id), **update_data)
        return self._to_dict(updated)

    async def delete_knowledge_item(self, item_id: str) -> bool:
        """Delete a knowledge item by ID. Returns True if deleted."""
        return await self._repo.delete(uuid.UUID(item_id))

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
        }
