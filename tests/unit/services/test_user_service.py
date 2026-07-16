"""Tests for user service registration and authentication."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock

import pytest

from backend.schemas.user import UserCreate, UserLogin
from backend.services.user_service import UserService


@pytest.fixture()
def mock_repo():
    repo = MagicMock()
    repo.get_by_username = AsyncMock(return_value=None)
    repo.get_by_email = AsyncMock(return_value=None)
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.session = MagicMock()
    repo.session.flush = AsyncMock()
    return repo


@pytest.fixture()
def service(mock_repo):
    session = MagicMock()
    svc = UserService(session)
    svc._repo = mock_repo
    return svc


class TestUserRegister:
    @pytest.mark.asyncio
    async def test_register_success(self, service):
        fake = MagicMock()
        fake.id = uuid.uuid4()
        fake.username = "newuser"
        fake.email = "new@example.com"
        fake.role = "user"
        fake.is_active = True
        fake.last_login_at = None
        fake.created_at = MagicMock()
        fake.updated_at = MagicMock()
        service._repo.create = AsyncMock(return_value=fake)

        data = UserCreate(username="newuser", email="new@example.com", password="securepass123")
        result = await service.register(data)
        assert result.username == "newuser"
        service._repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, service):
        existing = MagicMock()
        existing.id = uuid.uuid4()
        service._repo.get_by_username = AsyncMock(return_value=existing)

        data = UserCreate(username="existing", email="other@example.com", password="securepass123")
        with pytest.raises(ValueError, match="already exists"):
            await service.register(data)

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, service):
        existing = MagicMock()
        existing.id = uuid.uuid4()
        service._repo.get_by_email = AsyncMock(return_value=existing)

        data = UserCreate(username="newuser", email="taken@example.com", password="securepass123")
        with pytest.raises(ValueError, match="already registered"):
            await service.register(data)

    @pytest.mark.asyncio
    async def test_register_validates_min_password_length(self):
        with pytest.raises(Exception):
            UserCreate(username="u", email="e@x.c", password="short")

    @pytest.mark.asyncio
    async def test_register_validates_min_username_length(self):
        with pytest.raises(Exception):
            UserCreate(username="ab", email="e@x.c", password="longenough123")


class TestUserAuthenticate:
    @pytest.mark.asyncio
    async def test_authenticate_success(self, service):
        from backend.utils.auth import hash_password
        real_hash = hash_password("correct")
        user = MagicMock()
        user.id = uuid.uuid4()
        user.username = "loginuser"
        user.email = "login@example.com"
        user.hashed_password = real_hash
        user.role = "user"
        user.is_active = True
        user.last_login_at = None
        user.created_at = datetime.now(timezone.utc)
        service._repo.get_by_username = AsyncMock(return_value=user)

        data = UserLogin(username="loginuser", password="correct")
        result = await service.authenticate(data)
        assert result is not None
        assert result.username == "loginuser"

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(self, service):
        from backend.utils.auth import hash_password
        real_hash = hash_password("correctpass")
        user = MagicMock()
        user.id = uuid.uuid4()
        user.email = "test@example.com"
        user.hashed_password = real_hash
        user.role = "user"
        user.is_active = True
        service._repo.get_by_username = AsyncMock(return_value=user)

        data = UserLogin(username="loginuser", password="wrong")
        result = await service.authenticate(data)
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, service):
        service._repo.get_by_username = AsyncMock(return_value=None)
        data = UserLogin(username="ghost", password="x")
        result = await service.authenticate(data)
        assert result is None


class TestUserGet:
    @pytest.mark.asyncio
    async def test_get_user_found(self, service):
        user = MagicMock()
        user.id = uuid.uuid4()
        user.username = "getme"
        user.email = "get@example.com"
        user.role = "admin"
        user.is_active = True
        user.last_login_at = None
        user.created_at = MagicMock()
        service._repo.get_by_id = AsyncMock(return_value=user)

        result = await service.get_user(str(user.id))
        assert result is not None
        assert result.username == "getme"

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, service):
        service._repo.get_by_id = AsyncMock(return_value=None)
        result = await service.get_user(str(uuid.uuid4()))
        assert result is None
