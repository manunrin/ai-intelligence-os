# Development Roadmap

**Last Updated:** 2026-07-16 (Phase 6-C)

## Completed Phases

### Phase 1 — Project Foundation
- **Goal:** Establish project structure and infrastructure
- **Scope:** Monorepo layout, Docker Compose, env templates, Makefile
- **Dependencies:** None
- **Output:** Working `make start` with all services, git repo initialized

### Phase 2-A — Infrastructure Foundation
- **Goal:** Hardened deployment configuration
- **Scope:** Docker Compose service healthchecks, versioning, Makefile commands
- **Dependencies:** Phase 1
- **Output:** Production-ready docker-compose.yml with restart policies and health checks

### Phase 2-B — Database Architecture
- **Goal:** Complete data layer with migrations
- **Scope:** 9 SQLAlchemy ORM models, Alembic setup, async session management, relationship definitions
- **Dependencies:** Phase 2-A
- **Output:** 2 Alembic migrations covering full schema with indexes and constraints

### Phase 3-A — Agent Runtime Foundation
- **Goal:** Abstract agent execution framework
- **Scope:** AgentBase, WorkflowBase, ToolBase, ToolRegistry, prompt loader
- **Dependencies:** Phase 2-B
- **Output:** Composable agent/workflow/tool system with lifecycle management

### Phase 3-B — LLM Gateway
- **Goal:** Multi-provider LLM abstraction
- **Scope:** LLMRouter with YAML config, 4 providers (OpenAI, Anthropic, Ollama, Compatible), fallback chains, health checks
- **Dependencies:** Phase 3-A
- **Output:** Provider-agnostic chat and embedding interface

### Phase 3-C — Core Agent Skeletons
- **Goal:** Three foundational agents
- **Scope:** ResearchAgent, AnalystAgent, TranslatorAgent with prompt templates
- **Dependencies:** Phase 3-B
- **Output:** Basic intelligence pipeline (research → analyze → translate)

### Phase 4-A — Data Ingestion & Scheduler
- **Goal:** Automated information collection
- **Scope:** SourceConnector base class, RSS connector (OpenAI Blog), IngestionService with dedup, APScheduler integration
- **Dependencies:** Phase 3-C
- **Output:** Scheduled daily ingestion from configurable sources

### Phase 5-F — Autonomous Intelligence Pipeline
- **Goal:** Full multi-agent autonomous workflow with MCP integration
- **Scope:** LangGraph StateGraph builders, 4 MCP servers (Notion/Asana/Browser/GitHub), KnowledgeAgent, PronunciationAgent, ProjectManagerAgent, NotificationAgent, ArticlePipeline, event system, job scheduler
- **Dependencies:** Phase 4-A, Phase 3-C
- **Output:** End-to-end autonomous pipeline: ingest → research → analyze → translate → knowledge → tasks → notification

### Phase 6-A — API Foundation Layer
- **Goal:** RESTful API with layered architecture
- **Scope:** Router → Service → Repository pattern, 5 read endpoints, pagination, Pydantic response schemas, APIResponse envelope, centralized exception handling, OpenAPI metadata
- **Dependencies:** Phase 5-F
- **Output:** `/api/v1/*` endpoints for articles, knowledge, tasks, agents, reports

### Phase 6-A.1 — Architecture Review Fixes
- **Goal:** Fix database model issues discovered in review
- **Scope:** _utcnow import fixes, generic type corrections, relationship foreign_key disambiguation
- **Dependencies:** Phase 6-A
- **output:** Clean model relationships, passing type checks

### Phase 6-B — Service Wiring
- **Goal:** Connect stub services to real repository data
- **Scope:** Business services delegate to repositories, real data flows through to API responses
- **Dependencies:** Phase 6-A.1
- **Output:** API returns actual database content

### Phase 6-C — Dashboard Integration
- **Goal:** Frontend connected to backend APIs
- **Scope:** Dashboard page with tabs, concurrent data fetching, unwrap() helper, CORS middleware, DataTable/Card rendering, error handling
- **Dependencies:** Phase 6-B
- **Output:** Functional dashboard showing live data from all 5 endpoints

## Upcoming Phases

### Phase 6-D — Write Operations & Authentication

**Goal:** Enable data mutation and user management.

**Completed — Phase 6-D.1 (Backend Write Operations):**
- POST/PUT/DELETE endpoints for articles, tasks, knowledge items
- POST/GET endpoints for reports
- POST `/agents/{id}/run` endpoint
- Pydantic v2 input schemas with validation
- Full Router → Service → Repository layering
- 85 new unit tests (203 total)

**Completed — Phase 6-D.2 (Authentication & Authorization):**
- User model with bcrypt password hashing
- JWT access token generation and verification (HS256)
- User registration and login endpoints
- `get_current_user` FastAPI dependency for all write endpoints
- Role check foundation (`require_role` dependency factory)
- Alembic migration for users table
- All write endpoints protected behind authentication

**Remaining:**
- Refresh token endpoint (deferred to later phase)
- Full RBAC middleware (admin/user roles defined but not enforced beyond basic check)
- Frontend auth UI (login form, token storage, auto-attach headers)
- Password reset flow

**Dependencies:** Phase 6-C
**Expected Output:** Full CRUD API with authenticated frontend

### Phase 7 — Observability & Production Readiness

**Goal:** Production-grade monitoring and deployment.

**Scope:**
- OpenTelemetry tracing across all layers
- Prometheus metrics endpoint
- Grafana dashboards
- Structured logging (JSON format)
- Kubernetes manifests or Helm charts
- CI/CD pipeline (GitHub Actions)
- Staging environment
- Load testing

**Dependencies:** Phase 6-D
**Expected Output:** Production-deployable system with full observability

### Phase 8 — Testing & Quality

**Goal:** Comprehensive test coverage and quality gates.

**Scope:**
- Unit test coverage >80%
- Integration test suite expansion
- E2E tests with Playwright
- Performance benchmarks
- Security audit (OWASP Top 10)
- Code quality gates (ruff, mypy strict mode)

**Dependencies:** Phase 6-D
**Expected Output:** Test-covered codebase ready for production deployment

### Phase 9 — Knowledge Layer Enhancement

**Goal:** Advanced knowledge management capabilities.

**Scope:**
- Vector search integration (Qdrant)
- RAG pipeline (question answering over knowledge base)
- Knowledge graph construction
- Cross-reference and relationship mapping
- Hybrid search (BM25 + vector fusion)
- Embedding caching
- Re-ranking with cross-encoder models

**Dependencies:** Phase 6-C, Phase 7
**Expected Output:** Semantic search and question-answering over collected knowledge

### Phase 10 — External Integrations

**Goal:** Expand data sources and output channels.

**Scope:**
- Additional connectors (Twitter/X, LinkedIn, arXiv, Hacker News)
- WeChat notification channel
- Telegram notification channel
- Email delivery (SMTP/SES)
- Notion/Asana bidirectional sync
- GitHub issue auto-creation from tasks

**Dependencies:** Phase 6-C
**Expected Output:** Multi-source, multi-channel intelligence distribution
