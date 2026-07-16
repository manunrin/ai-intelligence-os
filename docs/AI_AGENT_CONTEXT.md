# AI Agent Continuation Guide

**Purpose:** Enable Claude Code / ChatGPT / Codex to quickly understand this project and continue development safely.

**Last Updated:** 2026-07-16 (Phase 6-C)

## Quick Start

```bash
make start          # Start all services
make test           # Run tests
```

Open `http://localhost:3000` for the dashboard. API docs at `http://localhost:8000/api/docs`.

## Project Mission

Build an enterprise AI Intelligence Operating System that automatically collects global information, analyzes it with AI agents, creates knowledge, manages tasks, and delivers actionable intelligence.

Core flow: **Information → Knowledge → Action**

## Architecture Summary

**Monorepo** with two main services under Docker Compose:

| Service | Tech | Port | Entry |
|---------|------|------|-------|
| Frontend | Next.js 15 + TypeScript | 3000 | `frontend/app/page.tsx` |
| Backend | FastAPI + Python 3.12+ | 8000 | `backend/main.py` |

**Infrastructure:** PostgreSQL 16, Redis 7, Qdrant v1.11.5, MinIO

**Key patterns:**
- Layered backend: Router → Service → Repository → ORM Model
- Pydantic v2 schemas for all API contracts
- `APIResponse[T]` envelope on every endpoint
- LangGraph StateGraph for agent orchestration
- MCP servers for external integrations (Notion, Asana, Browser, GitHub)
- LiteLLM custom router for multi-provider LLM access

## Current Phase

**Phase 6-C complete.** The frontend dashboard is connected to real backend APIs via 5 read endpoints with pagination. All data flows from database through layered architecture to the UI.

**What's NOT done yet:** Write operations (POST/PUT/DELETE), authentication, per-tab loading states, pagination UI, error boundaries, E2E tests, production deployment.

## Important Design Decisions

### 1. API Response Envelope Pattern
Every endpoint returns `{ success, data, error }`. Frontend uses `unwrap<T>()` to extract arrays. **Do not change this pattern** — it's used across all 5 endpoints and the frontend client.

### 2. Agent Registry Auto-Registration
Agents register themselves at import time via `AgentRegistry.register()`. New agents must be imported in `backend/agents/registry.py` after the registry class definition.

### 3. MCP Tool Fallback
All MCP tools return stub data when no token is configured. Agents check `if tool:` before calling. **Never remove stub paths** — they're tested and required for CI.

### 4. LangGraph Error Isolation
Node failures are caught and recorded in `state.errors`, not raised. The pipeline continues through all stages. **Do not add try/except that raises** in node wrappers.

### 5. Async SQLAlchemy Sessions
All DB access uses async sessions via `get_session_factory()`. Never use sync SQLAlchemy. The session factory is a module-level global initialized at startup.

### 6. Prompt Templates Externalized
All LLM prompts live as `.md` files in `backend/prompts/`, loaded via `load_prompt()`. **Never hardcode prompts in Python code.**

### 7. Pagination Parameters
All list endpoints accept `?offset=0&limit=20` (max 100). Defined in `PaginationParams` model. Frontend currently doesn't use pagination controls.

## Coding Conventions

### Python
- Type hints everywhere (mypy strict mode)
- pydantic-settings for config (`Settings` class in `config.py`)
- Docstrings with Args/Returns format
- Line length: 100 chars
- Ruff linting: E, F, I, N, W, UP, B, SIM
- Imports sorted by ruff isort rules
- Async/await throughout, never blocking calls

### TypeScript
- Strict mode enabled
- Path aliases: `@/*` maps to project root
- Component props as interfaces (not types)
- CSS variables for theming (light/dark via `prefers-color-scheme`)
- TailwindCSS v4 with `@import "tailwindcss"` directive

### Database Models
- UUID primary keys (always `uuid.uuid4()`)
- TIMESTAMPTZ for all timestamps
- `_utcnow()` helper for defaults
- Explicit `foreign_keys=` on dual relationships
- JSONB for flexible payloads
- Alembic autogenerate from models

## Testing Conventions

### Unit Tests
- FastAPI TestClient with patched `get_session_factory`
- Mock LLM responses with `MagicMock` + `AsyncMock`
- Stub MCP tools when no tokens configured
- Parametrize over multiple endpoints/statuses

