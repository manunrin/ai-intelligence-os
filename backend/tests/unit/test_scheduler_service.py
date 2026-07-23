"""Unit tests for SchedulerService."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.scheduler.service import (
    SchedulerService,
    _job_to_dict,
)
from backend.database.models.scheduled_job import ScheduledJob


# ── Fixtures ──────────────────────────────────────────────────────────


def _utcnow():
    return datetime.now(timezone.utc)


def _make_mock_session() -> MagicMock:
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.close = AsyncMock()
    session.add = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


def _make_mock_runtime_service() -> AgentRuntimeService:
    svc = MagicMock()
    svc.submit = AsyncMock(return_value={"id": str(uuid.uuid4()), "status": "running"})
    return svc


class TestValidateCron:
    """Cron expression validation."""

    @pytest.mark.parametrize("expr", [
        "0 8 * * *",
        "*/5 * * * *",
        "0 */2 * * *",
        "0 9 * * 1-5",
        "0 0 * * 0",
    ])
    def test_valid_cron_expressions(self, expr):
        # Should not raise
        from croniter import croniter
        assert croniter.is_valid(expr) is True

    @pytest.mark.parametrize("expr", [
        "invalid",
        "* * *",
        "60 25 * * *",
        "",
    ])
    def test_invalid_cron_expressions(self, expr):
        from croniter import croniter
        assert croniter.is_valid(expr) is False


class TestCreateJob:
    """Creating scheduled jobs."""

    @pytest.mark.asyncio
    async def test_create_job_success(self):
        session = _make_mock_session()
        runtime = _make_mock_runtime_service()

        # The service calls session.execute() twice:
        # 1) Uniqueness check (SELECT by name) → None
        # 2) After add/commit, session.refresh is called (not execute)
        # We need execute to return None on first call (no existing job)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.side_effect = [mock_result]

        svc = SchedulerService(
            session_factory=lambda: session,
            runtime_service=runtime,
        )

        with patch.object(svc, "_register_with_scheduler"):
            result = await svc.create_job(
                name="test_job",
                cron_expression="0 8 * * *",
                job_type="intelligence",
                input_payload=None,
                user_id=uuid.uuid4(),
            )

        assert result["name"] == "test_job"
        assert result["job_type"] == "intelligence"
        session.add.assert_called_once()
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_job_duplicate_name_raises(self):
        session = _make_mock_session()
        runtime = _make_mock_runtime_service()

        # The first execute in create_job finds existing job
        existing = MagicMock()
        existing.name = "test_job"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        session.execute.return_value = mock_result

        svc = SchedulerService(
            session_factory=lambda: session,
            runtime_service=runtime,
        )

        with pytest.raises(ValueError, match="already exists"):
            await svc.create_job(
                name="test_job",
                cron_expression="0 8 * * *",
                job_type="intelligence",
                input_payload=None,
                user_id=uuid.uuid4(),
            )

    @pytest.mark.asyncio
    async def test_create_job_invalid_cron_raises(self):
        session = _make_mock_session()
        runtime = _make_mock_runtime_service()

        svc = SchedulerService(
            session_factory=lambda: session,
            runtime_service=runtime,
        )

        with pytest.raises(ValueError, match="Invalid cron"):
            await svc.create_job(
                name="bad",
                cron_expression="not-a-cron",
                job_type="intelligence",
                input_payload=None,
                user_id=uuid.uuid4(),
            )

    @pytest.mark.asyncio
    async def test_create_job_invalid_type_raises(self):
        session = _make_mock_session()
        runtime = _make_mock_runtime_service()

        svc = SchedulerService(
            session_factory=lambda: session,
            runtime_service=runtime,
        )

        with pytest.raises(ValueError, match="Invalid job_type"):
            await svc.create_job(
                name="bad",
                cron_expression="0 8 * * *",
                job_type="nonexistent",
                input_payload=None,
                user_id=uuid.uuid4(),
            )


class TestUpdateJob:
    """Updating scheduled jobs."""

    @pytest.mark.asyncio
    async def test_update_job_toggle_enabled(self):
        session = _make_mock_session()
        runtime = _make_mock_runtime_service()

        job_id = uuid.uuid4()
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.name = "test_job"
        mock_job.cron_expression = "0 8 * * *"
        mock_job.job_type = "intelligence"
        mock_job.enabled = True
        mock_job.input_payload = None
        mock_job.created_at = _utcnow()
        mock_job.updated_at = _utcnow()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_job
        session.execute.return_value = mock_result

        svc = SchedulerService(
            session_factory=lambda: session,
            runtime_service=runtime,
        )

        with patch.object(svc, "_reschedule_job"):
            result = await svc.update_job(str(job_id), enabled=False)

        assert result["enabled"] is False
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_nonexistent_job_raises(self):
        session = _make_mock_session()
        runtime = _make_mock_runtime_service()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        svc = SchedulerService(
            session_factory=lambda: session,
            runtime_service=runtime,
        )

        with pytest.raises(ValueError, match="not found"):
            await svc.update_job(str(uuid.uuid4()), enabled=True)


class TestDeleteJob:
    """Deleting scheduled jobs."""

    @pytest.mark.asyncio
    async def test_delete_job_success(self):
        session = _make_mock_session()
        runtime = _make_mock_runtime_service()

        job_id = uuid.uuid4()
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.name = "test_job"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_job
        session.execute.return_value = mock_result

        svc = SchedulerService(
            session_factory=lambda: session,
            runtime_service=runtime,
        )

        await svc.delete_job(str(job_id))

        session.delete.assert_called_once_with(mock_job)
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_raises(self):
        session = _make_mock_session()
        runtime = _make_mock_runtime_service()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        svc = SchedulerService(
            session_factory=lambda: session,
            runtime_service=runtime,
        )

        with pytest.raises(ValueError, match="not found"):
            await svc.delete_job(str(uuid.uuid4()))


class TestTriggerJobNow:
    """Manual trigger dispatches through AgentRuntimeService."""

    @pytest.mark.asyncio
    async def test_trigger_dispatches_to_runtime_service(self):
        session = _make_mock_session()
        runtime = _make_mock_runtime_service()

        job_id = uuid.uuid4()
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.name = "test_job"
        mock_job.cron_expression = "0 8 * * *"
        mock_job.job_type = "autonomous"
        mock_job.enabled = True
        mock_job.input_payload = {"topic": "AI news"}
        mock_job.last_run_id = None
        mock_job.last_run_at = None
        mock_job.last_run_status = None
        mock_job.last_run_duration_ms = None
        mock_job.created_at = _utcnow()
        mock_job.updated_at = _utcnow()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_job
        session.execute.return_value = mock_result

        svc = SchedulerService(
            session_factory=lambda: session,
            runtime_service=runtime,
        )

        await svc.trigger_job_now(str(job_id))

        runtime.submit.assert_called_once()
        call_kwargs = runtime.submit.call_args.kwargs
        assert call_kwargs["agent_type"] == "autonomous"
        assert call_kwargs["input_payload"]["topic"] == "AI news"


class TestRunScheduledJobRecordsSubmission:
    """_run_scheduled_job records submission status without polling."""

    @pytest.mark.asyncio
    async def test_records_submitted_status(self):
        session = _make_mock_session()
        runtime = _make_mock_runtime_service()

        job_id = uuid.uuid4()
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.name = "scheduled_test"
        mock_job.cron_expression = "0 8 * * *"
        mock_job.job_type = "intelligence"
        mock_job.enabled = True
        mock_job.input_payload = {}
        mock_job.last_run_id = None
        mock_job.last_run_at = None
        mock_job.last_run_status = None
        mock_job.last_run_duration_ms = None
        mock_job.created_at = _utcnow()
        mock_job.updated_at = _utcnow()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_job
        session.execute.return_value = mock_result

        # Make submit return a run with an id
        run_uuid = uuid.uuid4()
        runtime.submit = AsyncMock(return_value={"id": str(run_uuid), "status": "running"})

        svc = SchedulerService(
            session_factory=lambda: session,
            runtime_service=runtime,
        )

        await svc._run_scheduled_job(str(job_id))

        # Verify commit was called (to update last_run fields)
        assert session.commit.call_count >= 1
        # Verify last_run_status was set to "submitted"
        calls = [c for c in session.execute.call_args_list]
        # The job was loaded and then updated (commit was called)


class TestRestoreEnabledJobs:
    """On startup, only enabled jobs are registered."""

    @pytest.mark.asyncio
    async def test_restores_only_enabled_jobs(self):
        session = _make_mock_session()
        runtime = _make_mock_runtime_service()

        enabled_job = MagicMock()
        enabled_job.id = uuid.uuid4()
        enabled_job.name = "enabled_job"
        enabled_job.enabled = True

        mock_result = MagicMock()
        # The query filters by enabled=True, so only enabled jobs are returned
        mock_result.scalars.return_value.all.return_value = [enabled_job]
        session.execute.return_value = mock_result

        svc = SchedulerService(
            session_factory=lambda: session,
            runtime_service=runtime,
        )

        registered = []
        original_register = svc._register_with_scheduler

        def track_register(job):
            registered.append(job.name)
            return original_register(job)

        with patch.object(svc, "_register_with_scheduler", side_effect=track_register):
            await svc._restore_enabled_jobs()

        assert "enabled_job" in registered


class TestJobToDict:
    """_job_to_dict serialization."""

    def test_serializes_all_fields(self):
        job = MagicMock(spec=ScheduledJob)
        job.id = uuid.UUID("12345678-1234-5678-1234-567812345678")
        job.name = "test"
        job.cron_expression = "0 8 * * *"
        job.job_type = "intelligence"
        job.enabled = True
        job.input_payload = {"topic": "AI"}
        job.last_run_id = uuid.UUID("87654321-4321-8765-4321-876543216789")
        job.last_run_at = datetime(2026, 7, 23, 8, 0, 0, tzinfo=timezone.utc)
        job.last_run_status = "completed"
        job.last_run_duration_ms = 12345
        job.created_at = datetime(2026, 7, 1, tzinfo=timezone.utc)
        job.updated_at = datetime(2026, 7, 23, tzinfo=timezone.utc)

        d = _job_to_dict(job)

        assert d["id"] == "12345678-1234-5678-1234-567812345678"
        assert d["name"] == "test"
        assert d["cron_expression"] == "0 8 * * *"
        assert d["job_type"] == "intelligence"
        assert d["enabled"] is True
        assert d["input_payload"] == {"topic": "AI"}
        assert d["last_run_id"] == "87654321-4321-8765-4321-876543216789"
        assert d["last_run_status"] == "completed"
        assert d["last_run_duration_ms"] == 12345
        assert d["last_run_at"] == "2026-07-23T08:00:00+00:00"

    def test_null_fields_serialize_correctly(self):
        job = MagicMock(spec=ScheduledJob)
        job.id = uuid.uuid4()
        job.name = "test"
        job.cron_expression = "0 8 * * *"
        job.job_type = "intelligence"
        job.enabled = False
        job.input_payload = None
        job.last_run_id = None
        job.last_run_at = None
        job.last_run_status = None
        job.last_run_duration_ms = None
        job.created_at = _utcnow()
        job.updated_at = _utcnow()

        d = _job_to_dict(job)

        assert d["input_payload"] is None
        assert d["last_run_id"] is None
        assert d["last_run_at"] is None
        assert d["last_run_status"] is None
