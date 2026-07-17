"""Agent runtime event abstraction and SSE serialization."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum


class EventType(str, Enum):
    STAGE_START = "stage_start"
    STAGE_COMPLETE = "stage_complete"
    STAGE_FAILED = "stage_failed"
    RUN_COMPLETE = "run_complete"
    RUN_FAILED = "run_failed"
    RUN_CANCELLED = "run_cancelled"
    HEARTBEAT = "heartbeat"


@dataclass
class AgentEvent:
    type: EventType
    run_id: uuid.UUID
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    stage_name: str | None = None
    status: str | None = None
    output_summary: dict | None = None
    error_message: str | None = None
    duration_ms: int | None = None
    extra: dict = field(default_factory=dict)

    def to_sse(self) -> str:
        """Serialize to SSE format: event + data lines."""
        payload = {
            "type": self.type.value,
            "run_id": str(self.run_id),
            "timestamp": self.timestamp.isoformat(),
        }
        if self.stage_name is not None:
            payload["stage_name"] = self.stage_name
        if self.status is not None:
            payload["status"] = self.status
        if self.output_summary is not None:
            payload["output_summary"] = self.output_summary
        if self.error_message is not None:
            payload["error_message"] = self.error_message
        if self.duration_ms is not None:
            payload["duration_ms"] = self.duration_ms
        if self.extra:
            payload["extra"] = self.extra

        data = json.dumps(payload)
        return f"event: {self.type.value}\ndata: {data}\n\n"

    @classmethod
    def stage_start(cls, run_id: uuid.UUID, stage_name: str) -> AgentEvent:
        return cls(type=EventType.STAGE_START, run_id=run_id, stage_name=stage_name, status="executing")

    @classmethod
    def stage_complete(cls, run_id: uuid.UUID, stage_name: str, duration_ms: int | None = None, output_summary: dict | None = None) -> AgentEvent:
        return cls(
            type=EventType.STAGE_COMPLETE,
            run_id=run_id,
            stage_name=stage_name,
            status="completed",
            duration_ms=duration_ms,
            output_summary=output_summary,
        )

    @classmethod
    def stage_failed(cls, run_id: uuid.UUID, stage_name: str, error: str) -> AgentEvent:
        return cls(
            type=EventType.STAGE_FAILED,
            run_id=run_id,
            stage_name=stage_name,
            status="failed",
            error_message=error,
        )

    @classmethod
    def run_complete(cls, run_id: uuid.UUID, total_duration_ms: int | None = None) -> AgentEvent:
        return cls(
            type=EventType.RUN_COMPLETE,
            run_id=run_id,
            status="completed",
            duration_ms=total_duration_ms,
        )

    @classmethod
    def run_failed(cls, run_id: uuid.UUID, error: str) -> AgentEvent:
        return cls(type=EventType.RUN_FAILED, run_id=run_id, status="failed", error_message=error)

    @classmethod
    def run_cancelled(cls, run_id: uuid.UUID) -> AgentEvent:
        return cls(type=EventType.RUN_CANCELLED, run_id=run_id, status="cancelled")

    @classmethod
    def heartbeat(cls, run_id: uuid.UUID) -> AgentEvent:
        return cls(type=EventType.HEARTBEAT, run_id=run_id)


async def event_to_sse_generator(run_id: str, get_events):
    """Yield SSE-formatted strings from an async iterable of AgentEvent objects.

    Args:
        run_id: The run ID (used for logging only; events carry their own).
        get_events: Async iterable yielding AgentEvent instances.
    """
    try:
        async for event in get_events:
            yield event.to_sse()
    except GeneratorExit:
        pass
    except Exception as exc:
        error_event = AgentEvent(
            type=EventType.RUN_FAILED,
            run_id=uuid.UUID(run_id),
            error_message=str(exc),
        )
        yield error_event.to_sse()
