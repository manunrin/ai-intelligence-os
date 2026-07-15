"""Lightweight MCP client that communicates with an MCP server over HTTP/SSE."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class MCPClient:
    """HTTP client for talking to a remote MCP server.

    The client uses the standard MCP transport protocol (JSON-RPC over
    HTTP) as defined in the Model Context Protocol specification.
    """

    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._headers(),
            timeout=30.0,
        )

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available tools on the remote MCP server."""
        resp = await self._client.post("/tools/list")
        resp.raise_for_status()
        return resp.json().get("tools", [])

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Invoke a tool exposed by the remote MCP server."""
        resp = await self._client.post(
            "/tools/call",
            json={"name": tool_name, "arguments": arguments},
        )
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        await self._client.aclose()
