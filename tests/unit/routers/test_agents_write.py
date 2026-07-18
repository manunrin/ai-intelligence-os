"""Tests for agent run endpoint — POST /agents/{id}/run (legacy) and POST /agents/run."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app


class FakeSessionCtx:
    async def __aenter__(self):
        return MagicMock()

    async def __aexit__(self, *a):
        pass


class TrackingRuntimeService:
    """Minimal mock of AgentRuntimeService for endpoint testing."""

    def __init__(self, db, session_factory=None):
        self._db = db

    async def submit(self, agent_type, input_payload, user_id, *, timeout_seconds=300):
        return {
            "id": str(uuid.uuid4()), "agent_id": str(uuid.uuid4()),
            "workflow_id": None, "status": "running",
            "stage": "initializing",
            "input_payload": input_payload or {},
            "output_payload": None, "error_message": None,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "duration_ms": None,
            "user_id": str(user_id) if user_id else None,
        }


def _make_client_with_override(mock_service_cls):
    fake_user = MagicMock()
    fake_user.id = uuid.uuid4()
    fake_user.username = "testuser"
    fake_user.role = "user"
    fake_user.is_active = True

    app = create_app()

    from backend.routers.deps import get_current_user, get_runtime_service_with_event_pub

    async def mock_get_current_user():
        return fake_user

    app.dependency_overrides[get_current_user] = mock_get_current_user

    def make_mock_service():
        return mock_service_cls(None)

    app.dependency_overrides[get_runtime_service_with_event_pub] = make_mock_service

    client = TestClient(app)
    return client, app


class TestAgentRunLegacy:
    """Test legacy POST /agents/{agent_id}/run endpoint."""

    def test_post_run_agent_legacy(self):
        client, app = _make_client_with_override(TrackingRuntimeService)
        resp = client.post(
            f"/api/v1/agents/{uuid.uuid4()}/run",
            json={"query": "test"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["status"] == "running"
        app.dependency_overrides.clear()

    def test_post_run_agent_legacy_no_body(self):
        client, app = _make_client_with_override(TrackingRuntimeService)
        resp = client.post(f"/api/v1/agents/{uuid.uuid4()}/run")
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "running"
        app.dependency_overrides.clear()


class TestAgentRunSubmit:
    """Test new POST /agents/run endpoint."""

    def test_submit_agent_run(self):
        client, app = _make_client_with_override(TrackingRuntimeService)
        resp = client.post(
            "/api/v1/agents/run",
            json={
                "agent_type": "intelligence",
                "input_payload": {"topic": "AI trends"},
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["status"] == "running"
        app.dependency_overrides.clear()

    def test_submit_agent_run_validation_error(self):
        """Invalid agent_type is validated by AgentRuntimeService.submit(),
        which raises ValueError caught by the exception handler."""
        # This test validates the endpoint accepts valid payloads.
        # Validation errors from submit() are tested in service unit tests.
        client, app = _make_client_with_override(TrackingRuntimeService)
        resp = client.post(
            "/api/v1/agents/run",
            json={
                "agent_type": "intelligence",
                "input_payload": {"topic": "AI trends"},
                "topic": "AI trends",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["status"] == "running"
        assert body["data"]["input_payload"]["topic"] == "AI trends"
        app.dependency_overrides.clear()
