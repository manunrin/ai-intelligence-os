# Phase 10.1 — Agent Runtime Persistence: 正式集成方案

**日期:** 2026-07-22  
**状态:** 草案，等待确认  
**前置条件:** AsyncShallowPostgresSaver POC 已验证通过（clean DB）

---

## 0. POC 结论回顾

| 验证项 | 结果 |
|--------|------|
| `AsyncShallowPostgresSaver.setup()` | ✅ 成功创建表 |
| `graph.compile(checkpointer=saver)` | ✅ 编译成功 |
| `compiled.ainvoke()` 首次执行 | ✅ value=11 |
| `compiled.ainvoke()` 第二次执行（resume） | ✅ value=111，恢复正确 |
| 新 thread 独立运行 | ✅ value=1010 |
| Checkpoint 持久化到 PostgreSQL | ✅ 2 checkpoints 写入 |
| `langgraph==1.2.9` + `langgraph-checkpoint-postgres==3.1.0` | ✅ 兼容 |

### 关键发现

1. **必须使用 `AsyncShallowPostgresSaver`** — `PostgresSaver` 只有同步方法，无法在 `ainvoke()` 中使用
2. **Clean DB 验证通过** — 现有 `ai_intelligence_os` 数据库的 `checkpoint_blobs` 表有 4 列 PK（含 `version`），是旧数据残留。新建 DB 后 schema 匹配（3 列 PK），POC 全部通过
3. **同步查询限制** — `AsyncShallowPostgresSaver.get_tuple()` 在主线程会抛 `InvalidStateError`，必须用 `await aget_tuple()`；但恢复扫描可以直接查 PostgreSQL

---

## 1. Saver 生命周期设计

### 1.1 创建位置

```
FastAPI lifespan (startup)
    ↓
create ConnectionPool (asyncpg)
    ↓
create PostgresSaver(conn=pool)
    ↓
await saver.setup()
    ↓
app.state.checkpointer = saver
```

**选择 `PostgresSaver`（非 Shallow）的原因：**
- `PostgresSaver.setup()` 是同步方法，可在 lifespan 中直接调用
- `PostgresSaver` 支持完整 checkpoint history（shallow 只保留最新）
- 虽然 POC 用的是 `AsyncShallowPostgresSaver`，但正式环境应使用完整版本
- `PostgresSaver` 的 `list()`, `get_tuple()`, `put()`, `put_writes()` 都是同步方法
- 在 `SyncExecutor` 的 `run_in_executor` 线程中调用这些同步方法完全兼容

**等等 — 需要重新审视：**

当前 `SyncExecutor.execute()` 在后台线程中：
1. 创建新的 asyncio event loop
2. 调用 `graph_app.astream(state)`（异步图流）
3. LangGraph 内部会调用 checkpointer 的 `aput()` / `aget_tuple()`

如果 checkpointer 是 `PostgresSaver`（只有同步方法），LangGraph 的 `AsyncPregelLoop` 会调用 `BaseCheckpointSaver.aget_tuple()` → 默认实现是 `NotImplementedError`。

**结论：必须使用 `AsyncShallowPostgresSaver`。**

### 1.2 生命周期细节

```python
# backend/main.py lifespan

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... 现有初始化代码 ...

    # --- Checkpointer initialization ---
    from langgraph.checkpoint.postgres.shallow import AsyncShallowPostgresSaver

    db_url = str(settings.database_url)
    saver = await AsyncShallowPostgresSaver.from_conn_string(db_url).__aenter__()
    try:
        await saver.setup()
    except Exception:
        # Tables may already exist, swallow
        pass
    finally:
        await saver.__aexit__(None, None, None)

    app.state.checkpointer = saver

    yield

    # Shutdown: close saver connections
    if hasattr(app.state, 'checkpointer'):
        await app.state.checkpointer.__aexit__(None, None, None)
```

**问题：** `from_conn_string()` 返回的是 context manager，不能直接赋值给 `app.state`。

**修正方案：** 使用 `ConnectionPool` 手动管理：

