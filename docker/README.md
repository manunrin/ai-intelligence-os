# AI Intelligence OS — Docker Infrastructure

## Architecture

```
                    ┌─────────────┐
                    │   Frontend  │  :3000
                    │  (Next.js)  │
                    └──────┬──────┘
                           │ HTTP
                    ┌──────▼──────┐
                    │   Backend   │  :8000
                    │  (FastAPI)  │
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
   ┌──────▼──────┐  ┌─────▼─────┐  ┌──────▼──────┐
   │   PostgreSQL│  │   Redis   │  │   Qdrant    │
   │   :5432     │  │   :6379   │  │   :6333     │
   └─────────────┘  └───────────┘  └─────────────┘
          │
   ┌──────▼──────┐
   │    MinIO    │  :9000 / :9001
   │ Object Store│
   └─────────────┘
```

All services share the `ai-intelligence-net` bridge network. External ports are configurable via `.env`.

## Quick Start

### Start All Services

```bash
./scripts/start.sh
```

Or manually:

```bash
docker compose up -d --build
```

### Start Individual Services

```bash
docker compose up -d postgres redis qdrant minio   # infrastructure only
docker compose up -d backend                        # backend + its dependencies
docker compose up -d frontend                       # frontend + backend
```

## Stop & Cleanup

### Stop All Services (keep data)

```bash
./scripts/stop.sh
```

Or:

```bash
docker compose stop
```

### Remove All Containers & Volumes (destructive)

```bash
docker compose down -v
```

**Warning:** This deletes all persisted data.

## Logs

### Follow All Service Logs

```bash
./scripts/logs.sh
```

### Follow a Specific Service

```bash
docker compose logs -f backend
docker compose logs -f postgres
```

### Last 50 Lines of a Service

```bash
docker compose logs --tail=50 backend
```

## Port Reference

| Service     | Container Port | Host Port (env var)       | Purpose            |
|-------------|---------------|---------------------------|--------------------|
| Frontend    | 3000          | 3000 (`FRONTEND_PORT`)    | Next.js dev server |
| Backend     | 8000          | 8000 (`BACKEND_PORT`)     | FastAPI REST API   |
| PostgreSQL  | 5432          | 5432 (`POSTGRES_PORT`)    | Relational database|
| Redis       | 6379          | 6379 (`REDIS_PORT`)       | Cache / message broker |
| Qdrant      | 6333/6334     | 6333/6334 (`QDRANT_PORT`) | Vector search      |
| MinIO API   | 9000          | 9000 (`MINIO_PORT`)       | Object storage     |
| MinIO Console| 9001         | 9001 (`MINIO_CONSOLE_PORT`) | Web UI           |

## Health Checks

Every service has an automated healthcheck. Status:

```bash
docker compose ps
```

Healthy output example:
```
NAME          STATUS
aio-frontend  healthy
aio-backend   healthy
aio-postgres  healthy
aio-redis     healthy
aio-qdrant    healthy
aio-minio     healthy
```

## Environment Variables

All variables are documented in `.env.example`. Copy and customize:

```bash
cp .env.example .env
# Edit .env with your preferred values
```

Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | `postgres` | Database superuser |
| `POSTGRES_PASSWORD` | `postgres` | Database password |
| `POSTGRES_DB` | `ai_intelligence_os` | Database name |
| `REDIS_PASSWORD` | `redispassword` | Redis auth password |
| `MINIO_ACCESS_KEY` | `minioadmin` | MinIO access key |
| `MINIO_SECRET_KEY` | `minioadmin` | MinIO secret key |
| `QDRANT_API_KEY` | _(none)_ | Qdrant API key (optional) |

## Data Persistence

All service data is stored in named Docker volumes:

| Volume | Service | Contents |
|--------|---------|----------|
| `postgres_data` | PostgreSQL | WAL, tables, indexes |
| `redis_data` | Redis | AOF persistence |
| `qdrant_data` | Qdrant | Collections, points |
| `minio_data` | MinIO | Uploaded objects |

Backup volumes:

```bash
docker run --rm -v aio_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
```

## Troubleshooting

### Service won't become healthy

```bash
# Check service logs
docker compose logs backend

# Restart a single service
docker compose restart backend

# Rebuild without cache
docker compose build --no-cache backend
```

### Reset all data

```bash
docker compose down -v
docker compose up -d
```

### Connect to a running service

```bash
docker compose exec postgres psql -U postgres -d ai_intelligence_os
docker compose exec redis redis-cli
docker compose exec qdrant curl http://localhost:6333/
```
