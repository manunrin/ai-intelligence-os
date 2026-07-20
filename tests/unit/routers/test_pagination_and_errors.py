"""Tests for pagination and exception handling in routers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app


class FakeSessionCtx:
    """Minimal async session that returns empty results for queries."""

    def __init__(self):
        self.commit = AsyncMock()
        self.rollback = AsyncMock()
        self.close = AsyncMock()
        self.add = AsyncMock()
        self.flush = AsyncMock()

        _result = MagicMock()
        _result.scalars = MagicMock(return_value=_result)
        _result.all = MagicMock(return_value=[])
        _result.scalar_one_or_none = MagicMock(return_value=None)
        self.execute = AsyncMock(return_value=_result)


def _make_client() -> TestClient:
    """Create TestClient with auth overridden and fake session."""
    import uuid as _uuid

    from backend.routers.deps import get_current_user

    fake_user = MagicMock()
    fake_user.id = _uuid.uuid4()
    fake_user.username = "testuser"
    fake_user.role = "user"
    fake_user.is_active = True

    app = create_app()

    # A1: session_factory must be callable that returns a real fake session
    app.state.session_factory = FakeSessionCtx

    # Mock embedding and vector services for knowledge endpoints
    app.state.embedding_client = MagicMock()
    app.state.vector_service = MagicMock()

    async def mock_get_current_user():
        return fake_user

    app.dependency_overrides[get_current_user] = mock_get_current_user
    client = TestClient(app)
    return client


# ------------------------------------------------------------------
# Pagination tests — exercise multiple endpoints
# ------------------------------------------------------------------

class TestPagination:
    """Ensure pagination params are accepted on every list endpoint."""

    @pytest.mark.parametrize("url", [
        "/api/v1/knowledge?offset=2&limit=5",
        "/api/v1/tasks?offset=0&limit=3",
        "/api/v1/agents/runs?offset=1&limit=2",
        "/api/v1/reports?offset=0&limit=50",
    ])
    def test_stub_endpoints_accept_pagination(self, url: str) -> None:
        """All stub endpoints should accept offset/limit and return 200."""
        client = _make_client()
        resp = client.get(url)

        assert resp.status_code == 200, f"{url} returned {resp.status_code}: {resp.text[:200]}"
        body = resp.json()
        assert body["success"] is True
        assert isinstance(body["data"], list)


# ------------------------------------------------------------------
# Exception handling
# ------------------------------------------------------------------

class TestExceptionHandling:
    """Centralized exception handlers convert errors to JSON."""

    def test_health_no_exception(self) -> None:
        client = _make_client()
        resp = client.get("/api/health")
        assert resp.status_code in (200, 503)

    def test_openapi_schema_accessible_directly(self) -> None:
        """If OpenAPI spec is accessible, generic exception handler didn't break things."""
        client = _make_client()
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "paths" in data
        assert len(data["paths"]) >= 6
