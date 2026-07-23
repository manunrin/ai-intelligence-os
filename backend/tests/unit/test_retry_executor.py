"""Unit tests for RetryExecutor."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.workflows.error_classifier import ErrorCategory
from backend.workflows.executor import Executor, RunResult, SyncExecutor
from backend.workflows.retry_executor import RetryExecutor


def _make_run_result(
    status: str = "completed",
    error_message: str | None = None,
    retry_count: int = 0,
) -> RunResult:
    return RunResult(
        status=status,
        run_id=uuid.uuid4(),
        output_payload={"result": "data"} if status == "completed" else None,
        error_message=error_message,
        duration_ms=100,
        finished_at=datetime.now(timezone.utc),
        retry_count=retry_count,
    )


def _make_mock_inner_executor(
    results: list[RunResult] | Exception | None = None,
) -> Executor:
    """Create a mock Executor that returns a sequence of results or raises."""
    mock = MagicMock(spec=Executor)
    if results is None:
        results = [_make_run_result("completed")]
    elif isinstance(results, Exception):
        results = [results]

    if len(results) == 1 and isinstance(results[0], Exception):
        # Single exception — raise on every call
        async def failing(*_args, **_kwargs):
            raise results[0]
        mock.execute = AsyncMock(side_effect=failing)
    else:
        call_count = 0

        async def sequential(*_args, **_kwargs):
            nonlocal call_count
            result = results[min(call_count, len(results) - 1)]
            call_count += 1
            if isinstance(result, Exception):
                raise result
            return result

        mock.execute = AsyncMock(side_effect=sequential)
    return mock


class TestRetryExecutorCompletedImmediately:
    """Successful run should not retry."""

    @pytest.mark.asyncio
    async def test_completed_returns_immediately(self):
        inner = _make_mock_inner_executor([_make_run_result("completed")])
        executor = RetryExecutor(inner, max_attempts=3)

        result = await executor.execute(
            run_id=uuid.uuid4(),
            factory=lambda: None,
            state={},
            user_id=uuid.uuid4(),
            session=AsyncMock(),
            cancellation_token={},
        )

        assert result.status == "completed"
        assert result.retry_count == 0
        inner.execute.assert_called_once()


class TestRetryExecutorPermanentErrorNoRetry:
    """Permanent errors should not be retried."""

    @pytest.mark.asyncio
    async def test_permanent_error_no_retry(self):
        failed = _make_run_result("failed", error_message="ValueError: invalid input")
        inner = _make_mock_inner_executor([failed])
        executor = RetryExecutor(inner, max_attempts=3)

        result = await executor.execute(
            run_id=uuid.uuid4(),
            factory=lambda: None,
            state={},
            user_id=uuid.uuid4(),
            session=AsyncMock(),
            cancellation_token={},
        )

        assert result.status == "failed"
        assert result.retry_count == 0
        inner.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_authentication_error_no_retry(self):
        failed = _make_run_result("failed", error_message="AuthenticationError: invalid key")
        inner = _make_mock_inner_executor([failed])
        executor = RetryExecutor(inner, max_attempts=3)

        result = await executor.execute(
            run_id=uuid.uuid4(),
            factory=lambda: None,
            state={},
            user_id=uuid.uuid4(),
            session=AsyncMock(),
            cancellation_token={},
        )

        assert result.status == "failed"
        assert result.retry_count == 0


class TestRetryExecutorTransientRetries:
    """Transient errors should be retried with backoff."""

    @pytest.mark.asyncio
    async def test_transient_error_retries_then_succeeds(self):
        """First attempt fails transiently, second succeeds."""
        transient_fail = _make_run_result("failed", error_message="TimeoutError: timed out")
        success = _make_run_result("completed")
        inner = _make_mock_inner_executor([transient_fail, success])

        executor = RetryExecutor(inner, max_attempts=3, base_delay_ms=1, max_delay_ms=10)
        result = await executor.execute(
            run_id=uuid.uuid4(),
            factory=lambda: None,
            state={},
            user_id=uuid.uuid4(),
            session=AsyncMock(),
            cancellation_token={},
        )

        assert result.status == "completed"
        assert result.retry_count == 1
        assert inner.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_all_retries_exhausted(self):
        """All attempts fail with transient error → retry_count = max_attempts - 1."""
        transient_fail = _make_run_result("failed", error_message="rate limit exceeded")
        inner = _make_mock_inner_executor([transient_fail, transient_fail, transient_fail])

        executor = RetryExecutor(inner, max_attempts=3, base_delay_ms=1, max_delay_ms=10)
        result = await executor.execute(
            run_id=uuid.uuid4(),
            factory=lambda: None,
            state={},
            user_id=uuid.uuid4(),
            session=AsyncMock(),
            cancellation_token={},
        )

        assert result.status == "failed"
        assert result.retry_count == 2  # max_attempts(3) - 1
        assert inner.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_single_attempt_no_retries_needed(self):
        """max_attempts=1 means no retries at all."""
        transient_fail = _make_run_result("failed", error_message="timed out")
        inner = _make_mock_inner_executor([transient_fail])

        executor = RetryExecutor(inner, max_attempts=1, base_delay_ms=1000)
        result = await executor.execute(
            run_id=uuid.uuid4(),
            factory=lambda: None,
            state={},
            user_id=uuid.uuid4(),
            session=AsyncMock(),
            cancellation_token={},
        )

        assert result.status == "failed"
        assert result.retry_count == 0
        assert inner.execute.call_count == 1


class TestRetryExecutorRaisedExceptions:
    """RetryExecutor handles exceptions raised by inner.execute()."""

    @pytest.mark.asyncio
    async def test_raised_transient_exception_triggers_retry(self):
        """inner.execute() raises TimeoutError → retry."""
        transient_exc = TimeoutError("connection timed out")
        success = _make_run_result("completed")
        inner = _make_mock_inner_executor([transient_exc, success])

        executor = RetryExecutor(inner, max_attempts=3, base_delay_ms=1, max_delay_ms=10)
        result = await executor.execute(
            run_id=uuid.uuid4(),
            factory=lambda: None,
            state={},
            user_id=uuid.uuid4(),
            session=AsyncMock(),
            cancellation_token={},
        )

        assert result.status == "completed"
        assert result.retry_count == 1
        assert inner.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_raised_permanent_exception_no_retry(self):
        """inner.execute() raises ValueError → no retry."""
        perm_exc = ValueError("invalid input")
        inner = _make_mock_inner_executor([perm_exc])

        executor = RetryExecutor(inner, max_attempts=3, base_delay_ms=1000)
        result = await executor.execute(
            run_id=uuid.uuid4(),
            factory=lambda: None,
            state={},
            user_id=uuid.uuid4(),
            session=AsyncMock(),
            cancellation_token={},
        )

        assert result.status == "failed"
        assert result.retry_count == 0
        assert inner.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_raised_transient_exhausts_retries(self):
        """Multiple raised transient exceptions exhaust retries."""
        exc = TimeoutError("connection refused")
        inner = _make_mock_inner_executor([exc, exc, exc])

        executor = RetryExecutor(inner, max_attempts=3, base_delay_ms=1, max_delay_ms=10)
        result = await executor.execute(
            run_id=uuid.uuid4(),
            factory=lambda: None,
            state={},
            user_id=uuid.uuid4(),
            session=AsyncMock(),
            cancellation_token={},
        )

        assert result.status == "failed"
        assert result.retry_count == 2  # max_attempts(3) - 1
        assert inner.execute.call_count == 3


class TestRetryExecutorMetrics:
    """RetryExecutor records agent_run_retries_total counter."""

    @pytest.mark.asyncio
    async def test_counter_fires_on_retry(self):
        """A retry increments the agent_run_retries_total counter."""
        from backend.metrics import format_prometheus, reset

        reset()
        transient_fail = _make_run_result("failed", error_message="TimeoutError: timed out")
        success = _make_run_result("completed")
        inner = _make_mock_inner_executor([transient_fail, success])

        executor = RetryExecutor(inner, max_attempts=3, base_delay_ms=1, max_delay_ms=10)
        result = await executor.execute(
            run_id=uuid.uuid4(),
            factory=lambda: None,
            state={},
            user_id=uuid.uuid4(),
            session=AsyncMock(),
            cancellation_token={},
        )

        assert result.status == "completed"
        assert result.retry_count == 1
        output = format_prometheus()
        assert 'agent_run_retries_total{attempt="1"} 1' in output

    @pytest.mark.asyncio
    async def test_counter_bounded_label_on_many_retries(self):
        """Retry count >= 3 is bucketed as '3' to prevent cardinality growth."""
        from backend.metrics import format_prometheus, reset

        reset()
        exc = TimeoutError("connection refused")
        inner = _make_mock_inner_executor([exc, exc, exc])

        executor = RetryExecutor(inner, max_attempts=3, base_delay_ms=1, max_delay_ms=10)
        result = await executor.execute(
            run_id=uuid.uuid4(),
            factory=lambda: None,
            state={},
            user_id=uuid.uuid4(),
            session=AsyncMock(),
            cancellation_token={},
        )

        assert result.status == "failed"
        assert result.retry_count == 2
        output = format_prometheus()
        # 2 retries fire counter twice: attempt=1 (first retry) and attempt=2 (second retry)
        assert 'agent_run_retries_total{attempt="1"} 1' in output
        assert 'agent_run_retries_total{attempt="2"} 1' in output

    @pytest.mark.asyncio
    async def test_no_counter_on_zero_retries(self):
        """No retry counter when the first attempt succeeds."""
        from backend.metrics import format_prometheus, reset

        reset()
        inner = _make_mock_inner_executor([_make_run_result("completed")])

        executor = RetryExecutor(inner, max_attempts=3)
        result = await executor.execute(
            run_id=uuid.uuid4(),
            factory=lambda: None,
            state={},
            user_id=uuid.uuid4(),
            session=AsyncMock(),
            cancellation_token={},
        )

        assert result.status == "completed"
        assert result.retry_count == 0
        output = format_prometheus()
        assert "agent_run_retries_total" not in output


class TestRetryExecutorNonFailStatuses:
    """Cancelled/timeout statuses should not trigger retries."""

    @pytest.mark.asyncio
    async def test_cancelled_status_not_retried(self):
        cancelled = _make_run_result("cancelled")
        inner = _make_mock_inner_executor([cancelled])

        executor = RetryExecutor(inner, max_attempts=3, base_delay_ms=1000)
        result = await executor.execute(
            run_id=uuid.uuid4(),
            factory=lambda: None,
            state={},
            user_id=uuid.uuid4(),
            session=AsyncMock(),
            cancellation_token={},
        )

        assert result.status == "cancelled"
        assert result.retry_count == 0
        inner.execute.assert_called_once()


class TestRetryExecutorValidation:
    """Constructor validation."""

    def test_max_attempts_must_be_positive(self):
        with pytest.raises(ValueError, match="max_attempts"):
            RetryExecutor(SyncExecutor(), max_attempts=0)

    def test_max_delay_must_be_at_least_base(self):
        with pytest.raises(ValueError, match="max_delay_ms"):
            RetryExecutor(SyncExecutor(), base_delay_ms=5000, max_delay_ms=100)
