"""APScheduler-based job scheduler."""

from __future__ import annotations

import logging
from typing import Any

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
except ImportError:
    AsyncIOScheduler = None  # type: ignore
    CronTrigger = None  # type: ignore

from ...connectors.base import SourceConnector
from .daily_news_job import daily_news_job

logger = logging.getLogger(__name__)


class JobScheduler:
    """Manages scheduled ingestion jobs using APScheduler."""

    def __init__(self) -> None:
        self._scheduler: Any = None
        self._jobs: dict[str, dict[str, Any]] = {}

    def start(self) -> None:
        """Start the scheduler."""
        if AsyncIOScheduler is None:
            logger.warning("APScheduler not installed — scheduled jobs disabled")
            return
        self._scheduler = AsyncIOScheduler()
        self._scheduler.start()
        logger.info("JobScheduler started")

    def stop(self) -> None:
        """Shutdown the scheduler."""
        if self._scheduler:
            self._scheduler.shutdown()
            logger.info("JobScheduler stopped")

    def add_daily_news_job(
        self,
        connector: SourceConnector,
        cron_expression: str = "0 8 * * *",
        job_id: str = "daily_news",
    ) -> None:
        """Schedule a daily news ingestion job.

        Args:
            connector: The connector to run.
            cron_expression: Cron schedule (default: 8:00 AM daily).
            job_id: Unique identifier for this job.
        """
        if not self._scheduler:
            self.start()

        trigger = CronTrigger.from_crontab(cron_expression)
        self._scheduler.add_job(
            daily_news_job,
            trigger=trigger,
            args=[connector],
            id=job_id,
            replace_existing=True,
        )
        self._jobs[job_id] = {
            "connector_name": connector.name,
            "cron": cron_expression,
        }
        logger.info("Added job '%s': %s (%s)", job_id, connector.name, cron_expression)

    def list_jobs(self) -> dict[str, dict[str, Any]]:
        """Return registered job configurations."""
        return dict(self._jobs)
