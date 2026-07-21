"""Anthropic Claude provider — Messages API."""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

import httpx

from ..base import ChatMessage, ChatResponse, EmbeddingResponse, LLMProvider

logger = logging.getLogger(__name__)


class _AnthropicClient:
    """Thin httpx-based Anthropic API client."""

    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        self._api_key = api_key
        self._base_url = base_url or "https://api.anthropic.com"
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
                "accept": "text/event-stream",
            },
            timeout=httpx.Timeout(120.0),
        )

    async def chat(self, model: str, messages: list[dict[str, Any]], system: str | None = None, **kwargs: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {"model": model, "messages": messages, "max_tokens": kwargs.pop("max_tokens", 4096)}
        if system:
            payload["system"] = system
        payload.update(kwargs)
        resp = await self._client.post("/v1/messages", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def stream_chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
        system: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream chat completion tokens from Anthropic SSE endpoint."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
            **kwargs,
        }
        if system:
            payload["system"] = system

        async with self._client.stream("POST", "/v1/messages", json=payload) as resp:
            resp.raise_for_status()

            buffer = ""
            async for chunk in resp.aiter_text():
                buffer += chunk

                while "\n\n" in buffer:
                    event_data, buffer = buffer.split("\n\n", 1)

                    lines = event_data.strip().split("\n")
                    event_type = None
                    data_lines: list[str] = []

                    for line in lines:
                        if line.startswith("event: "):
                            event_type = line[7:].strip()
                        elif line.startswith("data: "):
                            data_lines.append(line[6:])

                    if event_type == "content_block_delta":
                        try:
                            data = json.loads(data_lines[0])
                            delta = data.get("delta", {})
                            text = delta.get("text", "")
                            if text:
                                yield text
                        except json.JSONDecodeError:
                            continue

    async def embedding(self, model: str, input_text: str, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError("Anthropic does not provide embeddings; use a compatible provider")

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get("/v1/messages", params={"model": "claude-sonnet-4-20250514", "max_tokens": 1})
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.warning("Anthropic health check failed: %s", exc)
            return False

    async def close(self) -> None:
        await self._client.aclose()


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        from os import getenv
        self._api_key = api_key or getenv("ANTHROPIC_API_KEY", "")
        self._base_url = base_url
        self._client: _AnthropicClient | None = None

    def _get_client(self) -> _AnthropicClient:
        if self._client is None:
            self._client = _AnthropicClient(self._api_key, self._base_url)
        return self._client

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
        client = self._get_client()
        system, anthropic_msgs = self._to_anthropic_messages(messages)
        data = await client.chat(model=model, messages=anthropic_msgs, system=system, **kwargs)
        content_blocks = data.get("content", [])
        content = "\n".join(block.get("text", "") for block in content_blocks if block.get("type") == "text")
        usage = data.get("usage", {})
        return ChatResponse(
            content=content,
            finish_reason=data.get("stop_reason"),
            usage={"prompt_tokens": usage.get("input_tokens", 0), "completion_tokens": usage.get("output_tokens", 0)},
            raw=data,
        )

    async def stream(self, messages: list[ChatMessage], model: str, **kwargs: Any) -> AsyncIterator[str]:
        """Stream a chat completion token by token."""
        client = self._get_client()
        system, anthropic_msgs = self._to_anthropic_messages(messages)
        async for chunk in client.stream_chat(model=model, messages=anthropic_msgs, system=system, **kwargs):
            yield chunk

    async def embedding(self, text: str, model: str = "claude-embed-v1", **kwargs: Any) -> EmbeddingResponse:
        # Anthropic does not offer a separate embedding endpoint
        raise NotImplementedError("Anthropic does not provide embeddings; use a compatible provider")

    async def health_check(self) -> bool:
        client = self._get_client()
        return await client.health_check()

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
