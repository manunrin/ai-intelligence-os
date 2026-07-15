# Agent Architecture

## Overview

AI Intelligence OS uses a layered agent runtime where agents, workflows, and tools form a composable system. Agents perform specific tasks, workflows orchestrate multi-agent pipelines, and tools provide capabilities (web search, API calls, translation) that any agent can invoke.

## Design Principles

1. **Abstraction over implementation** — `AgentBase` defines the contract; concrete agents fill in the logic
2. **Prompt templates externalized** — all LLM prompts live as markdown files in `backend/prompts/`, never hardcoded
3. **Tool registry pattern** — tools register centrally and are discovered at runtime
4. **Stateless execution** — each agent run is self-contained; state is passed via input/output dicts
5. **No direct LLM coupling** — agents call through a LLM gateway abstraction (implemented later)

## Agent Design

```
AgentBase (abstract)
├── name: str              # Unique identifier
├── version: str           # Semantic version
├── description: str       # Human-readable purpose
├── metadata: AgentMetadata  # Run tracking (state, timing, errors)
└── execute(input) → output  # Async entry point

Concrete agents inherit AgentBase:
  ResearchAgent   → name="research"
  AnalystAgent    → name="analyst"
  TranslatorAgent → name="translator"
  KnowledgeAgent  → name="knowledge"
  TaskAgent       → name="task"
  NotificationAgent→ name="notification"
```

Each agent implements `_execute_impl(input_data)` which receives a dict and returns a dict. The base class wraps this with:
- State tracking (`IDLE → RUNNING → COMPLETED/FAILED`)
- Error handling (returns `success: False` + error message)
- Metadata snapshot (run_id, timestamps, extra fields)

### Agent Lifecycle

```
Create → Execute → Complete/Fail → Inspect metadata
```

```python
agent = ResearchAgent()
result = await agent.execute({"topic": "AI agents", "focus_areas": ["security"]})
# result = {
#     "success": True,
#     "output": {...},
#     "metadata": {"run_id": "...", "state": "completed", ...}
# }
```

## Workflow Design

```
WorkflowBase (abstract)
├── name: str              # Workflow identifier
├── description: str       # Purpose
├── context: WorkflowContext  # Shared state across agents
├── get_agents() → list    # Ordered agent chain
└── execute(input) → output  # Pipeline runner

Concrete workflows define their agent chain:
  DailyIntelligenceWorkflow  → [Research → Crawl → Analyze → Translate → Store]
  OnDemandReportWorkflow     → [Research → Analyze → Format]
```

A workflow is an ordered chain of agents. Each agent's output becomes the next agent's input via shared `WorkflowContext.variables`.

### Workflow Execution Flow

```
Input → Agent[0].execute() → Agent[1].execute() → ... → Final Output
         ↓ success? fail?      ↓ success? fail?
       continue              stop on failure
```

If any agent fails, the workflow stops immediately and returns the error. Variables accumulated during execution remain accessible for debugging.

## Tool Calling Flow

```
ToolBase (abstract)          ToolRegistry
├── name: str                ├── register(tool)
├── description: str         ├── get(name) → ToolBase
├── parameters: dict         └── list_schemas() → {name: schema}
├── execute(**kwargs)        # Returns ToolResult
└── _execute_impl(**kwargs)  # Abstract

Tools register with the central registry:
  registry = ToolRegistry()
  registry.register(WebSearchTool())
  registry.register(TranslationTool())
  registry.register(FileStorageTool())
```

### How Agents Use Tools

1. Agent declares which tools it needs (via configuration or capability metadata)
2. At runtime, agent queries the registry for available tools
3. Agent invokes tool.execute(**params) → ToolResult(success, data, error)
4. Tool results are incorporated into the agent's output

```python
class ResearchAgent(AgentBase):
    async def _execute_impl(self, input_data):
        tool = self.registry.get("web_search")
        result = await tool.execute(query=input_data["topic"])
        if result.success:
            return {"findings": result.data}
        return {"error": result.error}
```

## Prompt Management

All LLM prompts are stored as markdown files in `backend/prompts/`:

```
backend/prompts/
├── research.md        # Research agent prompt template
├── analyst.md         # Analyst agent prompt template
└── translator.md      # Translation agent prompt template
```

Templates use Python `.format()` variable injection:

```markdown
# {{title}}

{{instruction}}

## Input
{{input_data}}
```

Loaded via `load_prompt(name, **variables)`:

```python
from backend.prompts.loader import load_prompt

prompt = load_prompt("research", topic="LLMs", focus_areas=["safety"])
# Renders the .md file with variables substituted
```

This ensures prompts are:
- **Version controlled** alongside code
- **Editable without redeployment** (when mounted as volumes)
- **Separate from logic** — no prompt strings in Python files

## Directory Structure

```
backend/
├── agents/
│   ├── __init__.py
│   └── base.py            # AgentBase, AgentMetadata, AgentState
├── workflows/
│   ├── __init__.py
│   └── base.py            # WorkflowBase, WorkflowContext
├── tools/
│   ├── __init__.py
│   ├── base.py            # ToolBase, ToolResult
│   └── registry.py        # ToolRegistry
└── prompts/
    ├── __init__.py
    ├── loader.py           # load_prompt(), list_available_prompts()
    ├── research.md         # Prompt templates
    ├── analyst.md
    └── translator.md
```

## Future Extensions

- **LangGraph integration** — replace `WorkflowBase` with LangGraph state machines
- **Human-in-the-loop** — add interrupt/resume capability to `AgentState`
- **Agent evaluation** — track quality scores per execution (see `docs/future-data-model.md`)
- **MCP tool consumption** — agents discover tools via MCP servers
