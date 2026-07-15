# Database Schema — AI Intelligence OS

## Entity Relationship Diagram

```
┌──────────┐       1   *  ┌──────────┐       *   1  ┌─────────────┐
│  Source   │─────────────▶│ Article  │◀────────────│ AgentRun    │
└──────────┘              └──────────┘              └──────┬──────┘
      │                       │                            │
      │                       │        *   *  1            │
      │                       ▼   ┌──────────┐            │
      │              ┌──────────┐ │  Report  │◀────────────┘
      │              │Knowledge│ └──────────┘
      │              │  Item   │
      │              └──────────┘
      │                   │
      │        *    1   * │          1   *  ┌──────────┐
      └───────────────────┴────────────────▶│  Task    │
                                            └──────────┘
                                                        │
                                                 *    │    1
                                              ┌────────▼────────┐
                                              │ UserPreference  │
                                              └─────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                        Workflow                            │
│  contains → AgentRun(s) → executed by → Agent(s)           │
└─────────────────────────────────────────────────────────────┘
```

## Table Definitions

### sources

Information ingestion origins (RSS feeds, blog URLs, GitHub repos, etc.)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, gen4 | Unique identifier |
| name | VARCHAR(255) | NOT NULL | Human-readable source name |
| url | TEXT | NOT NULL, UNIQUE | Source endpoint or feed URL |
| kind | VARCHAR(32) | NOT NULL | rss \| blog \| github \| api \| web |
| enabled | BOOLEAN | DEFAULT true | Whether this source is active |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Creation timestamp |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | Last modification timestamp |

**Indexes:** `idx_sources_kind` on `(kind)`

---

### articles

Raw intelligence items collected from sources.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, gen4 | Unique identifier |
| title | VARCHAR(500) | NOT NULL | Article headline |
| summary | TEXT | | Auto-generated brief summary |
| content | TEXT | | Full extracted content |
| source_id | UUID | FK→sources.id | Origin of this article |
| language | VARCHAR(8) | DEFAULT 'en' | ISO 639-1 language code |
| published_at | TIMESTAMPTZ | | Original publication time |
| fetched_at | TIMESTAMPTZ | DEFAULT NOW() | When collected by system |
| status | VARCHAR(16) | DEFAULT 'raw' | raw \| analyzed \| translated \| archived |
| metadata_ | JSONB | DEFAULT '{}' | Source-specific extra data |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Row creation time |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | Last modification time |

**Indexes:** `idx_articles_source`, `idx_articles_status`, `idx_articles_language`, `idx_articles_published` on `(published_at DESC)`

---

### intelligence_reports

Aggregated analysis output from the Analyst Agent pipeline.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, gen4 | Unique identifier |
| title | VARCHAR(500) | NOT NULL | Report headline |
| body | TEXT | NOT NULL | Full report content |
| category | VARCHAR(64) | | Technology \| Business \| Trend \| Security |
| importance_score | FLOAT | CHECK ≥ 0 AND ≤ 10 | Analyst-assigned score |
| article_ids | UUID[] | | Related articles |
| agent_run_id | UUID | FK→agent_runs.id | Source agent run |
| generated_by | VARCHAR(64) | | Agent name that produced it |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Generation timestamp |

**Indexes:** `idx_reports_category`, `idx_reports_importance` on `(importance_score DESC)`

---

### knowledge_items

Persisted knowledge entries with vector embeddings for semantic search.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, gen4 | Unique identifier |
| title | VARCHAR(500) | NOT NULL | Knowledge entry title |
| content | TEXT | NOT NULL | Full knowledge body |
| kind | VARCHAR(32) | NOT NULL | article \| report \| note \| translation |
| source_id | UUID | FK→sources.id | Originating source |
| article_id | UUID | FK→articles.id | Associated article (nullable) |
| report_id | UUID | FK→intelligence_reports.id | Associated report (nullable) |
| tags | VARCHAR(128)[] | DEFAULT '{}' | Classification tags |
| embedding | VECTOR(1536) | | Qdrant vector reference |
| external_url | TEXT | | Link to Notion page or external resource |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Creation timestamp |

**Indexes:** `idx_knowledge_kind`, `idx_knowledge_article`, `idx_knowledge_source`, `idx_knowledge_tags` on `(tags)` using GIN

---

### tasks

