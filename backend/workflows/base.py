"""Abstract base for workflow orchestration."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from ..agents.base import AgentBase


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowContext:
    """Shared state passed through a workflow execution chain."""
    run_id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: WorkflowStatus = WorkflowStatus.PENDING
    variables: dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    error: str | None = None


class WorkflowBase(ABC):
    """Base class for multi-agent workflow definitions.

    A workflow chains multiple agents together, passing output from one
    as input to the next. Subclasses define:
    - name: workflow identifier
    - description: human-readable purpose
    - agents(): list of AgentBase instances in this workflow
    - execute(): orchestration logic

    The base class provides:
    - context tracking (run_id, status, shared variables)
    - standardized lifecycle
    """

    name: str = "base_workflow"
    description: str = "Base workflow — no-op"

    def __init__(self, **kwargs: Any) -> None:
        self._context = WorkflowContext()
        self._kwargs = kwargs

    @property
    def context(self) -> WorkflowContext:
        return self._context

    @abstractmethod
    def get_agents(self) -> list[AgentBase]:
        """Return the ordered list of agents in this workflow."""

    async def execute(self, initial_input: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run the full workflow pipeline.

        Args:
            initial_input: Input fed into the first agent.

        Returns:
            Dict with:
              - success: bool
              - output: final agent output or None
              - context: WorkflowContext snapshot
        """
        if initial_input:
            self._context.variables.update(initial_input)
        self._context.status = WorkflowStatus.RUNNING

        agents = self.get_agents()
        current_input: dict[str, Any] = initial_input or {}

        try:
            for agent in agents:
                result = await agent.execute(current_input)
                if not result["success"]:
                    self._context.status = WorkflowStatus.FAILED
                    self._context.error = f"Agent '{agent.name}' failed: {result['metadata'].get('error')}"
                    return {
                        "success": False,
                        "output": None,
                        "context": self._context_as_dict(),
                    }
                current_input = result["output"] or {}

            self._context.status = WorkflowStatus.COMPLETED
            self._context.finished_at = datetime.now(timezone.utc)
            return {
                "success": True,
                "output": current_input,
                "context": self._context_as_dict(),
            }
        except Exception as exc:
            self._context.status = WorkflowStatus.FAILED
            self._context.error = str(exc)
            return {
                "success": False,
                "output": None,
                "context": self._context_as_dict(),
            }

    def _context_as_dict(self) -> dict[str, Any]:
        return {
            "run_id": str(self._context.run_id),
            "status": self._context.status.value,
            "variables": self._context.variables,
            "started_at": self._context.started_at.isoformat(),
            "finished_at": self._context.finished_at.isoformat() if self._context.finished_at else None,
            "error": self._context.error,
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
