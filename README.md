# AI Intelligence OS

Enterprise AI Intelligence Operating System — connecting Information → Knowledge → Action.

**Version:** 0.1.0

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
make start          # Start all services
make stop           # Stop all services
make logs           # View live logs
make test           # Run backend tests
```

See [docker/README.md](docker/README.md) for full Docker instructions.

## Environments

| Environment | Config File | Purpose |
|-------------|-------------|---------|
| Development | `.env.development.example` | Local development with hot reload |
| Test | `.env.test.example` | CI/testing with isolated data stores |
| Production | `.env.production.example` | Production deployment |

Copy the appropriate template to `.env` before starting:

```bash
cp .env.development.example .env   # or .env.test.example / .env.production.example
make start
```

Key differences:

- **Development**: debug enabled, local ports exposed, pool_min=1
- **Test**: isolated database names and Redis indices, mock LLM keys
- **Production**: debug disabled, strong passwords required, connection pooling increased

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make start` | Build and start all services (development) |
| `make stop` | Stop all services, preserve data |
| `make rebuild` | Rebuild containers without cache |
| `make clean` | Remove containers, networks, and volumes |
| `make logs` | Follow all service logs |
| `make logs-svc svc=<name>` | Follow a single service log |
| `make test` | Run backend test suite |
| `make test-unit` | Run unit tests only |
| `make test-integration` | Run integration tests only |
| `make init-db` | Run Alembic migrations |
| `make shell` | Open interactive backend shell |
| `make db-shell` | Open PostgreSQL psql session |
| `make redis-cli` | Open Redis CLI session |
| `make help` | Show all available commands |

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
