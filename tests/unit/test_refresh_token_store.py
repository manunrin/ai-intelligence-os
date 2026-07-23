"""Tests for Redis-backed refresh token store."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.services.refresh_token_store import RefreshTokenStore, _hash_token


class TestHashToken:
    def test_hash_is_deterministic(self):
        token = "test-token-12345"
        h1 = _hash_token(token)
        h2 = _hash_token(token)
        assert h1 == h2

    def test_hash_different_tokens(self):
        h1 = _hash_token("token-a")
        h2 = _hash_token("token-b")
        assert h1 != h2

    def test_hash_is_hex_64_chars(self):
        # SHA-256 produces 32 bytes = 64 hex chars
        h = _hash_token("any-token")
        assert len(h) == 64
        int(h, 16)  # valid hex


@pytest.fixture()
def mock_redis():
    """Create an AsyncMock Redis client with default return values."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    return redis


@pytest.fixture()
def store(mock_redis):
    return RefreshTokenStore(mock_redis, expire_days=7)


class TestRefreshTokenStore:
    async def test_store_sets_key_with_ttl(self, store, mock_redis):
        user_id = str(uuid.uuid4())
        token = "test-refresh-token-abc"
        await store.store(user_id, token)
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        key = call_args[0][0]
        assert key.startswith("rt:")
        payload = call_args[0][1]  # second positional arg is the JSON string
        data = json.loads(payload)
        assert data["user_id"] == user_id
        assert "exp_epoch" in data

    async def test_validate_returns_user_id_for_valid_token(self, store, mock_redis):
        token = "valid-token"
        now = datetime.now(timezone.utc)
        payload = json.dumps({
            "user_id": "user-123",
            "created_at": now.isoformat(),
            "exp_epoch": (now + timedelta(days=1)).timestamp(),
        })
        mock_redis.get = AsyncMock(return_value=payload.encode())

        result = await store.validate(token)
        assert result == "user-123"

    async def test_validate_returns_none_for_missing_token(self, store, mock_redis):
        mock_redis.get = AsyncMock(return_value=None)
        result = await store.validate("nonexistent")
        assert result is None

    async def test_validate_deletes_expired_token(self, store, mock_redis):
        token = "expired-token"
        past = datetime.now(timezone.utc) - timedelta(days=1)
        payload = json.dumps({
            "user_id": "user-123",
            "created_at": past.isoformat(),
            "exp_epoch": past.timestamp(),
        })
        mock_redis.get = AsyncMock(return_value=payload.encode())
        mock_redis.delete = AsyncMock(return_value=1)

        result = await store.validate(token)
        assert result is None
        mock_redis.delete.assert_called_once()

    async def test_revoke_deletes_key(self, store, mock_redis):
        mock_redis.delete = AsyncMock(return_value=1)
        result = await store.revoke("some-token")
        assert result is True
        mock_redis.delete.assert_called_once()

    async def test_revoke_returns_false_when_key_missing(self, store, mock_redis):
        mock_redis.delete = AsyncMock(return_value=0)
        result = await store.revoke("missing-token")
        assert result is False

    async def test_rotate_revokes_old_and_stores_new(self, store, mock_redis):
        user_id = str(uuid.uuid4())
        old_token = "old-token"
        new_token = "new-token"

        await store.rotate(old_token, new_token, user_id)

        # Old token should be revoked
        mock_redis.delete.assert_called()
        # New token should be stored (set called at least once more)
        assert mock_redis.set.call_count >= 1

    async def test_from_url_creates_instance(self):
        store = RefreshTokenStore.from_url("redis://localhost:6379/0", expire_days=14)
        assert store._expire_seconds == 14 * 86_400
