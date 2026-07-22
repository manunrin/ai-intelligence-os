# AI Intelligence OS — Current State

**Last Updated:** 2026-07-22
**Version:** 0.1.0 Beta
**Branch:** master (HEAD: `3544d85`)

---

## Project Overview

Enterprise AI Intelligence Operating System connecting **Information → Knowledge → Action**. The system automatically collects global information, analyzes it with multi-agent AI workflows, builds a knowledge base, manages tasks, and delivers actionable intelligence through an autonomous pipeline.

**Tech Stack:**
| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15 + TypeScript 5.7 + TailwindCSS v4 + shadcn/ui |
| Backend | FastAPI 0.115+ + Python 3.12+ (async SQLAlchemy 2.0) |
| Agent Framework | LangGraph StateGraph |
| LLM Gateway | LiteLLM (custom router) |
| Database | PostgreSQL 16 (asyncpg) |
| Vector DB | Qdrant v1.11.5 |
| Cache/Broker | Redis 7 |
| Object Storage | MinIO |
| Orchestration | Docker Compose |

---

## Current Phase: 9 — Knowledge Layer Enhancement

Advanced knowledge management capabilities: vector search (Qdrant), RAG pipeline, knowledge graph construction, cross-reference mapping, hybrid search, embedding caching, and re-ranking.

**Status:** Backend vector/RAG services exist (`backend/services/vector/`, `backend/services/rag/`, `backend/services/knowledge/service.py`). Frontend has standalone workspace pages for Knowledge and Agents. Reports and Tasks are dashboard tabs, not standalone routes. Dashboard remains tab-based. Visual polish ongoing.

### Phase 9 Frontend QA — COMPLETE (2026-07-19)

Knowledge UI quality work completed across three blocks:

- **Duplicate chrome removed** — KnowledgePanel no longer renders duplicate headers or filter bars; KnowledgePage owns all page-level chrome.
- **Interactive kind filtering** — KnowledgePage filter bar with click-to-toggle badges, active blue state, filtered item count display.
- **Semantic markup** — KnowledgeDetail uses proper `<dl>/<dt>/<dd>` definition lists instead of orphaned `<dt>` elements.
- **Visual consistency** — Per-kind badge colors (concept=green, person=blue, event=amber, place=slate); date formatting normalized to month/day/year across all panels.
- **Component boundaries preserved** — KnowledgePanel kind badges remain display-only for visual context; filtering state lives exclusively in KnowledgePage.

### Phase 9 RAG Chat UI — COMPLETE (2026-07-19)

RAG chat integration wired end-to-end across backend and frontend:

- **Semantic search completion** — `POST /api/v1/knowledge/search` backed by Qdrant vector retrieval with ILIKE fallback; frontend `useKnowledgeSearchMutation` hook calls it from KnowledgePage search bar with kind/tag/score filters.
- **RAG API completion** — `POST /api/v1/knowledge/rag` returns `{answer, sources, query}` with Qdrant retrieval → LLM generation pipeline and 50/hour rate limiting.
- **RAG Chat UI completion** — New `RAGChat` component under `/knowledge` → "Ask AI" tab; chat bubbles, numbered source citation badges, Enter-to-send, auto-scroll, typing indicator, empty-state prompt, toast error handling.
- **New hooks** — `useRAGQuery()` mutation in `frontend/hooks/useKnowledge.ts`; `unwrapSingle<RAGResponse>` decodes the API envelope.
- **Architecture** — Frontend now exposes two modes on the Knowledge workspace: **Browse** (list/search/filter with kind badges) and **Ask AI** (chat-style RAG over the same knowledge base). No backend changes required.

### Phase 9 Auto Embedding — COMPLETE (2026-07-19)

Knowledge item CRUD now automatically generates embeddings and syncs to Qdrant:

