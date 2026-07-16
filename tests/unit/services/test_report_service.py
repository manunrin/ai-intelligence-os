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
        service._repo.create = AsyncMock(return_value=fake)

        data = ReportCreate(title="New Report", body="Body text")
        result = await service.create_report(data)
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
    async def test_update_found(self, service, fake_report):
        service._repo.get_by_id = AsyncMock(return_value=fake_report)
        updated = MagicMock()
        updated.id = fake_report.id
        updated.title = "Updated Report"
        updated.body = fake_report.body
        updated.category = fake_report.category
        updated.importance_score = fake_report.importance_score
        updated.article_ids = fake_report.article_ids
        updated.agent_run_id = fake_report.agent_run_id
        updated.generated_by = fake_report.generated_by
        updated.created_at = fake_report.created_at
        service._repo.update = AsyncMock(return_value=updated)

        data = ReportUpdate(title="Updated Report")
        result = await service.update_report(str(fake_report.id), data)
        assert result["topic"] == "Updated Report"

    @pytest.mark.asyncio
    async def test_update_not_found(self, service):
        service._repo.get_by_id = AsyncMock(return_value=None)
        result = await service.update_report(
            str(uuid.uuid4()), ReportUpdate(title="X")
        )
        assert result is None


class TestReportServiceGet:
    @pytest.mark.asyncio
    async def test_get_found(self, service, fake_report):
        service._repo.get_by_id = AsyncMock(return_value=fake_report)
        result = await service.get_report(str(fake_report.id))
        assert result is not None
        assert result["topic"] == "Test Report"

    @pytest.mark.asyncio
    async def test_get_not_found(self, service):
        service._repo.get_by_id = AsyncMock(return_value=None)
        assert await service.get_report(str(uuid.uuid4())) is None
