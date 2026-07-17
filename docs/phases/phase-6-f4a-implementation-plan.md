# Phase 6-F.4A — Production Readiness Review & Implementation Plan

**Date:** 2026-07-17
**Status:** Draft — awaiting approval
**Preceded by:** Phase 6-F.3 (Agent Runtime)

---

## Executive Summary

This document reviews every proposed F.4A task against the CURRENT codebase, determines necessity, maps exact file changes, assesses migration risks and API impact, proposes simpler alternatives where available, and produces a prioritized implementation checklist with rollback strategy.

**Key finding:** The `JobScheduler` class exists at `backend/workers/scheduler/scheduler.py` but is **never instantiated or started** anywhere in the application. Scheduled jobs are dead code. This simplifies the scheduler fix — we don't need to shut down an existing running scheduler.

**Key finding:** There are two functions named `daily_intelligence_job`:
- `backend/workers/jobs/daily_intelligence_job.py:19` (used by scheduler)
- `backend/workers/jobs/autonomous_intelligence_job.py:15` (shadowed name)

---

## 1. Task-by-Task Review

### A1: Replace Global Mutable Engine State → app.state

#### Necessity: YES — Critical
Module-level globals (`_engine`, `_session_factory`) typed as `type | None` instead of actual engine types. Every module that imports from `connection.py` accesses the same global state. Prevents testing multiple app instances.

#### Files That Change

| File | Current Import Pattern | New Pattern |
|------|----------------------|-------------|
| `backend/database/connection.py` | Defines `_engine`, `_session_factory` globals; `create_engine_for_settings()` stores to globals | Return `(engine, factory)` tuple; remove all globals |
| `backend/main.py:17,34` | `from .database.connection import create_engine_for_settings, get_session_factory`; calls `create_engine_for_settings(settings)` in lifespan | Call `create_engine_for_settings(settings)`, store result in `app.state.engine`, `app.state.session_factory` |
| `backend/routers/deps.py:13,21-22` | `from ..database.connection import get_session_factory`; `session = get_session_factory()()` | `session = request.app.state.session_factory()()` |
| `backend/services/agent_runtime_service.py:105-107` | `from ..database.connection import get_session_factory as _gsf`; `sf = _gsf()` | `sf = request.app.state.session_factory` (passed via constructor or request) |
| `backend/app/bootstrap.py:7,46-53` | `from backend.database.connection import get_session_factory`; `_gsf()` pattern | Use `request.app.state.session_factory` instead |

#### Migration Risks
- **Medium** — 5 files touch connection patterns. Must verify all code paths use `app.state` consistently.
- The `agent_runtime_service.py` background execution path creates its own session via `self._session_factory`. After this change, the service must receive the factory explicitly (not import from `connection.py`).
- `bootstrap.py` uses `get_session_factory` to create a session for `AuditLogSubscriber`. This must be wired through `app.state`.

#### API Impact
None. Internal refactoring only.

#### Simpler Alternative?
No. The global state is fundamentally incompatible with process-based deployment and testing.

#### Breaking Tests?
Yes — tests that mock `get_session_factory` will break. They must be updated to set `app.state.session_factory` instead. All 6 router test files define their own `client` fixture that overrides `get_current_user` — these fixtures must also set `app.state.session_factory`.

---

### A2: Replace sys.modules Service Instantiation with FastAPI Depends()

#### Necessity: YES — High
Every CRUD router uses a `sys.modules[__name__]` introspection hack to enable test patching. This is fragile, opaque, and un-Pythonic.

#### Files That Change

| File | Current Code | New Code |
|------|-------------|----------|
| `backend/routers/articles.py:18-22` | `_make_article_service(db, request)` with sys.modules | `Depends(lambda db=Depends(get_db): ArticleService(db))` or explicit `get_article_service()` |
| `backend/routers/knowledge.py:18-22` | Same pattern | Same fix |
| `backend/routers/tasks.py:18-23` | Same pattern | Same fix |
| `backend/routers/reports.py:18-22` | Same pattern | Same fix |
| `backend/routers/auth.py:47-53,70-76` | `__import__("sys").modules.get(...)` | Same fix |
| `backend/routers/agents.py:30-38` | `_make_runtime_service(db)` + manual event_publisher injection | `Depends()` with event_publisher from `app.state` |

