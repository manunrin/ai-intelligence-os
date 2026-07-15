# Core Agents

## Overview

AI Intelligence OS includes three core agents that form the foundation of the intelligence pipeline:

```
Information → ResearchAgent → AnalystAgent → TranslatorAgent → Knowledge
```

## Agent Registry

| Agent | Name | Version | Description |
|-------|------|---------|-------------|
| ResearchAgent | `research` | 0.1.0 | Gathers and synthesizes information on a topic |
| AnalystAgent | `analyst` | 0.1.0 | Evaluates content for importance, impact, and categorization |
| TranslatorAgent | `translator` | 0.1.0 | Translates content into target languages with confidence scores |

## ResearchAgent

**Purpose:** Collect and synthesize information about a given topic.

**Input:**
```python
{
    "topic": "Latest developments in LLM reasoning",
    "focus_areas": ["safety", "performance"],
    "sources": ["https://example.com/blog", "https://example.com/paper"],
}
```

**Output:**
```python
{
    "topic": "...",
    "focus_areas": [...],
    "response": "Structured analysis text...",
    "usage": {"prompt_tokens": 150, "completion_tokens": 320},
}
```

**LLM Call:** `LLMClient.chat(messages, task="research")`
**Prompt File:** `prompts/research_agent.md`

---

## AnalystAgent

**Purpose:** Assess intelligence items across multiple evaluation dimensions.

**Input:**
```python
{
    "content": "Full text of an article or report...",
    "category_hint": "technology",
}
```

**Output:**
```python
{
    "content_length": 4500,
    "response": "Dimension scores and reasoning...",
    "usage": {"prompt_tokens": 200, "completion_tokens": 180},
}
```

**LLM Call:** `LLMClient.chat(messages, task="analysis")`
**Prompt File:** `prompts/analyst_agent.md`

---

## TranslatorAgent

**Purpose:** Translate content into multiple target languages.

**Input:**
```python
{
    "content": "Original English text...",
    "target_languages": ["zh-CN", "ja", "en"],
    "source_language": "en",
}
```

**Output:**
```python
{
    "source_language": "en",
    "target_languages": ["zh-CN", "ja", "en"],
    "response": "Translated content per language...",
    "usage": {"prompt_tokens": 100, "completion_tokens": 250},
}
```

**LLM Call:** `LLMClient.chat(messages, task="translation")`
**Prompt File:** `prompts/translator_agent.md`

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      Daily Workflow                         │
│                                                             │
│  Scheduler ──▶ ResearchAgent ──▶ AnalystAgent               │
│                                  │                          │
│                              TranslatorAgent                │
│                                  │                          │
│                            KnowledgeItem (store)            │
└─────────────────────────────────────────────────────────────┘
```

Each agent receives output from the previous stage via shared `WorkflowContext.variables`. The output of one agent becomes the input of the next.

## Usage Example

```python
from backend.services.llm.client import LLMClient
from backend.services.llm.router import LLMRouter
from backend.agents.research.agent import ResearchAgent
from backend.agents.analyst.agent import AnalystAgent

router = LLMRouter()
client = LLMClient(router)

research = ResearchAgent(llm_client=client)
result = await research.execute({"topic": "AI regulation", "focus_areas": ["EU", "US"]})

analyst = AnalystAgent(llm_client=client)
analysis = await analyst.execute({"content": result["output"]["response"]})
```

## Not Implemented

- NotificationAgent
- ProjectManagerAgent
- KnowledgeAgent
- PronunciationAgent
- CrawlerAgent
- MCP integration
- API endpoints
- News crawler
