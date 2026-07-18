# AI Intelligence OS

Enterprise-grade AI operating system connecting **Information → Knowledge → Action** through intelligent agent workflows, RAG pipelines, and real-time observability.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org)
[![Docker Compose](https://img.shields.io/badge/docker-compose-compatible-brightgreen.svg)](https://docs.docker.com/compose/)

## Architecture

```
┌──────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│  Browser  │────▶│  Next.js FE  │────▶│  FastAPI Backend │────▶│ LangGraph     │
│           │     │  (React 19)  │     │  (REST API)      │     │ Agent Runtime │
└──────────┘     └──────────────┘     └────────┬────────┘     └───────┬──────┘
                                                │                      │
                     ┌──────────────────────────┘                      │
                     ▼                                                  ▼
              ┌──────────────┐                                ┌─────────────────┐
              │   Prometheus │                                │  Agent Workers   │
              │   + Grafana  │                                │  (Async)         │
              └──────────────┘                                └────────┬────────┘
                                                                        │
                     ┌──────────────────────────────────────────────────┤
                     ▼                                                  ▼
            ┌─────────────────┐    ┌──────────────┐    ┌─────────────────────────┐
            │ PostgreSQL      │    │ Qdrant       │    │ MinIO Object Storage    │
            │ (Relational)    │    │ (Vector DB)  │    │ (Documents/Files)       │
            └─────────────────┘    └──────────────┘    └─────────────────────────┘
                     │                    │
                     ▼                    ▼
               ┌──────────┐        ┌──────────┐
               │  Redis   │        │  LLMs    │
               │ (Cache/  │        │ (OpenAI, │
               │  Queue)  │        │ Anthropic│
               └──────────┘        └──────────┘
```

## Key Features

| Feature | Description |
|---------|-------------|
| **Agent Runtime** | LangGraph-based agent orchestration with stage tracking and async execution |
| **LLM Gateway** | Multi-provider routing with automatic fallback (OpenAI, Anthropic, Ollama, Compatible) |
| **RAG Pipeline** | Embedding generation + vector search via Qdrant for knowledge retrieval |
| **Knowledge Layer** | Structured knowledge base with articles, tasks, reports, and audit trails |
| **Observability** | Prometheus metrics, OpenTelemetry tracing, Grafana dashboards, alerting rules |
| **MCP Integration** | Model Context Protocol connectors for Notion, Asana, GitHub, Browser |
| **REST API** | Auto-generated OpenAPI/Swagger docs at `/docs` |
| **Frontend** | Next.js 15 dashboard with real-time agent stream tracking |

## Quick Start

### Prerequisites

- Docker Engine 24+ with Docker Compose v2
- 4 GB RAM minimum (8 GB recommended)
- Python 3.12+ (for local development outside Docker)

### One-command start

```bash
# 1. Clone and configure
git clone https://github.com/your-org/ai-intelligence-os.git
cd ai-intelligence-os
cp .env.development.example .env

# 2. Start all services
make start

# 3. Open in browser
open http://localhost:3000
```

Services will be available at:

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 |

### Development mode

```bash
# Start infrastructure only
docker compose up -d postgres redis qdrant minio

# Run backend locally (requires .env)
uv pip install -e ".[dev]"
python -m backend.main

# Run frontend locally
cd frontend && npm install && npm run dev
```

## Environment Variables

Copy `.env.development.example` to `.env` and adjust as needed.

### Required

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://postgres:postgres@postgres:5432/ai_intelligence_os` | PostgreSQL connection string |
| `REDIS_URL` | `redis://:redispassword@redis:6379/0` | Redis connection string |
| `QDRANT_URL` | `http://qdrant:6333` | Qdrant vector database URL |
| `MINIO_ENDPOINT` | `minio:9000` | MinIO object storage endpoint |

### LLM Providers (at least one required)

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key for GPT models |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude models |
| `OLLAMA_BASE_URL` | Local Ollama instance URL |
| `COMPATIBLE_API_BASE` | OpenAI-compatible API base URL |

### MCP Integrations (optional)

| Variable | Description |
|----------|-------------|
| `NOTION_TOKEN` / `NOTION_DATABASE_ID` | Notion integration |
| `ASANA_TOKEN` / `ASANA_WORKSPACE_ID` / `ASANA_PROJECT_ID` | Asana integration |
| `GITHUB_TOKEN` / `GITHUB_OWNER` / `GITHUB_REPOSITORY` | GitHub integration |

See [`.env.example`](.env.example) for the complete list with descriptions.

## Docker Deployment

### Full stack

```bash
make start          # Build and start all services
make stop           # Stop all services (data preserved)
make rebuild        # Rebuild without cache
make clean          # Remove containers, networks, volumes
make logs           # Follow all service logs
```

### Database

```bash
make init-db        # Run Alembic migrations
make db-shell       # Open PostgreSQL shell
```

### Testing

```bash
make test           # Run full test suite inside container
make test-unit      # Unit tests only
make test-integration  # Integration tests only
make test-coverage  # Tests with coverage report
```

## Project Structure

```
├── frontend/          # Next.js 15 dashboard application
├── backend/           # FastAPI REST API + metrics module
│   ├── routers/       # API route handlers
│   ├── services/      # Business logic (agent, LLM, embedding, vector)
│   ├── models/        # SQLAlchemy ORM models
│   └── utils/         # JWT, security, logging utilities
├── agents/            # LangGraph agent definitions
├── database/          # Migrations (Alembic) + seed data
├── monitoring/        # Prometheus rules + Grafana dashboards
├── mcp_servers/       # MCP server configurations
├── workers/           # Background task workers
├── tests/             # Unit + integration tests
├── scripts/           # Dev utility scripts
├── docs/              # Documentation
├── docker-compose.yml # Service orchestration
└── Makefile           # Build and lifecycle commands
```

## Observability

| Component | Endpoint | Description |
|-----------|----------|-------------|
| Prometheus metrics | `GET /metrics` | Prometheus text exposition format |
| Accept client metrics | `POST /metrics` | Receive frontend metrics |
| Health check | `GET /api/health` | Readiness probe (DB + bootstrap) |
| Liveness probe | `GET /api/live` | Liveness check |
| API docs | `GET /docs` | Swagger UI (auto-generated) |
| Grafana | `http://localhost:3001` | Pre-built dashboards |

See [`monitoring/README.md`](monitoring/README.md) for full metrics documentation.

## Testing

```bash
# Run all tests (inside Docker)
make test

# Run locally (requires dependencies)
pytest tests/unit/ -v
pytest tests/integration/ -v

# Frontend tests
cd frontend && npm test
```

## License

Private — All rights reserved.