#### Migration Risks
- **Low-Medium** — Straightforward replacement. Each router has ~5 endpoint functions that call `_make_*_service(db, request)`. Replace with a single `Depends()` wrapper.
- Test fixtures that currently do `app.dependency_overrides[ArticleService] = MockArticleService` will continue to work since `Depends()` supports override.

#### API Impact
None. The service constructor signature doesn't change. Only the instantiation mechanism changes.

#### Simpler Alternative?
Could use `functools.partial` instead of a dependency function, but `Depends()` is the FastAPI idiomatic approach and enables `dependency_overrides` for testing.

#### Breaking Tests?
Minimal. Existing tests use `app.dependency_overrides` which works with `Depends()`. However, tests that currently monkey-patch `sys.modules` entries will break. These tests need updating.

---

### A3: Fix ReportService._to_dict() Dead Fields

#### Necessity: YES — Medium
The `_to_dict()` method returns hardcoded nulls for `research_result`, `analysis_result`, `translation_result` and empty lists for `knowledge_items`, `tasks`. These fields are advertised in the response schema but never populated.

#### Two Approaches

**Approach A (Recommended): Remove dead fields from response schema.**
- Files: `backend/schemas/report.py` (remove `research_result`, `analysis_result`, `translation_result`, `knowledge_items`, `tasks` from `IntelligenceReportResponse`)
- Files: `frontend/types/index.ts` (remove same fields from `IntelligenceReport` type)
- Risk: Low — these fields are always null. Removing them changes the response shape but doesn't lose data.
- Breaking: Yes — API response shape changes. Frontend types must update.

**Approach B: Populate fields from related models.**
- Requires joins across `intelligence_reports ↔ agent_runs ↔ articles/knowledge_items/tasks`
- Risk: High — introduces complex queries, potential N+1 issues, significant code change
- Breaking: No — existing null values stay null, just properly queried
- Not recommended: The relationship between reports and agent runs is loose (FK exists but not enforced in the service layer).

#### Migration Risks
Approach A is low risk — the fields are dead code. Approach B is high risk — requires new queries and could introduce performance regressions.

#### API Impact
Approach A removes fields from the response envelope. Clients receiving `null` for these fields will see them absent instead.

#### Simpler Alternative?
Approach A is the simplest. Just delete 5 fields from the schema and the corresponding lines in `_to_dict()`.

#### Breaking Tests?
Yes — tests that assert on `report.research_result` etc. will fail. But these tests are testing dead code (always null).

---

### A4: Unify Error Envelope

#### Necessity: YES — Medium
Exception handlers return `{success, data, error}` but `ErrorResponse` schema has `{code, message, details}`. Two formats confuse clients.

#### Current State
```python
# Exception handler output (errors.py:20-22):
{"success": False, "data": None, "error": str(exc)}

# ErrorResponse schema (schemas/error.py:10-15):
{code: str, message: str, details: list[dict] | None}
```

#### Proposed Change
Make exception handlers return the `ErrorResponse` format:
```python
# RequestValidationError → {"code": "VALIDATION_ERROR", "message": "...", "details": [...]}
# HTTPException → {"code": "HTTP_ERROR", "message": "...", "details": None}
# Generic Exception → {"code": "INTERNAL_ERROR", "message": "Internal server error", "details": None}
```

#### Files That Change

| File | Change |
|------|--------|
| `backend/routers/errors.py` | Rewrite all 3 exception handlers to return `{code, message, details}` |
| `frontend/lib/api.ts` | Update error parsing from `body.error` to `body.message` |

#### Migration Risks
- **Medium** — The error format change affects ALL error responses. Frontend error handling must adapt.
- The frontend `api.ts` line 31 does `message = body.error || body.detail || message`. This needs to handle both old and new format during transition, or update immediately.

#### API Impact
YES — breaking change for error response format. All clients that parse `response.error` must switch to `response.message`.

#### Simpler Alternative?
Keep the current `{success, data, error}` format and just add `code` field to it:
```python
{"success": False, "data": None, "error": "...", "code": "VALIDATION_ERROR"}
```
This preserves backward compatibility (error string still at `.error`) while adding structure.

