# Phase 6-E: API Hardening Plan

## Executive Summary

Phase 6-D.2 completed basic authentication (register/login/JWT) and Phase 6-D.3 will build the frontend auth UI. Phase 6-E hardens the backend API so it is production-ready for authenticated users. Five workstreams, estimated 10-14 days.

---

## Current Architecture Assessment

### What exists
- **JWT auth**: HS256, 30-min expiry, `sub` claim = user UUID. Access token only (no refresh).
- **Endpoints**: 19 routes across 6 routers (`auth`, `articles`, `knowledge`, `tasks`, `agents`, `reports`). Write routes require `Depends(get_current_user)`. All read routes are public.
- **Error handling**: Global exception handlers return `{success, data, error}` format. Custom `NotFoundException` and `BadRequestException`.
- **OpenAPI**: Every endpoint has `summary`, `description`, `operation_id`, `response_model`. Swagger at `/api/docs`, ReDoc at `/api/redoc`.
- **Layered architecture**: Router -> Service -> Repository -> ORM Model. Clean separation.

### What is missing (gaps)

| Gap | Severity | Impact |
|-----|----------|--------|
| No `user_id` on any resource table | Critical | Cannot scope data to users; no ownership enforcement |
| AgentRun has no user association | High | Cannot attribute agent runs to users; dashboard cannot filter |
| No audit logging | High | No compliance trail; cannot investigate incidents |
| JWT security scheme not declared in OpenAPI | Medium | Swagger UI shows no "Authorize" button; docs don't reflect auth requirements |
| Rate limiting absent | Medium | API vulnerable to brute-force on `/auth/login` and write endpoints |
| `require_role()` unused | Low | Role infrastructure exists but no route uses it |
| No input validation beyond Pydantic | Low | No content size limits, no payload sanitization |

---

## Workstream 1: OpenAPI JWT Security Documentation

**Goal**: Make the OpenAPI spec accurately describe the JWT auth flow so Swagger UI provides an "Authorize" button and clients can test authenticated endpoints directly.

### Changes needed

**File: `backend/main.py`** (lines 49-58)

Add `security_schemes` and `security` to the FastAPI constructor:

```python
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

app = FastAPI(
    title="AI Intelligence OS",
    version="0.1.0",
    description="Enterprise AI Intelligence Operating System",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
    # NEW: declare the JWT Bearer security scheme
    security_schemes=[
        {
            "bearerJwt": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT access token obtained from POST /api/v1/auth/login",
            }
        }
    ],
    security=[{"bearerJwt": []}],  # Apply globally (override per-route for public endpoints)
)
```

Then mark public endpoints (`/auth/register`, `/auth/login`, `/auth/health`) with `security=[]` to exclude them.

**File: `backend/routers/deps.py`** — Add a reusable security dependency:

```python
bearer_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
```

This allows the `get_current_user` dep to be optional (for public+protected hybrid routes).

**File: `backend/routers/auth.py`** — Update login endpoint:

- Change `token: str` query param on `/auth/me` to use `Depends(oauth2_scheme)` instead of manual decoding
- This aligns `/auth/me` with the standard auth pattern used by all other protected routes
- Remove the manual JWT decode logic (lines 70-76) and use `Depends(get_current_user)` instead

**File: `backend/schemas/response.py`** — Add error response models:

```python
class ErrorResponse(BaseModel):
    success: Literal[False]
    data: None
    error: str
```

Add `responses={401: {"model": ErrorResponse, "description": "Unauthorized"}, ...}` to all protected endpoints so Swagger shows the auth failure path.

### Files affected
- `backend/main.py`
- `backend/routers/deps.py`
- `backend/routers/auth.py`
- `backend/schemas/response.py`
- All 6 router files (add `responses` dict to protected endpoints)

### Acceptance criteria
- Swagger UI shows "Authorize" button
- Clicking it prompts for a bearer token
- Protected endpoints show a lock icon; public endpoints show an open icon
- 401/403 error responses documented in OpenAPI spec
- `curl` from Swagger works end-to-end

---

