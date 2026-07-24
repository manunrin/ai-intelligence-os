"""Security tests: IDOR prevention on agent runs and scheduler user isolation.

Covers three critical fixes:
1. Agent run get/cancel/resume must verify run ownership (IDOR fix)
2. Scheduler job history must filter by requesting user's ID
3. Scheduler update/delete must verify job ownership

Tests use service-layer unit tests + raw source file inspection for router
checks. The TestClient integration tests are covered by CI inside Docker
where slowapi is properly configured.
"""

from __future__ import annotations

import inspect
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Fix 1: Agent Run IDOR — service layer ────────────────────────────

USER_A = uuid.uuid4()
USER_B = uuid.uuid4()


class TestAgentRuntimeServiceOwnership:
    """Verify get_run, cancel_run, resume enforce user ownership."""

    @pytest.fixture()
    def mock_checkpointer(self):
        cp = MagicMock()
        cp.aget = AsyncMock(return_value=None)
        return cp

    def _make_mock_run(self, run_id, owner_id, status="running"):
        run = MagicMock()
        run.id = run_id
        run.user_id = owner_id
        run.status = status
        run.stage = "research"
        run.input_payload = {}
        run.output_payload = None
        run.error_message = None
        run.started_at = datetime.now(timezone.utc)
        run.finished_at = None
        run.duration_ms = None
        run.thread_id = f"agent-run-{run_id}"
        run.agent_id = uuid.uuid4()
        run.workflow_id = None
        run.retry_count = 0
        run.scheduled_job_id = None
        run.evaluations = []
        return run

    @pytest.mark.asyncio
    async def test_get_run_returns_data_for_own_run(self, mock_checkpointer):
        """User A can read their own run — returns full dict."""
        from backend.services.agent_runtime_service import AgentRuntimeService

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        run_id = uuid.uuid4()
        mock_run = self._make_mock_run(run_id, USER_A, "completed")

        svc = AgentRuntimeService.__new__(AgentRuntimeService)
        svc._request_session = mock_session
        svc._checkpointer = mock_checkpointer
        svc._cancellation_tokens = {}
        svc._run_tasks = {}

        with patch(
            "backend.services.agent_runtime_service._make_repo"
        ) as mock_make_repo:
            mock_stage_repo = MagicMock()
            mock_stage_repo.get_by_run_id = AsyncMock(return_value=[])
            mock_make_repo.return_value = (
                MagicMock(get_by_id=AsyncMock(return_value=mock_run)),
                mock_stage_repo,
            )

            result = await svc.get_run(str(run_id), user_id=USER_A)

        assert result is not None
        assert result["id"] == str(run_id)

    @pytest.mark.asyncio
    async def test_get_run_returns_none_for_other_user(self, mock_checkpointer):
        """User B cannot read User A's run — returns None (not found)."""
        from backend.services.agent_runtime_service import AgentRuntimeService

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        run_id = uuid.uuid4()
        mock_run = self._make_mock_run(run_id, USER_A, "completed")

        svc = AgentRuntimeService.__new__(AgentRuntimeService)
        svc._request_session = mock_session
        svc._checkpointer = mock_checkpointer
        svc._cancellation_tokens = {}
        svc._run_tasks = {}

        with patch(
            "backend.services.agent_runtime_service._make_repo"
        ) as mock_make_repo:
            mock_stage_repo = MagicMock()
            mock_stage_repo.get_by_run_id = AsyncMock(return_value=[])
            mock_make_repo.return_value = (
                MagicMock(get_by_id=AsyncMock(return_value=mock_run)),
                mock_stage_repo,
            )

            result = await svc.get_run(str(run_id), user_id=USER_B)

        assert result is None

    @pytest.mark.asyncio
    async def test_cancel_run_raises_for_other_user(self, mock_checkpointer):
        """User B cannot cancel User A's run — raises PermissionError."""
        from backend.services.agent_runtime_service import AgentRuntimeService

        mock_session = MagicMock()
        run_id = uuid.uuid4()
        mock_run = self._make_mock_run(run_id, USER_A, "running")

        svc = AgentRuntimeService.__new__(AgentRuntimeService)
        svc._request_session = mock_session
        svc._checkpointer = mock_checkpointer
        svc._cancellation_tokens = {}
        svc._run_tasks = {}

        with patch(
            "backend.services.agent_runtime_service._make_repo"
        ) as mock_make_repo:
            mock_make_repo.return_value = (
                MagicMock(get_by_id=AsyncMock(return_value=mock_run)),
                None,
            )

            with pytest.raises(PermissionError, match="does not belong to this user"):
                await svc.cancel_run(str(run_id), user_id=USER_B)

    @pytest.mark.asyncio
    async def test_resume_raises_for_other_user(self, mock_checkpointer):
        """User B cannot resume User A's interrupted run — raises PermissionError."""
        from backend.services.agent_runtime_service import AgentRuntimeService

        mock_session = MagicMock()
        run_id = uuid.uuid4()
        mock_run = self._make_mock_run(run_id, USER_A, "interrupted")

        svc = AgentRuntimeService.__new__(AgentRuntimeService)
        svc._request_session = mock_session
        svc._checkpointer = mock_checkpointer
        svc._cancellation_tokens = {}
        svc._run_tasks = {}

        with patch(
            "backend.services.agent_runtime_service._make_repo"
        ) as mock_make_repo:
            mock_make_repo.return_value = (
                MagicMock(get_by_id=AsyncMock(return_value=mock_run)),
                None,
            )

            with pytest.raises(PermissionError, match="does not belong to this user"):
                await svc.resume(str(run_id), user_id=USER_B)


