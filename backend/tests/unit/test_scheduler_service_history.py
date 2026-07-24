"""Unit tests for SchedulerService execution history integration.

Tests that scheduled job dispatch links to agent_runs via scheduled_job_id,
and that completion status updates propagate back to ScheduledJob.last_run_*.
"""

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


class TestDispatchLinksToScheduler:
    """_dispatch_job passes scheduled_job_id through to runtime_service.submit()."""

    @pytest.mark.asyncio
    async def test_dispatch_passes_scheduled_job_id(self):
        session = _make_mock_session()
        runtime = MagicMock()
        runtime.submit = AsyncMock(return_value={"id": str(uuid.uuid4()), "status": "running"})

        job_id = uuid.uuid4()
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.name = "test_job"
        mock_job.cron_expression = "0 8 * * *"
        mock_job.job_type = "intelligence"
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

        await svc._dispatch_job(mock_job)

        # Verify scheduled_job_id was passed
        call_kwargs = runtime.submit.call_args.kwargs
        assert call_kwargs["scheduled_job_id"] == str(job_id)
        assert call_kwargs["agent_type"] == "intelligence"

    @pytest.mark.asyncio
    async def test_dispatch_includes_agent_type_from_job(self):
        session = _make_mock_session()
        runtime = MagicMock()
        runtime.submit = AsyncMock(return_value={"id": str(uuid.uuid4()), "status": "running"})

        job_id = uuid.uuid4()
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.job_type = "autonomous"
        mock_job.input_payload = {}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_job
        session.execute.return_value = mock_result

        svc = SchedulerService(
            session_factory=lambda: session,
            runtime_service=runtime,
        )

        await svc._dispatch_job(mock_job)

        call_kwargs = runtime.submit.call_args.kwargs
        assert call_kwargs["agent_type"] == "autonomous"
        assert call_kwargs["input_payload"]["_agent_type"] == "autonomous"


class TestUpdateLastRun:
    """update_last_run updates ScheduledJob denormalized fields."""

    @pytest.mark.asyncio
    async def test_update_last_run_success(self):
        session = _make_mock_session()
        job_id = uuid.uuid4()
        run_id = uuid.uuid4()

        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.name = "test_job"
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
            runtime_service=MagicMock(),
        )

        await svc.update_last_run(job_id, run_id, "completed", 12345)

        assert mock_job.last_run_id == run_id
        assert mock_job.last_run_status == "completed"
        assert mock_job.last_run_duration_ms == 12345
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_last_run_nonexistent_job_noop(self):
        session = _make_mock_session()
        job_id = uuid.uuid4()
        run_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        svc = SchedulerService(
            session_factory=lambda: session,
            runtime_service=MagicMock(),
        )

        # Should not raise — just logs warning
        await svc.update_last_run(job_id, run_id, "completed", 1000)
        session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_last_run_exception_logged(self):
        session = _make_mock_session()
        job_id = uuid.uuid4()
        run_id = uuid.uuid4()

        session.execute.side_effect = RuntimeError("DB error")

        svc = SchedulerService(
            session_factory=lambda: session,
            runtime_service=MagicMock(),
        )

        # Should not raise — catches and logs
        await svc.update_last_run(job_id, run_id, "failed", None)
        session.close.assert_called_once()


class TestRunScheduledJobRecordsSubmission:
    """_run_scheduled_job records submission status."""

    @pytest.mark.asyncio
    async def test_records_submitted_status_on_dispatch(self):
        session = _make_mock_session()
        runtime = MagicMock()

        job_id = uuid.uuid4()
        run_uuid = uuid.uuid4()
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

        runtime.submit = AsyncMock(return_value={"id": str(run_uuid), "status": "running"})
        svc = SchedulerService(
            session_factory=lambda: session,
            runtime_service=runtime,
        )

        await svc._run_scheduled_job(str(job_id))

        # Verify commit was called (to update last_run fields)
        assert session.commit.call_count >= 1
        assert mock_job.last_run_id == run_uuid
        assert mock_job.last_run_status == "submitted"


class TestTriggerJobCreatesHistoryLink:
    """Manual trigger also creates a linked agent_run."""

    @pytest.mark.asyncio
    async def test_trigger_job_passes_scheduled_job_id(self):
        session = _make_mock_session()
        runtime = MagicMock()
        runtime.submit = AsyncMock(return_value={"id": str(uuid.uuid4()), "status": "running"})

        job_id = uuid.uuid4()
        test_user = uuid.uuid4()
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.name = "test_job"
        mock_job.job_type = "autonomous"
        mock_job.enabled = True
        mock_job.input_payload = {"topic": "AI news"}
        mock_job.last_run_id = None
        mock_job.last_run_at = None
        mock_job.last_run_status = None
        mock_job.last_run_duration_ms = None
        mock_job.created_by = test_user
        mock_job.created_at = _utcnow()
        mock_job.updated_at = _utcnow()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_job
        session.execute.return_value = mock_result

        svc = SchedulerService(
            session_factory=lambda: session,
            runtime_service=runtime,
        )

        await svc.trigger_job_now(str(job_id), user_id=test_user)

        call_kwargs = runtime.submit.call_args.kwargs
        assert call_kwargs["scheduled_job_id"] == str(job_id)
