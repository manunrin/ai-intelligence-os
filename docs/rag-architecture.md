# RAG Architecture

## Overview

The Retrieval-Augmented Generation (RAG) system enables semantic search over the knowledge base. When users ask questions about previously processed articles, the system retrieves relevant knowledge items via vector similarity and synthesizes an answer using an LLM.

```
┌─────────────────────────────────────────────────────────────┐
│                     User Query                               │
│                  "Latest AI developments"                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              RagRetriever                                    │
│                                                              │
│  1. Embed query → vector                                     │
│  2. Search Qdrant collection                                 │
│  3. Fetch full KnowledgeItems from PostgreSQL                │
│  4. Rank & return top-K                                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              RagGenerator                                    │
│                                                              │
│  1. Build context from retrieved chunks                      │
│  2. Format prompt: [context] + question                     │
│  3. Call LLM provider (e.g. gpt-4o)                         │
│  4. Return answer + sources                                  │
└─────────────────────────────────────────────────────────────┘
```

## Components

### Embedding Service (`backend/services/embedding/`)

Unified embedding interface that wraps any LLM provider's embedding capability.

**EmbeddingProvider** — Abstract interface for embedding backends.

```python
class EmbeddingProvider(ABC):
    async def embed(text: str, model: str | None) -> EmbeddingResult
    async def health_check() -> bool
```

**LLMGatewayEmbeddingProvider** — Wraps `LLMRouter.embedding()` to satisfy the provider interface.

**EmbeddingClient** — High-level client with batch support.

```python
client = EmbeddingClient(provider)
result = await client.embed("Hello world")
results = await client.embed_batch(["text1", "text2"])
```

### Vector Store (`backend/services/vector/`)

Qdrant HTTP client for vector operations.

**QdrantVectorService**:
- `ensure_collection()` — Creates collection with Cosine distance if not exists
- `upsert(points)` — Batch insert/update points with payloads
- `search(query_vector, limit, score_threshold, filter)` — Vector similarity search
- `delete(point_ids)` — Remove specific points
- `health_check()` — Verify Qdrant connectivity

Collection config:
- Name: `knowledge_items`
- Distance: `Cosine`
- Vector size: `1536` (OpenAI text-embedding-3-small default)

### RAG Retriever (`backend/services/rag/retriever.py`)

Orchestrates the retrieval phase of RAG.

**Flow**:
1. **Embed query** — Convert natural language question to vector
2. **Vector search** — Find similar points in Qdrant
3. **DB fetch** — Load full KnowledgeItem records from PostgreSQL
4. **Fallback** — If embedding/vector search fails, fall back to ILIKE keyword search on title/content

**Filters**:
- `kind_filter` — Restrict to article/report/translation
- `tag_filter` — Restrict to items with specific tag
- `score_threshold` — Minimum similarity score

**RetrievalResult**:
```python
@dataclass
class RetrievalResult:
    knowledge_id: str
    title: str
    content: str
    kind: str
    score: float | None   # Cosine similarity (higher = more similar)
    tags: list[str]
```

### RAG Generator (`backend/services/rag/generator.py`)

Synthesizes answers from retrieved context.

**Flow**:
1. Format retrieved chunks as numbered context blocks
2. Build user message: `[context] + question`
3. Call LLM provider via chat endpoint
4. Return structured result with answer + source references

**Output**:
```python
{
    "answer": "Based on the retrieved knowledge...",
    "sources": [{"knowledge_id": "...", "title": "..."}],
    "query": "Original user question"
}
```

## Complete RAG Flow

```
User Query
    │
    ▼
┌─────────────────┐
│  RagRetriever   │
│                 │
│ 1. Embed ───────┼──▶ EmbeddingClient
│                 │      │
│ 2. Search ──────┼──▶ QdrantVectorService
│                 │      │
│ 3. Fetch ───────┼──▶ SQLAlchemy (KnowledgeItem)
│                 │
│ Fallback ───────┼──▶ ILIKE keyword search
└────────┬────────┘
         │ RetrievalResult[]
         ▼
┌─────────────────┐
│ RagGenerator    │
│                 │
│ Context + Query │
│     │           │
│     ▼           │
│  LLM Chat       │
└────────┬────────┘
         │
         ▼
  Answer + Sources
```

## Usage Example

```python
# Setup
embedding_client = EmbeddingClient(LLMGatewayEmbeddingProvider(router))
vector_svc = QdrantVectorService(url="http://qdrant:6333")
await vector_svc.ensure_collection()

retriever = RagRetriever(session, embedding_client, vector_svc)
generator = RagGenerator(openai_provider, model="gpt-4o")

# Retrieve
results = await retriever.retrieve(
    query="What did OpenAI announce today?",
    limit=5,
    kind_filter="article",
)

# Generate
answer = await generator.generate(
    query="What did OpenAI announce today?",
    context=results,
    temperature=0.3,
)
```

## Integration with Pipeline

When articles flow through `ArticlePipeline`, each stage can optionally generate embeddings:

```python
pipeline = ArticlePipeline(session)
result = await pipeline.run(
    article_id,
    embed=True,          # Enable embedding generation
    embedding_client=ec, # Inject EmbeddingClient
    vector_service=vs,   # Inject QdrantVectorService
)
```

This ensures all knowledge items are immediately searchable after processing.

## Not Implemented

- MCP integration
- Notion / Asana connectors
- WeChat / Telegram notifications
- Frontend UI
- Hybrid search (BM25 + vector fusion)
- Embedding caching
- Re-ranking with cross-encoder models
- Multi-query expansion
- Source deduplication across embeddings
