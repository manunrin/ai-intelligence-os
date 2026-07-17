# Phase 6-F Implementation Plan

## Executive Summary

Phase 6-F is the integration and hardening phase that bridges the completed backend API foundation (Phases 6-A through 6-E) with a functional frontend experience and operational readiness. The backend now has a complete layered architecture (Router -> Service -> Repository), authenticated write operations, user-scoped data ownership, audit logging, rate limiting, security headers, structured logging, and production-ready Docker Compose with Postgres, Redis, Qdrant, and MinIO. The remaining work focuses on frontend integration, closing backend gaps, and preparing for production deployment.

---

## 1. Completed Architecture Summary

### Phase 6-D.1: Backend Write Operations
- POST/PUT/DELETE endpoints for articles, tasks, knowledge items, reports
- `POST /agents/{id}/run` endpoint for agent execution triggers
- Pydantic v2 input schemas (`TaskCreate`, `TaskUpdate`, `ReportCreate`, `ArticleCreate`, `KnowledgeCreate`) with validation
- Full Router -> Service -> Repository layering maintained across all write operations
- 85+ unit tests added (203 total test count at completion)

### Phase 6-D.2: Authentication & Authorization
- `User` model with bcrypt password hashing via `passlib`
- JWT access token generation (HS256, 30-min expiry) and verification
- Registration (`POST /auth/register`) and login (`POST /auth/login`) endpoints
- `get_current_user` FastAPI dependency — extracts Bearer token from `Authorization` header, validates against DB
- `require_role()` dependency factory for future RBAC enforcement
- Alembic migration for users table creation
- All write endpoints protected behind `Depends(get_current_user)`
- Read endpoints remain public (scoped by user_id in service layer)

### Phase 6-E.1: OpenAPI JWT Security Documentation
- Custom `openapi()` method on FastAPI app declares `Bearer` security scheme in components
- Public paths (`/auth/register`, `/auth/login`, `/health`, `/live`) explicitly excluded from auth requirement
- Protected endpoints auto-marked with `{"Bearer": []}` security requirement
- Swagger UI shows lock icons on protected endpoints

### Phase 6-E.2: Audit Logging System
- `AuditLog` model with user_id, action, resource_type, resource_id, changes (JSONB), IP, user-agent
- `audit_router` at `/admin/audit-logs` with filtering by action, resource_type, user_id, date range
- Admin-only access via `require_role("admin")`
- `AuditStatsResponse` endpoint with period aggregation (24h/7d/30d/90d)
- Event publisher wired to `AuditLogSubscriber` in bootstrap — persists domain events to DB
- `AuditAction` enum: CREATE, UPDATE, DELETE, AGENT_RUN, LOGIN

### Phase 6-E.3: User Ownership for Resources
- `user_id` FK (nullable, SET NULL on delete) added to all resource tables:
  - `agent_runs`, `articles`, `knowledge_items`, `tasks`, `intelligence_reports`
- Bidirectional ORM relationships on `User` model: `articles`, `tasks`, `knowledge_items`, `reports`, `agent_runs`
- All service methods accept `user_id` parameter
- Repository `list_by_user()` methods for scoped queries
- Agent run creation passes `current_user.id` from router

### Phase 6-E.4: API Error & Security Improvements
- **Rate limiting**: `slowapi` with Redis storage + in-memory fallback; configurable limits via env vars
- **CORS**: Environment-aware — defaults to localhost:3000, overridable via `CORS_ALLOWED_ORIGINS`
- **Security headers**: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, HSTS toggle
- **Error responses**: Consistent `{success: false, data: null, error: "..."}` format via centralized handlers
- **Health check**: `/api/health` verifies database connectivity via asyncpg; returns 503 if unhealthy
- **Liveness probe**: `/api/live` always returns 200
- **Request IDs**: `X-Request-ID` attached to every request/response for tracing
- **Structured logging**: JSON log records via `logging_config.make_request_log_record()`

---

## 2. Remaining Backend Gaps

### Gap 1: Agent Execution Pipeline (Critical)
**Current state**: `AgentService.run_agent()` creates an `AgentRun` record with status "running" and publishes an audit event, but does NOT actually invoke the agent's LangGraph workflow or LLM calls. The agent instances exist in `bootstrap.get_agents_with_mcp()` but are never called from the API.

**Impact**: The `/agents/{id}/run` endpoint is a stub — it records intent but produces no intelligence output. The dashboard's Agent Runs tab shows "running" forever.

**Work needed**:
- Wire `AgentService.run_agent()` to actually invoke the appropriate agent's execute method
- Implement async execution with status updates (running -> completed/failed)
- Handle agent errors gracefully (capture traceback in `error_message`)
- Support both synchronous (fast agents) and asynchronous (long-running) execution modes
- Pass `input_payload` through agent's processing pipeline

