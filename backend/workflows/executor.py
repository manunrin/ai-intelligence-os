"""Executor protocol and synchronous execution implementation."""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Type alias for pipeline factory: callable that returns a compiled LangGraph app
PipelineFactory = Callable[[], Any]


@dataclass
class RunResult:
    status: str
    run_id: uuid.UUID
    output_payload: dict | None = None
    error_message: str | None = None
    duration_ms: int | None = None
    finished_at: datetime | None = None
    stages: list[dict[str, Any]] = field(default_factory=list)


class Executor:
    """Abstract protocol for agent run execution.

    Implementations:
    - SyncExecutor: runs in background thread via asyncio (F.3 default)
    - RQExecutor: enqueues job to RQ queue (future)
    - CeleryExecutor: enqueues task to Celery (future)
    """

    async def execute(
        self,
        run_id: uuid.UUID,
        factory: PipelineFactory,
        state: dict[str, Any],
        user_id: uuid.UUID,
        session: AsyncSession,
        cancellation_token: dict[uuid.UUID, bool],
    ) -> RunResult:
        raise NotImplementedError


class SyncExecutor(Executor):
    """Runs agent execution in a background thread via run_in_executor."""

    async def execute(
        self,
        run_id: uuid.UUID,
        factory: PipelineFactory,
        state: dict[str, Any],
        user_id: uuid.UUID,
        session: AsyncSession,
        cancellation_token: dict[uuid.UUID, bool],
    ) -> RunResult:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: _sync_execute_impl(run_id, factory, state, user_id, session, cancellation_token),
        )


def _utcnow():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


def _sync_execute_impl(
    run_id: uuid.UUID,
    factory: PipelineFactory,
    state: dict[str, Any],
    user_id: uuid.UUID,
    session: AsyncSession,
    cancellation_token: dict[uuid.UUID, bool],
) -> RunResult:
    """Synchronous execution of a compiled LangGraph app.

    Uses .astream() because graph nodes are async coroutines.
    Runs the event loop inline so cancellation works between steps.
    """
    start_time = datetime.now(timezone.utc)
    try:
        graph_app = factory()

        # Run the async stream in an inline event loop
        _loop = asyncio.new_event_loop()
        try:
            chunks = _loop.run_until_complete(
                _stream_with_cancel(graph_app, state, run_id, cancellation_token)
            )
        finally:
            _loop.close()

        # Combine all chunks into final output
        output = {}
        for chunk in chunks:
            if isinstance(chunk, dict):
                output.update(chunk)

        duration = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        return RunResult(
            status="completed",
            run_id=run_id,
            output_payload=output,
            duration_ms=duration,
            finished_at=datetime.now(timezone.utc),
        )

    except Exception as exc:
        duration = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        logger.exception("Run %s failed: %s", str(run_id), exc)
        return RunResult(
            status="failed",
            run_id=run_id,
            error_message=str(exc),
            duration_ms=duration,
            finished_at=datetime.now(timezone.utc),
        )


async def _stream_with_cancel(graph_app, state, run_id, cancellation_token):
    """Stream from an async graph, checking cancellation between steps."""
    chunks = []
    async for chunk in graph_app.astream(state):
        if cancellation_token.get(run_id, False):
            return chunks  # partial result
        if chunk is not None:
            chunks.append(chunk)
    return chunks
