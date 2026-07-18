"""Simple Prometheus-compatible metrics endpoint."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from typing import Any

# ── Internal registries (no external deps) ──────────────────────────

_histograms: dict[str, list[float]] = defaultdict(list)
_counters: dict[str, int] = defaultdict(int)


def counter(name: str, value: int = 1) -> None:
    """Increment a named counter."""
    _counters[name] += value


def histogram(name: str, value: float) -> None:
    """Record a histogram observation."""
    _histograms[name].append(value)


def reset() -> None:
    """Clear all metrics (useful for tests)."""
    _counters.clear()
    _histograms.clear()


def format_prometheus() -> str:
    """Render all metrics in Prometheus text exposition format."""
    lines: list[str] = []
    for name, count in sorted(_counters.items()):
        lines.append(f"# HELP {name} Application counter metric")
        lines.append(f"# TYPE {name} counter")
        lines.append(f"{name} {count}")
    for name, values in sorted(_histograms.items()):
        lines.append(f"# HELP {name} Application histogram metric")
        lines.append(f"# TYPE {name} histogram")
        total = len(values)
        if total == 0:
            continue
        s = sorted(values)
        p50 = s[int(total * 0.5)]
        p95 = s[min(int(total * 0.95), total - 1)]
        p99 = s[min(int(total * 0.99), total - 1)]
        lines.append(f"{name}_count {total}")
        lines.append(f"{name}_sum {sum(values):.6f}")
        lines.append(f"{name}_p50 {p50:.6f}")
        lines.append(f"{name}_p95 {p95:.6f}")
        lines.append(f"{name}_p99 {p99:.6f}")
    return "\n".join(lines) + "\n"