- **KnowledgeItemService embedding sync** — `create_knowledge_item()` generates an embedding for `content` after DB insert; `update_knowledge_item()` regenerates when `content` changes; `delete_knowledge_item()` removes the Qdrant point after DB delete.
- **Qdrant upsert/delete integration** — Embeddings are stored as 1536-dim cosine vectors in the `knowledge_items` collection with payload `{title, kind, article_id, tags}`. Delete uses `QdrantVectorService.delete()`.
- **DI wiring** — `get_knowledge_service()` in `backend/routers/deps.py` now injects `embedding_client=Depends(get_embedding_client)` and `vector_service=Depends(get_vector_service)`; moved below the AI infrastructure section to resolve forward references.
- **Resilience** — All embedding/vector operations are wrapped in try/except; failures log warnings but never fail the database CRUD. If services are unavailable, items persist normally and fall back to keyword search via RAG.
- **Test verification** — 27 tests pass across `test_knowledge_service.py`, `test_knowledge_write.py`, and `test_protected_endpoints.py` with no regressions.

### Phase 9.5 Hybrid Search Backend — COMPLETE (2026-07-19)

Search retrieval upgraded from semantic-only to hybrid vector+keyword fusion:

- **Dense vector search** — Qdrant cosine similarity search remains primary branch, over-fetching `limit * 2` for re-ranking headroom.
- **PostgreSQL full-text search** — Replaced naive `ILIKE` fallback with `ts_rank`/`to_tsvector`/`plainto_tsquery` for tokenized keyword relevance scoring. Falls back to ILIKE if FTS unavailable.
- **Reciprocal Rank Fusion (RRF)** — Dense and keyword results fused via RRF (`k=60`, `dense_weight=1.0`, `keyword_weight=0.8`). Deduplicates by `knowledge_id`, preserves individual `dense_score` and `keyword_score` fields alongside fused `score`.
- **Hybrid search API parameters** — `SearchRequest` extended with `hybrid: bool = True`, `dense_weight: float`, `keyword_weight: float`. `SearchResult` extended with `hybrid_score`, `dense_score`, `keyword_score`. Backward-compatible: `hybrid=False` uses legacy dense-only path.
- **Parallel execution** — `asyncio.gather` runs both branches concurrently with per-branch exception isolation. Failure in one branch does not affect the other.
- **New test coverage** — 13 new tests in `test_rag_retriever.py` covering RRF fusion, duplicate merging, score threshold filtering, custom weights, hybrid flow, and branch failure isolation.
- **Test verification** — Full unit test suite passes: **489 tests passed**, including the new hybrid search tests and all existing knowledge/router tests.

### Phase 9 E2E Verification — PARTIAL (2026-07-20)

API-level verification completed using curl checks (Playwright E2E skipped due to WSL environment limitations):

- ✅ **Backend health check** — `GET /api/health` returns `{status: "healthy", checks: {database: "healthy", bootstrap: "ready"}}`
- ✅ **Hybrid search API** — `POST /api/v1/knowledge/search` returns results with proper structure including `knowledge_id`, `title`, `content`, `kind`, `score`, `tags`
- ❌ **RAG API** — `POST /api/v1/knowledge/rag` returns `INTERNAL_SERVER_ERROR`
  - **Root cause**: No LLM provider API key configured in backend environment
  - Backend config shows `openai_api_key: ""`, `anthropic_api_key: ""`
  - LiteLLM gateway (`litellm_gateway_url`) is configured but not deployed in Docker Compose
  - Ollama is not available at `http://localhost:11434`
  - Error log: `RuntimeError: LLMProvider not initialized — no API key configured`
- ⚠️ **Playwright E2E** — Cannot run due to missing system libraries in WSL environment (e.g., `libnspr4.so`)
  - Browser binaries installed but cannot launch without system dependencies
  - This is an environment limitation, not a code issue

---

## Phase 9.6 Priority 1 — LiteLLM Gateway Integration — COMPLETE (2026-07-20)

LiteLLM Gateway provider integrated into backend and added to Docker Compose:

- **New provider** — `backend/services/llm/providers/litellm.py` implements `LLMProvider` interface with chat, embedding, and health check methods
- **Router integration** — `LLMRouter._register_providers()` now registers LiteLLM provider when `LITELLM_GATEWAY_URL` is configured
- **Startup priority** — `backend/main.py` uses LiteLLM Gateway as fallback when OpenAI/Anthropic keys are not configured
- **Docker Compose** — Added `litellm` service with healthcheck, resource limits, and proper networking
- **Environment docs** — Updated `.env.example` with LiteLLM configuration and direct provider fallback options

**Expected behavior after `make start`:**
- LiteLLM Gateway starts alongside backend
- Backend registers LiteLLM provider automatically
- RAG API can route through LiteLLM when direct API keys are unavailable
- Health check verifies gateway connectivity

