# Monitoring

Observability configuration for the AI Intelligence OS platform.

## Components

- **Prometheus** — Metrics collection with labeled counters/histograms
- **Structured JSON logging** — Request-scoped log correlation via `request_id`
- **Frontend observability** — Client-side API latency and agent stream tracking

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/metrics` | GET | Prometheus text exposition format (all metrics) |
| `/metrics` | POST | Accept Prometheus-formatted metrics from clients |
| `/api/health` | GET | Readiness probe (DB + bootstrap state) |
| `/api/live` | GET | Liveness probe |

## HTTP Metrics

| Metric | Type | Labels | Source |
|--------|------|--------|--------|
| `http_requests_total` | counter | `method`, `status`, `path` | LogMiddleware |
| `http_request_duration_seconds` | histogram | `method`, `status`, `path` | LogMiddleware |

**Path normalization**: UUID segments in request paths are replaced with `<uuid>` to prevent cardinality explosion. E.g., `/api/v1/agents/runs/550e8400-.../stream` → `/api/v1/agents/runs/<uuid>/stream`.

## Agent Run Metrics

| Metric | Type | Labels | Source |
|--------|------|--------|--------|
| `agent_runs_total` | counter | `agent_type`, `status` (`submitted`/`completed`/`failed`/`cancelled`/`timeout`/`error`) | AgentRuntimeService |
| `agent_run_duration_seconds` | histogram | `agent_type`, `status` | AgentRuntimeService |
| `agent_stages_total` | counter | `stage_name` | AgentRuntimeService._persist_stages |

## LLM Metrics

| Metric | Type | Labels | Source |
|--------|------|--------|--------|
| `llm_requests_total` | counter | `provider`, `model`, `status` (`success`/`failed`) | LLMRouter |
| `llm_request_duration_seconds` | histogram | `provider`, `model`, `status` | LLMRouter |

## Embedding Metrics

| Metric | Type | Labels | Source |
|--------|------|--------|--------|
| `embedding_requests_total` | counter | `model`, `status` (`success`/`failed`) | EmbeddingClient |
| `embedding_request_duration_seconds` | histogram | `model`, `status` | EmbeddingClient |
| `embedding_batch_total` | counter | `model`, `status` | EmbeddingClient.embed_batch() |
| `embedding_batch_items_total` | counter | `model`, `result` (`success`/`failed`) | EmbeddingClient.embed_batch() |
| `embedding_batch_duration_seconds` | histogram | `model`, `status` | EmbeddingClient.embed_batch() |

## Vector Search Metrics

| Metric | Type | Labels | Source |
|--------|------|--------|--------|
| `vector_search_total` | counter | `status` (`success`/`failed`) | QdrantVectorService.search() |
| `vector_search_duration_seconds` | histogram | `status` | QdrantVectorService.search() |
| `vector_operations_total` | counter | `operation` (`upsert`), `status` | QdrantVectorService.upsert() |
| `vector_operation_duration_seconds` | histogram | `operation`, `status` | QdrantVectorService.upsert() |

## Frontend Metrics

| Metric | Type | Labels | Source |
|--------|------|--------|--------|
| `http_requests_total` | counter | `method`, `status`, `path` | api.ts request wrapper |
| `http_request_duration_seconds` | histogram | `method`, `status`, `path` | api.ts request wrapper |
| `agent_stream_events_total` | counter | `type` | useAgentStream hook |
| `agent_stage_duration_seconds` | histogram | `stage` | useAgentStream hook |

## Histogram Buckets

All backend histograms use configurable bucket boundaries. Default Prometheus standard buckets:

```
[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
```

Custom buckets can be passed via `histogram(name, value, buckets=(...))`. Output follows Prometheus text format with `_bucket{le="..."}` cumulative lines plus `_count`, `_sum`, and `_bucket{le="+Inf"}`.

## Logging

All log records are structured JSON with:

- `timestamp` — UTC ISO 8601
- `level` — INFO/WARNING/ERROR
- `logger` — module name
- `message` — formatted log message
- `request_id` — UUID for request correlation (injected by middleware)
- `duration_ms` — request duration (HTTP requests only)
- `method`, `path`, `status_code` — HTTP context (requests only)

The `X-Request-ID` header is echoed in responses and propagated to all log records within the request scope.
