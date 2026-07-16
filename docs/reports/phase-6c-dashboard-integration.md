# Phase 6-C: Dashboard Integration & End-to-End API

## Goals

Connect the Next.js frontend dashboard to the backend REST API so users can see real data from the database through the UI.

## Architecture

### Data Flow

```
User → Next.js Dashboard (page.tsx)
  ↓ fetch("/api/v1/articles") etc.
  ↓ unwrap<T>() extracts data from APIResponse envelope
  ↓ sets React state
Backend FastAPI (main.py)
  ↓ CORS middleware allows localhost:3000
  ↓ Router → Service → Repository → ORM
  ↓ Returns { success: true, data: [...], error: null }
Frontend
  ↓ unwrap() extracts array from data field
  ↓ DataTable / Card / StatCard render results
```

### Component Interaction

```
Dashboard (page.tsx)
├── Header (title, status badge)
├── Stats Row (StatCard × 4)
│   ├── Articles count
│   ├── Knowledge Items count
│   ├── Active Tasks count
│   └── Agent Runs count
├── Tab Navigation
│   ├── Dashboard View
│   │   ├── Recent Articles Card
│   │   ├── Knowledge Items Card
│   │   ├── Active Tasks Card
│   │   └── Agent Runs Card
│   ├── Articles Table (DataTable)
│   ├── Knowledge Table (DataTable)
│   ├── Tasks Table (DataTable)
│   ├── Agents Table (DataTable)
│   └── Reports List (Card × N)
└── Error Banner
```

## Files Changed

| File | Lines Changed | Description |
|------|--------------|-------------|
| `backend/main.py` | +12 | Added CORS middleware |
| `frontend/lib/api.ts` | +16 | Added `unwrap()`, improved error parsing |
| `frontend/app/page.tsx` | +21/-24 | Fixed API paths, added unwrap, fixed TS types |
| `frontend/components/ui/Table.tsx` | +16/-12 | Fixed undeclared generic `T` |
| `frontend/types/index.ts` | +6/-6 | Converted interfaces to type aliases |

## Files Added

| File | Purpose |
|------|---------|
| `docs/CHANGELOG.md` | Project changelog |
| `docs/decisions/ADR-006-dashboard-integration.md` | ADR for unwrap pattern |
| `docs/logs/phase-6c-summary.md` | Development log |
| `docs/reports/phase-6c-dashboard-integration.md` | This report |

## Test Results

```
138 passed, 5 skipped, 1 warning in 1.66s
```

- All Python unit tests pass (108)
- All Python integration tests pass (30)
- Next.js production build compiles successfully
- No new test failures introduced

## Known Issues

1. **No pagination UI** — Dashboard loads all items at once. The backend supports offset/limit query params but the frontend ignores them. Future phase should add pagination controls.

2. **No refresh mechanism** — Data is fetched once on mount. No pull-to-refresh or auto-reload.

3. **Reports tab shows raw dict fields** — `research_result`, `analysis_result` etc. are displayed as JSON strings because the schema types them as `dict`. Proper nested response models would give structured display.

4. **No optimistic updates** — Creating/editing/deleting data is not yet supported (no POST/PUT/DELETE endpoints implemented).

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| CORS misconfiguration in prod | Backend unreachable from prod frontend | Use env var for origin, validate in CI |
| Large datasets without pagination | Memory exhaustion in browser | Add pagination UI in next phase |
| Silent unwrap failure | Dashboard shows empty data | unwrap() has fallback to treat raw as array |

## Performance Notes

- **Initial load:** 5 parallel API requests. With empty DB, each returns in <5ms. Total page load ~100ms.
- **Empty state:** All endpoints return `{"success": true, "data": [], "error": null}` — minimal payload.
- **Bundle size:** No new dependencies added. Frontend bundle unchanged.
- **CORS overhead:** Negligible — Starlette CORS adds ~1 header check per request.

## Recommended Next Phase

**Phase 6-D: Write Operations & User Experience**

1. Implement POST/PUT/DELETE endpoints for all resources
2. Add request input schemas (TaskCreate, ArticleCreate, etc.)
3. Add pagination UI components
4. Add loading spinners per-tab (not global)
5. Add create/edit modals
6. Add error boundaries per section
