# Phase 6-F.4: Platform Hardening — Implementation Design

**Date:** 2026-07-17
**Status:** Draft — awaiting approval
**Preceded by:** Phase 6-F.3 (Agent Runtime)

---

## Executive Summary

Phase 6-F.3 delivered on-demand agent execution, SSE streaming, and per-stage observability. The foundation works for interactive use but is **not production-ready**: background runs die on restart, there is no persistent task queue, the scheduler conflicts with ASGI, and the entire intelligence pipeline (LLM routing, RAG, embeddings, vector search) has zero test coverage.

This design breaks F.4 into three sequential phases (F.4A, F.4B, F.4C) that address the highest-risk issues first while remaining backward-compatible with the F.3 API contract.

### Guiding Principles

1. **Preserve the Executor protocol** defined in F.3 — `SyncExecutor` already exists; we add `RQExecutor` alongside it, not replacing it.
2. **No breaking API changes** — all new endpoints are additive; existing responses keep their shape.
3. **Tests before code** — every backend change requires tests; frontend changes require Vitest coverage.
4. **Infrastructure before features** — the task queue must exist before any new agent feature ships.

---

## 1. Task Inventory

### 1.1 Architecture Changes

| # | Task | Risk | Breaking? | Depends On |
|---|------|------|-----------|------------|
| A1 | Replace global mutable engine state with app.state injection | Medium | No | — |
| A2 | Replace `sys.modules` service instantiation with FastAPI `Depends()` | Medium | No | A1 |
| A3 | Fix `ReportService._to_dict()` — populate real data or remove dead fields | Low | Yes (response shape) | — |
| A4 | Unify error envelope (`ErrorResponse` schema matches exception handler output) | Low | Yes (error format) | — |
| A5 | Fix UUID validation in schemas — use Pydantic `field_validator` | Low | Yes (error format: 500→422) | — |
| A6 | Rename duplicate `KnowledgeService` classes | Low | No | — |
| A7 | Fix `AsyncIOScheduler` → `BackgroundScheduler` | Low | No | — |
| A8 | Add pipeline registry pattern to replace string-based `PIPELINE_MAP` | Low | No | A2 |

### 1.2 Infrastructure

| # | Task | Risk | Breaking? | Depends On |
|---|------|------|-----------|------------|
| B1 | Integrate RQ as persistent task queue | High | No | — |
| B2 | Wire `RQExecutor` into `AgentRuntimeService` behind config flag | Medium | No | B1 |
| B3 | Add database indexes on FK columns and filter columns | Low | No (online-safe) | — |
| B4 | Add Redis health check to `/api/health` | Low | No | B1 |
| B5 | Add Qdrant and MinIO health checks to `/api/health` | Low | No | — |

### 1.3 Security

| # | Task | Risk | Breaking? | Depends On |
|---|------|------|-----------|------------|
| C1 | Rotate all committed credentials and remove `.env` from git history | Critical | No | — |
| C2 | Apply rate limiting to all POST/PUT/DELETE endpoints | Low | No | — |
| C3 | Add `OPTIONS` to CORS `allow_methods` | Low | No | — |
| C4 | Add `Content-Security-Policy` header | Low | No | — |
| C5 | Populate audit log with `ip_address`, `user_agent`, `request_id` | Low | No | — |
| C6 | Disable Swagger docs in production | Low | No | — |

### 1.4 Testing

| # | Task | Risk | Breaking? | Depends On |
|---|------|------|-----------|------------|
| D1 | Establish shared test fixtures in `conftest.py` (factories, fake sessions, `_make_client`) | Low | No | — |
| D2 | Test LLM router (routing rules, fallback chain, provider registration) | Low | No | — |
| D3 | Test RAG retriever and generator | Low | No | — |
| D4 | Test embedding client | Low | No | — |
| D5 | Test MCP server clients (Notion, Asana, Browser, GitHub) | Low | No | — |
| D6 | Test `AgentRuntimeService.submit/cancel/stream` with mocked executor | Low | No | — |
| D7 | Test `AgentRuntimeCallback` event emission | Low | No | — |
| D8 | Add API integration tests (router → service → repo → real DB via testcontainers) | Medium | No | D1 |
| D9 | Add migration reversibility tests | Low | No | — |

### 1.5 Performance

| # | Task | Risk | Breaking? | Depends On |
|---|------|------|-----------|------------|
| E1 | Add missing database indexes (FK + status/category columns) | Low | No | — |
| E2 | Share `httpx.AsyncClient` pool across LLM providers | Low | No | — |
| E3 | Add response caching for read-only list endpoints | Low | No | — |

---

## 2. Dependency Graph

