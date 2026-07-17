"""Agent runtime service — orchestrates agent execution and lifecycle tracking.

This service does NOT reimplement agent execution logic. It:
- Creates run records and dispatches to pipeline factories
- Manages lifecycle state transitions (running → completed/failed/cancelled)
- Collects callback events and persists stage progress
- Provides cancellation coordination
- Exposes streaming/SSE interface

Actual agent work is delegated to existing LangGraph pipelines via the Executor protocol.
"""

from __future__ import annotations

import asyncio
import importlib
import logging
import uuid
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..repositories.agent_run_repository import AgentRunRepository
from ..repositories.agent_stage_progress_repository import AgentStageProgressRepository
from ..workflows.executor import Executor, PipelineFactory, RunResult, SyncExecutor

logger = logging.getLogger(__name__)


def _utcnow():
    return datetime.now(timezone.utc)


def _run_to_dict(run: Any) -> dict[str, Any]:
    """Convert ORM model to serializable dict."""
    return {
        "id": str(run.id),
        "agent_id": str(run.agent_id),
        "workflow_id": str(run.workflow_id) if run.workflow_id else None,
        "status": run.status,
        "stage": getattr(run, "stage", "initializing"),
        "input_payload": run.input_payload,
        "output_payload": run.output_payload,
        "error_message": run.error_message,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "duration_ms": run.duration_ms,
        "user_id": str(run.user_id) if run.user_id else None,
    }


# Pipeline type → factory function mapping
PIPELINE_MAP: dict[str, Any] = {
    "intelligence": "backend.workflows.daily_intelligence.compile_intelligence_graph",
    "autonomous": "backend.workflows.autonomous_intelligence.compile_autonomous_intelligence",
}


class AgentNotFoundError(Exception):
    pass


class AgentRunNotFoundError(Exception):
    pass


class AgentTimeoutError(Exception):
    pass


def _make_repo(session: AsyncSession):
    """Create repos bound to a specific session."""
    return AgentRunRepository(session), AgentStageProgressRepository(session)


