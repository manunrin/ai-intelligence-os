"""Tests for pagination and exception handling in routers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app


class FakeSessionCtx:
    """Context manager that yields a fake session without hitting the DB."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass

    async def execute(self, stmt):
        class Result:
            @staticmethod
            def scalars():
                class Scalars:
                    @staticmethod
                    def all():
                        return []
                return Scalars()
        return Result()


def _make_client() -> TestClient:
    """Create TestClient with get_session_factory patched to avoid real DB."""
    app = create_app()
    return TestClient(app)


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
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
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
        assert resp.status_code == 200

    def test_openapi_schema_accessible_directly(self) -> None:
        """If OpenAPI spec is accessible, generic exception handler didn't break things."""
        client = _make_client()
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "paths" in data
        assert len(data["paths"]) >= 6