```
┌─────────────────────────────────────────────────┐
│                    SECURITY                     │
│  C1 (rotate secrets) ─── independent ───────────┤
│  C2-C6 ────────────────────────────────────────┤
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│              ARCHITECTURE (A)                    │
│  A1 (global state → app.state) ─────────────────┤
│  A2 (DI via Depends) ───── A1 ──────────────────┤
│  A3 (ReportService fix) ─── independent ────────┤
│  A4 (Error envelope) ───── independent ────────┤
│  A5 (UUID validation) ─── independent ──────────┤
│  A6 (KnowledgeService rename) ─ independent ────┤
│  A7 (Scheduler fix) ───── independent ──────────┤
│  A8 (Pipeline registry) ─ A2 ───────────────────┤
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│             INFRASTRUCTURE (B)                   │
│  B1 (RQ integration) ─── independent ───────────┤
│  B2 (RQExecutor) ─────── B1 ────────────────────┤
│  B3 (DB indexes) ─────── independent ───────────┤
│  B4-B5 (health checks) ─ independent ───────────┤
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│                 TESTING (D)                      │
│  D1 (shared fixtures) ─ independent ────────────┤
│  D2-D6 ─────────────── D1 ──────────────────────┤
│  D7 (callback test) ─ D1 ───────────────────────┤
│  D8 (integration) ──── D1, B1 ──────────────────┤
│  D9 (migration tests) ─ independent ────────────┤
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│               PERFORMANCE (E)                    │
│  E1 (indexes) ──────── independent ─────────────┤
│  E2 (shared httpx pool) ─ A1 ───────────────────┤
│  E3 (response cache) ─ B1 (Redis) ──────────────┤
└─────────────────────────────────────────────────┘
```

---

## 3. Phased Roadmap

### Phase 6-F.4A: Foundation & Security (Week 1-2)

**Goal:** Eliminate critical risks and establish a stable base for all subsequent work.

#### Task C1: Credential Rotation (Critical)

**Why first:** Live Notion and Asana tokens are committed in `.env`. Any public push compromises external integrations.

**Scope:**
- `git filter-branch` or `git filter-repo` to remove `.env` from history
- Rotate Notion token, Asana token, JWT secret, database password
- Add `.env` to `.gitignore` (verify it is already there)
- Add pre-commit hook to block `.env` commits

**Risk:** Low — mechanical operation. Must be done carefully to avoid corrupting history.

**Breaking changes:** None to API.

---

#### Task A1: Global State → app.state (High)

**Current problem:** `backend/database/connection.py` uses module-level globals (`_engine`, `_session_factory`) typed as `type | None` instead of actual engine types. This prevents testing multiple app instances and causes thread-safety issues.

**Design:**

```python
# backend/database/connection.py
# BEFORE (current):
_engine: type | None = None
_session_factory: type | None = None

def create_engine_for_settings(settings: Settings):
    global _engine, _session_factory
    _engine = create_async_engine(...)
    ...

# AFTER:
def create_engine_for_settings(settings: Settings):
    """Create engine and return (engine, session_factory). Caller stores in app.state."""
    engine = create_async_engine(...)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, factory
```

**Files modified:**
- `backend/database/connection.py` — return engine+factory instead of storing globally
- `backend/main.py:lifespan` — store returned values in `app.state.engine`, `app.state.session_factory`
- `backend/routers/deps.py:get_db` — read from `request.app.state.session_factory`
- `backend/services/agent_runtime_service.py:_gsf import` — read from `request.app.state.session_factory`

**Dependencies:** None. This is a pure refactoring — same behavior, different storage location.

**Risk:** Medium — touches every file that imports from `connection.py`. Must verify all paths.

**Breaking changes:** None. External API unchanged.

---

#### Task A7: Scheduler Fix (Medium)

**Current problem:** `JobScheduler.start()` creates `AsyncIOScheduler()` which calls `asyncio.run()` internally — conflicts with the ASGI event loop.

**Design:**

```python
# backend/workers/scheduler/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler  # NOT AsyncIOScheduler

class JobScheduler:
    def start(self):
        self._scheduler = BackgroundScheduler()
        self._scheduler.start()
```

**Risk:** Low — single file change. `BackgroundScheduler` runs in a daemon thread, safe inside ASGI.

**Breaking changes:** None. Scheduler interface unchanged.

---

#### Task C2: Rate Limit All Write Endpoints (High)

**Current problem:** Only `/register` and `/login` are rate-limited. All CRUD endpoints (articles, tasks, knowledge, reports, agents) accept unlimited writes.

**Design:**

```python
# backend/rate_limiter.py — add endpoint-specific limits
ENDPOINT_LIMITS = {
    "/api/v1/articles": "100/hour",
    "/api/v1/tasks": "100/hour",
    "/api/v1/knowledge": "100/hour",
    "/api/v1/reports": "50/hour",
    "/api/v1/agents/run": "20/hour",
    "/api/v1/agents/runs/*/cancel": "10/hour",
}

# In each router, apply limiter via decorator or middleware
# Prefer middleware approach to avoid touching every endpoint:
# RateLimitMiddleware reads X-Forwarded-For for proxy awareness
```

**Files modified:**
- `backend/rate_limiter.py` — add endpoint configuration, switch to `X-Forwarded-For` key function
- `backend/main.py` — ensure slowapi is configured with proper key function

**Risk:** Low — additive change. Existing rate-limited endpoints continue working.

**Breaking changes:** None. Clients that were hammering endpoints will now be throttled (desired behavior).

---

#### Task C3: CORS OPTIONS Method (Low)

**File:** `backend/main.py:122`

Add `"OPTIONS"` to `allow_methods`. Simple one-line change.

**Risk:** Trivial.

---

#### Task C4: Content-Security-Policy Header (Medium)

**File:** `backend/routers/security_headers.py`

Add `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self' ${API_BASE};` to security headers middleware.

**Risk:** Low — CSP can be conservative initially. May need tuning if third-party scripts are loaded.

**Breaking changes:** Potentially blocks inline scripts if any exist in frontend. Audit frontend for `<script>` tags.

---

#### Task C5: Audit Log Enrichment (Low)

