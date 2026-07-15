"""Ollama provider implementation for local models."""

from __future__ import annotations

import os
from typing import Any

from ..base import ChatMessage, ChatResponse, EmbeddingResponse, LLMProvider


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

    async def chat(self, messages: list[ChatMessage], model: str = "mistral", **kwargs: Any) -> ChatResponse:
        # Placeholder — actual implementation calls Ollama /api/chat endpoint
        raise NotImplementedError("Ollama provider not yet connected")

    async def embedding(self, text: str, model: str = "nomic-embed-text", **kwargs: Any) -> EmbeddingResponse:
        # Placeholder — actual implementation calls Ollama /api/embed endpoint
        raise NotImplementedError("Ollama provider not yet connected")

    async def health_check(self) -> bool:
        # Placeholder — ping Ollama /api/tags to verify service is running
        return True
