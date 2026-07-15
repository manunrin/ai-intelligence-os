"""Abstract base for all AI agents."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class AgentState(str, Enum):
    """Agent execution state."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


@dataclass
class AgentMetadata:
    """Runtime metadata for an agent instance."""
    run_id: uuid.UUID = field(default_factory=uuid.uuid4)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    state: AgentState = AgentState.IDLE
    error: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class AgentBase(ABC):
    """Base class for all agents in the system.

    Subclasses must implement:
    - name: unique identifier
    - version: semantic version string
    - description: human-readable purpose
    - execute(): core agent logic

    The base class provides:
    - metadata tracking (run_id, state, timing)
    - lifecycle management
    - standardized input/output contracts
    """

    # Override in subclasses
    name: str = "base_agent"
    version: str = "0.1.0"
    description: str = "Base agent — no-op"

    def __init__(self, **kwargs: Any) -> None:
        self._metadata = AgentMetadata()
        self._kwargs = kwargs

    @property
    def metadata(self) -> AgentMetadata:
        return self._metadata

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent with given input and return structured output.

        Args:
            input_data: Arbitrary context the agent needs.

        Returns:
            Dict with keys:
              - success: bool
              - output: agent-specific result payload
              - metadata: AgentMetadata snapshot
        """
        self._metadata.state = AgentState.RUNNING
        try:
            result = await self._execute_impl(input_data)
            self._metadata.state = AgentState.COMPLETED
            return {
                "success": True,
                "output": result,
                "metadata": self._metadata_as_dict(),
            }
        except Exception as exc:
            self._metadata.state = AgentState.FAILED
            self._metadata.error = str(exc)
            return {
                "success": False,
                "output": None,
                "metadata": self._metadata_as_dict(),
            }

    @abstractmethod
    async def _execute_impl(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Subclass implements actual agent logic here."""

    def _metadata_as_dict(self) -> dict[str, Any]:
        return {
            "run_id": str(self._metadata.run_id),
            "started_at": self._metadata.started_at.isoformat(),
            "state": self._metadata.state.value,
            "error": self._metadata.error,
            "extra": self._metadata.extra,
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r} version={self.version!r}>"
