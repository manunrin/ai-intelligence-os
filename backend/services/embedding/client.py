"""Embedding client — manages provider selection and batch operations."""

from __future__ import annotations

import logging

from .base import EmbeddingProvider, EmbeddingResult

logger = logging.getLogger(__name__)


class EmbeddingClient:
    """High-level embedding interface used by KnowledgeService and RAG.

    Delegates to an EmbeddingProvider (typically backed by LLMGatewayEmbeddingProvider).
    """

    def __init__(self, provider: EmbeddingProvider) -> None:
        self._provider = provider

    async def embed(self, text: str, model: str | None = None) -> EmbeddingResult:
        """Generate embedding for a single text string.

        Args:
            text: Input text.
            model: Optional model override.

        Returns:
            EmbeddingResult with vector and metadata.
        """
        return await self._provider.embed(text, model=model)

    async def embed_batch(self, texts: list[str], model: str | None = None) -> list[EmbeddingResult]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of input strings.
            model: Optional model override.

        Returns:
            List of EmbeddingResult, one per input.
        """
        results: list[EmbeddingResult] = []
        for i, text in enumerate(texts):
            try:
                result = await self._provider.embed(text, model=model)
                results.append(result)
            except Exception as exc:
                logger.error("Embedding failed for text[%d]: %s", i, exc)
                results.append(EmbeddingResult(embedding=[], model=model or "default"))
        return results

    async def health_check(self) -> bool:
        """Check if the underlying embedding backend is healthy."""
        return await self._provider.health_check()
