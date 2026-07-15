"""Knowledge item repository."""

from typing import Any

from sqlalchemy import select

from ..database.models import KnowledgeItem
from .base_repository import BaseRepository


class KnowledgeItemRepository(BaseRepository[KnowledgeItem]):
    @property
    def model(self) -> type[KnowledgeItem]:
        return KnowledgeItem

    async def list_by_kind(self, kind: str) -> list[KnowledgeItem]:
        stmt = select(KnowledgeItem).where(KnowledgeItem.kind == kind)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_tag(self, tag: str) -> list[KnowledgeItem]:
        stmt = select(KnowledgeItem).where(KnowledgeItem.tags.contains([tag]))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_article(self, article_id: Any) -> list[KnowledgeItem]:
        stmt = select(KnowledgeItem).where(KnowledgeItem.article_id == article_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