**Files:**
- `backend/routers/errors.py:LogMiddleware` — capture `X-Forwarded-For`, `User-Agent`, `X-Request-ID`
- `backend/events/subscriber.py:AuditLogSubscriber.handle()` — pass captured metadata to `AuditLog` creation
- `backend/database/models/audit_log.py` — verify `ip_address`, `user_agent` columns exist (they do)

**Risk:** Low — additive field population. Existing audit records unaffected.

---

#### Task C6: Disable Swagger in Production (Low)

**File:** `backend/main.py:67-68`

```python
docs_url="/api/docs" if settings.app_env != "production" else None,
redoc_url="/api/redoc" if settings.app_env != "production" else None,
```

**Risk:** Trivial.

---

#### Task A3: ReportService._to_dict() Fix (Medium)

**Current problem:** Returns hardcoded nulls for `research_result`, `analysis_result`, `translation_result` and empty lists for `knowledge_items`, `tasks`. These fields are advertised in the response schema but never populated.

**Two options:**

**Option A (Recommended):** Remove the dead fields from the response. They were never implemented and adding them now would require joining 3 unrelated tables (intelligence_reports ↔ agent_runs ↔ knowledge_items/tasks).

```python
# backend/schemas/report.py — remove research_result, analysis_result,
# translation_result, knowledge_items, tasks from IntelligenceReportResponse
```

**Option B:** Populate them by querying related models. This is a large refactor with uncertain value.

**Risk:** Medium — Option A is a breaking change (response shape shrinks). Option B is high effort.

**Breaking changes:** Option A removes fields from API responses. Frontend types in `frontend/types/index.ts` must be updated.

---

#### Task A4: Error Envelope Unification (Medium)

**Current problem:** Exception handlers return `{success, data, error}` but `ErrorResponse` schema has `{code, message, details}`. Clients see two formats.

**Design:** Make exception handlers return the `ErrorResponse` schema:

```python
# backend/routers/errors.py
@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc):
    errors = []
    for err in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in err["loc"]),
            "message": err["msg"],
            "type": err["type"],
        })
    return JSONResponse(
        status_code=422,
        content={"code": "VALIDATION_ERROR", "message": "Request validation failed", "details": errors},
    )
```

**Risk:** Medium — changes error format for all validation failures. Frontend `api.ts` error parsing must adapt.

**Breaking changes:** Yes — error response format changes from `{success, data, error}` to `{code, message, details}`.

---

#### Task A5: UUID Validation in Schemas (Low)

**Current problem:** `source_id`, `agent_run_id`, `knowledge_item_id` declared as `str` — invalid UUIDs cause 500 errors in service layer.

**Design:**

```python
from pydantic import field_validator
import uuid as _uuid

class ArticleCreate(BaseModel):
    source_id: str = Field(...)

    @field_validator("source_id")
    @classmethod
    def validate_uuid(cls, v):
        try:
            _uuid.UUID(v)
        except ValueError:
            raise ValueError("Must be a valid UUID")
        return v
```

Apply to all schemas with UUID fields: `article_create.py`, `report_create.py`, `task_create.py`, `knowledge_create.py`.

**Risk:** Low — converts 500 → 422. Better UX, no behavioral change for valid input.

**Breaking changes:** Minor — error format changes from 500 to 422 for invalid UUIDs.

---

#### Task A6: KnowledgeService Rename (Low)

**Current files:**
- `backend/services/knowledge_service.py` → rename to `backend/services/knowledge_crud_service.py`
- `backend/services/knowledge/service.py` → rename to `backend/services/knowledge_pipeline_service.py`

Update all imports in routers and workflow nodes.

**Risk:** Low — mechanical rename + import updates.

**Breaking changes:** None to API.

---

#### Task A8: Pipeline Registry (Low)

**Current problem:** `PIPELINE_MAP` in `agent_runtime_service.py` uses string module paths resolved via `importlib`. Typos not caught at import time.

**Design:**

```python
# backend/workflows/registry.py
from .daily_intelligence import compile_intelligence_graph
from .autonomous_intelligence import compile_autonomous_intelligence

PIPELINE_REGISTRY: dict[str, PipelineFactory] = {
    "intelligence": compile_intelligence_graph,
    "autonomous": compile_autonomous_intelligence,
}

# backend/services/agent_runtime_service.py
# BEFORE:
module_path = PIPELINE_MAP[pipeline_type]  # string path
mod = importlib.import_module(mod_path)     # runtime resolution

# AFTER:
graph_builder = PIPELINE_REGISTRY[pipeline_type]  # direct reference
def factory():
    return graph_builder()
```

**Risk:** Low — import-time validation catches typos immediately.

**Breaking changes:** None.

---

### Phase 6-F.4B: Persistent Task Queue (Week 2-3)

**Goal:** Replace `asyncio.create_task()` with RQ so agent runs survive process restarts.

#### Task B1: RQ Integration (High)

**Decision rationale:** RQ was chosen over Celery because:
- Single dependency (`rq`), no message broker needed beyond Redis (already configured)
- Simpler operational footprint — no flower dashboard, beat scheduler, or worker autoscaling
- Easy migration path: swap `SyncExecutor` for `RQExecutor` behind a config flag
- Compatible with existing `redis` dependency

**Files to create:**

```
backend/workers/rq/
  __init__.py          — RQ connection helper
  worker.py            — rq worker entry point (for docker-compose)
  jobs.py              — RQ job functions that wrap SyncExecutor/RQExecutor
```

**Design:**

