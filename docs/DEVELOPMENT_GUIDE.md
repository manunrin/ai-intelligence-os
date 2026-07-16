# Development Guide

**Last Updated:** 2026-07-16 (Phase 6-C)

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.12+ | Backend runtime |
| Node.js | 22+ | Frontend build |
| Docker | 29+ | Container orchestration |
| Docker Compose | v5+ | Multi-container management |
| Git | Latest | Version control |

## Environment Setup

### 1. Clone and Initialize

```bash
cd /path/to/ai-intelligence-os

# Copy environment template
cp .env.development.example .env
```

### 2. Backend Virtual Environment

```bash
cd backend
python -m venv .venv
source .venv/bin/activate    # Linux/macOS
# or
.venv\Scripts\activate       # Windows

pip install -e ".[dev]"
```

### 3. Frontend Dependencies

```bash
cd frontend
npm install
```

### 4. Infrastructure Services

```bash
make start
# Starts: PostgreSQL, Redis, Qdrant, MinIO, Backend, Frontend
```

Wait ~30 seconds for all services to become healthy, then verify:

```bash
make ps
```

## Running Services

### Backend

```bash
# Via Docker (recommended)
make start

# Directly (development)
cd backend
uvicorn main:app --reload --port 8000
```

API docs available at: `http://localhost:8000/api/docs`

### Frontend

```bash
cd frontend
npm run dev
```

Dashboard available at: `http://localhost:3000`

### Both Together

```bash
make start    # Starts all services via Docker Compose
make stop     # Stops all services (data preserved)
make logs     # Follow all service logs
make logs-svc svc=backend    # Single service log
```

## Database

### Migrations

```bash
# Run all pending migrations
make init-db

# Or directly:
docker compose exec backend alembic upgrade head

# Create a new migration (after changing models):
docker compose exec backend alembic revision --autogenerate -m "description"
```

### Database Shell

```bash
# psql
make db-shell

# Direct:
docker compose exec postgres psql -U postgres -d ai_intelligence_os
```

### Reset Database

```bash
make clean          # Remove all containers and volumes
make start          # Fresh start (recreates schema from init)
```

## Testing

```bash
# All tests
make test

# Unit tests only
make test-unit

# Integration tests only
make test-integration

# Direct:
docker compose exec backend pytest -v
docker compose exec backend pytest tests/unit/ -v
docker compose exec backend pytest tests/integration/ -v
```

### Test Structure

```
tests/
├── unit/
│   ├── agents/           # Agent registry, individual agent execution
│   ├── mcp/              # MCP servers, tool definitions, registry
│   └── routers/          # API endpoints, pagination, schemas
└── integration/
    ├── mcp/              # Real API integration tests (skipped without credentials)
    └── test_autonomous_workflow.py  # End-to-end pipeline test
```

## Configuration

### Environment Variables

All configuration comes from `.env`. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://postgres:postgres@postgres:5432/ai_intelligence_os` | PostgreSQL connection |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `QDRANT_URL` | `http://qdrant:6333` | Vector database |
| `MINIO_ENDPOINT` | `minio:9000` | Object storage |
| `LITELLM_GATEWAY_URL` | `http://litellm:4000` | LLM gateway |
| `APP_DEBUG` | `true` (dev) / `false` (prod) | Debug mode |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Frontend API base URL |

### Environment Profiles

| Profile | File | Differences |
|---------|------|-------------|
| Development | `.env.development.example` | Debug on, pool_min=1, local ports exposed |
| Test | `.env.test.example` | Isolated DB names/indices, mock keys |
| Production | `.env.production.example` | Debug off, strong passwords, pool increased |

### LLM Routing Config

`backend/config/models.yaml` defines provider routing:

```yaml
defaults:
  provider: openai
  model: gpt-4o

routing:
  summary:   - [openai, gpt-4o]
              - [anthropic, claude-sonnet-4-20250514]
  translation:- [compatible, qwen-max]
               - [openai, gpt-4o]
  research:   - [openai, gpt-4o]
              - [anthropic, claude-sonnet-4-20250514]
  analysis:   - [anthropic, claude-sonnet-4-20250514]
              - [openai, gpt-4o]
  local:      - [ollama, mistral]
              - [compatible, qwen2.5]
  embedding:  - [openai, text-embedding-3-small]
              - [compatible, bge-m3]
```

## MCP Configuration

Set tokens in `.env` to enable real API calls. Without tokens, MCP tools return stub data.

