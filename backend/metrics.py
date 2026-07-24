"""Prometheus-compatible metrics with label support and histogram buckets."""

from __future__ import annotations

import math
import time
import uuid
from collections import defaultdict
from typing import Any


# ── Internal registries ────────────────────────────────────────

_counters: dict[str, dict[tuple[str, ...], int]] = defaultdict(lambda: defaultdict(int))
_histograms: dict[str, dict[tuple[str, ...], list[float]]] = defaultdict(lambda: defaultdict(list))

# Default Prometheus buckets (seconds) for latency-style histograms
_DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)


def counter(name: str, value: int = 1, labels: dict[str, str] | None = None) -> None:
    """Increment a named counter, optionally with labels.

    Args:
        name: Metric name (e.g. "http_requests_total").
        value: Amount to increment (default 1).
        labels: Optional label dict (e.g. {"method": "GET", "status": "200"}).
    """
    key = _label_key(labels)
    _counters[name][key] += value


def histogram(name: str, value: float, labels: dict[str, str] | None = None, buckets: tuple[float, ...] | None = None) -> None:
    """Record a histogram observation, optionally with labels.

    Uses built-in bucket accumulation so format_prometheus renders proper
    Prometheus histogram _bucket lines instead of raw percentile computation.

    Args:
        name: Metric name (e.g. "http_request_duration_seconds").
        value: Observation value (e.g. elapsed seconds).
        labels: Optional label dict.
        buckets: Upper bounds for bucket lines. Defaults to Prometheus standard.
    """
    key = _label_key(labels)
    if buckets is None:
        buckets = _DEFAULT_BUCKETS
    _histograms[name][key].append((value, buckets))


# ── Evaluation score tracking ────────────────────────────────────

_evaluation_scores: list[float] = []


def record_evaluation_score(score: float) -> None:
    """Record an evaluation score for distribution tracking."""
    _evaluation_scores.append(score)


def get_evaluation_scores() -> list[float]:
    """Return all recorded evaluation scores."""
    return list(_evaluation_scores)


def reset_evaluation_scores() -> None:
    """Clear recorded evaluation scores (for tests)."""
    _evaluation_scores.clear()


def reset() -> None:
    """Clear all metrics (useful for tests)."""
    _counters.clear()
    _histograms.clear()


def _label_key(labels: dict[str, str] | None) -> tuple[str, ...]:
    """Convert a label dict to a sorted tuple for hashing."""
    if not labels:
        return ()
    return tuple(sorted(labels.items()))


def _compute_buckets(values: list[tuple[float, tuple[float, ...]]]) -> list[tuple[int, float]]:
    """Compute cumulative bucket counts from a list of (value, buckets) tuples.

    Returns list of (upper_bound, cumulative_count) pairs.
    """
    # Collect all unique bucket boundaries across all observations
    all_bounds: set[float] = set()
    for _, buckets in values:
        all_bounds.update(buckets)
    all_bounds.add(float("inf"))
    sorted_bounds = sorted(all_bounds)

    result: list[tuple[int, float]] = []
    for bound in sorted_bounds:
        count = sum(1 for v, _ in values if v <= bound)
        result.append((bound, count))
    return result


def format_prometheus() -> str:
    """Render all metrics in Prometheus text exposition format."""
    lines: list[str] = []
    for name, buckets in sorted(_counters.items()):
        for key, count in sorted(buckets.items()):
            lines.append(f"# HELP {name} Application counter metric")
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name}{_format_labels(key)} {count}")
    for name, buckets in sorted(_histograms.items()):
        for key, observations in sorted(buckets.items()):
            if not observations:
                continue
            bucket_lines = _compute_buckets(observations)
            total_count = len(observations)
            total_sum = sum(v for v, _ in observations)

            lines.append(f"# HELP {name} Application histogram metric")
            lines.append(f"# TYPE {name} histogram")
            for bound, cum_count in bucket_lines[:-1]:  # all explicit buckets
                upper = f"{bound:.6f}" if bound != math.inf else "+Inf"
                lines.append(f"{name}{_format_labels(key)}_bucket{{{_format_labels_inner(key)}le=\"{upper}\"}} {cum_count}")
            # +Inf bucket always equals total_count
            lines.append(f"{name}{_format_labels(key)}_bucket{{{_format_labels_inner(key)}le=\"+Inf\"}} {total_count}")
            lines.append(f"{name}{_format_labels(key)}_count {total_count}")
            lines.append(f"{name}{_format_labels(key)}_sum {total_sum:.6f}")

    # ── Evaluation score distribution ──────────────────────────────
    scores = _evaluation_scores
    if scores:
        score_buckets = (0.0, 25.0, 50.0, 75.0, 100.0)
        score_counts: dict[float, int] = {}
        for b in score_buckets:
            score_counts[b] = sum(1 for s in scores if s <= b)

        lines.append("# HELP evaluation_scores_total Total number of recorded evaluation scores")
        lines.append("# TYPE evaluation_scores_total counter")
        lines.append(f"evaluation_scores_total {{}} {len(scores)}")

        lines.append("# HELP evaluation_score_distribution Evaluation score histogram")
        lines.append("# TYPE evaluation_score_distribution histogram")
        for bound in score_buckets:
            lines.append(f'evaluation_score_distribution_bucket{{le="{bound:.1f}"}} {score_counts[bound]}')
        lines.append('evaluation_score_distribution_bucket{{le="+Inf"}} {len(scores)}')
        lines.append(f"evaluation_score_distribution_count {{}} {len(scores)}")
        lines.append(f"evaluation_score_distribution_sum {{}} {sum(scores):.1f}")

    return "\n".join(lines) + "\n"


def _format_labels(key: tuple[str, ...]) -> str:
    """Format a label tuple as Prometheus labels string."""
    if not key:
        return ""
    parts = ",".join(f'{k}="{v}"' for k, v in key)
    return f"{{{parts}}}"


def _format_labels_inner(key: tuple[str, ...]) -> str:
    """Format a label tuple without outer braces (used inside bucket label)."""
    if not key:
        return ""
    parts = ",".join(f'{k}="{v}"' for k, v in key)
    return parts