**Recommendation:** Use the simpler alternative. It avoids breaking frontend error parsing.

#### Breaking Tests?
Yes — router tests that assert on `response.json()["error"]` will need to check the new format.

---

### A5: UUID Validation in Schemas

#### Necessity: YES — Low
Invalid UUID strings cause `ValueError` in service layer → 500 error. Should be 422 validation error.

#### Files That Change

| Schema File | Field | Current Type | New Type |
|------------|-------|-------------|----------|
| `backend/schemas/article_create.py:14` | `source_id` | `str` | `str` + `field_validator` |
| `backend/schemas/article_create.py:26` | `source_id` (update) | `str \| None` | `str \| None` + validator |
| `backend/schemas/report_create.py:15` | `article_ids` | `list[str]` | `list[str]` + validator per item |
| `backend/schemas/report_create.py:16` | `agent_run_id` | `str \| None` | `str \| None` + validator |
| `backend/schemas/task_create.py:17` | `agent_run_id` | `str \| None` | `str \| None` + validator |
| `backend/schemas/task_create.py:18` | `knowledge_item_id` | `str \| None` | `str \| None` + validator |
| `backend/schemas/knowledge_create.py:14` | `article_id` | `str \| None` | `str \| None` + validator |

#### Migration Risks
- **Low** — Purely additive validation. Valid input continues to work exactly the same.
- Invalid input goes from 500 to 422 — better UX.

#### API Impact
Minor — error response changes from 500 to 422 for invalid UUIDs.

#### Simpler Alternative?
Use Pydantic's `Annotated[str, BeforeValidator(validate_uuid)]` for less boilerplate than `@field_validator`.

#### Breaking Tests?
Tests that expect 500 on invalid UUID will get 422. Must update assertions.

---

### A6: Rename Duplicate KnowledgeService Classes

#### Necessity: YES — Low
Two classes named `KnowledgeService` in different modules causes confusion:
- `backend/services/knowledge_service.py` — CRUD service for API endpoints
- `backend/services/knowledge/service.py` — persistence/embedding service for pipeline nodes

#### Files That Change

| File | Change |
|------|--------|
| `backend/services/knowledge_service.py` | Rename class → `KnowledgeItemService` |
| `backend/routers/knowledge.py:15` | Update import from `knowledge_service` |
| `backend/pipelines/article_pipeline.py:30` | Import stays same (uses `knowledge.service.KnowledgeService`) |
| `backend/services/knowledge/__init__.py` | Update re-export if needed |

#### Migration Risks
- **Very Low** — Mechanical rename. Only 2 import sites affected.

#### API Impact
None. Internal rename only.

#### Simpler Alternative?
Rename the subpackage instead: `backend/services/knowledge_persistence/service.py`. Less disruptive to the flat import in routers.

#### Breaking Tests?
None. Tests import by module path, not class name.

---

### A7: Fix AsyncIOScheduler → BackgroundScheduler

#### Necessity: YES — Medium
`AsyncIOScheduler.start()` creates its own event loop, conflicting with ASGI. However, **the scheduler is never started** — `JobScheduler` is defined but never instantiated in `main.py`, `bootstrap.py`, or any lifecycle hook.

#### Verification
Grep for `JobScheduler(` or `job_scheduler` returns zero results. The scheduler class is dead code.

#### Implication
We can change the scheduler implementation without worrying about runtime conflicts. The fix is straightforward:

#### Files That Change

| File | Change |
|------|--------|
| `backend/workers/scheduler/scheduler.py:9` | `from apscheduler.schedulers.background import BackgroundScheduler` |
| `backend/workers/scheduler/scheduler.py:33` | `self._scheduler = BackgroundScheduler()` |

#### Migration Risks
- **Very Low** — Scheduler is dead code. No runtime impact.
- When the scheduler IS wired up later (F.4B), it will use `BackgroundScheduler` which is thread-safe inside ASGI.

#### API Impact
None.

#### Simpler Alternative?
No change needed right now since the scheduler isn't running. Defer until F.4B when it's actually integrated.

#### Breaking Tests?
None.

