# AI Intelligence OS

Enterprise AI Intelligence Operating System — connecting Information → Knowledge → Action.

## Architecture

```
User → Frontend (Next.js) → Backend API (FastAPI) → Agent Runtime (LangGraph) → AI Agents → Knowledge Layer → External Services
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js + TypeScript + TailwindCSS + shadcn/ui |
| Backend | FastAPI + Python 3.12+ |
| Agent Framework | LangGraph |
| LLM Gateway | LiteLLM |
| Database | PostgreSQL |
| Vector DB | Qdrant |
| Cache | Redis |
| Object Storage | MinIO |
| Container Orchestration | Docker Compose |

## Quick Start

```bash
docker compose up -d
```

See [docs/development-plan.md](docs/development-plan.md) for the development roadmap.

## Structure

```
├── frontend/          # Next.js application
├── backend/           # FastAPI application
├── agents/            # LangGraph agent definitions
├── mcp_servers/       # Model Context Protocol servers
├── workers/           # Background task workers
├── database/          # Migrations & seed data
├── docker/            # Container configurations
├── tests/             # Integration & unit tests
├── monitoring/        # Observability configs
└── scripts/           # Dev & utility scripts
```

## License

Private — All rights reserved.
