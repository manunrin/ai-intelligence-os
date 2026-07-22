# Phase 10 Implementation Plan — Agent Runtime & Production Hardening

**Author:** Agnes-2.5-Flash  
**Date:** 2026-07-22  
**Prerequisite:** Phase 9.6 Stabilization confirmed COMPLETE (`CURRENT_STATE.md` last updated 2026-07-22, HEAD `a7ce575`)  
**Status:** Draft — awaiting approval

---

## 1. Current State Assessment

### What Phase 9.6 Completed

| Item | Status | Notes |
|------|--------|-------|
| LiteLLM Gateway integration | ✅ Complete | Provider registered, fallback chain works, RAG returns 200 |
| Frontend auth flow | ✅ Complete | Middleware, login/register pages, auth context, token auto-attach |
| Backend stabilization | ✅ Complete | Qdrant error handling, empty SSE fix, hybrid RAG, bge-m3, frontend search hook |
| Unit test coverage | ✅ 91 tests passing | Across hooks, components, lib, knowledge service |
| Runtime verification | ✅ Mostly green | Embeddings populated, keyword/semantic/hybrid search all working, SSE streaming works |

### Remaining Known Issues (from CURRENT_STATE.md)

1. **No refresh tokens** — Access-only HS256 JWT, session dies on browser close
2. **No pagination UI** — Backend supports offset/limit, frontend has no controls
3. **Report PUT/DELETE not implemented** — Out of scope for Phase 6-D.1
4. **Notification channels are stubs** — Email/Telegram/WeChat log only
5. **LiteLLM Gateway needs API keys** — External dependency, not code defect
6. **Prometheus/Grafana not in Docker Compose** — Observability endpoints exist but no collectors
7. **Agent run execution partially wired** — AgentRuntimeService exists but executor is in-memory
8. **MCP servers are unidirectional** — Write tools exist but no change polling/sync
9. **Scheduler is in-memory only** — APScheduler BackgroundScheduler, no persistence or API
10. **RBAC is a foundation, not enforced** — `require_role` exists but no role checks on routes
11. **No standalone Articles/Tasks pages** — Only dashboard tabs
12. **Score visibility gap** — Hybrid scores exist in schema but router only exposes fused `score`

### Architecture Snapshot

```
User → Next.js (frontend/:3000) → FastAPI (backend/:8000) → LangGraph Workflows → AI Agents
                                     ↓                    ↓
                               PostgreSQL 16           MCP Servers (embedded)
                               Qdrant                  Notion/Asana/Browser/GitHub
                               Redis 7                 APScheduler (in-memory)
                               MinIO

Key files:
  backend/services/agent_runtime_service.py  — Run lifecycle, background tasks, cancellation
  backend/workflows/executor.py              — SyncExecutor (run_in_executor, inline event loop)
  backend/workflows/registry.py              — 2 pipelines: intelligence, autonomous
  backend/mcp/registry.py                    — Tool lookup by dotted name
  backend/workers/scheduler/scheduler.py     — APScheduler wrapper
  backend/connectors/base.py                 — SourceConnector abstract class
  backend/agents/notification/agent.py       — Stub notification dispatch
```

---

## 2. Phase 10 Goals

Phase 10 shifts the system from **"working prototype"** to **"operable production system"**. The focus is four pillars:

### Pillar A: Agent Runtime Reliability
Make agent runs durable, observable, and recoverable. Currently runs are in-memory background tasks with no persistence across restarts.

### Pillar B: Workflow Executor Evolution
Move beyond `SyncExecutor` to a pluggable executor model with retry, timeout, and async queue support.

### Pillar C: MCP & External Integrations
Expand from read/write stubs to real bidirectional integrations and additional data sources.

### Pillar D: Production Hardening
Observability stack, authentication hardening, permissions enforcement, task scheduling API, reliability patterns.

---

## 3. Priority Matrix

