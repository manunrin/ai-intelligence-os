# Phase 9.6 — Stabilization & Runtime Completion

**Created:** 2026-07-20
**Status:** Proposal
**Prerequisite for:** Phase 10 (External Integrations)
**Estimated effort:** 2–4 weeks

---

## Purpose

Phase 9.6 closes the gap between Phase 9's completed backend services and an end-to-end working system. The current codebase has a complete AI/RAG/search stack on paper, but several runtime dependencies are missing and the frontend cannot exercise the backend's protected endpoints. This phase focuses on making the existing system **verifiable and usable** before expanding outward in Phase 10.

The guiding principle: ship what works, document what doesn't. External blockers (missing API keys, unavailable infrastructure) should not prevent milestone completion — they should be recorded as known issues per Agent Execution Rules.

---

## Current State Summary

### What Works Today

| Capability | Status | Evidence |
|------------|--------|----------|
| Hybrid search (vector + FTS with RRF) | Complete | 13 new tests in `test_rag_retriever.py` |
| Auto-embedding on knowledge CRUD | Complete | Qdrant upsert/delete integrated |
| RAG Chat UI (Browse + Ask AI tabs) | Complete | `RAGChat` component, `useRAGQuery()` hook |
| Agent runtime (7 agents, 3 workflows) | Complete | LangGraph StateGraph builders |
| MCP servers (Notion, Asana, Browser, GitHub) | Complete | 16+ tools, registry pattern |
| Auth backend (JWT, bcrypt, protected writes) | Complete | `auth.py` router, `get_current_user` dep |
| Test suite | 489 passing | Unit + integration tests |

### What Blocks End-to-End Functionality

| Blocker | Impact | Root Cause |
|---------|--------|------------|
| LiteLLM Gateway not deployed | RAG API returns 500; all LLM-dependent features non-functional | Service configured in env but absent from `docker-compose.yml` |
| Frontend auth disconnected | Users cannot create/edit articles, tasks, knowledge items, reports from UI | Login/register pages exist but don't call backend auth endpoints |
| No pagination controls | Lists load everything; degrades with data growth | Backend supports offset/limit but frontend has no UI |
| Notification channels are stubs | Pipeline outputs never reach humans | `NotificationAgent` only logs |
| Only one data connector | System ingests only OpenAI Blog | `connectors/rss/` has one file; `connectors/api/` is empty |

---

## Implementation Order

### Priority 1: LiteLLM Gateway — Unblocks Everything

**Complexity:** Low | **Effort:** 2–4 hours

The single most important item. Without an LLM provider, the RAG pipeline, knowledge extraction agents, and "Ask AI" chat are cosmetic. Every AI feature depends on this.

**Tasks:**
1. Add `litellm` service to `docker-compose.yml` using `ghcr.io/litellm/litellm:v1.x.x`
2. Mount or reference `backend/config/models.yaml` for provider routing
3. Add healthcheck (`GET /health/liveness`)
4. Set restart policy and resource limits consistent with other services
5. Verify `POST /api/v1/knowledge/rag` returns a valid answer instead of 500

**Files:** `docker-compose.yml`, possibly `Dockerfile.litellm` or a dedicated config volume mount

**Known issue if blocked:** If LiteLLM image pull fails or provider keys remain unset, document the limitation and continue. The code path is complete; the runtime dependency is the only gap.

---

### Priority 2: Frontend Authentication Flow

**Complexity:** Medium | **Effort:** 1–2 days

Backend already protects all write endpoints with `get_current_user`. Without frontend auth, users cannot exercise any mutation API from the UI.

**Tasks:**
1. Implement JWT token storage strategy (recommend: httpOnly cookie via refresh token endpoint, or localStorage with XSS considerations for v0.1.0)
2. Create `frontend/lib/auth-context.tsx` — React Context provider managing token lifecycle
3. Wire `frontend/lib/api.ts` to auto-attach `Authorization: Bearer <token>` header
4. Connect `frontend/app/login/page.tsx` and `frontend/app/register/page.tsx` to backend auth endpoints
5. Add logout functionality and token expiration handling
6. Gate write operations behind authenticated state (show login prompt when unauthenticated)

**Files:** `frontend/lib/api.ts`, `frontend/lib/auth-context.tsx` (new), `frontend/app/login/page.tsx`, `frontend/app/register/page.tsx`, `frontend/components/layout/Sidebar.tsx`

**Design decision needed:** Refresh token endpoint was deferred in Phase 6-D.2. For v0.1.0, localStorage with manual logout is acceptable. Document the lack of refresh tokens as a known issue.

---

### Priority 3: Remaining Phase 9 Items

**Complexity:** Mixed | **Effort:** 2–4 days total

Four items listed in CURRENT_STATE.md as next recommended tasks. These complete the Phase 9 scope.

#### 3a. Expose Kind/Tag Filters on RAG Endpoint

**Complexity:** Low | **Effort:** 2–3 hours

Extend `RAGRequest` schema with optional `kind_filter` and `tag_filter` parameters. Pass them through to the retriever so "Ask AI" can scope retrieval to specific knowledge kinds (e.g., only concepts, only people).

**Files:** `backend/schemas/knowledge.py`, `backend/services/rag/retriever.py`, `frontend/hooks/useKnowledge.ts`, `frontend/components/panels/RAGChat.tsx`

---

#### 3b. Streaming RAG Responses (SSE)

**Complexity:** Medium | **Effort:** 1 day

