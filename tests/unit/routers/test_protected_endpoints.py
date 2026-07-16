"""Tests for protected write endpoints — 401 without valid token."""

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


class ProtectedTrackingService:
    """Mock service that returns predictable responses."""

    def __init__(self, db):
        self._db = db

    async def create_article(self, data):
        return {
            "id": str(uuid.uuid4()), "title": "Created", "source": "rss",
            "status": "raw", "language": "en", "tags": [], "summary": None,
            "content": None, "url": None,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "published_at": None,
        }

    async def create_task(self, data):
        return {
            "id": str(uuid.uuid4()), "title": "New Task", "description": None,
            "priority": "medium", "status": "pending", "dependency": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    async def create_knowledge_item(self, data):
        return {
            "id": str(uuid.uuid4()), "title": "New Item", "content": "Data",
            "kind": "note", "article_id": None, "tags": ["test"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    async def create_report(self, data):
        return {
            "id": str(uuid.uuid4()), "topic": "New Report",
            "research_result": None, "analysis_result": None,
            "translation_result": None, "knowledge_items": [], "tasks": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

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


class TestProtectedEndpointsWithoutToken:
    """Write endpoints should return 401 when no valid JWT token is provided."""

    def test_articles_post_requires_auth(self):
        # Create app WITHOUT dependency override — no authenticated user
        from backend.main import create_app
        app = create_app()
        client = TestClient(app)
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            resp = client.post("/api/v1/articles", json={
                "title": "Test", "source_id": str(uuid.uuid4()),
            })
        assert resp.status_code == 401
        client.close()

    def test_tasks_post_requires_auth(self):
        from backend.main import create_app
        app = create_app()
        client = TestClient(app)
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            resp = client.post("/api/v1/tasks", json={"title": "Test"})
        assert resp.status_code == 401
        client.close()

    def test_knowledge_post_requires_auth(self):
        from backend.main import create_app
        app = create_app()
        client = TestClient(app)
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            resp = client.post("/api/v1/knowledge", json={
                "title": "Test", "content": "Data", "kind": "note",
            })
        assert resp.status_code == 401
        client.close()

    def test_reports_post_requires_auth(self):
        from backend.main import create_app
        app = create_app()
        client = TestClient(app)
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            resp = client.post("/api/v1/reports", json={
                "title": "Test", "body": "Body",
            })
        assert resp.status_code == 401
        client.close()

    def test_agents_run_requires_auth(self):
        from backend.main import create_app
        app = create_app()
        client = TestClient(app)
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            resp = client.post(f"/api/v1/agents/{uuid.uuid4()}/run")
        assert resp.status_code == 401
        client.close()


class TestProtectedEndpointsWithValidToken:
    """Write endpoints should succeed when authenticated."""

    def test_articles_post_with_token(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.articles.ArticleService", ProtectedTrackingService):
                resp = client.post(
                    "/api/v1/articles",
                    json={"title": "Test", "source_id": str(uuid.uuid4())},
                )
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "Created"
        app.dependency_overrides.clear()

    def test_tasks_post_with_token(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.tasks.TaskService", ProtectedTrackingService):
                resp = client.post("/api/v1/tasks", json={"title": "Test"})
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "New Task"
        app.dependency_overrides.clear()

    def test_knowledge_post_with_token(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.knowledge.KnowledgeService", ProtectedTrackingService):
                resp = client.post(
                    "/api/v1/knowledge",
                    json={"title": "Test", "content": "Data", "kind": "note"},
                )
        assert resp.status_code == 200
        app.dependency_overrides.clear()

    def test_reports_post_with_token(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.reports.ReportService", ProtectedTrackingService):
                resp = client.post(
                    "/api/v1/reports",
                    json={"title": "Test", "body": "Body"},
                )
        assert resp.status_code == 200
        app.dependency_overrides.clear()

    def test_agents_run_with_token(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.agents.AgentService", ProtectedTrackingService):
                resp = client.post(f"/api/v1/agents/{uuid.uuid4()}/run")
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "running"
        app.dependency_overrides.clear()
