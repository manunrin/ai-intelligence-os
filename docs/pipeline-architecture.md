# Pipeline Architecture

## Event-Driven Overview

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  Source       │────▶│  Ingestion      │────▶│  ArticleCreated  │
│  Connector    │     │  Service        │     │  Event           │
│              │     │                 │     │                  │
│ RSS / API    │     │ fetch → dedup   │     │ publish ────────▶│
│              │     │ → save          │     │                  │
└──────────────┘     └────────┬────────┘     └────────┬─────────┘
                              │                       │
                              ▼                       ▼
                     ┌───────────────┐     ┌──────────────────┐
                     │  Article      │     │  Pipeline          │
                     │  (articles)   │     │  Subscriber        │
                     └───────┬───────┘     └────────┬─────────┘
                             │                      │
                             ▼                      ▼
                    ┌──────────────────┐   ┌──────────────────┐
                    │  ArticlePipeline │   │  KnowledgeItem   │
                    │  (LangGraph)     │──▶│  (knowledge)     │
                    │                  │   │                  │
                    │ Research Agent   │   │ kind=article     │
                    │ Analyst Agent    │   │ kind=report      │
                    │ Translator Agent │   │ kind=translation │
                    └──────────────────┘   └──────────────────┘
```

## Components

### Event System (`backend/events/`)

Async event publisher with subscriber registry for decoupled communication between pipeline stages.

**ArticleCreatedEvent** — Published when a new article is saved via `IngestionService`.

```python
event = ArticleCreatedEvent(
    article_id=uuid,
    title="OpenAI Announces...",
    url="https://openai.com/blog/...",
    language="en",
    tags=["ai", "research"],
)
await publisher.publish(event)
```

**EventPublisher** — Manages subscriber callbacks per event type.

```python
publisher = EventPublisher()
publisher.subscribe(ArticleCreatedEvent, on_article_created)
await publisher.publish(event)
```

### IngestionService Extension

`IngestionService` now accepts an optional `event_publisher` parameter. When articles are saved and flushed to the database, an `ArticleCreatedEvent` is published for each new article.

```python
ingestion = IngestionService(session, event_publisher=publisher)
result = await ingestion.ingest(connector)
```

### ArticlePipeline (`backend/pipelines/`)

Orchestrates the full intelligence lifecycle for a single article:

1. **Load** — Fetches Article from DB by ID
2. **AgentRun** — Creates execution record with input payload
3. **Build Graph** — Constructs LangGraph StateGraph with Research/Analyst/Translator agents
4. **Execute** — Runs research → analyze → translate pipeline
5. **Persist** — Saves each stage output as a KnowledgeItem
6. **Update** — Sets article status ("raw" → "analyzed" → "translated")

```python
pipeline = ArticlePipeline(session)
result = await pipeline.run(article_id)
# Returns: {"article_id": "...", "knowledge_ids": [...], "errors": [], "final_status": "translated"}
```

### KnowledgeService (`backend/services/knowledge/`)

Manages KnowledgeItem creation and retrieval. Provides typed helpers for different knowledge types:

- `create()` — Generic knowledge item creation
- `create_from_analysis()` — Wraps AnalystAgent output into a report-type KnowledgeItem
- `create_from_translation()` — Wraps TranslatorAgent output into a translation-type KnowledgeItem

### DailyIntelligenceJob (`backend/workers/jobs/`)

Top-level worker that orchestrates the full daily cycle across all configured sources:

```
Phase 1: Ingestion
  For each connector:
    IngestionService.fetch() → deduplicate → save → publish events

Phase 2: Intelligence
  For each raw/analyzed article:
    ArticlePipeline.run(article_id) → research → analyze → translate → knowledge

Phase 3: Commit
  Flush all changes, update statuses
```

```python
job = DailyIntelligenceJob(session, event_publisher=publisher)
result = await job.run(connectors=[openai_rss, github_rss])
# Returns: {"articles_fetched": N, "articles_saved": N,
#           "articles_processed": N, "knowledge_items": N}
```

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Daily Intelligence Job                        │
│                                                                  │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │ Connectors  │───▶│ Ingestion    │───▶│ ArticleCreated   │   │
│  │             │    │ Service      │    │ Event            │   │
│  │ OpenAI Blog │    │              │    │                  │   │
│  │ GitHub API  │    │ fetch→dedup  │    │ ──► Pipeline     │   │
│  │ RSS Feeds   │    │ → save       │    │ ──► Knowledge    │   │
│  └─────────────┘    └──────────────┘    └──────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              ArticlePipeline (per article)               │   │
│  │                                                          │   │
│  │  Load Article ──▶ Create AgentRun ──▶ Compile Graph      │   │
│  │                                              │           │   │
│  │  START ──▶ research_node ──▶ analyst_node ──▶ translator │   │
│  │                            │         │              │   │   │
│  │                            ▼         ▼              ▼   │   │
│  │                      Knowledge     Knowledge    Knowledge│   │
│  │                      (article)     (report)      (trans) │   │
│  │                                                          │   │
│  │  Update Article.status → "translated"                    │   │
│  │  Complete AgentRun                                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Commit all changes                                              │
└─────────────────────────────────────────────────────────────────┘
```

## Execution Flow

### Manual Invocation

```python
async with get_session() as session:
    publisher = EventPublisher()
    connectors = [OpenAIBlogRssConnector()]

    # Phase 1: Ingest
    ingestion = IngestionService(session, event_publisher=publisher)
    stats = await ingestion.ingest(connectors[0])

    # Phase 2: Process each new article
    pipeline = ArticlePipeline(session)
    result = await pipeline.run(article_id)
```

### Scheduled Execution

```python
scheduler = JobScheduler()
scheduler.add_daily_news_job(
    connectors=[OpenAIBlogRssConnector()],
    cron_expression="0 8 * * *",
    job_id="daily_intelligence",
)
scheduler.start()
```

## Error Handling

- **Node failures**: Caught within node wrappers, recorded in `state.errors`, pipeline continues
- **AgentRun failures**: Status set to "failed", error message stored, article status remains "raw"
- **Pipeline exceptions**: Logged with full traceback, agent run marked failed, article untouched
- **Event handler failures**: Logged and suppressed — never block the main pipeline

## State Transitions

```
Article:  raw ──▶ analyzed ──▶ translated
AgentRun: running ──▶ completed | failed
```

## Not Implemented

- MCP integration
- Notion / Asana connectors
- WeChat / Telegram notifications
- Frontend UI
- Real LLM connections
- Async event dispatch (currently synchronous)
- Dead letter queue for failed events
- Retry logic for pipeline failures