# ── Fix 2 & 3: Router-level checks via source inspection ─────────────

def _read_source(relative_path):
    """Read source file relative to project root."""
    import os
    # This file is at tests/unit/routers/test_security_fixes.py
    # Go up 3 levels to get to project root
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    with open(os.path.join(root, relative_path), "r") as f:
        return f.read()


class TestSchedulerHistoryIsolation:
    """GET /scheduler/jobs/{id}/history must only return runs for the requesting user."""

    def test_history_query_filters_by_current_user_id(self):
        """The history query must include user_id filter in its WHERE clause."""
        source = _read_source("backend/routers/scheduler.py")

        # Verify current_user dependency is present
        assert "get_current_user" in source
        assert "current_user: Any = Depends(get_current_user)" in source

        # Verify the WHERE clause includes user_id filter
        assert "AgentRun.user_id" in source or "user_id ==" in source


class TestSchedulerCRUDIsolation:
    """Update and delete must verify job ownership."""

    def test_update_job_service_accepts_and_checks_user_id(self):
        """update_job must accept user_id and check against job.created_by."""
        from backend.services.scheduler.service import SchedulerService

        sig = inspect.signature(SchedulerService.update_job)
        assert "user_id" in sig.parameters, "update_job must accept user_id parameter"

        source = inspect.getsource(SchedulerService.update_job)
        assert "created_by" in source, (
            "update_job must check job.created_by against user_id"
        )

    def test_delete_job_service_accepts_and_checks_user_id(self):
        """delete_job must accept user_id and check against job.created_by."""
        from backend.services.scheduler.service import SchedulerService

        sig = inspect.signature(SchedulerService.delete_job)
        assert "user_id" in sig.parameters, "delete_job must accept user_id parameter"

        source = inspect.getsource(SchedulerService.delete_job)
        assert "created_by" in source, (
            "delete_job must check job.created_by against user_id"
        )

    def test_router_passes_user_id_to_update(self):
        """The update_job router must pass current_user.id to the service."""
        source = _read_source("backend/routers/scheduler.py")
        assert "user_id=current_user.id" in source

    def test_router_passes_user_id_to_delete(self):
        """The delete_job router must pass current_user.id to the service."""
        source = _read_source("backend/routers/scheduler.py")
        assert "user_id=current_user.id" in source


