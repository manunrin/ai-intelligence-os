# Phase 13 — Evaluation Intelligence

**Status:** Architecture proposal (not implemented)
**Prepared:** 2026-07-24
**Builds on:** Phase 11 (evaluation system) + Phase 12 (cost control, caching, confidence scoring)

---

## Problem Statement

Phase 11–12 deliver a functional evaluation system: every completed run gets scored via LLM with cost control and caching. But the results are **static snapshots** — stored, displayed, and forgotten. Two critical capabilities are missing:

1. **No trend analysis.** A single score of 72 tells you nothing. Is quality improving, declining, or stable?
2. **No regression detection.** A sudden drop from 90 to 55 is actionable; a drift from 78 to 75 is noise. The system can't distinguish them.

Phase 13 closes this gap by transforming evaluation data into **system-level visibility** and **proactive regression detection**.

---

## In Scope for Phase 13

| Capability | Description |
|---|---|
| Trend analytics | Rolling averages, slopes, and confidence intervals over evaluation scores per pipeline type |
| Regression detection | Statistical alerting (EWMA control chart) for significant quality drops |
| Scheduled quality analysis | Daily automated scan that recomputes trends and checks for regressions |

## Deferred to Future Phases

| Capability | Target Phase | Reason |
|---|---|---|
| Prompt versioning (`evaluator_version` column, re-scoring history) | Phase 14 | Adds schema complexity not needed for visibility |
| Automatic learning loop (prompt suggestions, criteria weight adjustment) | Phase 14 | Requires human-in-the-loop design, separate from detection |
| Behavior modification (auto-adjusting pipeline configs based on evaluations) | Phase 15 | High-risk autonomous change; needs extensive guardrails |
| Agent-to-agent comparison | Phase 14 | Low priority — current system has few agents; add when multi-agent scale exists |
| Drift detection (weekly distribution shifts) | Phase 14 | Nice-to-have; EWMA regression covers the critical case |

---

## Goals

| Goal | Description |
|------|-------------|
| **Trend visibility** | Compute rolling averages, slopes, and sample sizes over evaluation scores per pipeline type |
| **Regression alerts** | Detect statistically significant quality drops and surface them in the UI |
| **Scheduled analysis** | Automated daily scan keeps trends fresh and catches regressions without manual queries |
| **Zero new infrastructure** | All computation uses existing PostgreSQL + in-memory aggregation. No new external dependencies |

---

## Architecture

### Data Model Changes

#### New table: `evaluation_trends`

```sql
-- Migration 0013
CREATE TABLE evaluation_trends (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_type VARCHAR(32) NOT NULL,       -- 'intelligence' | 'autonomous'
    window_start  TIMESTAMPTZ NOT NULL,       -- start of time bucket
    window_end    TIMESTAMPTZ NOT NULL,       -- end of time bucket
    sample_size   INTEGER NOT NULL DEFAULT 0,
    avg_score     FLOAT NOT NULL,
    min_score     FLOAT,
    max_score     FLOAT,
    stddev_score  FLOAT,                       -- null if sample_size < 2
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_eval_trends_pipeline_window ON evaluation_trends(pipeline_type, window_start DESC);
```

Buckets: hourly (last 24h), daily (last 30d). Computed by scheduled job and on-demand trend queries.

#### New table: `evaluation_regressions`

```sql
-- Migration 0013b
CREATE TABLE evaluation_regressions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_type   VARCHAR(32) NOT NULL,
    detected_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    severity        VARCHAR(16) NOT NULL CHECK (severity IN ('warning', 'critical')),
    score_before    FLOAT NOT NULL,            -- baseline avg before regression
    score_after     FLOAT NOT NULL,            -- current avg after regression
    drop_pct        FLOAT NOT NULL,            -- percentage point drop
    sample_size     INTEGER NOT NULL,
    trigger_run_id  UUID,                      -- the run that triggered detection
    description     TEXT,                      -- human-readable summary
    acknowledged    BOOLEAN NOT NULL DEFAULT FALSE,
    resolved        BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_at     TIMESTAMPTZ,
    FOREIGN KEY (trigger_run_id) REFERENCES agent_runs(id) ON DELETE SET NULL
);

CREATE INDEX idx_eval_regressions_active ON evaluation_regressions(severity, acknowledged, resolved) WHERE resolved = FALSE;
```