### Gap 2: No Refresh Token Mechanism (Medium)
**Current state**: JWT access tokens expire after 30 minutes with no refresh mechanism. Users must re-login when their token expires.

**Impact**: Poor UX for dashboard usage; session loss mid-work.

**Work needed**:
- Add `refresh_tokens` table with FK to users, expiry, is_revoked flag
- `POST /auth/refresh` endpoint accepting refresh token, returning new access token
- `POST /auth/logout` endpoint revoking refresh token
- Optional: sliding expiry on refresh tokens

### Gap 3: Missing Delete Endpoints (Low-Medium)
**Current state**: Articles router has no DELETE endpoint. Knowledge items have no DELETE. Tasks have no DELETE. Reports have no DELETE. Only articles have a PUT (update).

**Impact**: Users cannot remove their own content. The write operations plan included DELETE but only partial implementation exists.

**Work needed**:
- `DELETE /articles/{id}` with soft-delete or hard-delete option
- `DELETE /knowledge/{id}`
- `DELETE /tasks/{id}`
- `DELETE /reports/{id}`
- All requiring `get_current_user` ownership check

### Gap 4: Article Update Endpoint Incomplete (Low)
**Current state**: Articles router has `PUT /articles/{id}` but no PATCH endpoint for partial updates. Input schema validation may not cover all mutable fields.

**Work needed**:
- Add `PATCH /articles/{id}` for partial updates
- Ensure update endpoint validates user ownership

### Gap 5: No Background Task Queue (Medium)
**Current state**: Agent runs are created synchronously in the request handler. Long-running agents would block HTTP connections. No Celery/RQ/Bull queue.

**Impact**: Cannot support agents that take more than a few seconds. Dashboard will hang during agent execution.

**Work needed**:
- Choose task queue (RQ is simplest — already has Redis available)
- Create `enqueue_agent_run()` background task
- Add polling endpoint `GET /agents/runs/{run_id}/status` for clients to check progress
- WebSocket or SSE for real-time status updates (deferred to later)

### Gap 6: Seed Data / Bootstrap Script (Low)
**Current state**: No script to seed initial admin user or sample data. New deployments start completely empty.

**Work needed**:
- Bootstrap script creating default admin user (from env vars)
- Optional: seed sample agents, sources, articles for demo purposes

### Gap 7: No Migration Version Tracking Visible (Low)
**Current state**: Alembic config exists (`backend/alembic/`) but no migration files visible in `migrations/versions/`. It's unclear if migrations have been generated for the `user_id` columns and `audit_logs` table.

**Work needed**:
- Verify all schema changes have corresponding migration files
- Ensure `alembic upgrade head` works cleanly on fresh database

---

## 3. Frontend Integration Status

### Current State
| Area | Status | Details |
|------|--------|---------|
| Layout | Basic | Single `page.tsx` with header, stats row, tab navigation |
| Components | Minimal | 6 UI components: Badge, Button, Card, Input, StatCard, Table |
| Data fetching | Read-only | Concurrent fetch of 5 endpoints on mount via `api.get()` + `unwrap()` |
| Auth UI | **None** | No login page, no token storage, no auth header attachment |
| Write operations | **None** | No forms, no mutation hooks, no optimistic updates |
| Real-time | **None** | Polling-based only; no SSE/WebSocket |
| Error handling | Basic | Catches fetch errors, shows banner |
| Routing | Single page | Tab-based navigation, no Next.js pages/routing |
| TypeScript types | Partial | Types exist in `types/index.ts` but don't match backend response envelope |
| API client | Basic | `fetch` wrapper with no auth header support, no interceptors |

### Critical Frontend Gaps

**Gap F1: Authentication UI (Critical)**
- Login page at `/login` with username/password form
- Token storage in httpOnly cookie or localStorage
- API client middleware to attach `Authorization: Bearer <token>` header
- Protected route logic — redirect unauthenticated users to login
- Logout button in header
- Current user display (username/avatar placeholder)

**Gap F2: Write Operation UI (High)**
- Article creation form (title, content, source URL)
- Knowledge item creation form
- Task creation/editing form
- Report viewing detail page
- Agent run trigger UI with input form
- Delete confirmations with toast notifications

**Gap F3: Type Synchronization (Medium)**
- Frontend types (`Article`, `AgentRun`, `Task`, etc.) don't account for new backend fields: `user_id`, `duration_ms`, `embedding_*`, `priority`, `status` variations
- `unwrap()` helper assumes array data but backend returns `{ success, data, error }` envelope
- Need generated types from OpenAPI spec or shared schema definitions

**Gap F4: Dashboard Enhancements (Medium)**
- Auth status indicator in header (replacing current "Connected/Offline" badge)
- Per-user resource counts in stat cards
- Empty states with clear CTAs ("Create your first article")
- Loading skeletons instead of generic pulse animation

