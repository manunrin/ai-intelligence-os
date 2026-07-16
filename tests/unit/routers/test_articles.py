"""Tests for article router — pagination, dependency override, empty DB."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture()
def client():
    app = create_app()
    return TestClient(app)


def _fake_article(**kwargs):
    """Build a MagicMock that mimics an ORM Article model instance."""
    now = datetime.now(timezone.utc)
    fake = MagicMock()
    fake.id = kwargs.get("id", "550e8400-e29b-41d4-a716-446655440000")
    fake.title = kwargs.get("title", "Test Article")
    fake.summary = kwargs.get("summary", "A test summary")
    fake.content = kwargs.get("content", "Content here")
    fake.url = kwargs.get("url", None)
    fake.source = MagicMock()
    fake.source.name = kwargs.get("source", "rss")
    fake.language = kwargs.get("language", "en")
    fake.tags = kwargs.get("tags", [])
    fake.status = kwargs.get("status", "raw")
    fake.fetched_at = kwargs.get("fetched_at", now)
    fake.published_at = kwargs.get("published_at", None)
    fake.metadata_ = kwargs.get("metadata_", {"tags": []})
    return fake


class FakeSessionCtx:
    """Context manager that yields a fake session without hitting the DB."""

    async def __aenter__(self):
        return MagicMock()

    async def __aexit__(self, *a):
        pass


# ------------------------------------------------------------------
# Dependency override tests
# ------------------------------------------------------------------

class TestDependencyOverride:
    """Use FastAPI TestClient with patched get_session_factory to avoid real DB."""

    def test_empty_database_returns_empty_list(self, client: TestClient) -> None:
        """When the repository returns no rows, data should be []."""

        class FakeRepo:
            def __init__(self, session):
                self.session = session

            async def list_all(self, *, offset=0, limit=20, order_by=None, descending=True):
                return []

            async def count(self):
                return 0

        # Patch where ArticleService imports it from
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.services.article_service.ArticleRepository", FakeRepo):
                resp = client.get("/api/v1/articles")

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"] == []
        assert body["error"] is None

    def test_pagination_params_passed_to_service(self, client: TestClient) -> None:
        """Verify offset/limit query params are forwarded."""
        captured: dict[str, int] = {}

        class TrackingRepo:
            def __init__(self, session):
                self.session = session

            async def list_all(self, *, offset=0, limit=20, order_by=None, descending=True):
                captured["offset"] = offset
                captured["limit"] = limit
                return []

            async def count(self):
                return 0

        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.services.article_service.ArticleRepository", TrackingRepo):
                resp = client.get("/api/v1/articles?offset=10&limit=5")

        assert resp.status_code == 200
        assert captured.get("offset") == 10
        assert captured.get("limit") == 5

    def test_default_pagination_values(self, client: TestClient) -> None:
        """Without query params, defaults should be offset=0, limit=20."""
        captured: dict[str, int] = {}

        class TrackingRepo:
            def __init__(self, session):
                self.session = session

            async def list_all(self, *, offset=0, limit=20, order_by=None, descending=True):
                captured["offset"] = offset
                captured["limit"] = limit
                return []

            async def count(self):
                return 0

        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.services.article_service.ArticleRepository", TrackingRepo):
                resp = client.get("/api/v1/articles")

        assert resp.status_code == 200
        assert captured.get("offset") == 0
        assert captured.get("limit") == 20


# ------------------------------------------------------------------
# Response schema validation
# ------------------------------------------------------------------

class TestResponseSchema:
    def test_article_response_contains_required_fields(self, client: TestClient) -> None:
        """The response must conform to APIResponse[list[ArticleResponse]]."""
        now = datetime.now(timezone.utc)
        fake_art = _fake_article(
            title="Test Article",
            summary="A test summary",
            content="Content here",
            url="http://example.com",
            source="rss",
            language="en",
            tags=["a", "b"],
            status="raw",
            fetched_at=now,
            published_at=now,
        )

        class SnapshotRepo:
            def __init__(self, session):
                self.session = session

            async def list_all(self, *, offset=0, limit=20, order_by=None, descending=True):
                return [fake_art]

            async def count(self):
                return 1

        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.services.article_service.ArticleRepository", SnapshotRepo):
                resp = client.get("/api/v1/articles")

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert isinstance(body["data"], list)
        assert len(body["data"]) == 1

        # Validate individual article fields
        article_data = body["data"][0]
        required_fields = [
            "id", "title", "summary", "content", "url",
            "source", "language", "tags", "status",
            "fetched_at", "published_at",
        ]
        for field in required_fields:
            assert field in article_data, f"Missing field: {field}"