---

### A8: Pipeline Registry Pattern

#### Necessity: YES — Low
`PIPELINE_MAP` uses string module paths resolved via `importlib`. Typos not caught at import time.

#### Current Code
```python
# agent_runtime_service.py:56-59
PIPELINE_MAP = {
    "intelligence": "backend.workflows.daily_intelligence.compile_intelligence_graph",
    "autonomous": "backend.workflows.autonomous_intelligence.compile_autonomous_intelligence",
}
```
Resolved at runtime via:
```python
module_path = PIPELINE_MAP[pipeline_type]
mod_path, func_name = module_path.rsplit(".", 1)
mod = importlib.import_module(mod_path)
graph_builder = getattr(mod, func_name)
```

#### Verification of Targets
- `compile_intelligence_graph` exists in `backend/workflows/builder.py:45`
- `compile_autonomous_intelligence` exists in `backend/workflows/autonomous_intelligence.py:84`
- Both are exported via `backend/workflows/daily_intelligence.py:5` and `backend/workflows/autonomous_intelligence.py:84` respectively

#### Files That Change

| File | Change |
|------|--------|
| `backend/workflows/registry.py` | NEW FILE — define `PIPELINE_REGISTRY: dict[str, PipelineFactory]` with direct references |
| `backend/services/agent_runtime_service.py:56-59` | Replace string map with `from ..workflows.registry import PIPELINE_REGISTRY` |
| `backend/services/agent_runtime_service.py:227-230` | Replace `importlib` resolution with direct lookup |

#### Migration Risks
- **Low** — Import-time validation catches typos immediately.
- `importlib` import can be removed from `agent_runtime_service.py` if no longer needed elsewhere.

#### API Impact
None.

#### Simpler Alternative?
Directly import the pipeline functions in `agent_runtime_service.py` instead of creating a separate registry file. Fewer files, same benefit.

#### Breaking Tests?
None.

---

### C2: Rate Limit All Write Endpoints

#### Necessity: YES — High
Only `/register` and `/login` are rate-limited. All CRUD endpoints accept unlimited writes.

#### Current State
```python
# rate_limiter.py:8-18
from slowapi.util import get_remote_address
limiter = Limiter(
    key_func=get_remote_address,  # IP-only, broken behind proxies
    default_limits=[_default],   # 100/hour global
    storage_uri=_redis_url,
    in_memory_fallback=[_default],  # silent fallback!
)
```

Applied only in:
- `backend/routers/auth.py:45` — `@limiter.limit(_login_rate_limit())` on register
- `backend/routers/auth.py:68` — `@limiter.limit(_login_rate_limit())` on login

#### Files That Change

| File | Change |
|------|--------|
| `backend/rate_limiter.py` | Add `X-Forwarded-For` key function; add endpoint-specific limits dict |
| `backend/main.py:122` | Add `"OPTIONS"` to CORS `allow_methods` (related security fix) |
| `backend/routers/articles.py` | Add `@limiter.limit("100/hour")` to POST/PUT/DELETE |
| `backend/routers/knowledge.py` | Same |
| `backend/routers/tasks.py` | Same |
| `backend/routers/reports.py` | Same |
| `backend/routers/agents.py` | Add `@limiter.limit("20/hour")` to POST /run, POST /cancel |

#### Migration Risks
- **Low** — Additive rate limiting. Clients making legitimate requests won't be affected.
- The `in_memory_fallback` silently degrades if Redis is unavailable. This is a known issue but not introduced by this change.

#### API Impact
None for legitimate traffic. Abusive traffic will now be throttled.

#### Simpler Alternative?
Apply rate limiting via middleware instead of decorators. One middleware handles all endpoints. Less file changes, same effect.

**Recommended:** Use middleware approach. Add a `RateLimitMiddleware` that checks `request.method in ("POST", "PUT", "DELETE")` and applies limits based on endpoint.

#### Breaking Tests?
Tests that make rapid sequential writes may hit rate limits. Need to mock or increase limits in test env.

---

### C3: CORS OPTIONS Method

#### Necessity: YES — Trivial
`allow_methods=["GET", "POST", "PUT", "DELETE"]` missing `OPTIONS`. Browser preflight fails.

