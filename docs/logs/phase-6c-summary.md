# Phase 6-C: Dashboard Integration — Development Log

## Date
2026-07-16

## Major Commands

```bash
# Review phase — analyzed all frontend and backend files
find frontend -type f \( -name "*.tsx" -o -name "*.ts" \) | grep -v node_modules | sort
grep -rn "import logging\|from logging" backend --include="*.py"

# Implementation
cd frontend && npx next build   # verify production build compiles
cd ../backend && .venv/bin/python -c "from backend.main import create_app"  # verify imports

# Testing
.venv/bin/python -m pytest tests/ -q
```

## Important Decisions

1. **Frontend unwrap pattern chosen over backend change** — The APIResponse envelope is a deliberate architectural choice for consistency. Adding a thin `unwrap()` helper on the frontend is cheaper than modifying every endpoint.

2. **CORS via Starlette middleware** — FastAPI's `add_middleware` with `CORSMiddleware` is the standard approach. Origin sourced from `NEXT_PUBLIC_API_URL` env var with `http://localhost:3000` default.

3. **Table component simplified generics** — The original `DataTable<T>` used an undeclared type parameter `T`. Simplified to `unknown[]` which matches how all consumers use it.

4. **Type aliases over interfaces** — Frontend types used `interface X { ... } & Record<string, unknown>` which is invalid TypeScript. Converted to `type X = { ... } & Record<string, unknown>` which compiles correctly.

## Problems Encountered

### Problem 1: Dashboard showed empty data
**Root cause:** Three simultaneous issues — wrong API paths (`/api/` vs `/api/v1/`), envelope not unwrapped, CORS blocked.
**Solution:** Fixed all three in one pass.

### Problem 2: Next.js build failed on Table component
**Root cause:** `interface TableProps { data: T[]; ... }` references `T` before it's declared. `DataTable<T>` declares the generic but `TableProps` doesn't.
**Solution:** Removed generic entirely; `DataTable` accepts `unknown[]` which covers all consumer types.

### Problem 3: Next.js build failed on types/index.ts
**Root cause:** `export interface Article { ... } & Record<string, unknown>` is invalid syntax. Intersection on interface declarations requires type aliases.
**Solution:** Changed all `interface` to `type` aliases with trailing semicolons.

### Problem 4: Badge variant type errors
**Root cause:** Color maps included `"muted"` but the `Record` type didn't declare it, causing TS to reject the assignment.
**Solution:** Added `"muted"` to the union type in each color map, removed redundant cast expressions.

## Test Results

| Suite | Passed | Skipped | Failed |
|-------|--------|---------|--------|
| Unit (Python) | 108 | 1 | 0 |
| Integration (Python) | 30 | 5 | 0 |
| **Total** | **138** | **5** | **0** |

Next.js production build: **Compiled successfully**.

## Files Modified

| File | Change |
|------|--------|
| `backend/main.py` | Added CORS middleware |
| `frontend/lib/api.ts` | Added `unwrap()`, improved error parsing |
| `frontend/app/page.tsx` | Fixed API paths, added unwrap calls, fixed TS type errors |
| `frontend/components/ui/Table.tsx` | Fixed undeclared generic `T` |
| `frontend/types/index.ts` | Converted interfaces to type aliases |

## Files Created

| File | Purpose |
|------|---------|
| `docs/CHANGELOG.md` | Project changelog |
| `docs/decisions/ADR-006-dashboard-integration.md` | Architecture decision record |
