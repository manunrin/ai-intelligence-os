"""Integration tests for AgentRuntimeService evaluation flow."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.agent_runtime_service import (
    AgentRuntimeService,
    _make_repo,
)
from backend.services.evaluation.schemas import EvaluationResponse


def _make_mock_session():
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
        refresh = AsyncMock()

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


class TestEvaluateOutput:
    @pytest.mark.asyncio
    async def test_evaluate_output_calls_service(self, service, mock_session):
        """_evaluate_output calls EvaluationService when configured."""
        mock_eval = AsyncMock()
        mock_eval.evaluate = AsyncMock(return_value=EvaluationResponse(score=85.0))
        service._evaluation_service = mock_eval

        result = await service._evaluate_output(
            pipeline_type="intelligence",
            output_payload={"summary": "done"},
            input_payload={"topic": "test"},
        )
        assert result is not None
        assert result.score == 85.0
        mock_eval.evaluate.assert_called_once()

    @pytest.mark.asyncio
    async def test_evaluate_output_no_service_returns_none(self, service):
        """_evaluate_output returns None when no EvaluationService is configured."""
        result = await service._evaluate_output(
            pipeline_type="intelligence",
            output_payload={},
            input_payload={},
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_evaluate_output_exception_returns_none(self, service):
        """_evaluate_output returns None on any exception."""
        mock_eval = MagicMock()
        mock_eval.evaluate = AsyncMock(side_effect=RuntimeError("LLM down"))
        service._evaluation_service = mock_eval

        result = await service._evaluate_output(
            pipeline_type="intelligence",
            output_payload={},
            input_payload={},
        )
        assert result is None


class TestPersistEvaluation:
    @pytest.mark.asyncio
    async def test_persist_evaluation_creates_record(self, service, mock_session):
        """_persist_evaluation creates an AgentEvaluation record."""
        run_id = uuid.uuid4()
        eval_response = EvaluationResponse(
            score=90.0,
            criteria={"accuracy": 95.0, "relevance": 85.0},
        )

        await service._persist_evaluation(
            session=mock_session,
            run_id=run_id,
            evaluation_result=eval_response,
            pipeline_type="intelligence",
        )

        # Verify session.add was called with an AgentEvaluation instance
        call_args = mock_session.add.call_args
        assert call_args is not None
        instance = call_args[0][0]
        assert instance.agent_run_id == run_id
        assert instance.pipeline_type == "intelligence"
        assert instance.score == 90.0

    @pytest.mark.asyncio
    async def test_persist_evaluation_with_none_score(self, service, mock_session):
        """_persist_evaluation handles None score gracefully."""
        eval_response = EvaluationResponse(score=None, criteria={})

        await service._persist_evaluation(
            session=mock_session,
            run_id=uuid.uuid4(),
            evaluation_result=eval_response,
            pipeline_type="autonomous",
        )

        call_args = mock_session.add.call_args
        instance = call_args[0][0]
        assert instance.pipeline_type == "autonomous"


class TestGetRunIncludesEvaluation:
    @pytest.mark.asyncio
    async def test_get_run_includes_evaluation_data(self, service, mock_session, mock_repo):
        """get_run includes evaluation_score and evaluation_criteria."""
        run_id = uuid.uuid4()
        fake_run = MagicMock()
        fake_run.id = run_id
        fake_run.agent_id = run_id
        fake_run.workflow_id = None
        fake_run.status = "completed"
        fake_run.stage = "complete"
        fake_run.input_payload = {}
        fake_run.output_payload = {"result": "data"}
        fake_run.error_message = None
        fake_run.started_at = datetime.now(timezone.utc)
        fake_run.finished_at = datetime.now(timezone.utc)
        fake_run.duration_ms = 5000
        fake_run.user_id = uuid.uuid4()
        fake_run.retry_count = 0

        mock_repo.get_by_id = AsyncMock(return_value=fake_run)

        # Patch eval_repo to return a mock evaluation
        from backend.services.evaluation.repository import AgentEvaluationRepository
        mock_eval = MagicMock()
        mock_eval.get_by_run_id = AsyncMock(
            return_value=MagicMock(score=85.0, criteria={"accuracy": 90.0})
        )
        with patch.object(
            AgentEvaluationRepository, "__new__", return_value=mock_eval
        ):
            result = await service.get_run(str(run_id))

        assert result is not None
        assert result["evaluation_score"] == 85.0
        assert result["evaluation_criteria"]["accuracy"] == 90.0

    @pytest.mark.asyncio
    async def test_get_run_without_evaluation(self, service, mock_session, mock_repo):
        """get_run returns None evaluation fields when no evaluation exists."""
        run_id = uuid.uuid4()
        fake_run = MagicMock()
        fake_run.id = run_id
        fake_run.agent_id = run_id
        fake_run.workflow_id = None
        fake_run.status = "completed"
        fake_run.stage = "complete"
        fake_run.input_payload = {}
        fake_run.output_payload = None
        fake_run.error_message = None
        fake_run.started_at = datetime.now(timezone.utc)
        fake_run.finished_at = datetime.now(timezone.utc)
        fake_run.duration_ms = 5000
        fake_run.user_id = uuid.uuid4()
        fake_run.retry_count = 0

        mock_repo.get_by_id = AsyncMock(return_value=fake_run)

        from backend.services.evaluation.repository import AgentEvaluationRepository
        mock_eval = MagicMock()
        mock_eval.get_by_run_id = AsyncMock(return_value=None)
        with patch.object(
            AgentEvaluationRepository, "__new__", return_value=mock_eval
        ):
            result = await service.get_run(str(run_id))

        assert result is not None
        assert result["evaluation_score"] is None
        assert result["evaluation_criteria"] is None


class TestListAgentRunsBatchEvaluation:
    @pytest.mark.asyncio
    async def test_list_agent_runs_includes_evaluation_scores(self, service, mock_session):
        """list_agent_runs batch-fetches evaluations and adds scores."""
        user_id = uuid.uuid4()
        run1_id = uuid.uuid4()
        run2_id = uuid.uuid4()

        fake_run1 = MagicMock()
        fake_run1.id = run1_id
        fake_run1.user_id = user_id
        fake_run1.started_at = datetime.now(timezone.utc)
        fake_run1.status = "completed"
        fake_run1.output_payload = {"result": "a"}
        fake_run1.input_payload = {"topic": "t1"}
        fake_run1.retry_count = 0

        from backend.services.evaluation.repository import AgentEvaluationRepository
        mock_eval = MagicMock()
        mock_eval.get_by_run_ids = AsyncMock(
            return_value=[MagicMock(agent_run_id=run1_id, score=85.0)]
        )
        with patch.object(AgentEvaluationRepository, "__new__", return_value=mock_eval):
            with patch.object(service._request_session, 'execute') as mock_exec:
                result_mock = MagicMock()
                result_mock.scalars.return_value.all.return_value = [fake_run1]
                mock_exec.return_value = result_mock

                runs = await service.list_agent_runs(user_id)

        assert len(runs) == 1
        assert runs[0]["evaluation_score"] == 85.0
