"""Abstract base for all tools callable by agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    """Standardized tool execution result."""
    success: bool
    data: Any = None
    error: str | None = None


class ToolBase(ABC):
    """Base class for tools that agents can invoke.

    Every tool must declare:
    - name: unique identifier used by agent runtime
    - description: what this tool does (used in LLM prompts)
    - parameters: JSON Schema describing required/optional inputs

    Subclasses implement execute() with the actual logic.
    """

    name: str = "base_tool"
    description: str = "Base tool — no-op"
    parameters: dict[str, Any] = field(default_factory=dict)

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with provided arguments.

        Args:
            **kwargs: Parameters defined in self.parameters.

        Returns:
            ToolResult with success flag, data, and optional error.
        """
        try:
            result = await self._execute_impl(**kwargs)
            return ToolResult(success=True, data=result)
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))

    @abstractmethod
    async def _execute_impl(self, **kwargs: Any) -> Any:
        """Subclass implements actual tool logic here."""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
