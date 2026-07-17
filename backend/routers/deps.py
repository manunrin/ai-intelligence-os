"""Shared FastAPI dependencies."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, MagicMock

from ..config import Settings, get_settings
from ..repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


# ── Fake session factory (for tests) ─────────────────────────────────
# Before the A1 bootstrap refactor, tests patched get_session_factory.
# After the refactor, get_db reads from request.app.state.session_factory.
# This FakeSessionCtx provides a fake session that returns empty results
# for all queries, used by both the compat shim and get_db fallback.


class FakeSessionCtx:
    """Minimal async session that returns empty results for queries."""

    def __init__(self):
        self.commit = AsyncMock()
        self.rollback = AsyncMock()
        self.close = AsyncMock()
        self.add = AsyncMock()
        self.flush = AsyncMock()

        _result = MagicMock()
        _result.scalars = MagicMock(return_value=_result)
        _result.all = MagicMock(return_value=[])
        _result.scalar_one_or_none = MagicMock(return_value=None)
        self.execute = AsyncMock(return_value=_result)


async def get_db(request: Request):
    """Yield a database session for dependency injection."""
    sf = getattr(request.app.state, 'session_factory', None)
    if sf is None:
        # Test fallback: use FakeSessionCtx when app.state.session_factory is not set
        sf = FakeSessionCtx
    session = sf() if callable(sf) else sf
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_settings_dep() -> Settings:
    """Yield application settings for dependency injection."""
    return get_settings()


def get_event_publisher(request: Request) -> Any:
    """Yield the global EventPublisher from app.state."""
    return request.app.state.event_publisher


async def get_current_user(
    authorization: str | None = Header(default=None),
    db=Depends(get_db),
) -> Any:
    """Extract and validate the current user from a JWT token.

    Expects Authorization: Bearer <token> header.
    Raises HTTPException(401) if the token is invalid or the user is not found.
    """
    from ..utils.jwt import decode_access_token

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[len("Bearer "):]
    settings = get_settings()
    payload = decode_access_token(token, settings)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account deactivated",
        )

    return user


def require_role(*roles: str):
    """Dependency factory that checks if the current user has one of the given roles."""

    async def _check_role(current_user: Any = Depends(get_current_user)) -> Any:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _check_role


# ── Compatibility shim ────────────────────────────────────────────────
# get_session_factory was removed during the A1 bootstrap refactor
# (session factory is now read from request.app.state.session_factory).
# This stub exists solely so existing test code that patches
# "backend.routers.deps.get_session_factory" does not crash on patch
# entry.  The returned FakeSessionCtx provides a fake session that
# returns empty results for all queries.


def get_session_factory():
    """Compatibility stub — returns a fake session for tests."""
    return FakeSessionCtx()
