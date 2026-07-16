"""Shared FastAPI dependencies."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings, get_settings
from ..database.connection import get_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session for dependency injection."""
    async with get_session_factory() as session:
        yield session


async def get_settings_dep() -> Settings:
    """Yield application settings for dependency injection."""
    return get_settings()
