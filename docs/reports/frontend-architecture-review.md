# Frontend Architecture Review — Pre-Phase 6-F.3

**Date:** 2026-07-17
**Scope:** Post F-1 (auth) and F-2 (write operations) frontend state
**Goal:** Assess readiness for Phase 6-F.3 (Agent Runtime) before starting implementation

---

## 1. Component Organization

### Shared UI Components — Good Foundation

`components/ui/` exports 7 well-designed primitives that are reused across the app:

| Component | Used By | Reusability |
|-----------|---------|-------------|
| `Button` | All pages + modals | High — variants/sizes cover all needs |
| `Card` | Dashboard, reports tab | High |
| `Badge` | Status display everywhere | High |
| `Input` | Login, register, form bodies | High |
| `Modal` | All CRUD operations | High |
| `DataTable` | Articles, knowledge, tasks, agents tabs | High |
| `StatCard` | Dashboard stats row | High |

These are clean, unopinionated primitives with consistent Tailwind v4 styling and dark mode support.

### Forms — Structural Duplication Detected

All four form bodies (`ArticleFormBody`, `TaskFormBody`, `KnowledgeFormBody`, `ReportFormBody`) share an identical structural pattern:

- **Identical props interface**: `{ initialData?, error, onError, onSubmit }`
- **Identical state shape**: `useState` per field + `useEffect` to populate from `initialData` on edit
- **Identical submit/cancel layout**: Same button positioning, same disabled logic pattern
- **Duplicated textarea styling**: Each form has a hand-copied `<textarea>` with ~90 characters of Tailwind classes that exactly duplicate the `Input` component's styling. This is the single biggest code smell — there should be a `<Textarea>` component or shared utility class.
- **Duplicated select styling**: Same inline Tailwind on `<select>` elements across all forms.

**Verdict**: Forms are not reusable as standalone pages (tightly coupled to modal pattern), but the duplication is mechanical and extractable. A generic `FormBody<T>` wrapper with field renderers would eliminate ~60% of form code.

### API Calls — Centralized Module, Scattered Usage

The `lib/api.ts` module is well-designed: fetch-based with Bearer token injection, unified error handling, and envelope unwrapping. However:

- Login and register pages bypass it entirely, calling `fetch` directly with duplicated auth/error patterns
- The dashboard re-fetches everything on mount via `Promise.all` with no caching
- No pagination support despite backend supporting it (backend returns paginated lists, frontend ignores pagination)

---

## 2. State Management

### Current: AuthContext Only

The app uses two React Contexts:
1. **AuthContext** (`lib/auth-context.tsx`) — handles token, user, SSR-safe localStorage persistence
2. **ToastContext** (`lib/toast.tsx`) — simple notification system

Both are appropriate and well-implemented. AuthContext properly syncs with the API module via `setAuthToken()`.

### Gap: Server State Lives in useState

All application data (articles, knowledge, tasks, agent runs, reports) lives as `useState` in the single `DashboardContent` component. This means:

- **No caching**: Every tab switch triggers a full `Promise.all` re-fetch of all entities
- **No stale-while-revalidate**: Data is either fresh or loading — no optimistic UX
- **No deduplication**: If two components need articles, both trigger separate fetches
- **No background refetch**: No automatic refresh when returning to a tab
- **No error boundaries**: A single failed fetch breaks the entire dashboard

### Assessment: AuthContext Is Enough for Auth, But Not for Data

For Phase 6-F.3 (Agent Runtime), which will introduce real-time agent monitoring, streaming outputs, and live status updates, the current `useState` approach will not scale. Specifically:

- Agent runs require polling or SSE/WebSocket for live status
- Multiple tabs may need shared access to agent state
- Form submissions need optimistic updates without breaking the global state

**Recommendation**: Introduce **React Query** (@tanstack/react-query) for server state. It solves caching, deduplication, background refetching, and pagination — all critical for the Agent Runtime phase. AuthContext can remain for auth state (client state vs server state distinction).

Zustand is **not needed** at this stage. React Query handles server state; client state (modal open/close, active tab) is fine with `useState`. Zustand would add complexity without solving a current problem.

---

## 3. Dashboard Scalability

### Current Architecture: Single-File Tab Router

Everything lives in `app/page.tsx` (~505 lines):
- 6 tabs controlled by `useState<TabKey>`
- No URL routing, no browser history
- All data fetched once on mount
- All modals embedded at the bottom of the file

### Problem: Agent Monitor Won't Fit

The Agent Runtime phase requires:
- Live agent status (polling every few seconds)
- Agent run detail view (click-to-expand or drill-down)
- Agent configuration/editing
- Workflow visualization
- Error logs and output inspection

This is easily 300+ additional lines of component logic, state, and rendering. The current file is already at 505 lines with basic CRUD.

### Audit Viewer Similarly Impacted

Intelligence reports currently render as simple card lists. An audit viewer would need:
- Timeline visualization
- Drill-down into individual research steps
- Knowledge item cross-referencing

### Recommended Evolution Path

