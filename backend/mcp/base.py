"""Abstract base classes for MCP servers and tools."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from .schemas import MCPToolDefinition

logger = logging.getLogger(__name__)


class MCPServerBase(ABC):
    """Base class for all MCP servers.

    An MCP server exposes a set of tools that agents can invoke
    through the MCP registry.  Subclasses must declare their tools
    via available_tools() and provide a factory method via
    _create_tool().
    """

    name: str = "mcp_server"
    version: str = "0.1.0"
    description: str = "MCP server skeleton"

    @abstractmethod
    def available_tools(self) -> list[MCPToolDefinition]:
        """Return the list of tool definitions this server provides."""
        ...

    @abstractmethod
    def _create_tool(self, tool_name: str) -> MCPTool | None:
        """Factory: given a tool name, return the corresponding MCPTool instance."""
        ...

    async def initialize(self) -> None:
        """Called once when the server is registered.  Override to
        perform connection setup or credential validation."""
        pass

    async def shutdown(self) -> None:
        """Called when the application is shutting down.  Override to
        release resources (HTTP clients, DB connections, …)."""
        pass


class MCPTool(ABC):
    """Adapts a declarative tool definition to the existing ToolBase
    interface so the MCP layer plugs into the current ToolRegistry
    without changes to agent code.

    Each concrete tool subclass must implement _execute_impl() with
    the actual integration logic.
    """

    server: MCPServerBase

    @property
    @abstractmethod
    def tool_definition(self) -> MCPToolDefinition:
        """Return the declarative definition for this tool."""
        ...

    @property
    def name(self) -> str:
        return self.tool_definition.name

    @property
    def description(self) -> str:
        return self.tool_definition.description

    @property
    def parameters(self) -> dict[str, Any]:
        return self.tool_definition.parameters

    @abstractmethod
    async def _execute_impl(self, **kwargs: Any) -> Any:
        """Subclass implements actual tool logic here."""
        ...

    async def execute(self, **kwargs: Any) -> Any:
        """Execute the tool and return structured output."""
        logger.debug("Executing MCP tool %s with %s", self.name, kwargs)
        result = await self._execute_impl(**kwargs)
        return {"success": True, "data": result}
