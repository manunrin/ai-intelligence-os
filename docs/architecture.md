# System Architecture

**Version:** 0.1.0  
**Last Updated:** 2026-07-16 (Phase 6-C)

## 1. High-Level Architecture

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
│  │ Routes   │  │ Services │  │ Repos    │                   │
│  └──────────┘  └──────────┘  └──────────┘                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    Agent Runtime Layer                       │
│                 (LangGraph State Machines)                   │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐              │
│  │Resrch│→│Analyse│→│Transl │→│Knowlge│→│PM/Notif│            │
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

## 2. Frontend Architecture

### Technology

- **Framework:** Next.js 15 App Router with TypeScript 5.7
- **Styling:** TailwindCSS v4 with CSS custom properties for light/dark themes
- **Components:** Hand-built UI components inspired by shadcn/ui patterns
- **Build:** Standalone output mode (`output: "standalone"`)

### Directory Structure

```
frontend/
├── app/
│   ├── layout.tsx          # Root layout with metadata
│   ├── page.tsx            # Dashboard — main entry point
│   └── globals.css         # Theme variables (light/dark)
├── components/ui/
│   ├── Badge.tsx           # Status badges with variants
│   ├── Button.tsx          # Buttons with variant/size system
│   ├── Card.tsx            # Content cards with header/footer
│   ├── Input.tsx           # Form inputs with validation states
│   ├── StatCard.tsx        # KPI stat cards with accent borders
│   └── Table.tsx           # DataTable with renderCell customization
├── lib/
│   └── api.ts              # API client + unwrap() envelope helper
└── types/
    └── index.ts            # TypeScript types for all entities
```

### Key Components

**Dashboard (`page.tsx`):**
- Tabbed interface: Dashboard, Articles, Knowledge, Tasks, Agents, Reports
- Stats row with 4 StatCards showing aggregate counts
- Concurrent data fetching via `Promise.all` across 5 endpoints
- `unwrap<T>()` helper extracts `data` array from backend's `APIResponse` envelope
- Conditional rendering with loading skeleton and error banner
- Badge-based status coloring per entity type

**API Client (`lib/api.ts`):**
- `request<T>()` base function with error parsing
- `api.get/post/put/delete()` methods
- `unwrap<T>()` handles both envelope-wrapped responses and raw arrays
- Reads `NEXT_PUBLIC_API_URL` from environment, defaults to `http://localhost:8000`

**Type System (`types/index.ts`):**
- 6 entity types: Article, KnowledgeItem, AgentRun, Task, IntelligenceReport, AgentInfo
- All use `& Record<string, unknown>` for flexible backend data
- Strict discriminated unions for status/priority enums

### Data Flow

```
page.tsx
  ↓ Promise.all([
  ↓   api.get("/api/v1/articles"),
  ↓   api.get("/api/v1/knowledge"),
  ↓   api.get("/api/v1/tasks"),
  ↓   api.get("/api/v1/agents/runs"),
  ↓   api.get("/api/v1/reports")
  ↓ ])
  ↓ unwrap<T>() extracts data from { success, data, error } envelope
  ↓ React state (useState)
  ↓ DataTable / Card / StatCard render
```

## 3. Backend Architecture

### Technology

- **Framework:** FastAPI 0.115+ with async-first design
- **Validation:** Pydantic v2 request/response models
- **Database:** SQLAlchemy 2.0 async with asyncpg driver
- **Migrations:** Alembic with async engine support

### Layered Architecture