#### Files That Change

| File | Line | Change |
|------|------|--------|
| `backend/main.py` | 122 | `allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]` |

#### Migration Risks
Trivial. One-line change.

#### API Impact
None. Fixes broken browser preflight.

#### Breaking Tests?
None.

---

### C4: Content-Security-Policy Header

#### Necessity: YES — Medium
No CSP header. User-generated content flows through SSE streaming without protection.

#### Files That Change

| File | Line | Change |
|------|------|--------|
| `backend/routers/security_headers.py` | 17-24 | Add `Content-Security-Policy` to `_get_headers()` |

#### Proposed CSP
```python
"CSP-Directive": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self' ${API_BASE}; frame-ancestors 'none'; object-src 'none'"
```

#### Migration Risks
- **Medium** — CSP can block legitimate scripts. Must audit frontend for inline `<script>` tags.
- The Next.js dev server uses inline scripts. In production (`next build`), scripts are externalized.

#### API Impact
None for non-browser clients. May affect browsers with strict CSP enforcement.

#### Simpler Alternative?
Start with a permissive CSP (`report-only` mode) that logs violations without blocking:
```
Content-Security-Policy-Report-Only: default-src 'self'; ...
```
Then switch to active CSP after verifying no violations.

#### Breaking Tests?
None. Tests use `TestClient` (no browser).

---

### C5: Audit Log Enrichment

#### Necessity: YES — Medium
`AuditLog` model has `ip_address`, `user_agent` columns but they're never populated. `AuditLogEvent` already has these fields (event.py:54-55).

#### Files That Change

| File | Change |
|------|--------|
| `backend/routers/errors.py:LogMiddleware` | Extract `X-Forwarded-For` and `User-Agent` from request headers, attach to `request.state` |
| `backend/events/event.py:AuditLogEvent` | Already has `ip_address`, `user_agent` fields — no change needed |
| `backend/routers/deps.py:get_current_user` | Pass `request.headers.get("X-Forwarded-For")` and `request.headers.get("User-Agent")` to `AuditLogEvent` |
| `backend/services/*_service.py` | Pass IP/user-agent from request context to `_publish_audit()` calls |
| `backend/routers/agents.py` | Pass IP/user-agent when publishing audit events |

#### Migration Risks
- **Medium** — Requires threading request metadata through service layers that currently don't receive it.
- Services receive `event_publisher` but not the request object. Need to either:
  - Pass IP/user-agent as parameters to `_publish_audit()` (cleanest)
  - Store in `contextvars` (more automatic but harder to debug)

#### API Impact
None. Audit log records get additional fields.

#### Simpler Alternative?
Use `contextvars.ContextVar` to propagate request metadata through async call chains. One place to set, auto-available everywhere.

#### Breaking Tests?
Tests that call `_publish_audit()` directly need to pass the new parameters.

---

### C6: Disable Swagger in Production

#### Necessity: YES — Trivial
OpenAPI docs accessible without auth at `/api/docs` and `/api/redoc`.

#### Files That Change

| File | Line | Change |
|------|------|--------|
| `backend/main.py:67-68` | `docs_url="/api/docs"`, `redoc_url="/api/redoc"` | Condition on `settings.app_env != "production"` |

#### Migration Risks
Trivial. One conditional.

#### API Impact
None. Docs disappear in production.

#### Breaking Tests?
None. Tests run in development mode.

---

## 2. Prioritized Implementation Checklist

Ordered by risk, dependency, and blast radius.

### Block 1: Foundation (Day 1-2)

- [ ] **C6** — Disable Swagger in production (trivial, no risk)
- [ ] **C3** — Add OPTIONS to CORS allow_methods (trivial, fixes browser preflight)
- [ ] **A6** — Rename duplicate KnowledgeService (low risk, mechanical)
- [ ] **A7** — Switch AsyncIOScheduler → BackgroundScheduler (dead code, no runtime impact)

### Block 2: Core Infrastructure (Day 2-4)

- [ ] **A1** — Replace global engine state with app.state (medium risk, touches 5 files)
- [ ] **A2** — Replace sys.modules with FastAPI Depends() (medium risk, touches 5 routers)
- [ ] **A8** — Pipeline registry pattern (low risk, follows A1 since it touches agent_runtime_service)

