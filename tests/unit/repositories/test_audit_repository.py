"""Tests for AuditRepository — persistence and admin query methods."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.repositories.audit_repository import AuditRepository


def _make_mock_session():
    """Build a mock session with chainable execute() returning scalars().all()."""
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
def mock_session():
    return _make_mock_session()


@pytest.fixture()
def repo(mock_session):
    return AuditRepository(mock_session)


class TestAuditRepositoryCreate:
    @pytest.mark.asyncio
    async def test_create_adds_and_flushes(self, repo, mock_session):
        created_at = datetime.now(timezone.utc)
        result = await repo.create(
            user_id=uuid.uuid4(),
            action="create",
            resource_type="article",
            resource_id=uuid.uuid4(),
            metadata_={"key": "val"},
            ip_address="10.0.0.1",
            created_at=created_at,
        )
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()


class TestAuditRepositoryQueryLogs:
    @pytest.mark.asyncio
    async def test_query_logs_empty(self, repo, mock_session):
        result = await repo.query_logs()
        assert result == []
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_query_logs_with_action_filter(self, repo, mock_session):
        result = await repo.query_logs(action="create")
        assert result == []
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_query_logs_with_resource_type_filter(self, repo, mock_session):
        result = await repo.query_logs(resource_type="article")
        assert result == []
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_query_logs_with_user_id_filter(self, repo, mock_session):
        user_id = uuid.uuid4()
        result = await repo.query_logs(user_id=user_id)
        assert result == []
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_query_logs_with_date_range(self, repo, mock_session):
        start = datetime.now(timezone.utc) - timedelta(days=1)
        end = datetime.now(timezone.utc)
        result = await repo.query_logs(start_date=start, end_date=end)
        assert result == []
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_query_logs_with_pagination(self, repo, mock_session):
        result = await repo.query_logs(offset=10, limit=5)
        assert result == []
        mock_session.execute.assert_awaited_once()


class TestAuditRepositoryActionCounts:
    @pytest.mark.asyncio
    async def test_action_counts_returns_dict(self, repo, mock_session):
        result = await repo.action_counts(days=7)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_action_counts_custom_days(self, repo, mock_session):
        result = await repo.action_counts(days=30)
        assert isinstance(result, dict)


class TestAuditRepositoryDailyTrend:
    @pytest.mark.asyncio
    async def test_daily_trend_returns_list(self, repo, mock_session):
        result = await repo.daily_trend(days=7)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_daily_trend_custom_days(self, repo, mock_session):
        result = await repo.daily_trend(days=90)
        assert isinstance(result, list)