```
backend/
├── main.py                 # App factory, lifespan, CORS, router registration
├── config.py               # Settings class (pydantic-settings)
├── routers/                # Layer 1: HTTP routing
│   ├── api.py              # Aggregated router (includes all sub-routers)
│   ├── articles.py         # GET /api/v1/articles
│   ├── knowledge.py        # GET /api/v1/knowledge
│   ├── tasks.py            # GET /api/v1/tasks
│   ├── agents.py           # GET /api/v1/agents/runs
│   ├── reports.py          # GET /api/v1/reports
│   ├── deps.py             # FastAPI dependencies (get_db, get_settings)
│   ├── errors.py           # Exception handlers + logging middleware
│   └── pagination.py       # PaginationParams shared model
├── services/               # Layer 2: Business logic
│   ├── article_service.py  # ArticleService (list, count)
│   ├── knowledge_service.py (legacy)
│   ├── knowledge/          # Layer 2b: Extended knowledge ops
│   │   └── service.py      # KnowledgeService (create, create_from_analysis/translation)
│   ├── task_service.py     # TaskService (list)
│   ├── agent_service.py    # AgentService (list runs)
│   ├── report_service.py   # ReportService (list)
│   ├── ingestion/          # Data ingestion
│   │   └── service.py      # IngestionService (fetch→dedup→save→publish events)
│   ├── llm/                # LLM gateway
│   │   ├── base.py         # LLMProvider ABC, ChatMessage, ChatResponse
│   │   ├── client.py       # LLMClient (unified interface)
│   │   ├── router.py       # LLMRouter (provider selection, fallback chains)
│   │   └── providers/      # 4 provider implementations
│   │       ├── openai.py
│   │       ├── anthropic.py
│   │       ├── ollama.py
│   │       └── compatible.py
│   ├── embedding/          # Embedding service
│   │   ├── base.py         # EmbeddingProvider, EmbeddingResult
│   │   └── client.py       # EmbeddingClient (batch support)
│   ├── vector/             # Vector store
│   │   └── qdrant.py       # QdrantVectorService (httpx-based)
│   └── rag/                # RAG pipeline
│       ├── retriever.py    # RagRetriever (vector search + DB fallback)
│       └── generator.py    # RagGenerator (context synthesis)
├── repositories/           # Layer 3: Data access
│   ├── base_repository.py  # BaseRepository[T] generic CRUD
│   ├── article_repository.py
│   ├── knowledge_repository.py
│   ├── task_repository.py
│   ├── agent_run_repository.py
│   └── report_repository.py
├── schemas/                # Layer 4: API contracts
│   ├── response.py         # APIResponse[T] generic envelope
│   ├── article.py          # ArticleResponse
│   ├── knowledge.py        # KnowledgeItemResponse
│   ├── task.py             # TaskResponse
│   ├── agent_run.py        # AgentRunResponse
│   └── report.py           # IntelligenceReportResponse
├── database/               # Data layer
│   ├── base.py             # SQLAlchemy Base, _utcnow helper
│   ├── connection.py       # Engine factory, session management
│   └── models/             # ORM entities (9 tables)
│       ├── source.py
│       ├── article.py
│       ├── intelligence_report.py
│       ├── knowledge_item.py
│       ├── task.py
│       ├── agent.py
│       ├── agent_run.py
│       ├── workflow.py
│       └── user_preference.py
├── agents/                 # Agent runtime
│   ├── base.py             # AgentBase, AgentMetadata, AgentState
│   ├── registry.py         # AgentRegistry (auto-registration)
│   ├── research/agent.py
│   ├── analyst/agent.py
│   ├── translator/agent.py
│   ├── knowledge/agent.py
│   ├── pronunciation/agent.py
│   ├── project_manager/agent.py
│   └── notification/agent.py
├── workflows/              # Workflow orchestration
│   ├── base.py             # WorkflowBase, WorkflowContext
│   ├── daily_intelligence.py
│   ├── autonomous_intelligence.py
│   ├── knowledge_pipeline.py
│   └── graph/              # LangGraph builders
│       ├── builder.py      # build_intelligence_graph()
│       ├── nodes.py        # research/analyst/translators nodes
│       ├── state.py        # IntelligenceState
│       ├── ops_nodes.py    # knowledge/pronunciation/pm/notification nodes
│       ├── operations_state.py  # OperationsState
│       ├── autonomous_nodes.py   # Autonomous workflow nodes
│       └── autonomous_state.py   # AutonomousState
├── pipelines/              # Per-article processing
│   ├── __init__.py
│   └── article_pipeline.py # ArticlePipeline
├── mcp/                    # MCP infrastructure
│   ├── base.py             # MCPServerBase, MCPTool
│   ├── client.py           # MCPClient (HTTP/SSE transport)
│   ├── registry.py         # MCPRegistry (server registration, tool lookup)
│   ├── schemas.py          # MCPServerConfig, MCPToolDefinition
│   └── servers/            # 4 server implementations
│       ├── notion/server.py + tools.py
│       ├── asana/server.py + tools.py
│       ├── browser/server.py + tools.py
│       └── github/server.py + tools.py
├── tools/                  # Local tool system
│   ├── base.py             # ToolBase, ToolResult
│   └── registry.py         # ToolRegistry (local + MCP fallback)
├── connectors/             # Data ingestion
│   ├── base.py             # SourceConnector (fetch→parse→normalize)
│   ├── rss/openai_blog.py  # OpenAIBlogRssConnector
│   └── api/                # API connector package
├── workers/                # Background jobs
│   ├── jobs/               # Job implementations
│   │   ├── daily_intelligence_job.py
│   │   ├── autonomous_intelligence_job.py
│   │   └── service.py      # DailyIntelligenceJob, AutonomousIntelligenceJob
│   └── scheduler/          # APScheduler wrapper
│       └── scheduler.py    # JobScheduler
├── events/                 # Event system
│   ├── event.py            # BaseEvent, ArticleCreatedEvent
│   └── publisher.py        # EventPublisher (subscriber registry)
├── prompts/                # Prompt templates
│   ├── loader.py           # load_prompt(), list_available_prompts()
│   └── *.md                # 14 prompt template files
└── alembic/                # Database migrations
    ├── env.py              # Async migration runner
    └── versions/           # 2 migrations
        ├── 0001_initial.py
        └── 0002_operations_agents.py
```

