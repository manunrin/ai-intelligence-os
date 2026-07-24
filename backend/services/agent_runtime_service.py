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
import logging
import uuid
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..repositories.agent_run_repository import AgentRunRepository
from ..repositories.agent_stage_progress_repository import AgentStageProgressRepository
from ..services.evaluation.repository import AgentEvaluationRepository
from ..workflows.executor import Executor, PipelineFactory, RunResult, SyncExecutor
from ..workflows.retry_executor import RetryExecutor
from ..workflows.registry import PIPELINE_REGISTRY
from ..context_vars import agent_run_id as _agent_ctx, trace_span as _trace_ctx
from ..metrics import counter, histogram

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
        "retry_count": getattr(run, "retry_count", 0),
        "recovered_at": run.recovered_at.isoformat() if getattr(run, "recovered_at", None) else None,
        "scheduled_job_id": str(run.scheduled_job_id) if getattr(run, "scheduled_job_id", None) else None,
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


def _make_all_repos(session: AsyncSession):
    """Create all repos (including evaluation) bound to a session."""
    ar, sp = _make_repo(session)
    return ar, sp, AgentEvaluationRepository(session)


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
        checkpointer: Any = None,
        evaluation_service: Any = None,  # EvaluationService — injected at runtime
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
        self._executor: Executor = RetryExecutor(
            SyncExecutor(),
            max_attempts=getattr(self, '_retry_max_attempts', 3),
            base_delay_ms=getattr(self, '_retry_base_delay_ms', 1000),
            max_delay_ms=getattr(self, '_retry_max_delay_ms', 30000),
        )
        self._cancellation_tokens: dict[uuid.UUID, bool] = {}
        self._run_tasks: dict[uuid.UUID, asyncio.Task | None] = {}
        self._checkpointer: Any = checkpointer
        self._scheduled_job_id: str | None = None
        self._evaluation_service = evaluation_service

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

        # Batch-fetch evaluation scores for these runs
        run_ids = [r.id for r in runs]
        eval_map: dict[uuid.UUID, float | None] = {}
        conf_map: dict[uuid.UUID, float | None] = {}
        if run_ids:
            eval_repo = AgentEvaluationRepository(self._request_session)
            evaluations = await eval_repo.get_by_run_ids(run_ids)
            for ev in evaluations:
                eval_map[ev.agent_run_id] = ev.score
                conf_map[ev.agent_run_id] = ev.evaluator_confidence

        output = []
        for r in runs:
            d = _run_to_dict(r)
            d["evaluation_score"] = eval_map.get(r.id)
            d["evaluation_confidence"] = conf_map.get(r.id)
            output.append(d)
        return output

    async def submit(
        self,
        agent_type: str,
        input_payload: dict[str, Any],
        user_id: uuid.UUID,
        *,
        timeout_seconds: int = 300,
        scheduled_job_id: str | None = None,
    ) -> dict[str, Any]:
        """Submit an agent run for asynchronous execution.

        Creates an AgentRun record, resolves the pipeline factory,
        dispatches to the executor, and returns immediately.
        """
        if agent_type not in PIPELINE_REGISTRY:
            raise ValueError(
                f"Unknown agent_type '{agent_type}'. Valid types: {list(PIPELINE_REGISTRY.keys())}"
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
            thread_id=f"agent-run-{run_id}",
            scheduled_job_id=uuid.UUID(scheduled_job_id) if scheduled_job_id else None,
        )

        logger.info("Agent run submitted: type=%s run=%s", agent_type, str(run_id))
        await self._request_session.commit()

        # Record agent submission metric
        trigger = "cron" if scheduled_job_id else "user"
        counter("agent_runs_total", labels={"agent_type": agent_type, "status": "submitted", "trigger": trigger})

        # Set agent run context for downstream log correlation
        _agent_ctx.set(str(run_id))

        # Store scheduled_job_id for completion callbacks
        self._scheduled_job_id = scheduled_job_id

        # Publish audit event for the run creation
        try:
            from ..context_vars import ip_address as _ip_ctx, user_agent as _ua_ctx
            if hasattr(self, '_event_publisher') and self._event_publisher is not None:
                await self._event_publisher.publish(AuditLogEvent(
                    action=AuditAction.AGENT_RUN,
                    resource_type="agent_run",
                    metadata={"run_id": str(run_id), "agent_type": agent_type},
                    user_id=user_id,
                    ip_address=_ip_ctx.get(),
                    user_agent=_ua_ctx.get(),
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
                thread_id=f"agent-run-{run_id}",
                checkpointer=self._checkpointer,
                scheduled_job_id=self._scheduled_job_id,
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
        thread_id: str | None = None,
        checkpointer: Any = None,
        scheduled_job_id: str | None = None,
    ) -> None:
        """Execute a run in the background with its own DB session."""
        from ..trace import start_span
        from ..workflows.graph.callbacks import AgentRuntimeCallback

        # Create a dedicated session for this background task
        session = self._session_factory()  # session_factory() returns a session
        callback = AgentRuntimeCallback(run_id)
        self._cancellation_tokens[run_id] = False

        repo, stage_repo = _make_repo(session)

        # Start agent run span — inherits parent HTTP span from context vars
        with start_span(f"agent_run.{pipeline_type}", attributes={
            "agent.run.id": str(run_id),
            "agent.type": pipeline_type,
        }) as run_span:
            try:
                graph_builder = PIPELINE_REGISTRY[pipeline_type]

                def factory():
                    return graph_builder(checkpointer=checkpointer)

                result = await asyncio.wait_for(
                    self._executor.execute(
                        run_id=run_id,
                        factory=factory,
                        state=state,
                        user_id=state.get("user_id") if isinstance(state.get("user_id"), uuid.UUID) else None or run_id,
                        session=session,
                        cancellation_token=self._cancellation_tokens,
                        thread_id=thread_id,
                    ),
                    timeout=timeout_seconds,
                )

                # Record agent run completion metric with stage info
                trigger = "cron" if self._scheduled_job_id else "user"
                counter("agent_runs_total", labels={"agent_type": pipeline_type, "status": result.status, "trigger": trigger})
                if result.duration_ms is not None:
                    histogram("agent_run_duration_seconds", result.duration_ms / 1000.0, labels={"agent_type": pipeline_type, "status": result.status})

                if result.status == "cancelled":
                    await self._finalize_cancelled(repo, run_id, result)
                elif result.status == "completed":
                    eval_result = None
                    if (result.output_payload
                            and self._evaluation_service is not None):
                        eval_result = await self._evaluate_output(
                            pipeline_type, result.output_payload, state, session,
                        )
                    if eval_result is not None:
                        await self._persist_evaluation(session, run_id, eval_result, pipeline_type)
                        await session.commit()
                    await self._finalize_completed(
                        repo, stage_repo, run_id, result, callback.events,
                    )
                elif result.status == "failed":
                    await self._finalize_failed(
                        repo, run_id, result, retry_count=result.retry_count,
                    )
                else:
                    # Any other status (e.g., timeout from executor itself)
                    logger.warning("Run %s ended with unexpected status: %s", str(run_id), result.status)

            except asyncio.TimeoutError:
                logger.warning("Run %s exceeded %ds timeout", str(run_id), timeout_seconds)
                await self._finalize_failed(
                    repo, run_id, RunResult(
                        status="timeout",
                        run_id=run_id,
                        error_message=f"Run exceeded {timeout_seconds}s timeout",
                    ),
                    retry_count=0,
                )
                counter("agent_runs_total", labels={"agent_type": pipeline_type, "status": "timeout", "trigger": "cron" if self._scheduled_job_id else "user"})

            except Exception as exc:
                logger.exception("Unexpected error in run %s", str(run_id))
                await self._finalize_failed(
                    repo, run_id, RunResult(
                        status="failed",
                        run_id=run_id,
                        error_message=str(exc),
                    ),
                    retry_count=0,
                )
                counter("agent_runs_total", labels={"agent_type": pipeline_type, "status": "error", "trigger": "cron" if self._scheduled_job_id else "user"})

            finally:
                self._cancellation_tokens.pop(run_id, None)
                self._run_tasks.pop(run_id, None)
                _agent_ctx.set(None)
                await session.close()

    async def _evaluate_output(
        self,
        pipeline_type: str,
        output_payload: dict[str, Any],
        input_payload: dict[str, Any],
        session: AsyncSession | None = None,
    ) -> Any | None:
        """Run LLM-based quality evaluation on a completed run's output.

        Returns EvaluationResponse or None on any failure.
        Passes session for cache upsert.
        """
        if self._evaluation_service is None:
            logger.debug("EvaluationService not configured — skipping evaluation")
            return None
        try:
            return await self._evaluation_service.evaluate(
                pipeline_type=pipeline_type,
                output_payload=output_payload,
                input_payload=input_payload,
                session=session,
            )
        except Exception:
            logger.warning(
                "Evaluation failed for run %s pipeline %s",
                str(getattr(self, '_current_run_id', 'unknown')),
                pipeline_type,
                exc_info=True,
            )
            return None

    async def _persist_evaluation(
        self,
        session: AsyncSession,
        run_id: uuid.UUID,
        evaluation_result: Any,
        pipeline_type: str,
    ) -> None:
        """Persist an evaluation result to the agent_evaluations table."""
        from ..database.models import AgentEvaluation

        score = None
        criteria = None
        confidence = None
        if hasattr(evaluation_result, "score"):
            score = evaluation_result.score
        if hasattr(evaluation_result, "criteria"):
            criteria = evaluation_result.criteria
        if hasattr(evaluation_result, "evaluator_confidence"):
            confidence = evaluation_result.evaluator_confidence

        instance = AgentEvaluation(
            agent_run_id=run_id,
            pipeline_type=pipeline_type,
            score=float(score) if score is not None else None,
            criteria=criteria or {},
            evaluator_confidence=float(confidence) if confidence is not None else None,
        )
        session.add(instance)
        await session.flush()

        # Record score for Prometheus distribution tracking
        if score is not None:
            try:
                from ..metrics import record_evaluation_score
                record_evaluation_score(float(score))
            except Exception:
                pass  # metrics failure must never block evaluation
        logger.info(
            "Evaluation persisted for run %s (score=%s, confidence=%s)",
            str(run_id),
            score,
            getattr(evaluation_result, "evaluator_confidence", None),
        )

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
        await self._notify_scheduler_of_completion(
            self._scheduled_job_id, run_id, result.status, result.duration_ms,
        )

    async def _finalize_failed(
        self,
        repo: AgentRunRepository,
        run_id: uuid.UUID,
        result: RunResult,
        *,
        retry_count: int = 0,
    ) -> None:
        now = _utcnow()
        await repo.update(
            run_id,
            status=result.status,
            stage="failed",
            output_payload=None,
            error_message=result.error_message,
            finished_at=now,
            duration_ms=result.duration_ms,
            retry_count=retry_count,
        )
        logger.warning("Run %s failed: %s (retries: %d)", str(run_id), result.error_message, retry_count)
        await self._notify_scheduler_of_completion(
            self._scheduled_job_id, run_id, result.status, result.duration_ms,
        )

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
        await self._notify_scheduler_of_completion(
            self._scheduled_job_id, run_id, "cancelled", result.duration_ms,
        )

    async def _notify_scheduler_of_completion(
        self,
        scheduled_job_id: str | None,
        run_id: uuid.UUID,
        status: str,
        duration_ms: int | None,
    ) -> None:
        """Update ScheduledJob.last_run_* fields when a scheduled run completes.

        Uses direct DB query to avoid circular import with SchedulerService.
        """
        if not scheduled_job_id:
            return
        session = self._session_factory()
        try:
            from ..database.models import ScheduledJob
            stmt = select(ScheduledJob).where(ScheduledJob.id == uuid.UUID(scheduled_job_id))
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()
            if job is None:
                return
            job.last_run_id = run_id
            job.last_run_at = _utcnow()
            job.last_run_status = status
            job.last_run_duration_ms = duration_ms
            await session.commit()
        except Exception:
            logger.warning("Failed to update last_run for job %s", scheduled_job_id, exc_info=True)
        finally:
            await session.close()

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

        # Record stage-level histogram metrics
        for name in stages_by_name:
            counter("agent_stages_total", labels={"stage_name": name})

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

        # Include evaluation data if available
        eval_repo = AgentEvaluationRepository(self._request_session)
        eval_result = await eval_repo.get_by_run_id(run_uuid)
        if eval_result:
            result["evaluation_score"] = eval_result.score
            result["evaluation_criteria"] = eval_result.criteria
            result["evaluation_confidence"] = eval_result.evaluator_confidence
        else:
            result["evaluation_score"] = None
            result["evaluation_criteria"] = None
            result["evaluation_confidence"] = None

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

    async def resume(
        self,
        run_id: str,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Resume an interrupted agent run from its LangGraph checkpoint.

        Validates that the run is in 'interrupted' status, loads the
        persisted checkpoint state via checkpointer.aget(), updates the
        run record back to 'running', and dispatches execution using the
        same thread_id so LangGraph continues from the saved state.

        Args:
            run_id: UUID string of the interrupted run to resume.
            user_id: Authenticated user requesting the resume.

        Returns:
            Updated run dict with status 'running'.

        Raises:
            AgentRunNotFoundError: If run_id does not exist.
            ValueError: If run is not in 'interrupted' status.
        """
        run_uuid = uuid.UUID(run_id)
        repo, _ = _make_repo(self._request_session)

        run = await repo.get_by_id(run_uuid)
        if run is None:
            raise AgentRunNotFoundError(run_id)
        if run.status != "interrupted":
            raise ValueError(
                f"Cannot resume run with status '{run.status}'. "
                "Only 'interrupted' runs can be resumed."
            )

        # Update run record back to running state
        now = _utcnow()
        await repo.update(
            run_uuid,
            status="running",
            stage="resuming",
            started_at=now,
            finished_at=None,
            duration_ms=None,
        )
        await self._request_session.commit()

        # Load checkpoint state to pass as initial state
        thread_id = f"agent-run-{run_uuid}"
        config = {"configurable": {"thread_id": thread_id}}
        cp = self._checkpointer
        resume_state: dict[str, Any] | None = None

        if cp is not None:
            try:
                checkpoint_tuple = await cp.aget(config)
                if checkpoint_tuple is not None:
                    # Extract channel values from checkpoint state
                    checkpoint_data = checkpoint_tuple.checkpoint or {}
                    channel_values = checkpoint_data.get("channel_values", {})
                    if channel_values:
                        resume_state = dict(channel_values)
                        logger.info(
                            "Loaded checkpoint state for run %s (thread_id=%s)",
                            str(run_uuid),
                            thread_id,
                        )
            except Exception:
                logger.warning(
                    "Failed to load checkpoint for run %s; using original input_payload",
                    str(run_uuid),
                    exc_info=True,
                )

        # Fall back to original input_payload if no checkpoint state loaded
        if resume_state is None:
            resume_state = dict(run.input_payload or {})

        # Resolve pipeline type from input payload
        pipeline_type = (resume_state.get("_agent_type")
                         or (run.input_payload or {}).get("_agent_type")
                         or "intelligence")
        if pipeline_type not in PIPELINE_REGISTRY:
            pipeline_type = "intelligence"

        # Dispatch execution — same thread_id, checkpoint-aware
        bg_task = asyncio.create_task(
            self._execute_run(
                run_id=run_uuid,
                pipeline_type=pipeline_type,
                state=resume_state,
                timeout_seconds=300,
                thread_id=thread_id,
                checkpointer=self._checkpointer,
            )
        )
        self._run_tasks[run_uuid] = bg_task

        logger.info("Resumed run %s (thread_id=%s, pipeline=%s)", str(run_uuid), thread_id, pipeline_type)
        return _run_to_dict(run)

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

    async def _recover_stale_runs(
        self,
        checkpointer: Any | None = None,
        max_hours: int = 24,
    ) -> dict[str, int]:
        """Recover stale agent runs by checking LangGraph checkpoint existence.

        Scans for runs in 'running' or 'cancelling' state whose thread_id
        still has a valid checkpoint in LangGraph. If a checkpoint exists,
        the run is marked as 'recovered'; otherwise it is marked as 'failed'
        with a recovery error note.

        Args:
            checkpointer: Optional AsyncShallowPostgresSaver instance.
                Falls back to self._checkpointer if not provided.
            max_hours: Only consider runs started more than this many hours ago.

        Returns:
            Dict with counts: {'checked': N, 'recovered': N, 'marked_failed': N}
        """
        from sqlalchemy import select
        from ..database.models import AgentRun

        # Use provided checkpointer or fall back to stored one
        cp = checkpointer if checkpointer is not None else self._checkpointer

        if not cp:
            logger.warning("No checkpointer provided; skipping recovery scan")
            return {"checked": 0, "recovered": 0, "marked_failed": 0}

        repo, _ = _make_repo(self._request_session)

        # Query stale runs: status is running/cancelling AND started > max_hours ago
        cutoff = _utcnow() - timedelta(hours=max_hours)
        stmt = (
            select(AgentRun)
            .where(
                AgentRun.status.in_(["running", "cancelling"]),
                AgentRun.started_at < cutoff,
                AgentRun.thread_id.isnot(None),
            )
            .order_by(AgentRun.started_at.asc())
        )
        result = await self._request_session.execute(stmt)
        stale_runs = list(result.scalars().all())

        if not stale_runs:
            logger.info("No stale runs found within %dh window", max_hours)
            return {"checked": 0, "recovered": 0, "marked_failed": 0}

        logger.info(
            "Recovery scan: found %d stale runs (started > %dh ago)",
            len(stale_runs),
            max_hours,
        )

        recovered_count = 0
        failed_count = 0

        for run in stale_runs:
            thread_id = run.thread_id
            if not thread_id:
                continue

            # Check if checkpoint exists for this thread_id
            config = {"configurable": {"thread_id": thread_id}}
            try:
                checkpoint_tuple = await cp.aget_tuple(config)
            except Exception as exc:
                logger.error(
                    "Checkpoint lookup failed for thread_id=%s: %s",
                    thread_id,
                    exc,
                )
                # Treat lookup failure as no checkpoint → mark failed
                await repo.update(
                    run.id,
                    status="failed",
                    stage="recovery_failed",
                    error_message=f"Recovery: checkpoint lookup failed: {exc}",
                    finished_at=_utcnow(),
                )
                await self._request_session.commit()
                failed_count += 1
                continue

            if checkpoint_tuple is not None:
                # Checkpoint exists → run was interrupted but state can be recovered
                now = _utcnow()
                await repo.update(
                    run.id,
                    status="interrupted",
                    stage="recovered",
                    recovered_at=now,
                    output_payload={
                        "recovered": True,
                        "checkpoint_version": str(
                            checkpoint_tuple.config.get("configurable", {}).get(
                                "thread_ts", "unknown"
                            )
                        ),
                    },
                    error_message=(
                        "Run was interrupted; checkpoint found at version "
                        f"{checkpoint_tuple.config.get('configurable', {}).get('thread_ts', 'unknown')}. "
                        "State is recoverable via resume API."
                    ),
                    finished_at=now,
                )
                await self._request_session.commit()
                recovered_count += 1
                logger.info(
                    "Recovered run %s (thread_id=%s, checkpoint version=%s)",
                    str(run.id),
                    thread_id,
                    checkpoint_tuple.config.get("configurable", {}).get(
                        "thread_ts", "unknown"
                    ),
                )
            else:
                # No checkpoint → mark as failed with recovery error
                await repo.update(
                    run.id,
                    status="failed",
                    stage="no_checkpoint",
                    error_message=(
                        "Recovery: no LangGraph checkpoint found for thread_id="
                        f"{thread_id}; run likely lost state."
                    ),
                    finished_at=_utcnow(),
                )
                await self._request_session.commit()
                failed_count += 1
                logger.info(
                    "Marked run %s as failed: no checkpoint for thread_id=%s",
                    str(run.id),
                    thread_id,
                )

        logger.info(
            "Recovery scan complete: checked=%d, recovered=%d, marked_failed=%d",
            len(stale_runs),
            recovered_count,
            failed_count,
        )
        return {
            "checked": len(stale_runs),
            "recovered": recovered_count,
            "marked_failed": failed_count,
        }
