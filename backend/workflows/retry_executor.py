"""RetryExecutor — wraps an Executor with exponential backoff retry logic.

Handles two failure modes:
  A) inner.execute() returns a failed RunResult (e.g., LLM call fails inside _sync_execute_impl)
  B) inner.execute() raises a transient exception (e.g., network error bubbling up)

Retry semantics depend on LangGraph checkpoint semantics: retries only help when
downstream tools are idempotent. Non-idempotent side-effect tools may produce
duplicate effects across retries.

retry_count = number of retries AFTER the initial attempt.
  - First successful execution: retry_count = 0
  - max_attempts=3 means: 1 initial + up to 2 retries → retry_count max = 2
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..metrics import counter
from .error_classifier import ErrorCategory, classify_error
from .executor import Executor, PipelineFactory, RunResult

logger = logging.getLogger(__name__)


class RetryExecutor(Executor):
    """Wraps an inner executor with configurable retry and exponential backoff."""

    def __init__(
        self,
        inner: Executor,
        *,
        max_attempts: int = 3,
        base_delay_ms: int = 1000,
        max_delay_ms: int = 30000,
    ) -> None:
        """
        Args:
            inner: The wrapped executor (typically SyncExecutor).
            max_attempts: Total execution attempts including the initial one.
                max_attempts=3 means: 1 initial + 2 retries → retry_count max = 2.
            base_delay_ms: Initial backoff delay in milliseconds.
            max_delay_ms: Maximum backoff delay cap.
        """
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if base_delay_ms < 0:
            raise ValueError("base_delay_ms must be >= 0")
        if max_delay_ms < base_delay_ms:
            raise ValueError("max_delay_ms must be >= base_delay_ms")

        self._inner = inner
        self._max_attempts = max_attempts
        self._base_delay_ms = base_delay_ms
        self._max_delay_ms = max_delay_ms

    def _record_retry(self, retries: int) -> None:
        """Record a retry event with bounded label values."""
        bucket = str(min(retries, 3))
        counter("agent_run_retries_total", labels={"attempt": bucket})

    async def execute(
        self,
        run_id: uuid.UUID,
        factory: PipelineFactory,
        state: dict[str, Any],
        user_id: uuid.UUID,
        session: AsyncSession,
        cancellation_token: dict[uuid.UUID, bool],
        thread_id: str | None = None,
    ) -> RunResult:
        last_result: RunResult | None = None
        actual_retries = 0

        for attempt in range(1, self._max_attempts + 1):
            try:
                result = await self._inner.execute(
                    run_id=run_id,
                    factory=factory,
                    state=state,
                    user_id=user_id,
                    session=session,
                    cancellation_token=cancellation_token,
                    thread_id=thread_id,
                )
            except Exception as exc:
                # Failure mode B: inner.execute() raised an exception.
                category = classify_error(str(exc))
                logger.warning(
                    "Run %s attempt %d/%d raised %s (%s)",
                    str(run_id),
                    attempt,
                    self._max_attempts,
                    type(exc).__name__,
                    str(exc)[:200],
                )
                if category == ErrorCategory.TRANSIENT and attempt < self._max_attempts:
                    delay_ms = min(self._base_delay_ms * (2 ** (attempt - 1)), self._max_delay_ms)
                    logger.info(
                        "Transient error on run %s, retrying in %d ms (attempt %d/%d)",
                        str(run_id),
                        delay_ms,
                        attempt,
                        self._max_attempts,
                    )
                    await asyncio.sleep(delay_ms / 1000.0)
                    actual_retries += 1
                    # Record retry event (bounded label to prevent cardinality growth)
                    self._record_retry(actual_retries)
                    continue
                # Permanent error or last attempt — return with exception details.
                return RunResult(
                    status="failed",
                    run_id=run_id,
                    error_message=str(exc),
                    retry_count=actual_retries,
                )

            last_result = result

            # Completed → return immediately (no retries needed).
            if result.status == "completed":
                return RunResult(
                    status="completed",
                    run_id=result.run_id,
                    output_payload=result.output_payload,
                    duration_ms=result.duration_ms,
                    finished_at=result.finished_at,
                    stages=result.stages,
                    retry_count=actual_retries,
                )

            # Non-fail statuses (cancelled, timeout) → return immediately, no retry.
            if result.status not in ("failed",):
                return RunResult(
                    status=result.status,
                    run_id=result.run_id,
                    output_payload=result.output_payload,
                    error_message=result.error_message,
                    duration_ms=result.duration_ms,
                    finished_at=result.finished_at,
                    stages=result.stages,
                    retry_count=actual_retries,
                )

            # Failed — classify and decide whether to retry.
            category = classify_error(result.error_message or "")
            if category == ErrorCategory.PERMANENT:
                logger.info(
                    "Permanent error on run %s attempt %d; not retrying: %s",
                    str(run_id),
                    attempt,
                    result.error_message[:200] if result.error_message else "",
                )
                return RunResult(
                    status="failed",
                    run_id=result.run_id,
                    output_payload=result.output_payload,
                    error_message=result.error_message,
                    duration_ms=result.duration_ms,
                    finished_at=result.finished_at,
                    stages=result.stages,
                    retry_count=actual_retries,
                )

            # Transient failure — retry if attempts remain.
            if attempt < self._max_attempts:
                delay_ms = min(self._base_delay_ms * (2 ** (attempt - 1)), self._max_delay_ms)
                logger.info(
                    "Transient error on run %s, retrying in %d ms (attempt %d/%d): %s",
                    str(run_id),
                    delay_ms,
                    attempt,
                    self._max_attempts,
                    result.error_message[:200] if result.error_message else "",
                )
                await asyncio.sleep(delay_ms / 1000.0)
                actual_retries += 1
                # Record retry event (bounded label to prevent cardinality growth)
                self._record_retry(actual_retries)
            else:
                # Exhausted all retries.
                logger.warning(
                    "Run %s exhausted all %d attempts (%d retries): %s",
                    str(run_id),
                    self._max_attempts,
                    actual_retries,
                    result.error_message[:200] if result.error_message else "",
                )

        # All attempts exhausted — return the last result with retry_count.
        assert last_result is not None
        return RunResult(
            status="failed",
            run_id=last_result.run_id,
            output_payload=last_result.output_payload,
            error_message=last_result.error_message,
            duration_ms=last_result.duration_ms,
            finished_at=last_result.finished_at,
            stages=last_result.stages,
            retry_count=actual_retries,
        )
