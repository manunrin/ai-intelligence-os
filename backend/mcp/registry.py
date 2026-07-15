"""Central registry for MCP servers and tool discovery."""

from __future__ import annotations

import logging
from typing import Any

from .base import MCPServerBase, MCPTool
from .schemas import MCPServerConfig, MCPToolDefinition

logger = logging.getLogger(__name__)


class MCPRegistry:
    """Discovers and routes tool calls across all registered MCP servers.

    Agents query the registry via ``get_tool()`` using a dotted name like
    ``"notion.create_page"``.  The registry resolves the name to the
    appropriate server and tool instance.
    """

    def __init__(self) -> None:
        self._servers: dict[str, MCPServerBase] = {}
        self._tools: dict[str, MCPTool] = {}

    # ------------------------------------------------------------------
    # Server lifecycle
    # ------------------------------------------------------------------

    def register_server(self, server: MCPServerBase) -> None:
        """Register an MCP server and all its tools."""
        if server.name in self._servers:
            logger.warning("Server %s already registered, skipping", server.name)
            return

        self._servers[server.name] = server

        for tool_def in server.available_tools():
            full_name = f"{server.name}.{tool_def.name}"
            tool_instance = server._create_tool(tool_def.name)
            if tool_instance:
                self._tools[full_name] = tool_instance

        logger.info(
            "Registered MCP server '%s' with %d tool(s)",
            server.name,
            len(server.available_tools()),
        )

    async def initialize_all(self) -> None:
        """Call ``initialize()`` on every registered server."""
        for server in self._servers.values():
            await server.initialize()

    async def shutdown_all(self) -> None:
        """Call ``shutdown()`` on every registered server."""
        for server in self._servers.values():
            await server.shutdown()

    # ------------------------------------------------------------------
    # Tool lookup
    # ------------------------------------------------------------------

    def get_tool(self, tool_name: str) -> MCPTool | None:
        """Resolve a tool by its fully-qualified name.

        Example::

            tool = registry.get_tool("notion.create_page")
            result = await tool.execute(title="AI News", content="...")

        Args:
            tool_name: Dotted name like ``"server.tool"``.

        Returns:
            The ``MCPTool`` instance, or ``None`` if not found.
        """
        return self._tools.get(tool_name)

    def list_tools(self) -> dict[str, MCPTool]:
        """Return all registered tools."""
        return dict(self._tools)

    def list_schemas(self) -> dict[str, dict[str, Any]]:
        """Return tool name -> parameter schema mapping for LLM prompting."""
        return {
            name: tool.parameters
            for name, tool in self._tools.items()
        }

    def list_servers(self) -> dict[str, MCPServerBase]:
        """Return all registered servers."""
        return dict(self._servers)
