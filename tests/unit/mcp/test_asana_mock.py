"""Tests for Asana MCP server tools."""

import pytest

from backend.mcp.servers.asana.server import AsanaMCPServer
from backend.mcp.servers.asana.tools import (
    AsanaAddComment,
    AsanaCompleteTask,
    AsanaCreateTask,
    AsanaUpdateTaskStatus,
)


def test_server_available_tools():
    server = AsanaMCPServer()
    tools = server.available_tools()
    assert len(tools) == 4
    names = {t.name for t in tools}
    assert names == {"create_task", "update_task_status", "complete_task", "add_comment"}


def test_create_tool_factory():
    server = AsanaMCPServer()
    tool = server._create_tool("create_task")
    assert isinstance(tool, AsanaCreateTask)
    assert tool.server is server


def test_unknown_tool_returns_none():
    server = AsanaMCPServer()
    tool = server._create_tool("nonexistent")
    assert tool is None


@pytest.mark.asyncio
async def test_create_task():
    server = AsanaMCPServer()
    tool = server._create_tool("create_task")
    result = await tool.execute(name="Fix bug", project="proj-1", priority="high")
    assert result["success"] is True
    assert result["data"]["name"] == "Fix bug"


@pytest.mark.asyncio
async def test_update_task_status():
    server = AsanaMCPServer()
    tool = server._create_tool("update_task_status")
    result = await tool.execute(task_id="task-1", status="in_progress")
    assert result["success"] is True
    assert result["data"]["status"] == "in_progress"


@pytest.mark.asyncio
async def test_complete_task():
    server = AsanaMCPServer()
    tool = server._create_tool("complete_task")
    result = await tool.execute(task_id="task-1")
    assert result["success"] is True
    assert result["data"]["completed"] is True


@pytest.mark.asyncio
async def test_add_comment():
    server = AsanaMCPServer()
    tool = server._create_tool("add_comment")
    result = await tool.execute(task_id="task-1", text="Done!")
    assert result["success"] is True
    assert result["data"]["text"] == "Done!"
