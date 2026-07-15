# LangGraph Architecture

## Overview

The LangGraph runtime replaces the simple `WorkflowBase` chain with a stateful `StateGraph` that provides:

- Explicit state schema (`IntelligenceState`)
- Node-based execution (each agent = one node)
- Error isolation (node failures don't crash the pipeline)
- Checkpointing support (human-in-the-loop, resume)
- Visual graph debugging (`app.get_graph().draw_mermaid_png()`)

## State Design

All data flows through a single `IntelligenceState` model. Each node reads inputs from the state, executes its agent, and writes results back.

```python
class IntelligenceState(BaseModel):
    # Input
    topic: str
    focus_areas: list[str]
    target_languages: list[str] = ["zh-CN", "ja"]
    source_language: str | None

    # Stage outputs (filled by each node)
    research_result: dict | None
    analysis_result: dict | None
    translation_result: dict | None

    # Error tracking
    errors: list[dict[str, str]]

    # LLM message history (LangGraph built-in)
    messages: list
```

Fields merge on each step — partial updates are safe. A node can update just `research_result` without touching other fields.

## Node Design

Each node is a thin wrapper that delegates to an existing `AgentBase` subclass:

```
┌──────────────────────────────────────────────────┐
│  ResearchNode (wrapper)                           │
│  ├─ reads: state.topic, state.focus_areas         │
│  ├─ calls: ResearchAgent.execute(input_data)      │
│  └─ writes: state.research_result                 │
├──────────────────────────────────────────────────┤
│  AnalystNode (wrapper)                            │
│  ├─ reads: state.research_result.response         │
│  ├─ calls: AnalystAgent.execute(input_data)       │
│  └─ writes: state.analysis_result                 │
├──────────────────────────────────────────────────┤
│  TranslatorNode (wrapper)                         │
│  ├─ reads: state.analysis_result.response         │
│  ├─ calls: TranslatorAgent.execute(input_data)    │
│  └─ writes: state.translation_result              │
└──────────────────────────────────────────────────┘
```

Nodes catch exceptions and record them in `state.errors` rather than raising. This prevents a single node failure from crashing the entire pipeline.

## Graph Structure

```
START
  │
  ▼
┌─────────┐
│ research │  → ResearchAgent
└────┬────┘
     │
     ▼
┌─────────┐
│ analyst  │  → AnalystAgent
└────┬────┘
     │
     ▼
┌─────────────┐
│ translator   │  → TranslatorAgent
└────┬────────┘
     │
     ▼
   END
```

Built via `build_intelligence_graph()` → `StateGraph(IntelligenceState)` → `add_node()` → `add_edge()` → `compile()`.

## Execution Flow

```python
from backend.workflows.daily_intelligence import run_daily_intelligence

result = run_daily_intelligence(
    topic="Latest developments in AI reasoning",
    focus_areas=["safety", "performance"],
    target_languages=["zh-CN", "ja"],
)

# result contains:
# {
#     "topic": "...",
#     "research_result": {...},
#     "analysis_result": {...},
#     "translation_result": {...},
#     "errors": []
# }
```

## Checkpointing

Enable with `compile_intelligence_graph(checkpoint=True)`:

```python
app = compile_intelligence_graph(checkpoint=True)
# Enables:
# - State persistence between steps
# - Human-in-the-loop approval gates
# - Graph replay from any checkpoint
```

## Not Implemented

- MCP integration
- Notion/Asana connectors
- WeChat/Telegram notifications
- News crawler
- Scheduled task runner
- Real LLM connections (providers still return NotImplemented)
