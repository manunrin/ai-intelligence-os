"""Database connection and session management."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..config import Settings


def create_engine_for_settings(settings: Settings):
    """Create a new async engine and session factory bound to the given settings.

    Returns ``(engine, session_factory)`` for storage in ``app.state``.
    This replaces the previous global-mutating pattern so that each app
    instance owns its own engine/factory pair — a requirement for
    process-based deployment and reliable testing.
    """
    engine = create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_min,
        max_overflow=settings.database_pool_max - settings.database_pool_min,
        pool_pre_ping=True,
        echo=settings.app_debug,
    )
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, factory


async def get_session_from_factory(session_factory) -> AsyncGenerator[AsyncSession, None]:
    """Yield a DB session from a *provided* factory (not a global).

    Used by routers via ``Depends(get_db)`` which reads the factory
    from ``request.app.state.session_factory``.
    """
    session = session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
