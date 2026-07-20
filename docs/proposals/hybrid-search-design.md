# Phase 9.5 — Hybrid Search Design Proposal

**Date:** 2026-07-19  
**Status:** Design review  
**Scope:** `backend/services/rag/retriever.py`, `backend/services/vector/`, `POST /api/v1/knowledge/search`

---

## 1. Current State

The retrieval pipeline is **semantic-only**:

```
Query → EmbeddingClient.embed(query) → QdrantVectorService.search(dense_vector) → DB fetch → Ranked by cosine similarity
```

Keyword search exists only as a **failure fallback** in `RagRetriever._db_search()` (`retriever.py:120-153`). It uses naive PostgreSQL `ILIKE` substring matching against `title` and `content`, with no tokenization, no relevance scoring, and no BM25.

### What is missing

| Capability | Present? | Notes |
|-----------|----------|-------|
| Dense vector search | Yes | Qdrant Cosine, 1536-dim |
| Sparse vector / BM25 | No | No sparse vector config, no Elasticsearch/Whoosh |
| Hybrid fusion | No | Keyword search is fallback only, never combined with vector |
| Re-ranking | No | Over-fetch x2 provides headroom but no explicit re-ranker |
| Text indexing | No | Qdrant collection has dense vectors only |
| Tokenization | No | `_db_search` matches raw query string as substring |

### Infrastructure constraints

- `QdrantVectorService` is a thin `httpx` REST client with no base interface.
- Collection config (`ensure_collection`) creates only dense vectors: `{"vectors": {"size": 1536, "distance": "Cosine"}}`.
- Qdrant supports hybrid via sparse vectors (since v1.7+), but no sparse embedding provider is configured. All providers return dense vectors only.
- The `KnowledgeItem` ORM model has no sparse vector column.
- PostgreSQL is available and already used for keyword fallback.

---

## 2. Recommended Approach: Application-Level Hybrid (Path B)

Two implementation paths were evaluated:

### Path A — Qdrant-Native Hybrid

Requires adding sparse vector configuration to Qdrant, a sparse embedding provider, multi-vector upsert, and Qdrant's hybrid query API. This is architecturally elegant but requires Qdrant >= 1.7, a new sparse embedding provider, schema changes, and data migration of all existing points.

**Verdict: Defer.** Too much infrastructure change for a Phase 9.5 task.

### Path B — Application-Level Hybrid (Recommended)

Keep dense Qdrant search as-is. Elevate the existing PostgreSQL keyword path from "failure fallback" to a first-class parallel retrieval branch. Fuse results at the application layer using Reciprocal Rank Fusion (RRF).

**Why this approach:**
- No Qdrant schema changes required.
- No new embedding providers needed.
- Leverages PostgreSQL `ts_rank` / `to_tsvector` for real BM25-like ranking.
- Minimal API surface change — same endpoint, same request schema.
- Can be rolled out incrementally with a feature flag.
- Falls back cleanly if either branch fails independently.

---

## 3. BM25 Keyword Search Integration

Replace the current `ILIKE` fallback with PostgreSQL full-text search.

### Implementation

Use PostgreSQL `ts_rank` with `plainto_tsquery` for tokenized keyword search:

```sql
SELECT id, title, content, kind, tags,
       ts_rank(to_tsvector('english', title || ' ' || content),
               plainto_tsquery('english', $1)) AS keyword_score
FROM knowledge_items
WHERE to_tsvector('english', title || ' ' || content) @@ plainto_tsquery('english', $1)
ORDER BY keyword_score DESC
LIMIT $2
```

This provides:
- **Tokenization** — splits query into lexemes, handles stemming.
- **Relevance scoring** — `ts_rank` approximates BM25 behavior (term frequency weighted by position).
- **No new dependencies** — uses built-in PostgreSQL extensions.

### Optional enhancement: custom weight by field

Title matches are more meaningful than content matches. Use a weighted `tsvector`:

```python
vector = f"'A':{title} 'B':{content}"
weights = [0.8, 0.4]  # title gets higher weight
```

Or use PostgreSQL `setweight` on the tsvector columns directly.

### File to modify