```python
# backend/workers/rq/jobs.py
import uuid
from datetime import datetime, timezone
from rq import get_current_job

from backend.database.connection import get_session_factory
from backend.services.agent_runtime_service import AgentRuntimeService
from backend.workflows.executor import SyncExecutor

def execute_agent_run(
    run_id: str,
    pipeline_type: str,
    state: dict,
    timeout_seconds: int,
) -> None:
    """RQ job: executes an agent run in a separate worker process."""
    session_factory = get_session_factory()
    service = AgentRuntimeService(session_factory)  # uses factory, not request session
    executor = SyncExecutor()

    # Delegate to existing service method (extracted from _execute_run)
    # This reuses all existing lifecycle logic
    ...
```

**Docker Compose addition:**

```yaml
services:
  rq_worker:
    build:
      context: .
      dockerfile: Dockerfile.backend
    command: rq worker ai-intelligence -u ${REDIS_URL} --results-ttl 300
    environment:
      - DATABASE_URL=...
      - REDIS_URL=...
    depends_on:
      - redis
      - postgres
    deploy:
      resources:
        limits:
          memory: 2G
```

**Risk:** Medium — adds a new process to the architecture. Must verify Redis connectivity and worker lifecycle.

**Breaking changes:** None. The `Executor` protocol is unchanged; we just add a new implementation.

---

#### Task B2: Wire RQExecutor into AgentRuntimeService (Medium)

**Design:**

```python
# backend/services/agent_runtime_service.py
from ..workflows.executor import Executor, SyncExecutor, RQExecutor

class AgentRuntimeService:
    def __init__(self, session_or_factory, *, use_rq: bool | None = None):
        ...
        if use_rq is None:
            use_rq = settings.app_env == "production"
        self._executor: Executor = RQExecutor() if use_rq else SyncExecutor()

    async def submit(self, ...):
        ...
        if isinstance(self._executor, RQExecutor):
            await self._executor.enqueue(...)  # pushes to RQ queue
        else:
            bg_task = asyncio.create_task(self._execute_run(...))
```

**Config flag:** `USE_RQ=true` in `.env` for production. Defaults to `false` for development.

**Risk:** Medium — dual-path execution. Must test both paths thoroughly.

**Breaking changes:** None. API response identical regardless of executor type.

---

#### Task D6: Test AgentRuntimeService (Low)

Unit tests for `submit()`, `cancel_run()`, `stream_events()` using mocked executor.

**File:** `tests/unit/services/test_agent_runtime_service.py`

---

### Phase 6-F.4C: Test Foundation (Week 3-4)

**Goal:** Establish test infrastructure and cover the intelligence pipeline.

#### Task D1: Shared Test Fixtures (Low)

**Consolidate duplicated patterns across 6+ test files:**

```python
# tests/conftest.py
import pytest
from unittest.mock import MagicMock, AsyncMock
import uuid
from datetime import datetime, timezone, timedelta

@pytest.fixture
def fake_user():
    user = MagicMock()
    user.id = uuid.uuid4()
    user.username = "testuser"
    user.role = "user"
    user.is_active = True
    return user

@pytest.fixture
def fake_article():
    """Create a minimal Article ORM mock."""
    article = MagicMock()
    article.id = uuid.uuid4()
    article.title = "Test Article"
    article.status = "raw"
    article.user_id = uuid.uuid4()
    article.created_at = datetime.now(timezone.utc)
    return article

@pytest.fixture
def fake_session():
    """AsyncMock session that mimics SQLAlchemy session methods."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session

@pytest.fixture
def test_client(fake_user, monkeypatch):
    """TestClient with auth override, shared across all router tests."""
    from fastapi.testclient import TestClient
    from backend.main import create_app
    from backend.routers.deps import get_current_user

    async def mock_get_current_user():
        return fake_user

    app = create_app()
    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield TestClient(app)
    app.dependency_overrides.clear()
```

Remove duplicated `_make_client()`, `FakeSessionCtx`, `TrackingService` from all individual test files.

**Risk:** Low — purely additive fixtures. Existing tests continue to work.

**Breaking changes:** None. Individual test files can be migrated incrementally.

---

#### Task D2: LLM Router Tests (Low)

**File:** `tests/unit/services/llm/test_router.py`

Test cases:
- Provider registration with API keys
- Routing by explicit model string (`openai/gpt-4o`, `anthropic/claude-sonnet`)
- Routing by task name (`summary`, `translation`)
- Default provider fallback
- Fallback chain execution (primary fails → secondary succeeds)
- All providers fail → raises `RuntimeError`
- Health check returns provider statuses
- Missing config file → uses defaults
- Unknown provider in model string → logs warning, uses default

**Mocks:** Each provider's `chat()` and `embedding()` methods.

---

#### Task D3: RAG Tests (Low)

**File:** `tests/unit/services/rag/test_retriever.py`, `test_generator.py`

Test cases for retriever:
- Query construction from topic/focus areas
- Vector store interaction (mock Qdrant)
- Chunk retrieval and ranking
- Empty result handling

Test cases for generator:
- Prompt assembly from retrieved chunks
- LLM client invocation
- Response parsing
- Error handling when LLM fails

---

#### Task D4: Embedding Client Tests (Low)

**File:** `tests/unit/services/embedding/test_client.py`

Test cases:
- Text chunking (size limits, overlap)
- Batch embedding requests
- Provider selection
- Retry on transient failure
- Rate limit backoff

---

#### Task D5: MCP Client Tests (Low)

**File:** `tests/unit/mcp/servers/test_notion_client.py`, etc.

