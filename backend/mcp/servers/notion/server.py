"""Notion MCP server — exposes Notion integrations as discoverable tools."""

from __future__ import annotations

import os

from ...base import MCPServerBase, MCPTool
from ...schemas import MCPToolDefinition
from .tools import (
    NotionAppendBlock,
    NotionCreatePage,
    NotionQueryDatabase,
    NotionUpdatePage,
)


class NotionMCPServer(MCPServerBase):
    """MCP server for the Notion API.

    Exposes tools for page management, database queries, and block operations.
    """

    name = "notion"
    version = "0.1.0"
    description = "Notion integration — pages, databases, blocks"

    _tools: dict[str, type[MCPTool]] = {
        "create_page": NotionCreatePage,
        "update_page": NotionUpdatePage,
        "query_database": NotionQueryDatabase,
        "append_block": NotionAppendBlock,
    }

    def available_tools(self) -> list[MCPToolDefinition]:
        return [
            MCPToolDefinition(
                name="create_page",
                description="Create a new Notion page under a parent page or database.",
                parameters={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Page title (first paragraph block).",
                        },
                        "content": {
                            "type": "string",
                            "description": "Markdown-like body content.",
                        },
                        "parent_id": {
                            "type": "string",
                            "description": "Parent page or database ID.",
                        },
                    },
                    "required": ["title", "parent_id"],
                },
            ),
            MCPToolDefinition(
                name="update_page",
                description="Update an existing Notion page's properties or content.",
                parameters={
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "Page to update.",
                        },
                        "properties": {
                            "type": "object",
                            "description": "Notion property patch.",
                        },
                        "content": {
                            "type": "array",
                            "description": "List of blocks to append on top of existing content.",
                        },
                    },
                    "required": ["page_id"],
                },
            ),
            MCPToolDefinition(
                name="query_database",
                description="Query a Notion database with optional filter and sort.",
                parameters={
                    "type": "object",
                    "properties": {
                        "database_id": {
                            "type": "string",
                            "description": "Database to query.",
                        },
                        "filter": {
                            "type": "object",
                            "description": "Notion filter JSON.",
                        },
                        "sorts": {
                            "type": "array",
                            "description": "Notion sort JSON array.",
                        },
                        "page_size": {
                            "type": "integer",
                            "description": "Number of results per page.",
                        },
                    },
                    "required": ["database_id"],
                },
            ),
            MCPToolDefinition(
                name="append_block",
                description="Append blocks to an existing page.",
                parameters={
                    "type": "object",
                    "properties": {
                        "parent_id": {
                            "type": "string",
                            "description": "Page ID to append blocks to.",
                        },
                        "blocks": {
                            "type": "array",
                            "description": "Array of block objects.",
                        },
                    },
                    "required": ["parent_id", "blocks"],
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
