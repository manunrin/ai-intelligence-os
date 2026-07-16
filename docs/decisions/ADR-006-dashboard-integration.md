# Architecture Decision Record: ADR-006

## Dashboard Integration via API Envelope Unwrapping

**Status:** Accepted  
**Date:** 2026-07-16  
**Phase:** 6-C

---

### Context

The frontend dashboard (`app/page.tsx`) needed to connect to the backend REST API established in Phase 6-A/6-B. Three critical mismatches prevented any data from reaching the UI:

1. **Path mismatch:** Frontend called `/api/articles`, backend served `/api/v1/articles`.
2. **Envelope mismatch:** Backend wraps every response in `{ success, data, error }`; frontend assigned the envelope directly to React state.
3. **CORS blocked:** No `CORSMiddleware` configured; browser rejected cross-origin requests from `localhost:3000` to `localhost:8000`.

### Decision

Use a thin `unwrap<T>()` helper in the frontend API client that extracts the `data` array from the backend's `APIResponse` envelope. Configure CORS middleware on the backend using Starlette's built-in `CORSMiddleware`, sourced from `NEXT_PUBLIC_API_URL` env var with a sensible default.

### Alternatives Considered

| Alternative | Pros | Cons |
|-------------|------|------|
| Change backend to not wrap responses | Simpler frontend | Loses consistent error envelope across all endpoints |
| Frontend manually checks `res.success && res.data` each call | Explicit | Duplicated logic across every fetch call |
| Proxy through Next.js rewrites | Single origin, no CORS needed | Adds infra complexity, breaks local dev parity |
| Use `unwrap()` helper (chosen) | Zero backend changes, single reusable function | Slight abstraction layer on frontend |

### Rationale

The backend's `APIResponse[T]` envelope provides consistent structure across all endpoints (success flag, typed data, error message). Changing it would require modifying every endpoint and breaking existing tests. The `unwrap()` approach keeps the backend clean while giving the frontend a single, testable abstraction point.

### Tradeoffs

- **Added:** One new utility function (`unwrap`) in the API client
- **Removed:** None
- **Risk:** Low — `unwrap()` has a fallback path if the response is already an array
- **Performance:** Negligible — single object property access per response

### Implementation

```typescript
// frontend/lib/api.ts
export async function unwrap<T>(raw: unknown): Promise<T[]> {
  if (raw == null) return [];
  if (typeof raw === "object" && !Array.isArray(raw)) {
    const obj = raw as Record<string, unknown>;
    if ("data" in obj && Array.isArray(obj.data)) return obj.data as T[];
  }
  return Array.isArray(raw) ? (raw as T[]) : [];
}
```

```python
# backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("NEXT_PUBLIC_API_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
