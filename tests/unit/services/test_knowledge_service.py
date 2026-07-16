"""Tests for knowledge service business logic."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock

import pytest

from backend.services.knowledge_service import KnowledgeService
from backend.schemas.knowledge_create import KnowledgeItemCreate, KnowledgeItemUpdate


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
    svc = KnowledgeService(session)
    svc._repo = mock_repo
    return svc


@pytest.fixture()
def fake_item():
    item = MagicMock()
    item.id = uuid.uuid4()
    item.title = "Test Item"
    item.content = "Content here"
    item.kind = "note"
    item.article_id = None
    item.tags = ["tag1"]
    item.created_at = datetime.now(timezone.utc)
    return item


class TestKnowledgeServiceCreate:
    @pytest.mark.asyncio
    async def test_create_valid(self, service):
        fake = MagicMock()
        fake.id = uuid.uuid4()
        fake.title = "New"
        fake.content = "Data"
        fake.kind = "summary"
        fake.article_id = None
        fake.tags = []
        fake.created_at = datetime.now(timezone.utc)
        service._repo.create = AsyncMock(return_value=fake)

        data = KnowledgeItemCreate(title="New", content="Data", kind="summary")
        result = await service.create_knowledge_item(data)
        assert result["title"] == "New"

    @pytest.mark.asyncio
    async def test_create_validates_required_fields(self):
        with pytest.raises(Exception):
            KnowledgeItemCreate(title="", content="Data", kind="x")

    @pytest.mark.asyncio
    async def test_create_validates_kind_max_length(self):
        with pytest.raises(Exception):
            KnowledgeItemCreate(title="T", content="C", kind="x" * 33)


class TestKnowledgeServiceUpdate:
    @pytest.mark.asyncio
    async def test_update_found(self, service, fake_item):
        service._repo.get_by_id = AsyncMock(return_value=fake_item)
        updated = MagicMock()
        updated.id = fake_item.id
        updated.title = "Updated"
        updated.content = fake_item.content
        updated.kind = fake_item.kind
        updated.article_id = fake_item.article_id
        updated.tags = fake_item.tags
        updated.created_at = fake_item.created_at
        service._repo.update = AsyncMock(return_value=updated)

        data = KnowledgeItemUpdate(title="Updated")
        result = await service.update_knowledge_item(str(fake_item.id), data)
        assert result["title"] == "Updated"

    @pytest.mark.asyncio
    async def test_update_not_found(self, service):
        service._repo.get_by_id = AsyncMock(return_value=None)
        result = await service.update_knowledge_item(
            str(uuid.uuid4()), KnowledgeItemUpdate(title="X")
        )
        assert result is None


class TestKnowledgeServiceDelete:
    @pytest.mark.asyncio
    async def test_delete_success(self, service):
        service._repo.delete = AsyncMock(return_value=True)
        assert await service.delete_knowledge_item(str(uuid.uuid4())) is True

    @pytest.mark.asyncio
    async def test_delete_not_found(self, service):
        service._repo.delete = AsyncMock(return_value=False)
        assert await service.delete_knowledge_item(str(uuid.uuid4())) is False


class TestKnowledgeServiceGet:
    @pytest.mark.asyncio
    async def test_get_found(self, service, fake_item):
        service._repo.get_by_id = AsyncMock(return_value=fake_item)
        result = await service.get_knowledge_item(str(fake_item.id))
        assert result is not None
        assert result["title"] == "Test Item"

    @pytest.mark.asyncio
    async def test_get_not_found(self, service):
        service._repo.get_by_id = AsyncMock(return_value=None)
        assert await service.get_knowledge_item(str(uuid.uuid4())) is None