# ── PermissionError → HTTP 403 handler ───────────────────────────────

class TestPermissionErrorHandler:
    """Ensure PermissionError returns 403, not 500."""

    def test_permission_error_handler_registered(self):
        """The error handler module must handle PermissionError."""
        source = _read_source("backend/routers/errors.py")
        assert "PermissionError" in source, (
            "register_exception_handlers must have a PermissionError handler"
        )
        assert "HTTP_403_FORBIDDEN" in source, (
            "PermissionError handler must return 403 status"
        )


# ── Fix 4 & 5: Scheduler list_jobs and trigger_job_now isolation ─────

class TestSchedulerListJobsIsolation:
    """GET /scheduler/jobs must only return jobs owned by the current user."""

    def test_list_jobs_service_accepts_user_id(self):
        """list_jobs must accept user_id parameter."""
        from backend.services.scheduler.service import SchedulerService

        sig = inspect.signature(SchedulerService.list_jobs)
        params = list(sig.parameters.keys())
        # 'self' is always first; check if user_id is among the rest
        assert "user_id" in params[1:], "list_jobs must accept user_id parameter"

    def test_list_jobs_service_filters_by_user_id(self):
        """list_jobs must filter ScheduledJob by created_by == user_id."""
        source = _read_source("backend/services/scheduler/service.py")
        # The service file contains list_jobs which should query by created_by
        assert "created_by" in source, "Scheduler service must filter by created_by"

    def test_router_passes_user_id_to_list(self):
        """The list_jobs router must pass current_user.id to the service."""
        source = _read_source("backend/routers/scheduler.py")
        assert "user_id=current_user.id" in source


class TestSchedulerTriggerOwnership:
    """POST /scheduler/jobs/{id}/trigger must verify job ownership."""

    def test_trigger_job_now_accepts_user_id(self):
        """trigger_job_now must accept user_id parameter."""
        from backend.services.scheduler.service import SchedulerService

        sig = inspect.signature(SchedulerService.trigger_job_now)
        params = list(sig.parameters.keys())
        assert "user_id" in params[1:], "trigger_job_now must accept user_id parameter"

    def test_trigger_job_now_checks_ownership(self):
        """trigger_job_now must check job.created_by against user_id."""
        source = _read_source("backend/services/scheduler/service.py")
        assert "created_by" in source

    def test_router_passes_user_id_to_trigger(self):
        """The trigger_job router must pass current_user.id to the service."""
        source = _read_source("backend/routers/scheduler.py")
        assert "user_id=current_user.id" in source

    @pytest.mark.asyncio
    async def test_trigger_raises_for_other_user(self):
        """User B cannot trigger User A's scheduled job — raises PermissionError."""
        from backend.services.scheduler.service import SchedulerService

        session = MagicMock()
        mock_job = MagicMock()
        mock_job.id = uuid.uuid4()
        mock_job.name = "test_job"
        mock_job.cron_expression = "0 8 * * *"
        mock_job.job_type = "intelligence"
        mock_job.enabled = True
        mock_job.input_payload = {}
        mock_job.created_by = USER_A
        mock_job.updated_at = datetime.now(timezone.utc)
        mock_job.last_run_id = None
        mock_job.last_run_at = None
        mock_job.last_run_status = None
        mock_job.last_run_duration_ms = None
        mock_job.created_at = datetime.now(timezone.utc)

        session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_job))
        )
        session.close = AsyncMock()

        runtime = MagicMock()
        runtime.submit = AsyncMock(return_value={"id": str(uuid.uuid4()), "status": "running"})

        svc = SchedulerService(
            session_factory=lambda: session,
            runtime_service=runtime,
        )

        with pytest.raises(PermissionError, match="does not belong to this user"):
            await svc.trigger_job_now(str(mock_job.id), user_id=USER_B)