Test cases per server:
- Authentication (token/env var validation)
- Tool call with mock HTTP responses
- Error handling (401, 404, 500)
- Timeout handling
- Token refresh (if applicable)

---

#### Task D7: Callback Tests (Low)

**File:** `tests/unit/workflows/graph/test_callbacks.py`

Test `AgentRuntimeCallback`:
- `on_chain_start` → appends StageEvent with phase="start"
- `on_chain_end` → appends StageEvent with phase="end", outputs
- `on_chain_error` → appends StageEvent with phase="error", error_message
- Tool events → ignored (pass-through)
- Node name extraction from serialized dict

---

#### Task D8: API Integration Tests (Medium)

**File:** `tests/integration/test_api.py`

Use `testcontainers` or `pytest-postgresql` for a real PostgreSQL instance:

```python
@pytest.mark.integration
@pytest.fixture
def integration_db():
    """Spin up real PostgreSQL for integration tests."""
    from testcontainers.postgres import PostgresContainer
    with PostgresContainer("postgres:16-alpine") as pg:
        url = pg.get_connection_url()
        # Run migrations
        yield url
```

Test full stack: router → service → repository → real DB → response parsing.

---

#### Task D9: Migration Reversibility Tests (Low)

**File:** `tests/integration/test_migrations.py`

```python
@pytest.mark.integration
def test_migration_0001_reversible():
    """Verify alembic downgrade/upgrade cycle works."""
    ...

@pytest.mark.integration
def test_clean_database_upgrade():
    """Verify migrations work from scratch."""
    ...
```

---

### Phase 6-F.4D: Performance & Polish (Week 4-5)

**Goal:** Address performance bottlenecks and finalize the platform.

#### Task E1: Database Indexes (Low)

**Migration:** `0008_add_performance_indexes`

```sql
-- Foreign key indexes
CREATE INDEX idx_articles_source_id ON articles(source_id);
CREATE INDEX idx_agent_runs_agent_id ON agent_runs(agent_id);
CREATE INDEX idx_agent_runs_workflow_id ON agent_runs(workflow_id);
CREATE INDEX idx_reports_agent_run_id ON intelligence_reports(agent_run_id);
CREATE INDEX idx_tasks_agent_run_id ON tasks(agent_run_id);
CREATE INDEX idx_tasks_knowledge_item_id ON tasks(knowledge_item_id);
CREATE INDEX idx_knowledge_items_source_id ON knowledge_items(source_id);
CREATE INDEX idx_knowledge_items_article_id ON knowledge_items(article_id);
CREATE INDEX idx_knowledge_items_report_id ON knowledge_items(report_id);

-- Filter column indexes
CREATE INDEX idx_articles_status ON articles(status);
CREATE INDEX idx_agent_runs_status ON agent_runs(status);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_priority ON tasks(priority);
CREATE INDEX idx_knowledge_items_kind ON knowledge_items(kind);
```

**Risk:** Low — `CREATE INDEX CONCURRENTLY` for online safety.

**Breaking changes:** None.

---

#### Task E2: Shared httpx Pool (Low)

**Current problem:** Each `LLMProvider` creates its own `httpx.AsyncClient` with no shared connection pool.

**Design:** Create a shared pool at application startup:

```python
# backend/main.py lifespan
app.state.httpx_pool = httpx.AsyncClient(
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    timeout=httpx.Timeout(30.0),
)

# Each provider receives the pool or shares a global client
```

**Risk:** Low — additive change. Existing per-provider clients remain until migrated.

---

#### Task E3: Response Caching (Low)

**Design:** Use Redis-backed caching for read-only list endpoints:

```python
# backend/routers/articles.py
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

@router.get("/articles", response_model=APIResponse[list[ArticleResponse]])
@cache_control(ttl=60)  # 60-second cache
async def list_articles(...):
    ...
```

**Risk:** Low — cache miss falls through to normal behavior.

**Breaking changes:** None. Responses may be slightly stale (≤60s).

---

#### Task B3-B5: Health Check Extensions (Low)

Extend `/api/health` to check Redis, Qdrant, and MinIO in addition to PostgreSQL.

**File:** `backend/main.py:health_check()`

---

### Phase 6-F.4E: Frontend Foundation (Week 5-6)

**Goal:** Split the monolithic page, add form library, establish test infrastructure.

#### Task F1: Route Extraction from page.tsx (Medium)

**Current problem:** `frontend/app/page.tsx` (307 lines) manages all tabs, modals, data fetching, and mutations.

**Design:** Create route pages using Next.js App Router:

```
frontend/app/dashboard/
  page.tsx           — Tab navigation shell (tabs array moved here)
  layout.tsx         — Auth guard + header
  articles/
    page.tsx         — ArticlesPanel + article modal
    new/page.tsx     — Create article form (optional deep link)
  knowledge/
    page.tsx         — KnowledgePanel + knowledge modal
  tasks/
    page.tsx         — TasksPanel + task modal
  agents/
    page.tsx         — AgentsPanel only (no modals)
  reports/
    page.tsx         — ReportsPanel + report modal
```

Each page fetches only its own data. Tab navigation becomes route navigation (`/dashboard/articles`, `/dashboard/tasks`, etc.).

**Risk:** Medium — changes URL structure. Bookmarked URLs will break. Mitigate with a redirect route.

**Breaking changes:** Yes — URL structure changes. Add a catch-all `/dashboard/*` redirect.

---