### API Endpoints

| Method | Path | Summary | Operation ID |
|--------|------|---------|--------------|
| GET | `/api/health` | Health check | — |
| GET | `/api/v1/articles` | List articles | listArticles |
| GET | `/api/v1/knowledge` | List knowledge items | listKnowledgeItems |
| GET | `/api/v1/tasks` | List tasks | listTasks |
| GET | `/api/v1/agents/runs` | List agent runs | listAgentRuns |
| GET | `/api/v1/reports` | List intelligence reports | listReports |

All endpoints support pagination (`?offset=0&limit=20`, max 100). All return `APIResponse[T]` envelope.

### Response Envelope

```python
class APIResponse(Generic[T]):
    success: bool
    data: T | None
    error: str | None = None
```

Frontend `unwrap()` extracts the `data` field automatically.

### Exception Handling

Centralized handlers in `routers/errors.py`:
- `NotFoundException` → 404
- `BadRequestException` → 400
- `RequestValidationError` → 422
- Generic `Exception` → 500 (with logging)

All errors return `{success: false, data: null, error: "message"}`.

## 4. Database Architecture

### Entity Relationship Diagram

```
sources 1──* articles *──1 intelligence_reports
                  │
                  ├──* knowledge_items
                  │
                  └──1 tasks

agents 1──* agent_runs *──1 workflows
              │
              ├──* intelligence_reports
              │
              └──* tasks

knowledge_items optional links to: sources, articles, intelligence_reports
tasks optional link to: knowledge_items, agent_runs
user_preferences standalone keyed by user_id + key
```

### Tables

| Table | Rows | Purpose |
|-------|------|---------|
| sources | Information origins | RSS feeds, blog URLs, GitHub repos |
| articles | Raw intelligence items | Collected content with status tracking |
| intelligence_reports | Analyst outputs | Aggregated analysis with importance scores |
| knowledge_items | Persisted knowledge | Entries with vector embeddings for semantic search |
| tasks | Actionable items | Created by ProjectManagerAgent |
| agents | Agent definitions | LangGraph serialized graph definitions |
| agent_runs | Execution instances | Individual agent run records |
| workflows | Top-level definitions | Multi-agent pipeline orchestration |
| user_preferences | User configuration | Personalization settings |

### Design Decisions

1. **UUID primary keys** — distributed-safe, no sequential ID leakage
2. **JSONB for payloads** — flexible agent state without schema migrations
3. **TIMESTAMPTZ everywhere** — timezone-aware timestamps for global operation
4. **Soft deletes via status fields** — agent runs and articles retain history
5. **Array columns for tags/IDs** — PostgreSQL-native, avoids join tables
6. **FK relationships with explicit foreign_keys** — disambiguates dual relationships

### Migrations

- `0001_initial` — Full schema generation from SQLAlchemy models (9 tables, 20+ indexes)
- `0002_operations_agents` — Added `language_data`/`learning_notes` to knowledge_items, `generated_by_agent` to tasks

## 5. Agent Architecture

### AgentBase Contract

```python
class AgentBase(ABC):
    name: str = "base_agent"
    version: str = "0.1.0"
    description: str = "..."

    async def execute(input_data: dict) -> dict:
        # Returns: {"success": bool, "output": any, "metadata": AgentMetadata}
```

### Agent Registry

Auto-registers all concrete agents at import time:

```python
for agent_cls in (KnowledgeAgent, PronunciationAgent, ProjectManagerAgent, NotificationAgent):
    AgentRegistry.register(agent_cls)
```

Lookup: `AgentRegistry.instantiate("knowledge", llm_client=client, mcp_registry=registry)`

### Agent Lifecycle

```
Create → Execute → Complete/Fail → Inspect metadata
```

Each agent tracks: run_id, started_at, state (IDLE/RUNNING/COMPLETED/FAILED/INTERRUPTED), error message.

### Agent-MCP Integration Pattern

Agents optionally receive an `MCPRegistry`. When present, they call tools via the registry:

