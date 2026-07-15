"""Anthropic Claude provider — Messages API."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ..base import ChatMessage, ChatResponse, EmbeddingResponse, LLMProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        from os import getenv
        self._api_key = api_key or getenv("ANTHROPIC_API_KEY", "")
        self._base_url = base_url or "https://api.anthropic.com"
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            timeout=httpx.Timeout(120.0),
        )

    def _to_anthropic_messages(self, messages: list[ChatMessage]) -> tuple[str | None, list[dict[str, Any]]]:
        system: str | None = None
        result: list[dict[str, Any]] = []
        for msg in messages:
            role = msg.role.value
            if role == "system":
                system = msg.content
            elif role in ("user", "assistant"):
                result.append({"role": role, "content": msg.content})
            elif role == "tool":
                result.append({
                    "role": "user",
                    "content": [{"type": "tool_result", "tool_use_id": msg.tool_call_id, "content": msg.content}],
                })
        return system, result

    async def chat(self, messages: list[ChatMessage], model: str = "claude-sonnet-4-20250514", **kwargs: Any) -> ChatResponse:
        system, anthropic_msgs = self._to_anthropic_messages(messages)
        payload: dict[str, Any] = {"model": model, "messages": anthropic_msgs, "max_tokens": kwargs.pop("max_tokens", 4096)}
        if system:
            payload["system"] = system
        payload.update(kwargs)
        resp = await self._client.post("/v1/messages", json=payload)
        resp.raise_for_status()
        data = resp.json()
        content_blocks = data.get("content", [])
        content = "\n".join(block.get("text", "") for block in content_blocks if block.get("type") == "text")
        usage = data.get("usage", {})
        return ChatResponse(
            content=content,
            finish_reason=data.get("stop_reason"),
            usage={"prompt_tokens": usage.get("input_tokens", 0), "completion_tokens": usage.get("output_tokens", 0)},
            raw=data,
        )

    async def embedding(self, text: str, model: str = "claude-embed-v1", **kwargs: Any) -> EmbeddingResponse:
        # Anthropic does not offer a separate embedding endpoint
        raise NotImplementedError("Anthropic does not provide embeddings; use a compatible provider")

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get("/v1/messages", params={"model": "claude-sonnet-4-20250514", "max_tokens": 1})
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.warning("Anthropic health check failed: %s", exc)
            return False