| Phase | Architecture | File Count |
|-------|-------------|------------|
| Current (F-1/F-2) | Single `page.tsx` with tabs | 1 |
| Pre-F.3 (minimal refactor) | Extract each tab into its own component file | 7 |
| F.3 (Agent Runtime) | Convert tabs to URL routes | 6+ |

The minimal refactor before F.3 is **component extraction**, not route migration. Move each tab's logic into `components/dashboard/DashboardTab.tsx`, `components/articles/ArticlesTab.tsx`, etc. This keeps the tab-based UX (no URL changes needed) while making each section independently testable and maintainable.

Route-based navigation can come after F.3 is stable — it's a higher-effort change that blocks incremental delivery.

---

## 4. Type Management

### Current State: Manual Sync

Frontend types in `types/index.ts` are manually maintained TypeScript interfaces with `& Record<string, unknown>` for extensibility. Comparison with backend Pydantic schemas:

| Entity | Frontend | Backend | Sync Status |
|--------|----------|---------|-------------|
| Article | `fetched_at: string` | `fetched_at: datetime` | In sync (string accepts ISO dates) |
| Task | `dependency: string[]` | `dependency: list[str]` | In sync |
| Task | Missing `external_id`, `due_date`, `agent_run_id` | Present in `TaskCreate` | **Drift** — frontend can't create tasks with these fields |
| KnowledgeItem | In sync | In sync | OK |
| AgentRun | In sync | In sync | OK |
| IntelligenceReport | In sync | In sync | OK |

### Risks

1. **No code generation**: When backend schemas change, frontend types won't update automatically. This is the highest risk for a project with frequent backend iteration.
2. **No runtime validation**: Frontend sends whatever the form state contains. There's no Zod schema to validate input before sending to the API.
3. **String enums**: All typed fields (status, priority, kind) use `string` instead of discriminated unions. This means `priority: "critical"` compiles fine even though only `"low"|"medium"|"high"|"urgent"` are valid.

### Recommendation

For pre-F.3 preparation:
- **Add Zod schemas** for all form inputs (validation before API call)
- **Use TypeScript enum/literal types** for discriminated fields (status, priority, kind)
- **Future**: Consider `openapi-typescript` to generate frontend types from FastAPI schema. This is a Phase 6-G improvement, not a blocker for F.3.

---

## 5. Minimal Refactoring Recommendations Before Agent Runtime

### Priority 1: Extract Tab Components (1-2 hours)

Move each tab's rendering logic out of `page.tsx` into its own component file. This is the single highest-impact change:

```
components/
  dashboard/DashboardTab.tsx        # ~50 lines extracted
  articles/ArticlesTab.tsx          # ~40 lines extracted
  knowledge/KnowledgeTab.tsx        # ~35 lines extracted
  tasks/TasksTab.tsx                # ~35 lines extracted
  agents/AgentsTab.tsx              # ~25 lines extracted
  reports/ReportsTab.tsx            # ~40 lines extracted
```

**Why**: Each tab becomes independently testable. AgentRuntimeTab can be added alongside existing tabs without touching `page.tsx`'s core logic.

### Priority 2: Add Textarea and Select UI Components (30 min)

Extract the duplicated inline styling into `components/ui/Textarea.tsx` and `components/ui/Select.tsx` following the same pattern as `Input.tsx`.

**Why**: Eliminates ~40 lines of duplicated CSS across 4 form files.

### Priority 3: Add Zod Schemas for Form Validation (1 hour)

Create `schemas/` directory with Zod equivalents of all form inputs. Use in form components before API submission.

**Why**: Catches invalid data early. Provides a foundation for future `openapi-typescript` integration.

### Priority 4: Introduce React Query (4-8 hours, can span F.3)

Migrate from `useState` + `useEffect` fetch pattern to `@tanstack/react-query`. This is the biggest change but doesn't need to block F.3 start:

- AuthContext stays (client state)
- All entity data moves to React Query (server state)
- Agent polling becomes a simple `useQuery({ refetchInterval: 5000 })`

**Decision point**: Start F.3 with current state management and migrate to React Query in parallel, OR do the React Query migration first and then build Agent Runtime on top. The former is lower-risk; the latter is cleaner architecture.

### What NOT to Do Before F.3

- **Don't convert tabs to URL routes yet** — adds complexity (URL state, browser history) without enabling Agent Runtime features
- **Don't add Zustand** — not solving a current problem
- **Don't generate types from OpenAPI** — nice-to-have, not a blocker
- **Don't add testing framework** — out of scope for architecture prep

---

## Summary Scorecard

| Dimension | Rating | Notes |
|-----------|--------|-------|
| Component organization | **B+** | Good primitives, form duplication is mechanical fix |
| State management | **C** | AuthContext works; server state needs React Query before Agent Runtime |
| Dashboard scalability | **C-** | Single-file architecture cannot absorb Agent Monitor without extraction |
| Type management | **C+** | Manual sync works for now; Zod validation needed; OpenAPI codegen is future work |
| Overall readiness for F.3 | **PREP NEEDED** | Priority 1-2 extracts should happen first; React Query can be phased |
