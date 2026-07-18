"""Tests for Prometheus-compatible metrics module."""

from __future__ import annotations

import pytest

from backend.metrics import counter, histogram, format_prometheus, reset


class TestCounter:
    """Test basic counter operations."""

    def test_increment(self):
        """counter() increments a named counter."""
        reset()
        counter("http_requests_total")
        assert "http_requests_total 1" in format_prometheus()

    def test_multiple_increments(self):
        """Multiple counter calls accumulate."""
        reset()
        counter("http_requests_total")
        counter("http_requests_total")
        counter("http_requests_total")
        assert "http_requests_total 3" in format_prometheus()

    def test_custom_value(self):
        """counter() accepts custom increment value."""
        reset()
        counter("errors_total", 5)
        assert "errors_total 5" in format_prometheus()

    def test_independent_counters(self):
        """Different counters track independently."""
        reset()
        counter("reqs_a")
        counter("reqs_b")
        counter("reqs_b")
        out = format_prometheus()
        assert "reqs_a 1" in out
        assert "reqs_b 2" in out


class TestHistogram:
    """Test histogram operations."""

    def test_record_observation(self):
        """histogram() records an observation."""
        reset()
        histogram("duration_seconds", 0.123)
        out = format_prometheus()
        assert "duration_seconds_count 1" in out
        assert "duration_seconds_sum 0.123000" in out

    def test_multiple_observations(self):
        """Multiple observations accumulate."""
        reset()
        histogram("duration_seconds", 0.1)
        histogram("duration_seconds", 0.2)
        histogram("duration_seconds", 0.3)
        out = format_prometheus()
        assert "duration_seconds_count 3" in out
        assert "duration_seconds_sum 0.600000" in out

    def test_percentiles(self):
        """Percentile values are calculated correctly."""
        reset()
        for i in range(100):
            histogram("latency", float(i))
        out = format_prometheus()
        assert "latency_p50 50" in out
        assert "latency_p95 95" in out


class TestFormatPrometheus:
    """Test output formatting."""

    def test_combined_metrics(self):
        """Both counters and histograms appear in output."""
        reset()
        counter("requests_total")
        histogram("duration_seconds", 0.5)
        out = format_prometheus()
        assert "# HELP requests_total" in out
        assert "# TYPE requests_total counter" in out
        assert "# HELP duration_seconds" in out
        assert "# TYPE duration_seconds histogram" in out

    def test_reset_clears_all(self):
        """reset() clears all metrics."""
        counter("x")
        histogram("y", 1.0)
        reset()
        out = format_prometheus()
        assert "x" not in out
        assert "y" not in out
