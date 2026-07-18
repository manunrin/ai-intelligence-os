"""Tests for audit log router endpoints — list_audit_logs and audit_stats."""

from __future__ import annotations

import uuid
from collections import namedtuple
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app


def _make_mock_session():
    """Build a mock async session with chainable execute()."""
    result = MagicMock()
    result.scalars = MagicMock(return_value=result)
    result.all = MagicMock(return_value=[])
    result.scalar_one_or_none = MagicMock(return_value=None)

    class MockSession:
        execute = AsyncMock(return_value=result)
        add = AsyncMock()
        commit = AsyncMock()
        flush = AsyncMock()
        close = AsyncMock()

    return MockSession()


@pytest.fixture()
def mock_db():
    return _make_mock_session()


@pytest.fixture()
def admin_client(mock_db):
    """Test client with admin user authenticated via dependency override."""
    fake_user = MagicMock()
    fake_user.id = uuid.uuid4()
    fake_user.username = "admin"
    fake_user.role = "admin"
    fake_user.is_active = True

    app = create_app()

    from backend.routers.deps import get_db, get_current_user

    async def mock_get_db():
        yield mock_db

    async def mock_get_current_user():
        return fake_user

    app.dependency_overrides[get_db] = mock_get_db
    app.dependency_overrides[get_current_user] = mock_get_current_user

    yield TestClient(app)
    app.dependency_overrides.clear()


# Namedtuple mimics SQLAlchemy row access (e.g., row.day, row.cnt)
_SqlRow = namedtuple("SqlRow", ["day", "cnt"])


class TestListAuditLogs:
    def test_requires_admin_role(self, mock_db):
        """list_audit_logs requires admin role — unauthenticated returns 401."""
        app = create_app()
        client = TestClient(app)
        resp = client.get("/api/v1/admin/audit-logs")
        assert resp.status_code == 401

    def test_list_audit_logs_success(self, admin_client, mock_db):
        """Successful list returns APIResponse with data array."""
        fake_log = MagicMock()
        fake_log.id = uuid.uuid4()
        fake_log.action = "create"
        fake_log.resource_type = "article"
        fake_log.resource_id = uuid.uuid4()
        fake_log.user_id = uuid.uuid4()
        fake_log.ip_address = "10.0.0.1"
        fake_log.user_agent = "Test/1.0"
        fake_log.metadata_ = {"key": "val"}
        fake_log.created_at = datetime.now(timezone.utc)

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [fake_log]
        mock_db.execute = AsyncMock(return_value=result_mock)

        resp = admin_client.get("/api/v1/admin/audit-logs?limit=10")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "data" in body


class TestAuditStats:
    def test_stats_requires_admin_role(self, mock_db):
        """audit_stats requires admin role."""
        app = create_app()
        client = TestClient(app)
        resp = client.get("/api/v1/admin/audit-logs/stats")
        assert resp.status_code == 401

    def test_audit_stats_success(self, admin_client, mock_db):
        """Successful stats returns aggregated counts and trend."""
        # action_counts uses .all() → plain tuples
        # daily_trend uses .all() → named tuples with .day and .cnt
        action_row = MagicMock()
        action_row.all.return_value = [("create", 5), ("update", 3)]

        trend_row = MagicMock()
        trend_day = datetime(2026, 7, 18, tzinfo=timezone.utc)
        trend_row.all.return_value = [_SqlRow(day=trend_day, cnt=1)]

        # First call (action_counts) returns action_row, second (daily_trend) returns trend_row
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return action_row
            return trend_row

        mock_db.execute = AsyncMock(side_effect=side_effect)

        resp = admin_client.get("/api/v1/admin/audit-logs/stats?period=7d")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "data" in body

    def test_audit_stats_unknown_period_defaults_to_7d(self, admin_client, mock_db):
        """Unknown period value falls back to default of 7 days."""
        empty_result = MagicMock()
        empty_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=empty_result)

        resp = admin_client.get("/api/v1/admin/audit-logs/stats?period=invalid")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
