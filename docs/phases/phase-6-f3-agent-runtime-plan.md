# Phase 6-F.3 — Agent Runtime Design Plan

**Date:** 2026-07-17
**Status:** Draft — awaiting approval
**Preceded by:** Phase 6-F.2 (write operations UI), Phase 6-F.2 prep (React Query migration)

---

## Executive Summary

Phase 6-F.3 implements **Agent Runtime**: real-time monitoring, on-demand execution, and observability for the LangGraph-based agent pipeline. Currently, agents execute only through scheduled/background jobs (`AutonomousIntelligenceJob`) with no way to trigger them on demand or observe their progress. The `POST /agents/{id}/run` endpoint is a no-op that creates a "phantom" run record without executing anything.

This plan bridges that gap by:
1. Wiring the API endpoint to actually invoke LangGraph pipelines via the existing `AgentService` infrastructure
2. Adding streaming status updates via Server-Sent Events
3. Extending the database schema with per-stage progress tracking
4. Building a frontend Agent Monitor tab

### Guiding Principle

**AgentRuntimeService does NOT create a second execution system.** It orchestrates execution, lifecycle tracking, callbacks, and persistence — delegating actual agent work to the existing `AgentService`, LangGraph pipelines, MCP registry, and workflow infrastructure. The execution abstraction is async-worker-ready from day one so it can later be replaced by RQ/Celery/worker queue without API changes.

---

## 1. Current AgentRun Model Limitations

### Existing Schema (`backend/database/models/agent_run.py`)

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | |
| `agent_id` | FK → agents | Synthetic UUID in ArticlePipeline (orphaned FKs) |
| `workflow_id` | FK → workflows, nullable | Never populated |
| `status` | String, max 16 chars | Only `"running"`, `"completed"`, `"failed"` |
| `input_payload` | JSONB | Stores trigger context |
| `output_payload` | JSONB | Stores final result |
| `error_message` | TEXT, nullable | Only set on full failure |
| `started_at` | DateTime | |
| `finished_at` | DateTime, nullable | Set only on completion/failure |
| `duration_ms` | Integer, nullable | **Never computed** |
| `user_id` | FK → users, indexed | |

### Critical Gaps

1. **No per-stage progress**: Cannot tell which LangGraph node is executing (research, analyst, translator, etc.)
2. **No intermediate state**: Pipeline outputs are lost if the process crashes mid-execution
3. **`duration_ms` dead column**: Exists in schema but never populated
4. **`get_run()` stub**: Returns `None` — no API to fetch a single run by ID
5. **No concurrency control**: No lock, retry count, or max attempts
6. **No cancellation**: No mechanism to abort a running pipeline
7. **Status enum too short**: 16-char limit constrains future state values like `"stage_research"`, `"stage_translating"`

### Decision: Extend vs Replace

We extend `AgentRun` rather than creating a new model. The existing fields serve as the execution envelope; we add staging via a separate table to keep the main table lean.

---

## 2. Execution Architecture — No Second Execution System

### Relationship to Existing Infrastructure

```
┌──────────────────────────────────────────────────────┐
│  AgentRuntimeService (orchestration layer)            │
│  - Creates AgentRun records                           │
│  - Dispatches to pipeline factory                     │
│  - Manages lifecycle transitions                      │
│  - Collects callback events                           │
│  - Persists results                                   │
└──────────┬─────────────────────────────┬──────────────┘
           │ delegates to                │ delegates to
           ▼                             ▼
┌─────────────────────┐    ┌──────────────────────────┐
│  AgentService        │    │  LangGraph Pipelines      │
│  (existing CRUD)     │    │  (existing, unchanged)    │
│  - list_agent_runs   │    │  - build_intelligence_graph│
│  - run_agent stub    │    │  - compile_autonomous_*   │
│  - audit logging     │    │                           │
└──────────────────────┘    └──────────────────────────┘
                                      │
                                      ▼
                          ┌──────────────────────┐
                          │  MCP Registry         │
                          │  Tool Registry        │
                          │  LLM Client/Router    │
                          └──────────────────────┘
```

