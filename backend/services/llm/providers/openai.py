"""OpenAI provider — Chat Completions API + Embeddings API."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ..base import ChatMessage, ChatResponse, EmbeddingResponse, LLMProvider

logger = logging.getLogger(__name__)

_SYSTEM_ROLES = {"system"}
_USER_ROLES = {"user", "tool"}


class _OpenAIClient:
    """Thin httpx-based OpenAI API client."""

    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        self._api_key = api_key
        self._base_url = base_url or "https://api.openai.com/v1"
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(120.0),
        )

    async def chat(self, model: str, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        resp = await self._client.post("/chat/completions", json={
            "model": model,
            "messages": messages,
            **kwargs,
        })
        resp.raise_for_status()
        return resp.json()

    async def embedding(self, model: str, input_text: str, **kwargs: Any) -> dict[str, Any]:
        resp = await self._client.post("/embeddings", json={
            "model": model,
            "input": input_text,
            **kwargs,
        })
        resp.raise_for_status()
        return resp.json()

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get("/models")
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.warning("OpenAI health check failed: %s", exc)
            return False

    async def close(self) -> None:
        await self._client.aclose()


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        from os import getenv
        self._api_key = api_key or getenv("OPENAI_API_KEY", "")
        self._base_url = base_url
        self._client: _OpenAIClient | None = None

    def _get_client(self) -> _OpenAIClient:
        if self._client is None:
            self._client = _OpenAIClient(self._api_key, self._base_url)
        return self._client

    def _to_openai_messages(self, messages: list[ChatMessage]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for msg in messages:
            role_map: dict[str, str] = {
                "system": "system",
                "user": "user",
                "assistant": "assistant",
                "tool": "tool",
            }
            entry: dict[str, Any] = {"role": role_map.get(msg.role.value, msg.role.value), "content": msg.content}
            if msg.tool_calls:
                entry["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                entry["tool_call_id"] = msg.tool_call_id
            result.append(entry)
        return result

    async def chat(self, messages: list[ChatMessage], model: str = "gpt-4o", **kwargs: Any) -> ChatResponse:
        client = self._get_client()
        openai_msgs = self._to_openai_messages(messages)
        data = await client.chat(model=model, messages=openai_msgs, **kwargs)
        choices = data.get("choices", [])
        content = choices[0]["message"]["content"] if choices else ""
        usage = data.get("usage", {})
        finish_reason = choices[0].get("finish_reason") if choices else None
        return ChatResponse(content=content, finish_reason=finish_reason, usage=usage, raw=data)

    async def embedding(self, text: str, model: str = "text-embedding-3-small", **kwargs: Any) -> EmbeddingResponse:
        client = self._get_client()
        data = await client.embedding(model=model, input_text=text, **kwargs)
        embeddings = [item["embedding"] for item in data.get("data", [])]
        usage = data.get("usage", {})
        return EmbeddingResponse(embeddings=embeddings, usage=usage, raw=data)

    async def health_check(self) -> bool:
        client = self._get_client()
        return await client.health_check()