```python
tool = self._mcp_registry.get_tool("notion.create_page")
if tool:
    result = await tool.execute(title=title, parent_id=parent_id, content=content)
```

When absent, agents fall back gracefully (return None/empty results).

## 6. Workflow Architecture

### Three Workflow Layers

**1. WorkflowBase (abstract)** — Ordered agent chain with shared context:
```
Input → Agent[0].execute() → Agent[1].execute() → ... → Final Output
```

**2. LangGraph StateGraph** — Stateful node-based execution:
- `build_intelligence_graph()` — research → analyst → translator
- `build_autonomous_intelligence_graph()` — full 6-node pipeline
- `build_knowledge_pipeline_graph()` — combines intelligence + operations

**3. Job Services** — Scheduled execution:
- `DailyIntelligenceJob` — Basic pipeline via APScheduler
- `AutonomousIntelligenceJob` — Full pipeline with MCP integration

### State Schemas

Three Pydantic models flow through graphs:

| Schema | Fields | Used By |
|--------|--------|---------|
| IntelligenceState | topic, focus_areas, research_result, analysis_result, translation_result, errors | Daily pipeline |
| OperationsState | + knowledge_result, pronunciation_result, project_plan_result, notification_result | Knowledge pipeline |
| AutonomousState | + article_id, content, tags, source, knowledge_result, project_plan_result, notification_result | Autonomous workflow |

### Error Handling

Node failures are caught and recorded in `state.errors` rather than raising. The pipeline continues through all stages even when individual nodes fail.

## 7. MCP Integration Architecture

### Design Principles

- **Abstraction over implementation** — Agents call `registry.get_tool("notion.create_page")`, never import Notion SDK
- **Uniform contract** — Every tool implements `execute(**kwargs) -> {"success": bool, "data": any}`
- **Token isolation** — Credentials live in server config, not agent code
- **Unified discovery** — `registry.list_schemas()` returns all available tools for LLM prompting

### Server Registration

All 4 servers registered at application bootstrap:

```python
ApplicationBootstrap.initialize():
    for server_cls in (NotionMCPServer, AsanaMCPServer, BrowserMCPServer, GitHubMCPServer):
        mcp_registry.register_server(server_cls())
    tool_registry.set_mcp_registry(mcp_registry)
```

### Deployment Modes

1. **Embedded** (current) — All servers run inside backend process
2. **Standalone** — Each server as separate container with HTTP endpoint
3. **Hybrid** — Core servers embedded; experimental ones standalone

## 8. Data Flow Diagrams

### Article Ingestion Flow

```
External Source (RSS/API)
    ↓ fetch()
SourceConnector.parse()
    ↓ normalize()
RawArticle (standardized)
    ↓ IngestionService.ingest()
Dedup (SHA-256 URL hash)
    ↓ save()
Article (PostgreSQL)
    ↓ publish()
ArticleCreatedEvent → subscribers
```

### Intelligence Pipeline Flow

```
Article (DB)
    ↓ ArticlePipeline.run(article_id)
    ↓
LangGraph StateGraph:
    START → research_node → analyst_node → translator_node → END
    ↓                              ↓               ↓
ResearchAgent              AnalystAgent     TranslatorAgent
    ↓                              ↓               ↓
research_result          analysis_result   translation_result
    ↓                              ↓               ↓
KnowledgeService.create() → KnowledgeItem (DB)
```

### Autonomous Intelligence Flow

```
Article (DB)
    ↓ ArticlePipeline.run()
KnowledgeItem (DB)
    ↓
AutonomousWorkflow (LangGraph):
    START → research → analyst → translator → knowledge → project_manager → notification → END
    ↓                                                    ↓                    ↓
KnowledgeAgent (+ Notion MCP)                    ProjectManagerAgent      NotificationAgent
    ↓                                                    ↓                    ↓
notion_page_id / notion_url                    asana_task_ids[]           markdown digest
```

### API Request Flow

```
Browser (page.tsx)
    ↓ fetch("/api/v1/articles")
FastAPI CORSMiddleware
    ↓
Router (/articles)
    ↓ Depends(get_db) → AsyncSession
ArticleService.list_articles(offset, limit)
    ↓
ArticleRepository.list_all(offset, limit)
    ↓
SQLAlchemy select(Article).order_by().offset().limit()
    ↓
PostgreSQL
    ↓
ArticleService._to_dict() → serializable dict
    ↓
ArticleResponse.model_validate() → Pydantic model
    ↓
APIResponse(success=True, data=[...], error=None)
    ↓ JSON
Browser unwrap<T>() → T[]
    ↓
React state → DataTable render
```
