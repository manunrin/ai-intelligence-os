"""Embedding client — manages provider selection and batch operations."""

from __future__ import annotations

import logging
import time as _time

from ...metrics import counter, histogram
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
        start = _time.monotonic()
        try:
            result = await self._provider.embed(text, model=model)
            elapsed = _time.monotonic() - start
            counter("embedding_requests_total", labels={"model": model or "default", "status": "success"})
            histogram("embedding_request_duration_seconds", elapsed, labels={"model": model or "default", "status": "success"})
            return result
        except Exception as exc:
            elapsed = _time.monotonic() - start
            counter("embedding_requests_total", labels={"model": model or "default", "status": "failed"})
            histogram("embedding_request_duration_seconds", elapsed, labels={"model": model or "default", "status": "failed"})
            raise

    async def embed_batch(self, texts: list[str], model: str | None = None) -> list[EmbeddingResult]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of input strings.
            model: Optional model override.

        Returns:
            List of EmbeddingResult, one per input.
        """
        start = _time.monotonic()
        model_label = model or "default"
        success_count = 0
        fail_count = 0
        results: list[EmbeddingResult] = []

        for i, text in enumerate(texts):
            try:
                result = await self._provider.embed(text, model=model)
                results.append(result)
                success_count += 1
            except Exception as exc:
                logger.error("Embedding failed for text[%d]: %s", i, exc)
                results.append(EmbeddingResult(embedding=[], model=model or "default"))
                fail_count += 1

        elapsed = _time.monotonic() - start
        counter("embedding_batch_total", labels={"model": model_label, "status": "success"})
        counter("embedding_batch_items_total", labels={"model": model_label, "result": "success"}, value=success_count)
        counter("embedding_batch_items_total", labels={"model": model_label, "result": "failed"}, value=fail_count)
        histogram("embedding_batch_duration_seconds", elapsed, labels={"model": model_label, "status": "success"})
        return results

    async def health_check(self) -> bool:
        """Check if the underlying embedding backend is healthy."""
        return await self._provider.health_check()
