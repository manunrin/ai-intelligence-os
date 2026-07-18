"""Prometheus-compatible metrics with label support."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from typing import Any


# ── Internal registries ────────────────────────────────────────

_counters: dict[str, dict[tuple[str, ...], int]] = defaultdict(lambda: defaultdict(int))
_histograms: dict[str, dict[tuple[str, ...], list[float]]] = defaultdict(lambda: defaultdict(list))


def counter(name: str, value: int = 1, labels: dict[str, str] | None = None) -> None:
    """Increment a named counter, optionally with labels.

    Args:
        name: Metric name (e.g. "http_requests_total").
        value: Amount to increment (default 1).
        labels: Optional label dict (e.g. {"method": "GET", "status": "200"}).
    """
    key = _label_key(labels)
    _counters[name][key] += value


def histogram(name: str, value: float, labels: dict[str, str] | None = None) -> None:
    """Record a histogram observation, optionally with labels.

    Args:
        name: Metric name (e.g. "http_request_duration_seconds").
        value: Observation value (e.g. elapsed seconds).
        labels: Optional label dict.
    """
    key = _label_key(labels)
    _histograms[name][key].append(value)


def reset() -> None:
    """Clear all metrics (useful for tests)."""
    _counters.clear()
    _histograms.clear()


def _label_key(labels: dict[str, str] | None) -> tuple[str, ...]:
    """Convert a label dict to a sorted tuple for hashing."""
    if not labels:
        return ()
    return tuple(sorted(labels.items()))


def format_prometheus() -> str:
    """Render all metrics in Prometheus text exposition format."""
    lines: list[str] = []
    for name, buckets in sorted(_counters.items()):
        for key, count in sorted(buckets.items()):
            lines.append(f"# HELP {name} Application counter metric")
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name}{_format_labels(key)} {count}")
    for name, buckets in sorted(_histograms.items()):
        for key, values in sorted(buckets.items()):
            total = len(values)
            if total == 0:
                continue
            s = sorted(values)
            p50 = s[int(total * 0.5)]
            p95 = s[min(int(total * 0.95), total - 1)]
            p99 = s[min(int(total * 0.99), total - 1)]
            lines.append(f"# HELP {name} Application histogram metric")
            lines.append(f"# TYPE {name} histogram")
            lines.append(f"{name}{_format_labels(key)}_count {total}")
            lines.append(f"{name}{_format_labels(key)}_sum {sum(values):.6f}")
            lines.append(f"{name}{_format_labels(key)}_p50 {p50:.6f}")
            lines.append(f"{name}{_format_labels(key)}_p95 {p95:.6f}")
            lines.append(f"{name}{_format_labels(key)}_p99 {p99:.6f}")
    return "\n".join(lines) + "\n"


def _format_labels(key: tuple[str, ...]) -> str:
    """Format a label tuple as Prometheus labels string."""
    if not key:
        return ""
    parts = ",".join(f'{k}="{v}"' for k, v in key)
    return f"{{{parts}}}"
