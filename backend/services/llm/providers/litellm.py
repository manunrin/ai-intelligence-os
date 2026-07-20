"""LiteLLM Gateway provider — unified LLM interface via LiteLLM."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ..base import ChatMessage, ChatResponse, EmbeddingResponse, LLMProvider

logger = logging.getLogger(__name__)


class LiteLLMProvider(LLMProvider):
    name = "litellm"

    def __init__(self, api_base: str | None = None, api_key: str | None = None) -> None:
        from os import getenv
        self._api_base = api_base or getenv("LITELLM_GATEWAY_URL", "http://localhost:4000")
        self._api_key = api_key or getenv("LITELLM_API_KEY", "")
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

    async def chat(self, messages: list[ChatMessage], model: str = "gpt-4o", **kwargs: Any) -> ChatResponse:
        resp = await self._client.post("/v1/chat/completions", json={
            "model": model,
            "messages": self._to_openai_messages(messages),
            **kwargs,
        })
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices", [])
        content = choices[0]["message"]["content"] if choices else ""
        usage = data.get("usage", {})
        finish_reason = choices[0].get("finish_reason") if choices else None
        return ChatResponse(content=content, finish_reason=finish_reason, usage=usage, raw=data)

    async def embedding(self, text: str, model: str = "text-embedding-3-small", **kwargs: Any) -> EmbeddingResponse:
        resp = await self._client.post("/v1/embeddings", json={
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
            resp = await self._client.get("/health/liveness")
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.warning("LiteLLM health check failed: %s", exc)
            return False
