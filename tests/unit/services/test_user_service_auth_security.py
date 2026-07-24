"""Tests for UserService password change and account deactivation with refresh token revocation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.schemas.user import PasswordChangeRequest
from backend.services.user_service import UserService


@pytest.fixture()
def mock_repo():
    session = MagicMock()
    session.flush = AsyncMock()
    repo = MagicMock()
    repo.get_by_username = AsyncMock(return_value=None)
    repo.get_by_email = AsyncMock(return_value=None)
    repo.get_by_id = AsyncMock()
    repo.create = AsyncMock()
    repo.session = session
    return repo


@pytest.fixture()
def mock_token_store():
    store = AsyncMock()
    store.revoke_all_user_tokens = AsyncMock(return_value=3)
    return store


class TestChangePassword:
    def _make_user(self, user_id=None, hashed_pw="hashed", is_active=True):
        user = MagicMock()
        user.id = user_id or uuid.uuid4()
        user.hashed_password = hashed_pw
        user.is_active = is_active
        return user

    @pytest.mark.asyncio
    async def test_change_password_revokes_all_tokens(self, mock_repo, mock_token_store):
        user = self._make_user()
        mock_repo.get_by_id = AsyncMock(return_value=user)
        svc = UserService(None, token_store=mock_token_store)
        svc._repo = mock_repo

        from backend.utils.auth import hash_password
        old_hash = hash_password("correct")
        user.hashed_password = old_hash

        data = PasswordChangeRequest(
            current_password="correct",
            new_password="newsecurepass123",
        )
        await svc.change_password(str(user.id), data.current_password, data.new_password)

        # Verify password was updated (bcrypt salts differ each call)
        assert user.hashed_password != old_hash
        mock_repo.session.flush.assert_awaited_once()

        # Verify all tokens revoked
        mock_token_store.revoke_all_user_tokens.assert_awaited_once_with(str(user.id))

    @pytest.mark.asyncio
    async def test_change_password_wrong_current_raises(self, mock_repo, mock_token_store):
        user = self._make_user()
        mock_repo.get_by_id = AsyncMock(return_value=user)
        svc = UserService(None, token_store=mock_token_store)
        svc._repo = mock_repo

        from backend.utils.auth import hash_password
        user.hashed_password = hash_password("correct")

        with pytest.raises(ValueError, match="Current password is incorrect"):
            await svc.change_password(str(user.id), "wrong", "newsecurepass123")

        # Token revocation should NOT happen on failure
        mock_token_store.revoke_all_user_tokens.assert_not_called()

    @pytest.mark.asyncio
    async def test_change_password_no_token_store_succeeds(self, mock_repo):
        user = self._make_user()
        mock_repo.get_by_id = AsyncMock(return_value=user)
        svc = UserService(None, token_store=None)
        svc._repo = mock_repo

        from backend.utils.auth import hash_password
        old_hash = hash_password("correct")
        user.hashed_password = old_hash

        await svc.change_password(str(user.id), "correct", "newsecurepass123")

        assert user.hashed_password != old_hash
        mock_repo.session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_change_password_token_store_failure_does_not_block(self, mock_repo):
        user = self._make_user()
        mock_repo.get_by_id = AsyncMock(return_value=user)
        svc = UserService(None, token_store=AsyncMock(side_effect=RuntimeError("redis down")))
        svc._repo = mock_repo

        from backend.utils.auth import hash_password
        old_hash = hash_password("correct")
        user.hashed_password = old_hash

        # Should succeed despite token store failure (logged as warning)
        await svc.change_password(str(user.id), "correct", "newsecurepass123")

        assert user.hashed_password != old_hash


class TestDeactivateUser:
    def _make_user(self, user_id=None, is_active=True, hashed_pw="hashed"):
        user = MagicMock()
        user.id = user_id or uuid.uuid4()
        user.hashed_password = hashed_pw
        user.is_active = is_active
        return user

    @pytest.mark.asyncio
    async def test_deactivate_revokes_all_tokens(self, mock_repo, mock_token_store):
        user = self._make_user(is_active=True)
        mock_repo.get_by_id = AsyncMock(return_value=user)
        svc = UserService(None, token_store=mock_token_store)
        svc._repo = mock_repo

        await svc.deactivate_user(str(user.id))

        assert user.is_active is False
        mock_repo.session.flush.assert_awaited_once()
        mock_token_store.revoke_all_user_tokens.assert_awaited_once_with(str(user.id))

    @pytest.mark.asyncio
    async def test_deactivate_nonexistent_raises(self, mock_repo):
        mock_repo.get_by_id = AsyncMock(return_value=None)
        svc = UserService(None, token_store=MagicMock())
        svc._repo = mock_repo

        with pytest.raises(ValueError, match="User not found"):
            await svc.deactivate_user(str(uuid.uuid4()))

        svc._token_store.revoke_all_user_tokens.assert_not_called()

    @pytest.mark.asyncio
    async def test_deactivate_already_inactive_revokes_tokens(self, mock_repo, mock_token_store):
        """Even if already inactive, deactivate still revokes tokens (defensive)."""
        user = self._make_user(is_active=False)
        mock_repo.get_by_id = AsyncMock(return_value=user)
        svc = UserService(None, token_store=mock_token_store)
        svc._repo = mock_repo

        await svc.deactivate_user(str(user.id))

        assert user.is_active is False
        mock_token_store.revoke_all_user_tokens.assert_awaited_once()
