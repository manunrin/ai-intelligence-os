"""Tests for Notion MCP server tools."""

import pytest

from backend.mcp.servers.notion.server import NotionMCPServer
from backend.mcp.servers.notion.tools import (
    NotionAppendBlock,
    NotionCreatePage,
    NotionQueryDatabase,
    NotionUpdatePage,
)


def test_server_available_tools():
    server = NotionMCPServer()
    tools = server.available_tools()
    assert len(tools) == 4
    names = {t.name for t in tools}
    assert names == {"create_page", "update_page", "query_database", "append_block"}


def test_create_tool_factory():
    server = NotionMCPServer()
    tool = server._create_tool("create_page")
    assert isinstance(tool, NotionCreatePage)
    assert tool.server is server


def test_unknown_tool_returns_none():
    server = NotionMCPServer()
    tool = server._create_tool("nonexistent")
    assert tool is None


@pytest.mark.asyncio
async def test_create_page():
    server = NotionMCPServer()
    tool = server._create_tool("create_page")
    result = await tool.execute(title="AI News", parent_id="parent-123", content="Hello")
    assert result["success"] is True
    assert result["data"]["title"] == "AI News"
    assert result["data"]["parent_id"] == "parent-123"


@pytest.mark.asyncio
async def test_update_page():
    server = NotionMCPServer()
    tool = server._create_tool("update_page")
    result = await tool.execute(page_id="page-456", properties={"title": "Updated"})
    assert result["success"] is True
    assert result["data"]["updated"] is True


@pytest.mark.asyncio
async def test_query_database():
    server = NotionMCPServer()
    tool = server._create_tool("query_database")
    result = await tool.execute(database_id="db-789")
    assert result["success"] is True
    assert result["data"]["database_id"] == "db-789"


@pytest.mark.asyncio
async def test_append_block():
    server = NotionMCPServer()
    tool = server._create_tool("append_block")
    blocks = [{"type": "paragraph", "text": "Hello"}]
    result = await tool.execute(parent_id="page-123", blocks=blocks)
    assert result["success"] is True
    assert result["data"]["block_count"] == 1