**What AgentRuntimeService does NOT do:**
- Does NOT reimplement agent execution logic
- Does NOT create its own MCP tool invocations
- Does NOT build or compile LangGraph graphs
- Does NOT manage LLM routing

**What AgentRuntimeService DOES do:**
- Orchestrates: creates run record → dispatches → tracks → persists result
- Wraps existing pipeline factories with runtime callbacks
- Manages lifecycle state transitions
- Provides cancellation coordination
- Exposes streaming/SSE interface

### Current Flow (Background Jobs Only)

```
AutonomousIntelligenceJob.run()
  ├─ Phase 1: IngestionService.ingest(connector) → Article[]
  ├─ Phase 2: ArticlePipeline.run(article_id)
  │     ├─ Create AgentRun (synthetic UUID)
  │     ├─ Build StateGraph(research→analyst→translator)
  │     └─ graph.invoke(initial_state) → synchronous, blocking
  └─ Phase 3: compile_autonomous_intelligence().invoke(state)
        ├─ Build StateGraph(6 nodes with MCP agents)
        └─ app.invoke(initial_state) → synchronous, blocking
```

### Target Flow (Async-Worker-Ready)

```
POST /api/v1/agents/run              ← API entry point
  └─ AgentRuntimeService.submit(agent_type, input_payload, user_id)
       ├─ Create AgentRun (status="running", stage="initializing")
       ├─ Get pipeline factory by agent type (see §3)
       ├─ Dispatch via Executor interface:
       │    ├─ Sync: executor.execute(run_id, factory, state)
       │    └─ Async: executor.enqueue(run_id, factory, state)  ← RQ/Celery-ready
       └─ Return AgentRun ID immediately

Executor (background thread / worker)
  ├─ Wrap pipeline with AgentRuntimeCallback
  ├─ Stream stage updates → AgentStageProgress table
  ├─ On completion → update AgentRun.status = "completed"
  └─ On failure → update AgentRun.status = "failed"

SSE Endpoint
  GET /api/v1/agents/runs/{id}/stream
  └─ Yield Event objects (see §7)
```

### Key Design Decisions

- **Keep LangGraph as-is**: No rewrite of graphs/nodes. The runtime layer wraps invocation.
- **Async-worker-ready interface**: `Executor` protocol defined now; sync implementation used in F.3, swappable for RQ/Celery later.
- **No LLM-driven tool calling yet**: Agents still use hardcoded MCP tool selection. This phase adds the runtime/monitoring layer, not autonomous tool selection.

---

## 3. Pipeline Selection Strategy

### Constraint: No Name-String Matching

Pipeline selection must NOT rely solely on agent name string matching. We use this priority order:

1. **`agent.graph_def` configuration** — each agent record stores which graph definition to use (e.g., `"intelligence"`, `"autonomous"`)
2. **`agent.type` field** — if an explicit type discriminator exists on the agent model
3. **Explicit mapping table** — a small, typed `PIPELINE_MAP` dict in code:

```python
PIPELINE_MAP: dict[str, PipelineFactory] = {
    "intelligence": build_intelligence_graph,
    "autonomous": compile_autonomous_intelligence,
}
```

4. **Fallback: name matching** — only as compatibility behavior for legacy agents without graph_def or type

### Pipeline Factory Protocol

```python
PipelineFactory = Callable[[], CompiledGraph]
"""Returns a compiled LangGraph application ready for .invoke()/.stream()"""
```

The runtime service receives a `PipelineFactory`, not a raw graph builder. This decouples the runtime from graph compilation details.

---

## 4. LangGraph Integration Point

### Current Node Wrappers

Nodes in `workflows/graph/nodes.py` and `autonomous_nodes.py` already wrap agents with try/catch error handling. They write results into the shared state dict.

### Required Change: Stage Callbacks

LangGraph supports **callbacks** via `on_chain_start`, `on_chain_end`, `on_chain_error`. We use these to emit stage progress events:

