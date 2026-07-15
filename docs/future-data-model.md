# Future Data Model — Planned Tables

The following tables are planned for future phases. They are documented here for reference but must NOT be implemented until explicitly requested.

---

## agent_evaluations

Purpose: Track agent performance metrics and quality scores over time.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| agent_run_id | UUID | FK→agent_runs.id | Execution being evaluated |
| evaluator_agent_id | UUID | FK→agents.id | Agent that performed evaluation |
| quality_score | FLOAT | CHECK ≥ 0 AND ≤ 10 | Overall quality rating |
| accuracy_score | FLOAT | CHECK ≥ 0 AND ≤ 10 | Factual accuracy rating |
| completeness_score | FLOAT | CHECK ≥ 0 AND ≤ 10 | Coverage assessment |
| criteria | JSONB | NOT NULL | Evaluation criteria breakdown |
| notes | TEXT | | Free-text evaluator comments |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Evaluation timestamp |

**Why:** Enables agent self-improvement loops and quality gate enforcement.

---

## feedback

Purpose: Collect user feedback on intelligence outputs and agent behavior.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| user_id | VARCHAR(128) | NOT NULL | Feedback author |
| target_type | VARCHAR(32) | NOT NULL | article \| report \| task \| agent_run |
| target_id | UUID | NOT NULL | Referenced entity ID |
| rating | SMALLINT | CHECK ≥ 1 AND ≤ 5 | 1–5 star rating |
| comment | TEXT | | User-provided feedback text |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Submission time |

**Why:** Closes the human-in-the-loop feedback cycle for continuous improvement.

---

## model_versions

Purpose: Track which LLM models were used at each point in time.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| provider | VARCHAR(64) | NOT NULL | openai \| anthropic \| google |
| model_name | VARCHAR(128) | NOT NULL | e.g. gpt-4o, claude-sonnet-4-20250514 |
| alias | VARCHAR(64) | | Human-readable label |
| capabilities | JSONB | | Supported features (tools, vision, etc.) |
| is_active | BOOLEAN | DEFAULT true | Whether this model is routable |
| deprecated_at | TIMESTAMPTZ | | When this model was retired |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | Registration time |

**Why:** LiteLLM routing needs a registry of available models; enables audit trail of which model produced which output.

---

## Implementation Guard

These tables are **documented only**. Do not create:
- SQLAlchemy models in `backend/database/models/`
- Migration entries in Alembic
- API endpoints referencing them
- Any code that queries these tables

They become active only when a phase explicitly requests their implementation.