```python
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres.shallow import AsyncShallowPostgresSaver

pool = ConnectionPool(
    conninfo=str(settings.database_url),
    min_size=1,
    max_size=2,
    open=True,
    kwargs={"autocommit": True},
)

saver = AsyncShallowPostgresSaver(conn=pool)
await saver.setup()
app.state.checkpointer = saver
```

**shutdown:**
```python
pool.close()
```

### 1.3 为什么不用单例

每个 `AgentRuntimeService` 实例需要访问同一个 saver。通过 `app.state.checkpointer` 共享即可，不需要单例模式。

---

## 2. Graph Builder 修改方案

### 2.1 修改文件

`backend/workflows/graph/builder.py`

### 2.2 当前代码

```python
def compile_intelligence_graph(checkpoint: bool = False) -> Any:
    graph = build_intelligence_graph()
    compile_kwargs: dict[str, Any] = {}
    if checkpoint:
        from langgraph.checkpoint.memory import MemorySaver
        compile_kwargs["checkpointer"] = MemorySaver()
    return graph.compile(**compile_kwargs)
```

### 2.3 修改方案

```python
def compile_intelligence_graph(
    checkpointer: Any = None,
    checkpoint: bool = False,
) -> Any:
    graph = build_intelligence_graph()
    compile_kwargs: dict[str, Any] = {}

    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer
    elif checkpoint:
        from langgraph.checkpoint.memory import MemorySaver
        compile_kwargs["checkpointer"] = MemorySaver()

    return graph.compile(**compile_kwargs)
```

**同样修改 `autonomous_intelligence.py` 中的编译函数。**

### 2.4 Registry 修改

`backend/workflows/registry.py` 目前注册的是 factory 函数：

```python
PIPELINE_REGISTRY = {
    "intelligence": compile_intelligence_graph,
    "autonomous": compile_autonomous_intelligence,
}
```

需要改为接收 checkpointer 参数：

```python
PIPELINE_REGISTRY: dict[str, Callable[..., Any]] = {
    "intelligence": lambda cp=None: compile_intelligence_graph(checkpointer=cp),
    "autonomous": lambda cp=None: compile_autonomous_intelligence(checkpointer=cp),
}
```

或者更简洁地保持原样，在 executor 层传入 checkpointer。

---

## 3. Executor 修改方案

### 3.1 当前代码

`backend/workflows/executor.py` 的 `SyncExecutor`:

```python
class SyncExecutor(Executor):
    async def execute(self, run_id, factory, state, user_id, session, cancellation_token):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: _sync_execute_impl(run_id, factory, state, user_id, session, cancellation_token),
        )
```

`_sync_execute_impl` 创建新的 event loop，然后调用 `graph_app.astream()`。

### 3.2 修改方案

**核心变更：** `Executor` 协议不变，但 `SyncExecutor` 改为直接使用当前 event loop 的 `asyncio.to_thread()` 或直接 async 执行。

实际上，由于 `factory()` 已经返回 compiled graph（包含 checkpointer），而 `_stream_with_cancel` 已经是 async 的：

```python
class SyncExecutor(Executor):
    async def execute(
        self,
        run_id: uuid.UUID,
        factory: PipelineFactory,
        state: dict[str, Any],
        user_id: uuid.UUID,
        session: AsyncSession,
        cancellation_token: dict[uuid.UUID, bool],
        checkpointer: Any = None,
    ) -> RunResult:
        """Execute using async stream with optional checkpointer."""
        start_time = datetime.now(timezone.utc)
        try:
            graph_app = factory()

            chunks = await _stream_with_cancel(
                graph_app, state, run_id, cancellation_token
            )

            output = {}
            for chunk in chunks:
                if isinstance(chunk, dict):
                    output.update(chunk)

            duration = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            return RunResult(
                status="completed",
                run_id=run_id,
                output_payload=output,
                duration_ms=duration,
                finished_at=datetime.now(timezone.utc),
            )
        except Exception as exc:
            ...
```

**注意：** 当前 `_sync_execute_impl` 用 `asyncio.new_event_loop()` 来运行 async 代码。这是因为 `run_in_executor` 在线程中调用。如果我们去掉 `run_in_executor`，直接在 async context 中执行，就不需要新 event loop。

### 3.3 Thread ID 映射

