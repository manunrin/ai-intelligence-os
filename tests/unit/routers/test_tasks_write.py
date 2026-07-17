"""Tests for task write endpoints — POST, GET, PUT, DELETE, 404, validation."""

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

    async def get_task(self, tid, user_id=None):
        return {
            "id": str(uuid.uuid4()), "title": "Found", "description": None,
            "priority": "high", "status": "pending", "dependency": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    async def create_task(self, data, user_id=None):
        return {
            "id": str(uuid.uuid4()), "title": "New Task", "description": None,
            "priority": "medium", "status": "pending", "dependency": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    async def update_task(self, tid, data, user_id=None):
        return {
            "id": str(uuid.uuid4()), "title": "Updated", "description": None,
            "priority": "high", "status": "in_progress", "dependency": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    async def delete_task(self, tid, user_id=None):
        return True


class NotFoundService(TrackingService):
    async def get_task(self, tid, user_id=None):
        return None

    async def update_task(self, tid, data, user_id=None):
        return None

    async def delete_task(self, tid, user_id=None):
        return False


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


class TestTaskCreate:
    def test_post_create_task(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.tasks.TaskService", TrackingService):
                resp = client.post("/api/v1/tasks", json={"title": "New Task"})
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "New Task"
        app.dependency_overrides.clear()

    def test_post_validation_error_missing_title(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            resp = client.post("/api/v1/tasks", json={"priority": "high"})
        assert resp.status_code == 422
        app.dependency_overrides.clear()


class TestTaskGetById:
    def test_get_found(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.tasks.TaskService", TrackingService):
                resp = client.get(f"/api/v1/tasks/{uuid.uuid4()}")
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "Found"
        app.dependency_overrides.clear()

    def test_get_not_found_returns_404(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.tasks.TaskService", NotFoundService):
                resp = client.get(f"/api/v1/tasks/{uuid.uuid4()}")
        assert resp.status_code == 404
        app.dependency_overrides.clear()


class TestTaskUpdate:
    def test_put_update(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.tasks.TaskService", TrackingService):
                resp = client.put(f"/api/v1/tasks/{uuid.uuid4()}", json={"status": "in_progress"})
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "in_progress"
        app.dependency_overrides.clear()

    def test_put_not_found_returns_404(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.tasks.TaskService", NotFoundService):
                resp = client.put(f"/api/v1/tasks/{uuid.uuid4()}", json={"title": "X"})
        assert resp.status_code == 404
        app.dependency_overrides.clear()


class TestTaskDelete:
    def test_delete_success(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.tasks.TaskService", TrackingService):
                resp = client.delete(f"/api/v1/tasks/{uuid.uuid4()}")
        assert resp.status_code == 200
        app.dependency_overrides.clear()

    def test_delete_not_found_returns_404(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.tasks.TaskService", NotFoundService):
                resp = client.delete(f"/api/v1/tasks/{uuid.uuid4()}")
        assert resp.status_code == 404
        app.dependency_overrides.clear()