### Block 3: Data Integrity (Day 4-5)

- [ ] **A5** — UUID validation in schemas (low risk, purely additive)
- [ ] **A3** — Remove dead report fields (low risk, fields are always null)

### Block 4: Security Hardening (Day 5-7)

- [ ] **C2** — Rate limit all write endpoints (medium risk, depends on A1 for proxy-aware key)
- [ ] **C4** — Add CSP header (medium risk, may need tuning)
- [ ] **C5** — Audit log enrichment (medium risk, requires request metadata threading)

---

## 3. Exact File-by-File Modification Plan

### New Files (3)

| File | Purpose |
|------|---------|
| `backend/workflows/registry.py` | Pipeline registry — replaces string-based PIPELINE_MAP |

### Modified Files (18)

| File | Tasks | Lines Changed (est.) |
|------|-------|---------------------|
| `backend/main.py` | C3, C6 | ~5 |
| `backend/config.py` | None | 0 |
| `backend/database/connection.py` | A1 | ~20 (remove globals, change return type) |
| `backend/routers/deps.py` | A1, C5 | ~10 |
| `backend/routers/errors.py` | C5 | ~15 (attach IP/UA to request.state) |
| `backend/routers/security_headers.py` | C4 | ~5 |
| `backend/rate_limiter.py` | C2 | ~15 (add endpoint config, proxy key) |
| `backend/services/agent_runtime_service.py` | A1, A8 | ~20 (remove importlib, use registry) |
| `backend/services/knowledge_service.py` | A6 | ~5 (rename class) |
| `backend/routers/articles.py` | A2 | ~10 (replace _make_service with Depends) |
| `backend/routers/knowledge.py` | A2, A6 | ~10 |
| `backend/routers/tasks.py` | A2 | ~10 |
| `backend/routers/reports.py` | A2 | ~10 |
| `backend/routers/auth.py` | A2 | ~15 |
| `backend/routers/agents.py` | A2, C5 | ~15 |
| `backend/schemas/article_create.py` | A5 | ~5 |
| `backend/schemas/report_create.py` | A5 | ~5 |
| `backend/schemas/task_create.py` | A5 | ~5 |
| `backend/schemas/knowledge_create.py` | A5 | ~5 |
| `backend/schemas/report.py` | A3 | ~10 (remove dead fields) |
| `backend/workflows/graph/builder.py` | None (verify export exists) | 0 |
| `backend/workflows/autonomous_intelligence.py` | None (verify export exists) | 0 |
| `backend/workers/scheduler/scheduler.py` | A7 | ~5 |

### Test Files to Update (10+)

| File | Change |
|------|--------|
| `tests/conftest.py` | Set `app.state.session_factory` instead of overriding `get_session_factory` |
| `tests/unit/routers/test_articles.py` | Update client fixture for A1 |
| `tests/unit/routers/test_articles_write.py` | Update _make_client for A2 |
| `tests/unit/routers/test_knowledge_write.py` | Update for A2, A6 |
| `tests/unit/routers/test_tasks_write.py` | Update for A2 |
| `tests/unit/routers/test_reports_write.py` | Update for A2 |
| `tests/unit/routers/test_auth.py` | Update for A2 |
| `tests/unit/routers/test_agents_write.py` | Update for A2 |
| `tests/unit/services/test_report_service.py` | Update for A3 |
| `tests/unit/services/test_article_service.py` | Update for A2 |
| `tests/unit/services/test_task_service.py` | Update for A2 |
| `tests/unit/services/test_knowledge_service.py` | Update for A6 |

---

## 4. Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|-----------|------------|
| A1 breaks background execution | High | Medium | Ensure `AgentRuntimeService.__init__` accepts session factory from `app.state` |
| A2 breaks test patching | Medium | Low | `Depends()` supports `dependency_overrides` — same mechanism |
| A3 changes API response shape | Medium | Low | Fields are always null — removing them is safe |
| A5 converts 500→422 | Low | Very Low | Better behavior, not a regression |
| C2 rate limits legitimate traffic | Medium | Low | Set generous limits; can adjust iteratively |
| C4 CSP blocks frontend scripts | Medium | Medium | Use `Content-Security-Policy-Report-Only` first |
| C5 breaks audit events | Low | Low | Audit is fire-and-forget — failures are logged, not raised |
| A7 has no effect (dead code) | None | N/A | Skip until F.4B when scheduler is wired up |