| Priority | Workstream | Why Now | Dependencies |
|----------|-----------|---------|--------------|
| **P0** | Runtime persistence (checkpointing) | Runs die on restart; no recovery | LangGraph checkpointer already imported but unused |
| **P0** | Observability stack (Prometheus + Grafana in Docker Compose) | We have metrics/endpoints but no way to view them | Phase 7 partial |
| **P1** | Executor retry + dead-letter | Failed runs are lost; no second chances | P0 runtime persistence |
| **P1** | Notification channels (real implementations) | NotificationAgent is the only output channel; currently logs only | None |
| **P1** | Scheduler API + persistence | No way to list/modify scheduled jobs; in-memory only | None |
| **P1** | Refresh tokens | Auth sessions are fragile; login required after every refresh | JWT foundation exists |
| **P2** | MCP bidirectional sync | Notion/Asana/GitHub tools write but don't poll for changes | MCP server framework exists |
| **P2** | Additional connectors (HN, arXiv) | Single RSS source limits intelligence coverage | Connector base class exists |
| **P2** | RBAC enforcement | `require_role` exists but unused | User model + roles exist |
| P3 | Pagination UI | Nice-to-have frontend polish | Backend pagination exists |
| P3 | Standalone Articles/Tasks pages | Navigation improvement | Data layer exists |

---

## 4. Technical Route by Workstream

### 4.1 Agent Runtime Persistence (P0)

**Problem:** `AgentRuntimeService._execute_run()` uses `asyncio.create_task()` with in-memory `_cancellation_tokens` and `_run_tasks`. If the backend restarts, all running/cancelled state is lost. The LangGraph builder already imports `MemorySaver` checkpointer but doesn't use it.

**Solution:**
- Enable LangGraph `checkpointer=True` in graph compilation (already wired in `compile_intelligence_graph(checkpoint=True)`)
- Use PostgreSQL-backed checkpointing instead of `MemorySaver` for durability
- Add `interrupt_before` / `interrupt_after` hooks for human-in-the-loop
- Persist `AgentRun.status` transitions to DB atomically with checkpoint writes
- Add a startup recovery scan: on backend init, query `agent_runs` where status IN (`running`, `cancelling`) and rehydrate or mark stale

**Files to modify:**
- `backend/workflows/graph/builder.py` — enable checkpointer
- `backend/workflows/executor.py` — pass checkpointer to compiled graph
- `backend/services/agent_runtime_service.py` — recovery scan, stale-run handling
- `backend/database/models/agent_run.py` — add `checkpoint_id` column, `recovered_at` field
- New migration `0003_agent_run_persistence`

### 4.2 Pluggable Executor with Retry (P1)

**Problem:** `SyncExecutor` runs everything in a single background thread via `run_in_executor`. No retry on transient failures, no queue capacity limits, no dead-letter.

**Solution:**
- Keep `Executor` protocol (already abstract), add `RetryExecutor` decorator
- Implement exponential backoff for LLM/provider failures (not for permanent errors)
- Add circuit breaker: if a provider fails N times in M seconds, skip it for cooldown
- Add `DeadLetterQueue` — failed runs persisted with error context, retryable via API
- Future: `RedisExecutor` for distributed queue (defer to Phase 11)

**Files to modify:**
- `backend/workflows/executor.py` — add `RetryExecutor`, `CircuitBreaker`
- `backend/services/agent_runtime_service.py` — wire retry config from settings
- `backend/config.py` — add retry/circuit-breaker settings
- `backend/routers/agents.py` — add `/runs/{id}/retry` endpoint
- New migration for dead-letter table or reuse `agent_runs` with `retry_count`

### 4.3 Notification Channels (P1)

**Problem:** `NotificationAgent._dispatch_notifications()` calls stub methods that only `logger.info()`. No real delivery.

**Solution:**
- Create `backend/services/notification/` with three providers:
  - **SMTP** — `aiosmtpd`/`aiosmtp` for outbound email; template rendering with Jinja2
  - **Telegram Bot** — `python-telegram-bot` or direct Bot API via httpx
  - **Slack Webhook** — incoming webhook URL, markdown→Blocks conversion
- Each provider implements `NotificationChannel` interface:
  ```python
  class NotificationChannel(ABC):
      name: str
      async def send(self, content: str, recipients: list[str]) -> bool
      async def validate(self) -> bool
  ```
- Channel registry (same pattern as MCPRegistry)
- `NotificationAgent` reads `channels` from input and dispatches to registered providers
- Config-driven: `NOTIFICATION_CHANNELS=email,telegram,slack`; per-channel credentials in `.env`
- Graceful degradation: failed channel logs warning, doesn't fail the pipeline

