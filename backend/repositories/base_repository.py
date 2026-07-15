"""Repository base for common CRUD operations."""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

ModelT = TypeVar("ModelT")


class BaseRepository(ABC, Generic[ModelT]):
    """Generic async repository providing standard CRUD."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @property
    @abstractmethod
    def model(self) -> type[ModelT]:
        """Return the ORM model this repository manages."""

    async def get_by_id(self, id: Any) -> ModelT | None:
        """Fetch a single entity by primary key."""
        return await self.session.get(self.model, id)

    async def list_all(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        order_by: InstrumentedAttribute | None = None,
        descending: bool = True,
    ) -> list[ModelT]:
        """List entities with pagination."""
        stmt = select(self.model)
        if order_by is not None:
            stmt = stmt.order_by(order_by.desc() if descending else order_by.asc())
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self) -> int:
        """Count total rows."""
        stmt = select(func.count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def create(self, **kwargs: Any) -> ModelT:
        """Insert a new entity."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, id: Any, **kwargs: Any) -> ModelT | None:
        """Update an existing entity by primary key."""
        instance = await self.get_by_id(id)
        if instance is None:
            return None
        for key, value in kwargs.items():
            setattr(instance, key, value)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, id: Any) -> bool:
        """Delete an entity by primary key. Returns True if deleted."""
        instance = await self.get_by_id(id)
        if instance is None:
            return False
        await self.session.delete(instance)
        await self.session.flush()
        return True

    async def execute(self, stmt: Select) -> list[ModelT]:
        """Execute a pre-built select statement."""
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
