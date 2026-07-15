"""Database connection and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..config import Settings, get_settings

_engine: type | None = None
_session_factory: type | None = None


def create_engine_for_settings(settings: Settings):
    """Create a new async engine bound to the given settings."""
    global _engine, _session_factory
    _engine = create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_max,
        max_overflow=settings.database_pool_min,
        pool_pre_ping=True,
        echo=settings.app_debug,
    )
    _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    return _engine


def get_engine():
    """Return the current async engine, creating it if necessary."""
    global _engine
    if _engine is None:
        create_engine_for_settings(get_settings())
    return _engine


def get_session_factory():
    """Return the current async session factory."""
    global _session_factory
    if _session_factory is None:
        get_engine()
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yield an async DB session with auto-commit/rollback."""
    session = get_session_factory()()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
