# CHANGELOG

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to Semantic Versioning.

## [Unreleased] — Phase 6-D.1: Backend Write Operations

### Date
2026-07-16

### Commit
`auto`

### Added
- **Article write operations**: POST `/api/v1/articles`, GET `/api/v1/articles/{id}`, PUT `/api/v1/articles/{id}`, DELETE `/api/v1/articles/{id}`
- **Task write operations**: POST `/api/v1/tasks`, GET `/api/v1/tasks/{id}`, PUT `/api/v1/tasks/{id}`, DELETE `/api/v1/tasks/{id}`
- **Knowledge item write operations**: POST `/api/v1/knowledge`, GET `/api/v1/knowledge/{id}`, PUT `/api/v1/knowledge/{id}`, DELETE `/api/v1/knowledge/{id}`
- **Report write operations**: POST `/api/v1/reports`, GET `/api/v1/reports/{id}`
- **Agent run trigger**: POST `/api/v1/agents/{agent_id}/run` to start agent workflow execution
- **Pydantic v2 input schemas**: `ArticleCreate/Update`, `TaskCreate/Update`, `KnowledgeItemCreate/Update`, `ReportCreate/Update` with field validation, min/max length constraints
- **Service write methods**: `create_*`, `update_*`, `delete_*`, `get_*` on all business services
- **Repository base methods**: `create()`, `update()`, `delete()`, `get_by_id()` available via `BaseRepository`
- **Unit tests**: Repository layer (12 tests), Service layer (38 tests), Router layer (35 tests) = 85 new tests
- `tests/conftest.py`: pytest-asyncio fixture for async test support

### Changed
- `ArticleService`: added get, create, update, delete methods
- `TaskService`: added get, create, update, delete methods
- `KnowledgeService`: added get, create, update, delete methods
- `ReportService`: added get, create, update methods
- `AgentService`: added `run_agent()` method to trigger agent workflows
- All routers extended with write endpoints following Router → Service → Repository pattern
- Fixed deprecated `max_items` in knowledge schema (replaced with Pydantic v2 default behavior)

### Test Results
- **203 total unit tests** (108 existing + 95 new)
- All existing tests continue passing
- New coverage: repository CRUD, service business logic, router HTTP endpoints, validation errors, 404 handling

---
