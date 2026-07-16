"""Article business logic service."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.article_repository import ArticleRepository
from ..schemas.article_create import ArticleCreate, ArticleUpdate


class ArticleService:
    """Business logic for article operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = ArticleRepository(session)

    async def list_articles(self, offset: int = 0, limit: int = 20) -> list[dict[str, Any]]:
        """Return paginated articles as dicts for response serialization."""
        articles = await self._repo.list_all(offset=offset, limit=limit)
        return [self._to_dict(a) for a in articles]

    async def count_articles(self) -> int:
        """Return total article count."""
        return await self._repo.count()

    async def get_article(self, article_id: str) -> dict[str, Any] | None:
        """Return a single article by ID, or None if not found."""
        article = await self._repo.get_by_id(uuid.UUID(article_id))
        if article is None:
            return None
        return self._to_dict(article)

    async def create_article(self, data: ArticleCreate) -> dict[str, Any]:
        """Create and persist a new article from validated schema data."""
        now = datetime.now(timezone.utc)
        kwargs = {
            "title": data.title,
            "summary": data.summary,
            "content": data.content,
            "source_id": uuid.UUID(data.source_id),
            "language": data.language,
            "status": data.status,
            "metadata_": data.metadata_ or {},
            "fetched_at": now,
            "created_at": now,
            "updated_at": now,
        }
        article = await self._repo.create(**kwargs)
        return self._to_dict(article)

    async def update_article(self, article_id: str, data: ArticleUpdate) -> dict[str, Any] | None:
        """Update an existing article. Returns None if not found."""
        existing = await self._repo.get_by_id(uuid.UUID(article_id))
        if existing is None:
            return None
        update_data = data.model_dump(exclude_unset=True)
        if "source_id" in update_data and update_data["source_id"] is not None:
            update_data["source_id"] = uuid.UUID(update_data["source_id"])
        if "metadata_" in update_data and update_data["metadata_"] is not None:
            pass  # already a dict
        elif "metadata_" in update_data:
            del update_data["metadata_"]
        if "article_id" in update_data:
            del update_data["article_id"]
        updated = await self._repo.update(uuid.UUID(article_id), **update_data)
        return self._to_dict(updated)

    async def delete_article(self, article_id: str) -> bool:
        """Delete an article by ID. Returns True if deleted."""
        return await self._repo.delete(uuid.UUID(article_id))

    @staticmethod
    def _to_dict(article: Any) -> dict[str, Any]:
        """Convert ORM model to serializable dict."""
        return {
            "id": str(article.id),
            "title": article.title,
            "summary": article.summary,
            "content": article.content,
            "url": article.metadata_.get("url") if article.metadata_ else None,
            "source": article.source.name if article.source else "",
            "language": article.language,
            "tags": article.metadata_.get("tags", []) if article.metadata_ else [],
            "status": article.status,
            "fetched_at": article.fetched_at.isoformat() if article.fetched_at else None,
            "published_at": article.published_at.isoformat() if article.published_at else None,
        }
