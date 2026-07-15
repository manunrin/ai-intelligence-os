"""Registry for tool discovery and lookup."""

from .base import ToolBase


class ToolRegistry:
    """Central registry for all available tools.

    Agents query the registry to discover and invoke tools at runtime.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolBase] = {}

    def register(self, tool: ToolBase) -> None:
        """Register a tool instance."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolBase | None:
        """Lookup a tool by name."""
        return self._tools.get(name)

    def list_all(self) -> dict[str, ToolBase]:
        """Return all registered tools."""
        return dict(self._tools)

    def list_schemas(self) -> dict[str, dict[str, Any]]:
        """Return tool name -> parameter schema mapping for LLM prompting."""
        return {name: tool.parameters for name, tool in self._tools.items()}
