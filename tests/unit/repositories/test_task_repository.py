"""Tests for task repository create/update/delete/get_by_id."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from backend.repositories.task_repository import TaskRepository


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
    return TaskRepository(session)


def _make_task(**kwargs):
    t = MagicMock()
    t.id = kwargs.get("id", uuid.uuid4())
    t.title = kwargs.get("title", "Test Task")
    t.description = kwargs.get("description", None)
    t.priority = kwargs.get("priority", "medium")
    t.status = kwargs.get("status", "pending")
    t.created_at = None
    t.updated_at = None
    return t


class TestTaskRepositoryCreate:
    @pytest.mark.asyncio
    async def test_create_task(self, repo, session):
        task = await repo.create(
            title="Test Task", description="A task", priority="high",
            status="pending", created_at=None, updated_at=None,
        )
        assert task.title == "Test Task"
        assert len(session._store) == 1

    @pytest.mark.asyncio
    async def test_create_returns_instance(self, repo, session):
        task = await repo.create(
            title="New", created_at=None, updated_at=None,
        )
        assert task is not None
        assert hasattr(task, "id")


class TestTaskRepositoryUpdate:
    @pytest.mark.asyncio
    async def test_update_existing(self, repo, session):
        task = _make_task(title="Old")
        session._store[str(task.id)] = task
        updated = await repo.update(task.id, title="Updated")
        assert updated.title == "Updated"

    @pytest.mark.asyncio
    async def test_update_nonexistent_returns_none(self, repo, session):
        result = await repo.update(uuid.uuid4(), title="Ghost")
        assert result is None


class TestTaskRepositoryDelete:
    @pytest.mark.asyncio
    async def test_delete_existing(self, repo, session):
        task = _make_task(title="Delete Me")
        session._store[str(task.id)] = task
        assert await repo.delete(task.id) is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self, repo, session):
        assert await repo.delete(uuid.uuid4()) is False


class TestTaskRepositoryGetById:
    @pytest.mark.asyncio
    async def test_get_existing(self, repo, session):
        task = _make_task(title="Find Task")
        session._store[str(task.id)] = task
        found = await repo.get_by_id(task.id)
        assert found is not None
        assert found.title == "Find Task"

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, repo, session):
        assert await repo.get_by_id(uuid.uuid4()) is None
