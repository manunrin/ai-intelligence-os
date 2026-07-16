"""Tests for article write endpoints — POST, PUT, DELETE, 404, validation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app


@pytest.fixture()
def client():
    app = create_app()
    return TestClient(app)


class FakeSessionCtx:
    async def __aenter__(self):
        return MagicMock()

    async def __aexit__(self, *a):
        pass


class TrackingService:
    """Mock service that returns predictable responses per method call."""

    def __init__(self, db):
        self._db = db

    async def get_article(self, aid):
        return {
            "id": str(uuid.uuid4()), "title": "Found", "source": "rss",
            "status": "raw", "language": "en", "tags": [], "summary": "S",
            "content": "C", "url": None,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "published_at": None,
        }

    async def create_article(self, data):
        return {
            "id": str(uuid.uuid4()), "title": "Created", "source": "rss",
            "status": "raw", "language": "en", "tags": [], "summary": None,
            "content": None, "url": None,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "published_at": None,
        }

    async def update_article(self, aid, data):
        return {
            "id": str(uuid.uuid4()), "title": "Updated", "source": "rss",
            "status": "raw", "language": "en", "tags": [], "summary": None,
            "content": None, "url": None,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "published_at": None,
        }

    async def delete_article(self, aid):
        return True


class TestArticleCreate:
    def test_post_create_article(self, client):
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.articles.ArticleService", TrackingService):
                resp = client.post("/api/v1/articles", json={
                    "title": "Created", "source_id": str(uuid.uuid4()),
                })
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["title"] == "Created"

    def test_post_validation_error_missing_title(self, client):
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            resp = client.post("/api/v1/articles", json={"source_id": str(uuid.uuid4())})
        assert resp.status_code == 422

    def test_post_validation_error_empty_title(self, client):
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            resp = client.post("/api/v1/articles", json={"title": "", "source_id": str(uuid.uuid4())})
        assert resp.status_code == 422


class TestArticleGetById:
    def test_get_found(self, client):
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.articles.ArticleService", TrackingService):
                resp = client.get(f"/api/v1/articles/{uuid.uuid4()}")
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "Found"

    def test_get_not_found_returns_404(self, client):
        class NotFoundService(TrackingService):
            async def get_article(self, aid):
                return None

        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.articles.ArticleService", NotFoundService):
                resp = client.get(f"/api/v1/articles/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestArticleUpdate:
    def test_put_update(self, client):
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.articles.ArticleService", TrackingService):
                resp = client.put(f"/api/v1/articles/{uuid.uuid4()}", json={"title": "Updated"})
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "Updated"

    def test_put_not_found_returns_404(self, client):
        class NotFoundService(TrackingService):
            async def update_article(self, aid, data):
                return None

        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.articles.ArticleService", NotFoundService):
                resp = client.put(f"/api/v1/articles/{uuid.uuid4()}", json={"title": "X"})
        assert resp.status_code == 404


class TestArticleDelete:
    def test_delete_success(self, client):
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.articles.ArticleService", TrackingService):
                resp = client.delete(f"/api/v1/articles/{uuid.uuid4()}")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_delete_not_found_returns_404(self, client):
        class NotFoundService(TrackingService):
            async def delete_article(self, aid):
                return False

        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.articles.ArticleService", NotFoundService):
                resp = client.delete(f"/api/v1/articles/{uuid.uuid4()}")
        assert resp.status_code == 404
