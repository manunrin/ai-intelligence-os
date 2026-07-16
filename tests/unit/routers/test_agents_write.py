"""Tests for agent run endpoint — POST /agents/{id}/run."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app


class FakeSessionCtx:
    async def __aenter__(self):
        return MagicMock()

    async def __aexit__(self, *a):
        pass


class TrackingService:
    def __init__(self, db):
        self._db = db

    async def run_agent(self, agent_id, input_payload=None):
        return {
            "id": str(uuid.uuid4()), "agent_id": str(uuid.uuid4()),
            "workflow_id": None, "status": "running",
            "input_payload": input_payload or {},
            "output_payload": None, "error_message": None,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
        }


def _make_client():
    from unittest.mock import MagicMock
    import uuid as _uuid

    fake_user = MagicMock()
    fake_user.id = _uuid.uuid4()
    fake_user.username = "testuser"
    fake_user.role = "user"
    fake_user.is_active = True

    from backend.main import create_app
    from backend.routers.deps import get_current_user

    app = create_app()

    async def mock_get_current_user():
        return fake_user

    app.dependency_overrides[get_current_user] = mock_get_current_user
    return TestClient(app), app


class TestAgentRun:
    def test_post_run_agent(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.agents.AgentService", TrackingService):
                resp = client.post(
                    f"/api/v1/agents/{uuid.uuid4()}/run",
                    json={"query": "test"},
                )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["status"] == "running"
        app.dependency_overrides.clear()

    def test_post_run_agent_no_body(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.agents.AgentService", TrackingService):
                resp = client.post(f"/api/v1/agents/{uuid.uuid4()}/run")
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "running"
        app.dependency_overrides.clear()
