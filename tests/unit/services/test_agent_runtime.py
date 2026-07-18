"""Tests for AgentRuntimeService — submit, cancel, get_run, stream."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.agent_runtime_service import (
    AgentRuntimeService,
    AgentRunNotFoundError,
    _run_to_dict,
)


def _make_mock_session():
    """Build a session mock with chainable execute() returning scalars().all()."""
    result = MagicMock()
    result.scalars = MagicMock(return_value=result)
    result.all = MagicMock(return_value=[])
    result.scalar_one_or_none = MagicMock(return_value=None)

    class MockSession:
        execute = AsyncMock(return_value=result)
        add = MagicMock()
        commit = AsyncMock()
        flush = AsyncMock()
        close = AsyncMock()

    return MockSession()


@pytest.fixture()
def mock_session():
    return _make_mock_session()


@pytest.fixture()
def mock_repo(mock_session):
    repo = AsyncMock()
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.list_by_user = AsyncMock(return_value=[])
    return repo


@pytest.fixture()
def mock_stage_repo(mock_session):
    repo = AsyncMock()
    repo.create_stage = AsyncMock()
    repo.update_stage = AsyncMock()
    repo.get_by_run_id = AsyncMock(return_value=[])
    return repo


@pytest.fixture()
def service(mock_session, mock_repo, mock_stage_repo):
    sf = MagicMock()
    sf.return_value = MagicMock()
    svc = AgentRuntimeService(mock_session, session_factory=sf)
    with patch(
        "backend.services.agent_runtime_service._make_repo",
        return_value=(mock_repo, mock_stage_repo),
    ):
        yield svc


class TestAgentRuntimeServiceSubmit:
    @pytest.mark.asyncio
    async def test_submit_creates_run_record(self, service, mock_session, mock_repo):
        """submit() creates an AgentRun record and returns it as dict."""
        run_id = uuid.uuid4()
        fake_run = MagicMock()
        fake_run.id = run_id
        fake_run.agent_id = run_id
        fake_run.workflow_id = None
        fake_run.status = "running"
        fake_run.stage = "initializing"
        fake_run.input_payload = {"topic": "test"}
        fake_run.output_payload = None
        fake_run.error_message = None
        fake_run.started_at = datetime.now(timezone.utc)
        fake_run.finished_at = None
        fake_run.duration_ms = None
        fake_run.user_id = uuid.uuid4()

        mock_repo.create = AsyncMock(return_value=fake_run)

        # Patch create_task so submit doesn't actually start bg execution
        with patch.object(asyncio, "create_task"):
            result = await service.submit(
                agent_type="intelligence",
                input_payload={"topic": "test"},
                user_id=fake_run.user_id,
            )

        assert result["status"] == "running"
        assert result["stage"] == "initializing"
        assert result["input_payload"]["topic"] == "test"
        mock_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_invalid_agent_type(self, service):
        """submit() raises ValueError for unknown agent_type."""
        with pytest.raises(ValueError, match="Unknown agent_type"):
            await service.submit(
                agent_type="nonexistent",
                input_payload={},
                user_id=uuid.uuid4(),
            )

    def test_available_pipelines_have_registry(self):
        """PIPELINE_REGISTRY contains expected pipeline types."""
        from backend.workflows.registry import PIPELINE_REGISTRY
        assert "intelligence" in PIPELINE_REGISTRY
        assert "autonomous" in PIPELINE_REGISTRY


class TestAgentRuntimeServiceGetRun:
    @pytest.mark.asyncio
    async def test_get_run_returns_none_for_missing(self, service, mock_repo):
        mock_repo.get_by_id.return_value = None
        result = await service.get_run(str(uuid.uuid4()))
        assert result is None

    @pytest.mark.asyncio
    async def test_get_run_returns_dict_with_stages(self, service, mock_repo, mock_stage_repo):
        run_id = uuid.uuid4()
        run_obj = MagicMock()
        run_obj.id = run_id
        run_obj.agent_id = run_id
        run_obj.workflow_id = None
        run_obj.status = "running"
        run_obj.stage = "running"
        run_obj.input_payload = {}
        run_obj.output_payload = None
        run_obj.error_message = None
        run_obj.started_at = datetime.now(timezone.utc)
        run_obj.finished_at = None
        run_obj.duration_ms = None
        run_obj.user_id = uuid.uuid4()
        mock_repo.get_by_id.return_value = run_obj
        mock_stage_repo.get_by_run_id.return_value = []

        result = await service.get_run(str(run_id))
        assert result is not None
        assert result["id"] == str(run_id)
        assert result["stages"] == []
        assert result["stream_url"] is not None


class TestAgentRuntimeServiceCancel:
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_run(self, service, mock_repo):
        mock_repo.get_by_id.return_value = None
        with pytest.raises(AgentRunNotFoundError):
            await service.cancel_run(str(uuid.uuid4()), user_id=uuid.uuid4())

    @pytest.mark.asyncio
    async def test_cancel_running_run(self, service, mock_repo, mock_session):
        run_id = uuid.uuid4()
        run_obj = MagicMock()
        run_obj.status = "running"
        mock_repo.get_by_id.return_value = run_obj
        mock_repo.update = AsyncMock()
        service._run_tasks[run_id] = None

        result = await service.cancel_run(str(run_id), user_id=uuid.uuid4())
        assert result["cancelled"] is True
        assert mock_repo.update.call_count >= 1
        # Verify commit was called on the request session
        mock_session.commit.assert_called()


class TestRunToDict:
    def test_to_dict_converts_orm_model(self):
        run = MagicMock()
        run.id = uuid.uuid4()
        run.agent_id = uuid.uuid4()
        run.workflow_id = None
        run.status = "completed"
        run.stage = "complete"
        run.input_payload = {"key": "value"}
        run.output_payload = {"result": "data"}
        run.error_message = None
        run.started_at = datetime(2026, 7, 17, tzinfo=timezone.utc)
        run.finished_at = datetime(2026, 7, 17, tzinfo=timezone.utc)
        run.duration_ms = 5000
        run.user_id = uuid.uuid4()

        result = _run_to_dict(run)
        assert result["status"] == "completed"
        assert result["stage"] == "complete"
        assert result["duration_ms"] == 5000
        assert result["finished_at"] is not None


class TestAvailablePipelines:
    def test_available_pipelines_returns_list(self, service):
        pipelines = service.available_pipelines
        assert len(pipelines) == 2
        types = [p["type"] for p in pipelines]
        assert "intelligence" in types
        assert "autonomous" in types


class TestPersistStages:
    @pytest.mark.asyncio
    async def test_persist_stages_from_events(self, service, mock_stage_repo, mock_session):
        from backend.workflows.graph.callbacks import StageEvent

        run_id = uuid.uuid4()
        events = [
            StageEvent(run_id=run_id, node_name="research", phase="start"),
            StageEvent(run_id=run_id, node_name="research", phase="end", outputs={"summary": "done"}),
            StageEvent(run_id=run_id, node_name="analyst", phase="start"),
            StageEvent(run_id=run_id, node_name="analyst", phase="error", error_message="fail"),
        ]

        stage_repo = MagicMock()
        stage_repo.create_stage = AsyncMock()
        stage_repo.update_stage = AsyncMock()
        stage_repo.session = mock_session

        await service._persist_stages(stage_repo, run_id, events)

        # Each unique stage triggers one create_stage call (research + analyst = 2)
        assert stage_repo.create_stage.call_count == 2
        # update_stage is called for completed/failed stages (end + error = 2)
        assert stage_repo.update_stage.call_count == 2


class TestEventAbstraction:
    def test_sse_format(self):
        from backend.events.agent_event import AgentEvent, EventType

        run_id = uuid.uuid4()
        event = AgentEvent.stage_start(run_id, "research")
        sse = event.to_sse()
        assert "event: stage_start" in sse
        assert f'"run_id": "{run_id}"' in sse
        assert '"stage_name": "research"' in sse

    def test_all_event_types(self):
        from backend.events.agent_event import AgentEvent, EventType

        run_id = uuid.uuid4()
        for et in EventType:
            if et == EventType.HEARTBEAT:
                event = AgentEvent(type=et, run_id=run_id)
            else:
                event = AgentEvent(type=et, run_id=run_id, status="test")
            sse = event.to_sse()
            assert f"event: {et.value}" in sse
