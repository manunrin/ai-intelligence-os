"""Notion tool implementations (mocked for Phase 5-A)."""

from __future__ import annotations

from typing import Any

from ...base import MCPTool
from ...schemas import MCPToolDefinition


class NotionCreatePage(MCPTool):
    @property
    def tool_definition(self) -> MCPToolDefinition:
        return MCPToolDefinition(
            name="create_page",
            description="Create a new Notion page under a parent page or database.",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "parent_id": {"type": "string"},
                },
                "required": ["title", "parent_id"],
            },
        )

    async def _execute_impl(self, **kwargs: Any) -> Any:
        # TODO: Replace with real Notion API call (Phase 5-B)
        return {
            "id": "mock-page-id",
            "url": f"https://notion.so/mock-page-id",
            "title": kwargs.get("title", ""),
            "parent_id": kwargs.get("parent_id", ""),
        }


class NotionUpdatePage(MCPTool):
    @property
    def tool_definition(self) -> MCPToolDefinition:
        return MCPToolDefinition(
            name="update_page",
            description="Update an existing Notion page's properties or content.",
            parameters={
                "type": "object",
                "properties": {
                    "page_id": {"type": "string"},
                    "properties": {"type": "object"},
                    "content": {"type": "array"},
                },
                "required": ["page_id"],
            },
        )

    async def _execute_impl(self, **kwargs: Any) -> Any:
        return {"page_id": kwargs.get("page_id"), "updated": True}


class NotionQueryDatabase(MCPTool):
    @property
    def tool_definition(self) -> MCPToolDefinition:
        return MCPToolDefinition(
            name="query_database",
            description="Query a Notion database with optional filter and sort.",
            parameters={
                "type": "object",
                "properties": {
                    "database_id": {"type": "string"},
                    "filter": {"type": "object"},
                    "sorts": {"type": "array"},
                    "page_size": {"type": "integer"},
                },
                "required": ["database_id"],
            },
        )

    async def _execute_impl(self, **kwargs: Any) -> Any:
        return {
            "results": [],
            "has_more": False,
            "database_id": kwargs.get("database_id", ""),
        }


class NotionAppendBlock(MCPTool):
    @property
    def tool_definition(self) -> MCPToolDefinition:
        return MCPToolDefinition(
            name="append_block",
            description="Append blocks to an existing page.",
            parameters={
                "type": "object",
                "properties": {
                    "parent_id": {"type": "string"},
                    "blocks": {"type": "array"},
                },
                "required": ["parent_id", "blocks"],
            },
        )

    async def _execute_impl(self, **kwargs: Any) -> Any:
        return {
            "parent_id": kwargs.get("parent_id", ""),
            "block_count": len(kwargs.get("blocks", [])),
            "created": True,
        }
