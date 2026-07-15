"""Article repository."""

from typing import Any

from sqlalchemy import select

from ..database.models import Article
from .base_repository import BaseRepository


class ArticleRepository(BaseRepository[Article]):
    @property
    def model(self) -> type[Article]:
        return Article

    async def list_by_status(self, status: str) -> list[Article]:
        stmt = select(Article).where(Article.status == status)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_language(self, language: str) -> list[Article]:
        stmt = select(Article).where(Article.language == language)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_source(self, source_id: Any) -> list[Article]:
        stmt = select(Article).where(Article.source_id == source_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
