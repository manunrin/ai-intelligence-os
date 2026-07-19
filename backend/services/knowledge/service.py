"""Knowledge persistence service — creates KnowledgeItem records with embeddings."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models.knowledge_item import KnowledgeItem
from ..embedding.base import EmbeddingResult
from ..vector.qdrant import QdrantPoint, QdrantVectorService

logger = logging.getLogger(__name__)


class KnowledgeService:
    """Manages KnowledgeItem creation and retrieval.

    Used by pipeline nodes and worker jobs to persist agent output
    into the knowledge_items table. Optionally generates embeddings
    and upserts to the vector store.
    """

    def __init__(
        self,
        session: AsyncSession,
        vector_service: QdrantVectorService | None = None,
    ) -> None:
        self._session = session
        self._vector = vector_service

    async def create(
        self,
        title: str,
        content: str,
        kind: str,
        *,
        article_id: UUID | None = None,
        source_id: UUID | None = None,
        tags: list[str] | None = None,
        embedding_model: str | None = None,
        embedding_dimension: int | None = None,
        # Embedding generation
        embed: bool = False,
        embedding_client=None,  # EmbeddingClient (lazy import)
    ) -> KnowledgeItem:
        """Persist a knowledge item to the database.

        Args:
            title: Knowledge entry title.
            content: Full knowledge body.
            kind: article | report | note | translation
            article_id: Associated article (optional).
            source_id: Originating source (optional).
            tags: Classification tags.
            embedding_model: Embedding model name (optional).
            embedding_dimension: Vector dimension (optional).
            embed: If True, generate embedding and upsert to vector store.
            embedding_client: EmbeddingClient instance (required if embed=True).

        Returns:
            The persisted KnowledgeItem instance.
        """
        item = KnowledgeItem(
            title=title,
            content=content,
            kind=kind,
            article_id=article_id,
            source_id=source_id,
            tags=tags or [],
            embedding_model=embedding_model,
            embedding_dimension=embedding_dimension,
        )
        self._session.add(item)
        await self._session.flush()

        # Generate embedding and upsert to vector store
        if embed and embedding_client is not None:
            try:
                result = await embedding_client.embed(content)
                item.embedding_model = result.model
                item.embedding_dimension = len(result.embedding)
                if self._vector and result.embedding:
                    await self._vector.upsert([
                        QdrantPoint(
                            id=item.id,
                            vector=result.embedding,
                            payload={
                                "title": title,
                                "kind": kind,
                                "article_id": str(article_id) if article_id else None,
                                "tags": tags or [],
                            },
                        )
                    ])
                logger.info("Embedded and upserted KnowledgeItem %s", item.id)
            except Exception as exc:
                logger.warning("Embedding failed for '%s': %s", title, exc)

        return item

    async def create_from_analysis(
        self,
        article_id: UUID,
        analysis_result: dict[str, Any],
        tags: list[str] | None = None,
    ) -> KnowledgeItem:
        """Create a KnowledgeItem from AnalystAgent output.

        Args:
            article_id: The article this analysis belongs to.
            analysis_result: Output from AnalystAgent.execute().
            tags: Optional classification tags.

        Returns:
            The persisted KnowledgeItem.
        """
        response = (analysis_result or {}).get("response", "")
        score = (analysis_result or {}).get("importance_score")

        return await self.create(
            title=f"Analysis: {response[:80]}",
            content=response,
            kind="report",
            article_id=article_id,
            tags=tags or ["analysis"],
        )

    async def create_from_translation(
        self,
        article_id: UUID,
        translation_result: dict[str, Any],
        target_language: str,
    ) -> KnowledgeItem:
        """Create a KnowledgeItem from TranslatorAgent output.

        Args:
            article_id: The article this translation belongs to.
            translation_result: Output from TranslatorAgent.execute().
            target_language: Target language code.

        Returns:
            The persisted KnowledgeItem.
        """
        response = (translation_result or {}).get("response", "")

        return await self.create(
            title=f"Translation ({target_language})",
            content=response,
            kind="translation",
            article_id=article_id,
            tags=["translation", target_language],
        )
