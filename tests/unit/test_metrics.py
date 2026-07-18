"""Tests for Prometheus-compatible metrics module with label support."""

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


class TestCounterLabels:
    """Test counter with Prometheus-style labels."""

    def test_counter_with_labels(self):
        """counter() records separate buckets per label set."""
        reset()
        counter("http_requests_total", labels={"method": "GET"})
        counter("http_requests_total", labels={"method": "POST"})
        counter("http_requests_total", labels={"method": "GET"})
        out = format_prometheus()
        assert 'http_requests_total{method="GET"} 2' in out
        assert 'http_requests_total{method="POST"} 1' in out

    def test_counter_label_order_independent(self):
        """Label order does not affect bucket identity."""
        reset()
        counter("http_requests_total", labels={"method": "GET", "status": "200"})
        counter("http_requests_total", labels={"status": "200", "method": "GET"})
        out = format_prometheus()
        assert 'http_requests_total{method="GET",status="200"} 2' in out

    def test_multiple_label_pairs(self):
        """Multi-label counters create independent buckets."""
        reset()
        counter("api_calls_total", labels={"endpoint": "/users", "method": "GET"})
        counter("api_calls_total", labels={"endpoint": "/users", "method": "POST"})
        counter("api_calls_total", labels={"endpoint": "/posts", "method": "GET"})
        out = format_prometheus()
        assert 'api_calls_total{endpoint="/posts",method="GET"} 1' in out
        assert 'api_calls_total{endpoint="/users",method="GET"} 1' in out
        assert 'api_calls_total{endpoint="/users",method="POST"} 1' in out

    def test_count_without_labels_uses_empty_bucket(self):
        """Calls without labels go to an unlabeled bucket."""
        reset()
        counter("requests_total")
        counter("requests_total", labels={"method": "GET"})
        out = format_prometheus()
        assert "requests_total 1" in out
        assert 'requests_total{method="GET"} 1' in out


class TestHistogram:
    """Test histogram operations with configurable buckets."""

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

    def test_default_buckets(self):
        """Default Prometheus buckets are rendered correctly."""
        reset()
        histogram("latency_seconds", 0.05)
        histogram("latency_seconds", 0.25)
        histogram("latency_seconds", 1.5)
        out = format_prometheus()
        # 0.05 <= 0.05 (bucket), 0.25 <= 0.25, 1.5 > 1.0 but <= 2.5
        assert 'le="0.050000"} 1' in out
        assert 'le="0.250000"} 2' in out
        assert 'le="2.500000"} 3' in out
        assert 'le="+Inf"} 3' in out

    def test_custom_buckets(self):
        """Custom buckets override defaults."""
        reset()
        histogram("custom_seconds", 50, buckets=(10, 25, 50, 100))
        histogram("custom_seconds", 75, buckets=(10, 25, 50, 100))
        out = format_prometheus()
        # 50 <= 50, 75 > 50; both <= 100
        assert 'le="50.000000"} 1' in out
        assert 'le="100.000000"} 2' in out


class TestHistogramLabels:
    """Test histogram with Prometheus-style labels."""

    def test_histogram_with_labels(self):
        """histogram() records per-label buckets."""
        reset()
        histogram("request_duration_seconds", 0.5, labels={"method": "GET"})
        histogram("request_duration_seconds", 1.0, labels={"method": "POST"})
        out = format_prometheus()
        assert 'request_duration_seconds{method="GET"}_count 1' in out
        assert 'request_duration_seconds{method="POST"}_count 1' in out

    def test_histogram_label_aggregation(self):
        """Same-label observations aggregate into one bucket."""
        reset()
        histogram("request_duration_seconds", 0.1, labels={"method": "GET"})
        histogram("request_duration_seconds", 0.2, labels={"method": "GET"})
        histogram("request_duration_seconds", 0.3, labels={"method": "GET"})
        out = format_prometheus()
        assert 'request_duration_seconds{method="GET"}_count 3' in out
        assert 'request_duration_seconds{method="GET"}_sum 0.600000' in out

    def test_mixed_labeled_and_unlabeled(self):
        """Labeled and unlabeled histograms stay independent."""
        reset()
        histogram("duration_seconds", 0.5)
        histogram("duration_seconds", 1.0, labels={"method": "POST"})
        out = format_prometheus()
        assert "duration_seconds_count 1" in out
        assert 'duration_seconds{method="POST"}_count 1' in out


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

    def test_reset_clears_labeled(self):
        """reset() clears labeled metrics too."""
        reset()
        counter("x", labels={"method": "GET"})
        histogram("y", 0.5, labels={"method": "POST"})
        reset()
        out = format_prometheus()
        assert "x" not in out
        assert "y" not in out

    def test_label_formatting(self):
        """Labels render as curly-brace key=value pairs."""
        reset()
        counter("reqs", labels={"method": "GET", "status": "200"})
        out = format_prometheus()
        assert '{method="GET",status="200"}' in out
