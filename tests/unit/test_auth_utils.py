"""Tests for password hashing utilities."""

from __future__ import annotations

import pytest

from backend.utils.auth import hash_password, verify_password


class TestPasswordHashing:
    def test_hash_returns_non_empty_string(self):
        hashed = hash_password("testpassword123")
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != "testpassword123"

    def test_hash_different_each_call(self):
        h1 = hash_password("samepassword")
        h2 = hash_password("samepassword")
        assert h1 != h2  # bcrypt salts differently each time

    def test_verify_correct_password(self):
        hashed = hash_password("correctpass")
        assert verify_password("correctpass", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("correctpass")
        assert verify_password("wrongpass", hashed) is False

    def test_verify_empty_password(self):
        hashed = hash_password("correctpass")
        assert verify_password("", hashed) is False
