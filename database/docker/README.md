# Demo Seed Data

Idempotent seed script for populating the database with demo data.

## Usage

### Inside Docker

```bash
docker compose exec backend python -m database.docker.seed_demo
```

### From host (local Python)

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ai_intelligence_os \
python database/docker/seed_demo.py
```

### With explicit connection string

```bash
docker compose exec backend python -m database.docker.seed_demo \
  "postgresql+asyncpg://postgres:postgres@postgres:5432/ai_intelligence_os"
```

## What gets seeded

| Table | Count | Notes |
|-------|-------|-------|
| `sources` | 4 | Reuters, arXiv, GitHub Blog, Anthropic Research |
| `agents` | 3 | Analyst, Project Manager, Knowledge agents |
| `articles` | 3 | AI/ML topic articles with metadata |
| `knowledge_items` | 4 | Patterns, pipelines, concepts, best practices |
| `tasks` | 4 | Mix of pending/in_progress/completed with priorities |
| `intelligence_reports` | 2 | Q3 review and observability assessment |
| `agent_runs` | 3 | 2 completed, 1 failed with error message |

## Safety guarantees

- **Idempotent**: Safe to run multiple times. Only creates records that don't exist.
- **Read-only check**: Uses `SELECT ... WHERE name = ANY(...)` before inserting.
- **No overwrite**: Never updates or deletes existing records.
- **User data safe**: Only touches demo records by name/URL uniqueness; user-created data is unaffected.
