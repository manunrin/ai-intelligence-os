# LLM Gateway Architecture

## Overview

AI Intelligence OS uses a unified LLM gateway that abstracts away provider differences. All agents call through `LLMClient` → `LLMRouter` → `LLMProvider`, never directly to any specific vendor API.

```
┌─────────────────────────────────────────────────────────────┐
│                     Agent / Tool                             │
│         calls LLMClient.chat() / LLMClient.embedding()       │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    LLMClient                                 │
│  • Unified interface (chat, embedding)                       │
│  • Normalizes messages to ChatRole format                    │
│  • Passes through task/model/temperature params              │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    LLMRouter                                 │
│  • Resolves provider + model from task or explicit param     │
│  • Loads routing rules from config/models.yaml               │
│  • Executes primary provider, then fallback chain            │
│  • Tracks provider health status                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐
   │  OpenAI  │ │Anthropic │ │ Compatible│
   │  (GPT)   │ │(Claude)  │ │(Qwen/DS) │
   └──────────┘ └──────────┘ └──────────┘
          │
   ┌──────▼──────┐
   │   Ollama    │
   │ (Local)     │
   └─────────────┘
```

## Provider Design

Each provider implements `LLMProvider`:

```python
class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages, model, **kwargs) -> ChatResponse

    @abstractmethod
    async def embedding(self, text, model, **kwargs) -> EmbeddingResponse

    @abstractmethod
    async def health_check(self) -> bool
```

### Registered Providers

| Provider | Name | Models | Auth |
|----------|------|--------|------|
| OpenAI | `openai` | gpt-4o, text-embedding-3-small | API key (env) |
| Anthropic | `anthropic` | claude-sonnet-4-20250514 | API key (env) |
| Ollama | `ollama` | mistral, nomic-embed-text | Base URL (env) |
| Compatible | `compatible` | qwen-max, qwen2.5, bge-m3 | API key + base URL (env) |

The `Compatible` provider accepts any OpenAI-format API, making it work with Qwen, DeepSeek, vLLM, and similar services.

Providers are auto-registered at startup: if their API key/URL is present in environment variables, they become available. Missing credentials simply skip registration.

## Routing Design

### Resolution Order

1. **Explicit model** — `"openai/gpt-4o"` or just `"gpt-4o"` (uses default provider)
2. **Task category** — looks up `config/models.yaml` routing rules
3. **Default** — falls back to `defaults.provider` + `defaults.model`

### Configuration (`config/models.yaml`)

```yaml
defaults:
  provider: openai
  model: gpt-4o

routing:
  summary:
    - [openai, gpt-4o]
    - [anthropic, claude-sonnet-4-20250514]
  translation:
    - [compatible, qwen-max]
    - [openai, gpt-4o]
  local:
    - [ollama, mistral]
```

Each routing entry is `[provider_name, model_name]`. The first registered provider in the list is used; others form the fallback chain.

## Fallback Mechanism

When a provider call fails (network error, rate limit, model unavailable), the router automatically tries the next provider in the chain:

```
Request → primary(openai/gpt-4o) → FAIL
        → fallback(anthropic/claude-sonnet-4-20250514) → OK ✓
```

The fallback chain is derived from the same routing rule that selected the primary. Only providers that are actually registered are considered.

If ALL providers fail, a `RuntimeError` is raised with details of every failure.

## Message Format

All providers receive messages in a unified format:

```python
ChatMessage(role=ChatRole.SYSTEM, content="You are helpful.")
ChatMessage(role=ChatRole.USER, content="Explain quantum computing.")
ChatMessage(role=ChatRole.ASSISTANT, content="Quantum computing...")
```

Each provider converts this to its native format internally.

## Health Checks

`router.check_health()` returns a dict mapping provider names to boolean health status. Useful for:
- Monitoring dashboards
- Excluding unhealthy providers from routing
- Alerting on provider outages

## Not Implemented

- Actual HTTP calls to providers (marked `NotImplemented`)
- Streaming responses
- Token counting
- Cost tracking
- Rate limit handling

These will be added when connecting to real APIs.
