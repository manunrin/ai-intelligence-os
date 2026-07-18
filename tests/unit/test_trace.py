"""Tests for distributed tracing infrastructure."""

from __future__ import annotations

import pytest

from backend.trace import (
    _NoOpSpan,
    _NoOpTracer,
    get_tracer,
    record_event,
    set_attr,
    start_span,
)


class TestNoOpSpan:
    """Verify no-op span is safe to call in all scenarios."""

    def test_noop_span_context_manager(self):
        """_NoOpSpan works as a context manager."""
        with _NoOpSpan() as span:
            assert isinstance(span, _NoOpSpan)

    def test_noop_span_add_event(self):
        """_NoOpSpan.add_event does not raise."""
        span = _NoOpSpan()
        span.add_event("test_event", {"key": "value"})

    def test_noop_span_set_attribute(self):
        """_NoOpSpan.set_attribute does not raise."""
        span = _NoOpSpan()
        span.set_attribute("key", "value")
        span.set_attribute("count", 42)

    def test_noop_span_is_not_recording(self):
        """_NoOpSpan.is_recording returns False."""
        assert _NoOpSpan().is_recording is False


class TestNoOpTracer:
    """Verify no-op tracer returns no-op spans."""

    def test_start_span_returns_noop(self):
        """_NoOpTracer.start_span returns a _NoOpSpan."""
        tracer = _NoOpTracer()
        span = tracer.start_span("test")
        assert isinstance(span, _NoOpSpan)

    def test_start_as_current_span_returns_noop(self):
        """_NoOpTracer.start_as_current_span yields a _NoOpSpan."""
        tracer = _NoOpTracer()
        with tracer.start_as_current_span("test") as span:
            assert isinstance(span, _NoOpSpan)


class TestPublicAPI:
    """Test public API functions when OTel is unavailable."""

    def test_start_span_noop(self):
        """start_span() works as context manager even without OTel SDK."""
        with start_span("test_operation") as span:
            assert span is not None

    def test_set_attr_noop(self):
        """set_attr() on a no-op span does not raise."""
        span = _NoOpSpan()
        set_attr(span, "key", "value")

    def test_record_event_noop(self):
        """record_event() on a no-op span does not raise."""
        span = _NoOpSpan()
        record_event(span, "event_name", {"k": "v"})

    def test_get_tracer_noop(self):
        """get_tracer() returns _NoOpTracer when OTel is unavailable."""
        tracer = get_tracer()
        assert isinstance(tracer, _NoOpTracer)
