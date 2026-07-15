"""Article ingestion service — fetch, deduplicate, persist."""

from __future__ import annotations

import hashlib
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from ...connectors.base import RawArticle
from ...database.models.article import Article
from ...events.event import ArticleCreatedEvent

logger = logging.getLogger(__name__)


def _url_hash(url: str) -> str:
    """Generate a short hash for deduplication by URL."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


class IngestionService:
    """Orchestrates article ingestion from connectors through deduplication to persistence.

    Pipeline:
        Connector.run() → RawArticles → Deduplicate → Repository.save() → Publish Event
    """

    def __init__(self, session: AsyncSession, event_publisher=None) -> None:
        self._session = session
        self._publisher = event_publisher

    async def ingest(self, connector, batch_size: int = 50) -> dict[str, int]:
        """Run a connector's full ingestion pipeline.

        Args:
            connector: A SourceConnector instance.
            batch_size: Maximum articles to process per call.

        Returns:
            Counts: {"fetched": N, "deduplicated": N, "saved": N}
        """
        articles = await connector.run()
        stats = {"fetched": len(articles), "deduplicated": 0, "saved": 0}

        existing_urls = await self._get_existing_urls()

        saved_ids: list[UUID] = []

        for article in articles[:batch_size]:
            url_hash = _url_hash(article.url)
            if url_hash in existing_urls:
                stats["deduplicated"] += 1
                continue

            result = await self._save_article(article)
            if result is not None:
                stats["saved"] += 1
                saved_ids.append(result)
                existing_urls.add(url_hash)

        await self._session.commit()

        # Publish events for all newly saved articles
        for aid in saved_ids:
            if self._publisher:
                await self._publisher.publish(ArticleCreatedEvent(article_id=aid))

        logger.info(
            "Ingestion complete: %s fetched, %s deduplicated, %s saved",
            stats["fetched"], stats["deduplicated"], stats["saved"],
        )
        return stats

    async def _get_existing_urls(self) -> set[str]:
        """Return hashes of already-persisted article URLs."""
        stmt = Article.__table__.select().columns(Article.metadata_)
        result = await self._session.execute(stmt)
        hashes = set()
        for row in result.all():
            meta = row.metadata_ or {}
            uh = meta.get("url_hash")
            if uh:
                hashes.add(uh)
        return hashes

    async def _save_article(self, article: RawArticle) -> UUID | None:
        """Save a RawArticle as an ORM Article entity.

        Returns:
            The article UUID on success, or None on failure.
        """
        try:
            url_hash = _url_hash(article.url)
            orm_article = Article(
                title=article.title,
                summary=article.summary,
                content=article.content,
                language=article.language,
                published_at=article.published_at,
                status="raw",
                metadata_={**article.metadata_, "url": article.url, "url_hash": url_hash},
            )
            self._session.add(orm_article)
            await self._session.flush()
            return orm_article.id
        except Exception as exc:
            logger.error("Failed to save article '%s': %s", article.title, exc)
            return None
