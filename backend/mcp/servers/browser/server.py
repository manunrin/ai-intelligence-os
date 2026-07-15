"""Browser MCP server — exposes web interaction tools for research agents."""

from __future__ import annotations

from typing import Type

from ...base import MCPServerBase, MCPTool
from ...schemas import MCPToolDefinition
from .tools import BrowserExtract, BrowserFetch, BrowserSearch


class BrowserMCPServer(MCPServerBase):
    """MCP server for browser-based web interactions.

    Exposes tools for search, page fetching, and content extraction.
    Designed for future news-collection and research agents.
    """

    name = "browser"
    version = "0.1.0"
    description = "Browser integration — search, fetch, extract web content"

    _tools: dict[str, Type[MCPTool]] = {
        "search": BrowserSearch,
        "fetch": BrowserFetch,
        "extract": BrowserExtract,
    }

    def available_tools(self) -> list[MCPToolDefinition]:
        return [
            MCPToolDefinition(
                name="search",
                description="Perform a web search and return result snippets.",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query.",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return.",
                        },
                    },
                    "required": ["query"],
                },
            ),
            MCPToolDefinition(
                name="fetch",
                description="Fetch a URL and return its HTML content.",
                parameters={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "format": "uri",
                            "description": "URL to fetch.",
                        },
                    },
                    "required": ["url"],
                },
            ),
            MCPToolDefinition(
                name="extract",
                description="Extract structured content (articles, links, metadata) from a URL.",
                parameters={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "format": "uri",
                            "description": "URL to extract from.",
                        },
                        "strategy": {
                            "type": "string",
                            "enum": ["article", "links", "metadata"],
                            "description": "Extraction strategy.",
                        },
                    },
                    "required": ["url"],
                },
            ),
        ]

    def _create_tool(self, tool_name: str) -> MCPTool | None:
        cls = self._tools.get(tool_name)
        if cls is None:
            return None
        instance = cls()
        instance.server = self
        return instance