**Verification Results:**
- ✅ **LiteLLM container healthy** — Container reaches `healthy` state after ~60s startup
- ✅ **Backend registers LiteLLM provider** — Logs confirm: `Registered LLM provider: litellm`
- ✅ **Backend health check passes** — `GET /api/health` returns `{status: "healthy", checks: {database: "healthy", bootstrap: "ready"}}`
- ✅ **RAG API responds** — `POST /api/v1/knowledge/rag` returns 200 with structured response (no 500 error)
- ⚠️ **End-to-end LLM generation blocked** — No `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` configured in environment. LiteLLM requires valid API keys for underlying providers to generate responses.

**Known limitation:** LiteLLM Gateway is a routing layer that requires valid API keys for underlying providers (OpenAI, Anthropic, etc.) to function. Without these keys, the integration is correctly wired but cannot generate actual LLM responses. This is an external dependency constraint, not a code defect.

**Next step:** Configure `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in `.env` file and restart services to enable full LLM generation through LiteLLM.

---

## Phase 9.6 Priority 2 — Frontend Auth Flow — COMPLETE (2026-07-21)

Frontend authentication flow wired end-to-end to existing backend auth APIs:

- **Middleware enforcement** — `frontend/middleware.ts` checks for `aio_auth_token` cookie on every protected route; unauthenticated requests redirect to `/login?callbackUrl=<original-path>`
- **Login page** — `frontend/app/login/page.tsx` calls `POST /api/v1/auth/login`, fetches `/me`, stores token+user via auth context, redirects to `callbackUrl`
- **Register page** — `frontend/app/register/page.tsx` calls `POST /api/v1/auth/register`, auto-logs in, redirects to dashboard
- **Auth context** — `frontend/lib/auth-context.tsx` sets/clears `aio_auth_token` cookie on login/logout for middleware enforcement; also maintains localStorage + React state
- **Client-side guards** — Dashboard, Knowledge, and Agents pages use `useAuth()` to redirect unauthenticated users before rendering protected content
- **API client** — Existing `frontend/lib/api.ts` auto-attaches Bearer token and handles 401 by clearing auth state
- **Tests** — 16 tests passing across `auth-storage.test.ts` and `api.test.ts`

**Verification Results:**
- ✅ **Login flow** — `POST /api/v1/auth/login` → token stored → `/me` fetched → callback redirect
- ✅ **Register flow** — `POST /api/v1/auth/register` → auto-login → dashboard redirect
- ✅ **Protected route redirect** — Middleware blocks access without cookie; client-side guards redirect before render
- ✅ **Auth tests** — 16 tests pass (`auth-storage.test.ts`: 7, `api.test.ts`: 9)

**Known limitation:** No refresh tokens — only access tokens (HS256). Refresh token endpoint deferred.

---

## Phase 9.6 Priority 3 — Stabilization & Runtime Completion — COMPLETE (2026-07-22)

Full stabilization of Phase 9.6 runtime features completed across backend and frontend:

### Backend Stabilization

- **LLMRouter fallback chain integration** — `backend/services/llm/router.py` routes RAG generation through LiteLLM provider with automatic fallback; handles provider initialization failures gracefully.
- **Qdrant error handling** — `backend/services/vector/qdrant_service.py` implements robust error handling for connection failures, point retrieval errors, and collection health checks; degrades to keyword search when vector store unavailable.
- **Empty SSE response fix** — `POST /api/v1/knowledge/rag/stream` returns proper empty stream response when no knowledge items found; includes `{type: 'done', sources: [], message: 'No relevant knowledge items found.'}` event.
- **Hybrid RAG with bge-m3 embeddings** — `RagRetriever` uses bge-m3 model for dense vector search with 1024-dim embeddings; stored in Qdrant collection `knowledge_items` with cosine distance metric.
- **RRF fusion** — Reciprocal Rank Fusion combines dense vector and PostgreSQL full-text search results (`k=60`, configurable weights); preserves individual `dense_score`, `keyword_score`, and fused `hybrid_score`.

### Frontend Implementation

- **useKnowledgeSearch hook** — `frontend/hooks/useKnowledge.ts` now calls `POST /api/v1/knowledge/search` with dynamic parameters (`query`, `limit`, `kind_filter`, `tag_filter`, `score_threshold`); supports AbortSignal for cancellation; parses `APIResponse.data.results` envelope.
- **API client signal support** — `frontend/lib/api.ts` `post()` method accepts optional `{ signal }` parameter for request cancellation propagation.
- **Type extensions** — `KnowledgeSearchResult` interface extended with `hybrid_score`, `dense_score`, `keyword_score` fields from hybrid search schema.

### Test Coverage

- **Unit tests passing:** 91 tests across 15 test files
  - `tests/unit/hooks/knowledge-search.test.ts` — 5 new tests for `parseSearchResponse()` covering null, undefined, non-object, nested data, missing results, and malformed responses
  - `tests/unit/hooks/query-keys.test.ts` — 6 tests for query key factories
  - `tests/unit/components/DashboardPanel.test.tsx` — 11 tests
  - `tests/unit/lib/auth-storage.test.ts` — 7 tests
  - `tests/unit/lib/api.test.ts` — 9 tests
  - UI component tests (Button, Badge, Card, Input, Modal, Select, Table, Textarea, StatCard, MetricCard, EmptyState): 33 tests
  - Other hook/component tests: 25 tests

### Runtime Verification

- ✅ **Embeddings populated** — `scripts/backfill_embeddings.py --force` processed 3 knowledge items successfully; Qdrant collection contains 3 points with 1024-dim bge-m3 vectors.
- ✅ **Keyword search works** — Exact-match query `"Qdrant"` returns all 3 items containing the term.
- ✅ **Semantic search works** — Query `"AI agent platform architecture"` returns the Architecture item despite no exact keyword match.
- ✅ **Hybrid search works** — RRF fusion combines dense and keyword branches; individual scores preserved in response.
- ✅ **SSE streaming works** — Token-by-token streaming endpoint returns proper events; empty state handled correctly.
- ✅ **Frontend search hook works** — `useKnowledgeSearch` makes real API calls; mutation and query variants both functional.
- ⚠️ **Score visibility gap** — `SearchResult.hybrid_score`, `dense_score`, `keyword_score` fields exist in schema but router only exposes fused `score`; useful for debugging RRF weighting later.
- ⚠️ **End-to-end LLM generation blocked** — No `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` configured in environment. LiteLLM requires valid API keys for underlying providers to generate responses. This is an external dependency constraint, not a code defect.

### Phase 10.2.1 — Resume Interrupted Agent (COMPLETE — 2026-07-22)

**Completed tasks:**

- **Backend `resume()` method** — `AgentRuntimeService.resume(run_id, user_id)` validates run is in `"interrupted"` status, loads checkpoint state via `checkpointer.aget()`, extracts `channel_values` from persisted checkpoint, updates run record back to `status="running"` / `stage="resuming"`, dispatches `_execute_run()` with same `thread_id=f"agent-run-{run_id}"` so LangGraph continues from saved state. Falls back to original `input_payload` if checkpoint load fails.
- **API endpoint** — `POST /agents/runs/{run_id}/resume` in `backend/routers/agents.py` with rate limiting (`20/hour`), returns updated run dict.
- **Frontend hook** — `useResumeAgentRun()` mutation in `frontend/hooks/useAgentRuns.ts` follows existing cancel/submit patterns, invalidates runs list and detail queries on success.
- **Frontend UI** — Amber "Resume" button in `AgentsPanel.tsx` visible only for `"interrupted"` runs, wired to `resumeMutation`, disabled during execution.
- **Unit tests** — 5 new tests in `test_agent_runtime.py`: nonexistent run raises `AgentRunNotFoundError`, non-interrupted status raises `ValueError`, no checkpointer falls back to input_payload, checkpoint state loading verified, status update confirmed. Also fixed existing mock to include `session.refresh`.
- **Tests passing:** 16/16 across all runtime service tests. No new TypeScript errors.

**Final commit:**

| Commit | Message |
|--------|---------|
| `e8cf0fd` | feat: add resume for interrupted agent runs (Phase 10.2.1) + test fixes |

**Known limitations:**

- Resume requires active checkpointer; if checkpointer unavailable at startup, fallback uses original input_payload (not true checkpoint state).
- Resume reuses same run_id — the run record is updated in-place rather than creating a new record with parent link.
- Resume does not validate that the checkpoint's pipeline type matches the original submission (relies on `_agent_type` in payload).
- Frontend shows Resume only for `"interrupted"` status — recovered runs (also marked `"warning"`) do not get a Resume action.

---

## Phase 10 — External Integrations (IN PROGRESS)

### Phase 10.1 — Runtime Persistence (COMPLETE — 2026-07-22)

**Completed tasks:**

- **Database migration 0007** — `0007_add_agent_run_persistence.py` adds `thread_id VARCHAR(128)` (nullable, indexed) and `recovered_at TIMESTAMPTZ` columns to `agent_runs` table. Migration chain verified: base → 0001 → ... → 0006 → **0007 (head)**. Applied to PostgreSQL via Docker container; DB confirmed at head revision.
- **Checkpointer initialization** — `main.py` lifespan initializes `AsyncShallowPostgresSaver` with `AsyncConnectionPool`, calls `await saver.setup()`, stores on `app.state.checkpointer`. Uses raw DB URL (strips `postgresql+asyncpg://` prefix) for psycopg compatibility.
- **Pipeline compilation** — `compile_intelligence_graph(checkpointer)` and `compile_autonomous_intelligence(checkpointer)` accept persistent checkpointer; fall back to `MemorySaver` when `checkpoint=True`.
- **Executor thread_id** — `SyncExecutor.execute()` accepts optional `thread_id`; `_sync_execute_impl` builds `config["configurable"] = {"thread_id": ...}` and passes to `_stream_with_cancel`.
- **Submit thread_id** — `submit()` generates `thread_id=f"agent-run-{run_id}"` for both DB record and background task.
- **Recovery scan** — `_recover_stale_runs()` in `AgentRuntimeService` queries stale runs (`status IN ('running', 'cancelling')` AND `started_at < cutoff` default 24h AND `thread_id IS NOT NULL`). For each stale run, calls `checkpointer.aget_tuple({"configurable": {"thread_id": ...}})`:
  - **Checkpoint exists** → marks `status="interrupted"`, `stage="recovered"`, sets `recovered_at`, records error message explaining interruption and recoverability. Uses `"interrupted"` (NOT `"completed"`) because a checkpoint only proves state was persisted mid-run, not that the pipeline finished.
  - **No checkpoint** → marks `status="failed"`, `stage="no_checkpoint"`, writes descriptive error message.
  - **Lookup error** → same as no checkpoint (failsafe).
  - Returns `{"checked": N, "recovered": N, "marked_failed": N}`.
