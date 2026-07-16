# Architecture

## System Overview

AI Intelligence OS is a layered platform that transforms raw information into actionable knowledge through AI agents.

```
┌─────────────────────────────────────────────────────────────┐
│                        User Interface                        │
│                   (Next.js + shadcn/ui)                      │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS / API
┌──────────────────────────▼──────────────────────────────────┐
│                     Backend API Layer                        │
│                  (FastAPI + Pydantic)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │ Auth     │  │ Routes   │  │ Services │                   │
│  └──────────┘  └──────────┘  └──────────┘                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    Agent Runtime Layer                       │
│                 (LangGraph State Machines)                   │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐              │
│  │Super │→│Resrch│→│Analyse│→│Transl │→│Knowlge│→...         │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘              │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    MCP Server Layer                          │
│         (Notion · Asana · Browser · GitHub)                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    Data & Storage Layer                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │PostgreSQL│ │  Qdrant  │ │  Redis   │ │  MinIO   │       │
│  │(relational│ │(vector  │ │(cache   │ │(object   │       │
│  │  data)   │ │ search)  │ │ store)  │ │ storage) │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  External Services Layer                     │
│  ┌────────────────┐    ┌────────────────┐                   │
│  │ LiteLLM Gateway│    │ Provider APIs  │                   │
│  │ (unified LLM)  │───▶│ GPT · Claude   │                   │
│  └────────────────┘    │ · Gemini · ... │                   │
│                        └────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### Backend (`backend/`)
- RESTful API with OpenAPI auto-documentation
- Pydantic v2 request/response validation
- Async SQLAlchemy 2.0 for database access
- Modular router structure — one file per resource domain
- Service layer encapsulates business logic

### Frontend (`frontend/`)
- Next.js App Router with TypeScript
- TailwindCSS + shadcn/ui component library
- Client components for data fetching (dashboard uses `fetch` via custom API client)
- API client with response envelope unwrapping (`unwrap()` helper)
- CORS-aware: backend configured to allow frontend dev server origin
- DataTable, Card, StatCard, Badge, Button, Input components

### Agents (`agents/`)
- LangGraph state machines define agent workflows
- Each agent is a node in a directed graph
- State transitions are explicit and serializable
- Human-in-the-loop approval gates via interrupt nodes

### MCP Servers (`mcp_servers/`)
- Each server exposes tools/resources/prompts via MCP
- Isolated process per integration (Notion, Asana, etc.)
- Shared agent runtime consumes MCP tool outputs

### Workers (`workers/`)
- Background job processing (scheduled crawls, analysis pipelines)
- Message queue driven (Redis broker)
- Idempotent task design with retry policies

### Database (`database/`)
- Alembic-managed migrations
- Version-controlled seed data
- init.sql for Docker Compose bootstrap

### Monitoring (`monitoring/`)
- OpenTelemetry for traces, metrics, logs
- Prometheus scrape configs
- Grafana dashboard definitions

## Data Flow

### API Request → Response Flow

```
Dashboard (page.tsx)
  ↓ Promise.all([
  ↓   api.get("/api/v1/articles"),
  ↓   api.get("/api/v1/knowledge"),
  ↓   api.get("/api/v1/tasks"),
  ↓   api.get("/api/v1/agents/runs"),
  ↓   api.get("/api/v1/reports")
  ↓ ])
  ↓ unwrap<T>() extracts data from { success, data, error } envelope
Backend FastAPI
  ↓ CORSMiddleware (allows localhost:3000)
  ↓ Router → Service → Repository → ORM
  ↓ Returns APIResponse[T] envelope
Frontend
  ↓ unwrap() extracts T[] from data field
  ↓ React state updated
  ↓ DataTable / Card / StatCard render results
```

1. **Ingestion** — Scheduler triggers Research/Crawler agents → external sources
2. **Analysis** — Analyst Agent evaluates importance, category, impact
3. **Translation** — Translator Agent produces CN/JP/EN versions
4. **Knowledge** — Knowledge Agent stores to PostgreSQL + Qdrant vector index
5. **Action** — Project Manager Agent creates tasks in Asana, pages in Notion
6. **Notification** — Notification Agent alerts via Telegram/WeChat/Email

## Technology Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Web framework | FastAPI | Native async, auto OpenAPI, Pydantic validation |
| Agent orchestration | LangGraph | Explicit state machine, human-in-the-loop, persistent state |
| LLM abstraction | LiteLLM | Single interface for 100+ providers, fallback chains |
| Vector DB | Qdrant | Rust performance, Python SDK, filter-based search |
| Container orchestration | Docker Compose | Local dev simplicity, production-ready with swarm/K8s migration path |
