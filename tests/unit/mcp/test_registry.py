"""Tests for MCP registry."""

from unittest.mock import MagicMock, AsyncMock

import pytest

from backend.mcp.base import MCPServerBase, MCPTool
from backend.mcp.registry import MCPRegistry
from backend.mcp.schemas import MCPToolDefinition


class _MockServer(MCPServerBase):
    """Minimal server for testing the registry."""

    name = "test"
    version = "0.1.0"
    description = "Mock server"

    def available_tools(self) -> list[MCPToolDefinition]:
        return [
            MCPToolDefinition(
                name="echo",
                description="Echo back input.",
                parameters={"type": "object", "properties": {"text": {"type": "string"}}},
            ),
            MCPToolDefinition(
                name="ping",
                description="Ping the server.",
                parameters={"type": "object"},
            ),
        ]

    def _create_tool(self, tool_name: str) -> MCPTool | None:
        mock_tool = MagicMock(spec=MCPTool)
        mock_tool.name = tool_name
        mock_tool.parameters = {"type": "object"}
        mock_tool.execute = AsyncMock(return_value={"success": True, "data": {}})
        return mock_tool


@pytest.mark.asyncio
async def test_register_server():
    registry = MCPRegistry()
    server = _MockServer()
    registry.register_server(server)

    assert "test" in registry.list_servers()
    assert len(registry.list_tools()) == 2


@pytest.mark.asyncio
async def test_get_tool():
    registry = MCPRegistry()
    server = _MockServer()
    registry.register_server(server)

    tool = registry.get_tool("test.echo")
    assert tool is not None
    assert tool.name == "echo"

    unknown = registry.get_tool("test.nonexistent")
    assert unknown is None


@pytest.mark.asyncio
async def test_list_schemas():
    registry = MCPRegistry()
    server = _MockServer()
    registry.register_server(server)

    schemas = registry.list_schemas()
    assert "test.echo" in schemas
    assert "test.ping" in schemas


@pytest.mark.asyncio
async def test_duplicate_server_registration():
    registry = MCPRegistry()
    server = _MockServer()
    registry.register_server(server)
    registry.register_server(server)  # Should log warning, not double-register

    assert len(registry.list_servers()) == 1


@pytest.mark.asyncio
async def test_initialize_and_shutdown():
    registry = MCPRegistry()
    server = _MockServer()
    registry.register_server(server)

    await registry.initialize_all()
    await registry.shutdown_all()