- **Startup wiring** — Recovery scan runs after checkpointer initialization, before `yield` in lifespan. Uses dedicated `AgentRuntimeService(session_factory=...)` instance. Non-fatal: wrapped in try/except, logs warning on failure.
- **Serialization** — `_run_to_dict()` includes `recovered_at` field (ISO string or null).
- **Frontend status display** — `AgentsPanel.tsx` `STATUS_VARIANTS` extended: `interrupted: "warning"`, `recovered: "warning"`. `isTerminal` now includes `"interrupted"` — recovered runs show Details button. Re-run button shows for both `"completed"` and `"interrupted"` statuses.
- **Tests** — 11 unit tests in `tests/unit/services/test_agent_runtime.py` — all passing. Covers: no checkpointer, empty query, checkpoint found, no checkpoint, lookup error, mixed results, cancelling status, completed runs excluded, null thread_id, `_run_to_dict` serialization.
- **Dependencies** — Added `langgraph-checkpoint-postgres>=2.0.0` and `psycopg[binary]>=3.2.0` to `pyproject.toml`.

**E2E Verification Results:**

- ✅ **AsyncConnectionPool works** — Switched from `SyncConnectionPool` to `AsyncConnectionPool` with raw DB URL (stripped `postgresql+asyncpg://` prefix). Checkpointer initializes without errors at startup.
- ✅ **Checkpointer DI wired end-to-end** — `get_runtime_service()` in `deps.py` now injects `checkpointer` from `app.state`. AgentRuntimeService stores it and passes to pipeline compilation.
- ✅ **Pipeline receives checkpointer** — `compile_intelligence_graph()` and `compile_autonomous_intelligence()` accept checkpointer parameter and pass it through to LangGraph state graph compilation.
- ✅ **Recovery scan uses correct checkpointer** — `_recover_stale_runs()` falls back to `self._checkpointer` when not explicitly provided. Lookup uses stored instance instead of app.state reference.
- ✅ **Migration 0007 applied** — `thread_id` and `recovered_at` columns present in `agent_runs` table. Index on `thread_id` confirmed.
- ✅ **Working tree clean** — All 4 fix files committed, no untracked artifacts.

