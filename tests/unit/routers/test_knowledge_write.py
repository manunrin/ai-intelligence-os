"""Tests for knowledge item write endpoints — POST, GET, PUT, DELETE, 404, validation."""

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

    async def get_knowledge_item(self, iid):
        return {
            "id": str(uuid.uuid4()), "title": "Found", "content": "Here",
            "kind": "note", "article_id": None, "tags": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    async def create_knowledge_item(self, data):
        return {
            "id": str(uuid.uuid4()), "title": "New Item", "content": "Data",
            "kind": "note", "article_id": None, "tags": ["test"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    async def update_knowledge_item(self, iid, data):
        return {
            "id": str(uuid.uuid4()), "title": "Updated", "content": "Here",
            "kind": "note", "article_id": None, "tags": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    async def delete_knowledge_item(self, iid):
        return True


class NotFoundService(TrackingService):
    async def get_knowledge_item(self, iid):
        return None

    async def update_knowledge_item(self, iid, data):
        return None

    async def delete_knowledge_item(self, iid):
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


class TestKnowledgeCreate:
    def test_post_create(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.knowledge.KnowledgeService", TrackingService):
                resp = client.post("/api/v1/knowledge", json={
                    "title": "New Item", "content": "Data", "kind": "note"
                })
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "New Item"
        app.dependency_overrides.clear()

    def test_post_validation_error_missing_content(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            resp = client.post("/api/v1/knowledge", json={"title": "T", "kind": "x"})
        assert resp.status_code == 422
        app.dependency_overrides.clear()


class TestKnowledgeGetById:
    def test_get_found(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.knowledge.KnowledgeService", TrackingService):
                resp = client.get(f"/api/v1/knowledge/{uuid.uuid4()}")
        assert resp.status_code == 200
        app.dependency_overrides.clear()

    def test_get_not_found_returns_404(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.knowledge.KnowledgeService", NotFoundService):
                resp = client.get(f"/api/v1/knowledge/{uuid.uuid4()}")
        assert resp.status_code == 404
        app.dependency_overrides.clear()


class TestKnowledgeUpdate:
    def test_put_update(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.knowledge.KnowledgeService", TrackingService):
                resp = client.put(f"/api/v1/knowledge/{uuid.uuid4()}", json={"title": "Updated"})
        assert resp.status_code == 200
        app.dependency_overrides.clear()

    def test_put_not_found_returns_404(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.knowledge.KnowledgeService", NotFoundService):
                resp = client.put(f"/api/v1/knowledge/{uuid.uuid4()}", json={"title": "X"})
        assert resp.status_code == 404
        app.dependency_overrides.clear()


class TestKnowledgeDelete:
    def test_delete_success(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.knowledge.KnowledgeService", TrackingService):
                resp = client.delete(f"/api/v1/knowledge/{uuid.uuid4()}")
        assert resp.status_code == 200
        app.dependency_overrides.clear()

    def test_delete_not_found_returns_404(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.knowledge.KnowledgeService", NotFoundService):
                resp = client.delete(f"/api/v1/knowledge/{uuid.uuid4()}")
        assert resp.status_code == 404
        app.dependency_overrides.clear()
