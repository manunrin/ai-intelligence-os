"""Tests for Grafana dashboard configuration validation."""

from __future__ import annotations

import json
import pathlib
import re

import pytest

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent.parent  # repo root
GRAFANA_DIR = ROOT_DIR / "monitoring" / "grafana"
DASHBOARDS_DIR = GRAFANA_DIR / "dashboards"
PROVISIONING_DIR = GRAFANA_DIR / "provisioning"
README_FILE = GRAFANA_DIR / "README.md"
ALERTS_DIR = ROOT_DIR / "monitoring" / "alerts"

# All known metric names from the application codebase
KNOWN_METRICS = {
    # HTTP
    "http_requests_total",
    "http_request_duration_seconds",
    # Agent runs
    "agent_runs_total",
    "agent_run_duration_seconds",
    "agent_stages_total",
    "agent_run_retries_total",
    # LLM
    "llm_requests_total",
    "llm_request_duration_seconds",
    # Embedding
    "embedding_requests_total",
    "embedding_request_duration_seconds",
    "embedding_batch_total",
    "embedding_batch_items_total",
    "embedding_batch_duration_seconds",
    # Vector search
    "vector_operations_total",
    "vector_operation_duration_seconds",
    "vector_search_total",
    "vector_search_duration_seconds",
}

# Prometheus label names used across all metrics
KNOWN_LABELS = {
    "status", "method", "path", "provider", "model", "agent_type",
    "stage_name", "operation", "result", "le", "trigger", "attempt",
}

# All PromQL functions used in dashboards
_PROMQL_FUNCS = {
    "sum", "rate", "histogram_quantile", "by", "le",
    "avg", "min", "max", "count", "increase",
}


def _extract_metric_names_from_promql(expr: str) -> set[str]:
    """Extract base metric names from a PromQL expression.

    Strips quoted strings and PromQL suffixes (_bucket, _count, _sum)
    to resolve back to the underlying metric name.
    """
    cleaned = re.sub(r'"[^"]*"', '""', expr)
    candidates = re.findall(r"\b([a-z][a-z0-9_]*)\b", cleaned)
    raw_metrics = {
        c for c in candidates
        if c not in _PROMQL_FUNCS and c not in KNOWN_LABELS and len(c) >= 3
    }
    # Resolve derived names (e.g. metric_bucket -> metric)
    return {_resolve_base_metric(n) for n in raw_metrics}


