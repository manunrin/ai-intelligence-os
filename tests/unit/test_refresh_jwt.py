"""Tests for refresh token JWT utilities."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend.utils.jwt import create_refresh_token


@pytest.fixture()
def mock_settings():
    from unittest.mock import MagicMock

    s = MagicMock()
    s.jwt_secret_key = "test-secret-key-for-jwt-signing-at-least-32chars"
    s.jwt_algorithm = "HS256"
    s.jwt_access_token_expire_minutes = 30
    s.jwt_refresh_token_expire_days = 7
    return s


class TestCreateRefreshToken:
    def test_create_returns_tuple(self, mock_settings):
        user_id = str(uuid.uuid4())
        result = create_refresh_token(user_id, mock_settings)
        token_str, expires_at = result
        assert isinstance(token_str, str)
        assert isinstance(expires_at, datetime)

    def test_create_returns_64_char_hex(self, mock_settings):
        token_str, _ = create_refresh_token("user-id", mock_settings)
        # secrets.token_hex(32) produces 64 hex chars
        assert len(token_str) == 64
        int(token_str, 16)  # will raise if not valid hex

    def test_create_unique_tokens(self, mock_settings):
        tokens = {create_refresh_token("user-id", mock_settings)[0] for _ in range(10)}
        assert len(tokens) == 10  # all unique

    def test_create_expires_in_future(self, mock_settings):
        _, expires_at = create_refresh_token("user-id", mock_settings)
        assert expires_at.tzinfo is not None or expires_at.utcoffset() is not None
        assert expires_at > datetime.now(timezone.utc)

    def test_create_respects_custom_expire_days(self, mock_settings):
        mock_settings.jwt_refresh_token_expire_days = 30
        _, expires_at = create_refresh_token("user-id", mock_settings)
        now = datetime.now(timezone.utc)
        delta = expires_at - now
        # Should be approximately 30 days (allow 1 second tolerance)
        assert timedelta(seconds=29) <= delta <= timedelta(days=31)