```python
from langgraph.callbacks import BaseCallbackHandler

class AgentRuntimeCallback(BaseCallbackHandler):
    def __init__(self, run_id: uuid.UUID, session_factory):
        self.run_id = run_id
        self._session_factory = session_factory

    async def on_chain_start(self, serialized, inputs, *, run_id):
        node_name = serialized.get("name", "unknown")
        await self._update_stage(self.run_id, f"stage_{node_name}", "executing")

    async def on_chain_end(self, outputs, *, run_id):
        node_name = serialized.get("name", "unknown")
        await self._update_stage(self.run_id, f"stage_{node_name}", "completed", outputs)

    async def on_chain_error(self, error, *, run_id):
        await self._fail_agent_run(self.run_id, str(error))
```

### Graph Compilation

We create **compiled graph factories** that inject the callback handler:

```python
def make_pipeline_factory(base_factory: PipelineFactory, run_id: uuid.UUID, session_factory):
    """Wrap any existing pipeline factory with runtime observability."""
    def factory() -> CompiledGraph:
        graph = base_factory()
        # Inject callback before compile
        return graph
    return factory
```

### No Graph Rewrite Needed

The existing graphs (`build_intelligence_graph`, `compile_autonomous_intelligence`, etc.) remain unchanged. The runtime layer only adds the callback handler at compile time.

---

## 5. MCP Tool Invocation Flow

### Current State

MCP tools are invoked directly by agents inside `_execute_impl`:

```python
# ResearchAgent._execute_impl
tool = self.mcp_registry.get_tool("browser.search")
result = await tool.execute({"query": topic})
```

Tools check for env vars and fall back to stub responses. All 4 MCP servers (Notion, Asana, Browser, GitHub) are registered at bootstrap in `ApplicationBootstrap`.

### Changes for Agent Runtime

**No changes to MCP tool implementations.** The runtime layer observes tool calls via the callback handler's `on_tool_start`/`on_tool_end` hooks, logging them to `AgentStageProgress` without modifying the call path.

```json
{
  "run_id": "...",
  "stage": "research",
  "tool_call": {"server": "browser", "tool": "search", "args": {"query": "..."}},
  "status": "completed",
  "duration_ms": 2340
}
```

This gives visibility into which external tools were called during each stage without changing how agents work.

---

## 6. Async Execution Abstraction (Worker-Ready Interface)

### Executor Protocol

```python
class Executor(Protocol):
    """Abstracts how agent runs are dispatched.

    Implementations:
    - SyncExecutor: runs in-thread via asyncio (F.3 default)
    - RQExecutor: enqueues job to RQ queue (future)
    - CeleryExecutor: enqueues task to Celery (future)
    """
    async def execute(self, run_id: uuid.UUID, factory: PipelineFactory,
                      state: dict, user_id: uuid.UUID) -> RunResult: ...
    async def enqueue(self, run_id: uuid.UUID, factory: PipelineFactory,
                      state: dict, user_id: uuid.UUID) -> None: ...
```

### SyncExecutor (Phase 6-F.3 Default)

Runs in a background thread via `asyncio.to_thread()` to avoid blocking the event loop:

```python
class SyncExecutor:
    async def execute(self, run_id, factory, state, user_id) -> RunResult:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: _sync_execute_impl(run_id, factory, state, user_id)
        )
```

### Submit Pattern (API Entry Point)

```python
@router.post("/run", response_model=APIResponse[AgentRunResponse])
async def submit_agent_run(
    body: AgentRunRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = get_agent_runtime_service(db)
    run = await service.submit(
        agent_type=body.agent_type,
        input_payload=body.input_payload,
        user_id=current_user.id,
    )
    return APIResponse(success=True, data=run, error=None)
```

**The API always returns immediately with the run ID.** Execution proceeds asynchronously. This is the contract that will remain identical when we swap SyncExecutor for RQ/Celery.

---

## 7. Database Migration Plan

### Pre-Migration Verification

Before modifying `AgentRun`, verify:

1. **Existing schema audit** — Run `alembic history --verbose` and `alembic current` to confirm migration chain is intact
2. **Audit log compatibility** — Verify `audit_logs` table references to `agent_runs` are not broken (FK constraints, trigger functions)
3. **Ownership tracking** — Confirm `user_id` FK on `agent_runs` is not referenced by ownership policies that assume specific column types
4. **Current data** — Check if any `agent_runs` rows exist with `status` values outside the new valid set