**Files to create:**
- `backend/services/notification/base.py`
- `backend/services/notification/smtp_channel.py`
- `backend/services/notification/telegram_channel.py`
- `backend/services/notification/slack_channel.py`
- `backend/services/notification/service.py`

### 4.4 Scheduler API & Persistence (P1)

**Problem:** `JobScheduler` is an in-memory APScheduler wrapper. No API to list/add/remove jobs. No persistence across restarts.

**Solution:**
- Store job definitions in a new `scheduled_jobs` PostgreSQL table:
  ```
  id, name, cron_expression, enabled, connectors_json, last_run_at, next_run_at, created_by, updated_by
  ```
- Replace in-memory `_jobs` dict with DB-backed job store
- Add API endpoints:
  - `GET /api/v1/scheduler/jobs` — list scheduled jobs
  - `POST /api/v1/scheduler/jobs` — create/update schedule
  - `DELETE /api/v1/scheduler/jobs/{id}` — remove schedule
  - `POST /api/v1/scheduler/jobs/{id}/trigger` — manual trigger
- Use APScheduler `BackgroundJobStore` (SQLAlchemy) instead of default memory store
- On startup, restore enabled jobs from DB

**Files to modify:**
- `backend/workers/scheduler/scheduler.py` — use SQLALchemyJobStore
- `backend/database/models/` — new `scheduled_job.py` model
- `backend/routers/` — new `scheduler.py` router
- `backend/services/` — `scheduler_service.py`
- New migration

### 4.5 Refresh Tokens (P1)

**Problem:** Only HS256 access tokens, 30-minute expiry. No refresh mechanism.

**Solution:**
- Add `refresh_tokens` table with `token_hash`, `user_id`, `device_info`, `expires_at`, `revoked_at`
- Issue refresh token alongside access token on login/register
- New endpoint: `POST /api/v1/auth/refresh` — validates refresh token, rotates, returns new pair
- New endpoint: `POST /api/v1/auth/logout` — revokes refresh token
- Access token remains HS256 (fast verification); refresh token uses same secret but longer-lived (7 days)
- Token rotation: each refresh issues a new refresh token and revokes the old one

**Files to modify:**
- `backend/database/models/user.py` — add refresh token relationship
- New model `backend/database/models/refresh_token.py`
- `backend/utils/jwt.py` — add refresh token generation/validation
- `backend/routers/auth.py` — add refresh/logout endpoints
- `backend/services/user_service.py` — refresh token CRUD
- New migration `0004_refresh_tokens`

### 4.6 MCP Bidirectional Sync (P2)

**Problem:** MCP tools are fire-and-forget writes. No polling for external changes.

**Solution:**
- Add `poll_interval` and `last_sync_state` to MCP server config
- New `MCPChangeWatcher` service that periodically calls read tools (e.g., `notion.query_database`, `github.list_issues`) and publishes events
- Event subscribers can update local knowledge/articles/tasks tables
- For Notion: watch database pages for updates, sync to knowledge_items
- For GitHub: watch repo issues/PRs, sync to articles or tasks
- Asana: mark completed tasks as done in local tasks table

**Files to create:**
- `backend/mcp/change_watcher.py`
- `backend/services/mcp_sync/service.py`

### 4.7 Additional Connectors (P2)

**Problem:** Only OpenAI Blog RSS connector exists.

**Solution:**
- **Hacker News** — Firebase API (no auth needed): `https://hacker-news.firebaseio.com/v0/topstories.json`
- **arXiv** — OAI-PMH or search API: `http://export.arxiv.org/api/query`
- Both extend `SourceConnector` base class
- Register in `ApplicationBootstrap.initialize()`
- Configurable via environment: `CONNECTOR_HN_ENABLED=true`, `CONNECTOR_ARXIV_ENABLED=true`
- arXiv supports category filtering (`cat:cs.ai`, etc.)

**Files to create:**
- `backend/connectors/api/hacker_news.py`
- `backend/connectors/api/arxiv.py`

### 4.8 Observability Stack (P0)

**Problem:** Metrics endpoint at `/metrics` exists. OpenTelemetry spans exist. But Prometheus and Grafana are NOT in Docker Compose. Dashboards are documented but never deployed.

**Solution:**
- Add `prometheus` service to `docker-compose.yml`:
  ```yaml
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
  ```
