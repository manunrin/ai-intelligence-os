"""Article business logic service."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.article_repository import ArticleRepository


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