#### Task F2: Form Library (React Hook Form + Zod) (Medium)

**Current problem:** 4 form components with ~200 lines of duplicated state management.

**Design:**

```bash
cd frontend && npm install react-hook-form zod @hookform/resolvers
```

Create generic form hook:

```typescript
// frontend/hooks/useEntityForm.ts
export function useEntityForm<T extends Record<string, unknown>>(
  schema: z.ZodType<T>,
  initialData?: T | null,
  onSubmit: (data: T) => Promise<void>,
) {
  const form = useForm<T>({
    resolver: zodResolver(schema),
    defaultValues: initialData ?? ({} as T),
  });
  // handleSubmit, loading, error handling built-in
}
```

**Risk:** Medium — new dependency, migration of 4 forms.

**Breaking changes:** None to API. UI behavior identical.

---

#### Task F3: Frontend Type Safety (Low)

**Current problem:** All types use `& Record<string, unknown>` band-aid and bare `string` for enums.

**Design:**

```typescript
// frontend/types/index.ts
export type ArticleStatus = "raw" | "analyzed" | "translated" | "error";
export type TaskPriority = "low" | "medium" | "high" | "critical";
export type TaskStatus = "pending" | "in_progress" | "completed" | "cancelled";
export type KnowledgeKind = "concept" | "entity" | "relationship" | "event";

export interface Article {
  id: string;
  title: string;
  summary: string | null;
  content: string | null;
  url: string | null;
  source: string;
  language: string;
  tags: string[];
  status: ArticleStatus;
  fetched_at: string;
  published_at: string | null;
  user_id: string | null;
}
// Remove & Record<string, unknown> from all types
```

Also update mutation bodies to use typed schemas instead of `Record<string, unknown>`.

**Risk:** Low — purely additive type constraints.

**Breaking changes:** None.

---

#### Task F4: Frontend Test Infrastructure (Low)

**Setup:**

```bash
cd frontend && npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom @testing-library/user-event
```

**File:** `frontend/vitest.config.ts`

```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
  },
});
```

**First tests:**
- `useAuth` context (mount, login, logout, token persistence)
- `api` client (request interception, error handling, 401 cleanup)
- `ArticleForm` component (render, validation, submit)
- `AgentsPanel` sub-components (split first, then test individually)

---

#### Task F5: Panel Extraction (Low)

**Current problem:** `AgentsPanel` (310 lines) handles list, form, detail modal, streaming, actions.

**Design:** Split into:

```
frontend/components/panels/
  AgentsPanel.tsx         — List only (DataTable + header)
  AgentsRunForm.tsx       — New run modal
  AgentsRunDetail.tsx     — Detail modal
  AgentsActions.tsx       — Cancel/Retry/Re-run buttons
  AgentsStageProgress.tsx — Per-stage progress display
```

Same pattern for other panels: extract `renderCell` logic into shared components.

**Risk:** Low — visual regression risk only.

**Breaking changes:** None.

---

## 4. Breaking API Changes Summary

| Change | Phase | Impact | Mitigation |
|--------|-------|--------|------------|
| A3: Remove dead fields from report response | F.4A | Frontend types must drop `research_result`, `analysis_result`, etc. | Update `IntelligenceReport` type in `frontend/types/index.ts` |
| A4: Unify error envelope | F.4A | Error format changes from `{success, data, error}` to `{code, message, details}` | Update `api.ts` error parsing; update all frontend error handling |
| A5: UUID validation 500→422 | F.4A | Clients expecting 500 on bad UUID get 422 | No frontend code sends invalid UUIDs currently |
| F1: Route extraction | F.4E | URL structure changes (`/` → `/dashboard/articles`, etc.) | Add redirect route `/dashboard` → `/dashboard/articles` |

**Recommendation:** Execute A4 last in F.4A, after confirming no frontend consumer depends on the current error format. The current format works; the unified format is cleaner but has migration cost.

---

## 5. Tasks to Postpone Until After Async Worker System Exists

These tasks depend on having a persistent task queue (B1/B2) before they can be safely implemented:

| Task | Reason |
|------|--------|
| **Scheduled autonomous jobs** (new cron-triggered pipelines) | Currently triggered by broken `AsyncIOScheduler`. Must wait for `BackgroundScheduler` (A7) + RQ (B1) to avoid double-execution or crashes. |
| **Auto-retry on failed agent runs** | Requires knowing whether a failure is due to transient LLM error vs. permanent pipeline error. The current executor doesn't distinguish these. RQ provides built-in retry semantics. |
| **Concurrent run limits per user** | Without a centralized queue, enforcing per-user concurrency limits requires in-memory state that is lost on restart. RQ provides natural throttling via queue depth. |
| **Long-running pipeline timeout adjustments** (>5 min) | The current 300s timeout is hardcoded. With RQ, timeout becomes a worker configuration. Adjusting it before the worker exists is premature. |
| **Checkpoint/recovery for interrupted runs** | Requires persistent state storage (PostgreSQL-based LangGraph checkpointer). The current `MemorySaver` is fine for sync execution but meaningless with RQ workers. |

---

## 6. Implementation Order Recommendation

