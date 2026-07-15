"""AI Operations Agent Architecture.

This document describes the four operations agents, their responsibilities,
data flow through the knowledge pipeline, and design decisions.

## Agent Responsibilities

### KnowledgeAgent
Converts analyzed intelligence content into structured knowledge entries.
Extracts summaries, key points, tags, and knowledge type classification.
Uses LLM to categorize content (tutorial, research, news, etc.).

### PronunciationAgent
Generates multilingual pronunciation data for learning cards.
Supports Chinese (pinyin), English (IPA), and Japanese (kana + romaji).
Reads knowledge summaries and produces structured pronunciation guides.

### ProjectManagerAgent
Converts knowledge and goals into actionable project plans.
Produces prioritized task lists with dependencies.
Does NOT call Asana or any external API — only outputs structured plans.

### NotificationAgent
Generates Markdown-formatted daily digests from news, knowledge, and tasks.
Supports multiple output channels (WeChat, Telegram, Email).
Does NOT send messages — only generates content for delivery.

## Data Flow

```
Article (ingested)
  ↓
ResearchAgent (findings)
  ↓
AnalystAgent (analysis)
  ↓
TranslatorAgent (translation)
  ↓
KnowledgeAgent (structured knowledge)
  ↓
PronunciationAgent (learning cards)
  ↓
ProjectManagerAgent (actionable tasks)
  ↓
NotificationAgent (daily digest)
  ↓
[MCP Layer → Notion/Asana/WeChat/Telegram]
```

Each agent reads from shared state, writes its output, and passes control
to the next agent. Errors are captured but do not stop the pipeline.

## Why Agents Don't Call External APIs Directly

1. **Separation of concerns**: Agents focus on reasoning and transformation.
   External system integration is handled by the MCP layer.

2. **Testability**: Mock LLM responses are sufficient for unit testing.
   No network calls needed.

3. **Flexibility**: Swap external systems without touching agent code.
   The MCP registry routes tool calls transparently.

4. **Security**: Credentials live in server config, not agent code.

## Design Decisions

- All agents extend `AgentBase` for uniform lifecycle management
- Schemas use Pydantic for validation at agent boundaries
- Prompt templates are external `.md` files loaded at runtime
- Output parsing is graceful — falls back to structured defaults on failure
- The pipeline composes with the existing intelligence graph via shared state
