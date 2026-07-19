# AI Intelligence OS — Current State

**Last Updated:** 2026-07-19  
**Version:** 0.1.0 Beta  
**Branch:** master (HEAD: `c9dae14`)

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
- Dashboard with tabbed interface (Dashboard, Articles, Knowledge, Tasks, Agents, Reports)
- Workspace pages: standalone routes for Knowledge and Agents
- Agent execution visualization with core AI product experience
- Rich card components replacing flat tables
- Design token system: custom easing curves, durations, refined colors
- Button system with press feedback and refined variants
- EmptyState component for consistent empty states
- Toast notification system
- Slide-over detail views (KnowledgeDetail)
- MetricCard component
- Modal component with form bodies (KnowledgeForm, ReportForm, TaskForm)
- Sidebar polish, dashboard polish, toast polish

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
- `hooks/` — @tanstack/react-query hooks (useKnowledge, useArticles, useTasks, useReports, useAgentRuns, useAgentStream)
- `lib/` — API client, auth context, query client, toast system, observability

**Workers/Jobs:**
- `workers/jobs/` — Job execution modules including ArticlePipeline (per-article LangGraph execution with research → analyst → translator nodes)
- `workers/scheduler/` — APScheduler-based job scheduling with cron expressions

---

## Recent Changes (last 10 commits)

| Commit | Message |
|--------|---------|
| `c9dae14` | fix(frontend): polish command center interactions |
| `d0d4633` | fix(frontend): polish phase 9 visual consistency issues |
| `90715fe` | fix(frontend): load global styles in app layout |
| `b2c28c7` | fix(frontend): remove stale props from AgentsPanel |
| `62dbea5` | feat(frontend): polish sidebar, dashboard, toasts, slide-over detail views |
| `00137e0` | feat(frontend): workspace pages — rich cards replace flat tables |
| `c6e85fe` | feat(frontend): agent execution visualization |
| `d9f63db` | feat(frontend): add EmptyState component |
| `fae09e3` | feat(frontend): upgrade button system with press feedback |
| `d895326` | feat(frontend): add design token system |

All recent activity has been frontend-focused. Backend services (vector search, RAG, knowledge extraction) were implemented earlier but have not had corresponding frontend workspace pages or deep integration since the dashboard migration to tabbed layout.

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

---

## Next Recommended Tasks

### Immediate (finish Phase 9)
1. Wire up vector search UI — connect KnowledgePage to Qdrant similarity search results
2. Build RAG question-answering interface — chat-style or search-box UI over knowledge base
3. Implement knowledge graph visualization — node-link diagram showing entity relationships
4. Add hybrid search (BM25 + vector fusion) to knowledge search

### Short-term
5. Build frontend auth flow — login/register pages that store JWT tokens and attach to API requests
6. Add pagination controls to all list views (knowledge, articles, tasks, reports)
7. Implement per-tab loading/error states on dashboard
8. Connect agent run button to actual LangGraph workflow execution

### Medium-term (Phase 10)
9. Additional connectors (Twitter/X, LinkedIn, arXiv, Hacker News)
10. Notification channels (Telegram, WeChat, Email SMTP/SES)
11. GitHub issue auto-creation from tasks via MCP
