"""Autonomous Intelligence Job Service — orchestrates end-to-end workflow."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from backend.connectors.base import RawArticle, SourceConnector
from backend.database.models.article import Article
from backend.events.event import ArticleCreatedEvent
from backend.events.publisher import EventPublisher
from backend.services.ingestion.service import IngestionService

logger = logging.getLogger(__name__)


class AutonomousIntelligenceJob:
    """Runs the full autonomous intelligence cycle across all configured sources.

    Flow:
        1. Ingest articles from all connectors
        2. For each new article, run the autonomous pipeline
           (research → analyst → translator → knowledge → project manager → notification)
        3. Persist results and update article statuses
    """

    def __init__(
        self,
        session: AsyncSession,
        event_publisher: EventPublisher | None = None,
        mcp_registry: Any = None,
        notion_database_id: str = "",
        asana_project_id: str = "",
    ) -> None:
        self._session = session
        self._event_publisher = event_publisher
        self._mcp_registry = mcp_registry
        self._notion_database_id = notion_database_id
        self._asana_project_id = asana_project_id

    async def run(
        self,
        connectors: list[SourceConnector],
    ) -> dict[str, Any]:
        """Execute the full autonomous intelligence cycle.

        Args:
            connectors: List of SourceConnector instances to process.

        Returns:
            Aggregated stats dict.
        """
        # Import here to avoid circular imports at module level
        from backend.pipelines.article_pipeline import ArticlePipeline
        from backend.workflows.autonomous_intelligence import compile_autonomous_intelligence

        stats = {
            "articles_fetched": 0,
            "articles_saved": 0,
            "articles_processed": 0,
            "knowledge_items": 0,
            "notion_pages_created": 0,
            "asana_tasks_created": 0,
        }

        # Phase 1: Ingest all articles from all connectors
        for connector in connectors:
            logger.info("Fetching from connector '%s'...", connector.name)
            ingestion = IngestionService(
                self._session, event_publisher=self._event_publisher
            )
            ingest_result = await ingestion.ingest(connector)
            stats["articles_fetched"] += ingest_result["fetched"]
            stats["articles_saved"] += ingest_result["saved"]

        if stats["articles_saved"] == 0:
            logger.info("No new articles to process — exiting")
            return stats

        # Phase 2: Run autonomous pipeline on each new article
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

                    # Phase 3: Run autonomous workflow with MCP integration
                    aw_stats = await self._run_autonomous_workflow(
                        article, pipeline_result
                    )
                    stats["notion_pages_created"] += aw_stats.get("notion_pages", 0)
                    stats["asana_tasks_created"] += aw_stats.get("asana_tasks", 0)

                    logger.info(
                        "Processed article '%s': %d knowledge items, %d MCP ops",
                        article.title,
                        len(kids),
                        aw_stats.get("total_mcp_ops", 0),
                    )
            except Exception as exc:
                logger.error(
                    "Autonomous pipeline failed for article '%s': %s",
                    article.title,
                    exc,
                    exc_info=True,
                )

        await self._session.commit()
        return stats

    async def _run_autonomous_workflow(
        self,
        article: Article,
        pipeline_result: dict[str, Any],
    ) -> dict[str, int]:
        """Run the autonomous workflow (operations stages) for one article."""
        from backend.workflows.autonomous_intelligence import compile_autonomous_intelligence

        try:
            app = compile_autonomous_intelligence(
                mcp_registry=self._mcp_registry,
                notion_database_id=self._notion_database_id,
                asana_project_id=self._asana_project_id,
            )

            initial_state = {
                "article_id": str(article.id),
                "topic": article.title,
                "content": article.summary or article.content[:500],
                "focus_areas": self._extract_tags(article),
                "tags": self._extract_tags(article),
                "source": article.metadata_.get("source", "rss"),
                "source_language": article.language,
            }

            final_state = app.invoke(initial_state)

            knowledge = final_state.get("knowledge_result", {}) or {}
            pm_result = final_state.get("project_plan_result", {}) or {}

            return {
                "notion_pages": 1 if knowledge.get("notion_page_id") else 0,
                "asana_tasks": len(pm_result.get("asana_task_ids", [])),
                "total_mcp_ops": (
                    1 if knowledge.get("notion_page_id") else 0
                )
                + len(pm_result.get("asana_task_ids", [])),
            }
        except Exception as exc:
            logger.warning("Autonomous workflow failed for '%s': %s", article.title, exc)
            return {"notion_pages": 0, "asana_tasks": 0, "total_mcp_ops": 0}

    @staticmethod
    def _extract_tags(article: Article) -> list[str]:
        meta = article.metadata_ or {}
        tags = meta.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]
        return list(tags)[:5]
