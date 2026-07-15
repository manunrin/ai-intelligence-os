"""OpenAI provider implementation."""

from __future__ import annotations

import os
from typing import Any

from ..base import ChatMessage, ChatResponse, EmbeddingResponse, LLMProvider


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._base_url = base_url

    async def chat(self, messages: list[ChatMessage], model: str = "gpt-4o", **kwargs: Any) -> ChatResponse:
        # Placeholder — actual implementation uses httpx to call OpenAI Chat Completions API
        raise NotImplementedError("OpenAI provider not yet connected")

    async def embedding(self, text: str, model: str = "text-embedding-3-small", **kwargs: Any) -> EmbeddingResponse:
        # Placeholder — actual implementation uses httpx to call OpenAI Embeddings API
        raise NotImplementedError("OpenAI provider not yet connected")

    async def health_check(self) -> bool:
        # Placeholder — ping OpenAI API key validation endpoint
        return True
