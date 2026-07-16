# Lessons Learned — Phases 1 to 6-C

**Date:** 2026-07-16

## Major Problems Encountered

### 1. Database Model `_utcnow` Import Failures
**Problem:** Multiple model files imported `_utcnow` from different paths (`from ..database.base import _utcnow` vs `from ...database.base import _utcnow`). After refactoring, some models had incorrect relative import depths causing `ImportError` at runtime.

**Root Cause:** The database models directory was reorganized into a subpackage (`models/`) but not all model files updated their relative imports consistently. Some used 2-level (`..`), others used 3-level (`...`) parent references.

**Solution:** Standardized all models to use `from ...database.base import Base, _utcnow` (3 levels for models inside `backend/database/models/`). Added `_utcnow()` as a function rather than a lambda for clarity.

**Prevention:** Use absolute imports in new models: `from backend.database.base import _utcnow`. Run `mypy .` after any model file creation to catch import errors immediately.

---

### 2. SQLAlchemy Relationship Foreign Key Ambiguity
**Problem:** Tables with multiple FK relationships to the same table (e.g., `AgentRun` related to both `agents` and `workflows`, `Task` related to `agent_runs` and `knowledge_items`) caused SQLAlchemy to fail with "Could not determine join condition between parent/child tables."

**Root Cause:** When a table has two columns referencing the same parent table, SQLAlchemy can't infer which FK is which without explicit `foreign_keys=` parameter on the relationship.

**Solution:** Added explicit `foreign_keys="[Model.column]"` to all ambiguous relationships. For example:
```python
runs = relationship("AgentRun", back_populates="agent", foreign_keys="AgentRun.agent_id")
runs = relationship("AgentRun", back_populates="workflow", foreign_keys="AgentRun.workflow_id")
```

**Prevention:** Always specify `foreign_keys=` when a table has multiple FK relationships to the same model. Use the string form `[Model.column]` to avoid circular import issues.

---

### 3. Dashboard API Path Mismatch
**Problem:** Frontend dashboard called `/api/articles` but backend served `/api/v1/articles`. All data failed silently because the frontend received 404s.

**Root Cause:** Phase 6-A established the `/api/v1/` prefix, but the dashboard was written before this convention was set and never updated.

**Solution:** Updated all 5 endpoint paths in `page.tsx` to use `/api/v1/*` prefix.

**Prevention:** Document the API path convention in the development guide. Use a single constant for the API base path in the frontend client.

---

### 4. Missing CORS Configuration
**Problem:** Browser blocked cross-origin requests from `localhost:3000` (frontend) to `localhost:8000` (backend). No data reached the UI.

**Root Cause:** FastAPI app didn't include CORSMiddleware. The backend and frontend run on different ports in development, requiring CORS.

**Solution:** Added `CORSMiddleware` in `main.py` using `NEXT_PUBLIC_API_URL` env var with sensible default.

**Prevention:** Include CORS middleware by default in the FastAPI app factory. Add it during Phase 1 infrastructure setup, not Phase 6.

---

### 5. Backend Response Envelope Not Unwrapped on Frontend
**Problem:** Dashboard assigned full `{ success, data, error }` envelope to React state instead of extracting the `data` array. Tables rendered with envelope object instead of entity data.

**Root Cause:** Backend wraps every response in `APIResponse[T]`, but the frontend didn't have a helper to extract the data field.

**Solution:** Created `unwrap<T>()` helper in `lib/api.ts` that checks for the envelope structure and extracts `data`. Falls back to treating raw value as array if already unwrapped.

**Prevention:** Document the envelope pattern in AI_AGENT_CONTEXT.md. Create the unwrap helper during Phase 6-A when the envelope is introduced, not after.

---

### 6. TypeScript Build Failure from Interface Intersection Syntax
**Problem:** `tsc --noEmit` failed with `interface {} & Record<string, unknown>` syntax error. TypeScript doesn't support intersection with empty interface.

**Root Cause:** Used `interface Foo extends Record<string, unknown> & {}` pattern which is invalid TypeScript.

**Solution:** Converted all entity types from `interface` + intersection to `type` aliases with `& Record<string, unknown>`.

