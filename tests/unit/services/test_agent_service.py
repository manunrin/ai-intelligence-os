"""Tests for agent service run_agent business logic."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock

import pytest

from backend.services.agent_service import AgentService


@pytest.fixture()
def mock_repo():
    repo = MagicMock()
    repo.list_all = AsyncMock(return_value=[])
    repo.create = AsyncMock()
    return repo


@pytest.fixture()
def service(mock_repo):
    session = MagicMock()
    svc = AgentService(session)
    svc._repo = mock_repo
    return svc


class TestAgentServiceRun:
    @pytest.mark.asyncio
    async def test_run_agent_creates_record(self, service):
        fake = MagicMock()
        fake.id = uuid.uuid4()
        fake.agent_id = uuid.uuid4()
        fake.workflow_id = None
        fake.status = "running"
        fake.input_payload = {"query": "test"}
        fake.output_payload = None
        fake.error_message = None
        fake.started_at = datetime.now(timezone.utc)
        fake.finished_at = None
        service._repo.create = AsyncMock(return_value=fake)

        result = await service.run_agent(str(fake.agent_id), input_payload={"query": "test"})
        assert result["status"] == "running"
        assert result["input_payload"] == {"query": "test"}
        service._repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_agent_default_payload(self, service):
        fake = MagicMock()
        fake.id = uuid.uuid4()
        fake.agent_id = uuid.uuid4()
        fake.workflow_id = None
        fake.status = "running"
        fake.input_payload = {}
        fake.output_payload = None
        fake.error_message = None
        fake.started_at = datetime.now(timezone.utc)
        fake.finished_at = None
        service._repo.create = AsyncMock(return_value=fake)

        result = await service.run_agent(str(fake.agent_id))
        assert result["status"] == "running"
        assert result["input_payload"] == {}