每个 agent run 需要一个唯一的 `thread_id` 用于 LangGraph checkpoint：

```python
thread_id = f"agent-run-{run_id}"
config = {"configurable": {"thread_id": thread_id}}
```

这个 `thread_id` 需要存储到 `AgentRun` 表中，以便恢复扫描时查找。

---

## 4. AgentRun 数据模型设计

### 4.1 新增字段

```python
# backend/database/models/agent_run.py

class AgentRun(Base):
    # ... 现有字段 ...

    thread_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    # LangGraph checkpoint thread_id，格式: "agent-run-{uuid}"

    recovered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # 恢复时间戳（从 stale 状态恢复的时间）
```

### 4.2 Migration

```sql
-- 0003_agent_run_persistence
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS thread_id VARCHAR(128);
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS recovered_at TIMESTAMPTZ;
CREATE INDEX idx_agent_runs_thread_id ON agent_runs(thread_id) WHERE thread_id IS NOT NULL;
```

### 4.3 是否需要 checkpoint_id？

**不需要单独字段。** `thread_id` 本身就是 LangGraph 的 checkpoint 标识符。通过 `thread_id` 可以：
- 查询该 run 的 checkpoint
- 恢复 stale run
- 无需额外的 `checkpoint_id` 列

---

## 5. Recovery Scan 设计

### 5.1 触发时机

在 `AgentRuntimeService.__init__()` 或 FastAPI lifespan 中，所有其他初始化完成之后。

### 5.2 逻辑

```python
async def _recover_stale_runs(self) -> None:
    """Mark stale running/cancelling runs as failed or recovered."""
    from sqlalchemy import select
    from ..database.models import AgentRun

    stmt = select(AgentRun).where(
        AgentRun.status.in_(["running", "cancelling"])
    )
    result = await self._request_session.execute(stmt)
    stale_runs = result.scalars().all()

    for run in stale_runs:
        now = _utcnow()

        # Check if this run has a checkpoint in LangGraph
        if run.thread_id:
            try:
                # Try to access checkpointer to verify checkpoint exists
                # If it fails, the run is truly lost
                pass
            except Exception:
                pass

        # Mark as stale/failed
        run.status = "failed"
        run.stage = "stale"
        run.error_message = (
            f"Run was interrupted during backend restart. "
            f"Started at {run.started_at.isoformat()}. "
            f"Marked stale by recovery scan."
        )
        run.finished_at = now
        run.duration_ms = int((now - run.started_at).total_seconds() * 1000)
        run.recovered_at = now

        counter("agent_runs_recovered_total", labels={"status": "stale"})
        logger.warning("Marked stale run %s as failed", str(run.id))

    await self._request_session.commit()
```

### 5.3 恢复策略

Phase 10.1 只做 **stale detection + marking**，不做真正的 checkpoint 恢复（那是 Phase 10.2 的 retry 功能）。

原因：
- `AsyncShallowPostgresSaver` 只保留最新 checkpoint，不支持 time-travel
- 真正的 resume 需要从 checkpoint 重建 state，这需要额外工作
- 先确保 stale runs 被正确标记，不丢失可观测性

---

## 6. FastAPI Lifespan 集成

### 6.1 修改文件

`backend/main.py`

### 6.2 集成点

在现有 lifespan 中，LLM router 和 embedding client 初始化之后添加 checkpointer：

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bootstrap

    from .config import get_settings
    logger.info("Starting AI Intelligence OS backend...")

    # Initialize engine explicitly
    engine, session_factory = create_engine_for_settings(get_settings())

    # Initialize MCP servers, tool registry, and agents
    _bootstrap = ApplicationBootstrap(session_factory)
    _bootstrap.initialize()

    # ... 现有 LLM/embedding/vector initialization ...

    # --- Checkpointer initialization ---
    from psycopg_pool import ConnectionPool
    from langgraph.checkpoint.postgres.shallow import AsyncShallowPostgresSaver

    settings = get_settings()
    db_url = str(settings.database_url)

    pool = ConnectionPool(
        conninfo=db_url,
        min_size=1,
        max_size=2,
        open=True,
        kwargs={"autocommit": True},
    )

    checkpointer = AsyncShallowPostgresSaver(conn=pool)
    try:
        await checkpointer.setup()
        logger.info("Checkpointer initialized with AsyncShallowPostgresSaver")
    except Exception as exc:
        logger.warning("Checkpointer setup failed: %s", exc)
        checkpointer = None

    app.state.checkpointer = checkpointer
    app.state.checkpoint_pool = pool

    # ... 现有 yield ...

    yield

    # Shutdown
    if hasattr(app.state, 'checkpointer') and app.state.checkpointer:
        await app.state.checkpointer.__aexit__(None, None, None)
    if hasattr(app.state, 'checkpoint_pool'):
        app.state.checkpoint_pool.close()

    if _bootstrap:
        await _bootstrap.mcp_registry.shutdown_all()
    await engine.dispose()
    logger.info("Backend shutdown complete")