**Prevention:** Use `type` aliases (not `interface`) when you need intersection types with `Record<string, unknown>`. Run `npm run type-check` frequently during frontend development.

---

### 7. DataTable Generic Type Error
**Problem:** `DataTable` component referenced an undeclared generic `T` in its props type, causing TypeScript compilation failure.

**Root Cause:** Component definition used `T[]` in generic parameter but never declared `T` in the generic clause.

**Solution:** Simplified to `unknown[]` since the component doesn't actually need typed data — it works with any record shape via `renderCell` callback.

**Prevention:** Keep component generics minimal. If a generic isn't used in the implementation, don't declare it.

---

### 8. Badge Variant Type Cast Complexity
**Problem:** Badge component had overly complex union type assertions for variant colors, making the code hard to read and maintain.

**Root Cause:** Tried to be too precise with TypeScript discriminated unions when a simple `Record<string, string>` mapping was sufficient.

**Solution:** Simplified to `Record<string, string>` variant map with default fallback. Removed redundant union assertions.

**Prevention:** Prefer simple type mappings over complex discriminated unions for CSS class variants. Use `as const` assertions where appropriate.

---

## Architecture Decisions & Lessons

### 1. Layered Architecture (Router → Service → Repository)
**Decision:** Introduced in Phase 6-A after initial direct router-to-database access.
**Lesson:** The layered approach added ~200 lines of boilerplate but made testing trivial (mock repositories instead of databases). Worth the upfront cost.
**Recommendation:** Apply layered architecture from Phase 1, not retroactively.

### 2. MCP Server Stub Pattern
**Decision:** MCP tools return structured stub data when no token is configured, rather than raising errors.
**Lesson:** This allowed the entire autonomous pipeline to work end-to-end without real API credentials. Tests pass green without external dependencies.
**Recommendation:** Keep this pattern for all external integrations.

### 3. Prompt Templates as Markdown Files
**Decision:** All LLM prompts stored as `.md` files in `backend/prompts/`, loaded via template rendering.
**Lesson:** Prompts are now version-controlled and editable without redeployment. However, the template format uses Python `.format()` which doesn't support f-string features like `{variable!r}`.
**Recommendation:** Consider switching to Jinja2 or f-string templates for more flexible formatting.

### 4. Alembic Autogenerate from Models
**Decision:** Generated initial migration from SQLAlchemy models using `--autogenerate`.
**Lesson:** Worked well for the initial schema but subsequent manual changes to models require careful review of generated migrations. The autogenerate missed some index definitions.
**Recommendation:** Always review autogenerated migrations carefully. Add indexes manually in migration scripts rather than relying on autogenerate for index changes.

### 5. LangGraph State Over Shared Context Variables
**Decision:** Moved from `WorkflowBase` (shared dict) to LangGraph `StateGraph` (Pydantic models).
**Lesson:** State schemas provide better type safety and documentation. Each node reads/writes specific fields. Error isolation works well — one failing node doesn't crash the pipeline.
**Recommendation:** Use LangGraph StateGraph for all multi-agent workflows. Avoid the old WorkflowBase pattern for new code.

### 6. Async First Throughout
**Decision:** All layers are async — FastAPI routes, SQLAlchemy sessions, HTTP clients, agent execution.
**Lesson:** Consistent async design means no blocking calls anywhere. However, it requires careful attention to `await` throughout the call chain. Missing an `await` causes silent coroutine objects instead of results.
**Recommendation:** Run mypy strict mode to catch missing awaits. Use `async def` consistently — never mix sync and async in the same call chain.

## Future Prevention Checklist

- [ ] Add linting/pre-commit hooks (ruff, mypy, tsc)
- [ ] Add CI pipeline to catch integration issues early
- [ ] Document API conventions (envelope, pagination, paths) in README
- [ ] Create project scaffold script to enforce structure
- [ ] Add integration tests that verify frontend-backend path compatibility
- [ ] Document environment variable requirements per service
- [ ] Add health check endpoints for all infrastructure services
- [ ] Create runbook for common deployment scenarios
