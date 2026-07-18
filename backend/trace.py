"""Distributed tracing via OpenTelemetry (optional, degrades gracefully).

When opentelemetry-api and opentelemetry-sdk are installed, this module
creates real spans. When they are absent, every call becomes a no-op
— metrics continue working normally.

Usage:
    from .trace import tracer, start_span

    with start_span("my_operation"):
        ...
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Generator

logger = logging.getLogger(__name__)


# ── Lazy OTel import ────────────────────────────────────────────

_otlp_available: bool | None = None
_tracer: Any = None


def _ensure_tracer() -> Any:
    """Lazily initialize the OTel tracer on first use."""
    global _otlp_available, _tracer

    if _otlp_available is not None:
        return _tracer

    try:
        from opentelemetry import trace as otel_trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

        provider = TracerProvider()
        processor = BatchSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)
        otel_trace.set_tracer_provider(provider)

        _tracer = otel_trace.get_tracer(
            "ai-intelligence-os",
            instrumenting_library_version="0.1.0",
        )
        _otlp_available = True
        logger.info("OpenTelemetry tracing enabled")
    except ImportError:
        _otlp_available = False
        _tracer = None
        logger.debug("OpenTelemetry SDK not installed — tracing disabled (metrics unaffected)")

    return _tracer


# ── No-op fallback ─────────────────────────────────────────────

class _NoOpSpan:
    """Minimal span that does nothing."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def add_event(self, name: str, attributes: dict[str, str] | None = None) -> None:
        pass

    def set_attribute(self, key: str, value: str | int | float | bool) -> None:
        pass

    @property
    def is_recording(self) -> bool:
        return False


class _NoOpTracer:
    """Tracer that returns no-op spans."""

    def start_span(self, name: str, **kwargs: Any) -> "_NoOpSpan":
        return _NoOpSpan()

    @contextmanager
    def start_as_current_span(self, name: str, **kwargs: Any) -> Generator[_NoOpSpan, None, None]:
        yield _NoOpSpan()


# ── Public API ─────────────────────────────────────────────────

@contextmanager
def start_span(name: str, attributes: dict[str, str] | None = None) -> Generator[Any, None, None]:
    """Context manager that starts an OTel span (or no-op if unavailable)."""
    tracer = _ensure_tracer()
    if tracer is None or tracer is False:
        yield _NoOpSpan()
        return

    if isinstance(tracer, _NoOpTracer):
        yield _NoOpSpan()
        return

    with tracer.start_as_current_span(name) as span:
        if attributes:
            for k, v in attributes.items():
                span.set_attribute(k, v)
        yield span


def record_event(span: Any, event_name: str, attributes: dict[str, str] | None = None) -> None:
    """Record a named event on a span."""
    if hasattr(span, "add_event"):
        span.add_event(event_name, attributes or {})


def set_attr(span: Any, key: str, value: str | int | float | bool) -> None:
    """Set an attribute on a span."""
    if hasattr(span, "set_attribute"):
        span.set_attribute(key, value)


def get_tracer() -> Any:
    """Return the current tracer instance (useful for manual span creation)."""
    t = _ensure_tracer()
    if t is None or t is False:
        return _NoOpTracer()
    if isinstance(t, _NoOpTracer):
        return t
    return t
