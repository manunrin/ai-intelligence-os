"""Compatible provider — any OpenAI-format API (Qwen, DeepSeek, vLLM)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ..base import ChatMessage, ChatResponse, EmbeddingResponse, LLMProvider

logger = logging.getLogger(__name__)


class CompatibleProvider(LLMProvider):
    name = "compatible"

    def __init__(
        self,
        api_base: str | None = None,
        api_key: str | None = None,
        default_model: str = "qwen-max",
    ) -> None:
        from os import getenv
        self._api_base = api_base or getenv("COMPATIBLE_API_BASE", "http://localhost:8080/v1")
        self._api_key = api_key or getenv("COMPATIBLE_API_KEY", "")
        self._default_model = default_model
        self._client = httpx.AsyncClient(
            base_url=self._api_base,
            headers={"Authorization": f"Bearer {self._api_key}"} if self._api_key else {},
            timeout=httpx.Timeout(120.0),
        )

    def _to_openai_messages(self, messages: list[ChatMessage]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for msg in messages:
            entry: dict[str, Any] = {"role": msg.role.value, "content": msg.content}
            if msg.tool_calls:
                entry["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                entry["tool_call_id"] = msg.tool_call_id
            result.append(entry)
        return result

    async def chat(self, messages: list[ChatMessage], model: str | None = None, **kwargs: Any) -> ChatResponse:
        model = model or self._default_model
        resp = await self._client.post("/chat/completions", json={
            "model": model,
            "messages": self._to_openai_messages(messages),
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

    async def embedding(self, text: str, model: str | None = None, **kwargs: Any) -> EmbeddingResponse:
        model = model or self._default_model
        resp = await self._client.post("/embeddings", json={
            "model": model,
            "input": text,
            **kwargs,
        })
        resp.raise_for_status()
        data = resp.json()
        embeddings = [item["embedding"] for item in data.get("data", [])]
        usage = data.get("usage", {})
        return EmbeddingResponse(embeddings=embeddings, usage=usage, raw=data)

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get("/models")
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.warning("Compatible provider health check failed: %s", exc)
            return False
