"""Anthropic Claude provider implementation."""

from __future__ import annotations

import os
from typing import Any

from ..base import ChatMessage, ChatResponse, EmbeddingResponse, LLMProvider


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._base_url = base_url or "https://api.anthropic.com"

    async def chat(self, messages: list[ChatMessage], model: str = "claude-sonnet-4-20250514", **kwargs: Any) -> ChatResponse:
        # Placeholder — actual implementation uses httpx to call Anthropic Messages API
        raise NotImplementedError("Anthropic provider not yet connected")

    async def embedding(self, text: str, model: str = "claude-embed-v1", **kwargs: Any) -> EmbeddingResponse:
        # Anthropic does not provide a separate embedding API; use a compatible endpoint
        raise NotImplementedError("Anthropic provider not yet connected")

    async def health_check(self) -> bool:
        # Placeholder — verify API key with a lightweight request
        return True
