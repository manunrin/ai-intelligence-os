# Phase 10.1 Implementation Plan — Observability & Agent Runtime Persistence

**Parent:** Phase 10 (Agent Runtime & Production Hardening)  
**Date:** 2026-07-22  
**Scope:** P0 items only — Observability stack activation + Agent runtime persistence  
**Status:** Draft — awaiting approval  

---

## 1. Scope

Phase 10.1 delivers two foundational capabilities that unlock everything else in Phase 10:

1. **Observability Stack Activation** — Wire Prometheus + Grafana into Docker Compose so existing metrics/dashboards/alerts are actually reachable and renderable.
2. **Agent Runtime Persistence** — Make agent runs survive backend restarts via LangGraph PostgreSQL-backed checkpointing and a startup recovery scan.

Both are P0 in the Phase 10 plan. Neither requires new external credentials or UI work.

---

## 2. Task Breakdown

### Task 10.1.1 — Prometheus Service in Docker Compose

**Files:**
- `docker-compose.yml` — add `prometheus` service
- `monitoring/prometheus.yml` — scrape config targeting backend `/metrics`
- `.env` / `.env.example` — add `PROMETHEUS_SCRAPE_INTERVAL`

**What:**
- Add `prometheus` container with `prom/prometheus:latest` image
- Mount `monitoring/prometheus.yml` as config
- Mount `prometheus_data` volume for TSDB
- Scrape `http://backend:8000/metrics` every 30s
- Expose port 9090
- Healthcheck via `/-/healthy`

### Task 10.1.2 — Grafana Service in Docker Compose

**Files:**
- `docker-compose.yml` — add `grafana` service
- `monitoring/grafana/provisioning/datasources/prometheus.yml` — already exists, verify path
- `monitoring/grafana/provisioning/dashboards/default.yml` — already exists, verify path
- `.env` / `.env.example` — add `GRAFANA_ADMIN_PASSWORD`

**What:**
- Add `grafana` container with `grafana/grafana:latest` image
- Mount existing dashboard JSON files into `/var/lib/grafana/dashboards`
- Mount existing provisioning files into `/etc/grafana/provisioning`
- Set admin password via env var
- Depends on prometheus being healthy
- Expose port 3001 (avoid conflict with MinIO console on 9001)

### Task 10.1.3 — Verify Dashboards Render

**Files:**
- `monitoring/grafana/dashboards/agent_performance.json` — verify datasource UID matches provisioned Prometheus
- `monitoring/grafana/dashboards/ai_operations_overview.json` — same
- `monitoring/grafana/dashboards/llm_rag_performance.json` — same

**What:**
- Confirm all three dashboards reference datasource UID `prometheus` (matching provisioned datasource)
- Fix any mismatched UIDs
- Start stack, open Grafana at :3001, verify dashboards load without "no data" errors from datasource config

### Task 10.1.4 — Alert Rules Integration

**Files:**
- `monitoring/alerts/alerting_rules.yaml` — already exists
- `monitoring/prometheus.yml` — add alerting rule file reference

**What:**
- Reference `alerting_rules.yaml` in Prometheus config
- Verify alert expressions use metric names that actually exist in backend `/metrics`
- Cross-check: `agent_runs_total`, `agent_run_duration_seconds`, `llm_requests_total`, `llm_request_duration_seconds`, `vector_search_total` (may need to verify this metric exists)

### Task 10.1.5 — LangGraph Checkpointer Enablement

**Files:**
- `backend/workflows/graph/builder.py` — change `compile_intelligence_graph(checkpoint=True)` default
- `backend/workflows/executor.py` — pass compiled graph with checkpointer to executor
- `backend/config.py` — add `langgraph_checkpoint_db_url` setting (or reuse `database_url`)

**What:**
- LangGraph's `MemorySaver` is insufficient for production — need PostgreSQL-backed checkpointer
- Install `langgraph-checkpoint-postgres` dependency
- Create a `PostgresSaver` instance using the existing database connection
- Modify `compile_intelligence_graph()` to accept and apply the checkpointer
- Update both `intelligence` and `autonomous` pipeline compilation

### Task 10.1.6 — AgentRun Recovery Scan

**Files:**
- `backend/services/agent_runtime_service.py` — add `_recover_stale_runs()` method
- `backend/database/models/agent_run.py` — add `checkpoint_id` column, `recovered_at` timestamp
- Alembic migration `0003_agent_run_persistence`

**What:**
- On application startup, query `agent_runs` where status IN (`running`, `cancelling`)
- For each stale run:
  - Mark as `recovered` if checkpoint exists in LangGraph state store
  - Mark as `failed` with error message if no checkpoint found (run died before checkpointing)
- Update `AgentRun` model with `checkpoint_id` (nullable string UUID) and `recovered_at` (nullable datetime)
- Add recovery metric counter `agent_runs_recovered_total`

### Task 10.1.7 — Run Status Tracking Enhancement

