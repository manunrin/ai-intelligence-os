"""Tests for Prometheus alert rules configuration validation."""

from __future__ import annotations

import pathlib
import re

import pytest
import yaml

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
ALERTS_FILE = ROOT_DIR.parent / "monitoring" / "alerts" / "alerting_rules.yaml"


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture()
def all_rules():
    """Load all alert rules across all groups."""
    with open(ALERTS_FILE) as f:
        data = yaml.safe_load(f)
    rules = []
    for group in data["groups"]:
        for rule in group.get("rules", []):
            rule["_group"] = group["name"]
            rules.append(rule)
    return rules


@pytest.fixture()
def alert_names(all_rules):
    """Return set of alert names."""
    return {r["alert"] for r in all_rules}


@pytest.fixture()
def all_exprs(all_rules):
    """Return list of (alert_name, expression) tuples."""
    result = []
    for rule in all_rules:
        expr = rule["expr"].strip()
        if expr.startswith("|"):
            expr = "\n".join(
                line for line in expr.split("\n")[1:] if line.strip()
            )
        result.append((rule["alert"], expr))
    return result


@pytest.fixture()
def label_selector_rules(all_rules):
    """Filter to only rules that use label selectors."""
    return [r for r in all_rules if "{" in r["expr"]]


# ── File existence and YAML validity ──────────────────────────────


class TestAlertRulesFileExists:
    def test_alert_rules_file_exists(self):
        assert ALERTS_FILE.exists(), f"Not found at {ALERTS_FILE}"

    def test_alert_rules_valid_yaml(self):
        with open(ALERTS_FILE) as f:
            data = yaml.safe_load(f)
        assert data is not None

    def test_has_groups(self):
        with open(ALERTS_FILE) as f:
            data = yaml.safe_load(f)
        assert "groups" in data
        assert isinstance(data["groups"], list)
        assert len(data["groups"]) > 0

    def test_group_has_name(self):
        with open(ALERTS_FILE) as f:
            data = yaml.safe_load(f)
        for group in data["groups"]:
            assert "name" in group
            assert isinstance(group["name"], str)
            assert len(group["name"]) > 0


# ── Rule structure ────────────────────────────────────────────────


class TestAlertRuleStructure:
    def test_each_rule_has_alert_name(self, all_rules):
        for rule in all_rules:
            assert "alert" in rule
            assert isinstance(rule["alert"], str)
            assert len(rule["alert"]) > 0

    def test_each_rule_has_expr(self, all_rules):
        for rule in all_rules:
            assert "expr" in rule
            assert isinstance(rule["expr"], str)
            assert len(rule["expr"].strip()) > 0

    def test_each_rule_has_for(self, all_rules):
        for rule in all_rules:
            assert "for" in rule
            assert isinstance(rule["for"], str)

    def test_each_rule_has_severity_label(self, all_rules):
        for rule in all_rules:
            assert "labels" in rule
            assert "severity" in rule["labels"]
            assert rule["labels"]["severity"] in ("critical", "warning")

    def test_each_rule_has_annotations(self, all_rules):
        for rule in all_rules:
            assert "annotations" in rule
            ann = rule["annotations"]
            assert "summary" in ann
            assert "description" in ann


# ── Expected alert names ──────────────────────────────────────────


EXPECTED_ALERTS = [
    "AgentRunFailureRateHigh",
    "AgentRunLatencyP95High",
    "LLMFallbackRateHigh",
    "LLMRequestErrorRateHigh",
    "VectorSearchErrorRateHigh",
    "HTTP5xxErrorRateHigh",
]


class TestAlertRuleNames:
    def test_expected_alert_count(self, all_rules):
        assert len(all_rules) == 6

    def test_all_expected_alerts_present(self, alert_names):
        for name in EXPECTED_ALERTS:
            assert name in alert_names, f"Missing expected alert: {name}"

    def test_no_unexpected_alerts(self, alert_names):
        assert alert_names == set(EXPECTED_ALERTS)


# ── Metric name references ────────────────────────────────────────


KNOWN_METRICS = {
    "http_requests_total",
    "http_request_duration_seconds",
    "agent_runs_total",
    "agent_run_duration_seconds",
    "agent_stages_total",
    "llm_requests_total",
    "llm_request_duration_seconds",
    "embedding_requests_total",
    "embedding_request_duration_seconds",
    "embedding_batch_total",
    "embedding_batch_items_total",
    "embedding_batch_duration_seconds",
    "vector_operations_total",
    "vector_operation_duration_seconds",
    "vector_search_total",
    "vector_search_duration_seconds",
}

