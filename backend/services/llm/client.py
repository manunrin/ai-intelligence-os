"""Unified LLM client — single entry point for all LLM calls."""

from __future__ import annotations

import logging
from typing import Any

from .base import ChatMessage, ChatResponse, EmbeddingResponse, LLMProvider
from .router import LLMRouter

logger = logging.getLogger(__name__)


class LLMClient:
    """High-level client used by agents and tools.

    Delegates all calls to the configured LLMRouter which handles
    provider selection, model routing, and fallback chains.

    Usage:
        client = LLMClient(router)
        response = await client.chat(messages, task="summary")
        embedding = await client.embedding("Hello world", task="search")
    """

    def __init__(self, router: LLMRouter) -> None:
        self._router = router

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        task: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """Send a chat request through the router.

        Args:
            messages: Chat history.
            task: Task category for routing (e.g. "summary", "translation").
                If provided, the router selects the best provider/model.
            model: Explicit model override (bypasses routing).
            temperature: Sampling temperature.
            max_tokens: Maximum response tokens.
            **kwargs: Additional provider parameters.

        Returns:
            ChatResponse from the selected provider.
        """
        return await self._router.chat(
            messages,
            task=task,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    async def embedding(
        self,
        text: str,
        *,
        model: str | None = None,
        **kwargs: Any,
    ) -> EmbeddingResponse:
        """Generate an embedding through the router.

        Args:
            text: Input text.
            model: Explicit model override.
            **kwargs: Additional provider parameters.

        Returns:
            EmbeddingResponse with vector data.
        """
        return await self._router.embedding(text, model=model, **kwargs)

    def get_router(self) -> LLMRouter:
        """Return the underlying router for advanced operations."""
        return self._router
