# Monitoring

Observability configuration for the AI Intelligence OS platform.

## Components

- **OpenTelemetry** — Distributed tracing across all services
- **Prometheus** — Metrics collection and alerting thresholds
- **Grafana** — Dashboard definitions and alert rules

## Metrics

| Metric | Source | Description |
|--------|--------|-------------|
| `agent_execution_duration` | Agents | Time per agent node execution |
| `request_latency_ms` | Backend | HTTP request latency histogram |
| `db_pool_active` | Backend | Active database connections |
| `vector_search_latency_ms` | Qdrant | Semantic search query time |
