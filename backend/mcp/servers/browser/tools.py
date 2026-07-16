"""Browser tool implementations — wired to the real Browser API."""

from __future__ import annotations

import logging
import os
from typing import Any

from ...base import MCPTool
from ...schemas import MCPToolDefinition
from .client import BrowserAPIError, BrowserClient

logger = logging.getLogger(__name__)


def _has_config() -> bool:
    """Check whether a Browser API URL and key are configured."""
    url = os.environ.get("BROWSER_API_URL", "").strip()
    key = os.environ.get("BROWSER_API_KEY", "").strip()
    return bool(url and key)


# ------------------------------------------------------------------
# Tool: search
# ------------------------------------------------------------------

class BrowserSearch(MCPTool):
    @property
    def tool_definition(self) -> MCPToolDefinition:
        return MCPToolDefinition(
            name="search",
            description="Perform a web search and return result snippets.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer"},
                },
                "required": ["query"],
            },
        )

    async def _execute_impl(self, **kwargs: Any) -> Any:
        query = kwargs.get("query", "")
        max_results = kwargs.get("max_results", 5)

        if not _has_config():
            logger.debug("BrowserSearch: no config configured, returning stub")
            return {
                "query": query,
                "results": [],
                "total": 0,
            }

        client = BrowserClient()
        try:
            result = await client.search(query=query, max_results=max_results)
            return {
                "query": query,
                "results": result.get("results", []),
                "total": result.get("total", len(result.get("results", []))),
                "raw": result,
            }
        except BrowserAPIError as exc:
            logger.warning("Browser search failed: %s", exc)
            return {
                "query": query,
                "results": [],
                "total": 0,
                "error": str(exc),
            }


# ------------------------------------------------------------------
# Tool: fetch
# ------------------------------------------------------------------

class BrowserFetch(MCPTool):
    @property
    def tool_definition(self) -> MCPToolDefinition:
        return MCPToolDefinition(
            name="fetch",
            description="Fetch a URL and return its HTML content.",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "format": "uri"},
                },
                "required": ["url"],
            },
        )

    async def _execute_impl(self, **kwargs: Any) -> Any:
        url = kwargs.get("url", "")

        if not _has_config():
            logger.debug("BrowserFetch: no config configured, returning stub")
            return {
                "url": url,
                "status_code": 200,
                "content": "<html><body>Mock content</body></html>",
            }

        client = BrowserClient()
        try:
            result = await client.fetch(url=url)
            return {
                "url": url,
                "status_code": result.get("status_code", 200),
                "content": result.get("content", ""),
                "raw": result,
            }
        except BrowserAPIError as exc:
            logger.warning("Browser fetch failed: %s", exc)
            return {
                "url": url,
                "status_code": 0,
                "content": "",
                "error": str(exc),
            }


# ------------------------------------------------------------------
# Tool: extract
# ------------------------------------------------------------------

class BrowserExtract(MCPTool):
    @property
    def tool_definition(self) -> MCPToolDefinition:
        return MCPToolDefinition(
            name="extract",
            description="Extract structured content from a URL.",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "format": "uri"},
                    "strategy": {
                        "type": "string",
                        "enum": ["article", "links", "metadata"],
                    },
                },
                "required": ["url"],
            },
        )

    async def _execute_impl(self, **kwargs: Any) -> Any:
        url = kwargs.get("url", "")
        strategy = kwargs.get("strategy", "article")

        if not _has_config():
            logger.debug("BrowserExtract: no config configured, returning stub")
            return {
                "url": url,
                "title": "Mock Page Title",
                "extracted": True,
            }

        client = BrowserClient()
        try:
            result = await client.extract(url=url)
            return {
                "url": url,
                "title": result.get("title", ""),
                "extracted": True,
                "raw": result,
            }
        except BrowserAPIError as exc:
            logger.warning("Browser extract failed: %s", exc)
            return {
                "url": url,
                "title": "",
                "extracted": False,
                "error": str(exc),
            }