---

## 4. Agent Execution Pipeline Status

### Architecture Overview
```
Bootstrap (startup)
  -> MCPRegistry(Notion, Asana, Browser, GitHub)
  -> ToolRegistry (wired to MCP)
  -> EventPublisher (wired to AuditLogSubscriber)
  -> get_agents_with_mcp() returns dict[name, Agent]

AgentService.run_agent(agent_id, input_payload, user_id)
  -> Creates AgentRun record (status="running")
  -> Publishes AuditLogEvent
  -> [MISSING: Actually invokes agent.execute(input_payload)]
  -> Returns run record

Agents defined in bootstrap:
  - knowledge: KnowledgeAgent (MCP + notion_database_id)
  - research: ResearchAgent (MCP)
  - project_manager: ProjectManagerAgent (MCP + asana_project_id)
  - notification: NotificationAgent (MCP)
```

### Current Deficiencies
1. **No invocation path**: `AgentService.run_agent()` never calls `self._agents[agent_id].execute(...)`. The `_agents` dict isn't even stored on the service.
2. **No result capture**: Even if invoked, there's no mechanism to update `output_payload` and `finished_at` on the `AgentRun` record.
3. **No error propagation**: Agent exceptions would crash the request handler without updating the run status to "failed".
4. **No pipeline chaining**: The autonomous pipeline (research -> analyze -> translate -> knowledge -> tasks) exists as LangGraph StateGraph builders but isn't wired into any API endpoint.
5. **Agent config from env**: Notion database ID, Asana project ID are hardcoded as empty strings in bootstrap.

### Recommended Approach
- Store agent instances on `AgentService` during initialization (injected from `app.state.bootstrap`)
- `run_agent()` calls `agent.execute(input_payload)` synchronously for fast agents
- Wrap in try/except to set status to "failed" and capture error message
- For long-running agents, use background task queue (see Gap 5 above)
- Add `POST /workflows/run` endpoint for LangGraph pipeline execution

---

## 5. Database Maturity Assessment

### Schema Completeness: 95%
All required models exist with proper relationships:
- `User` --1:N--> `Article`, `Task`, `KnowledgeItem`, `IntelligenceReport`, `AgentRun`
- `Source` --1:N--> `Article`
- `Agent` --1:N--> `AgentRun`
- `AgentRun` --1:N--> `IntelligenceReport`, `Task`
- `Workflow` --1:N--> `AgentRun`
- `AuditLog` -- standalone with indexes on user_id, resource_type, created_at

### Indexing: Good
- `user_id` indexed on all resource tables
- `resource_type`, `created_at` indexed on audit_logs
- UUID primary keys on all tables

### Constraints: Adequate
- Foreign keys with appropriate ON DELETE behavior (CASCADE for owned resources, SET NULL for audit trail)
- Check constraint on report importance_score range
- Unique constraints on username and email

### Migration State: Needs Verification
- Alembic config present but migration files need audit
- Need to verify: do migrations for `user_id` columns and `audit_logs` table exist and are applied?
- Fresh `docker compose up` should produce a clean database with all tables

### Recommendations
- Run `alembic heads` and `alembic history` to verify migration completeness
- Add migration for refresh_tokens table (Phase 6-F work)
- Consider adding soft-delete pattern (deleted_at column) for audit compliance

---

## 6. Production Readiness Assessment

### Infrastructure: 80% Ready
| Component | Status | Notes |
|-----------|--------|-------|
| Docker Compose | Complete | 6 services with healthchecks, restart policies, resource limits |
| PostgreSQL | Complete | Persistent volume, init SQL, connection pooling |
| Redis | Complete | Used for rate limiting (slowapi) |
| Qdrant | Complete | Vector search (not yet fully wired to app) |
| MinIO | Complete | Object storage (not yet wired to app) |
| LiteLLM Gateway | Configured | Not included in docker-compose (opt-in) |
| Environment variables | Complete | `.env.example` covers all services |

### Security: 70% Ready
| Area | Status | Notes |
|------|--------|-------|
| Password hashing | Good | bcrypt via passlib |
| JWT | Adequate | HS256, 30-min expiry, no refresh |
| Rate limiting | Good | Redis-backed, configurable per-endpoint |
| CORS | Good | Environment-aware, no wildcard in production |
| Security headers | Good | HSTS optional, X-Frame-Options, nosniff |
| Input validation | Good | Pydantic schemas on all write endpoints |
| SQL injection | Good | SQLAlchemy ORM parameterized queries |
| XSS | Partial | Backend is API-only; frontend needs sanitization |
| Auth UI | Missing | No login page, no token management |
| HTTPS | Partial | HSTS header available but requires external TLS termination |

