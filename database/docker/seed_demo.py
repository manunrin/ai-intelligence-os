"""Idempotent demo/seed data for AI Intelligence OS v0.1.0 Beta.

Usage inside Docker:
    docker compose exec backend python -m database.docker.seed_demo

Usage locally (requires .env + installed deps):
    DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_intelligence_os \
    python database/docker/seed_demo.py

This script is safe to run multiple times — it only creates records that do not
already exist. It never overwrites user-created data.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import uuid
from datetime import datetime, timedelta, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Minimal ORM imports — avoid pulling in the full app stack
# ---------------------------------------------------------------------------
sys.path.insert(0, ".")

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text

from backend.database.models.agent import Agent
from backend.database.models.agent_run import AgentRun
from backend.database.models.agent_stage_progress import AgentStageProgress
from backend.database.models.article import Article
from backend.database.models.intelligence_report import IntelligenceReport
from backend.database.models.knowledge_item import KnowledgeItem
from backend.database.models.source import Source
from backend.database.models.task import Task

# ---------------------------------------------------------------------------
# Demo data definitions
# ---------------------------------------------------------------------------

SOURCES = [
    {"name": "Reuters", "url": "https://www.reuters.com/", "kind": "news", "source_type": "official"},
    {"name": "arXiv", "url": "https://arxiv.org/", "kind": "paper", "source_type": "official"},
    {"name": "GitHub Blog", "url": "https://github.blog/", "kind": "news", "source_type": "community"},
    {"name": "Anthropic Research", "url": "https://www.anthropic.com/research", "kind": "paper", "source_type": "official"},
]

AGENTS = [
    {
        "name": "analyst",
        "display_name": "Analyst Agent",
        "description": "Produces intelligence reports from articles and knowledge items.",
        "graph_def": {"type": "langgraph", "version": "1", "nodes": ["ingest", "analyze", "report"]},
        "version": "1.0.0",
        "enabled": True,
    },
    {
        "name": "project_manager",
        "display_name": "Project Manager Agent",
        "description": "Breaks down goals into actionable tasks with priorities and deadlines.",
        "graph_def": {"type": "langgraph", "version": "1", "nodes": ["plan", "decompose", "assign"]},
        "version": "1.0.0",
        "enabled": True,
    },
    {
        "name": "knowledge",
        "display_name": "Knowledge Agent",
        "description": "Extracts structured knowledge from unstructured documents.",
        "graph_def": {"type": "langgraph", "version": "1", "nodes": ["extract", "embed", "store"]},
        "version": "1.0.0",
        "enabled": True,
    },
]

ARTICLES = [
    {
        "title": "Advances in Multimodal LLM Reasoning",
        "summary": "Survey of recent progress in multimodal large language models combining text, vision, and code understanding.",
        "content": "Recent work demonstrates that fine-tuning on multimodal instruction datasets significantly improves reasoning across modalities...",
        "language": "en",
        "status": "processed",
        "metadata_": {"authors": ["Demo Author"], "tags": ["llm", "multimodal"]},
    },
    {
        "title": "Vector Databases at Scale: Lessons from Production",
        "summary": "Practical experiences deploying vector search systems handling billions of embeddings.",
        "content": "Production deployments of vector databases reveal critical trade-offs between recall, latency, and storage cost...",
        "language": "en",
        "status": "processed",
        "metadata_": {"authors": ["Demo Author"], "tags": ["vector-db", "production"]},
    },
    {
        "title": "Agent Orchestration Patterns in LangGraph",
        "summary": "Common patterns for building multi-agent systems using LangGraph's state machine primitives.",
        "content": "LangGraph provides a declarative way to define agent workflows as state machines with conditional edges...",
        "language": "en",
        "status": "raw",
        "metadata_": {"authors": ["Demo Author"], "tags": ["agents", "langgraph"]},
    },
]

KNOWLEDGE_ITEMS = [
    {
        "title": "LLM Fallback Strategy",
        "content": "When the primary LLM provider fails, the router attempts configured fallback providers in order. Each attempt is logged with provider name and error type.",
        "kind": "pattern",
        "tags": ["llm", "resilience", "fallback"],
    },
    {
        "title": "Vector Search Indexing Pipeline",
        "content": "Documents are chunked by semantic boundaries, embedded via text-embedding-3-large, and stored in Qdrant with metadata filters for source tracking.",
        "kind": "pipeline",
        "tags": ["vector-search", "embedding", "qdrant"],
    },
    {
        "title": "Agent Stage Progress Tracking",
        "content": "Each agent run emits stage completion events recorded in agent_stages_total. Stages include initializing, planning, executing, validating, and completing.",
        "kind": "concept",
        "tags": ["agent", "observability", "stages"],
    },
    {
        "title": "Prometheus Metric Label Cardinality Limits",
        "content": "HTTP request metrics use path normalization to replace UUID segments with <uuid> placeholders, preventing cardinality explosion from dynamic routes.",
        "kind": "best-practice",
        "tags": ["metrics", "prometheus", "cardinality"],
    },
]

TASKS = [
    {
        "title": "Review Qdrant collection schema",
        "description": "Verify vector dimension and index type match current embedding model configuration.",
        "status": "pending",
        "priority": "high",
    },
    {
        "title": "Update LLM routing rules",
        "description": "Add support for new compatible API providers in models.yaml routing configuration.",
        "status": "in_progress",
        "priority": "medium",
    },
    {
        "title": "Implement rate limiting for MCP endpoints",
        "description": "Add per-client rate limits to Notion and GitHub MCP integrations.",
        "status": "pending",
        "priority": "low",
    },
    {
        "title": "Add Grafana alert notifications",
        "description": "Configure Alertmanager integration to send critical alerts to Slack webhook.",
        "status": "completed",
        "priority": "high",
    },
]

REPORTS = [
    {
        "title": "Q3 AI Infrastructure Review",
        "body": "Analysis of LLM provider reliability, vector search performance trends, and agent runtime stability over the past quarter.",
        "category": "review",
        "importance_score": 8.5,
        "generated_by": "analyst",
    },
    {
        "title": "Observability Maturity Assessment",
        "body": "Current state of metrics collection, distributed tracing, and alerting coverage across all platform services.",
        "category": "assessment",
        "importance_score": 7.0,
        "generated_by": "analyst",
    },
]

AGENT_RUNS = [
    {
        "status": "completed",
        "stage": "completed",
        "input_payload": {"task": "analyze_articles", "count": 3},
        "output_payload": {"reports_generated": 1, "articles_processed": 3},
        "duration_ms": 45200,
    },
    {
        "status": "completed",
        "stage": "completed",
        "input_payload": {"task": "decompose_goal", "goal": "improve_search"},
        "output_payload": {"tasks_created": 4, "priority_breakdown": {"high": 1, "medium": 2, "low": 1}},
        "duration_ms": 12800,
    },
    {
        "status": "failed",
        "stage": "executing",
        "input_payload": {"task": "extract_knowledge", "document_count": 10},
        "error_message": "Embedding provider timeout after 30s",
        "duration_ms": 30000,
    },
]


# ---------------------------------------------------------------------------
# Seeding logic
# ---------------------------------------------------------------------------


async def seed_sources(session: AsyncSession) -> dict[str, uuid.UUID]:
    """Create demo sources. Returns mapping of name → id."""
    existing = await session.execute(text("SELECT id, name FROM sources WHERE name = ANY(:names)"))
    rows = {r.name: r.id for r in existing.fetchall()}

    created = {}
    for src in SOURCES:
        if src["name"] not in rows:
            s = Source(**src)
            session.add(s)
            await session.flush()
            rows[src["name"]] = s.id
        created[src["name"]] = rows[src["name"]]

    log.info("Sources: %d total (%d new)", len(created), sum(1 for k in SOURCES if k["name"] not in rows))
    return created


async def seed_agents(session: AsyncSession) -> dict[str, uuid.UUID]:
    """Create demo agents. Returns mapping of name → id."""
    existing = await session.execute(text("SELECT id, name FROM agents WHERE name = ANY(:names)"))
    rows = {r.name: r.id for r in existing.fetchall()}

    created = {}
    for ag in AGENTS:
        if ag["name"] not in rows:
            a = Agent(**ag)
            session.add(a)
            await session.flush()
            rows[ag["name"]] = a.id
        created[ag["name"]] = rows[ag["name"]]

    log.info("Agents: %d total (%d new)", len(created), sum(1 for k in AGENTS if k["name"] not in rows))
    return created


async def seed_articles(session: AsyncSession, sources: dict[str, uuid.UUID]) -> list[uuid.UUID]:
    """Create demo articles linked to sources."""
    ids: list[uuid.UUID] = []
    now = datetime.now(timezone.utc)

    for art in ARTICLES:
        # Use first available source
        source_id = next(iter(sources.values()))
        a = Article(
            **art,
            source_id=source_id,
            published_at=now - timedelta(days=len(ids) * 7),
        )
        session.add(a)
        await session.flush()
        ids.append(a.id)

    log.info("Articles: %d seeded", len(ids))
    return ids


async def seed_knowledge(session: AsyncSession) -> list[uuid.UUID]:
    """Create demo knowledge items."""
    ids: list[uuid.UUID] = []
    for item in KNOWLEDGE_ITEMS:
        ki = KnowledgeItem(**item)
        session.add(ki)
        await session.flush()
        ids.append(ki.id)

    log.info("Knowledge items: %d seeded", len(ids))
    return ids


async def seed_tasks(session: AsyncSession) -> list[uuid.UUID]:
    """Create demo tasks."""
    ids: list[uuid.UUID] = []
    for task in TASKS:
        t = Task(**task)
        session.add(t)
        await session.flush()
        ids.append(t.id)

    log.info("Tasks: %d seeded", len(ids))
    return ids


async def seed_reports(session: AsyncSession, articles: list[uuid.UUID]) -> list[uuid.UUID]:
    """Create demo intelligence reports."""
    ids: list[uuid.UUID] = []
    for rpt in REPORTS:
        r = IntelligenceReport(**rpt, article_ids=articles[: min(2, len(articles))])
        session.add(r)
        await session.flush()
        ids.append(r.id)

    log.info("Reports: %d seeded", len(ids))
    return ids


async def seed_agent_runs(session: AsyncSession, agents: dict[str, uuid.UUID]) -> list[uuid.UUID]:
    """Create demo agent runs."""
    ids: list[uuid.UUID] = []
    now = datetime.now(timezone.utc)

    for i, run_data in enumerate(AGENT_RUNS):
        agent_name = list(agents.keys())[i % len(agents)]
        ar = AgentRun(
            agent_id=agents[agent_name],
            status=run_data["status"],
            stage=run_data["stage"],
            input_payload=run_data["input_payload"],
            output_payload=run_data.get("output_payload"),
            error_message=run_data.get("error_message"),
            duration_ms=run_data["duration_ms"],
            started_at=now - timedelta(hours=(len(ids) + 1) * 6),
            finished_at=(
                now - timedelta(hours=(len(ids) + 1) * 6 - run_data["duration_ms"] / 3600000)
                if run_data["status"] == "completed"
                else None
            ),
        )
        session.add(ar)
        await session.flush()
        ids.append(ar.id)

        # Add a stage progress record
        sp = AgentStageProgress(
            run_id=ar.id,
            stage_name="initializing",
            sequence=1,
            status="completed",
            started_at=ar.started_at,
            completed_at=ar.started_at + timedelta(seconds=1),
        )
        session.add(sp)

    log.info("Agent runs: %d seeded", len(ids))
    return ids


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def run_seed(database_url: str | None = None) -> None:
    """Execute the full seed pipeline."""
    import os

    url = database_url or os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_intelligence_os")

    # Create engine — use sync driver for alembic-compatible URL, convert if needed
    if "asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://")

    engine = create_async_engine(url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with factory() as session:
            log.info("Connected to database — starting seed")

            sources = await seed_sources(session)
            agents = await seed_agents(session)
            articles = await seed_articles(session, sources)
            await seed_knowledge(session)
            await seed_tasks(session)
            await seed_reports(session, articles)
            await seed_agent_runs(session, agents)

            await session.commit()
            log.info("Seed complete. Run 'make start' and visit http://localhost:3000")
    finally:
        await engine.dispose()


def main() -> None:
    """CLI entry point."""
    db_url = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(run_seed(db_url))


if __name__ == "__main__":
    main()