### Integration Tests
- Skip when credentials not available (`pytest.mark.skipif`)
- Test graph building and compilation
- Test full pipeline with mock LLM
- Verify state schema fields

### Test File Naming
- `test_<entity>.py` for unit tests
- `test_<entity>_real.py` for integration tests requiring credentials
- Fixtures in conftest or inline `@pytest.fixture`

## Documentation Rules

### Existing Documentation Structure
```
docs/
├── AI_INTELLIGENCE_OS_SPEC.md    # Original spec (do not modify)
├── architecture.md               # System architecture (updated Phase 6-C)
├── agent-architecture.md         # Agent design
├── core-agents.md               # Core agent details
├── database-schema.md           # Full schema documentation
├── development-plan.md          # Phase tracking (update when phases complete)
├── future-data-model.md         # Planned tables (document only)
├── ingestion-architecture.md    # Data ingestion design
├── langgraph-architecture.md    # LangGraph design
├── llm-architecture.md          # LLM gateway design
├── mcp-architecture.md          # MCP infrastructure
├── operations-agent-architecture.md  # Operations agents
├── pipeline-architecture.md     # Article pipeline design
├── rag-architecture.md          # RAG system design
├── decisions/                   # ADRs
│   └── ADR-006-dashboard-integration.md
├── logs/                        # Phase implementation logs
├── reports/                     # Phase completion reports
├── PROJECT_STATUS.md            # Current snapshot (this doc's sibling)
├── ROADMAP.md                   # Future phases
├── DEVELOPMENT_GUIDE.md         # How to develop
└── CHANGELOG.md                 # Change history
```

### When Creating Documentation
- Link related docs with relative paths
- Include version/date in frontmatter or header
- Update CHANGELOG.md with each significant change
- Update development-plan.md when phases complete
- Keep future-data-model.md as documentation-only (no code)

## Things NOT to Change Casually

### DO NOT Modify
1. **APIResponse envelope structure** — frontend unwrap() depends on it
2. **UUID primary keys** — distributed-safe design, changing breaks everything
3. **LangGraph edge structure** — nodes expect specific state field names
4. **MCP server registration order** — bootstrap.py registers in specific sequence
5. **Database model column names** — Alembic migrations reference them exactly
6. **Pydantic field names in schemas** — API consumers depend on exact names
7. **_utcnow() pattern** — all models use this for timezone-aware defaults
8. **async session factory global** — module-level singleton, changing requires lifespan rewrite

### DO Add Without Asking
- New prompt template .md files in `backend/prompts/`
- New agent classes following AgentBase pattern
- New MCP server implementations following MCPServerBase pattern
- New repository methods following BaseRepository[T] pattern
- New environment variable prefixes in Settings class
- New Alembic migrations (always review before committing)

### DO Ask Before Modifying
- Database schema changes (review migration impact)
- API endpoint signatures (breaking change risk)
- Frontend component interfaces (affects all consumers)
- Docker Compose service configuration
- LLM provider routing configuration
- Test infrastructure changes

## Common Workflows

### Adding a Read Endpoint
1. Create model (if new) in `backend/database/models/`
2. Create repository in `backend/repositories/` extending BaseRepository
3. Create schema in `backend/schemas/`
4. Create service in `backend/services/`
5. Create router in `backend/routers/`
6. Register in `backend/routers/api.py`
7. Add to frontend `types/index.ts`
8. Add to dashboard `page.tsx` fetch
9. Write unit tests

### Adding an Agent
1. Create `backend/agents/<name>/agent.py` extending AgentBase
2. Create `backend/agents/<name>/schemas.py` with Pydantic models
3. Create `backend/prompts/<name>.md`
4. Register in `backend/agents/registry.py`
5. Wire into workflow in `backend/workflows/graph/`
6. Write unit tests in `tests/unit/agents/`

### Adding an MCP Server
1. Create `backend/mcp/servers/<name>/server.py` extending MCPServerBase
2. Implement tools in `tools.py` extending MCPTool
3. Register in `backend/app/bootstrap.py`
4. Wire into agents that need it
5. Write tests in `tests/unit/mcp/`