```
Week 1-2:  F.4A — Foundation & Security
  Day 1-2:  C1 (credential rotation) — MUST be first
  Day 3-4:  A1 (global state → app.state)
  Day 4-5:  A2 (DI via Depends), A6 (KnowledgeService rename)
  Day 5-6:  A7 (scheduler fix), C2-C6 (security hardening)
  Day 6-7:  A3 (ReportService), A4 (error envelope), A5 (UUID validation)
  Day 7-8:  A8 (pipeline registry), review, merge

Week 2-3:  F.4B — Persistent Task Queue
  Day 1-2:  B1 (RQ integration, docker-compose worker)
  Day 3-4:  B2 (RQExecutor wiring, config flag)
  Day 4-5:  B3 (DB indexes migration)
  Day 5-6:  B4-B5 (health check extensions)
  Day 6-7:  D6 (AgentRuntimeService tests), review, merge

Week 3-4:  F.4C — Test Foundation
  Day 1-2:  D1 (shared fixtures)
  Day 2-4:  D2-D5 (LLM, RAG, embedding, MCP tests)
  Day 4-5:  D7 (callback tests)
  Day 5-6:  D8 (API integration tests)
  Day 6-7:  D9 (migration tests), review, merge

Week 4-5:  F.4D — Performance & Polish
  Day 1-2:  E1 (indexes — migration already done in B3)
  Day 2-3:  E2 (shared httpx pool)
  Day 3-4:  E3 (response caching)
  Day 4-5:  Final integration testing, review, merge

Week 5-6:  F.4E — Frontend Foundation
  Day 1-3:  F1 (route extraction from page.tsx)
  Day 3-5:  F2 (form library migration)
  Day 5-6:  F3 (type safety improvements)
  Day 6-7:  F4 (frontend test infrastructure)
  Week 6:   F5 (panel extraction), final review, merge
```

---

## 7. Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| RQ adds operational complexity | Medium | Medium | Keep RQ minimal — no flower, no beat. Single worker process. |
| Error envelope change breaks frontend | High | Medium | Defer A4 until frontend is ready; keep old format as fallback |
| Route extraction breaks bookmarks | High | Low | Add redirect routes; communicate URL change |
| CSP blocks legitimate scripts | Medium | Low | Start with permissive CSP, tighten iteratively |
| New dependencies in frontend (RHF, Zod, Vitest) | Low | Low | Pin versions, audit for conflicts |
| DB indexes cause lock contention | Low | Low | Use `CREATE INDEX CONCURRENTLY` |
| RQ workers consume more memory | Medium | Low | Set memory limits in docker-compose; monitor |

---

## 8. Success Criteria

### F.4A Entry Gate
- [ ] `.env` removed from git history, all credentials rotated
- [ ] Engine/session stored in `app.state`, not module globals
- [ ] All routers use FastAPI `Depends()` for service injection
- [ ] Rate limiting applied to all write endpoints
- [ ] Security headers include CSP
- [ ] Audit logs capture IP, user-agent, request-id

### F.4B Entry Gate
- [ ] RQ worker starts independently via docker-compose
- [ ] `AgentRuntimeService.submit()` routes to RQ when `USE_RQ=true`
- [ ] Running agent survives `docker compose restart backend`
- [ ] Health check verifies Redis connectivity

### F.4C Entry Gate
- [ ] LLM router has ≥80% test coverage
- [ ] RAG retriever and generator tested
- [ ] MCP clients tested for all 4 servers
- [ ] Shared fixtures eliminate all duplicated test helpers
- [ ] API integration tests pass against real PostgreSQL

### F.4D Entry Gate
- [ ] All FK columns indexed
- [ ] Status/category filter columns indexed
- [ ] Shared httpx pool reduces connection count by ≥50%
- [ ] Read endpoints return cached responses (verified via logs)

### F.4E Entry Gate
- [ ] `page.tsx` ≤50 lines (tab shell only)
- [ ] Each resource has its own route page
- [ ] Forms use React Hook Form + Zod
- [ ] Vitest runs with ≥60% frontend coverage
- [ ] `AgentsPanel` split into ≥3 sub-components

---

## 9. Files Summary

### New Files

| File | Purpose | Phase |
|------|---------|-------|
| `backend/workers/rq/__init__.py` | RQ connection helper | F.4B |
| `backend/workers/rq/worker.py` | RQ worker entry point | F.4B |
| `backend/workers/rq/jobs.py` | RQ job functions | F.4B |
| `backend/workflows/registry.py` | Pipeline registry | F.4A |
| `frontend/hooks/useEntityForm.ts` | Generic form hook | F.4E |
| `frontend/components/panels/AgentsRunForm.tsx` | Extracted from AgentsPanel | F.4E |
| `frontend/components/panels/AgentsRunDetail.tsx` | Extracted from AgentsPanel | F.4E |
| `frontend/components/panels/AgentsActions.tsx` | Extracted from AgentsPanel | F.4E |
| `frontend/vitest.config.ts` | Test configuration | F.4E |
| `frontend/tests/setup.ts` | Test setup | F.4E |
| `frontend/tests/utils.ts` | Test utilities | F.4E |

### Modified Files (Backend)