Actionable items created by the Project Manager Agent.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, gen4 | Unique identifier |
| title | VARCHAR(500) | NOT NULL | Task title |
| description | TEXT | | Task details and context |
| status | VARCHAR(16) | DEFAULT 'pending' | pending \| in_progress \| blocked \| done \| cancelled |
| priority | VARCHAR(8) | DEFAULT 'medium' | low \| medium \| high \| critical |
| external_id | VARCHAR(128) | | Asana task ID |
| external_url | TEXT | | Link to external task board |
| agent_run_id | UUID | FK→agent_runs.id | Source agent run |
| knowledge_item_id | UUID | FK→knowledge_items.id | Associated knowledge |
| due_date | DATE | | Target completion date |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Creation timestamp |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | Last modification time |

**Indexes:** `idx_tasks_status`, `idx_tasks_priority`, `idx_tasks_agent_run`

---

### agents

Registered AI agent definitions within the LangGraph runtime.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, gen4 | Unique identifier |
| name | VARCHAR(64) | NOT NULL, UNIQUE | Agent identifier (e.g. research, analyst) |
| display_name | VARCHAR(128) | NOT NULL | Human-readable name |
| description | TEXT | | Agent capabilities and purpose |
| graph_def | JSONB | NOT NULL | LangGraph serialized graph definition |
| version | VARCHAR(16) | DEFAULT '1.0.0' | Agent graph schema version |
| enabled | BOOLEAN | DEFAULT true | Whether this agent can be invoked |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Registration time |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | Last modification time |

**Indexes:** `idx_agents_enabled` on `(enabled)` where enabled = true

---

### agent_runs

Individual execution instances of agents.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, gen4 | Unique identifier |
| agent_id | UUID | FK→agents.id | Agent that was executed |
| workflow_id | UUID | FK→workflows.id | Parent workflow (nullable) |
| status | VARCHAR(16) | DEFAULT 'running' | running \| completed \| failed \| interrupted |
| input_payload | JSONB | DEFAULT '{}' | Initial state passed to the agent |
| output_payload | JSONB | | Final state after execution |
| error_message | TEXT | | Error details if failed |
| started_at | TIMESTAMPTZ | DEFAULT NOW() | Execution start time |
| finished_at | TIMESTAMPTZ | | Execution end time |
| duration_ms | BIGINT | | Computed duration |

**Indexes:** `idx_runs_agent`, `idx_runs_workflow`, `idx_runs_status`, `idx_runs_started` on `(started_at DESC)`

---

### workflows

Top-level workflow definitions orchestrating multi-agent pipelines.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, gen4 | Unique identifier |
| name | VARCHAR(128) | NOT NULL | Workflow identifier |
| description | TEXT | | Human-readable description |
| schedule_cron | VARCHAR(64) | | Cron expression for scheduling |
| graph_def | JSONB | NOT NULL | Serialized LangGraph workflow |
| version | VARCHAR(16) | DEFAULT '1.0.0' | Workflow schema version |
| enabled | BOOLEAN | DEFAULT true | Whether this workflow is active |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Creation time |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | Last modification time |

**Indexes:** `idx_workflows_enabled` on `(enabled)` where enabled = true

---

### user_preferences

User configuration and personalization settings.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, gen4 | Unique identifier |
| user_id | VARCHAR(128) | NOT NULL | External user identifier |
| key | VARCHAR(64) | NOT NULL | Setting key (e.g. default_language) |
| value | JSONB | NOT NULL | Setting value |
| scope | VARCHAR(16) | DEFAULT 'user' | user \| global |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | Last modification time |

**Indexes:** `idx_prefs_user_key` on `(user_id, key)` UNIQUE

---

## Data Relationships

```
Source 1──* Article *──1 IntelligenceReport
                  │
                  ├──* KnowledgeItem
                  │
                  └──1 Task

Agent 1──* AgentRun *──1 Workflow
              │
              ├──* IntelligenceReport
              │
              └──* Task

KnowledgeItem has optional links to: Source, Article, IntelligenceReport
Task has optional link to: KnowledgeItem, AgentRun
UserPreference is standalone keyed by user_id + key
```

## Design Decisions

1. **UUID primary keys** — distributed-safe, no sequential ID leakage
2. **JSONB for payloads** — flexible agent state without schema migrations
3. **TIMESTAMPTZ everywhere** — timezone-aware timestamps for global operation
4. **Soft deletes via status fields** — agent runs and articles retain history
5. **Array columns for tags/IDs** — PostgreSQL-native, avoids join tables for simple collections
