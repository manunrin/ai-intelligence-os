# Monitoring

Observability configuration for the AI Intelligence OS platform.

## Components

- **Prometheus** — Metrics collection and alerting thresholds
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
