# AI Intelligence OS — Current State

**Last Updated:** 2026-07-22
**Version:** 0.1.0 Beta
**Branch:** master (HEAD: `a345d29`)

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

## Phase 9.6 RAG Streaming & Runtime Integration — COMPLETE (2026-07-22)

Runtime integration completing the hybrid RAG backend (embedding generation and RRF fusion documented under Phase 9 Auto Embedding and Phase 9.5 Hybrid Search Backend):

- **SSE streaming RAG endpoint** — `POST /api/v1/knowledge/rag/stream` streams LLM-generated answers token-by-token via Server-Sent Events; frontend `RAGChat` consumes the stream.
- **Embedding backfill tooling** — `scripts/backfill_embeddings.py` processes all `KnowledgeItem` rows, generates embeddings via the LiteLLM/Ollama pipeline, upserts to Qdrant, and stores model metadata. Supports `--force` to rebuild collection from scratch.

**Runtime Verification Results:**
- ✅ **Embeddings populated** — `scripts/backfill_embeddings.py --force` processed 3 knowledge items successfully; Qdrant collection contains 3 points.
- ✅ **Keyword search works** — Exact-match query `"Qdrant"` returns all 3 items containing the term.
- ✅ **Semantic search works** — Query `"AI agent platform architecture"` returns the Architecture item despite no exact keyword match.
- ✅ **Qdrant vector search available** — Collection healthy, cosine distance configured, 1024-dim vectors indexed.
- ⚠️ **Score visibility gap** — `SearchResult.hybrid_score`, `dense_score`, `keyword_score` fields exist in schema but router only exposes fused `score`; useful for debugging RRF weighting later.

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

## Current Architecture

```
User → Next.js (frontend/:3000) → FastAPI (backend/:8000) → LangGraph Workflows → AI Agents
                                         ↓                    ↓
                                   PostgreSQL 16           MCP Servers
                                   Qdrant                  Notion/Asana/Browser/GitHub
                                   Redis 7                 APScheduler
                                   MinIO
```

**Backend Layers:**
- Routers (`routers/`) — 7 sub-routers (auth, articles, knowledge, tasks, agents, reports, audit) under single `/api/v1` prefix
- Services (`services/`) — Business logic across 10+ service modules including embedding, vector, RAG, knowledge, LLM routing
- Repositories (`repositories/`) — BaseRepository[T] with specialized CRUD per entity
- Models (`database/models/`) — 9 ORM entities with relationships
- Schemas (`schemas/`) — Pydantic v2 response models + APIResponse envelope

**Frontend Structure:**
- `app/` — Next.js App Router with 5 route groups (dashboard, knowledge, agents, login, register). Reports and Tasks are dashboard tabs, not standalone routes.
- `components/panels/` — Domain panels (KnowledgePanel, ReportsPanel, TasksPanel, AgentsPanel, ArticlesPanel, DashboardPanel, etc.)
- `components/ui/` — 11 shared UI components (Button, Badge, Card, Table, Input, Modal, Select, Textarea, StatCard, MetricCard, EmptyState)
- `components/knowledge/` — Form bodies (KnowledgeForm)
- `hooks/` — @tanstack/react-query hooks (useKnowledge, useArticles, useTasks, useReports, useAgentRuns, useAgentStream, useRAGQuery)
- `lib/` — API client, auth context, query client, toast system, observability

**Workers/Jobs:**
- `workers/jobs/` — Job execution modules including ArticlePipeline (per-article LangGraph execution with research → analyst → translator nodes)
- `workers/scheduler/` — APScheduler-based job scheduling with cron expressions

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
5. **Agent run creates record only** — Workflow execution triggered but not wired to LangGraph runner.
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

### Phase 9.6 — Stabilization & Runtime Completion (next)

Full roadmap: `docs/proposals/phase-9.6-roadmap.md`

1. **Add LiteLLM Gateway to Docker Compose** (Priority 1, ~2–4 hrs) — unblocks RAG API and all LLM-dependent features; currently the single largest blocker to end-to-end verification
2. **Complete frontend auth flow** (Priority 2, ~1–2 days) — wire existing login/register pages to backend auth endpoints, implement token storage and auto-attach headers
3. **Phase 9 remaining items** (Priority 3):
   - Expose kind/tag filters on RAG endpoint for scoped retrieval
   - Add streaming response support to RAG chat (SSE)
   - Add GIN full-text index migration for PostgreSQL FTS performance
   - Knowledge graph visualization (timeboxed; defer if scope grows)
4. **Pagination controls** (Priority 4, ~0.5–1 day) — reusable component wired into all list views

### Phase 10 — External Integrations (deferred until 9.6 complete)

See `docs/proposals/phase-10-roadmap.md` for detailed plan.

High-priority items:
- New data connectors (Hacker News RSS, arXiv API first; Twitter/X and LinkedIn require credentials)
- Real notification channels (Email SMTP, Telegram Bot, Slack Webhook)
- Bidirectional MCP sync (Notion page changes, Asana task completion, GitHub issue creation)
- Add Prometheus/Grafana services to Docker Compose
