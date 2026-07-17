"""Tests for article service business logic."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock

import pytest

from backend.services.article_service import ArticleService
from backend.schemas.article_create import ArticleCreate, ArticleUpdate


@pytest.fixture()
def mock_repo():
    repo = MagicMock()
    repo.list_all = AsyncMock(return_value=[])
    repo.count = AsyncMock(return_value=0)
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.update = AsyncMock(return_value=None)
    repo.delete = AsyncMock(return_value=True)
    return repo


@pytest.fixture()
def service(mock_repo):
    session = MagicMock()
    svc = ArticleService(session)
    svc._repo = mock_repo
    return svc


@pytest.fixture()
def fake_article():
    art = MagicMock()
    art.id = uuid.uuid4()
    art.title = "Test Article"
    art.summary = "A summary"
    art.content = "Content body"
    art.metadata_ = {"url": "http://example.com", "tags": ["test"]}
    source = MagicMock()
    source.name = "RSS Feed"
    art.source = source
    art.language = "en"
    art.status = "processed"
    now = datetime.now(timezone.utc)
    art.fetched_at = now
    art.published_at = now
    return art


class TestArticleServiceList:
    @pytest.mark.asyncio
    async def test_list_empty(self, service):
        result = await service.list_articles()
        assert result == []

    @pytest.mark.asyncio
    async def test_list_with_data(self, service, fake_article):
        service._repo.list_all = AsyncMock(return_value=[fake_article])
        result = await service.list_articles()
        assert len(result) == 1
        assert result[0]["title"] == "Test Article"


class TestArticleServiceGet:
    @pytest.mark.asyncio
    async def test_get_found(self, service):
        test_user_id = uuid.uuid4()
        fake = MagicMock()
        fake.id = uuid.uuid4()
        fake.title = "Test Article"
        fake.summary = "A summary"
        fake.content = "Content body"
        fake.metadata_ = {"url": "http://example.com", "tags": ["test"]}
        source = MagicMock()
        source.name = "RSS Feed"
        fake.source = source
        fake.language = "en"
        fake.status = "processed"
        now = datetime.now(timezone.utc)
        fake.fetched_at = now
        fake.published_at = now
        fake.user_id = test_user_id
        service._repo.get_by_id = AsyncMock(return_value=fake)
        result = await service.get_article(str(fake.id), user_id=test_user_id)
        assert result is not None
        assert result["title"] == "Test Article"

    @pytest.mark.asyncio
    async def test_get_not_found(self, service):
        service._repo.get_by_id = AsyncMock(return_value=None)
        result = await service.get_article(str(uuid.uuid4()), user_id=uuid.uuid4())
        assert result is None


class TestArticleServiceCreate:
    @pytest.mark.asyncio
    async def test_create_valid(self, service):
        fake = MagicMock()
        fake.id = uuid.uuid4()
        fake.title = "New"
        fake.summary = None
        fake.content = None
        fake.metadata_ = {}
        fake.source = MagicMock()
        fake.source.name = "Source"
        fake.language = "en"
        fake.status = "raw"
        fake.fetched_at = datetime.now(timezone.utc)
        fake.published_at = None
        fake.user_id = None
        service._repo.create = AsyncMock(return_value=fake)

        data = ArticleCreate(
            title="New",
            source_id=str(uuid.uuid4()),
        )
        result = await service.create_article(data, user_id=uuid.uuid4())
        assert result["title"] == "New"
        service._repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_validates_required_title(self):
        with pytest.raises(Exception):
            ArticleCreate(title="", source_id=str(uuid.uuid4()))

    @pytest.mark.asyncio
    async def test_create_enforces_max_length(self):
        with pytest.raises(Exception):
            ArticleCreate(
                title="x" * 501,
                source_id=str(uuid.uuid4()),
            )


class TestArticleServiceUpdate:
    @pytest.mark.asyncio
    async def test_update_found(self, service):
        test_user_id = uuid.uuid4()
        fake = MagicMock()
        fake.id = uuid.uuid4()
        fake.title = "Test Article"
        fake.summary = "A summary"
        fake.content = "Content body"
        fake.metadata_ = {"url": "http://example.com", "tags": ["test"]}
        source = MagicMock()
        source.name = "RSS Feed"
        fake.source = source
        fake.language = "en"
        fake.status = "processed"
        now = datetime.now(timezone.utc)
        fake.fetched_at = now
        fake.published_at = now
        fake.user_id = test_user_id
        service._repo.get_by_id = AsyncMock(return_value=fake)
        updated = MagicMock()
        updated.id = fake.id
        updated.title = "Updated Title"
        updated.summary = fake.summary
        updated.content = fake.content
        updated.metadata_ = fake.metadata_
        updated.source = fake.source
        updated.language = fake.language
        updated.status = fake.status
        updated.fetched_at = fake.fetched_at
        updated.published_at = fake.published_at
        updated.user_id = fake.user_id
        service._repo.update = AsyncMock(return_value=updated)

        data = ArticleUpdate(title="Updated Title")
        result = await service.update_article(str(fake.id), data, user_id=test_user_id)
        assert result["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_update_not_found(self, service):
        service._repo.get_by_id = AsyncMock(return_value=None)
        result = await service.update_article(
            str(uuid.uuid4()), ArticleUpdate(title="X"), user_id=uuid.uuid4()
        )
        assert result is None


class TestArticleServiceDelete:
    @pytest.mark.asyncio
    async def test_delete_success(self, service):
        test_user_id = uuid.uuid4()
        fake = MagicMock()
        fake.id = uuid.uuid4()
        fake.user_id = test_user_id
        service._repo.get_by_id = AsyncMock(return_value=fake)
        service._repo.delete = AsyncMock(return_value=True)
        assert await service.delete_article(str(fake.id), user_id=test_user_id) is True

    @pytest.mark.asyncio
    async def test_delete_not_found(self, service):
        service._repo.get_by_id = AsyncMock(return_value=None)
        assert await service.delete_article(str(uuid.uuid4()), user_id=uuid.uuid4()) is False