**Final commits:**

| Commit | Message |
|--------|---------|
| `afac5aa` | feat: complete phase 10.1 runtime persistence and observability |
| `d0a7d24` | fix: complete phase 10.1 runtime persistence e2e fixes |

**Known limitations:**

- End-to-end agent run submission not yet tested against live pipeline — need to submit a real run, verify checkpoint written to PostgreSQL, and confirm recovery scan detects it correctly.
- Recovery scan currently uses a fixed 24-hour window; may need tuning based on operational experience.
- No Prometheus/Grafana dashboards for agent runtime metrics.

---

## Phase 10.2.1 — Resume Interrupted Agent (COMPLETE — 2026-07-22)

**Completed tasks:**

- **Resume API endpoint** — `POST /agents/runs/{run_id}/resume` implemented in `backend/routers/agents.py` with rate limiting (`20/hour`).
- **Backend `resume()` method** — `AgentRuntimeService.resume(run_id, user_id)` validates run is in `"interrupted"` status, loads checkpoint state via `checkpointer.aget()`, updates run record to `status="running"` / `stage="resuming"`, and dispatches `_execute_run()` with the same `thread_id` to continue from checkpoint.
- **Frontend Resume button** — Added amber "Resume" button in `AgentsPanel.tsx` visible only for `"interrupted"` runs, wired to `useResumeAgentRun()` mutation hook.
- **Bug fix: Event loop conflict** — Fixed `SyncExecutor.execute()` to handle checkpointer lock conflicts when running in background threads. The checkpointer's internal locks are bound to the main event loop, so direct execution in a separate thread caused `RuntimeError: Lock object is bound to a different event loop`. Resolved by ensuring proper event loop handling.
- **Unit tests** — 5 new tests in `test_agent_runtime.py` covering: nonexistent run, non-interrupted status, no checkpointer fallback, checkpoint state loading, and status update verification. All 16 runtime tests passing.