## Workstream 2: Audit Logging System

**Goal**: Record every mutation (create/update/delete) with who did it, what changed, and when.

### Design

Two-tier approach:

**Tier 1: Request-level audit middleware** — logs every request to a database table.
**Tier 2: Domain event persistence** — captures structured change events via the existing event system.

### Tier 1: Audit Log Table

**New file: `backend/database/models/audit_log.py`**

```python
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)  # CREATE, UPDATE, DELETE, LOGIN, LOGOUT
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # article, agent_run, user
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    changes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # diff before/after
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
```

**New file: `backend/repositories/audit_log_repository.py`** — Standard BaseRepository subclass.

**New file: `backend/services/audit_service.py`**

```python
class AuditService:
    async def log(self, user_id, action, resource_type, resource_id, changes=None, request=None)
    async def get_user_logs(user_id, limit=50, offset=0)
    async def get_all_logs(limit=50, offset=0, resource_type=None)
```

**Middleware: `backend/routers/audit_middleware.py`**

Replace the current `_log_request` middleware in `errors.py` with one that:
1. Extracts `X-Forwarded-For` or `client.host` for IP
2. Extracts `User-Agent` header
3. Attaches user info from request state (set by auth dep)
4. Async-writes to audit log AFTER the response is sent

### Tier 2: Persist domain events

Connect the existing event system (`backend/events/`) to the audit service:

- `ArticleCreatedEvent` -> `AuditService.log(action="CREATE", resource_type="article")`
- `ArticleUpdatedEvent` -> `AuditService.log(action="UPDATE", resource_type="article", changes=diff)`
- `ArticleDeletedEvent` -> `AuditService.log(action="DELETE", resource_type="article")`

Add similar events for knowledge, tasks, reports, and agent runs.

### New API endpoint

**File: `backend/routers/audit.py`** (new router)

```
GET  /audit/logs          - List audit logs (admin only, requires role=admin)
GET  /audit/logs/{id}     - Get single audit log entry
```

### Files affected
- `backend/database/models/audit_log.py` (new)
- `backend/repositories/audit_log_repository.py` (new)
- `backend/services/audit_service.py` (new)
- `backend/routers/audit.py` (new)
- `backend/routers/errors.py` (modify middleware)
- `backend/main.py` (register audit router + middleware)
- `backend/events/*.py` (wire events to audit service)

### Acceptance criteria
- Every POST/PUT/DELETE creates an audit log row
- Logs include user_id, action, resource type/id, IP, timestamp
- Admin can query audit logs via API
- Domain events trigger audit entries automatically

---

## Workstream 3: User Ownership for AgentRun & Resources

**Goal**: Associate all user-created resources with their creator. Enable per-user data scoping.

### Database changes

**Migration: Add `user_id` column to resource tables**

Tables needing `user_id`:
- `agent_runs` — the user who triggered the run
- `articles` — the user who created it
- `knowledge_items` — the user who created it
- `tasks` — the user who created it
- `reports` — the user who created it
- `workflows` — the user who created it
- `agents` — the user who created it (if applicable)

**New file: `backend/database/models/mixins/owned.py`**

```python
from sqlalchemy import ForeignKey, Uuid

class OwnedMixin:
    """Mixin for user-owned resources."""
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
```

Apply this mixin to all resource models. For `agent_runs`, add the FK and relationship:

```python
# In agent_run model
user = relationship("User", back_populates="agent_runs")
```

Add `agent_runs` relationship to User model:

```python
# In user model
agent_runs = relationship("AgentRun", back_populates="user", foreign_keys="AgentRun.user_id")
```

### Service layer changes

**File: `backend/services/agent_service.py`**

Modify `run_agent()`:

```python
async def run_agent(self, agent_id: str, input_payload: dict | None, user_id: uuid.UUID):
    kwargs = {
        ...
        "user_id": user_id,
    }
```

Update all service methods to accept `user_id` parameter.

**File: `backend/routers/agents.py`**

Pass `current_user.id` to the service:

```python
result = await service.run_agent(agent_id, input_payload=body, user_id=current_user.id)
```