---

## 5. Rollback Strategy

### Per-Task Rollback

| Task | Rollback Command | Effort |
|------|-----------------|--------|
| A1 | Revert `connection.py` to globals; revert `deps.py` to `get_session_factory()` | Low — pure revert |
| A2 | Revert router files to `_make_*_service()` pattern | Low — pure revert |
| A3 | Re-add dead fields to schema with `None` defaults | Low — pure revert |
| A5 | Remove `field_validator` decorators | Low — pure revert |
| A6 | Rename class back to `KnowledgeService` | Low — pure revert |
| A7 | N/A (skip) | N/A |
| A8 | Restore `importlib` resolution | Low — pure revert |
| C2 | Remove `@limiter.limit()` decorators | Low — pure revert |
| C3 | Remove `"OPTIONS"` from allow_methods | Trivial |
| C4 | Remove CSP header from middleware | Trivial |
| C5 | Stop passing IP/UA to audit events | Low |
| C6 | Always show docs | Trivial |

### Full Rollback
All changes are isolated to specific files. A single `git revert <commit>` restores everything. No database migrations, no config changes, no infrastructure changes.

---

## 6. Test Plan

### Pre-Implementation Baseline
Run full test suite before any changes:
```bash
cd backend && pytest tests/ -v --tb=short
```
Record pass/fail count. All tests must pass before starting.

### Per-Block Verification

**After Block 1 (C6, C3, A6, A7):**
```bash
pytest tests/unit/routers/test_routers_exist.py  # Verify all routers still load
pytest tests/unit/services/test_knowledge_service.py  # Verify renamed class works
```

**After Block 2 (A1, A2, A8):**
```bash
pytest tests/unit/routers/test_articles.py
pytest tests/unit/routers/test_articles_write.py
pytest tests/unit/routers/test_knowledge_write.py
pytest tests/unit/routers/test_tasks_write.py
pytest tests/unit/routers/test_reports_write.py
pytest tests/unit/routers/test_auth.py
pytest tests/unit/routers/test_agents_write.py
pytest tests/unit/services/test_article_service.py
pytest tests/unit/services/test_agent_runtime.py
```

**After Block 3 (A5, A3):**
```bash
pytest tests/unit/routers/test_schemas.py  # UUID validation
pytest tests/unit/services/test_report_service.py  # Dead field removal
```

**After Block 4 (C2, C4, C5):**
```bash
pytest tests/unit/routers/test_protected_endpoints.py  # Auth + rate limit
pytest tests/unit/test_events.py  # Audit events
pytest tests/unit/test_audit_subscriber.py  # Audit persistence
```

### Integration Verification
```bash
docker compose up -d --build
curl -f http://localhost:8000/api/health  # Verify health check works
curl -f -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/articles  # Verify CRUD
```

### Regression Checklist
- [ ] Login/register still works
- [ ] Article CRUD still works
- [ ] Knowledge CRUD still works
- [ ] Task CRUD still works
- [ ] Report creation still works
- [ ] Agent run submission still works
- [ ] Agent run cancellation still works
- [ ] SSE streaming still works
- [ ] Auth middleware still enforces JWT
- [ ] Role-based access still works
- [ ] Database sessions still commit/rollback correctly

---

## 7. Estimated Scope

### LOC Estimates

| Task | Lines Added | Lines Removed | Lines Modified | Total Touch |
|------|------------|---------------|----------------|-------------|
| A1 | 15 | 25 | 10 | 50 |
| A2 | 25 | 40 | 0 | 65 |
| A3 | 0 | 15 | 5 | 20 |
| A5 | 20 | 0 | 0 | 20 |
| A6 | 2 | 2 | 2 | 6 |
| A7 | 2 | 2 | 0 | 4 |
| A8 | 15 | 10 | 5 | 30 |
| C2 | 20 | 0 | 30 | 50 |
| C3 | 0 | 0 | 1 | 1 |
| C4 | 5 | 0 | 0 | 5 |
| C5 | 15 | 0 | 20 | 35 |
| C6 | 2 | 0 | 0 | 2 |
| **TOTAL** | **121** | **94** | **73** | **288** |