### Migration: `0007_add_agent_runtime_tracking`

#### New Table: `agent_stage_progress`

Tracks per-stage execution details within an AgentRun.

```sql
CREATE TABLE agent_stage_progress (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_run_id  UUID NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    stage_name    VARCHAR(64) NOT NULL,
    stage_order   INTEGER NOT NULL,
    status        VARCHAR(32) NOT NULL,
    input_summary JSONB,
    output_summary JSONB,
    error_message TEXT,
    duration_ms   INTEGER,
    started_at    TIMESTAMPTZ,
    finished_at   TIMESTAMPTZ,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(agent_run_id, stage_name)
);

CREATE INDEX idx_agent_stage_progress_run ON agent_stage_progress(agent_run_id);
```

#### Modified Table: `agent_runs`

Add two columns — backward compatible, non-breaking:

```sql
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS stage VARCHAR(64) DEFAULT 'initializing';
ALTER TABLE agent_runs ALTER COLUMN status TYPE VARCHAR(32) USING status::varchar(32);
```

- Widen `agent_runs.status` from `VARCHAR(16)` to `VARCHAR(32)` — safe, no data loss, uses `USING` clause for type cast
- Add `agent_runs.stage` column — nullable, defaults to `"initializing"`, no existing data affected

### SQLAlchemy Models

```python
class AgentStageProgress(Base):
    __tablename__ = "agent_stage_progress"
    id: Mapped[uuid.UUID]
    agent_run_id: Mapped[uuid.UUID]
    stage_name: Mapped[str]
    stage_order: Mapped[int]
    status: Mapped[str]
    input_summary: Mapped[dict | None]
    output_summary: Mapped[dict | None]
    error_message: Mapped[str | None]
    duration_ms: Mapped[int | None]
    started_at: Mapped[datetime]
    finished_at: Mapped[datetime | None]

class AgentRun(Base):
    # existing fields...
    stage: Mapped[str] = mapped_column(String(64), default="initializing")
    # status column widened to VARCHAR(32) via migration
```

### Alembic Migration Notes

- Widen `agent_runs.status` from `VARCHAR(16)` to `VARCHAR(32)` — safe, no data loss
- Add `agent_stage_progress` table — empty, no data migration needed
- Add `agent_runs.stage` column — nullable, defaults to `"initializing"`
- **Downgrade path**: DROP INDEX, DROP TABLE, revert ALTER COLUMN (use `VARCHAR(16)` downgrade)
- **No changes to audit_logs**: The audit log subscriber pattern is unaffected

---

## 8. Event Abstraction for Streaming

### Design Principle: Events First, Transport Second

Define a clean `AgentEvent` abstraction that is independent of the transport mechanism (SSE, WebSocket, polling). This allows swapping transports later without changing the event model.

### Event Types

```python
class EventType(str, Enum):
    STAGE_START = "stage_start"
    STAGE_COMPLETE = "stage_complete"
    STAGE_FAILED = "stage_failed"
    RUN_COMPLETE = "run_complete"
    RUN_FAILED = "run_failed"
    RUN_CANCELLED = "run_cancelled"
    HEARTBEAT = "heartbeat"

@dataclass
class AgentEvent:
    type: EventType
    run_id: uuid.UUID
    timestamp: datetime
    stage_name: str | None = None          # present for stage events
    status: str | None = None              # stage/status snapshot
    output_summary: dict | None = None     # truncated result
    error_message: str | None = None       # failure details
    duration_ms: int | None = None         # stage or total duration
    extra: dict = field(default_factory=dict)
```

### SSE Transport

```python
@router.get("/runs/{run_id}/stream")
async def stream_agent_status(
    run_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Stream agent execution progress as Server-Sent Events."""
    return StreamingResponse(
        event_to_sse_generator(run_id, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

Event format:
```
event: stage_start
data: {"type":"stage_start","run_id":"...","stage_name":"research","timestamp":"..."}

event: stage_complete
data: {"type":"stage_complete","run_id":"...","stage_name":"research","duration_ms":4520,"output_summary":{...}}