_PROMQL_KEYWORDS = {
    "sum", "rate", "histogram_quantile", "by", "le", "avg",
    "min", "max", "count", "increase", "delta", "deriv",
    "abs", "ceil", "floor", "round", "clamp_min", "clamp_max",
    "topk", "bottomk", "sort", "sort_desc", "label_replace",
    "label_join", "absent", "predict_linear", "resets",
    "quantile_over_time", "sum_over_time", "count_over_time",
    "stddev_over_time", "stdvar_over_time",
}

# Common Prometheus label names that are not metric names
_LABEL_NAMES = {
    "status", "method", "path", "provider", "model", "agent_type",
    "stage_name", "operation", "result", "type", "stage", "le",
}


def _extract_metric_names(expr: str) -> set[str]:
    # Strip quoted strings (label values like "failed|error|timeout", "5..")
    cleaned = re.sub(r'"[^"]*"', '""', expr)
    candidates = re.findall(r"\b([a-z][a-z0-9_]*)\b", cleaned)
    return {
        c for c in candidates
        if c not in _PROMQL_KEYWORDS and c not in _LABEL_NAMES and len(c) >= 3
    }


def _resolve_base_metric(name: str) -> str:
    """Resolve a Prometheus-derived name (e.g. metric_bucket) to its base."""
    for suffix in ("_bucket", "_count", "_sum"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


class TestMetricNameReferences:
    def test_all_expressions_reference_known_metrics(self, all_exprs):
        for alert_name, expr in all_exprs:
            referenced = {_resolve_base_metric(n) for n in _extract_metric_names(expr)}
            unknown = referenced - KNOWN_METRICS
            assert not unknown, (
                f"Alert '{alert_name}' references unknown metrics: {unknown}. "
                f"Known: {sorted(KNOWN_METRICS)}"
            )

    def test_agent_failure_rate_uses_agent_runs_total(self, all_rules):
        rule = next(r for r in all_rules if r["alert"] == "AgentRunFailureRateHigh")
        assert "agent_runs_total" in rule["expr"]

    def test_agent_latency_uses_agent_run_duration(self, all_rules):
        rule = next(r for r in all_rules if r["alert"] == "AgentRunLatencyP95High")
        assert "agent_run_duration_seconds_bucket" in rule["expr"]

    def test_llm_fallback_uses_llm_requests_total(self, all_rules):
        rule = next(r for r in all_rules if r["alert"] == "LLMFallbackRateHigh")
        assert "llm_requests_total" in rule["expr"]

    def test_llm_error_uses_llm_requests_total(self, all_rules):
        rule = next(r for r in all_rules if r["alert"] == "LLMRequestErrorRateHigh")
        assert "llm_requests_total" in rule["expr"]

    def test_vector_search_uses_vector_search_total(self, all_rules):
        rule = next(r for r in all_rules if r["alert"] == "VectorSearchErrorRateHigh")
        assert "vector_search_total" in rule["expr"]

    def test_http_5xx_uses_http_requests_total(self, all_rules):
        rule = next(r for r in all_rules if r["alert"] == "HTTP5xxErrorRateHigh")
        assert "http_requests_total" in rule["expr"]


# ── Label value consistency ───────────────────────────────────────


class TestLabelValueConsistency:
    def test_agent_status_labels_match(self, label_selector_rules):
        rule = next(r for r in label_selector_rules if r["alert"] == "AgentRunFailureRateHigh")
        expr = rule["expr"]
        assert "failed" in expr
        assert "error" in expr
        assert "timeout" in expr

    def test_llm_status_labels_match(self, label_selector_rules):
        for alert_name in ("LLMFallbackRateHigh", "LLMRequestErrorRateHigh"):
            rule = next(r for r in label_selector_rules if r["alert"] == alert_name)
            assert "success" in rule["expr"] or "failed" in rule["expr"]

    def test_vector_search_status_labels_match(self, label_selector_rules):
        rule = next(r for r in label_selector_rules if r["alert"] == "VectorSearchErrorRateHigh")
        assert 'status="failed"' in rule["expr"]

    def test_http_status_regex_matches_code_labels(self, label_selector_rules):
        rule = next(r for r in label_selector_rules if r["alert"] == "HTTP5xxErrorRateHigh")
        assert 'status=~"5..' in rule["expr"]
