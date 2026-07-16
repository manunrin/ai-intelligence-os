"""Tests for JWT token creation and decoding."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from backend.utils.jwt import create_access_token, decode_access_token


@pytest.fixture()
def mock_settings():
    settings = MagicMock()
    settings.jwt_secret_key = "test-secret-key-for-jwt-signing-at-least-32chars"
    settings.jwt_algorithm = "HS256"
    settings.jwt_access_token_expire_minutes = 30
    return settings


class TestCreateAccessToken:
    def test_create_returns_string(self, mock_settings):
        user_id = str(uuid.uuid4())
        token = create_access_token(user_id, mock_settings)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_contains_three_parts(self, mock_settings):
        """JWT tokens have 3 dot-separated parts: header.payload.signature."""
        user_id = str(uuid.uuid4())
        token = create_access_token(user_id, mock_settings)
        parts = token.split(".")
        assert len(parts) == 3

    def test_decode_valid_token(self, mock_settings):
        user_id = str(uuid.uuid4())
        token = create_access_token(user_id, mock_settings)
        payload = decode_access_token(token, mock_settings)
        assert payload is not None
        assert payload["sub"] == user_id


class TestDecodeAccessToken:
    def test_decode_invalid_token_returns_none(self, mock_settings):
        result = decode_access_token("invalid.token.here", mock_settings)
        assert result is None

    def test_decode_tampered_token_returns_none(self, mock_settings):
        user_id = str(uuid.uuid4())
        token = create_access_token(user_id, mock_settings)
        # Tamper with the signature
        parts = token.split(".")
        tampered = f"{parts[0]}.{parts[1]}.tampered"
        result = decode_access_token(tampered, mock_settings)
        assert result is None

    def test_decode_missing_sub_returns_none(self, mock_settings):
        from jose import jwt
        from datetime import datetime, timedelta, timezone

        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
        payload = {"exp": expire}
        token = jwt.encode(payload, mock_settings.jwt_secret_key, algorithm="HS256")
        result = decode_access_token(token, mock_settings)
        assert result is not None
        assert "sub" not in result or result.get("sub") is None