### Query scoping

All list/get endpoints for owned resources should scope by user:

```python
# In repositories, add:
async def list_by_user(self, user_id: uuid.UUID, offset=0, limit=20):
    query = self.base_query().where(self.model.user_id == user_id)
    return await self.list(offset, limit, query=query)
```

For Phase 6-E, scope the user's own resources. Public read endpoints (list articles, list agent runs) remain global for now — future phase adds a `?scope=user|global` param.

### Files affected
- `backend/database/models/user.py` (add agent_runs relationship)
- `backend/database/models/agent_run.py` (add user_id FK)
- `backend/database/models/article.py` (add user_id FK)
- `backend/database/models/knowledge_item.py` (add user_id FK)
- `backend/database/models/task.py` (add user_id FK)
- `backend/database/models/report.py` (add user_id FK)
- `backend/services/*_service.py` (all services accept user_id)
- `backend/routers/*.py` (all write endpoints pass current_user.id)
- `backend/repositories/*.py` (add list_by_user methods)
- Alembic migration for all schema changes

### Acceptance criteria
- Every new resource has a non-null `user_id`
- Agent runs are attributable to the triggering user
- User's dashboard shows only their own resources
- Existing seed data gets `user_id` populated

---

## Workstream 4: API Error & Security Improvements

### 4a: Rate Limiting

**File: `backend/routers/rate_limit.py`** (new)

Use the already-installed `slowapi` dependency:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

def ratelimit(key_func=None, limit="20/minute", window="1m", bucket="minute"):
    """Decorator for rate-limited endpoints."""
    from starlette.requests import Request
    async def wrapper(request: Request, *args, **kwargs):
        request.state.rate_limit = limiter.parse(limit)[0]
        request.state.rate_limit_durations = limiter.parse(limit)[1]
        return await limiter._limit_func(request, key_func or get_remote_address)
    return wrapper
```

Apply to sensitive endpoints:
- `POST /auth/login` — 10/minute (brute-force protection)
- `POST /auth/register` — 5/hour (account spam protection)
- `POST /agents/{id}/run` — 30/minute (agent run rate limit)
- All other write endpoints — 60/minute

### 4b: Input Validation

**File: `backend/schemas/agent_run.py`** — Replace raw `dict[str, Any]` with typed schema:

```python
class AgentRunInput(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    context: dict[str, Any] = Field(default_factory=dict)
```

Update the `/agents/{agent_id}/run` endpoint to use this typed body instead of `dict[str, Any] | None`.

### 4c: Error Response Consistency

Standardize all error responses across all routers to use the same shape:

```json
{
    "success": false,
    "data": null,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Agent not found",
        "details": null
    }
}
```

Add `error_code` to custom exceptions so the error response includes machine-readable codes.

### 4d: CORS Hardening

**File: `backend/main.py`** — Allow multiple origins for dev/prod:

```python
allow_origins=settings.cors_origins.split(",") if settings.cors_origins else ["http://localhost:3000"]
```

Add `settings.cors_origins` to config. In production, set to the actual frontend URL. Never use `"*"` with `allow_credentials=True`.

### 4e: Security Headers

**File: `backend/routers/security_headers.py`** (new middleware)

Add these headers to every response:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Cache-Control: no-store` (on auth endpoints)

### Files affected
- `backend/routers/rate_limit.py` (new)
- `backend/routers/auth.py` (apply rate limits)
- `backend/routers/agents.py` (typed body schema)
- `backend/schemas/agent_run.py` (add typed input schema)
- `backend/routers/errors.py` (add error codes, security headers middleware)
- `backend/main.py` (CORS config, security headers)
- `backend/config.py` (add cors_origins setting)

### Acceptance criteria
- `/auth/login` returns 429 after 10 failed attempts in 1 minute
- Agent run input is validated against a typed schema (not raw dict)
- All error responses include machine-readable error codes
- CORS rejects requests from unauthorized origins
- Security headers present on all responses

---

## Workstream 5: Production Readiness Checklist

### 5a: Health Check Enhancement

