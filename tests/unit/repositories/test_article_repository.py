"""Tests for article repository create/update/delete/get_by_id."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from backend.repositories.article_repository import ArticleRepository


class FakeSession:
    """Minimal fake session for repository unit tests."""

    def __init__(self):
        self._store: dict[str, MagicMock] = {}
        self._to_delete: set[str] = set()

    def add(self, instance):
        self._store[str(instance.id)] = instance

    async def flush(self):
        pass

    async def refresh(self, instance):
        pass

    async def delete(self, instance):
        self._to_delete.add(str(instance.id))

    async def get(self, model, id_value):
        key = str(id_value)
        return self._store.get(key)

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
    return ArticleRepository(session)


def _make_article(**kwargs):
    art = MagicMock()
    art.id = kwargs.get("id", uuid.uuid4())
    art.title = kwargs.get("title", "Test")
    art.summary = kwargs.get("summary", "Summary")
    art.content = kwargs.get("content", "Body")
    art.source_id = kwargs.get("source_id", uuid.uuid4())
    art.language = kwargs.get("language", "en")
    art.status = kwargs.get("status", "raw")
    art.metadata_ = kwargs.get("metadata_", {})
    art.fetched_at = None
    art.created_at = None
    art.updated_at = None
    return art


class TestArticleRepositoryCreate:
    @pytest.mark.asyncio
    async def test_create_article(self, repo, session):
        article = await repo.create(
            title="Test", source_id=uuid.uuid4(), metadata_={},
            fetched_at=None, created_at=None, updated_at=None,
        )
        assert article.title == "Test"
        assert len(session._store) == 1

    @pytest.mark.asyncio
    async def test_create_returns_instance(self, repo, session):
        article = await repo.create(
            title="New", source_id=uuid.uuid4(), metadata_={},
            fetched_at=None, created_at=None, updated_at=None,
        )
        assert article is not None
        assert hasattr(article, "id")


class TestArticleRepositoryUpdate:
    @pytest.mark.asyncio
    async def test_update_existing(self, repo, session):
        article = _make_article(title="Old")
        session._store[str(article.id)] = article
        updated = await repo.update(article.id, title="New")
        assert updated.title == "New"

    @pytest.mark.asyncio
    async def test_update_nonexistent_returns_none(self, repo, session):
        result = await repo.update(uuid.uuid4(), title="Ghost")
        assert result is None


class TestArticleRepositoryDelete:
    @pytest.mark.asyncio
    async def test_delete_existing(self, repo, session):
        article = _make_article(title="To Delete")
        session._store[str(article.id)] = article
        assert await repo.delete(article.id) is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self, repo, session):
        assert await repo.delete(uuid.uuid4()) is False


class TestArticleRepositoryGetById:
    @pytest.mark.asyncio
    async def test_get_existing(self, repo, session):
        article = _make_article(title="Find Me")
        session._store[str(article.id)] = article
        found = await repo.get_by_id(article.id)
        assert found is not None
        assert found.title == "Find Me"

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, repo, session):
        found = await repo.get_by_id(uuid.uuid4())
        assert found is None