| Token | Env Variable | Server |
|-------|--------------|--------|
| Notion | `NOTION_TOKEN` + `NOTION_DATABASE_ID` | NotionMCPServer |
| Asana | `ASANA_TOKEN` + `ASANA_WORKSPACE_ID` + `ASANA_PROJECT_ID` | AsanaMCPServer |
| GitHub | `GITHUB_TOKEN` + `GITHUB_OWNER` + `GITHUB_REPOSITORY` | GitHubMCPServer |
| Browser | `BROWSER_API_URL` + `BROWSER_API_KEY` | BrowserMCPServer |

## Common Development Tasks

### Adding a New Endpoint

1. **Create repository** (if needed) in `backend/repositories/`
2. **Create service** in `backend/services/`
3. **Create schema** in `backend/schemas/`
4. **Create router** in `backend/routers/`
5. **Register router** in `backend/routers/api.py`
6. **Add tests** in `tests/unit/routers/`

### Adding a New Agent

1. **Create agent class** extending `AgentBase` in `backend/agents/<name>/agent.py`
2. **Define schema** in `backend/agents/<name>/schemas.py` (Pydantic models)
3. **Register** in `backend/agents/registry.py` (auto-registration pattern)
4. **Add prompt template** in `backend/prompts/<name>.md`
5. **Add tests** in `tests/unit/agents/`
6. **Wire into workflow** in `backend/workflows/graph/`

### Adding a New MCP Server

1. **Create server** extending `MCPServerBase` in `backend/mcp/servers/<name>/server.py`
2. **Implement tools** extending `MCPTool` in `tools.py`
3. **Register** in `backend/app/bootstrap.py` ApplicationBootstrap
4. **Add tests** in `tests/unit/mcp/` and/or `tests/integration/mcp/`

### Creating a Database Migration

1. **Modify model** in `backend/database/models/<entity>.py`
2. **Generate migration:**
   ```bash
   docker compose exec backend alembic revision --autogenerate -m "description"
   ```
3. **Review generated migration** in `backend/alembic/versions/`
4. **Test migration:**
   ```bash
   docker compose exec backend alembic downgrade base
   docker compose exec backend alembic upgrade head
   ```

## Troubleshooting

### Backend won't start

```bash
# Check if dependencies are installed
docker compose exec backend pip list | grep fastapi

# Check database connectivity
docker compose exec backend python -c "from backend.config import get_settings; print(get_settings().database_url)"

# View startup logs
make logs-svc svc=backend
```

### Frontend can't connect to backend

1. Verify `.env` has `NEXT_PUBLIC_API_URL=http://localhost:8000`
2. Check CORS is configured (it is by default in `main.py`)
3. Verify backend is running: `curl http://localhost:8000/api/health`

### Database migration fails

```bash
# Check current migration head
docker compose exec backend alembic current

# Check for unapplied migrations
docker compose exec backend alembic history --rev-range base:head

# Force reset (WARNING: destroys data)
docker compose exec backend alembic downgrade base
docker compose exec backend alembic upgrade head
```

### Qdrant not reachable

```bash
# Check Qdrant health
curl http://localhost:6333/health

# Recreate collection (via code on first use)
# QdrantVectorService.ensure_collection() creates it automatically
```

### Port conflicts

```bash
# Check what's using common ports
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
lsof -i :6333  # Qdrant
lsof -i :8000  # Backend
lsof -i :3000  # Frontend

# Change ports in .env using POSTGRES_PORT, REDIS_PORT, etc.
```

## Code Style

### Python

```bash
# Lint
ruff check .

# Format
ruff format .

# Type check
mypy .
```

Configuration in `backend/pyproject.toml`:
- Target: Python 3.12
- Line length: 100
- Ruff selects: E, F, I, N, W, UP, B, SIM
- MyPy: strict mode

### TypeScript

```bash
cd frontend
npm run type-check   # tsc --noEmit
npm run lint           # next lint
```

Configuration in `frontend/tsconfig.json`:
- Strict mode enabled
- Path aliases: `@/*` → `./`
- Target: ES2022
- Module: bundler

## Docker Operations

```bash
# Full lifecycle
make start            # Build and start all services
make stop             # Stop (preserve data)
make rebuild          # Rebuild without cache
make clean            # Remove everything including volumes

# Service-specific
docker compose logs -f backend    # Backend logs
docker compose logs -f frontend   # Frontend logs
docker compose exec backend bash  # Backend shell

# Volume management
docker volume ls | grep ai-intelligence-os
docker volume rm ai-intelligence-os_postgres_data  # DANGER: deletes data
```
