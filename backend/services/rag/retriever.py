"""RAG retriever — retrieves relevant KnowledgeItems via vector similarity search."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models.knowledge_item import KnowledgeItem
from ..embedding.base import EmbeddingClient
from ..vector.qdrant import QdrantVectorService

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Single retrieval result with context and metadata."""
    knowledge_id: str
    title: str
    content: str
    kind: str
    score: float | None
    tags: list[str]


class RagRetriever:
    """Retrieves relevant KnowledgeItems for a query using hybrid vector+DB search.

    Flow:
        Query → Embed → Vector Search → DB Fetch → Ranked Results
    """

    def __init__(
        self,
        session: AsyncSession,
        embedding_client: EmbeddingClient,
        vector_service: QdrantVectorService,
    ) -> None:
        self._session = session
        self._embedding = embedding_client
        self._vector = vector_service

    async def retrieve(
        self,
        query: str,
        limit: int = 5,
        score_threshold: float | None = None,
        kind_filter: str | None = None,
        tag_filter: str | None = None,
    ) -> list[RetrievalResult]:
        """Retrieve relevant knowledge items for a query.

        Args:
            query: Natural language search query.
            limit: Maximum results to return.
            score_threshold: Minimum vector similarity score (0-1).
            kind_filter: Restrict to kind (article/report/translation).
            tag_filter: Restrict to items with this tag.

        Returns:
            Ranked list of RetrievalResult.
        """
        # Step 1: Generate embedding for the query
        try:
            query_embedding = await self._embedding.embed(query)
        except Exception as exc:
            logger.warning("Embedding failed, falling back to DB search: %s", exc)
            return await self._db_search(query, limit, kind_filter, tag_filter)

        # Step 2: Build Qdrant filter
        qdrant_filter: dict[str, Any] | None = None
        if kind_filter or tag_filter:
            qdrant_filter = {"must": []}
            if kind_filter:
                qdrant_filter["must"].append({"key": "kind", "match": {"value": kind_filter}})
            if tag_filter:
                qdrant_filter["must"].append({"key": "tags", "match": {"value": tag_filter}})

        # Step 3: Vector search
        try:
            vector_results = await self._vector.search(
                query_vector=query_embedding.embedding,
                limit=limit * 2,  # over-fetch to allow re-ranking
                score_threshold=score_threshold,
                filter=qdrant_filter,
            )
        except Exception as exc:
            logger.warning("Vector search failed, falling back to DB search: %s", exc)
            return await self._db_search(query, limit, kind_filter, tag_filter)

        # Step 4: Fetch full records from DB and construct results
        ids = [r["id"] for r in vector_results]
        if not ids:
            return []

        stmt = select(KnowledgeItem).where(KnowledgeItem.id.in_(ids))
        result = await self._session.execute(stmt)
        items_by_id = {str(item.id): item for item in result.scalars().all()}

        ranked: list[RetrievalResult] = []
        for hit in vector_results:
            item = items_by_id.get(hit["id"])
            if item:
                ranked.append(RetrievalResult(
                    knowledge_id=hit["id"],
                    title=item.title,
                    content=item.content,
                    kind=item.kind,
                    score=hit.get("score"),
                    tags=item.tags or [],
                ))

        return ranked[:limit]

    async def _db_search(
        self,
        query: str,
        limit: int,
        kind_filter: str | None = None,
        tag_filter: str | None = None,
    ) -> list[RetrievalResult]:
        """Fallback: simple keyword search against PostgreSQL title/content."""
        from sqlalchemy import or_

        conditions = [
            KnowledgeItem.title.ilike(f"%{query}%"),
            KnowledgeItem.content.ilike(f"%{query}%"),
        ]
        if kind_filter:
            conditions.append(KnowledgeItem.kind == kind_filter)
        if tag_filter:
            conditions.append(KnowledgeItem.tags.contains([tag_filter]))

        stmt = select(KnowledgeItem).where(or_(*conditions)).limit(limit)
        result = await self._session.execute(stmt)
        items = result.scalars().all()

        return [
            RetrievalResult(
                knowledge_id=str(item.id),
                title=item.title,
                content=item.content,
                kind=item.kind,
                score=None,
                tags=item.tags or [],
            )
            for item in items
        ]