- `backend/services/rag/retriever.py` — replace `_db_search()` with a `ts_rank`-based implementation. Add a new method `_keyword_search()` that returns `(results, scores)`.

---

## 4. Vector + Keyword Fusion Strategy

### Algorithm: Reciprocal Rank Fusion (RRF)

RRF is the standard for combining ranked result lists without requiring score normalization across heterogeneous ranking systems:

```
score(item) = Σ(1 / (k + rank_i(item)))
```

Where `k` is a smoothing constant (typically 60) and `rank_i` is the item's position in list `i`.

**Why RRF over weighted score merging:**
- Dense cosine similarity and `ts_rank` live on different scales (0–1 vs. arbitrary magnitude). Normalizing them reliably is hard.
- RRF only needs ordinal ranks, which are robust across ranking functions.
- RRF naturally handles the case where one branch returns fewer results than the other.
- The `k=60` default is well-established (van Rijsbergen, 2004).

### Fusion parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `k` (RRF constant) | 60 | Standard default |
| `dense_weight` | 1.0 | Base weight for vector results |
| `keyword_weight` | 0.8 | Slightly lower — keyword matches are precise but narrow |
| `dense_limit` | requested_limit * 2 | Already over-fetching; keep for re-ranking headroom |
| `keyword_limit` | requested_limit * 2 | Same over-fetch for keyword branch |
| `final_limit` | requested_limit | Truncate after fusion |

### Tuning knobs exposed to API

Add optional `dense_weight` and `keyword_weight` to `SearchRequest` so users can tilt the fusion. Default both to 1.0. This keeps the API flexible without forcing a single hardcoded ratio.

---

## 5. Ranking Algorithm

### Pipeline

```
1. Query → EmbeddingClient.embed(query)           [dense branch]
2. Query → PostgreSQL ts_rank                     [keyword branch]
3. Deduplicate by knowledge_id across both branches
4. Compute RRF score = dense_weight * rrf(dense_ranks) + keyword_weight * rrf(keyword_ranks)
5. Apply kind_filter / tag_filter as post-filter
6. Sort descending by fused score
7. Truncate to requested limit
```

### Branch failure handling

Each branch must fail independently without killing the entire search:

| Failure | Behavior |
|---------|----------|
| Embedding generation fails | Skip dense branch; return keyword results only |
| Qdrant unavailable | Skip dense branch; return keyword results only |
| PostgreSQL full-text search fails | Skip keyword branch; return dense results only |
| Both fail | Return empty results (same as today) |

This is strictly better than the current behavior, where any failure collapses to the naive `ILIKE` fallback.

### Filter application

Apply `kind_filter` and `tag_filter` **after** fusion rather than inside individual branches. This avoids filtering out items that would have been relevant through the other branch. Filters are cheap at the ID level.

---

## 6. API Changes

### Backward-compatible additions to `SearchRequest`

```python
class SearchRequest(BaseModel):
    query: str
    limit: int = Field(default=5, ge=1, le=50)
    kind_filter: Optional[str] = None
    tag_filter: Optional[str] = None
    score_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    # New fields (optional, backward compatible)
    dense_weight: float = Field(default=1.0, ge=0.0, le=10.0)
    keyword_weight: float = Field(default=0.8, ge=0.0, le=10.0)
    hybrid: bool = Field(default=True)  # When False, use dense-only (current behavior)
```

### Backward-compatible additions to `SearchResult`

```python
class SearchResult(BaseModel):
    knowledge_id: str
    title: str
    content: str
    kind: str
    score: Optional[float] = None        # Existing: cosine score (dense-only mode)
    hybrid_score: Optional[float] = None # New: RRF fused score
    dense_score: Optional[float] = None  # New: original cosine score, when present
    keyword_score: Optional[float] = None # New: ts_rank score, when present
    tags: list[str] = []
```

### Response semantics

- **Default (`hybrid=True`)**: Returns fused `hybrid_score`. Individual component scores included when available.
- **`hybrid=False`**: Dense-only path, identical to current behavior. `score` contains cosine similarity.
- **Score threshold**: Applied to `hybrid_score` in hybrid mode, or `score` in dense-only mode.

### Frontend impact

