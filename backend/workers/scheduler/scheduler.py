"""APScheduler-based job scheduler."""

from __future__ import annotations

import logging
from typing import Any

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
except ImportError:
    BackgroundScheduler = None  # type: ignore
    CronTrigger = None  # type: ignore

from ...connectors.base import SourceConnector
from .jobs.daily_intelligence_job import daily_intelligence_job

logger = logging.getLogger(__name__)


class JobScheduler:
    """Manages scheduled ingestion jobs using APScheduler."""

    def __init__(self) -> None:
        self._scheduler: Any = None
        self._jobs: dict[str, dict[str, Any]] = {}

    def start(self) -> None:
        """Start the scheduler."""
        if BackgroundScheduler is None:
            logger.warning("APScheduler not installed — scheduled jobs disabled")
            return
        self._scheduler = BackgroundScheduler()
        self._scheduler.start()
        logger.info("JobScheduler started (BackgroundScheduler)")

    def stop(self) -> None:
        """Shutdown the scheduler."""
        if self._scheduler:
            self._scheduler.shutdown()
            logger.info("JobScheduler stopped")

    def add_daily_news_job(
        self,
        connectors: list[SourceConnector],
        cron_expression: str = "0 8 * * *",
        job_id: str = "daily_intelligence",
    ) -> None:
        """Schedule a daily intelligence ingestion job.

        Args:
            connectors: List of SourceConnector instances to process.
            cron_expression: Cron schedule (default: 8:00 AM daily).
            job_id: Unique identifier for this job.
        """
        if not self._scheduler:
            self.start()

        trigger = CronTrigger.from_crontab(cron_expression)
        self._scheduler.add_job(
            daily_intelligence_job,
            trigger=trigger,
            args=[connectors],
            id=job_id,
            replace_existing=True,
        )
        names = [c.name for c in connectors]
        self._jobs[job_id] = {
            "connectors": names,
            "cron": cron_expression,
        }
        logger.info(
            "Added job '%s': %s (%s)",
            job_id,
            ", ".join(names),
            cron_expression,
        )

    def list_jobs(self) -> dict[str, dict[str, Any]]:
        """Return registered job configurations."""
        return dict(self._jobs)