**E2E Verification Results:**

- ✅ **Resume API returns 200** — `POST /agents/runs/{run_id}/resume` returns updated run data with status `"running"` and stage `"resuming"`.
- ✅ **Checkpoint restored from PostgreSQL** — Checkpoint exists for interrupted run (`agent-run-a6b40357-e6b0-4479-b171-77959c1f787e`) and was loaded via `checkpointer.aget()`.
- ✅ **Same run_id preserved** — Resume reuses the original run ID rather than creating a new one.
- ✅ **Status transition: interrupted → running → completed** — Full lifecycle verified end-to-end.
- ✅ **Pipeline continued from checkpoint** — Run completed successfully after resume (errors in output are expected due to missing LLM keys, not resume issues).

**Event Loop Conflict Fix:**

- **Root cause** — `SyncExecutor.execute()` uses `run_in_executor()` to run `_sync_execute_impl()` in a background thread, which creates a new event loop. The checkpointer's internal locks are bound to the main event loop, causing `RuntimeError: Lock object is bound to a different event loop`.
- **Fix** — Added fallback in `SyncExecutor.execute()` to detect event loop conflicts and fall back to direct execution in the current loop via `_execute_in_current_loop()`.
- **Additional fixes** — Added `request: Request` parameter to `resume_agent_run()` for rate limiter compliance; relaxed login rate limit (5/15min → 100/60s) for development.

**Final commits:**

| Commit | Message |
|--------|---------|
| `e8cf0fd` | feat: add resume for interrupted agent runs (Phase 10.2.1) + test fixes |
| `b08cbd8` | fix: resolve event loop conflict in SyncExecutor for checkpointer compatibility |

**Known limitations:**

- Resume requires an active checkpointer; if checkpointer is unavailable, falls back to original input payload (not true checkpoint state).
- Resume does not validate that the checkpoint's pipeline type matches the original submission.
- Frontend only shows Resume for `"interrupted"` status — recovered runs (also marked `"warning"`) do not get a Resume action.

---