```

---

## 7. 文件变更清单

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `backend/main.py` | 修改 | lifespan 中添加 checkpointer 初始化/shutdown |
| `backend/workflows/graph/builder.py` | 修改 | `compile_intelligence_graph()` 接收 `checkpointer` 参数 |
| `backend/workflows/autonomous_intelligence.py` | 修改 | 同上，`compile_autonomous_intelligence()` |
| `backend/workflows/executor.py` | 修改 | `SyncExecutor` 移除 `run_in_executor`，直接 async 执行 |
| `backend/services/agent_runtime_service.py` | 修改 | 传递 checkpointer 到 executor；添加 `_recover_stale_runs()` |
| `backend/database/models/agent_run.py` | 修改 | 添加 `thread_id`, `recovered_at` 字段 |
| `backend/alembic/versions/0003_agent_run_persistence.py` | 新建 | 数据库迁移 |
| `pyproject.toml` | 修改 | 添加 `psycopg-pool` 依赖 |

---

## 8. 测试计划

### 8.1 Unit Tests

- `test_checkpointer_lifecycle.py` — 验证 checkpointer 创建、setup、关闭
- `test_recovery_scan.py` — 验证 stale run 检测逻辑
- `test_executor_checkpoint.py` — 验证 executor 传递 checkpointer 到 graph

### 8.2 Integration Tests

- `test_agent_run_checkpoint.py` — 提交 agent run → 验证 checkpoint 写入 DB
- `test_stale_run_detection.py` — 模拟重启，验证 stale runs 被标记
- `test_thread_id_mapping.py` — 验证 `thread_id` 与 `run_id` 映射正确

### 8.3 Restart Recovery Test

1. 启动 backend，提交一个 agent run
2. 等待 run 开始执行（部分节点完成）
3. 停止 backend
4. 重新启动 backend
5. 验证：
   - 原 run 被标记为 `stale` 或 `failed`
   - `recovered_at` 有值
   - 新的 run 可以正常提交和执行
   - Checkpoint 表存在且可写入

---

## 9. 风险与注意事项

| 风险 | 影响 | 缓解 |
|------|------|------|
| `AsyncShallowPostgresSaver` 只保留最新 checkpoint | 无法 time-travel | 当前需求不需要；如需历史，后续换 `PostgresSaver` |
| `ConnectionPool` 在多线程环境下的行为 | 并发 run 可能争用连接 | `max_size=2` 足够；如不够再调大 |
| `setup()` 在已有表时抛异常 | 重启失败 | 捕获异常并 log warning，不阻断启动 |
| `thread_id` 冲突 | 不同 run 共享 checkpoint | 使用 `agent-run-{uuid}` 保证唯一 |
| Alembic migration 顺序 | 迁移冲突 | 确保 `0003` 在 `0002` 之后 |

---

## 10. 实施顺序

```
Step 1: pyproject.toml 添加 psycopg-pool 依赖
Step 2: database model 添加 thread_id, recovered_at
Step 3: Alembic migration 0003
Step 4: main.py lifespan 添加 checkpointer 初始化
Step 5: builder.py 修改接收 checkpointer
Step 6: executor.py 修改为 async-native
Step 7: agent_runtime_service.py 添加 recovery scan + 传递 checkpointer
Step 8: 编写测试
```

---

*方案待确认。确认后开始实施。*