event: run_complete
data: {"type":"run_complete","run_id":"...","status":"completed","total_duration_ms":12300}

event: heartbeat
data: {"type":"heartbeat","run_id":"...","timestamp":"..."}
```

### WebSocket Transport (Future)

The same `AgentEvent` dataclass serializes to JSON for WebSocket frames. No schema changes needed — just swap the transport layer.

### Polling Fallback (Frontend)

For environments where SSE is unreliable, the existing `GET /runs/{id}` endpoint returns the latest state. Frontend polls via React Query `refetchInterval`.

---

## 9. Cancellation Design

### State Machine

```
pending → running → completed
           │         → failed
           │         → timeout
           ↓
        cancelling → cancelled
                    → completed*  (*if node was nearly done)
```

The key transition: `running → cancelling → cancelled`. There is no direct `running → cancelled` — the `cancelling` intermediate state signals to the frontend that cancellation was requested and is in progress.

### Implementation

```python
async def cancel_run(self, run_id: uuid.UUID, user_id: uuid.UUID):
    run = await self._repo.get_by_id(run_id)
    if not run or run.status != "running":
        raise AgentRunNotFoundError(run_id)
    if run.user_id != user_id:
        raise PermissionDeniedError()

    # Transition: running → cancelling
    run.status = "cancelling"
    await self._session.commit()

    # Signal to running executor (via shared state or event bus)
    self._cancellation_tokens[run_id] = True

    # Background task monitors: when executor finishes current node,
    # it checks cancellation token and transitions to "cancelled"
    asyncio.create_task(self._await_cancellation_completion(run_id))

async def _await_cancellation_completion(self, run_id: uuid.UUID):
    """Wait for executor to observe cancellation and finalize."""
    for _ in range(30):  # up to 30 seconds
        await asyncio.sleep(1)
        run = await self._repo.get_by_id(run_id)
        if run and run.status in ("cancelled", "completed", "failed"):
            return
    # Force-finalize after timeout
    run = await self._repo.get_by_id(run_id)
    if run and run.status == "cancelling":
        run.status = "cancelled"
        run.finished_at = datetime.now(timezone.utc)
        await self._session.commit()
```

### Executor Integration

The executor checks `self._cancellation_tokens.get(run_id)` between nodes (not mid-node, since `graph.invoke()` is blocking). If cancellation is flagged:

```python
def _sync_execute_impl(run_id, factory, state, user_id):
    run = session.get(AgentRun, run_id)
    graph = factory()

    for chunk in graph.stream(state):  # use .stream() not .invoke() for interruptibility
        if cancellation_tokens.get(run_id):
            run.status = "cancelled"
            run.finished_at = datetime.now(timezone.utc)
            session.commit()
            return RunResult(status="cancelled")
        # process chunk...
```

Using `.stream()` instead of `.invoke()` allows checking cancellation between graph steps.

---

## 10. API Endpoint Design

### New Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/agents/run` | Submit agent run (async, returns run_id immediately) |
| `GET` | `/api/v1/agents/runs/{run_id}` | Get single run with stage details |
| `GET` | `/api/v1/agents/runs/{run_id}/stream` | SSE stream for live progress |
| `POST` | `/api/v1/agents/runs/{run_id}/cancel` | Cancel a running run |
| `GET` | `/api/v1/agents` | List available agents |

### Updated Existing Endpoint

`POST /api/v1/agents/{agent_id}/run` — kept for backward compatibility but deprecated. Routes to the new `AgentRuntimeService`.

### Endpoint Details

#### `POST /api/v1/agents/run`

```python
@router.post("/run", response_model=APIResponse[AgentRunResponse])
async def submit_agent_run(
    body: AgentRunRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = get_agent_runtime_service(db)
    run = await service.submit(
        agent_type=body.agent_type,
        input_payload=body.input_payload,
        user_id=current_user.id,
    )
    return APIResponse(success=True, data=run, error=None)
```

