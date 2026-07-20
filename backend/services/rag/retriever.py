"""RAG retriever — retrieves relevant KnowledgeItems via hybrid vector+keyword search."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select, func, text, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models.knowledge_item import KnowledgeItem
from ..embedding.client import EmbeddingClient
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
    dense_score: float | None = None
    keyword_score: float | None = None


class RagRetriever:
    """Retrieves relevant KnowledgeItems for a query using hybrid vector+DB search.

    Flow:
        Query → Embed → Vector Search → DB Fetch → Ranked Results
        Query → PostgreSQL FTS → Ranked Results
        Fuse via Reciprocal Rank Fusion (RRF)
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
        hybrid: bool = True,
        dense_weight: float = 1.0,
        keyword_weight: float = 0.8,
    ) -> list[RetrievalResult]:
        """Retrieve relevant knowledge items for a query.

        Args:
            query: Natural language search query.
            limit: Maximum results to return.
            score_threshold: Minimum similarity score (0-1). Applied to fused score in hybrid mode,
                or to vector score in dense-only mode.
            kind_filter: Restrict to kind (article/report/translation).
            tag_filter: Restrict to items with this tag.
            hybrid: If True, combine vector and keyword search via RRF. If False, use vector-only.
            dense_weight: Weight for dense vector branch in RRF fusion.
            keyword_weight: Weight for keyword branch in RRF fusion.

        Returns:
            Ranked list of RetrievalResult.
        """
        if not hybrid:
            return await self._retrieve_dense_only(
                query=query,
                limit=limit,
                score_threshold=score_threshold,
                kind_filter=kind_filter,
                tag_filter=tag_filter,
            )

        # Run both branches in parallel with isolated error handling
        dense_results, keyword_results = await asyncio.gather(
            self._retrieve_dense(query, limit, score_threshold, kind_filter, tag_filter),
            self._retrieve_keyword(query, limit, kind_filter, tag_filter),
        )

        # Filter branches that returned empty due to failures
        if not dense_results and not keyword_results:
            logger.warning("Both dense and keyword search returned no results for query: %s", query)
            return []

        # Fuse results using Reciprocal Rank Fusion
        return self._fuse_results(
            dense_results=dense_results,
            keyword_results=keyword_results,
            limit=limit,
            score_threshold=score_threshold,
            dense_weight=dense_weight,
            keyword_weight=keyword_weight,
        )

    async def _retrieve_dense_only(
        self,
        query: str,
        limit: int,
        score_threshold: float | None,
        kind_filter: str | None,
        tag_filter: str | None,
    ) -> list[RetrievalResult]:
        """Legacy dense-only retrieval path for backward compatibility."""
        try:
            query_embedding = await self._embedding.embed(query)
        except Exception as exc:
            logger.warning("Embedding failed, falling back to DB search: %s", exc)
            return await self._retrieve_keyword(query, limit, kind_filter, tag_filter)

        qdrant_filter = self._build_qdrant_filter(kind_filter, tag_filter)

        try:
            vector_results = await self._vector.search(
                query_vector=query_embedding.embedding,
                limit=limit * 2,
                score_threshold=score_threshold,
                filter=qdrant_filter,
            )
        except Exception as exc:
            logger.warning("Vector search failed, falling back to DB search: %s", exc)
            return await self._retrieve_keyword(query, limit, kind_filter, tag_filter)

        return await self._fetch_and_rank(vector_results, limit)

    async def _retrieve_dense(
        self,
        query: str,
        limit: int,
        score_threshold: float | None,
        kind_filter: str | None,
        tag_filter: str | None,
    ) -> list[RetrievalResult]:
        """Dense vector search branch. Returns empty list on failure."""
        try:
            query_embedding = await self._embedding.embed(query)
        except Exception as exc:
            logger.warning("Embedding failed: %s", exc)
            return []

        qdrant_filter = self._build_qdrant_filter(kind_filter, tag_filter)

        try:
            vector_results = await self._vector.search(
                query_vector=query_embedding.embedding,
                limit=limit * 2,
                score_threshold=score_threshold,
                filter=qdrant_filter,
            )
        except Exception as exc:
            logger.warning("Vector search failed: %s", exc)
            return []

        return await self._fetch_and_rank(vector_results, limit)

    async def _retrieve_keyword(
        self,
        query: str,
        limit: int,
        kind_filter: str | None = None,
        tag_filter: str | None = None,
    ) -> list[RetrievalResult]:
        """Keyword search using PostgreSQL full-text search. Falls back to ILIKE if FTS unavailable."""
        try:
            try:
                return await self._fts_search(query, limit, kind_filter, tag_filter)
            except Exception as exc:
                logger.warning("Full-text search failed, falling back to ILIKE: %s", exc)
                return await self._ilike_search(query, limit, kind_filter, tag_filter)
        except Exception as exc:
            logger.warning("Keyword search failed entirely: %s", exc)
            return []

    async def _fts_search(
        self,
        query: str,
        limit: int,
        kind_filter: str | None = None,
        tag_filter: str | None = None,
    ) -> list[RetrievalResult]:
        """PostgreSQL full-text search using ts_rank via SQLAlchemy ORM."""
        search_vector = func.to_tsvector('english',
                                         func.coalesce(KnowledgeItem.title, '') + ' ' +
                                         func.coalesce(KnowledgeItem.content, ''))
        search_query = func.plainto_tsquery('english', query)

        stmt = (
            select(
                KnowledgeItem,
                func.ts_rank(search_vector, search_query).label('keyword_score'),
            )
            .where(search_vector.op('@@')(search_query))
            .order_by(func.ts_rank(search_vector, search_query).desc())
            .limit(limit)
        )

        if kind_filter:
            stmt = stmt.where(KnowledgeItem.kind == kind_filter)
        if tag_filter:
            stmt = stmt.where(KnowledgeItem.tags.contains([tag_filter]))

        result = await self._session.execute(stmt)
        rows = result.all()

        return [
            RetrievalResult(
                knowledge_id=str(item.id),
                title=item.title,
                content=item.content,
                kind=item.kind,
                score=None,
                tags=list(item.tags) if item.tags else [],
                keyword_score=float(score) if score is not None else 0.0,
            )
            for item, score in rows
        ]

    async def _ilike_search(
        self,
        query: str,
        limit: int,
        kind_filter: str | None = None,
        tag_filter: str | None = None,
    ) -> list[RetrievalResult]:
        """Legacy ILIKE fallback."""
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
                keyword_score=0.0,
            )
            for item in items
        ]

    async def _fetch_and_rank(
        self,
        vector_results: list[dict[str, Any]],
        limit: int,
    ) -> list[RetrievalResult]:
        """Fetch full records from DB and construct RetrievalResult objects."""
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
                    dense_score=hit.get("score"),
                ))

        return ranked[:limit]

    def _build_qdrant_filter(
        self,
        kind_filter: str | None,
        tag_filter: str | None,
    ) -> dict[str, Any] | None:
        """Build Qdrant payload filter from kind and tag filters."""
        if not kind_filter and not tag_filter:
            return None

        must_conditions: list[dict[str, Any]] = []
        if kind_filter:
            must_conditions.append({"key": "kind", "match": {"value": kind_filter}})
        if tag_filter:
            must_conditions.append({"key": "tags", "match": {"value": tag_filter}})

        return {"must": must_conditions}

    def _fuse_results(
        self,
        dense_results: list[RetrievalResult],
        keyword_results: list[RetrievalResult],
        limit: int,
        score_threshold: float | None,
        dense_weight: float,
        keyword_weight: float,
    ) -> list[RetrievalResult]:
        """Fuse dense and keyword results using Reciprocal Rank Fusion (RRF)."""
        k = 60  # Standard RRF smoothing constant

        # Build rank maps: knowledge_id -> (rank, result)
        dense_ranks: dict[str, tuple[int, RetrievalResult]] = {}
        for rank, result in enumerate(dense_results, 1):
            dense_ranks[result.knowledge_id] = (rank, result)

        keyword_ranks: dict[str, tuple[int, RetrievalResult]] = {}
        for rank, result in enumerate(keyword_results, 1):
            keyword_ranks[result.knowledge_id] = (rank, result)

        # Compute fused scores
        fused_scores: dict[str, float] = {}
        for knowledge_id in set(dense_ranks.keys()) | set(keyword_ranks.keys()):
            score = 0.0
            if knowledge_id in dense_ranks:
                rank, _ = dense_ranks[knowledge_id]
                score += dense_weight * (1.0 / (k + rank))
            if knowledge_id in keyword_ranks:
                rank, _ = keyword_ranks[knowledge_id]
                score += keyword_weight * (1.0 / (k + rank))
            fused_scores[knowledge_id] = score

        # Sort by fused score descending
        sorted_ids = sorted(fused_scores.keys(), key=lambda x: fused_scores[x], reverse=True)

        # Apply score threshold
        if score_threshold is not None:
            sorted_ids = [
                kid for kid in sorted_ids
                if fused_scores[kid] >= score_threshold
            ]

        # Construct final results with fused scores
        results: list[RetrievalResult] = []
        for knowledge_id in sorted_ids[:limit]:
            dense_result = dense_ranks.get(knowledge_id)
            keyword_result = keyword_ranks.get(knowledge_id)

            # Merge data from both sources (prefer non-null values)
            title = dense_result[1].title if dense_result else keyword_result[1].title
            content = dense_result[1].content if dense_result else keyword_result[1].content
            kind = dense_result[1].kind if dense_result else keyword_result[1].kind
            tags = dense_result[1].tags if dense_result else keyword_result[1].tags

            results.append(RetrievalResult(
                knowledge_id=knowledge_id,
                title=title,
                content=content,
                kind=kind,
                score=fused_scores[knowledge_id],
                tags=tags,
                dense_score=dense_result[1].dense_score if dense_result else None,
                keyword_score=keyword_result[1].keyword_score if keyword_result else None,
            ))

        return results
