"""Unified embedding service — wraps LLM providers for vector generation."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..llm.base import EmbeddingResponse

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Single text embedding result."""
    embedding: list[float]
    model: str
    usage: dict | None = None


class EmbeddingProvider(ABC):
    """Interface for embedding backends."""

    @abstractmethod
    async def embed(self, text: str, model: str | None = None) -> EmbeddingResult:
        """Generate embedding for a single text."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the embedding backend is available."""


class LLMGatewayEmbeddingProvider(EmbeddingProvider):
    """Wraps LLMRouter.embedding() as an EmbeddingProvider."""

    def __init__(self, router) -> None:  # type: ignore[no-untyped-def]
        self._router = router

    async def embed(self, text: str, model: str | None = None) -> EmbeddingResult:
        resp: EmbeddingResponse = await self._router.embedding(text, model=model)
        embedding = resp.embeddings[0] if resp.embeddings else []
        return EmbeddingResult(embedding=embedding, model=model or "default", usage=resp.usage)

    async def health_check(self) -> bool:
        try:
            health = await self._router.check_health()
            return any(health.values())
        except Exception:
            return False