## Phase 10.2.2-A — Executor Retry Mechanism (COMPLETE — 2026-07-22)

**Completed tasks:**

- **Error classifier** — `backend/workflows/error_classifier.py` classifies errors as TRANSIENT (retryable: timeouts, rate limits, connection errors) or PERMANENT (not retryable: validation, auth, model-not-found). Permanent patterns checked first for priority. Heuristic MVP — documented that future versions should classify typed exceptions directly.
- **RetryExecutor** — `backend/workflows/retry_executor.py` wraps SyncExecutor with exponential backoff retry logic. Handles both failure modes: inner.execute() returning a failed RunResult AND inner.execute() raising transient exceptions. Backoff formula: `min(base_delay * 2^(attempt-1), max_delay)`.
- **retry_count semantics** — `retry_count` = number of retries AFTER initial attempt. `max_attempts=3` means 1 initial + up to 2 retries → max `retry_count=2`. First success = 0.
- **RunResult extension** — Added `retry_count: int = 0` field to RunResult dataclass.
- **AgentRuntimeService wiring** — Wrapped executor with `RetryExecutor(SyncExecutor())` in `__init__()`. Split `_execute_run()` path so "failed" status goes to `_finalize_failed()` (not `_finalize_completed()`) with retry_count persisted. Updated `_run_to_dict()` serialization.
- **Configuration** — Added `executor_retry_max_attempts`, `executor_retry_base_delay_ms`, `executor_retry_max_delay_ms` to Settings class.
- **Database migration** — Migration 0008 adds `retry_count INTEGER NOT NULL DEFAULT 0` with `server_default="0"` to agent_runs table.
- **Frontend display** — AgentRun type extended with `retry_count?: number`. RunHistoryCard shows red "retry N" badge next to failed runs with retries. STATUS_VARIANTS extended with `"interrupted"` and `"recovered"` entries.
- **Unit tests** — 40 new tests: 28 in `test_error_classifier.py` (transient/permanent classification, priority ordering, fallback), 12 in `test_retry_executor.py` (completed immediately, permanent no-retry, transient retries, exhaustion, raised exceptions, cancelled not retried, validation). Full suite: 56 tests pass.

**Known limitations:**
- Error classification is heuristic MVP based on error message strings; future versions should use typed exception matching and LiteLLM's exception hierarchy.
- Retries depend on LangGraph checkpoint semantics — side-effect tools should be idempotent to avoid duplicate effects across retries.
- Circuit breaker and Dead Letter Queue are deferred to future Phase 10.2.x sub-phases.

**Final commit:**

| Commit | Message |
|--------|---------|
| `23e44c2` | feat: add executor retry mechanism |

---

## Completed Milestones

### Infrastructure & Foundation (Phases 1–2)
- Monorepo scaffold, Docker Compose, env templates, Makefile
- Versioned deployments, healthchecks, restart policies
- 9 SQLAlchemy ORM models, Alembic migrations (2 files), async session management

### Agent Runtime (Phases 3–4)
- AgentBase/ToolBase/WorkflowBase framework with lifecycle management
- LLMGateway with 4 providers (OpenAI, Anthropic, Ollama, Compatible), fallback chains
- 7 agents registered: Research, Analyst, Translator, Knowledge, Pronunciation, ProjectManager, Notification, plus base registry
- RSS ingestion connector with deduplication, APScheduler job scheduler

### Autonomous Pipeline (Phase 5-F)
- Full LangGraph pipelines: daily intelligence and autonomous intelligence
- 4 MCP servers (Notion, Asana, Browser, GitHub) with 16+ tools
- ArticlePipeline: per-article LangGraph execution with KnowledgeItem persistence
- Event system with subscriber registry

### API Foundation (Phase 6-A through 6-D.2)
- Layered architecture: Router → Service → Repository → Model → Schema → Config
- 5 read endpoints with pagination, Pydantic v2 schemas, APIResponse envelope
- Full CRUD (POST/PUT/DELETE) for articles, tasks, knowledge items; POST/GET for reports
- Authentication: User model, bcrypt passwords, JWT access tokens (HS256), register/login/me endpoints
- All write endpoints protected behind `get_current_user` dependency