The frontend `useKnowledgeSearchMutation` already reads `data.results` and maps to `KnowledgeSearchResult`. Adding optional `hybrid_score` / `dense_score` / `keyword_score` fields is backward-compatible — the frontend will simply ignore unknown fields. No UI changes required for the initial rollout.

If we want to expose fusion quality visually later, we can add a small "matched by vector", "matched by keywords", or "matched by both" indicator to the search result card.

---

## 7. Migration Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| `ts_rank` scoring differs from BM25 | Medium | Acceptable approximation; `ts_rank` correlates well with BM25 for short queries |
| Performance regression from dual search | Medium | Both branches are bounded by `limit*2`; index `to_tsvector` on `title`+`content` if needed |
| Score distribution shift breaks existing clients | Low | `hybrid_score` is additive; items still sorted descending; `score_threshold` still works |
| Qdrant downtime now affects fewer results | Low | Previously a hard failure → keyword fallback. Now dense branch fails independently, keyword branch still works |
| Empty corpus edge case | Low | Both branches return empty → same behavior as today |
| Existing tests assume ILIKE fallback | Medium | Need to update `test_knowledge_service.py` mocks; the new `_keyword_search` should be mockable like `_db_search` |

### Indexing consideration

PostgreSQL full-text search on large tables benefits from a GIN index:

```sql
CREATE INDEX IF NOT EXISTS idx_knowledge_fts
ON knowledge_items USING gin(to_tsvector('english', title || ' ' || content));
```

This is a one-time migration. Without it, full-table scans could become slow as the knowledge base grows. Add to Alembic migration.

---

## 8. Implementation Plan

### Step 1 — Replace `_db_search` with `ts_rank` keyword search

**File:** `backend/services/rag/retriever.py`

- Add `_keyword_search()` using SQLAlchemy `func.ts_rank` + `func.to_tsvector` + `func.plainto_tsquery`.
- Keep `_db_search` as a compatibility wrapper or remove it.
- Each branch returns `list[RetrievalResult]` with a `score` from its own ranking function.

### Step 2 — Add fusion method

**File:** `backend/services/rag/retriever.py`

- Add `_fuse_results(dense, keyword, dense_weight, keyword_weight)` using RRF.
- Deduplicate by `knowledge_id`.
- Apply filters post-fusion.
- Sort by fused score descending.

### Step 3 — Update `retrieve()` to run both branches in parallel

**File:** `backend/services/rag/retriever.py`

- Use `asyncio.gather` to run dense and keyword searches concurrently.
- Catch exceptions per-branch so one failure doesn't kill the other.
- If both fail, return empty (unchanged).
- If one succeeds, return that branch alone (unchanged).
- If both succeed, fuse and return.

### Step 4 — Extend schemas

**Files:** `backend/schemas/search.py`

- Add `dense_weight`, `keyword_weight`, `hybrid` to `SearchRequest`.
- Add `hybrid_score`, `dense_score`, `keyword_score` to `SearchResult`.

### Step 5 — Update router

**File:** `backend/routers/knowledge.py`

- Pass new parameters to `retriever.retrieve()`.
- No response model changes needed (Pydantic ignores extra fields on response if not declared, or we declare them).

### Step 6 — Add Alembic migration for FTS index

**File:** `backend/alembic/versions/`

- Create GIN index on the concatenated searchable text.

### Step 7 — Tests

- Unit test RRF fusion with synthetic ranked lists.
- Unit test branch failure isolation (mock embedding or PG failure).
- Integration test: keyword-only query that vector search misses (e.g., exact acronym match).
- Integration test: hybrid query where both branches agree.

---

## 9. Alternative: True BM25 with Whoosh/Tantivy

If strict BM25 is required instead of PostgreSQL `ts_rank`, a Python BM25 library (e.g., `rank-bm25`) could be added as an in-memory indexer over the knowledge base. However:

- Requires maintaining a separate index synced with PostgreSQL.
- Adds a dependency and synchronization complexity.
- `ts_rank` is sufficient for the current scale and avoids index drift.

**Recommendation: defer true BM25 until the corpus exceeds what PostgreSQL FTS handles comfortably.**
