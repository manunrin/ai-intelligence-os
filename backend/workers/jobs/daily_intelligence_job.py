"""Daily intelligence job — runs via APScheduler.

This is the entry point called by the scheduler on a cron schedule.
It orchestrates the full pipeline: fetch → ingest → research → analyze → translate → knowledge.
"""

from __future__ import annotations

import logging

from ...connectors.base import SourceConnector
from ...database.connection import get_session
from ...events.publisher import EventPublisher
from .service import DailyIntelligenceJob

logger = logging.getLogger(__name__)


async def daily_intelligence_job(connectors: list[SourceConnector]) -> dict:
    """Scheduled job that runs the full intelligence pipeline.

    Args:
        connectors: List of SourceConnector instances to process.

    Returns:
        Aggregated stats dict.
    """
    event_publisher = EventPublisher()
    async for session in get_session():
        job = DailyIntelligenceJob(session, event_publisher=event_publisher)
        return await job.run(connectors)
    return {"articles_fetched": 0, "articles_saved": 0, "articles_processed": 0, "knowledge_items": 0}
