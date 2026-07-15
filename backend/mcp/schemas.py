"""MCP schemas shared across servers and clients."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server instance."""

    name: str
    version: str = "0.1.0"
    description: str = ""
    enabled: bool = True
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPToolDefinition:
    """Declarative tool definition used by MCP servers."""

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    returns: dict[str, Any] = field(default_factory=dict)
