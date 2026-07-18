"""Tests for labeled Prometheus metrics."""

from __future__ import annotations

import pytest

from backend.metrics import counter, histogram, format_prometheus, reset


class TestLabeledCounter:
    """Counter with labels creates independent buckets."""

    def test_single_label(self):
        """counter() with one label creates distinct buckets."""
        reset()
        counter("http_requests_total", labels={"method": "GET"})
        counter("http_requests_total", labels={"method": "POST"})
        out = format_prometheus()
        assert 'http_requests_total{method="GET"} 1' in out
        assert 'http_requests_total{method="POST"} 1' in out

    def test_multiple_labels(self):
        """Multiple labels produce multi-key buckets."""
        reset()
        counter("api_calls_total", labels={"endpoint": "/users", "method": "GET"})
        counter("api_calls_total", labels={"endpoint": "/users", "method": "POST"})
        out = format_prometheus()
        assert 'api_calls_total{endpoint="/users",method="GET"} 1' in out
        assert 'api_calls_total{endpoint="/users",method="POST"} 1' in out

    def test_label_order_ignored(self):
        """Label dict order does not affect bucket identity."""
        reset()
        counter("reqs", labels={"a": "1", "b": "2"})
        counter("reqs", labels={"b": "2", "a": "1"})
        out = format_prometheus()
        assert 'reqs{a="1",b="2"} 2' in out


class TestLabeledHistogram:
    """Histogram with labels creates per-label buckets."""

    def test_labeled_histogram(self):
        """histogram() records per-label observations."""
        reset()
        histogram("duration_seconds", 0.5, labels={"method": "GET"})
        histogram("duration_seconds", 1.0, labels={"method": "POST"})
        out = format_prometheus()
        assert 'duration_seconds{method="GET"}_count 1' in out
        assert 'duration_seconds{method="POST"}_count 1' in out

    def test_mixed_labeled_and_unlabeled(self):
        """Labeled and unlabeled histograms stay separate."""
        reset()
        histogram("latency", 0.1)
        histogram("latency", 0.5, labels={"method": "POST"})
        out = format_prometheus()
        assert "latency_count 1" in out
        assert 'latency{method="POST"}_count 1' in out


class TestAgentRunMetrics:
    """Agent run and stage counters with labels."""

    def test_agent_run_counter_labels(self):
        """agent_runs_total has agent_type and status labels."""
        reset()
        counter("agent_runs_total", labels={"agent_type": "intelligence", "status": "submitted"})
        counter("agent_runs_total", labels={"agent_type": "intelligence", "status": "completed"})
        counter("agent_runs_total", labels={"agent_type": "autonomous", "status": "failed"})
        out = format_prometheus()
        assert 'agent_runs_total{agent_type="intelligence",status="submitted"} 1' in out
        assert 'agent_runs_total{agent_type="intelligence",status="completed"} 1' in out
        assert 'agent_runs_total{agent_type="autonomous",status="failed"} 1' in out

    def test_agent_duration_histogram(self):
        """agent_run_duration_seconds histogram with labels."""
        reset()
        histogram("agent_run_duration_seconds", 2.5, labels={"agent_type": "intelligence", "status": "completed"})
        histogram("agent_run_duration_seconds", 8.3, labels={"agent_type": "intelligence", "status": "completed"})
        out = format_prometheus()
        assert 'agent_run_duration_seconds{agent_type="intelligence",status="completed"}_count 2' in out
        assert 'agent_run_duration_seconds{agent_type="intelligence",status="completed"}_sum 10.800000' in out

    def test_stage_metrics(self):
        """agent_stages_total counter per stage name."""
        reset()
        counter("agent_stages_total", labels={"stage_name": "research"})
        counter("agent_stages_total", labels={"stage_name": "analyze"})
        counter("agent_stages_total", labels={"stage_name": "translate"})
        out = format_prometheus()
        assert 'agent_stages_total{stage_name="research"} 1' in out
        assert 'agent_stages_total{stage_name="translate"} 1' in out