### Observability: 50% Ready
| Area | Status | Notes |
|------|--------|-------|
| Structured logging | Good | JSON log records with request IDs |
| Health checks | Good | Liveness + readiness with DB check |
| Audit logging | Good | Full audit trail with filtering |
| Request tracing | Partial | Request IDs logged but no distributed tracing |
| Metrics | Missing | No Prometheus metrics endpoint |
| Error alerting | Missing | No integration with monitoring tools |

### Testing: 60% Ready
| Area | Status | Notes |
|------|--------|-------|
| Unit tests | Good | ~2658 lines across routers and services |
| Integration tests | Partial | Only MCP autonomous workflow test exists |
| E2E tests | Missing | No Playwright or similar |
| Test coverage | Unknown | No coverage reporting configured |

### Deployment: 40% Ready
| Area | Status | Notes |
|------|--------|-------|
| Docker builds | Good | Multi-stage Dockerfiles exist |
| CI/CD | Missing | No GitHub Actions or equivalent |
| Staging env | Missing | Only dev/prod distinction |
| Database backups | Missing | No backup strategy for Postgres/Qdrant |
| Rollback strategy | Missing | No versioned deployment |

---

## 7. Recommended Next Phase Roadmap

### Phase 6-F: Frontend Integration & Agent Pipeline (Recommended Next)

**Duration**: 10-14 days
**Priority**: P0 — This is the last gap between a working API and a usable product.

#### Workstream F1: Authentication UI (3 days)
- Login page at `/login` with form validation
- Token management: store in localStorage with auto-refresh awareness
- API client enhancement: intercept requests to attach Bearer token
- Protected routes: redirect unauthenticated users
- Logout functionality
- Current user display in header

#### Workstream F2: Write Operations UI (3 days)
- Article creation/edit form
- Knowledge item creation form
- Task creation/edit form with status transitions
- Report detail view
- Agent run trigger form with input payload builder
- Delete confirmation dialogs
- Toast notifications for success/error feedback

#### Workstream F3: Agent Execution Wiring (3 days)
- Wire `AgentService.run_agent()` to invoke actual agent logic
- Add result capture and status update (completed/failed)
- Add `GET /agents/runs/{run_id}` for run detail
- Add `GET /agents/runs/{run_id}/status` for polling
- Handle agent errors gracefully

#### Workstream F4: Frontend Polish (2 days)
- Fix type synchronization between frontend and backend
- Loading skeletons replacing pulse animations
- Empty states with clear CTAs
- Auth status indicator in header
- Responsive layout improvements

#### Workstream F5: Backend Hardening (2-3 days)
- Implement delete endpoints for all resources
- Add PATCH endpoint for articles
- Background task queue (RQ) for long-running agents
- Bootstrap script for admin user creation
- Verify and complete Alembic migrations

#### Acceptance Criteria
- [ ] User can log in, see their name, and log out
- [ ] Unauthenticated requests to protected API return 401
- [ ] User can create, edit, and delete articles, tasks, knowledge items
- [ ] Agent run from dashboard actually executes and shows result
- [ ] All frontend types match backend response shapes
- [ ] `make start` produces a fully functional app

---

### Phase 7: Observability & Production Deployment (After 6-F)

**Duration**: 7-10 days
- OpenTelemetry tracing across backend layers
- Prometheus metrics endpoint (/metrics)
- Grafana dashboard for key metrics
- GitHub Actions CI pipeline (lint, test, build)
- Database backup strategy
- Staging environment setup

---

### Phase 8: Advanced Features (Post 7)

**Duration**: Variable
- Refresh token mechanism
- OAuth2/social login
- RAG query endpoint (question answering over knowledge base)
- Vector search integration with Qdrant
- WebSocket/SSE for real-time agent status
- Email notifications
- Admin panel for user management

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Agent execution hangs blocking HTTP request | High | High | Implement background task queue (RQ) from day one |
| Frontend token storage vulnerability | Medium | Medium | Use httpOnly cookies; document security tradeoffs |
| Rate limiter Redis dependency causes fallback degradation | Low | Medium | In-memory fallback is functional; monitor for rate limit bypass |
| Frontend-backend type drift | High | Medium | Generate frontend types from OpenAPI spec using openapi-typescript |
| Missing E2E tests mask integration bugs | Medium | High | Prioritize critical path E2E tests (login -> create -> view) |
| No database backup strategy | Certain | Critical | Add pg_dump cron job in docker-compose before any production use |

---

## Out of Scope (Deferred to Phase 7+)

- GraphQL API layer
- API versioning strategy (still hardcoded to `/api/v1`)
- Kubernetes manifests / Helm charts
- Load testing and performance benchmarks
- OWASP security audit
- Mobile app or PWA support
- Multi-tenant isolation beyond user_id scoping
- Webhook notifications
- Advanced RBAC (currently user/admin only)
- Service-to-service API keys