Replace full-response RAG with server-sent events for incremental token streaming. This transforms the RAG Chat UI from a waiting game into a real-time conversation.

**Tasks:**
1. Modify `POST /api/v1/knowledge/rag` to support `Accept: text/event-stream` or add a separate `GET /api/v1/knowledge/rag/stream` endpoint
2. Update `RagGenerator` to yield tokens incrementally via LiteLLM streaming
3. Update `RAGChat` component to render incremental messages with cursor
4. Add cancel/disconnect handling

**Files:** `backend/routers/knowledge.py`, `backend/services/rag/generator.py`, `frontend/components/panels/RAGChat.tsx`, `frontend/hooks/useKnowledge.ts`

**Note:** Requires LiteLLM Gateway (Priority 1) to be functional first.

---

#### 3c. GIN Full-Text Search Index Migration

**Complexity:** Low | **Effort:** 1 hour

Add a PostgreSQL GIN index on the `tsvector` column used by hybrid search FTS branch. This is a performance hardening step for production scale.

**Files:** New Alembic migration in `backend/alembic/versions/`

**Verification:** `EXPLAIN ANALYZE` query plan shows index scan instead of sequential scan.

---

#### 3d. Knowledge Graph Visualization

**Complexity:** High | **Effort:** 2–3 days

Node-link diagram showing entity relationships from the knowledge base. This requires either:
- A relationship data model (new table or JSONB field on `knowledge_items`)
- Graph inference from existing knowledge item metadata (tags, kinds, article links)

**Recommended approach for v0.1.0:** Use existing relationship signals (article_id links, shared tags, kind co-occurrence) to build a derived graph. Do not redesign the data model unless Phase 9 explicitly required it.

**Tech options:** D3.js force-directed graph, Cytoscape.js, or a simple SVG renderer.

**Files:** `frontend/components/knowledge/KnowledgeGraph.tsx` (new), `frontend/app/knowledge/page.tsx` (new tab), `backend/routers/knowledge.py` (graph endpoint, optional)

**Risk:** This is the largest item in Phase 9.6. If scope becomes too large, defer to a future Phase 11 and complete 3a–3c first.

---

### Priority 4: Pagination Controls

**Complexity:** Low-Medium | **Effort:** 0.5–1 day

Backend already supports `offset`/`limit` with max 100. Add a reusable `Pagination` UI component and wire it into list views.

**Tasks:**
1. Create `frontend/components/ui/Pagination.tsx`
2. Add page state to `useKnowledge`, `useArticles`, `useTasks`, `useReports` hooks
3. Wire pagination controls into KnowledgePage, ArticlesPanel, TasksPanel, ReportsPanel

**Files:** `frontend/components/ui/Pagination.tsx` (new), `frontend/hooks/*.ts`, affected panel components

**Note:** Can be done in parallel with other items once the hook pattern is established.

---

### Deferred: Phase 10 External Integrations

The following items are officially scoped as Phase 10 in ROADMAP.md. They depend on Track A being stable:

| Item | Complexity | Effort | Dependency |
|------|-----------|--------|------------|
| Hacker News connector | Medium | 0.5 day | None |
| arXiv connector | Medium | 0.5 day | None |
| Twitter/X connector | Medium | 1 day | API credentials |
| LinkedIn connector | Medium-High | 1–2 days | OAuth setup, limited API access |
| Email notification channel | Medium | 1 day | SMTP credentials |
| Telegram Bot channel | Medium | 0.5 day | Bot token |
| Slack Webhook channel | Low | 0.5 day | Webhook URL |
| WeChat channel | Medium-High | 1 day | AppID/secret |
| Bidirectional MCP sync | High | 3–5 days | All MCP servers stable |
| Prometheus/Grafana in compose | Low | 0.5–1 day | None |

These should be planned in a separate Phase 10 document after Phase 9.6 stabilization lands.

---

## Success Criteria

Phase 9.6 is complete when:

1. **`make start` brings up a fully functional system** — RAG API returns answers, not 500s
2. **Users can register, log in, and create content** from the frontend UI
3. **Hybrid search works with filters** — kind/tag scoping on both browse and RAG
4. **RAG responses stream incrementally** — typing indicator replaced by live token rendering
5. **All lists paginate** — no unbounded data loads
6. **489+ tests still pass** — no regressions from Phase 9
7. **Known issues documented** — external blockers recorded, not allowed to block delivery

---

## Risk Register

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| LiteLLM image unavailable or provider keys missing | Medium | Use Ollama as fallback; document missing keys |
| Streaming requires significant RAG generator rewrite | Medium | Start with non-streaming; add SSE as follow-up |
| Knowledge graph visualization scope creep | High | Timebox to derived graph from existing metadata; defer custom relationship model |
| Frontend auth token storage XSS risk | Low | Use httpOnly cookies if possible; document localStorage tradeoff |
| Twitter/LinkedIn connectors require credentials not available | High | Implement skeleton with stub data; document API access requirements |
| WSL Playwright E2E still broken | Certain | Use curl-based API verification; document environment limitation |

---

## Documentation Updates Required

Upon completion:
1. Update `docs/CURRENT_STATE.md` — mark Phase 9.6 items complete, remove from "Next Recommended Tasks"
2. Update `docs/ROADMAP.md` — move Phase 9.6 from proposal to completed, promote Phase 10 details
3. Add `docs/proposals/phase-10-roadmap.md` — detailed external integrations plan built on stabilized foundation
4. Update `docs/CHANGELOG.md` — entry for Phase 9.6 release
