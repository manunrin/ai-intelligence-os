"""Root conftest for the entire test suite."""

from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

# Ensure backend/ is on the path regardless of where pytest is invoked.
_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

import pytest
from fastapi.testclient import TestClient

# Set JWT secret before any imports that use Settings
os.environ.setdefault(
    "JWT_SECRET_KEY",
    "test-secret-key-for-jwt-signing-at-least-32chars",
)


def _make_fake_user():
    """Create a MagicMock representing an authenticated user."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.username = "testuser"
    user.role = "user"
    user.is_active = True
    return user


@pytest.fixture()
def fake_user():
    return _make_fake_user()


@pytest.fixture()
def client(fake_user):
    """TestClient with JWT dependency overridden so all requests are authenticated as fake_user."""
    from backend.main import create_app
    from backend.routers.deps import get_current_user

    async def mock_get_current_user():
        return fake_user

    app = create_app()
    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield TestClient(app)
    app.dependency_overrides.clear()
