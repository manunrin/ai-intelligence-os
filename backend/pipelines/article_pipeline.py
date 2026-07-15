"""Article Intelligence Pipeline — end-to-end data flow.

Pipeline:
    Article (DB) → ResearchAgent → AnalystAgent → TranslatorAgent → KnowledgeItem (DB)

This module orchestrates the full intelligence lifecycle for a single article:
1. Create an AgentRun record tracking execution
2. Run the LangGraph pipeline (research → analyze → translate)
3. Persist each stage output as a KnowledgeItem
4. Update article status from "raw" → "analyzed" → "translated"
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..agents.analyst.agent import AnalystAgent
from ..agents.research.agent import ResearchAgent
from ..agents.translator.agent import TranslatorAgent
from ..database.models.agent_run import AgentRun
from ..database.models.article import Article
from ..services.knowledge.service import KnowledgeService
from ..services.llm.client import LLMClient
from ..services.llm.router import LLMRouter


class PipelineState(TypedDict, total=False):
    """Minimal state schema for the article pipeline graph."""
    topic: str
    focus_areas: list[str]
    source_language: str | None
    research_result: dict | None
    analysis_result: dict | None
    translation_result: dict | None
    errors: list[dict[str, str]]


logger = logging.getLogger(__name__)


class ArticlePipeline:
    """Runs a single article through the full intelligence pipeline.

    Usage:
        pipeline = ArticlePipeline(session)
        result = await pipeline.run(article_id)
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._knowledge = KnowledgeService(session)

    async def run(self, article_id: UUID) -> dict[str, Any]:
        """Execute the full intelligence pipeline for one article.

        Args:
            article_id: UUID of the Article to process.

        Returns:
            Dict with keys: article_id, knowledge_ids, errors, final_status
        """
        # 1. Load article
        article = await self._get_article(article_id)
        if not article:
            logger.warning("Article %s not found — skipping pipeline", article_id)
            return {"article_id": str(article_id), "error": "not_found"}

        # 2. Create AgentRun record
        agent_run = await self._create_agent_run(article)

        # 3. Build LLM client and agents
        router = LLMRouter()
        llm_client = LLMClient(router)
        research_agent = ResearchAgent(llm_client=llm_client)
        analyst_agent = AnalystAgent(llm_client=llm_client)
        translator_agent = TranslatorAgent(llm_client=llm_client)

        # 4. Build and run the LangGraph pipeline
        graph = self._build_graph(research_agent, analyst_agent, translator_agent)
        initial_state: PipelineState = {
            "topic": article.title,
            "focus_areas": self._extract_tags(article),
            "source_language": article.language,
        }

        try:
            final_state = graph.invoke(initial_state)
        except Exception as exc:
            logger.error(
                "Pipeline failed for article '%s': %s",
                article.title, exc, exc_info=True,
            )
            await self._fail_agent_run(agent_run, str(exc))
            await self._update_article_status(article_id, "raw")
            return {
                "article_id": str(article_id),
                "error": str(exc),
                "final_status": "raw",
            }

        # 5. Persist results as KnowledgeItems
        knowledge_ids: list[str] = []
        knowledge_ids.extend(
            await self._persist_research_results(article_id, final_state.get("research_result"))
        )
        knowledge_ids.extend(
            await self._persist_analysis_results(article_id, final_state.get("analysis_result"))
        )
        knowledge_ids.extend(
            await self._persist_translation_results(
                article_id, final_state.get("translation_result"),
            )
        )

        # 6. Update article status
        new_status = "translated" if not final_state.get("errors") else "analyzed"
        await self._complete_agent_run(agent_run)
        await self._update_article_status(article_id, new_status)

        return {
            "article_id": str(article_id),
            "knowledge_ids": knowledge_ids,
            "errors": final_state.get("errors", []),
            "final_status": new_status,
        }

    # ── Internal helpers ──────────────────────────────────────

    async def _get_article(self, article_id: UUID) -> Article | None:
        stmt = select(Article).where(Article.id == article_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    def _extract_tags(self, article: Article) -> list[str]:
        meta = article.metadata_ or {}
        tags = meta.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]
        return list(tags)[:5]

    async def _create_agent_run(self, article: Article) -> AgentRun:
        run = AgentRun(
            agent_id=uuid.uuid4(),  # composite pipeline — synthetic agent ref
            workflow_id=None,
            status="running",
            input_payload={"article_id": str(article.id), "title": article.title},
        )
        self._session.add(run)
        await self._session.flush()
        return run

    async def _complete_agent_run(self, agent_run: AgentRun) -> None:
        agent_run.status = "completed"
        agent_run.finished_at = datetime.now(timezone.utc)

    async def _fail_agent_run(self, agent_run: AgentRun, error: str) -> None:
        agent_run.status = "failed"
        agent_run.error_message = error
        agent_run.finished_at = datetime.now(timezone.utc)

    async def _update_article_status(self, article_id: UUID, status: str) -> None:
        stmt = select(Article).where(Article.id == article_id)
        result = await self._session.execute(stmt)
        article = result.scalar_one_or_none()
        if article:
            article.status = status
            logger.info("Updated article %s status → %s", article_id, status)

    def _build_graph(
        self,
        research: ResearchAgent,
        analyst: AnalystAgent,
        translator: TranslatorAgent,
    ):
        """Build a compiled LangGraph with pre-injected agents."""
        graph = StateGraph(PipelineState)

        async def research_node(state: PipelineState) -> dict[str, Any]:
            result = await research.execute({
                "topic": state.get("topic", ""),
                "focus_areas": state.get("focus_areas", []),
            })
            return {"research_result": result.get("output")}

        async def analyst_node(state: PipelineState) -> dict[str, Any]:
            research_output = (state.get("research_result") or {}).get("response", "")
            if not research_output:
                raise ValueError("No research output to analyze")
            result = await analyst.execute({"content": research_output})
            return {"analysis_result": result.get("output")}

        async def translator_node(state: PipelineState) -> dict[str, Any]:
            analysis_output = (state.get("analysis_result") or {}).get("response", "")
            if not analysis_output:
                raise ValueError("No analysis output to translate")
            result = await translator.execute({
                "content": analysis_output,
                "target_languages": ["zh-CN", "ja"],
                "source_language": state.get("source_language"),
            })
            return {"translation_result": result.get("output")}

        graph.add_node("research", research_node)
        graph.add_node("analyst", analyst_node)
        graph.add_node("translator", translator_node)

        graph.add_edge(START, "research")
        graph.add_edge("research", "analyst")
        graph.add_edge("analyst", "translator")
        graph.add_edge("translator", END)

        return graph.compile()

    async def _persist_research_results(
        self, article_id: UUID, research_result: dict[str, Any] | None,
    ) -> list[str]:
        if not research_result:
            return []
        response = research_result.get("response", "")
        item = await self._knowledge.create(
            title=f"Research: {response[:80]}",
            content=response,
            kind="article",
            article_id=article_id,
            tags=["research"],
        )
        return [str(item.id)]

    async def _persist_analysis_results(
        self, article_id: UUID, analysis_result: dict[str, Any] | None,
    ) -> list[str]:
        if not analysis_result:
            return []
        item = await self._knowledge.create_from_analysis(article_id, analysis_result)
        return [str(item.id)]

    async def _persist_translation_results(
        self, article_id: UUID, translation_result: dict[str, Any] | None,
    ) -> list[str]:
        if not translation_result:
            return []
        item = await self._knowledge.create_from_translation(
            article_id, translation_result, target_language="zh-CN",
        )
        return [str(item.id)]