Lifecycle: `detected` → `acknowledged` → `resolved`. No user attribution needed (system-generated alerts).

### Backend Components

#### 1. `EvaluationTrendService` (`backend/services/evaluation/trend_service.py`)

Core analytics engine. Reads from `agent_evaluations` table, computes aggregations.

```python
class EvaluationTrendService:
    """Compute trends and detect regressions."""

    def get_trend(self, pipeline_type: str, days: int = 30) -> TrendResult
    # Returns: per-day avg_score, sample_size, slope, stddev.
    # Queries evaluation_trends table (pre-computed buckets).
    # Falls back to on-the-fly aggregation from agent_evaluations if no buckets exist.

    def compute_buckets(self, pipeline_type: str, lookback_days: int = 30) -> int
    # Computes hourly and daily buckets, stores in evaluation_trends.
    # Called by scheduled job and on-demand via API cache-bust param.

    def detect_regressions(self, pipeline_type: str, lookback_days: int = 7) -> list[RegressionAlert]
    # Uses EWMA control chart to detect significant drops.
    # Creates evaluation_regressions records for alerts above threshold.
    # Skips already-detected regressions (checks detected_at within lookback window).
```

**Detection algorithm:** EWMA (Exponentially Weighted Moving Average) control chart.
- Smooths score noise better than simple rolling average
- Configurable sensitivity via lambda parameter (default 0.2)
- Control limits: UCL = μ₀ + Lσ, LCL = μ₀ - Lσ (L=3 for 3-sigma)
- Triggers `warning` at 2σ, `critical` at 3σ
- Minimum sample enforcement: skip detection if fewer than `min_sample_for_regression` evaluations in window

#### 2. API Endpoints (`backend/routers/evaluation.py`)

```
GET    /api/v1/evaluation/trends?pipeline=intelligence&days=30
         → { pipeline_type, buckets: [{date, avg_score, sample_size, min_score, max_score, stddev}], slope, overall_avg }

GET    /api/v1/evaluation/regressions?status=open|acknowledged|resolved
         → { regressions: [{id, severity, score_before, score_after, drop_pct, detected_at, description}] }

POST   /api/v1/evaluation/regressions/{id}/resolve
         → { id, resolved: true }

GET    /api/v1/evaluation/trends/recompute?pipeline=intelligence
         → recomputes buckets, returns count
```

All endpoints protected by auth. Rate-limited at 60/hour for GET, 20/hour for POST.

#### 3. Scheduled Quality Analysis Job

A new `ScheduledJob` type (`evaluation_quality_analysis`) runs daily at 06:00 UTC:
- Recomputes trend buckets for all pipeline types
- Runs regression detection scan across all pipeline types
- Creates `evaluation_regressions` records for new alerts
- Sends notification (via existing notification channels) if critical regressions detected
- Idempotent: skips already-detected regressions within their lookback window

### Frontend Components

#### 1. `EvaluationTrendsPanel` (`frontend/components/panels/EvaluationTrendsPanel.tsx`)

Standalone `/evaluations` workspace page.

- **Line chart**: rolling average score over time per pipeline type, filterable
- **Sample size indicators**: dot size or opacity reflects sample_size per bucket
- **Trend arrow**: ↑ improving, ↓ declining, → stable (with slope value)
- **Time range selector**: 7d / 30d / custom
- **Recompute button**: triggers on-demand bucket refresh

#### 2. `RegressionAlertRow` (`frontend/components/panels/EvaluationTrendsPanel.tsx`)

