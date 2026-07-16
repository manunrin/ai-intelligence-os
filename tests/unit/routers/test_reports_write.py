"""Tests for report write endpoints — POST, GET by ID, validation errors."""

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

    async def get_report(self, rid):
        return {
            "id": str(uuid.uuid4()), "topic": "Found",
            "research_result": None, "analysis_result": None,
            "translation_result": None, "knowledge_items": [], "tasks": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    async def create_report(self, data):
        return {
            "id": str(uuid.uuid4()), "topic": "New Report",
            "research_result": None, "analysis_result": None,
            "translation_result": None, "knowledge_items": [], "tasks": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }


class NotFoundService(TrackingService):
    async def get_report(self, rid):
        return None


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


class TestReportCreate:
    def test_post_create_report(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.reports.ReportService", TrackingService):
                resp = client.post("/api/v1/reports", json={
                    "title": "New Report", "body": "Report body"
                })
        assert resp.status_code == 200
        assert resp.json()["data"]["topic"] == "New Report"
        app.dependency_overrides.clear()

    def test_post_validation_error_missing_body(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            resp = client.post("/api/v1/reports", json={"title": "T"})
        assert resp.status_code == 422
        app.dependency_overrides.clear()

    def test_post_validation_error_importance_too_high(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            resp = client.post("/api/v1/reports", json={
                "title": "T", "body": "B", "importance_score": 15
            })
        assert resp.status_code == 422
        app.dependency_overrides.clear()

    def test_post_validation_error_importance_negative(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            resp = client.post("/api/v1/reports", json={
                "title": "T", "body": "B", "importance_score": -5
            })
        assert resp.status_code == 422
        app.dependency_overrides.clear()


class TestReportGetById:
    def test_get_found(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.reports.ReportService", TrackingService):
                resp = client.get(f"/api/v1/reports/{uuid.uuid4()}")
        assert resp.status_code == 200
        assert resp.json()["data"]["topic"] == "Found"
        app.dependency_overrides.clear()

    def test_get_not_found_returns_404(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.routers.reports.ReportService", NotFoundService):
                resp = client.get(f"/api/v1/reports/{uuid.uuid4()}")
        assert resp.status_code == 404
        app.dependency_overrides.clear()
