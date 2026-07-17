"""LangGraph callback handler for agent runtime tracking.

Emits stage-level events that the AgentRuntimeService collects
and persists to the database. The callback does NOT write to the DB
directly — it only appends to an in-memory event buffer.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger(__name__)


@dataclass
class StageEvent:
    """A stage-level event emitted by the callback."""
    run_id: uuid.UUID
    node_name: str
    phase: str  # "start" | "end" | "error"
    error_message: str | None = None
    outputs: dict | None = None


class AgentRuntimeCallback(BaseCallbackHandler):
    """Collects LangGraph node execution events into a shared buffer.

    The AgentRuntimeService reads this buffer after invocation and
    persists events to the database.
    """

    def __init__(self, run_id: uuid.UUID) -> None:
        self.run_id = run_id
        self.events: list[StageEvent] = []
        self._current_node: str | None = None

    @property
    def ignore_llm(self) -> bool:
        return True

    @property
    def ignore_retriever(self) -> bool:
        return True

    @property
    def ignore_agent(self) -> bool:
        return True

    def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: Any,
        *,
        run_id: uuid.UUID,
        parent_run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        node_name = serialized.get("name", "unknown")
        if not isinstance(node_name, str):
            node_name = str(node_name)
        self._current_node = node_name
        self.events.append(StageEvent(
            run_id=self.run_id,
            node_name=node_name,
            phase="start",
        ))

    def on_chain_end(
        self,
        outputs: Any,
        *,
        run_id: uuid.UUID,
        parent_run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        if self._current_node is not None:
            out_dict = outputs if isinstance(outputs, dict) else {"_raw": str(outputs)[:500]}
            self.events.append(StageEvent(
                run_id=self.run_id,
                node_name=self._current_node,
                phase="end",
                outputs=out_dict,
            ))
            self._current_node = None

    def on_chain_error(
        self,
        error: Exception,
        *,
        run_id: uuid.UUID,
        parent_run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        if self._current_node is not None:
            self.events.append(StageEvent(
                run_id=self.run_id,
                node_name=self._current_node,
                phase="error",
                error_message=str(error),
            ))
            self._current_node = None

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input: Any,
        *,
        run_id: uuid.UUID,
        parent_run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        tool_name = serialized.get("name", "unknown")
        if not isinstance(tool_name, str):
            tool_name = str(tool_name)
        self.events.append(StageEvent(
            run_id=self.run_id,
            node_name=f"tool:{tool_name}",
            phase="start",
        ))

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: uuid.UUID,
        parent_run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        pass  # Tool events are nested under chain events

    def on_tool_error(
        self,
        error: Exception,
        *,
        run_id: uuid.UUID,
        parent_run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        pass
