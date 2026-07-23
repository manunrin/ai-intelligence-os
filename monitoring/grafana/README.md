# Grafana Dashboards

Pre-built Grafana dashboards for the AI Intelligence OS observability stack.

## Directory Structure

```
monitoring/grafana/
├── provisioning/
│   ├── datasources/prometheus.yml       # Prometheus datasource config
│   └── dashboards/default.yml           # Dashboard auto-loading config
├── dashboards/
│   ├── ai_operations_overview.json      # AI Operations Overview dashboard
│   ├── agent_performance.json           # Agent Performance dashboard
│   └── llm_rag_performance.json         # LLM & RAG Performance dashboard
└── README.md                            # This file
```

## Quick Start

### Docker Compose Setup

Add a Grafana service to `docker-compose.yml`:

```yaml
services:
  grafana:
    image: grafana/grafana:12.0.0
    container_name: aio-grafana
    restart: unless-stopped
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-admin}
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
      - grafana_data:/var/lib/grafana
    depends_on:
      - prometheus
    networks:
      - ai-intelligence-net
```

Add Prometheus (if not already present):

```yaml
  prometheus:
    image: prom/prometheus:v3.0.0
    container_name: aio-prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    networks:
      - ai-intelligence-net
```

Create `monitoring/prometheus/prometheus.yml`:

```yaml
global:
  scrape_interval: 30s

rule_files:
  - "/etc/prometheus/alerting_rules.yaml"

scrape_configs:
  - job_name: "backend"
    metrics_path: "/metrics"
    static_configs:
      - targets: ["backend:8000"]

  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]
```

Then run:

```bash
docker compose up -d prometheus grafana
```

Grafana will be available at `http://localhost:3001` (default credentials: `admin/admin`).

## Dashboards

### 1. AI Operations Overview (`ai-operations-overview`)

High-level system health at a glance.

| Panel | Metric | Type |
|-------|--------|------|
| HTTP Request Throughput | `http_requests_total` (rate by method) | Bar chart |
| HTTP 5xx Error Rate | `http_requests_total{status=~"5.."}` / total | Gauge |
| API Latency p95 | `http_request_duration_seconds_bucket` (histogram_quantile 0.95) | Bar chart |
| Agent Run Success/Failure Rate | `agent_runs_total` (by status) | Stacked bar |
| Active Agent Runs | `agent_runs_total{status="submitted"}` by type | Bar chart |
| LLM Error Rate | `llm_requests_total{status="failed"}` / total | Gauge |
| LLM Fallback Rate | `llm_requests_total{provider!="openai",status="success"}` / total | Gauge |

**Time range**: Last 1 hour, refresh every 30 seconds.

### 2. Agent Performance (`agent-performance`)

Deep dive into agent pipeline execution.

| Panel | Metric | Type |
|-------|--------|------|
| Agent Runs by Agent Type | `agent_runs_total` (rate by agent_type) | Stacked bar |
| Agent Success Rate | `agent_runs_total{status="completed"}` / total | Gauge |
| Agent Success/Failure Distribution | `agent_runs_total` (by agent_type + status) | Grouped bar |
| Agent Run Duration p50/p95 | `agent_run_duration_seconds_bucket` (histogram_quantile 0.50/0.95) | Bar chart |
| Agent Stage Execution Counts | `agent_stages_total` (rate by stage_name) | Bar chart |
| Total Retries (15m) | `agent_run_retries_total` (sum rate) | Stat |
| Retries by Attempt Count | `agent_run_retries_total` (rate by attempt) | Bar chart |
| Scheduled vs User Dispatches | `agent_runs_total{status="submitted"}` (rate by trigger) | Bar chart |

**Time range**: Last 1 hour, refresh every 30 seconds.

### 3. LLM & RAG Performance (`llm-rag-performance`)

LLM provider health, fallback patterns, and vector search metrics.

| Panel | Metric | Type |
|-------|--------|------|
| LLM Requests by Provider | `llm_requests_total` (rate by provider) | Stacked bar |
| LLM Request Latency | `llm_request_duration_seconds_bucket` (p50/p95) | Bar chart |
| LLM Fallback Distribution | `llm_requests_total` (by provider + status) | Stacked bar |
| Embedding Request Metrics | `embedding_requests_total` (by model + status) | Stacked bar |
| Vector Search Throughput | `vector_search_total` (success vs failed rate) | Bar chart |
| Vector Search Latency | `vector_search_duration_seconds_bucket` (p50/p95) | Bar chart |
| Vector Search Error Rate | `vector_search_total{status="failed"}` / total | Gauge |
| Embedding Batch Throughput | `embedding_batch_total` (rate by model) | Stacked bar |
| Embedding Batch Latency p50/p95 | `embedding_batch_duration_seconds_bucket` (histogram_quantile 0.50/0.95) | Bar chart |
| Vector Upsert Operations | `vector_operations_total` (rate by status) | Bar chart |
| Vector Upsert Latency p50/p95 | `vector_operation_duration_seconds_bucket` (histogram_quantile 0.50/0.95) | Bar chart |

## Datasource Configuration

The provisioning config creates a single Prometheus datasource named **Prometheus** accessible at `http://prometheus:9090`.

To use manually instead of provisioning:

1. Open Grafana → Settings → Data Sources → Add data source
2. Select **Prometheus**
3. Set URL to `http://<prometheus-host>:9090`
4. Save & Test

## Panel Metric Mapping Reference

All panels reference metrics defined in `backend/metrics.py` and instrumented across:

| Service | File | Metrics |
|---------|------|---------|
| HTTP middleware | `backend/routers/errors.py` | `http_requests_total`, `http_request_duration_seconds` |
| Agent runtime | `backend/services/agent_runtime_service.py` | `agent_runs_total`, `agent_run_duration_seconds`, `agent_stages_total`, `agent_run_retries_total` |
| LLM router | `backend/services/llm/router.py` | `llm_requests_total`, `llm_request_duration_seconds` |
| Embedding client | `backend/services/embedding/client.py` | `embedding_requests_total`, `embedding_request_duration_seconds`, `embedding_batch_total`, `embedding_batch_items_total`, `embedding_batch_duration_seconds` |
| Vector store | `backend/services/vector/qdrant.py` | `vector_search_total`, `vector_search_duration_seconds`, `vector_operations_total`, `vector_operation_duration_seconds` |

## Importing Dashboards Manually

If not using provisioning:

1. Open Grafana → Dashboards → New → Import
2. Upload the JSON file from `monitoring/grafana/dashboards/`
3. Select the **Prometheus** datasource
4. Click Import
