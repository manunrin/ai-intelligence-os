"""Compatible provider for any OpenAI-compatible API (Qwen, DeepSeek, etc.)."""

from __future__ import annotations

import os
from typing import Any

from ..base import ChatMessage, ChatResponse, EmbeddingResponse, LLMProvider


class CompatibleProvider(LLMProvider):
    """Provider for services implementing the OpenAI chat/completions API format.

    Works with:
    - Qwen (Tongyi Qianwen)
    - DeepSeek
    - vLLM
    - Any OpenAI-compatible inference server
    """

    name = "compatible"

    def __init__(
        self,
        api_base: str | None = None,
        api_key: str | None = None,
        default_model: str = "qwen-max",
    ) -> None:
        self._api_base = api_base or os.environ.get("COMPATIBLE_API_BASE", "http://localhost:8080/v1")
        self._api_key = api_key or os.environ.get("COMPATIBLE_API_KEY", "")
        self._default_model = default_model

    async def chat(self, messages: list[ChatMessage], model: str | None = None, **kwargs: Any) -> ChatResponse:
        # Placeholder — actual implementation calls {api_base}/chat/completions
        raise NotImplementedError("Compatible provider not yet connected")

    async def embedding(self, text: str, model: str | None = None, **kwargs: Any) -> EmbeddingResponse:
        # Placeholder — actual implementation calls {api_base}/embeddings
        raise NotImplementedError("Compatible provider not yet connected")

    async def health_check(self) -> bool:
        # Placeholder — ping the API base URL
        return True