**Files:**
- `backend/workflows/graph/callbacks.py` — extend to capture more granular events
- `backend/services/agent_runtime_service.py` — persist stage progress more frequently

**What:**
- Current callback captures node start/end/error but output summaries may be truncated
- Ensure stage progress is flushed to DB during long-running runs (not just at completion)
- Add `progress_percentage` field to stage progress tracking

### Task 10.1.8 — Tests

**Files:**
- `tests/unit/test_observability_stack.py` — test Prometheus config validity
- `tests/unit/test_agent_runtime_recovery.py` — test stale run detection and recovery logic
- `tests/integration/test_docker_compose_services.py` — test prometheus/grafana containers start

**What:**
- Unit tests for recovery scan logic
- Config validation tests for Prometheus scrape targets
- Integration test that verifies docker-compose services can start (if environment allows)

---

## 3. Dependencies & Order

```
Task 10.1.1 (Prometheus compose) ──→ Task 10.1.2 (Grafana compose) ──→ Task 10.1.3 (Dashboard verification)
       ↓                                                              ↓
Task 10.1.4 (Alert rules)                                      Task 10.1.8 (Tests)
                                                                ↑
Task 10.1.5 (LangGraph checkpointer) ──→ Task 10.1.6 (Recovery scan) ──┘
       ↓
Task 10.1.7 (Status tracking enhancement)
```

**Critical path:** 10.1.5 → 10.1.6 → 10.1.7 → 10.1.8

---

## 4. Database Migration

**Migration:** `0003_agent_run_persistence`

**Changes:**
```sql
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS checkpoint_id UUID;
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS recovered_at TIMESTAMPTZ;
CREATE INDEX idx_agent_runs_checkpoint ON agent_runs(checkpoint_id) WHERE checkpoint_id IS NOT NULL;
```

**Rationale:** `checkpoint_id` links an AgentRun to its LangGraph checkpoint state. `recovered_at` tracks when a stale run was successfully restored after a restart.

---

## 5. Docker Compose Changes

**Add to `services`:**

```yaml
  prometheus:
    image: prom/prometheus:latest
    container_name: aio-prometheus
    restart: unless-stopped
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
      - ./monitoring/alerts/alerting_rules.yaml:/etc/prometheus/alerts.yaml:ro
    ports:
      - "${PROMETHEUS_PORT:-9090}:9090"
    depends_on:
      backend:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:9090/-/healthy || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 10s
    networks:
      - ai-intelligence-net
    deploy:
      resources:
        limits:
          memory: 512M

  grafana:
    image: grafana/grafana:latest
    container_name: aio-grafana
    restart: unless-stopped
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-admin}
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards:ro
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning:ro
      - grafana_data:/var/lib/grafana
    ports:
      - "${GRAFANA_PORT:-3001}:3000"
    depends_on:
      prometheus:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:3000/api/health || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 30s
    networks:
      - ai-intelligence-net
    deploy:
      resources:
        limits:
          memory: 256M
```

**Add to `volumes`:**
```yaml
  prometheus_data:
    driver: local
  grafana_data:
    driver: local
```

**Add to `.env.example`:**
```
PROMETHEUS_PORT=9090
GRAFANA_PORT=3001
GRAFANA_ADMIN_PASSWORD=admin
PROMETHEUS_SCRAPE_INTERVAL=30s
```

---

## 6. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| `langgraph-checkpoint-postgres` not compatible with current LangGraph version | Checkpointer fails at compile time | Pin compatible versions in `pyproject.toml`; test with minimal graph first |
| Existing Grafana dashboards reference wrong datasource UID | Dashboards show "No Data" | Audit all dashboard JSON files for `datasource.uid` before enabling |
| Prometheus scrape breaks backend latency | Minor overhead (~1 req/30s) | Acceptable; can increase interval if needed |
| Recovery scan conflicts with new runs starting simultaneously | Race condition on status update | Use `UPDATE ... WHERE id = ? AND status IN (...)` with atomic conditions |
| Alert expressions reference non-existent metrics | Prometheus config invalid, won't start | Validate metric names against `backend/metrics.py` before deploying |

---

## 7. Success Criteria

- [ ] `make start` brings up Prometheus and Grafana alongside existing services
- [ ] Prometheus `/targets` shows backend as `UP`
- [ ] Grafana at `:3001` renders all 3 provisioned dashboards with real data
- [ ] Alert rules loaded in Prometheus (check `/api/v1/rules`)
- [ ] Backend startup recovers stale `running` agent runs correctly
- [ ] New agent runs have `checkpoint_id` populated after first node completes
- [ ] All new code has unit tests passing
- [ ] No regressions in existing 91 tests

---

## 8. Out of Scope for 10.1

- Executor retry/circuit breaker (10.2)
- Notification channels (10.2)
- Scheduler API (10.2)
- Refresh tokens (10.2)
- MCP bidirectional sync (10.3)
- Additional connectors (10.3)
- RBAC enforcement (10.3)
- Frontend pagination UI (10.3)