`AgentRunRequest` schema:
```python
class AgentRunRequest(BaseModel):
    agent_type: str                              # maps via PIPELINE_MAP
    input_payload: dict[str, Any] = Field(default_factory=dict)
    topic: str | None = None                     # convenience for intelligence workflows
    source_id: str | None = None                 # article ID for article-specific runs
```

#### `GET /api/v1/agents/runs/{run_id}`

Returns full run + all stage progress records:

```python
class AgentRunWithStages(AgentRunResponse):
    stages: list[StageProgressResponse]
    stream_url: str  # SSE endpoint URL for live updates
```

#### `GET /api/v1/agents/runs/{run_id}/stream`

Server-Sent Events endpoint using `AgentEvent` abstraction (§8).

#### `POST /api/v1/agents/runs/{run_id}/cancel`

```python
@router.post("/runs/{run_id}/cancel")
async def cancel_agent_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = get_agent_runtime_service(db)
    await service.cancel_run(run_id, user_id=current_user.id)
    return APIResponse(success=True, data={"cancelled": True})
```

#### `GET /api/v1/agents`

```python
@router.get("/")
async def list_agents():
    """Return available agent types and their descriptions."""
    return APIResponse(success=True, data=[
        {"type": "intelligence", "name": "Daily Intelligence", "description": "Research → Analyze → Translate", "nodes": 3},
        {"type": "autonomous", "name": "Autonomous Intelligence", "description": "Full pipeline with knowledge extraction and project planning", "nodes": 6},
    ])
```

---

## 11. Error Handling and Retries

### Error Categories

| Category | Example | Recovery |
|----------|---------|----------|
| **Transient LLM error** | 429 rate limit, connection timeout | Retry with exponential backoff (3 attempts) |
| **Node failure** | No research output for analyst | Mark stage as failed, continue pipeline |
| **MCP tool failure** | Notion API down | Log error, skip MCP step, continue |
| **Graph exception** | Invalid state, missing field | Fail entire run, capture traceback |
| **Timeout** | Run exceeds 5 minutes | Interrupt graph, mark as `"timeout"` |

### Retry Strategy

```python
async def _execute_with_retry(node_fn, retries=3, base_delay=1.0):
    """Retry transient failures with exponential backoff."""
    for attempt in range(retries):
        try:
            return await node_fn()
        except (httpx.TimeoutException, httpx.ConnectError, RateLimitError) as e:
            if attempt == retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            logger.warning("Retry %d/%d for %s after %.1fs: %s",
                          attempt + 1, retries, node_fn.__name__, delay, e)
            await asyncio.sleep(delay)
```

Applied at the **node level** (per-agent retry), not the graph level. Failed nodes return error results to state (current behavior preserved).

### Timeout Implementation

```python
import asyncio

async def _run_with_timeout(graph_app, state, timeout_seconds=300):
    """Run graph with hard timeout."""
    try:
        return await asyncio.wait_for(graph_app.astream(state), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        raise AgentTimeoutError(f"Run exceeded {timeout_seconds}s timeout")
```

---

## 12. Testing Strategy

### Backend Unit Tests (Complete Before Frontend)

| Test | File | Coverage |
|------|------|----------|
| `AgentRuntimeService.submit()` with valid payload | `tests/unit/services/test_agent_runtime.py` | Creates run, dispatches to executor, returns run_id |
| `AgentRuntimeService.submit()` with invalid agent_type | Same | Returns validation error, run stays in error state |
| `AgentRuntimeService.cancel_run()` | Same | Transitions running → cancelling → cancelled |
| `SyncExecutor.execute()` | Same | Verifies graph invocation and result persistence |
| `AgentRuntimeCallback.on_chain_start/end/error` | Same | Verifies DB writes for stage progress |
| Pipeline selection via `PIPELINE_MAP` | Same | Verifies correct factory lookup, fallback to name matching |
| `AgentEvent` serialization | Same | Verifies SSE and JSON encoding |

### Backend Integration Tests

| Test | File | Coverage |
|------|------|----------|
| Full flow: POST submit → SSE stream → completion | `tests/integration/test_agent_runtime.py` | End-to-end with mock LLM |
| Timeout scenario | Same | Verify `"timeout"` status |
| Cancellation between nodes | Same | Verify status transition running → cancelling → cancelled |
| MCP tool failure during run | Same | Verify stage continues with error |
| Concurrent runs (same agent) | Same | Verify isolation |

