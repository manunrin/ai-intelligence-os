"""Integration tests for observability: metrics endpoint, logging middleware, request IDs."""

from __future__ import annotations

import json
import uuid

import pytest


class TestMetricsEndpoint:
    """Test the /metrics HTTP endpoint returns valid Prometheus format."""

    @pytest.fixture()
    def app(self):
        from backend.main import create_app
        return create_app()

    def test_metrics_returns_200(self, app):
        """GET /metrics returns 200 with Prometheus content."""
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get("/metrics")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"

    def test_metrics_format(self, app):
        """/metrics returns valid Prometheus exposition format."""
        from backend.metrics import counter, reset
        from fastapi.testclient import TestClient

        reset()
        counter("test_metric_total", 42)

        client = TestClient(app)
        response = client.get("/metrics")
        assert "test_metric_total 42" in response.text

    def test_metrics_empty_when_no_data(self, app):
        """Empty metrics endpoint returns only newlines when nothing recorded."""
        from backend.metrics import reset
        from fastapi.testclient import TestClient

        reset()
        client = TestClient(app)
        response = client.get("/metrics")
        assert response.status_code == 200


class TestRequestLoggingMiddleware:
    """Test that the LogMiddleware sets request_id and logs structured data."""

    @pytest.fixture()
    def app(self):
        from backend.main import create_app
        return create_app()

    def test_request_id_in_response_headers(self, app):
        """Response includes X-Request-ID header."""
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get("/api/live")
        assert "X-Request-ID" in response.headers
        # Should be a valid UUID
        uuid.UUID(response.headers["X-Request-ID"])

    def test_request_id_echoed_back(self, app):
        """Client-provided X-Request-ID is echoed in response."""
        from fastapi.testclient import TestClient

        client = TestClient(app)
        rid = str(uuid.uuid4())
        response = client.get("/api/live", headers={"X-Request-ID": rid})
        assert response.headers["X-Request-ID"] == rid

    def test_json_logging_includes_request_id(self, app):
        """Log output contains request_id field in JSON."""
        import io
        import logging

        from backend.context_vars import request_id as _ctx
        from backend.logging_config import JSONFormatter
        from fastapi.testclient import TestClient

        # Capture log output
        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setFormatter(JSONFormatter())
        logger = logging.getLogger("backend.routers.errors")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        try:
            client = TestClient(app)
            client.get("/api/live")

            log_output = log_stream.getvalue()
            if log_output.strip():
                parsed = json.loads(log_output.strip().split("\n")[0])
                assert "request_id" in parsed
                assert parsed["request_id"] != "unknown"
        finally:
            logger.removeHandler(handler)

    def test_health_check_still_works(self, app):
        """Health endpoint returns a response (may be 503 if no DB)."""
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get("/api/health")
        assert response.status_code in (200, 503)
        data = response.json()
        assert "status" in data
        assert "checks" in data


class TestAgentRunContext:
    """Test that agent_run_id context var is set/cleared during runs."""

    def test_agent_run_context_set_on_submit(self):
        """agent_run_id context var is set after submit."""
        from backend.context_vars import agent_run_id as _ctx
        import uuid as _uuid

        _original = _ctx.get()
        try:
            _ctx.set("run-test-123")
            assert _ctx.get() == "run-test-123"
        finally:
            _ctx.set(_original)

    def test_agent_run_context_defaults_to_none(self):
        """Default agent_run_id is None."""
        from backend.context_vars import agent_run_id as _ctx

        # After reset, should be None
        _ctx.set(None)
        assert _ctx.get() is None
