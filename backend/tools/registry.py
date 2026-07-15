"""Registry for tool discovery and lookup."""

from __future__ import annotations

import logging
from typing import Any

from .base import ToolBase

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Central registry for all available tools.

    Agents query the registry to discover and invoke tools at runtime.
    Supports both local tools (ToolBase) and MCP tools registered via
    an optional MCPRegistry instance.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolBase] = {}
        self._mcp_registry: Any = None  # MCPRegistry | None

    def register(self, tool: ToolBase) -> None:
        """Register a local tool instance."""
        self._tools[tool.name] = tool

    def set_mcp_registry(self, mcp_registry: Any) -> None:
        """Attach an MCPRegistry so this registry can resolve MCP tools."""
        self._mcp_registry = mcp_registry
        logger.info("ToolRegistry wired to MCP registry (%d servers)", len(mcp_registry.list_servers()))

    def get_tool(self, name: str) -> ToolBase | Any | None:
        """Lookup a tool by name.

        Checks local tools first, then falls back to the MCP registry
        using the same dotted name format (e.g. "notion.create_page").
        """
        if name in self._tools:
            return self._tools[name]
        if self._mcp_registry:
            return self._mcp_registry.get_tool(name)
        return None

    def list_all(self) -> dict[str, ToolBase]:
        """Return all registered local tools."""
        return dict(self._tools)

    def list_schemas(self) -> dict[str, dict[str, Any]]:
        """Return tool name -> parameter schema mapping for LLM prompting.

        Merges local tool schemas with MCP tool schemas.
        """
        schemas: dict[str, dict[str, Any]] = {
            name: tool.parameters for name, tool in self._tools.items()
        }
        if self._mcp_registry:
            schemas.update(self._mcp_registry.list_schemas())
        return schemas

    def list_mcp_tools(self) -> dict[str, Any]:
        """Return all registered MCP tools (if wired)."""
        if self._mcp_registry:
            return self._mcp_registry.list_tools()
        return {}