Inline section within the Evaluations page.

- Lists active (unresolved) regressions
- Severity badge (warning=critical-amber, critical=red)
- Shows score_before → score_after delta, sample size, detected date
- "Resolve" button marks as resolved
- Clickable → expands to show description and link to triggering run

#### 3. `EvaluationWorkspace` (`frontend/app/evaluations/page.tsx`)

New standalone workspace combining:
- Trend chart (primary, top half)
- Active regression alerts (secondary, below chart)
- Summary stat tiles: total evaluations, average score, open regressions count

### Configuration

```python
# backend/config.py additions
evaluation_trend_lookback_days: int = 30       # default window for trend queries
evaluation_regression_lambda: float = 0.2      # EWMA smoothing factor
evaluation_regression_sigma_threshold: float = 3.0  # 3-sigma for critical alerts
evaluation_warning_sigma_threshold: float = 2.0     # 2-sigma for warnings
evaluation_min_sample_for_trend: int = 3         # minimum runs before computing trend
evaluation_min_sample_for_regression: int = 5    # minimum runs before detecting regressions
```

---

## Implementation Plan

### Phase 13.1 — Trends & Regression Detection (Backend)

**Files:**
- `backend/alembic/versions/0013_add_evaluation_trends_and_regessions.py`
- `backend/database/models/evaluation_trend.py`
- `backend/database/models/evaluation_regression.py`
- `backend/database/models/__init__.py` (register new models)
- `backend/services/evaluation/trend_service.py` (new file)
- `backend/services/evaluation/repository.py` (add trend + regression repos)
- `backend/routers/evaluation.py` (new file)
- `backend/routers/api.py` (register evaluation router)
- `backend/metrics.py` (new metrics: `evaluation_regressions_total`, `evaluation_trend_slope`)
- `backend/services/scheduler/service.py` (register `evaluation_quality_analysis` job type)

**Tests:** 25+ unit tests covering EWMA detection, trend bucket computation, regression lifecycle, API endpoints, scheduled job dispatch.

### Phase 13.2 — Frontend

**Files:**
- `frontend/app/evaluations/page.tsx` (new workspace page)
- `frontend/components/panels/EvaluationTrendsPanel.tsx` (new component)
- `frontend/hooks/useEvaluationTrends.ts` (new hook)
- `frontend/hooks/useEvaluationRegressions.ts` (new hook)
- `frontend/lib/api.ts` (add evaluation endpoint helpers)
- `frontend/types/index.ts` (extend with EvaluationTrend, EvaluationRegression types)

**Tests:** 15+ frontend tests for trend chart rendering, regression alert interaction, workspace page routing.

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Insufficient data for statistical detection | False positives/negatives | Enforce `min_sample` thresholds; degrade gracefully to empty trend with message |
| EWMA parameter tuning | Sensitivity vs noise tradeoff | Configurable `lambda` and `sigma_threshold`; start with conservative defaults (λ=0.2, 3σ) |
| Scheduled job blocking | Long-running analysis blocks startup | Run in background task; compute buckets lazily on first access; scheduled job non-fatal |
| Chart rendering performance | Slow render with many data points | Client-side downsampling (LTTB algorithm) for windows > 100 data points |

---

## Success Criteria

1. **Trend visibility**: `/evaluations` page shows score trend with per-day averages, sample sizes, and slope indicator
2. **Regression detection**: System identifies genuine quality drops (>15 point decline over sample ≥ 5) within 24h of occurrence
3. **False positive rate**: <10% of generated regression alerts are false positives (validated against historical data)
4. **Zero regressions**: All existing tests pass; no breaking changes to Phase 11–12 APIs
5. **Performance**: Trend query returns in <500ms for 30-day window with 1000+ evaluations (uses pre-computed buckets)
6. **Scheduled job**: Daily analysis runs without blocking app startup; notifications fire for critical regressions
