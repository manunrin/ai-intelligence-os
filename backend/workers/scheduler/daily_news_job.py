"""Daily news ingestion job — runs via APScheduler."""

from __future__ import annotations

import logging

from ...connectors.base import SourceConnector
from ...services.ingestion.service import IngestionService
from ...database.connection import get_session

logger = logging.getLogger(__name__)


async def daily_news_job(connector: SourceConnector) -> dict:
    """Scheduled job that runs a connector through the full ingestion pipeline.

    This is the entry point called by APScheduler on a cron schedule.
    It creates a DB session, runs ingestion, and commits.

    Args:
        connector: The SourceConnector to execute (e.g. OpenAIBlogRssConnector).

    Returns:
        Ingestion stats dict.
    """
    async for session in get_session():
        service = IngestionService(session)
        return await service.ingest(connector)
    return {"fetched": 0, "deduplicated": 0, "saved": 0}