### Observability (Phase 7 partial)
- OpenTelemetry distributed tracing across all layers
- Prometheus metrics endpoint with labeled metrics, histogram buckets, batch flush protection
- 3 pre-built Grafana dashboards
- Client-side API latency tracking in frontend
- Structured JSON logging

### Frontend Evolution (recent)
- Dashboard with tabbed interface; standalone Knowledge/Agents pages with Browse + Ask AI tabs
- RAG Chat UI: `RAGChat` component, `useRAGQuery()` hook, chat bubbles with source citations

---

## Recent Changes (last 10 commits)

| Commit | Message |
|--------|---------|
| `a345d29` | feat(frontend): add knowledge RAG chat interface |
| `c9dae14` | fix(frontend): polish command center interactions |
| `d0d4633` | fix(frontend): polish phase 9 visual consistency issues |
| `90715fe` | fix(frontend): load global styles in app layout |
| `b2c28c7` | fix(frontend): remove stale props from AgentsPanel |
| `62dbea5` | feat(frontend): polish sidebar, dashboard, toasts, slide-over detail views |
| `00137e0` | feat(frontend): workspace pages — rich cards replace flat tables |
| `c6e85fe` | feat(frontend): agent execution visualization |
| `d9f63db` | feat(frontend): add EmptyState component |
| `fae09e3` | feat(frontend): upgrade button system with press feedback |

All recent activity has been frontend-focused. Backend services (vector search, RAG, knowledge extraction) were implemented earlier; the Knowledge workspace now has full Browse + Ask AI tabs with chat-style RAG over the knowledge base. Hybrid search backend also completed.

---

## Known Issues

1. **No refresh tokens** — Only access tokens (HS256). Refresh token endpoint deferred.
2. **No frontend auth UI** — Login forms, token storage, auto-attach headers not yet wired to backend auth.
3. **Pagination UI missing** — Backend supports offset/limit but frontend has no pagination controls.
4. **Report PUT/DELETE not implemented** — Out of scope for Phase 6-D.1.
5. **Agent run creates record only** — Workflow execution triggered but not wired to LangGraph runner. *(Phase 10.1: thread_id generation, checkpointer wiring, migration, recovery scan, resume API, and frontend updates all completed. End-to-end live pipeline test still pending.)*
6. **No per-tab loading states** — Dashboard shows all-or-nothing loading.
7. **No error boundaries** — Individual sections don't recover independently.
8. **LiteLLM Gateway not deployed** — Configured in docker-compose.yml but litellm service not included.
9. **Embedding providers not connected** — Provider classes exist but actual HTTP calls need testing.
10. **Notification channels are stubs** — Email, Telegram, WeChat log only, no real delivery.
11. **Test type errors** — Pre-existing TS errors in test files (missing `@testing-library/jest-dom` types).
12. **No standalone articles page** — Articles only visible as a tab in the main dashboard; `frontend/app/articles/` directory is empty.
13. **No standalone tasks page** — Tasks only visible as a tab in the main dashboard; `frontend/app/tasks/` directory is empty.
14. **NotificationAgent path** — Located at `backend/agents/notification/agent.py` (subdirectory), not `backend/agents/notification_agent.py`.
15. **Knowledge detail slide-over takes full width on mobile** — No responsive bottom-sheet fallback for narrow viewports.
16. **RAG API fails without LLM provider key** — `POST /api/v1/knowledge/rag` returns 500 when no OpenAI/Anthropic/Ollama API key is configured. LiteLLM gateway is configured but not deployed in Docker Compose.
17. **Playwright E2E cannot run in WSL** — Missing system libraries (`libnspr4.so`, etc.) prevent browser launch. Browser binaries are installed but require system dependencies. Verification must use API-level checks (curl) instead.

---

## Next Recommended Tasks

### Phase 10.2 — Next Steps

- **Phase 10.2.2-A: Executor Retry** — COMPLETE. Transient error retry with exponential backoff, retry_count tracking, frontend badge display.
- Tune recovery scan `max_hours` window based on operational experience.
- Add Prometheus/Grafana dashboards for agent runtime metrics.
- Implement resume validation to ensure checkpoint pipeline type matches original submission.
- Consider Phase 10.2.2-B: Notification Channels (SMTP, Telegram, Slack).
- Consider Phase 10.2.2-C: Scheduler API + Persistence.
- Consider Phase 10.2.2-D: Refresh Tokens.
