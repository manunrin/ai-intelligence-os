"""Database connection and session management."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..config import get_settings


def _create_engine(settings: type[settings] | None = None):
    if settings is None:
        settings = get_settings()
    return create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_max,
        max_overflow=settings.database_pool_max * 2,
    )


engine = _create_engine()
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    """Yield an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