def _resolve_base_metric(name: str) -> str:
    for suffix in ("_bucket", "_count", "_sum"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


# ── Provisioning config tests ─────────────────────────────────────


class TestProvisioningConfig:
    def test_datasource_config_exists(self):
        assert (PROVISIONING_DIR / "datasources/prometheus.yml").exists()

    def test_dashboard_provisioner_config_exists(self):
        assert (PROVISIONING_DIR / "dashboards/default.yml").exists()

    def test_datasource_is_prometheus(self):
        import yaml
        with open(PROVISIONING_DIR / "datasources/prometheus.yml") as f:
            data = yaml.safe_load(f)
        ds = data["datasources"][0]
        assert ds["type"] == "prometheus"
        assert ds["name"] == "Prometheus"
        assert ds["isDefault"] is True

    def test_dashboard_provisioner_is_file_based(self):
        import yaml
        with open(PROVISIONING_DIR / "dashboards/default.yml") as f:
            data = yaml.safe_load(f)
        provider = data["providers"][0]
        assert provider["type"] == "file"
        assert "path" in provider["options"]


# ── Dashboard file existence ──────────────────────────────────────


EXPECTED_DASHBOARDS = {
    "ai_operations_overview.json": "AI Operations Overview",
    "agent_performance.json": "Agent Performance",
    "llm_rag_performance.json": "LLM & RAG Performance",
}


class TestDashboardFiles:
    @pytest.mark.parametrize("filename", EXPECTED_DASHBOARDS)
    def test_dashboard_file_exists(self, filename):
        assert (DASHBOARDS_DIR / filename).exists()

    def test_readme_exists(self):
        assert README_FILE.exists()

    def test_all_json_files_are_valid(self):
        for path in DASHBOARDS_DIR.glob("*.json"):
            with open(path) as f:
                data = json.load(f)
            assert isinstance(data, dict)

    def test_expected_dashboard_count(self):
        json_files = list(DASHBOARDS_DIR.glob("*.json"))
        assert len(json_files) == 3


# ── Dashboard JSON structure ──────────────────────────────────────


class TestDashboardStructure:
    @pytest.fixture(params=list(EXPECTED_DASHBOARDS.keys()))
    def dashboard(self, request):
        path = DASHBOARDS_DIR / request.param
        with open(path) as f:
            data = json.load(f)
        return data

    def test_has_title(self, dashboard):
        assert "title" in dashboard
        assert isinstance(dashboard["title"], str)
        assert len(dashboard["title"]) > 0

    def test_has_uid(self, dashboard):
        assert "uid" in dashboard
        assert isinstance(dashboard["uid"], str)
        assert len(dashboard["uid"]) > 0

    def test_has_panels(self, dashboard):
        assert "panels" in dashboard
        assert isinstance(dashboard["panels"], list)
        assert len(dashboard["panels"]) > 0

    def test_has_time_range(self, dashboard):
        assert "time" in dashboard
        assert "from" in dashboard["time"]
        assert "to" in dashboard["time"]

    def test_has_datasource_refs(self, dashboard):
        """Every panel references the prometheus datasource."""
        for panel in dashboard["panels"]:
            ds = panel.get("datasource", {})
            assert ds.get("type") == "prometheus" or any(
                t.get("type") == "prometheus"
                for t in panel.get("targets", [])
            ), f"Panel '{panel['title']}' missing prometheus datasource"

    def test_each_panel_has_title(self, dashboard):
        for panel in dashboard["panels"]:
            assert "title" in panel
            assert isinstance(panel["title"], str)
            assert len(panel["title"]) > 0

    def test_each_panel_has_targets(self, dashboard):
        for panel in dashboard["panels"]:
            assert "targets" in panel
            assert len(panel["targets"]) > 0

    def test_each_target_has_expr(self, dashboard):
        for panel in dashboard["panels"]:
            for target in panel["targets"]:
                assert "expr" in target
                assert isinstance(target["expr"], str)
                assert len(target["expr"].strip()) > 0

    def test_each_panel_has_gridpos(self, dashboard):
        for panel in dashboard["panels"]:
            assert "gridPos" in panel
            gp = panel["gridPos"]
            assert "h" in gp and "w" in gp and "x" in gp and "y" in gp


# ── Panel count per dashboard ─────────────────────────────────────


class TestPanelCounts:
    @pytest.fixture()
    def ai_ops_dashboard(self):
        with open(DASHBOARDS_DIR / "ai_operations_overview.json") as f:
            return json.load(f)

    @pytest.fixture()
    def agent_perf_dashboard(self):
        with open(DASHBOARDS_DIR / "agent_performance.json") as f:
            return json.load(f)

    @pytest.fixture()
    def llm_rag_dashboard(self):
        with open(DASHBOARDS_DIR / "llm_rag_performance.json") as f:
            return json.load(f)

    def test_ai_ops_has_7_panels(self, ai_ops_dashboard):
        assert len(ai_ops_dashboard["panels"]) == 7

    def test_agent_perf_has_8_panels(self, agent_perf_dashboard):
        assert len(agent_perf_dashboard["panels"]) == 8

    def test_llm_rag_has_11_panels(self, llm_rag_dashboard):
        assert len(llm_rag_dashboard["panels"]) == 11


# ── Required panels per dashboard ─────────────────────────────────


class TestRequiredPanels:
    @pytest.fixture()
    def ai_ops_dashboard(self):
        with open(DASHBOARDS_DIR / "ai_operations_overview.json") as f:
            return json.load(f)

    @pytest.fixture()
    def agent_perf_dashboard(self):
        with open(DASHBOARDS_DIR / "agent_performance.json") as f:
            return json.load(f)

    @pytest.fixture()
    def llm_rag_dashboard(self):
        with open(DASHBOARDS_DIR / "llm_rag_performance.json") as f:
            return json.load(f)

    def _get_panel_titles(self, dashboard):
        return {p["title"] for p in dashboard["panels"]}

    def test_ai_ops_http_throughput_panel(self, ai_ops_dashboard):
        titles = self._get_panel_titles(ai_ops_dashboard)
        assert any("HTTP Request Throughput" in t for t in titles)

    def test_ai_ops_5xx_error_rate_panel(self, ai_ops_dashboard):
        titles = self._get_panel_titles(ai_ops_dashboard)
        assert any("5xx Error Rate" in t for t in titles)

    def test_ai_ops_api_latency_panel(self, ai_ops_dashboard):
        titles = self._get_panel_titles(ai_ops_dashboard)
        assert any("API Latency" in t for t in titles)

    def test_ai_ops_agent_run_rate_panel(self, ai_ops_dashboard):
        titles = self._get_panel_titles(ai_ops_dashboard)
        assert any("Agent Run Success/Failure Rate" in t for t in titles)

    def test_ai_ops_active_agent_runs_panel(self, ai_ops_dashboard):
        titles = self._get_panel_titles(ai_ops_dashboard)
        assert any("Active Agent Runs" in t for t in titles)

    def test_ai_ops_llm_error_rate_panel(self, ai_ops_dashboard):
        titles = self._get_panel_titles(ai_ops_dashboard)
        assert any("LLM Error Rate" in t for t in titles)

    def test_ai_ops_llm_fallback_rate_panel(self, ai_ops_dashboard):
        titles = self._get_panel_titles(ai_ops_dashboard)
        assert any("LLM Fallback Rate" in t for t in titles)

    def test_agent_perf_by_type_panel(self, agent_perf_dashboard):
        titles = self._get_panel_titles(agent_perf_dashboard)
        assert any("Agent Runs by Agent Type" in t for t in titles)

    def test_agent_perf_success_failure_panel(self, agent_perf_dashboard):
        titles = self._get_panel_titles(agent_perf_dashboard)
        assert any("Success/Failure Distribution" in t for t in titles)

    def test_agent_perf_duration_panel(self, agent_perf_dashboard):
        titles = self._get_panel_titles(agent_perf_dashboard)
        assert any("Duration p50/p95" in t for t in titles)

    def test_agent_perf_stage_counts_panel(self, agent_perf_dashboard):
        titles = self._get_panel_titles(agent_perf_dashboard)
        assert any("Stage Execution Counts" in t for t in titles)

    def test_agent_perf_total_retries_panel(self, agent_perf_dashboard):
        titles = self._get_panel_titles(agent_perf_dashboard)
        assert any("Total Retries" in t for t in titles)

    def test_agent_perf_retries_by_attempt_panel(self, agent_perf_dashboard):
        titles = self._get_panel_titles(agent_perf_dashboard)
        assert any("Retries by Attempt Count" in t for t in titles)

    def test_agent_perf_dispatches_panel(self, agent_perf_dashboard):
        titles = self._get_panel_titles(agent_perf_dashboard)
        assert any("Scheduled vs User Dispatches" in t for t in titles)

    def test_llm_rag_provider_panel(self, llm_rag_dashboard):
        titles = self._get_panel_titles(llm_rag_dashboard)
        assert any("LLM Requests by Provider" in t for t in titles)

    def test_llm_rag_latency_panel(self, llm_rag_dashboard):
        titles = self._get_panel_titles(llm_rag_dashboard)
        assert any("LLM Request Latency" in t for t in titles)

    def test_llm_rag_fallback_panel(self, llm_rag_dashboard):
        titles = self._get_panel_titles(llm_rag_dashboard)
        assert any("Fallback Distribution" in t for t in titles)

    def test_llm_rag_embedding_panel(self, llm_rag_dashboard):
        titles = self._get_panel_titles(llm_rag_dashboard)
        assert any("Embedding Request" in t for t in titles)

    def test_llm_rag_vector_throughput_panel(self, llm_rag_dashboard):
        titles = self._get_panel_titles(llm_rag_dashboard)
        assert any("Vector Search Throughput" in t for t in titles)

    def test_llm_rag_vector_latency_panel(self, llm_rag_dashboard):
        titles = self._get_panel_titles(llm_rag_dashboard)
        assert any("Vector Search Latency" in t for t in titles)

    def test_llm_rag_vector_error_rate_panel(self, llm_rag_dashboard):
        titles = self._get_panel_titles(llm_rag_dashboard)
        assert any("Vector Search Error Rate" in t for t in titles)

    def test_llm_rag_embedding_batch_throughput_panel(self, llm_rag_dashboard):
        titles = self._get_panel_titles(llm_rag_dashboard)
        assert any("Embedding Batch Throughput" in t for t in titles)

    def test_llm_rag_embedding_batch_latency_panel(self, llm_rag_dashboard):
        titles = self._get_panel_titles(llm_rag_dashboard)
        assert any("Embedding Batch Latency" in t for t in titles)

    def test_llm_rag_vector_upsert_panel(self, llm_rag_dashboard):
        titles = self._get_panel_titles(llm_rag_dashboard)
        assert any("Vector Upsert Operations" in t for t in titles)

    def test_llm_rag_vector_upsert_latency_panel(self, llm_rag_dashboard):
        titles = self._get_panel_titles(llm_rag_dashboard)
        assert any("Vector Upsert Latency" in t for t in titles)


# ── Metric reference validation ───────────────────────────────────


class TestMetricReferences:
    @pytest.fixture(params=list(EXPECTED_DASHBOARDS.keys()))
    def dashboard(self, request):
        with open(DASHBOARDS_DIR / request.param) as f:
            return json.load(f)

    def test_all_referenced_metrics_exist(self, dashboard):
        """Every PromQL expr references a known metric."""
        for panel in dashboard["panels"]:
            for target in panel.get("targets", []):
                expr = target.get("expr", "")
                referenced = _extract_metric_names_from_promql(expr)
                unknown = referenced - KNOWN_METRICS
                assert not unknown, (
                    f"Panel '{panel['title']}' references unknown metrics: {unknown}. "
                    f"Known: {sorted(KNOWN_METRICS)}"
                )

    def test_no_unknown_label_values_in_selectors(self, dashboard):
        """Label selectors use only known label names."""
        import re as re_mod
        for panel in dashboard["panels"]:
            for target in panel.get("targets", []):
                expr = target.get("expr", "")
                # Extract label keys from {key op "value"} selectors
                # First find all {} blocks, then strip quoted values inside them,
                # then extract label keys before any operator.
                matches = re_mod.findall(r'\{([^}]*)\}', expr)
                for selector in matches:
                    # Strip quoted strings to avoid matching values as keys
                    cleaned = re_mod.sub(r'"[^"]*"', '', selector)
                    # Now extract label keys (word chars before an operator or comma)
                    keys_found = re_mod.findall(r'([a-z_][a-z0-9_]*)\s*[=~!]', cleaned)
                    for key in keys_found:
                        assert key in KNOWN_LABELS, (
                            f"Panel '{panel['title']}' uses unknown label: '{key}'"
                        )


# ── README documentation tests ────────────────────────────────────


class TestReadmeDocumentation:
    def test_readme_is_valid_markdown(self):
        content = README_FILE.read_text()
        assert len(content) > 100

    def test_readme_document_all_dashboards(self):
        content = README_FILE.read_text()
        for name in EXPECTED_DASHBOARDS.values():
            assert name in content, f"README missing documentation for '{name}'"

    def test_readme_document_all_metrics(self):
        """README panel mapping references all known metrics."""
        content = README_FILE.read_text()
        for metric in KNOWN_METRICS:
            assert metric in content, f"README missing metric: {metric}"

    def test_readme_has_datasource_instructions(self):
        content = README_FILE.read_text()
        assert "Prometheus" in content
        assert "datasource" in content.lower() or "Datasource" in content

    def test_readme_has_import_instructions(self):
        content = README_FILE.read_text()
        assert "Import" in content or "import" in content
