"""Scheduler service — manages scheduled job definitions and execution.

This service owns the ``scheduled_jobs`` table as the single source of truth.
APScheduler (AsyncIOScheduler) is used only as a fire-and-forget trigger: on
startup it re-registers every enabled job from the database, and when a job
fires it dispatches through :class:`AgentRuntimeService` so scheduled runs
follow the exact same path as user-submitted runs.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from croniter import croniter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ...config import get_settings
from ...database.models import ScheduledJob
from ...services.agent_runtime_service import AgentRuntimeService

logger = logging.getLogger(__name__)


def _utcnow():
    return datetime.now(timezone.utc)


_VALID_JOB_TYPES = {"intelligence", "autonomous"}


class SchedulerService:
    """Manage scheduled agent-job lifecycle and dispatch."""

    def __init__(
        self,
        session_factory: Callable[[], AsyncSession],
        runtime_service: AgentRuntimeService,
    ) -> None:
        self._session_factory = session_factory
        self._runtime_service = runtime_service
        self._scheduler: AsyncIOScheduler | None = None
        self._started = False

    # ── Lifecycle ───────────────────────────────────────────────────────

    async def start(self) -> None:
        """Initialize APScheduler and restore enabled jobs from DB."""
        if self._started:
            return

        settings = get_settings()
        if not settings.scheduler_enabled:
            logger.info("Scheduler disabled via SCHEDULER_ENABLED=false")
            return

        self._scheduler = AsyncIOScheduler()
        await self._restore_enabled_jobs()
        self._scheduler.start()
        self._started = True
        logger.info("SchedulerService started")

    async def stop(self) -> None:
        """Shutdown APScheduler."""
        if self._scheduler:
            self._scheduler.shutdown()
            self._scheduler = None
        self._started = False
        logger.info("SchedulerService stopped")

    # ── CRUD ────────────────────────────────────────────────────────────

    async def list_jobs(self, user_id: uuid.UUID) -> list[dict]:
        """Return scheduled jobs owned by the specific user, sorted by name."""
        session = self._session_factory()
        try:
            result = await session.execute(
                select(ScheduledJob).where(ScheduledJob.created_by == user_id).order_by(ScheduledJob.name.asc())
            )
            jobs = result.scalars().all()
            return [_job_to_dict(j) for j in jobs]
        finally:
            await session.close()

    async def get_job(self, job_id: str) -> dict | None:
        """Return a single scheduled job by ID, or None."""
        session = self._session_factory()
        try:
            stmt = select(ScheduledJob).where(ScheduledJob.id == uuid.UUID(job_id))
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()
            return _job_to_dict(job) if job else None
        finally:
            await session.close()

    async def create_job(
        self,
        name: str,
        cron_expression: str,
        job_type: str,
        input_payload: dict | None,
        user_id: uuid.UUID | None,
    ) -> dict:
        """Create a new scheduled job and register with APScheduler."""
        self._validate_cron(cron_expression)
        self._validate_job_type(job_type)

        session = self._session_factory()
        try:
            stmt = select(ScheduledJob).where(ScheduledJob.name == name)
            existing = await session.execute(stmt)
            if existing.scalar_one_or_none() is not None:
                raise ValueError(f"Job with name '{name}' already exists")

            job = ScheduledJob(
                id=uuid.uuid4(),
                name=name,
                cron_expression=cron_expression,
                job_type=job_type,
                enabled=True,
                input_payload=input_payload,
                created_by=user_id,
                updated_by=user_id,
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)

            self._register_with_scheduler(job)
            logger.info("Created scheduled job '%s' (cron=%s)", name, cron_expression)
            return _job_to_dict(job)
        finally:
            await session.close()

    async def update_job(
        self,
        job_id: str,
        *,
        name: str | None = None,
        cron_expression: str | None = None,
        job_type: str | None = None,
        enabled: bool | None = None,
        input_payload: dict | None = None,
        user_id: uuid.UUID | None = None,
    ) -> dict:
        """Update a scheduled job. Re-registers with APScheduler if cron changed."""
        session = self._session_factory()
        try:
            stmt = select(ScheduledJob).where(ScheduledJob.id == uuid.UUID(job_id))
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()
            if job is None:
                raise ValueError(f"Scheduled job {job_id} not found")
            if user_id is not None and job.created_by != user_id:
                raise PermissionError("Cannot update a job that does not belong to this user")

            old_cron = job.cron_expression
            old_enabled = job.enabled

            if name is not None:
                await self._validate_name_unique(session, name, exclude_id=job.id)
                job.name = name
            if cron_expression is not None:
                self._validate_cron(cron_expression)
                job.cron_expression = cron_expression
            if job_type is not None:
                self._validate_job_type(job_type)
                job.job_type = job_type
            if enabled is not None:
                job.enabled = enabled
            if input_payload is not None:
                job.input_payload = input_payload

            job.updated_at = _utcnow()
            await session.commit()

            # Re-register with APScheduler if cron or enabled state changed
            if old_cron != job.cron_expression or old_enabled != job.enabled:
                if job.enabled:
                    self._reschedule_job(job)
                else:
                    self._unregister_from_scheduler(job.id)

            return _job_to_dict(job)
        finally:
            await session.close()

    async def delete_job(self, job_id: str, user_id: uuid.UUID | None = None) -> None:
        """Remove a scheduled job from DB and APScheduler."""
        session = self._session_factory()
        try:
            stmt = select(ScheduledJob).where(ScheduledJob.id == uuid.UUID(job_id))
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()
            if job is None:
                raise ValueError(f"Scheduled job {job_id} not found")
            if user_id is not None and job.created_by != user_id:
                raise PermissionError("Cannot delete a job that does not belong to this user")

            self._unregister_from_scheduler(job.id)
            await session.delete(job)
            await session.commit()
            logger.info("Deleted scheduled job '%s'", job.name)
        finally:
            await session.close()

    async def toggle_job(self, job_id: str, enabled: bool) -> dict:
        """Toggle the enabled state of a scheduled job."""
        return await self.update_job(job_id, enabled=enabled)

    async def trigger_job_now(self, job_id: str, user_id: uuid.UUID) -> dict:
        """Manually trigger a scheduled job immediately."""
        session = self._session_factory()
        try:
            stmt = select(ScheduledJob).where(ScheduledJob.id == uuid.UUID(job_id))
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()
            if job is None:
                raise ValueError(f"Scheduled job {job_id} not found")
            if job.created_by != user_id:
                raise PermissionError("Cannot trigger a job that does not belong to this user")

            run_result = await self._dispatch_job(job)
            return _job_to_dict(job)
        finally:
            await session.close()

    # ── Internal ────────────────────────────────────────────────────────

    async def _restore_enabled_jobs(self) -> None:
        """On startup: read enabled jobs from DB and register each with APScheduler."""
        session = self._session_factory()
        try:
            result = await session.execute(
                select(ScheduledJob).where(
                    ScheduledJob.enabled.is_(True)
                ).order_by(ScheduledJob.name.asc())
            )
            jobs = result.scalars().all()
            for job in jobs:
                self._register_with_scheduler(job)
            logger.info("Restored %d scheduled jobs from database", len(jobs))
        finally:
            await session.close()

    async def _run_scheduled_job(self, job_id: str) -> None:
        """Triggered by APScheduler: dispatch to AgentRuntimeService.

        Records submission status immediately. Does NOT poll for completion.
        """
        session = self._session_factory()
        try:
            stmt = select(ScheduledJob).where(ScheduledJob.id == uuid.UUID(job_id))
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()
            if not job or not job.enabled:
                return

            now = _utcnow()
            try:
                run_result = await self._dispatch_job(job)
                run_uuid = uuid.UUID(run_result["id"])

                job.last_run_id = run_uuid
                job.last_run_at = now
                job.last_run_status = "submitted"
                await session.commit()
                logger.info(
                    "Scheduled job '%s' dispatched run %s", job.name, run_uuid
                )
            except Exception:
                logger.exception("Failed to dispatch scheduled job '%s'", job.name)
                job.last_run_at = now
                job.last_run_status = "failed"
                await session.commit()
        finally:
            await session.close()

    async def _dispatch_job(self, job: ScheduledJob) -> dict:
        """Submit a job's execution through AgentRuntimeService."""
        payload = dict(job.input_payload or {})
        payload.setdefault("_agent_type", job.job_type)
        return await self._runtime_service.submit(
            agent_type=job.job_type,
            input_payload=payload,
            user_id=None,  # system-initiated, not user-initiated
            scheduled_job_id=str(job.id),
        )

    # ── Execution history helpers ───────────────────────────────────────

    async def update_last_run(
        self,
        job_id: uuid.UUID,
        run_id: uuid.UUID,
        status: str,
        duration_ms: int | None = None,
    ) -> None:
        """Update denormalized last_run_* fields on a ScheduledJob.

        Called by AgentRuntimeService when a scheduled run reaches its final state.
        The agent_runs table remains the single source of truth; this is a cache.
        """
        session = self._session_factory()
        try:
            stmt = select(ScheduledJob).where(ScheduledJob.id == job_id)
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()
            if job is None:
                return
            job.last_run_id = run_id
            job.last_run_at = _utcnow()
            job.last_run_status = status
            job.last_run_duration_ms = duration_ms
            await session.commit()
        except Exception:
            logger.warning("Failed to update last_run for job %s", job_id, exc_info=True)
        finally:
            await session.close()

    # ── Validation ──────────────────────────────────────────────────────

    @staticmethod
    def _validate_cron(cron_expression: str) -> None:
        if not croniter.is_valid(cron_expression):
            raise ValueError(f"Invalid cron expression: {cron_expression}")

    @staticmethod
    def _validate_job_type(job_type: str) -> None:
        if job_type not in _VALID_JOB_TYPES:
            raise ValueError(
                f"Invalid job_type '{job_type}'. Must be one of: {_VALID_JOB_TYPES}"
            )

    @staticmethod
    async def _validate_name_unique(session: AsyncSession, name: str, *, exclude_id: uuid.UUID | None = None) -> None:
        stmt = select(ScheduledJob).where(ScheduledJob.name == name)
        if exclude_id is not None:
            stmt = stmt.where(ScheduledJob.id != exclude_id)
        result = await session.execute(stmt)
        if result.scalar_one_or_none() is not None:
            raise ValueError(f"Job with name '{name}' already exists")

    # ── APScheduler bridge ──────────────────────────────────────────────

    def _register_with_scheduler(self, job: ScheduledJob) -> None:
        if not self._scheduler:
            return
        self._scheduler.add_job(
            self._run_scheduled_job,
            "cron",
            id=str(job.id),
            args=[str(job.id)],
            cron_trigger=self._parse_cron(job.cron_expression),
            replace_existing=True,
        )

    def _reschedule_job(self, job: ScheduledJob) -> None:
        """Remove and re-add to pick up new cron/enable state."""
        self._unregister_from_scheduler(job.id)
        self._register_with_scheduler(job)

    def _unregister_from_scheduler(self, job_id: uuid.UUID) -> None:
        if not self._scheduler:
            return
        try:
            self._scheduler.remove_job(str(job_id))
        except Exception:
            pass  # Job may not exist if scheduler wasn't started yet

    @staticmethod
    def _parse_cron(expr: str) -> dict:
        """Convert cron expression dict to APScheduler kwargs."""
        parts = expr.strip().split()
        if len(parts) != 5:
            raise ValueError(f"Expected 5-field cron expression, got: {expr}")
        return {
            "minute": parts[0],
            "hour": parts[1],
            "day": parts[2],
            "month": parts[3],
            "day_of_week": parts[4],
        }


def _job_to_dict(job: ScheduledJob) -> dict:
    return {
        "id": str(job.id),
        "name": job.name,
        "cron_expression": job.cron_expression,
        "job_type": job.job_type,
        "enabled": job.enabled,
        "input_payload": job.input_payload,
        "last_run_id": str(job.last_run_id) if job.last_run_id else None,
        "last_run_at": job.last_run_at.isoformat() if job.last_run_at else None,
        "last_run_status": job.last_run_status,
        "last_run_duration_ms": job.last_run_duration_ms,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }
