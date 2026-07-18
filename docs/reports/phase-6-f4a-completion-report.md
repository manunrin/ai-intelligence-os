# Phase 6-F.4A — Completion Report

**Date:** 2026-07-18
**Status:** Complete
**Commit:** `fb867f2` — `refactor(error): unify error envelope across backend and frontend (A4)`

---

## 1. Completed Tasks and Commits

Phase 6-F.4A encompasses tasks A1 through A8, C2 through C5, and the final A4 error envelope unification.

| Commit | Task | Description |
|---|---|---|
| `fb867f2` | **A4** | Unify error envelope across backend and frontend |
| `091d8ee` | **C5** | Enrich audit logs with ip_address and user_agent |
| `8978245` | **C4** | Add Content-Security-Policy-Report-Only header |
| `2447093` | **C2** | Proxy-aware rate limiter key + rate limit all write endpoints |
| `6820262` | **A3** | Remove dead fields from report schema |
| `7d8d7e0` | **A5** | Add UUID validation to request schemas |
| `743433d` | **A8** | Replace PIPELINE_MAP importlib with registry pattern |
| `f580935` | **A2** | Centralize service factories in deps.py (DI refactor) |
| `756ea7c` | **Phase 6-F** | App state DI, ownership, audit, security, production improvements |

Working tree is clean. Only unrelated untracked files remain (`.claude/`, `docs/reports/frontend-architecture-review.md`, `scripts/check_notion.py`).

---

## 2. Current Architecture Overview

### Backend (`backend/`) — 12,922 lines Python

```
main.py                    FastAPI app factory, lifespan, middleware stack
├── config.py              Pydantic Settings (env-driven)
├── database/
│   ├── base.py            SQLAlchemy DeclarativeBase + naming convention
│   ├── connection.py      asyncpg engine + session factory
│   └── models/            11 ORM entities (User, Article, Task, KnowledgeItem,
│                           Agent, AgentRun, Workflow, AuditLog, Source, etc.)
├── routers/
│   ├── api.py             Aggregates 7 sub-routers under /api/v1
│   ├── auth.py            Register/Login/Me (JWT-based)
│   ├── articles.py        CRUD (paginated)
│   ├── tasks.py           CRUD (paginated)
│   ├── knowledge.py       CRUD (paginated)
│   ├── reports.py         CRUD (paginated)
│   ├── agents.py          Agent runs, SSE streaming, submit/cancel
│   ├── audit.py           Admin-only audit log queries
│   ├── deps.py            DI layer: get_db, get_current_user, require_role,
│   │                        service factories (TaskService, ArticleService, etc.)
│   ├── errors.py          Centralized exception handlers (ErrorResponse factory methods)
│   └── security_headers.py HSTS, CSP-RO, X-Frame, Referrer-Policy
├── services/              Business logic layer
│   ├── agent_runtime_service.py  Run lifecycle, SSE streaming, cancellation
│   ├── llm/router.py      Provider routing with fallback chains
│   ├── llm/providers/     OpenAI, Anthropic, Ollama, Compatible
│   ├── embedding/         Embedding client + provider abstraction
│   ├── vector/qdrant.py   Qdrant vector store client
│   ├── rag/               Retriever + Generator
│   ├── ingestion/         Article deduplication + persistence
│   ├── knowledge_service.py  KnowledgeItem creation + embedding
│   └── user_service.py    Registration + authentication
├── workflows/
│   ├── graph/builder.py   Daily intelligence graph (research → analyst → translator)
│   ├── autonomous_intelligence.py Full pipeline (6 nodes via LangGraph)
│   ├── executor.py        SyncExecutor background execution protocol
│   └── registry.py        Direct-import pipeline registry
├── agents/                8 agent definitions (Research, Analyst, Translator,
│                           Knowledge, Notification, ProjectManager, Pronunciation)
├── mcp/                   Model Context Protocol integration
│   ├── registry.py        Server + tool discovery
│   └── servers/{github,notion,browser,asana}/  4 MCP server integrations
├── events/                Event publisher/subscriber (AuditLogEvent, ArticleCreatedEvent)
├── workers/               APScheduler-based job scheduling
│   ├── scheduler/scheduler.py
│   └── jobs/              Daily intelligence + Autonomous intelligence jobs
├── schemas/
│   ├── response.py        APIResponse[T] envelope (success/data/error)
│   ├── error.py           ErrorResponse {code, message, details} + factory methods
│   └── *.py               Per-resource request/response schemas
└── prompts/*.md           10 prompt template files
```

### Frontend (`frontend/`) — 684 lines TypeScript/TSX

```
app/
├── layout.tsx             Root layout with Providers
├── page.tsx               Home (tabbed dashboard: dashboard/articles/knowledge/tasks/agents/reports)
├── login/page.tsx         Auth form
└── register/page.tsx      Registration + auto-login

components/ui/             9 custom UI components (Button, Input, Select, Textarea, Card, Badge, Table, Modal, StatCard)
components/panels/         6 panel components (Dashboard, Articles, Tasks, Knowledge, Agents, Reports)
components/articles/       ArticleForm.tsx
components/tasks/          TaskForm.tsx
components/knowledge/      KnowledgeForm.tsx
components/reports/        ReportForm.tsx

hooks/
├── useArticles.ts         React Query: list, create, update
├── useTasks.ts            React Query: list, create, update
├── useKnowledge.ts        React Query: list, create, update
├── useReports.ts          React Query: list, create
├── useAgentRuns.ts        React Query: list, submit, cancel, refresh
├── useDelete.ts           React Query: delete article/task/knowledge
└── useAgentStream.ts      SSE + polling fallback for agent run progress

lib/
├── api.ts                 Fetch wrapper + ApiError class + unwrap helpers
├── auth-context.tsx       AuthProvider: login/logout/refresh, JWT token management
├── auth-storage.ts        localStorage token/user persistence (SSR-safe)
├── query-client.ts        TanStack Query client (retry: 1, staleTime: 60s)
└── toast.tsx              Simple toast notification system (success/error/info)

types/index.ts             6 domain types (Article, KnowledgeItem, AgentRun, Task, IntelligenceReport, AgentInfo)
middleware.ts              Route protection middleware (client-side auth is primary guard)
```

### Data Layer

- **Database**: PostgreSQL 14 (asyncpg), SQLAlchemy 2.0 ORM
- **Migrations**: Alembic (6 migrations)
- **Vector Store**: Qdrant (semantic search over KnowledgeItems)
- **Cache/Rate Limiting**: Redis (slowapi limiter, proxy-aware key_func)
- **Auth**: JWT (python-jose + bcrypt), 30-minute access tokens
- **LLM**: Multi-provider router with fallback chains (OpenAI, Anthropic, Ollama, Compatible)
- **Workflow Engine**: LangGraph StateGraph for daily intelligence and autonomous pipelines

### Tools & Pipelines

- **tools/** — `ToolBase` abstraction + `ToolRegistry` (local tools + MCP tool lookup)
- **pipelines/** — `ArticlePipeline` orchestrator (fetch → research → analyze → translate → knowledge)

### Events

- **events/event.py** — `AuditLogEvent`, `ArticleCreatedEvent`, `BaseEvent`, `AuditAction` enum
- **events/agent_event.py** — Agent-specific event types
- **events/publisher.py** — Subscriber registry + dispatch loop
- **events/subscriber.py** — `AuditLogSubscriber` (persists events to DB)

---

## 3. Key Architectural Decisions During Phase 6-F.4A

### Decision 1: Unified `ErrorResponse` shape replaces ad-hoc strings

**Before:** Exception handlers returned `{"success": false, "data": null, "error": "string"}`. The `ErrorResponse` Pydantic model existed only for OpenAPI documentation and never matched the runtime output.

**After:** All handlers return `{code, message, details}` via `ErrorResponse.model_dump()`. The schema now matches what's documented in each router's `responses={}` OpenAPI dict, closing the spec/runtime gap.

### Decision 2: Factory methods on `ErrorResponse` for deterministic code mapping

- `from_http_exception()` maps HTTP status codes to machine-readable codes (e.g., 404 → `NOT_FOUND`, 409 → `CONFLICT`)
- `from_validation_error()` extracts per-field validation errors into `details[]` with `{field, message}` structure
- `from_rate_limit_exceeded()` was added as a dedicated handler (was previously using slowapi's default format)
- `from_unhandled_exception()` never leaks internals — always returns `"Internal server error"`

### Decision 3: Frontend `ApiError` preserves backward compatibility

- The fetch wrapper tries `body.message` first (new envelope), then falls back to `body.error` and `body.detail`
- `ApiError` extends `Error` so existing `err instanceof Error` checks in all form components continue to work
- `err.message` still contains the human-readable message for toast/banner display

### Decision 4: Fixed the one inconsistent route

`agents.py:get_agent_run` was returning `APIResponse(success=False, ...)` directly instead of raising `HTTPException(404)`. Now uses the standard raise pattern, which flows through the centralized handler and produces a proper `ErrorResponse`.

### Decision 5: Removed stale duplicate `ErrorResponse`

The `ErrorResponse` class in `backend/models.py` had a different shape (`detail: str`, `code: str`) and was never imported anywhere. Removed to eliminate ambiguity.

---

## 4. Remaining Technical Debt / Cleanup Items

| Item | Location | Severity | Notes |
|---|---|---|---|
| `get_session_factory` compat stub | `routers/deps.py:212` | Low | Dead code left for test patch compatibility; can be removed once tests exist |
| `PIPELINE_MAP` comment | `workflows/registry.py:3` | Trivial | Documentation-only reference to prior pattern |
| `"success": False` in internal dicts | `agents/base.py:85`, `workflows/base.py:90,107` | Low | Internal workflow result dicts, not API responses — out of scope for A4 |
| `X-Request-ID` not in error body | `routers/errors.py` | Low | Header is set on all responses via `LogMiddleware`, but error response body doesn't include it for client-side debugging |
| No backend test suite | `backend/tests/` | Medium | 0 tests collected; pytest config exists but no test files |
| No React error boundary | Frontend | Medium | Rendering crashes show Next.js default overlay |
| Silent auth refresh failure | `auth-context.tsx:84` | Low | Catches and logs out silently on failure |
| Silent SSE poll failure | `useAgentStream.ts:77` | Low | Silently retries next interval |
| No global React Query error handler | `query-client.ts` | Low | Failed queries produce no user-visible feedback |
| `unwrap`/`unwrapSingle` don't check `success` field | `api.ts:66-85` | Low | Extracts `data` regardless of `success` flag — works for current usage |
| No frontend config files | Frontend root | Low | No `.eslintrc.json`, `next.config.mjs`, or `tailwind.config.ts` — project uses Next.js defaults + `@tailwindcss/postcss` plugin |
| Loose frontend types | `types/index.ts` | Info | All domain types use `& Record<string, unknown>` spread, accepting any extra fields from the backend |

---

## 5. Recommended Next Development Phase

### Priority 1: Test Infrastructure (B1)

**Why:** Zero tests exist despite a mature codebase. Every subsequent change needs regression coverage.

**Scope:**
- Backend unit tests for service layer (user_service, article_service, task_service)
- Router integration tests with real DB (testcontainers or SQLite in-memory)
- Frontend component tests for form components and hooks
- Error envelope contract tests (verify `ErrorResponse` shape at all handler boundaries)

**Impact:** Enables safe refactoring, validates A4 behavior, catches breaking changes early.

### Priority 2: Frontend Error UX (B2)

**Why:** `ApiError` now carries structured `code` and `details`, but the frontend doesn't use them yet.

**Scope:**
- Global React Query `onError` handler in `query-client.ts`
- Toast notifications for mutation failures (currently only delete shows toasts)
- Use `ApiError.code` to customize error banners (e.g., `VALIDATION_ERROR` → show per-field errors)
- React error boundary for graceful rendering crash recovery
- Non-silent handling of auth refresh failures and SSE polling failures

**Impact:** Consistent error display across all forms, better UX for auth/session issues, structured error propagation.

### Priority 3: MCP Server Health + Tool Retry (B3)

**Why:** MCP tools (Notion, Asana, GitHub, Browser) are called by agents without health checks or retry logic.

**Scope:**
- Add `health_check()` to each MCP server
- Circuit breaker pattern for tool calls
- Graceful degradation when external APIs are unavailable
- Structured error propagation through agent pipeline stages

**Impact:** More resilient autonomous pipelines, clearer failure attribution.

### Priority 4: Production Deployment Hardening (C6)

**Why:** The app has `APP_ENV=production` mode but lacks many production requirements.

**Scope:**
- Docker Compose for full stack (PostgreSQL + Redis + Qdrant + app)
- Gunicorn/uvicorn worker configuration
- Health check endpoints at `/api/health` (already partially implemented)
- Request ID propagation end-to-end (logged and returned as `X-Request-ID` header; not yet included in error response body for client-side debugging)
- Environment-specific CORS, logging levels, debug flags

**Impact:** Ready for containerized deployment.
