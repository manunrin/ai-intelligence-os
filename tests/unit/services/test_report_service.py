"""Tests for report service business logic."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock

import pytest

from backend.services.report_service import ReportService
from backend.schemas.report_create import ReportCreate, ReportUpdate


@pytest.fixture()
def mock_repo():
    repo = MagicMock()
    repo.list_all = AsyncMock(return_value=[])
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.update = AsyncMock(return_value=None)
    return repo


@pytest.fixture()
def service(mock_repo):
    session = MagicMock()
    svc = ReportService(session)
    svc._repo = mock_repo
    return svc


@pytest.fixture()
def fake_report():
    r = MagicMock()
    r.id = uuid.uuid4()
    r.title = "Test Report"
    r.body = "Report body"
    r.category = "security"
    r.importance_score = 7.5
    r.article_ids = []
    r.agent_run_id = None
    r.generated_by = None
    r.created_at = datetime.now(timezone.utc)
    return r


class TestReportServiceCreate:
    @pytest.mark.asyncio
    async def test_create_valid(self, service):
        fake = MagicMock()
        fake.id = uuid.uuid4()
        fake.title = "New Report"
        fake.body = "Body text"
        fake.category = "tech"
        fake.importance_score = 5.0
        fake.article_ids = []
        fake.agent_run_id = None
        fake.generated_by = None
        fake.created_at = datetime.now(timezone.utc)
        fake.user_id = None
        service._repo.create = AsyncMock(return_value=fake)

        data = ReportCreate(title="New Report", body="Body text")
        result = await service.create_report(data, user_id=uuid.uuid4())
        assert result["topic"] == "New Report"

    @pytest.mark.asyncio
    async def test_create_validates_required_fields(self):
        with pytest.raises(Exception):
            ReportCreate(title="", body="Data")

    @pytest.mark.asyncio
    async def test_create_validates_importance_range(self):
        with pytest.raises(Exception):
            ReportCreate(title="T", body="B", importance_score=11)

    @pytest.mark.asyncio
    async def test_create_validates_min_importance(self):
        with pytest.raises(Exception):
            ReportCreate(title="T", body="B", importance_score=-1)


class TestReportServiceUpdate:
    @pytest.mark.asyncio
    async def test_update_found(self, service):
        test_user_id = uuid.uuid4()
        fake = MagicMock()
        fake.id = uuid.uuid4()
        fake.title = "Test Report"
        fake.body = "Report body"
        fake.category = "security"
        fake.importance_score = 7.5
        fake.article_ids = []
        fake.agent_run_id = None
        fake.generated_by = None
        fake.created_at = datetime.now(timezone.utc)
        fake.user_id = test_user_id
        service._repo.get_by_id = AsyncMock(return_value=fake)
        updated = MagicMock()
        updated.id = fake.id
        updated.title = "Updated Report"
        updated.body = fake.body
        updated.category = fake.category
        updated.importance_score = fake.importance_score
        updated.article_ids = fake.article_ids
        updated.agent_run_id = fake.agent_run_id
        updated.generated_by = fake.generated_by
        updated.created_at = fake.created_at
        updated.user_id = fake.user_id
        service._repo.update = AsyncMock(return_value=updated)

        data = ReportUpdate(title="Updated Report")
        result = await service.update_report(str(fake.id), data, user_id=test_user_id)
        assert result["topic"] == "Updated Report"

    @pytest.mark.asyncio
    async def test_update_not_found(self, service):
        service._repo.get_by_id = AsyncMock(return_value=None)
        result = await service.update_report(
            str(uuid.uuid4()), ReportUpdate(title="X"), user_id=uuid.uuid4()
        )
        assert result is None


class TestReportServiceGet:
    @pytest.mark.asyncio
    async def test_get_found(self, service):
        test_user_id = uuid.uuid4()
        fake = MagicMock()
        fake.id = uuid.uuid4()
        fake.title = "Test Report"
        fake.body = "Report body"
        fake.category = "security"
        fake.importance_score = 7.5
        fake.article_ids = []
        fake.agent_run_id = None
        fake.generated_by = None
        fake.created_at = datetime.now(timezone.utc)
        fake.user_id = test_user_id
        service._repo.get_by_id = AsyncMock(return_value=fake)
        result = await service.get_report(str(fake.id), user_id=test_user_id)
        assert result is not None
        assert result["topic"] == "Test Report"

    @pytest.mark.asyncio
    async def test_get_not_found(self, service):
        service._repo.get_by_id = AsyncMock(return_value=None)
        assert await service.get_report(str(uuid.uuid4()), user_id=uuid.uuid4()) is None
