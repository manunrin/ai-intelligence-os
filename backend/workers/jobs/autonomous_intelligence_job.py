"""Scheduler extension — wires autonomous intelligence into the daily job."""

from __future__ import annotations

import logging

from backend.connectors.base import SourceConnector
from backend.database.connection import get_session
from backend.events.publisher import EventPublisher
from backend.workers.jobs.service import AutonomousIntelligenceJob

logger = logging.getLogger(__name__)


async def daily_intelligence_job(
    connectors: list[SourceConnector],
    mcp_registry=None,
    notion_database_id: str = "",
    asana_project_id: str = "",
) -> dict:
    """Scheduled job that runs the full autonomous intelligence pipeline.

    Runs ingestion, then for each new article executes the full autonomous
    workflow (research → analyst → translator → knowledge → project manager → notification).

    Args:
        connectors: List of SourceConnector instances.
        mcp_registry: MCPRegistry wired with Notion/Asana/Browser servers.
        notion_database_id: Target Notion database for knowledge sync.
        asana_project_id: Target Asana project for task sync.

    Returns:
        Aggregated stats dict.
    """
    event_publisher = EventPublisher()
    async for session in get_session():
        job = AutonomousIntelligenceJob(
            session,
            event_publisher=event_publisher,
            mcp_registry=mcp_registry,
            notion_database_id=notion_database_id,
            asana_project_id=asana_project_id,
        )
        return await job.run(connectors)
    return {"articles_fetched": 0, "articles_saved": 0, "articles_processed": 0, "knowledge_items": 0}