- Add `grafana` service:
  ```yaml
  grafana:
    image: grafana/grafana:latest
    volumes:
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
  ```
- Wire backend `/metrics` as Prometheus scrape target
- Deploy 3 Grafana dashboards from `docs/` as provisioned JSON
- Add alert rules: high error rate, slow agent runs, low disk, provider health

**Files to create:**
- `monitoring/prometheus.yml`
- `monitoring/grafana/provisioning/datasources.yml`
- `monitoring/grafana/provisioning/dashboards.yml`
- `monitoring/grafana/dashboards/agent-runtime.json`
- `monitoring/grafana/dashboards/system-health.json`
- `monitoring/grafana/dashboards/llm-provider.json`

---

## 5. Implementation Sequence

```
Week 1:
  ├─ 5.1 Observability stack (Docker Compose + provisioning) — quick win, unblocks validation
  ├─ 5.2 Runtime persistence (LangGraph checkpointer + DB recovery)
  └─ 5.3 Scheduler API + persistence

Week 2:
  ├─ 5.4 Executor retry + circuit breaker
  ├─ 5.5 Notification channels (SMTP, Telegram, Slack)
  └─ 5.6 Refresh tokens

Week 3:
  ├─ 5.7 MCP bidirectional sync (change watcher)
  ├─ 5.8 Additional connectors (HN, arXiv)
  └─ 5.9 RBAC enforcement (role checks on write endpoints)

Ongoing:
  └─ 5.10 Frontend polish (pagination UI, standalone pages) — can happen in parallel
```

This is a **3-week plan** assuming single developer pace. Can compress to 2 weeks by pairing:
- Observability + RBAC (both config/deploy heavy)
- Runtime persistence + Executor retry (both touch agent runtime)
- Notification + Connectors (both external integrations)

---

## 6. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| LangGraph PostgreSQL checkpointer compatibility | P0 runtime blocked | Use `langgraph-checkpoint-postgres`; test with simple graph first |
| APScheduler SQLAlchemyJobStore conflicts with async app | Scheduler broken | Use sync job store with separate engine, or stick with memory + DB metadata overlay |
| SMTP/Telegram providers need credentials before testing | Notification feature unverifiable locally | Implement with env-gated stubs like MCP servers; CI skips if no creds |
| Refresh token rotation breaks existing frontend | Auth flow regression | Keep access token cookie format; add refresh endpoint behind new path |
| MCP change watcher adds load to external APIs | Rate limit hits | Conservative polling intervals, configurable, respect `Last-Modified` headers |
| arXiv API is slow/unreliable | Connector failures cascade | Per-connector timeout, circuit breaker, failure isolation |

---

## 7. Success Criteria

Phase 10 is complete when:

- [ ] **Backend restarts don't lose agent run state** — recovery scan restores or marks stale
- [ ] **Failed agent runs are retryable** — `/runs/{id}/retry` endpoint works
- [ ] **Notifications actually deliver** — at least SMTP or Telegram sends real messages
- [ ] **Scheduled jobs are visible and manageable** — API lists/creates/removes triggers
- [ ] **Users can stay logged in** — refresh token rotates across 7-day window
- [ ] **Prometheus scrapes backend metrics** — `/metrics` endpoint reachable from Prometheus container
- [ ] **Grafana renders dashboards** — provisioned JSON loads on first start
- [ ] **New connectors produce articles** — HN and arXiv items appear in Articles tab
- [ ] **MCP change watcher polls** — Notion/GitHub read tools trigger sync events
- [ ] **All new code has tests** — unit tests for services, integration tests for endpoints

---

## 8. Out of Scope (Deferred to Phase 11+)

- Distributed executor (Celery/RQ) — `RedisExecutor` placeholder exists
- Kubernetes manifests / Helm charts — roadmap Phase 7 goal, not feasible at this scale
- CI/CD pipeline — infrastructure concern
- Load testing — requires production-like environment
- Security audit (OWASP) — too early, do after Phase 10 stabilizes
- Twitter/LinkedIn connectors — require credentials
- Password reset flow — auth hardening Phase 11
- Re-ranking with cross-encoder — Phase 9 was scoped out

---

*Plan ready for review. Awaiting confirmation to begin implementation.*