### Mock Strategy

- **LLMRouter/LLMClient**: Mock to return deterministic test data (no real API calls)
- **MCP tools**: Use existing stub behavior (env var missing → mock response)
- **SSE streaming**: Test with `httpx.AsyncClient` and capture streamed events
- **Database**: Use test PostgreSQL instance (same pattern as existing tests)

### Frontend Tests

| Test | File | Coverage |
|------|------|----------|
| `useAgentStream` hook | `frontend/hooks/__tests__/useAgentStream.test.ts` | Connects, receives events, closes on unmount |
| `useAgentPolling` fallback | Same | Polls at interval, stops when run completes |
| `StageProgress` component | `frontend/components/panels/__tests__/StageProgress.test.tsx` | Renders correct colors/states |
| `AgentMonitorPanel` happy path | Same | Submits run, shows progress, displays output |

---

## 13. Delivery Order — Backend First, Then Frontend

### Phase A: Backend Infrastructure (Stable API)

1. Database migration (`0007_add_agent_runtime_tracking`)
2. `AgentStageProgress` model and repository
3. `AgentRuntimeService` with `submit()`, `cancel_run()`, `get_run()`
4. `Executor` protocol + `SyncExecutor` implementation
5. `AgentRuntimeCallback` for LangGraph integration
6. `AgentEvent` abstraction + SSE streaming endpoint
7. Pipeline selection via `PIPELINE_MAP`
8. New API endpoints: `/run`, `/runs/{id}`, `/runs/{id}/stream`, `/runs/{id}/cancel`
9. Update existing `POST /{agent_id}/run` to delegate to runtime service
10. **All unit + integration tests passing**

### Phase B: Frontend Integration

11. `useAgentStream` hook (SSE) + polling fallback
12. Extended React Query hooks for agent runs
13. `AgentMonitorPanel` component
14. `StageProgress` visual component
15. Wire into existing "Agents" tab on dashboard

**Do NOT begin Phase B until Phase A API is stable and tested.**

---

## 14. Files to Create / Modify

### New Files

| File | Purpose |
|------|---------|
| `backend/services/agent_runtime_service.py` | Core orchestration layer |
| `backend/workflows/graph/callbacks.py` | LangGraph callback handler for runtime tracking |
| `backend/workflows/executor.py` | Executor protocol + SyncExecutor |
| `backend/events/agent_event.py` | AgentEvent abstraction + SSE generator |
| `backend/database/models/agent_stage_progress.py` | New model |
| `backend/repositories/agent_stage_progress_repository.py` | CRUD for stage progress |
| `backend/schemas/agent_run.py` | Extended schemas (AgentRunWithStages, StageProgressResponse) |
| `frontend/hooks/useAgentStream.ts` | SSE event source hook |
| `frontend/components/panels/AgentMonitorPanel.tsx` | New panel replacing Agents tab |
| `frontend/components/panels/StageProgress.tsx` | Visual stage progress component |
| `frontend/components/panels/OutputViewer.tsx` | Collapsible output display |
| `backend/alembic/versions/0007_add_agent_runtime_tracking.py` | Migration |

### Modified Files

| File | Change |
|------|--------|
| `backend/database/models/agent_run.py` | Add `stage` column, widen `status` VARCHAR |
| `backend/services/agent_service.py` | Delegate to `AgentRuntimeService` where appropriate |
| `backend/routers/agents.py` | New endpoints, wire runtime service |
| `frontend/types/index.ts` | Add `AgentRunWithStages`, `StageProgress`, `AgentEvent` types |
| `frontend/app/page.tsx` | Wire AgentMonitorPanel into agents tab |

### Dependencies

**No new Python dependencies required.** Uses existing:
- `langgraph` (callbacks already available)
- `fastapi.StreamingResponse` (already installed via FastAPI)
- `asyncio` (stdlib)

**No new frontend dependencies.** Uses native `EventSource` API + React Query polling fallback.
