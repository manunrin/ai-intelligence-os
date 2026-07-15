# Ingestion Architecture

## Data Flow

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────────┐
│  External   │────▶│  Connector   │────▶│  RawArticle  │────▶│  Ingestion  │
│  Sources    │     │  (fetch)     │     │  (normalize) │     │  Service    │
│             │     │              │     │              │     │             │
│ OpenAI Blog │     │ RSS          │     │ deduplicate  │     │ ── save ──▶ │
│ GitHub API  │────▶│ REST API     │     │ hash check   │     │   PostgreSQL│
│ RSS Feeds   │     │ HTTP GET     │     │              │     │             │
│ ...         │     │ ...          │     │ ...          │     │             │
└─────────────┘     └──────────────┘     └──────────────┘     └──────┬──────┘
                                                                      │
                                                                      ▼
                                                               ┌─────────────┐
                                                               │  Article    │
                                                               │  (ORM)      │
                                                               └─────────────┘
```

## Components

### SourceConnector (abstract)

Base class defining the ingestion contract:

```python
class SourceConnector(ABC):
    async def fetch() -> Any        # Retrieve raw data
    async def parse(raw) -> list   # Parse into items
    def normalize(item) -> RawArticle  # Standardize
    async def run() -> list        # Full pipeline
```

Each connector implements `fetch()` + `normalize()` at minimum. `parse()` defaults to identity.

### RawArticle

Standardized data structure that flows between all stages:

```python
@dataclass
class RawArticle:
    title: str
    url: str
    summary: str = ""
    content: str = ""
    language: str = "en"
    published_at: datetime | None = None
    author: str | None = None
    tags: list[str] = []
    metadata_: dict = {}
```

### IngestionService

Orchestrates the full pipeline:

1. **Fetch** — calls `connector.run()` → list of `RawArticle`
2. **Deduplicate** — SHA-256 hash of URL checked against existing articles
3. **Persist** — writes to `articles` table via SQLAlchemy ORM

Returns stats: `{"fetched": N, "deduplicated": N, "saved": N}`

### Scheduler

Uses APScheduler to run ingestion jobs on cron schedules:

```python
scheduler = JobScheduler()
scheduler.add_daily_news_job(
    connector=OpenAIBlogRssConnector(),
    cron_expression="0 8 * * *",  # 8:00 AM daily
    job_id="daily_openai_news",
)
scheduler.start()
```

## Connector Registry

| Connector | Kind | Status |
|-----------|------|--------|
| OpenAIBlogRssConnector | RSS | Implemented |
| *(future)* | API | Skeleton ready |
| *(future)* | Crawler | Not implemented |

## Not Implemented

- MCP integration
- Notion / Asana connectors
- WeChat / Telegram notifications
- Frontend UI
- Real LLM connections
