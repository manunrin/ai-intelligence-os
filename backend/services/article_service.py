"""Article business logic service."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..events.event import AuditAction, AuditLogEvent
from ..repositories.article_repository import ArticleRepository
from ..schemas.article_create import ArticleCreate, ArticleUpdate

logger = logging.getLogger(__name__)


class ArticleService:
    """Business logic for article operations."""

    def __init__(self, session: AsyncSession, event_publisher=None) -> None:
        self._repo = ArticleRepository(session)
        self._publisher = event_publisher

    async def list_articles(
        self, offset: int = 0, limit: int = 20, user_id: uuid.UUID | None = None
    ) -> list[dict[str, Any]]:
        """Return paginated articles filtered by user_id if provided."""
        if user_id is not None:
            articles = await self._repo.list_by_user(user_id, offset=offset, limit=limit)
        else:
            articles = await self._repo.list_all(offset=offset, limit=limit)
        return [self._to_dict(a) for a in articles]

    async def count_articles(self) -> int:
        """Return total article count."""
        return await self._repo.count()

    async def get_article(
        self, article_id: str, user_id: uuid.UUID | None = None
    ) -> dict[str, Any] | None:
        """Return a single article by ID if owned by user_id, or None."""
        article = await self._repo.get_by_id(uuid.UUID(article_id))
        if article is None:
            return None
        if article.user_id != user_id:
            return None
        return self._to_dict(article)

    async def create_article(self, data: ArticleCreate, user_id: uuid.UUID) -> dict[str, Any]:
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
            "user_id": user_id,
        }
        article = await self._repo.create(**kwargs)
        await self._publish_audit(AuditAction.CREATE, str(article.id), user_id=user_id)
        return self._to_dict(article)

    async def update_article(
        self, article_id: str, data: ArticleUpdate, user_id: uuid.UUID | None = None
    ) -> dict[str, Any] | None:
        """Update an existing article if owned by user_id. Returns None if not found."""
        existing = await self._repo.get_by_id(uuid.UUID(article_id))
        if existing is None or existing.user_id != user_id:
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
        await self._publish_audit(AuditAction.UPDATE, article_id, user_id=user_id)
        return self._to_dict(updated)

    async def delete_article(self, article_id: str, user_id: uuid.UUID | None = None) -> bool:
        """Delete an article by ID if owned by user_id. Returns True if deleted."""
        existing = await self._repo.get_by_id(uuid.UUID(article_id))
        if existing is None or existing.user_id != user_id:
            return False
        success = await self._repo.delete(uuid.UUID(article_id))
        if success:
            await self._publish_audit(AuditAction.DELETE, article_id, user_id=user_id)
        return success

    async def _publish_audit(self, action: AuditAction, resource_id: str, *, user_id: uuid.UUID | None = None) -> None:
        if self._publisher is None:
            return
        try:
            from ..context_vars import ip_address as _ip_ctx, user_agent as _ua_ctx
            await self._publisher.publish(AuditLogEvent(
                action=action,
                resource_type="article",
                resource_id=uuid.UUID(resource_id),
                user_id=user_id,
                ip_address=_ip_ctx.get(),
                user_agent=_ua_ctx.get(),
                metadata={"resource_id": resource_id},
            ))
        except Exception:
            logger.error("Failed to publish audit event for %s article %s", action.value, resource_id, exc_info=True)

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
            "user_id": str(article.user_id) if article.user_id else None,
        }
