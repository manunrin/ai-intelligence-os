"""Knowledge item business logic service."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.knowledge_repository import KnowledgeItemRepository


class KnowledgeService:
    """Business logic for knowledge operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = KnowledgeItemRepository(session)

    async def list_knowledge_items(self, offset: int = 0, limit: int = 20) -> list[dict[str, Any]]:
        """Return paginated knowledge items as dicts for response serialization."""
        items = await self._repo.list_all(offset=offset, limit=limit)
        return [self._to_dict(item) for item in items]

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