class AgentRuntimeService:
    """Orchestrates agent run execution, lifecycle, and observability.

    Accepts either an AsyncSession (for request-bound usage) or a
    session factory callable (for background execution).  When using
    an AsyncSession directly, a separate persistent session is created
    for the background task so DB writes survive the request lifecycle.
    """

    def __init__(
        self,
        session_or_factory: AsyncSession | Callable[[], AsyncSession],
        *,
        session_factory: Callable[[], AsyncSession] | None = None,
    ) -> None:
        if isinstance(session_or_factory, async_sessionmaker):
            # sessionmaker — use it for both request and bg tasks
            self._session_factory: Callable[[], AsyncSession] = lambda: session_or_factory()
            self._request_session: AsyncSession | None = session_or_factory()
        elif callable(session_or_factory):
            # Callable that returns a session
            self._session_factory = session_or_factory
            self._request_session = session_or_factory()
        else:
            # Direct AsyncSession (request-scoped) — for background tasks we need our own
            # session since the request-scoped one will be closed when the response sends.
            # The factory must be provided explicitly by the caller.
            self._request_session = session_or_factory
            if session_factory is not None:
                self._session_factory = session_factory
            else:
                raise ValueError(
                    "AgentRuntimeService requires a session_factory when "
                    "initialized with a direct AsyncSession"
                )
        self._executor: Executor = SyncExecutor()
        self._cancellation_tokens: dict[uuid.UUID, bool] = {}
        self._run_tasks: dict[uuid.UUID, asyncio.Task | None] = {}

    async def list_agent_runs(self, user_id: uuid.UUID, *, offset: int = 0, limit: int = 20) -> list[dict[str, Any]]:
        """Return paginated agent runs for the given user."""
        from ..database.models import AgentRun
        from sqlalchemy import select, func

        stmt = (
            select(AgentRun)
            .where(AgentRun.user_id == user_id)
            .order_by(AgentRun.started_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._request_session.execute(stmt)
        runs = result.scalars().all()
        return [_run_to_dict(r) for r in runs]

    async def submit(
        self,
        agent_type: str,
        input_payload: dict[str, Any],
        user_id: uuid.UUID,
        *,
        timeout_seconds: int = 300,
    ) -> dict[str, Any]:
        """Submit an agent run for asynchronous execution.

        Creates an AgentRun record, resolves the pipeline factory,
        dispatches to the executor, and returns immediately.
        """
        if agent_type not in PIPELINE_MAP:
            raise ValueError(
                f"Unknown agent_type '{agent_type}'. Valid types: {list(PIPELINE_MAP.keys())}"
            )

        run_id = uuid.uuid4()
        now = _utcnow()

        repo, _ = _make_repo(self._request_session)

        # Resolve a real agent_id from the agents table (FK constraint)
        from ..database.models import Agent
        from sqlalchemy import select
        stmt = select(Agent.id).limit(1)
        result = await self._request_session.execute(stmt)
        agent_id = result.scalar_one_or_none()
        if agent_id is None:
            agent_id = uuid.uuid4()
            new_agent = Agent(id=agent_id, name="default", display_name="Default Agent",
                              description="Synthetic agent for runtime execution",
                              graph_def={}, version="1.0.0", enabled=True)
            self._request_session.add(new_agent)
            await self._request_session.flush()

        run = await repo.create(
            id=run_id,
            agent_id=agent_id,
            workflow_id=None,
            status="running",
            stage="initializing",
            input_payload=input_payload,
            output_payload=None,
            error_message=None,
            started_at=now,
            finished_at=None,
            duration_ms=None,
            user_id=user_id,
        )

        logger.info("Agent run submitted: type=%s run=%s", agent_type, str(run_id))
        await self._request_session.commit()

        # Publish audit event for the run creation
        try:
            from ..events.event import AuditAction, AuditLogEvent
            if hasattr(self, '_event_publisher') and self._event_publisher is not None:
                await self._event_publisher.publish(AuditLogEvent(
                    action=AuditAction.AGENT_RUN,
                    resource_type="agent_run",
                    metadata={"run_id": str(run_id), "agent_type": agent_type},
                    user_id=user_id,
                ))
        except Exception:
            logger.warning("Failed to publish audit event for run %s", str(run_id), exc_info=True)

        # Dispatch to executor in background — uses its own session
        bg_task = asyncio.create_task(
            self._execute_run(
                run_id=run_id,
                pipeline_type=agent_type,
                state=input_payload,
                timeout_seconds=timeout_seconds,
            )
        )
        self._run_tasks[run_id] = bg_task

        return _run_to_dict(run)

    async def _execute_run(
        self,
        run_id: uuid.UUID,
        pipeline_type: str,
        state: dict[str, Any],
        timeout_seconds: int,
    ) -> None:
        """Execute a run in the background with its own DB session."""
        from ..workflows.graph.callbacks import AgentRuntimeCallback

        # Create a dedicated session for this background task
        session = self._session_factory()  # session_factory() returns a session
        callback = AgentRuntimeCallback(run_id)
        self._cancellation_tokens[run_id] = False

        repo, stage_repo = _make_repo(session)

        try:
            module_path = PIPELINE_MAP[pipeline_type]
            mod_path, func_name = module_path.rsplit(".", 1)
            mod = importlib.import_module(mod_path)
            graph_builder = getattr(mod, func_name)

            def factory():
                return graph_builder()

            result = await asyncio.wait_for(
                self._executor.execute(
                    run_id=run_id,
                    factory=factory,
                    state=state,
                    user_id=state.get("user_id") if isinstance(state.get("user_id"), uuid.UUID) else None or run_id,
                    session=session,
                    cancellation_token=self._cancellation_tokens,
                ),
                timeout=timeout_seconds,
            )

            if result.status == "cancelled":
                await self._finalize_cancelled(repo, run_id, result)
            elif result.status in ("completed", "failed"):
                await self._finalize_completed(repo, stage_repo, run_id, result, callback.events)
            else:
                # Any other status (e.g., timeout from executor itself)
                logger.warning("Run %s ended with unexpected status: %s", str(run_id), result.status)

        except asyncio.TimeoutError:
            logger.warning("Run %s exceeded %ds timeout", str(run_id), timeout_seconds)
            await self._finalize_failed(repo, run_id, RunResult(
                status="timeout",
                run_id=run_id,
                error_message=f"Run exceeded {timeout_seconds}s timeout",
            ))

        except Exception as exc:
            logger.exception("Unexpected error in run %s", str(run_id))
            await self._finalize_failed(repo, run_id, RunResult(
                status="failed",
                run_id=run_id,
                error_message=str(exc),
            ))

        finally:
            self._cancellation_tokens.pop(run_id, None)
            self._run_tasks.pop(run_id, None)
            await session.close()

    async def _finalize_completed(
        self,
        repo: AgentRunRepository,
        stage_repo: AgentStageProgressRepository,
        run_id: uuid.UUID,
        result: RunResult,
        events: list[Any],
    ) -> None:
        now = _utcnow()
        await repo.update(
            run_id,
            status=result.status,
            stage="complete",
            output_payload=result.output_payload,
            error_message=result.error_message,
            finished_at=now,
            duration_ms=result.duration_ms,
        )
        await stage_repo.session.commit()
        await self._persist_stages(stage_repo, run_id, events)
        logger.info("Run %s completed in %d ms", str(run_id), result.duration_ms or 0)

    async def _finalize_failed(self, repo: AgentRunRepository, run_id: uuid.UUID, result: RunResult) -> None:
        now = _utcnow()
        await repo.update(
            run_id,
            status=result.status,
            stage="failed",
            output_payload=None,
            error_message=result.error_message,
            finished_at=now,
            duration_ms=result.duration_ms,
        )
        logger.warning("Run %s failed: %s", str(run_id), result.error_message)

    async def _finalize_cancelled(self, repo: AgentRunRepository, run_id: uuid.UUID, result: RunResult) -> None:
        now = _utcnow()
        await repo.update(
            run_id,
            status="cancelled",
            stage="cancelled",
            output_payload=result.output_payload,
            finished_at=now,
            duration_ms=result.duration_ms,
        )
        logger.info("Run %s cancelled after %d ms", str(run_id), result.duration_ms or 0)

    async def _persist_stages(self, stage_repo: AgentStageProgressRepository, run_id: uuid.UUID, events: list[Any]) -> None:
        stages_by_name: dict[str, dict[str, Any]] = {}
        order_counter = 0

        for event in events:
            name = event.node_name
            if name.startswith("tool:"):
                continue
            if name not in stages_by_name:
                stages_by_name[name] = {
                    "stage_name": name,
                    "status": "pending",
                    "output_summary": None,
                    "error_message": None,
                }
                order_counter += 1
            info = stages_by_name[name]
            if event.phase == "start":
                info["status"] = "executing"
            elif event.phase == "end":
                info["status"] = "completed"
                info["output_summary"] = event.outputs
            elif event.phase == "error":
                info["status"] = "failed"
                info["error_message"] = event.error_message

        for order, (name, info) in enumerate(sorted(stages_by_name.items(), key=lambda x: x[0])):
            await stage_repo.create_stage(
                agent_run_id=run_id,
                stage_name=name,
                stage_order=order,
                status=info["status"],
                input_summary={},
            )
            if info["status"] != "executing":
                await stage_repo.update_stage(
                    run_id, name,
                    status=info["status"],
                    output_summary=info["output_summary"],
                    error_message=info["error_message"],
                )
        await stage_repo.session.commit()

    async def get_run(self, run_id: str) -> dict[str, Any] | None:
        run_uuid = uuid.UUID(run_id)
        repo, stage_repo = _make_repo(self._request_session)
        run = await repo.get_by_id(run_uuid)
        if run is None:
            return None

        stages = await stage_repo.get_by_run_id(run_uuid)
        stage_dicts = [
            {
                "stage_name": s.stage_name,
                "stage_order": s.stage_order,
                "status": s.status,
                "input_summary": s.input_summary,
                "output_summary": s.output_summary,
                "error_message": s.error_message,
                "duration_ms": s.duration_ms,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "finished_at": s.finished_at.isoformat() if s.finished_at else None,
            }
            for s in stages
        ]

        result = _run_to_dict(run)
        result["stages"] = stage_dicts
        result["stream_url"] = f"/api/v1/agents/runs/{run_id}/stream"
        return result

    async def cancel_run(self, run_id: str, user_id: uuid.UUID) -> dict[str, Any]:
        run_uuid = uuid.UUID(run_id)
        repo, _ = _make_repo(self._request_session)
        run = await repo.get_by_id(run_uuid)
        if run is None:
            raise AgentRunNotFoundError(run_id)
        if run.status not in ("running", "cancelling"):
            raise ValueError(f"Cannot cancel run with status '{run.status}'")

        await repo.update(run_uuid, status="cancelling", stage="cancelling")
        self._cancellation_tokens[run_uuid] = True

        task = self._run_tasks.get(run_uuid)
        if task is not None:
            try:
                await asyncio.wait_for(task, timeout=30)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass

        await repo.update(
            run_uuid,
            status="cancelled",
            stage="cancelled",
            finished_at=_utcnow(),
        )
        await self._request_session.commit()

        logger.info("Run %s cancelled", str(run_id))
        return {"cancelled": True, "run_id": str(run_uuid)}

    async def stream_events(self, run_id: str):
        from ..events.agent_event import AgentEvent, EventType

        run_uuid = uuid.UUID(run_id)
        repo, _ = _make_repo(self._request_session)
        yield AgentEvent(type=EventType.RUN_COMPLETE, run_id=run_uuid, status="connected").to_sse()

        last_status: str | None = None
        while True:
            try:
                run = await repo.get_by_id(run_uuid)
                if run is None:
                    break
                current_status = run.status
                if current_status in ("completed", "failed", "cancelled") and current_status != last_status:
                    event_type = {
                        "completed": EventType.RUN_COMPLETE,
                        "failed": EventType.RUN_FAILED,
                        "cancelled": EventType.RUN_CANCELLED,
                    }.get(current_status, EventType.RUN_COMPLETE)
                    yield AgentEvent(type=event_type, run_id=run_uuid, status=current_status).to_sse()
                    break
                last_status = current_status
                await asyncio.sleep(2)
            except Exception:
                break

        yield AgentEvent(type=EventType.HEARTBEAT, run_id=run_uuid).to_sse()

    @property
    def available_pipelines(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "intelligence",
                "name": "Daily Intelligence",
                "description": "Research → Analyze → Translate",
                "nodes": 3,
            },
            {
                "type": "autonomous",
                "name": "Autonomous Intelligence",
                "description": "Full pipeline with knowledge extraction and project planning",
                "nodes": 6,
            },
        ]
