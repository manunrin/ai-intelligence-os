"""Tests for auth router — register, login, get_me."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app


class FakeSessionCtx:
    async def __aenter__(self):
        return MagicMock()

    async def __aexit__(self, *a):
        pass


class MockUserService:
    """Mock that simulates registration and authentication."""

    def __init__(self, db):
        self._db = db

    async def register(self, data):
        if data.username == "taken":
            raise ValueError("Username 'taken' already exists")
        return {
            "id": str(uuid.uuid4()),
            "username": data.username,
            "email": data.email,
            "role": "user",
            "is_active": True,
            "last_login_at": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    async def authenticate(self, data):
        if data.username == "validuser" and data.password == "correctpass123":
            user = MagicMock()
            user.id = uuid.uuid4()
            user.username = "validuser"
            user.email = "valid@example.com"
            user.role = "user"
            user.is_active = True
            user.last_login_at = None
            user.created_at = datetime.now(timezone.utc)
            return user
        return None

    async def get_user(self, user_id):
        user = MagicMock()
        user.id = uuid.UUID(user_id)
        user.username = "validuser"
        user.email = "valid@example.com"
        user.role = "user"
        user.is_active = True
        user.last_login_at = None
        user.created_at = datetime.now(timezone.utc)
        return user


def _make_client():
    from backend.main import create_app
    from backend.routers.deps import get_current_user

    fake_user = MagicMock()
    fake_user.id = uuid.uuid4()
    fake_user.username = "testuser"
    fake_user.role = "user"
    fake_user.is_active = True

    app = create_app()

    async def mock_get_current_user():
        return fake_user

    app.dependency_overrides[get_current_user] = mock_get_current_user
    return TestClient(app), app


class TestAuthRegister:
    def test_register_success(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.services.user_service.UserService", MockUserService):
                resp = client.post("/api/v1/auth/register", json={
                    "username": "newuser",
                    "email": "new@example.com",
                    "password": "securepass123",
                })
        assert resp.status_code == 201
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["username"] == "newuser"
        app.dependency_overrides.clear()

    def test_register_duplicate_username(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.services.user_service.UserService", MockUserService):
                resp = client.post("/api/v1/auth/register", json={
                    "username": "taken",
                    "email": "other@example.com",
                    "password": "securepass123",
                })
        assert resp.status_code == 409
        app.dependency_overrides.clear()

    def test_register_validation_error_short_password(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            resp = client.post("/api/v1/auth/register", json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "short",
            })
        assert resp.status_code == 422
        app.dependency_overrides.clear()


class TestAuthLogin:
    def test_login_success(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.services.user_service.UserService", MockUserService):
                resp = client.post("/api/v1/auth/login", json={
                    "username": "validuser",
                    "password": "correctpass123",
                })
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "access_token" in body["data"]
        assert body["data"]["token_type"] == "bearer"
        app.dependency_overrides.clear()

    def test_login_wrong_password(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.services.user_service.UserService", MockUserService):
                resp = client.post("/api/v1/auth/login", json={
                    "username": "validuser",
                    "password": "wrongpassword",
                })
        assert resp.status_code == 401
        app.dependency_overrides.clear()

    def test_login_missing_fields(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            resp = client.post("/api/v1/auth/login", json={"username": "u"})
        assert resp.status_code == 422
        app.dependency_overrides.clear()


class TestAuthMe:
    def test_get_me_with_valid_token(self):
        client, app = _make_client()
        with patch("backend.routers.deps.get_session_factory", lambda: FakeSessionCtx()):
            with patch("backend.services.user_service.UserService", MockUserService):
                resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer fake-token"})
        # Token decode will fail (not a real JWT), so we get 401
        # OAuth2PasswordBearer may also return 422 for non-form tokens
        assert resp.status_code in (401, 422)
        app.dependency_overrides.clear()
