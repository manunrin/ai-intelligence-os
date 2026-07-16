"""Tests for knowledge item repository create/update/delete/get_by_id."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from backend.repositories.knowledge_repository import KnowledgeItemRepository


class FakeSession:
    def __init__(self):
        self._store: dict[str, MagicMock] = {}

    def add(self, instance):
        self._store[str(instance.id)] = instance

    async def flush(self):
        pass

    async def refresh(self, instance):
        pass

    async def delete(self, instance):
        if str(instance.id) in self._store:
            del self._store[str(instance.id)]

    async def get(self, model, id_value):
        return self._store.get(str(id_value))

    async def execute(self, stmt):
        class Result:
            def scalars(self):
                return self
            def all(self):
                return []
            def scalar_one(self):
                return 0
        return Result()


@pytest.fixture()
def session():
    return FakeSession()


@pytest.fixture()
def repo(session):
    return KnowledgeItemRepository(session)


def _make_item(**kwargs):
    item = MagicMock()
    item.id = kwargs.get("id", uuid.uuid4())
    item.title = kwargs.get("title", "Test")
    item.content = kwargs.get("content", "Content")
    item.kind = kwargs.get("kind", "note")
    item.tags = kwargs.get("tags", [])
    item.created_at = None
    return item


class TestKnowledgeRepoCreate:
    @pytest.mark.asyncio
    async def test_create_item(self, repo, session):
        item = await repo.create(
            title="Test", content="Content", kind="note", tags=[],
            created_at=None,
        )
        assert item.title == "Test"
        assert len(session._store) == 1

    @pytest.mark.asyncio
    async def test_create_returns_instance(self, repo, session):
        item = await repo.create(
            title="New", content="Data", kind="summary", tags=[],
            created_at=None,
        )
        assert hasattr(item, "id")


class TestKnowledgeRepoUpdate:
    @pytest.mark.asyncio
    async def test_update_existing(self, repo, session):
        item = _make_item(title="Old")
        session._store[str(item.id)] = item
        updated = await repo.update(item.id, title="Updated")
        assert updated.title == "Updated"

    @pytest.mark.asyncio
    async def test_update_nonexistent_returns_none(self, repo, session):
        result = await repo.update(uuid.uuid4(), title="Ghost")
        assert result is None


class TestKnowledgeRepoDelete:
    @pytest.mark.asyncio
    async def test_delete_existing(self, repo, session):
        item = _make_item(title="Delete")
        session._store[str(item.id)] = item
        assert await repo.delete(item.id) is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self, repo, session):
        assert await repo.delete(uuid.uuid4()) is False


class TestKnowledgeRepoGetById:
    @pytest.mark.asyncio
    async def test_get_existing(self, repo, session):
        item = _make_item(title="Find")
        session._store[str(item.id)] = item
        found = await repo.get_by_id(item.id)
        assert found is not None
        assert found.title == "Find"

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, repo, session):
        assert await repo.get_by_id(uuid.uuid4()) is None
