"""Unit tests for AgentRuntimeService._recover_stale_runs."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.services.agent_runtime_service import (
    AgentRuntimeService,
    _run_to_dict,
    _utcnow,
)


# ── Fixtures ──────────────────────────────────────────────────────────


def _make_mock_session() -> MagicMock:
    """Return a MagicMock that mimics an AsyncSession with execute/commit/close stubs."""
    from unittest.mock import NonCallableMagicMock
    session = NonCallableMagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.close = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.add = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


def _make_mock_agent_run(
    *,
    run_id: str | None = None,
    status: str = "running",
    thread_id: str | None = "test-thread-1",
    started_at: datetime | None = None,
    recovered_at: datetime | None = None,
) -> MagicMock:
    """Build a MagicMock that mimics an AgentRun ORM object."""
    run = MagicMock()
    run.id = uuid.UUID(run_id) if run_id else uuid.uuid4()
    run.status = status
    run.thread_id = thread_id
    run.started_at = started_at or _utcnow() - timedelta(hours=48)
    run.recovered_at = recovered_at
    return run


def _build_service(session: AsyncMock | None = None) -> AgentRuntimeService:
    """Build an AgentRuntimeService backed by a fake session."""
    sess = session or _make_mock_session()
    return AgentRuntimeService(sess, session_factory=lambda: sess)


# ── Tests ─────────────────────────────────────────────────────────────


class TestRecoverStaleRunsNoCheckpointer:
    def test_returns_zeroes_when_no_checkpointer(self):
        svc = _build_service()
        result = asyncio.run(svc._recover_stale_runs(checkpointer=None))
        assert result == {"checked": 0, "recovered": 0, "marked_failed": 0}


class TestRecoverStaleRunsNoStaleRuns:
    @pytest.mark.asyncio
    async def test_empty_query_returns_zeroes(self):
        session = _make_mock_session()
        svc = _build_service(session)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute.return_value = mock_result

        mock_checkpointer = AsyncMock()
        result = await svc._recover_stale_runs(
            checkpointer=mock_checkpointer,
            max_hours=24,
        )
        assert result == {"checked": 0, "recovered": 0, "marked_failed": 0}


class TestRecoverStaleRunsWithCheckpoint:
    """A stale run whose thread_id still has a LangGraph checkpoint → recovered."""

    @pytest.mark.asyncio
    async def test_recovered_run_sets_recovered_at_and_completed_status(self):
        session = _make_mock_session()
        run = _make_mock_agent_run(status="running")

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [run]
        session.execute.return_value = mock_result

        # Simulate a valid checkpoint tuple
        checkpoint_config = {
            "configurable": {
                "thread_id": str(run.thread_id),
                "thread_ts": "1700000000000000",
            }
        }
        mock_checkpoint = MagicMock()
        mock_checkpoint.config = checkpoint_config
        mock_checkpoint.checkpoint = {}
        mock_checkpoint.metadata = {}
        mock_checkpoint.parent_config = None

        mock_checkpointer = AsyncMock()
        mock_checkpointer.aget_tuple = AsyncMock(return_value=mock_checkpoint)

        svc = _build_service(session)
        result = await svc._recover_stale_runs(
            checkpointer=mock_checkpointer,
            max_hours=24,
        )

        assert result["checked"] == 1
        assert result["recovered"] == 1
        assert result["marked_failed"] == 0
        assert session.commit.call_count >= 1


class TestRecoverStaleRunsNoCheckpoint:
    """A stale run with no checkpoint → marked failed."""

    @pytest.mark.asyncio
    async def test_no_checkpoint_marks_failed(self):
        session = _make_mock_session()
        run = _make_mock_agent_run(status="running")

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [run]
        session.execute.return_value = mock_result

        mock_checkpointer = AsyncMock()
        mock_checkpointer.aget_tuple = AsyncMock(return_value=None)

        svc = _build_service(session)
        result = await svc._recover_stale_runs(
            checkpointer=mock_checkpointer,
            max_hours=24,
        )

        assert result["checked"] == 1
        assert result["recovered"] == 0
        assert result["marked_failed"] == 1


class TestRecoverStaleRunsCheckpointLookupFailure:
    """When checkpoint lookup throws → treated as no checkpoint → failed."""

    @pytest.mark.asyncio
    async def test_lookup_error_marks_failed(self):
        session = _make_mock_session()
        run = _make_mock_agent_run(status="running")

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [run]
        session.execute.return_value = mock_result

        mock_checkpointer = AsyncMock()
        mock_checkpointer.aget_tuple = AsyncMock(
            side_effect=Exception("connection refused")
        )

        svc = _build_service(session)
        result = await svc._recover_stale_runs(
            checkpointer=mock_checkpointer,
            max_hours=24,
        )

        assert result["checked"] == 1
        assert result["marked_failed"] == 1


class TestRecoverStaleRunsMixedResults:
    """Multiple stale runs: some recovered, some failed."""

    @pytest.mark.asyncio
    async def test_mixed_recovery_outcomes(self):
        session = _make_mock_session()

        run_with_cp = _make_mock_agent_run(
            run_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            status="running",
        )
        run_without_cp = _make_mock_agent_run(
            run_id="b2c3d4e5-f6a7-8901-bcde-f12345678901",
            status="running",
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            run_with_cp,
            run_without_cp,
        ]
        session.execute.return_value = mock_result

        # First call → has checkpoint, second call → no checkpoint
        mock_checkpoint = MagicMock()
        mock_checkpoint.config = {"configurable": {"thread_ts": "v1"}}
        mock_checkpoint.checkpoint = {}
        mock_checkpoint.metadata = {}
        mock_checkpoint.parent_config = None

        mock_checkpointer = AsyncMock()
        mock_checkpointer.aget_tuple = AsyncMock(
            side_effect=[mock_checkpoint, None]
        )

        svc = _build_service(session)
        result = await svc._recover_stale_runs(
            checkpointer=mock_checkpointer,
            max_hours=24,
        )

        assert result["checked"] == 2
        assert result["recovered"] == 1
        assert result["marked_failed"] == 1


class TestRecoverStaleRunsCancellingStatus:
    """Runs in 'cancelling' status should also be scanned."""

    @pytest.mark.asyncio
    async def test_cancelling_runs_are_scanned(self):
        session = _make_mock_session()
        run = _make_mock_agent_run(status="cancelling")

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [run]
        session.execute.return_value = mock_result

        mock_checkpointer = AsyncMock()
        mock_checkpointer.aget_tuple = AsyncMock(return_value=None)

        svc = _build_service(session)
        result = await svc._recover_stale_runs(
            checkpointer=mock_checkpointer,
            max_hours=24,
        )

        assert result["checked"] == 1
        assert result["marked_failed"] == 1


class TestRecoverStaleRunsCompletedRunsExcluded:
    """Already completed runs should NOT be scanned."""

    @pytest.mark.asyncio
    async def test_completed_runs_filtered_out(self):
        session = _make_mock_session()

        # Completed run — should NOT appear in query results
        completed_run = _make_mock_agent_run(status="completed")

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute.return_value = mock_result

        mock_checkpointer = AsyncMock()

        svc = _build_service(session)
        result = await svc._recover_stale_runs(
            checkpointer=mock_checkpointer,
            max_hours=24,
        )

        assert result["checked"] == 0
        assert result["recovered"] == 0
        assert result["marked_failed"] == 0


class TestRecoverStaleRunsNoThreadId:
    """Runs without thread_id should be skipped during scan."""

    @pytest.mark.asyncio
    async def test_none_thread_id_skipped(self):
        session = _make_mock_session()

        run = _make_mock_agent_run(thread_id=None)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [run]
        session.execute.return_value = mock_result

        mock_checkpointer = AsyncMock()

        svc = _build_service(session)
        result = await svc._recover_stale_runs(
            checkpointer=mock_checkpointer,
            max_hours=24,
        )

        assert result["checked"] == 1
        assert result["recovered"] == 0
        assert result["marked_failed"] == 0


class TestRunToDictIncludesRecoveredAt:
    """_run_to_dict should include recovered_at field."""

    def test_dict_contains_recovered_at(self):
        run = _make_mock_agent_run(
            recovered_at=_utcnow() - timedelta(hours=1),
        )
        d = _run_to_dict(run)
        assert "recovered_at" in d
        assert d["recovered_at"] is not None

    def test_dict_handles_null_recovered_at(self):
        run = _make_mock_agent_run(recovered_at=None)
        d = _run_to_dict(run)
        assert "recovered_at" in d
        assert d["recovered_at"] is None


# ── Resume Tests ──────────────────────────────────────────────────────


class TestResumeAgentRun:
    """Tests for AgentRuntimeService.resume()."""

    @pytest.mark.asyncio
    async def test_resume_nonexistent_raises_not_found(self):
        session = _make_mock_session()
        svc = _build_service(session)
        # get_by_id uses session.get(), not session.execute()
        session.get = AsyncMock(return_value=None)

        from backend.services.agent_runtime_service import AgentRunNotFoundError

        with pytest.raises(AgentRunNotFoundError):
            await svc.resume(str(uuid.uuid4()), user_id=uuid.uuid4())

    @pytest.mark.asyncio
    async def test_resume_non_interrupted_raises_value_error(self):
        session = _make_mock_session()
        run_id = uuid.uuid4()
        run = _make_mock_agent_run(run_id=str(run_id), status="completed")
        session.get = AsyncMock(return_value=run)
        svc = _build_service(session)

        with pytest.raises(ValueError, match="Cannot resume run with status 'completed'"):
            await svc.resume(str(run_id), user_id=uuid.uuid4())

    @pytest.mark.asyncio
    async def test_resume_no_checkpointer_uses_input_payload(self):
        session = _make_mock_session()
        run_id = uuid.uuid4()
        input_payload = {"topic": "test", "_agent_type": "intelligence"}
        run = _make_mock_agent_run(
            run_id=str(run_id),
            status="interrupted",
        )
        run.input_payload = input_payload
        session.get = AsyncMock(return_value=run)

        svc = _build_service(session)
        result = await svc.resume(str(run_id), user_id=uuid.uuid4())

        assert result["status"] == "running"
        # Background task was created (no checkpointer → uses input_payload as state)

    @pytest.mark.asyncio
    async def test_resume_loads_checkpoint_state(self):
        session = _make_mock_session()
        run_id = uuid.uuid4()
        run = _make_mock_agent_run(
            run_id=str(run_id),
            status="interrupted",
        )
        run.input_payload = {"topic": "original", "_agent_type": "autonomous"}
        session.get = AsyncMock(return_value=run)

        # Simulate checkpoint with channel_values
        checkpoint_data = {
            "channel_values": {
                "__pregel_tasks": [],
                "research_output": {"analysis": "partial results"},
            },
        }
        checkpoint_config = {
            "configurable": {
                "thread_id": str(run_id),
                "thread_ts": "1700000000000001",
            }
        }
        mock_checkpoint = MagicMock()
        mock_checkpoint.checkpoint = checkpoint_data
        mock_checkpoint.config = checkpoint_config
        mock_checkpoint.metadata = {}
        mock_checkpoint.parent_config = None

        mock_checkpointer = AsyncMock()
        mock_checkpointer.aget = AsyncMock(return_value=mock_checkpoint)
        mock_checkpointer.aget_tuple = AsyncMock(return_value=mock_checkpoint)

        svc = _build_service(session)
        svc._checkpointer = mock_checkpointer

        result = await svc.resume(str(run_id), user_id=uuid.uuid4())

        assert result["status"] == "running"
        assert mock_checkpointer.aget.call_count == 1

    @pytest.mark.asyncio
    async def test_resume_updates_run_status_and_stage(self):
        session = _make_mock_session()
        run_id = uuid.uuid4()
        run = _make_mock_agent_run(
            run_id=str(run_id),
            status="interrupted",
        )
        run.input_payload = {"_agent_type": "intelligence"}
        session.get = AsyncMock(return_value=run)

        svc = _build_service(session)
        await svc.resume(str(run_id), user_id=uuid.uuid4())

        # Verify update was called with running status and resuming stage
        assert session.commit.call_count >= 1