### Affected Modules

| Module | Files | Risk |
|--------|-------|------|
| Database layer | `connection.py`, `deps.py` | Medium |
| Router layer | 5 CRUD routers + agents + auth | Medium |
| Service layer | `agent_runtime_service.py` | Low |
| Schema layer | 4 create/update schemas + report schema | Low |
| Workflow layer | `builder.py`, `autonomous_intelligence.py` (read-only) | None |
| Worker layer | `scheduler.py` (read-only) | None |
| Security layer | `security_headers.py`, `rate_limiter.py` | Low |
| Test layer | 10+ test files | Medium |

### New Dependencies
None. All changes use existing packages (`pydantic`, `fastapi`, `slowapi`).

---

## 8. Tasks to Postpone Until After Async Worker System Exists

These tasks require a persistent task queue (RQ/Celery) that doesn't exist yet:

| Task | Reason | Target Phase |
|------|--------|-------------|
| **RQExecutor integration** | Requires RQ worker process and queue infrastructure | F.4B |
| **Scheduled job recovery** | Needs persistent queue to track in-flight jobs | F.4B |
| **Connection pooling for LLM providers** | Shared `httpx.AsyncClient` pool benefits from worker architecture | F.4D |
| **Response caching for read endpoints** | Redis-backed cache needs Redis as primary storage, not just rate limiting | F.4D |
| **Auto-retry on failed agent runs** | Retry logic depends on queue semantics | F.4B+ |
| **Checkpoint/persistence for long runs** | Requires LangGraph checkpointer backed by PostgreSQL | F.4B+ |

---

## 9. Recommended Execution Order

```
Day 1:  C6 (Swagger) → C3 (CORS) → A6 (KnowledgeService rename)
        Quick wins, zero risk, establishes confidence

Day 2:  A1 (Global state → app.state)
        Most impactful change. Do early while context is fresh.
        Run full test suite after completion.

Day 3:  A2 (Depends injection) → A8 (Pipeline registry)
        A2 builds on A1 (both refactor service instantiation).
        A8 depends on A2 (agent_runtime_service already touched).

Day 4:  A5 (UUID validation) → A3 (Report dead fields)
        Both are data integrity fixes. Independent of each other.

Day 5:  C2 (Rate limiting) → C4 (CSP) → C5 (Audit enrichment)
        Security hardening. C2 depends on A1 (proxy-aware key needs settings from app.state).
        C4 should start with Report-Only mode.
        C5 depends on A1 (request metadata flow).
```

**Total estimated effort: 5 working days for one developer.**

---

## Appendix: Verification Commands

```bash
# Verify scheduler is dead code
grep -rn "JobScheduler(" backend/ --include="*.py" | grep -v __pycache__
# Expected: only the class definition in scheduler.py

# Verify duplicate daily_intelligence_job
grep -rn "def daily_intelligence_job" backend/ --include="*.py" | grep -v __pycache__
# Expected: two definitions (jobs/daily_intelligence_job.py and jobs/autonomous_intelligence_job.py)

# Verify sys.modules hacks
grep -rn "sys.modules\|__import__.*modules" backend/routers/ --include="*.py" | grep -v __pycache__
# Expected: 5 occurrences (articles, knowledge, tasks, reports, auth)

# Verify get_settings() calls (creates new Settings each time)
grep -rn "get_settings()" backend/ --include="*.py" | grep -v __pycache__ | wc -l
# Expected: 10+ calls across the codebase

# Verify httpx.AsyncClient creations (no shared pool)
grep -rn "httpx.AsyncClient" backend/ --include="*.py" | grep -v __pycache__
# Expected: 5 creations (4 providers + qdrant)

# Verify asyncio.create_task usage (no persistent queue)
grep -rn "asyncio.create_task" backend/ --include="*.py" | grep -v __pycache__
# Expected: 1 occurrence in agent_runtime_service.py:197
```
