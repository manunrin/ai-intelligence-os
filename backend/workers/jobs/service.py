"""Daily intelligence worker — end-to-end pipeline for all sources.

Flow:
    1. Fetch articles from all configured connectors via IngestionService
    2. For each newly saved article, run ArticlePipeline (research → analyze → translate)
    3. Persist results as KnowledgeItems
    4. Update article statuses

This is the entry point called by APScheduler or invoked manually.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...connectors.base import SourceConnector
from ...database.models.article import Article
from ...events.publisher import EventPublisher
from ...pipelines.article_pipeline import ArticlePipeline
from ...services.ingestion.service import IngestionService

logger = logging.getLogger(__name__)


class DailyIntelligenceJob:
    """Runs the full intelligence pipeline across all configured sources.

    Usage:
        job = DailyIntelligenceJob(session, event_publisher)
        result = await job.run(connectors=[openai_rss, github_rss])
    """

    def __init__(self, session: AsyncSession, event_publisher: EventPublisher | None = None) -> None:
        self._session = session
        self._event_publisher = event_publisher

    async def run(self, connectors: list[SourceConnector]) -> dict[str, Any]:
        """Execute the full daily intelligence cycle.

        Args:
            connectors: List of SourceConnector instances to process.

        Returns:
            Aggregated stats: {"articles_fetched": N, "articles_saved": N,
                               "articles_processed": N, "knowledge_items": N}
        """
        stats = {"articles_fetched": 0, "articles_saved": 0, "articles_processed": 0, "knowledge_items": 0}

        # Phase 1: Ingest all articles from all connectors
        for connector in connectors:
            logger.info("Fetching from connector '%s'...", connector.name)
            ingestion = IngestionService(self._session, event_publisher=self._event_publisher)
            ingest_result = await ingestion.ingest(connector)
            stats["articles_fetched"] += ingest_result["fetched"]
            stats["articles_saved"] += ingest_result["saved"]

        if stats["articles_saved"] == 0:
            logger.info("No new articles to process — exiting")
            return stats

        # Phase 2: Run intelligence pipeline on each new article
        stmt = (
            select(Article)
            .where(Article.status.in_(["raw", "analyzed"]))
            .order_by(Article.fetched_at.desc())
        )
        result = await self._session.execute(stmt)
        articles = result.scalars().all()

        for article in articles:
            try:
                pipeline = ArticlePipeline(self._session)
                pipeline_result = await pipeline.run(article.id)
                if "error" not in pipeline_result:
                    stats["articles_processed"] += 1
                    kids = pipeline_result.get("knowledge_ids", [])
                    stats["knowledge_items"] += len(kids)
                    logger.info(
                        "Processed article '%s': %d knowledge items",
                        article.title,
                        len(kids),
                    )
            except Exception as exc:
                logger.error(
                    "Pipeline failed for article '%s': %s",
                    article.title,
                    exc,
                    exc_info=True,
                )

        await self._session.commit()
        logger.info(
            "DailyIntelligenceJob complete: %d fetched, %d saved, %d processed, %d knowledge items",
            stats["articles_fetched"],
            stats["articles_saved"],
            stats["articles_processed"],
            stats["knowledge_items"],
        )
        return stats
