"""Notion tool implementations — wired to the real Notion API."""

from __future__ import annotations

import logging
import os
from typing import Any

from ...base import MCPTool
from ...schemas import MCPToolDefinition
from .client import NotionAPIError, NotionClient

logger = logging.getLogger(__name__)


def _has_token() -> bool:
    """Check whether a valid Notion token is configured."""
    return len(os.environ.get("NOTION_TOKEN", "").strip()) > 0


def _build_blocks(content: str) -> list[dict[str, Any]]:
    """Convert a plain-text content string into Notion paragraph blocks."""
    lines = [l for l in content.split("\n") if l.strip()]
    return [
        {
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": l.strip()}}]
            },
        }
        for l in lines
    ]


# ------------------------------------------------------------------
# Tool: create_page
# ------------------------------------------------------------------

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
        title = kwargs.get("title", "")
        parent_id = kwargs.get("parent_id", "")
        content_raw = kwargs.get("content", None)

        if not _has_token():
            logger.debug("NotionCreatePage: no token configured, returning stub")
            return {
                "id": "mock-page-id",
                "url": f"https://notion.so/mock-page-id",
                "title": title,
                "parent_id": parent_id,
            }

        client = NotionClient()
        blocks = _build_blocks(content_raw) if content_raw else None

        try:
            page = await client.create_page(
                parent_id=parent_id,
                title=title,
                content=blocks,
            )
            return {
                "id": page.get("id", ""),
                "url": page.get("url", ""),
                "title": title,
                "parent_id": parent_id,
                "raw": page,
            }
        except NotionAPIError as exc:
            logger.warning("Notion create_page failed: %s (%s)", exc, exc.code)
            return {
                "id": "",
                "url": "",
                "title": title,
                "parent_id": parent_id,
                "error": str(exc),
            }


# ------------------------------------------------------------------
# Tool: update_page
# ------------------------------------------------------------------

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
        page_id = kwargs.get("page_id", "")
        properties = kwargs.get("properties", None)

        if not _has_token():
            logger.debug("NotionUpdatePage: no token configured, returning stub")
            return {"page_id": page_id, "updated": True}

        client = NotionClient()
        try:
            page = await client.update_page(
                page_id=page_id,
                properties=properties,
            )
            return {
                "page_id": page_id,
                "updated": True,
                "raw": page,
            }
        except NotionAPIError as exc:
            logger.warning("Notion update_page failed: %s (%s)", exc, exc.code)
            return {
                "page_id": page_id,
                "updated": False,
                "error": str(exc),
            }


# ------------------------------------------------------------------
# Tool: query_database
# ------------------------------------------------------------------

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
        database_id = kwargs.get("database_id", "")
        filter_spec = kwargs.get("filter", None)
        sorts = kwargs.get("sorts", None)
        page_size = kwargs.get("page_size", None)

        if not _has_token():
            logger.debug("NotionQueryDatabase: no token configured, returning stub")
            return {
                "results": [],
                "has_more": False,
                "database_id": database_id,
            }

        client = NotionClient()
        try:
            result = await client.query_database(
                database_id=database_id,
                filter=filter_spec,
                sorts=sorts,
                page_size=page_size,
            )
            return {
                "results": result.get("results", []),
                "has_more": result.get("has_more", False),
                "database_id": database_id,
                "raw": result,
            }
        except NotionAPIError as exc:
            logger.warning("Notion query_database failed: %s (%s)", exc, exc.code)
            return {
                "results": [],
                "has_more": False,
                "database_id": database_id,
                "error": str(exc),
            }


# ------------------------------------------------------------------
# Tool: append_block
# ------------------------------------------------------------------

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
        parent_id = kwargs.get("parent_id", "")
        blocks = kwargs.get("blocks", [])

        if not _has_token():
            logger.debug("NotionAppendBlock: no token configured, returning stub")
            return {
                "parent_id": parent_id,
                "block_count": len(blocks),
                "created": True,
            }

        client = NotionClient()
        try:
            result = await client.append_block(
                parent_id=parent_id,
                blocks=blocks,
            )
            return {
                "parent_id": parent_id,
                "block_count": len(blocks),
                "created": True,
                "raw": result,
            }
        except NotionAPIError as exc:
            logger.warning("Notion append_block failed: %s (%s)", exc, exc.code)
            return {
                "parent_id": parent_id,
                "block_count": len(blocks),
                "created": False,
                "error": str(exc),
            }