**File: `backend/main.py`** — Upgrade health endpoint:

```python
@app.get("/api/health")
async def health_check(db=Depends(get_db)):
    """Check database connectivity and overall system health."""
    try:
        async with db.begin():
            await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"

    return {
        "status": "ok" if db_status == "healthy" else "degraded",
        "database": db_status,
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
```

### 5b: Configuration Management

**File: `backend/config.py`** — Add missing production settings:

```python
cors_origins: str = "http://localhost:3000"
jwt_refresh_token_expire_days: int = 7
debug: bool = False
log_level: str = "INFO"
allowed_hosts: str = "*"
```

### 5c: Database Migration Strategy

Create Alembic migrations for all schema changes:
1. Add `user_id` columns to all resource tables
2. Create `audit_logs` table
3. Backfill existing data with `user_id` from seed data

### 5d: Docker/Deployment Config

**File: `docker-compose.yml`** — Add production environment variables:
- `JWT_SECRET_KEY` (generated, not hardcoded)
- `CORS_ORIGINS` (frontend URL)
- `DATABASE_URL` (production DB)

**File: `Dockerfile.backend`** — Verify multi-stage build works with all dependencies including `slowapi`.

### 5e: Monitoring Hooks

**File: `backend/routers/errors.py`** — Add structured logging for errors:

```python
logger.error(
    "error=%s method=%s path=%s status=%d user_id=%s duration=%.3f",
    exc.__class__.__name__, request.method, request.url.path,
    status_code, user_id, elapsed,
)
```

This enables log aggregation tools (Datadog, CloudWatch, etc.) to parse and alert on errors.

### Files affected
- `backend/main.py` (health check)
- `backend/config.py` (production settings)
- `backend/routers/errors.py` (structured error logging)
- `docker-compose.yml` (env vars)
- `Dockerfile.backend` (verify deps)
- Alembic migration files

### Acceptance criteria
- `/api/health` checks DB connectivity and returns structured JSON
- All secrets loaded from env vars (no hardcoded secrets)
- Docker Compose has production-ready env var templates
- Error logs are structured JSON suitable for log aggregation

---

## Implementation Order & Dependencies

```
Phase A: Workstream 1 (OpenAPI JWT docs)
  -> No blockers. Can start immediately.
  -> Estimated: 1 day

Phase B: Workstream 3 (User ownership)
  -> Blocks Workstream 2 (audit needs user_id) and Workstream 4 (typed schemas)
  -> Database migrations first, then service/router changes
  -> Estimated: 3-4 days

Phase C: Workstream 2 (Audit logging)
  -> Depends on user_id being present
  -> Middleware + event wiring
  -> Estimated: 2-3 days

Phase D: Workstream 4 (Error/Security improvements)
  -> Independent but benefits from having typed schemas from Phase B
  -> Rate limiting, CORS, input validation, error codes
  -> Estimated: 2-3 days

Phase E: Workstream 5 (Production readiness)
  -> Final polish: health checks, config, docker, monitoring
  -> Estimated: 1-2 days
```

Total: 9-13 days. Parallelize Phases A and B where possible.

---

## Risk Register

| Risk | Mitigation |
|------|-----------|
| Adding `user_id` FK breaks existing seed data | Write migration backfill script; test on staging DB first |
| Rate limiting may block legitimate traffic during development | Make limits configurable via env vars; higher limits in dev mode |
| Audit middleware adds latency to every request | Async write to queue; flush batched to DB periodically |
| CORS changes may break local dev workflow | Default `cors_origins` includes localhost:3000; document override |
| JWT-only auth has no logout mechanism | Implement token blacklist table; add `/auth/logout` endpoint |

---

## Out of Scope (deferred to Phase 6-F)

- Refresh token mechanism (access token expiry = 30 min is acceptable for MVP)
- OAuth2/social login providers
- API versioning strategy (currently hardcoded to `/api/v1`)
- GraphQL support
- Webhook notifications for audit events
- RBAC beyond `user`/`admin` roles
- API key authentication for service-to-service calls
- Request/response body logging (privacy/compliance risk)
