# Alert Rules

Prometheus alerting rules for the AI Intelligence OS platform.

## Configuration

- **Rules file**: `alerting_rules.yaml` — loaded by Prometheus via `rule_files` in `prometheus.yml`
- **Group name**: `ai_intelligence_os_alerts`

## Alert Catalogue

### AgentRunFailureRateHigh — critical

| Field | Value |
|-------|-------|
| Expression | `sum(rate(agent_runs_total{status=~"failed\|error\|timeout"}[30m])) / sum(rate(agent_runs_total[30m])) > 0.05` |
| Severity | critical |
| For | 10m (must persist for 10 minutes before firing) |
| Description | Over the last 30 minutes, more than 5% of agent runs ended in failed, error, or timeout status. |
| Recommended Action | 1. Check `/metrics` for `agent_runs_total` breakdown by status.<br>2. Review structured JSON logs for error traces.<br>3. Verify pipeline definitions in `config/`.<br>4. Check downstream dependency health (LLM providers, vector store, Redis queue). |

### AgentRunLatencyP95High — warning

| Field | Value |
|-------|-------|
| Expression | `histogram_quantile(0.95, sum(rate(agent_run_duration_seconds_bucket{status="completed"}[15m])) by (le)) > 60` |
| Severity | warning |
| For | 10m |
| Description | Over the last 15 minutes, the p95 duration for completed agent runs exceeds 60 seconds. |
| Recommended Action | 1. Check `agent_run_duration_seconds` histogram buckets via `/metrics`.<br>2. Identify slowest `agent_type` using `histogram_quantile` by label.<br>3. Review stage-level timing from `agent_stages_total` and OpenTelemetry spans.<br>4. Consider increasing timeout budgets or optimizing slow pipeline stages. |

### LLMFallbackRateHigh — warning

| Field | Value |
|-------|-------|
| Expression | `sum(rate(llm_requests_total{provider!="openai", status="success"}[30m])) / sum(rate(llm_requests_total[30m])) > 0.25` |
| Severity | warning |
| For | 15m |
| Description | Over the last 30 minutes, more than 25% of successful LLM requests were served by non-default providers, indicating heavy fallback usage. |
| Recommended Action | 1. Check `llm_requests_total` by provider to identify fallback traffic.<br>2. Investigate primary provider (openai) health.<br>3. Review `llm_request_duration_seconds` for provider degradation.<br>4. If primary is consistently unavailable, consider permanent routing changes. |

### LLMRequestErrorRateHigh — critical

| Field | Value |
|-------|-------|
| Expression | `sum(rate(llm_requests_total{status="failed"}[10m])) / sum(rate(llm_requests_total[10m])) > 0.10` |
| Severity | critical |
| For | 5m |
| Description | Over the last 10 minutes, more than 10% of all LLM requests across all providers returned `status=failed`. |
| Recommended Action | 1. Check `llm_requests_total{status="failed"}` grouped by provider/model.<br>2. Review LLM provider API status pages and rate limit headers.<br>3. Verify API keys and credentials.<br>4. Check if all providers in the fallback chain are failing. |

### VectorSearchErrorRateHigh — warning

| Field | Value |
|-------|-------|
| Expression | `sum(rate(vector_search_total{status="failed"}[10m])) / sum(rate(vector_search_total[10m])) > 0.05` |
| Severity | warning |
| For | 5m |
| Description | Over the last 10 minutes, more than 5% of vector search operations failed. |
| Recommended Action | 1. Check Qdrant service health (container status, logs, `/api/health`).<br>2. Verify vector collection exists and is not corrupted.<br>3. Review embedding pipeline — stale embeddings can cause failures.<br>4. Check disk space on Qdrant storage volume. |

### HTTP5xxErrorRateHigh — critical

| Field | Value |
|-------|-------|
| Expression | `sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) > 0.05` |
| Severity | critical |
| For | 5m |
| Description | Over the last 5 minutes, more than 5% of all HTTP requests returned 5xx status codes. |
| Recommended Action | 1. Check application logs for stack traces.<br>2. Review `http_requests_total` by status and path to identify affected endpoints.<br>3. Verify database connectivity and connection pool health.<br>4. Check resource utilization (memory, CPU) on the backend container. |

## Metric-to-Alert Mapping

| Alert | Source Metrics |
|-------|---------------|
| AgentRunFailureRateHigh | `agent_runs_total` (counter) |
| AgentRunLatencyP95High | `agent_run_duration_seconds` (histogram) |
| LLMFallbackRateHigh | `llm_requests_total` (counter) |
| LLMRequestErrorRateHigh | `llm_requests_total` (counter) |
| VectorSearchErrorRateHigh | `vector_search_total` (counter) |
| HTTP5xxErrorRateHigh | `http_requests_total` (counter) |

## Prometheus Configuration Example

To wire these rules into your deployment, add to `prometheus.yml`:

```yaml
rule_files:
  - "monitoring/alerts/alerting_rules.yaml"

scrape_configs:
  - job_name: "backend"
    metrics_path: "/metrics"
    static_configs:
      - targets: ["backend:8000"]
```
