"""Tests for router registration and OpenAPI metadata."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app


class FakeSessionCtx:
    """Context manager that yields a fake session without hitting the DB."""

    async def __aenter__(self):
        return MagicMock()

    async def __aexit__(self, *a):
        pass


def _make_client() -> TestClient:
    """Create TestClient with get_session_factory patched to avoid real DB."""
    app = create_app()
    return TestClient(app)


class TestRouterRegistration:
    """Verify every sub-router is registered under /api/v1/."""

    EXPECTED_PATHS = [
        "/api/health",
        "/api/v1/articles",
        "/api/v1/knowledge",
        "/api/v1/tasks",
        "/api/v1/agents/runs",
        "/api/v1/reports",
    ]

    def test_openapi_paths_exist(self) -> None:
        schema = _make_client().get("/openapi.json").json()
        paths = list(schema["paths"].keys())
        for expected in self.EXPECTED_PATHS:
            assert expected in paths, f"Missing path: {expected}"

    @pytest.mark.parametrize("path", EXPECTED_PATHS)
    def test_each_path_has_summary(self, path: str) -> None:
        schema = _make_client().get("/openapi.json").json()
        endpoint = schema["paths"][path].get("get")
        assert endpoint is not None, f"No GET operation for {path}"
        assert endpoint.get("summary"), f"Missing summary for {path}"

    @pytest.mark.parametrize("path", EXPECTED_PATHS)
    def test_each_path_has_operation_id(self, path: str) -> None:
        schema = _make_client().get("/openapi.json").json()
        endpoint = schema["paths"][path].get("get")
        assert endpoint is not None
        assert endpoint.get("operationId"), f"Missing operationId for {path}"

    @pytest.mark.parametrize("path", EXPECTED_PATHS)
    def test_each_path_has_tags(self, path: str) -> None:
        schema = _make_client().get("/openapi.json").json()
        endpoint = schema["paths"][path].get("get")
        assert endpoint is not None
        tags = endpoint.get("tags", [])
        assert len(tags) > 0, f"No tags defined for {path}"


class TestHealthEndpoint:
    def test_health_returns_ok(self) -> None:
        client = _make_client()
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
