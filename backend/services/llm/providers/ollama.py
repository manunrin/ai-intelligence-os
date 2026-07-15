"""Ollama provider — local inference server."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ..base import ChatMessage, ChatResponse, EmbeddingResponse, LLMProvider

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, base_url: str | None = None) -> None:
        from os import getenv
        self._base_url = base_url or getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(300.0),
        )

    def _to_ollama_messages(self, messages: list[ChatMessage]) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        for msg in messages:
            result.append({"role": msg.role.value, "content": msg.content})
        return result

    async def chat(self, messages: list[ChatMessage], model: str = "mistral", **kwargs: Any) -> ChatResponse:
        resp = await self._client.post("/v1/chat/completions", json={
            "model": model,
            "messages": self._to_ollama_messages(messages),
            **kwargs,
        })
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices", [])
        content = choices[0]["message"]["content"] if choices else ""
        usage = data.get("usage", {})
        return ChatResponse(
            content=content,
            finish_reason=choices[0].get("finish_reason") if choices else None,
            usage=usage,
            raw=data,
        )

    async def embedding(self, text: str, model: str = "nomic-embed-text", **kwargs: Any) -> EmbeddingResponse:
        resp = await self._client.post("/api/embed", json={
            "model": model,
            "input": text,
        })
        resp.raise_for_status()
        data = resp.json()
        embedding = data.get("embedding", [])
        return EmbeddingResponse(embeddings=[[embedding]] if embedding else [], raw=data)

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get("/api/tags")
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.warning("Ollama health check failed: %s", exc)
            return False