| File | Change | Phase |
|------|--------|-------|
| `backend/database/connection.py` | Return engine+factory, remove globals | F.4A |
| `backend/main.py` | Store engine in app.state, extend health checks | F.4A, F.4B |
| `backend/routers/deps.py` | Read session_factory from app.state | F.4A |
| `backend/routers/articles.py` | Use Depends() instead of sys.modules hack | F.4A |
| `backend/routers/knowledge.py` | Same | F.4A |
| `backend/routers/tasks.py` | Same | F.4A |
| `backend/routers/reports.py` | Same | F.4A |
| `backend/routers/auth.py` | Same | F.4A |
| `backend/routers/errors.py` | Unified ErrorResponse format | F.4A |
| `backend/routers/security_headers.py` | Add CSP header | F.4A |
| `backend/rate_limiter.py` | Add endpoint limits, X-Forwarded-For key | F.4A |
| `backend/services/report_service.py` | Remove dead fields from _to_dict | F.4A |
| `backend/services/knowledge_service.py` | Rename to knowledge_crud_service.py | F.4A |
| `backend/services/agent_runtime_service.py` | Add RQExecutor path, pipeline registry | F.4A, F.4B |
| `backend/services/llm/providers/openai.py` | Accept shared httpx client | F.4D |
| `backend/services/llm/providers/anthropic.py` | Same | F.4D |
| `backend/services/llm/providers/ollama.py` | Same | F.4D |
| `backend/services/llm/providers/compatible.py` | Same | F.4D |
| `backend/workers/scheduler/scheduler.py` | AsyncIOScheduler → BackgroundScheduler | F.4A |
| `backend/schemas/article_create.py` | UUID validator on source_id | F.4A |
| `backend/schemas/report_create.py` | UUID validators | F.4A |
| `backend/schemas/task_create.py` | UUID validators | F.4A |
| `backend/schemas/knowledge_create.py` | UUID validators | F.4A |
| `backend/events/subscriber.py` | Pass ip_address, user_agent, request_id | F.4A |
| `docker-compose.yml` | Add rq_worker service, health checks | F.4B |
| `Dockerfile.backend` | Include RQ dependencies | F.4B |
| `backend/alembic/versions/0008_add_performance_indexes.py` | New migration | F.4B |

### Modified Files (Frontend)

| File | Change | Phase |
|------|--------|-------|
| `frontend/app/page.tsx` | Reduce to tab shell (~50 lines) | F.4E |
| `frontend/app/dashboard/` | New directory with route pages | F.4E |
| `frontend/lib/api.ts` | Update error parsing for unified envelope | F.4A |
| `frontend/types/index.ts` | Discriminated unions, remove Record band-aids | F.4E |
| `frontend/components/articles/ArticleForm.tsx` | Migrate to react-hook-form | F.4E |
| `frontend/components/tasks/TaskForm.tsx` | Same | F.4E |
| `frontend/components/knowledge/KnowledgeForm.tsx` | Same | F.4E |
| `frontend/components/reports/ReportForm.tsx` | Same | F.4E |
| `frontend/components/panels/AgentsPanel.tsx` | Reduce to list-only | F.4E |
| `frontend/hooks/useArticles.ts` | Typed mutation bodies | F.4E |
| `frontend/hooks/useTasks.ts` | Same | F.4E |
| `frontend/hooks/useKnowledge.ts` | Same | F.4E |
| `frontend/hooks/useReports.ts` | Same | F.4E |
| `frontend/package.json` | Add react-hook-form, zod, vitest deps | F.4E |

### Modified Files (Tests)

| File | Change | Phase |
|------|--------|-------|
| `tests/conftest.py` | Add shared fixtures, factories | F.4C |
| `tests/unit/routers/test_articles.py` | Use shared fixtures | F.4C |
| `tests/unit/routers/test_articles_write.py` | Remove duplicated helpers | F.4C |
| `tests/unit/routers/test_auth.py` | Same | F.4C |
| `tests/unit/routers/test_knowledge_write.py` | Same | F.4C |
| `tests/unit/routers/test_tasks_write.py` | Same | F.4C |
| `tests/unit/routers/test_reports_write.py` | Same | F.4C |
| `tests/unit/services/test_agent_runtime_service.py` | New — test service methods | F.4B |
| `tests/unit/services/llm/test_router.py` | New — test LLM routing | F.4C |
| `tests/unit/services/rag/test_retriever.py` | New | F.4C |
| `tests/unit/services/rag/test_generator.py` | New | F.4C |
| `tests/unit/services/embedding/test_client.py` | New | F.4C |
| `tests/unit/mcp/servers/test_notion_client.py` | New | F.4C |
| `tests/unit/mcp/servers/test_asana_client.py` | New | F.4C |
| `tests/unit/mcp/servers/test_browser_client.py` | New | F.4C |
| `tests/unit/mcp/servers/test_github_client.py` | New | F.4C |
| `tests/unit/workflows/graph/test_callbacks.py` | New | F.4C |
| `tests/integration/test_api.py` | New — API integration tests | F.4C |
| `tests/integration/test_migrations.py` | New — migration tests | F.4C |
| `tests/integration/conftest.py` | testcontainers fixture | F.4C |

---

## 10. Out of Scope for F.4

The following items were identified in the architecture review but deliberately deferred:

| Item | Reason | Target Phase |
|------|--------|-------------|
| Frontend component library (shadcn/ui) | Nice-to-have, not blocking | F.5 |
| WebSocket transport for agent streaming | SSE works; WebSocket adds complexity | F.5 |
| Refresh token flow / logout endpoint | Important but requires auth redesign | F.5 |
| Database backup strategy | Operational concern, not product feature | F.5 |
| Staging environment configuration | Operational concern | F.5 |
| Full CI/CD pipeline | Operational concern; Makefile exists | F.5 |
| Feature flags / gradual rollout | Not needed yet | F.6 |
| Connection pooling for external services (partial) | E2 covers LLM providers; MCP/connector pooling deferred | F.5 |
| HSTS enforcement | C4/C6 handle immediate concerns; HSTS requires HTTPS setup | F.5 |
