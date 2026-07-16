"""Tests for task service business logic."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock

import pytest

from backend.services.task_service import TaskService
from backend.schemas.task_create import TaskCreate, TaskUpdate


@pytest.fixture()
def mock_repo():
    repo = MagicMock()
    repo.list_all = AsyncMock(return_value=[])
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.update = AsyncMock(return_value=None)
    repo.delete = AsyncMock(return_value=True)
    return repo


@pytest.fixture()
def service(mock_repo):
    session = MagicMock()
    svc = TaskService(session)
    svc._repo = mock_repo
    return svc


@pytest.fixture()
def fake_task():
    t = MagicMock()
    t.id = uuid.uuid4()
    t.title = "Test Task"
    t.description = "Description"
    t.priority = "high"
    t.status = "pending"
    t.created_at = datetime.now(timezone.utc)
    return t


class TestTaskServiceCreate:
    @pytest.mark.asyncio
    async def test_create_valid(self, service):
        fake = MagicMock()
        fake.id = uuid.uuid4()
        fake.title = "New Task"
        fake.description = None
        fake.priority = "medium"
        fake.status = "pending"
        fake.created_at = datetime.now(timezone.utc)
        service._repo.create = AsyncMock(return_value=fake)

        data = TaskCreate(title="New Task")
        result = await service.create_task(data)
        assert result["title"] == "New Task"
        service._repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_validates_required_title(self):
        with pytest.raises(Exception):
            TaskCreate(title="", priority="high")


class TestTaskServiceUpdate:
    @pytest.mark.asyncio
    async def test_update_found(self, service, fake_task):
        service._repo.get_by_id = AsyncMock(return_value=fake_task)
        updated = MagicMock()
        updated.id = fake_task.id
        updated.title = "Updated"
        updated.description = fake_task.description
        updated.priority = fake_task.priority
        updated.status = fake_task.status
        updated.created_at = fake_task.created_at
        service._repo.update = AsyncMock(return_value=updated)

        data = TaskUpdate(title="Updated")
        result = await service.update_task(str(fake_task.id), data)
        assert result["title"] == "Updated"

    @pytest.mark.asyncio
    async def test_update_not_found(self, service):
        service._repo.get_by_id = AsyncMock(return_value=None)
        result = await service.update_task(str(uuid.uuid4()), TaskUpdate(title="X"))
        assert result is None


class TestTaskServiceDelete:
    @pytest.mark.asyncio
    async def test_delete_success(self, service):
        service._repo.delete = AsyncMock(return_value=True)
        assert await service.delete_task(str(uuid.uuid4())) is True

    @pytest.mark.asyncio
    async def test_delete_not_found(self, service):
        service._repo.delete = AsyncMock(return_value=False)
        assert await service.delete_task(str(uuid.uuid4())) is False


class TestTaskServiceGet:
    @pytest.mark.asyncio
    async def test_get_found(self, service, fake_task):
        service._repo.get_by_id = AsyncMock(return_value=fake_task)
        result = await service.get_task(str(fake_task.id))
        assert result is not None
        assert result["title"] == "Test Task"

    @pytest.mark.asyncio
    async def test_get_not_found(self, service):
        service._repo.get_by_id = AsyncMock(return_value=None)
        assert await service.get_task(str(uuid.uuid4())) is None
