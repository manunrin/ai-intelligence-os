"""LangGraph nodes for the autonomous intelligence workflow."""

from __future__ import annotations

import logging
from typing import Any

from backend.agents.analyst.agent import AnalystAgent
from backend.agents.knowledge.agent import KnowledgeAgent
from backend.agents.notification.agent import NotificationAgent
from backend.agents.project_manager.agent import ProjectManagerAgent
from backend.agents.research.agent import ResearchAgent
from backend.agents.translator.agent import TranslatorAgent
from backend.services.llm.client import LLMClient
from .autonomous_state import AutonomousState

logger = logging.getLogger(__name__)


def _make_research_node(
    agent: ResearchAgent | None = None,
) -> Any:
    """Create a LangGraph node wrapping ResearchAgent."""

    async def research_node(state: AutonomousState) -> dict[str, Any]:
        try:
            input_data = {
                "topic": state.topic,
                "focus_areas": state.focus_areas,
            }
            result = await agent.execute(input_data) if agent else {}
            return {"research_result": result.get("output")}
        except Exception as exc:
            logger.error("Research node failed: %s", exc)
            state.add_error("research", str(exc))
            return {"research_result": {"error": str(exc)}}

    return research_node


def _make_analyst_node(agent: AnalystAgent | None = None) -> Any:
    """Create a LangGraph node wrapping AnalystAgent."""

    async def analyst_node(state: AutonomousState) -> dict[str, Any]:
        try:
            research_output = (state.research_result or {}).get("response", "")
            if not research_output:
                raise ValueError("No research output to analyze")
            input_data = {"content": research_output}
            result = await agent.execute(input_data) if agent else {}
            return {"analysis_result": result.get("output")}
        except Exception as exc:
            logger.error("Analyst node failed: %s", exc)
            state.add_error("analysis", str(exc))
            return {"analysis_result": {"error": str(exc)}}

    return analyst_node


def _make_translator_node(agent: TranslatorAgent | None = None) -> Any:
    """Create a LangGraph node wrapping TranslatorAgent."""

    async def translator_node(state: AutonomousState) -> dict[str, Any]:
        try:
            analysis_output = (state.analysis_result or {}).get("response", "")
            if not analysis_output:
                raise ValueError("No analysis output to translate")
            input_data = {
                "content": analysis_output,
                "target_languages": state.target_languages,
                "source_language": state.source_language,
            }
            result = await agent.execute(input_data) if agent else {}
            return {"translation_result": result.get("output")}
        except Exception as exc:
            logger.error("Translator node failed: %s", exc)
            state.add_error("translation", str(exc))
            return {"translation_result": {"error": str(exc)}}

    return translator_node


def _make_knowledge_node(agent: KnowledgeAgent | None = None) -> Any:
    """Create a LangGraph node wrapping KnowledgeAgent."""

    async def knowledge_node(state: AutonomousState) -> dict[str, Any]:
        try:
            analysis_output = (state.analysis_result or {}).get("response", "")
            if not analysis_output:
                raise ValueError("No analysis output to convert to knowledge")
            input_data = {
                "title": state.topic,
                "content": analysis_output,
                "source": state.source or "autonomous_workflow",
                "tags": state.tags[:5],
            }
            result = await agent.execute(input_data) if agent else {}
            return {"knowledge_result": result.get("output")}
        except Exception as exc:
            logger.error("Knowledge node failed: %s", exc)
            state.add_error("knowledge", str(exc))
            return {"knowledge_result": {"error": str(exc)}}

    return knowledge_node


def _make_project_manager_node(agent: ProjectManagerAgent | None = None) -> Any:
    """Create a LangGraph node wrapping ProjectManagerAgent."""

    async def project_manager_node(state: AutonomousState) -> dict[str, Any]:
        try:
            knowledge = (state.knowledge_result or {}).get("notion_structure", "")
            if not knowledge:
                knowledge = (state.knowledge_result or {}).get("summary", "")
            if not knowledge:
                raise ValueError("No knowledge structure for project planning")
            input_data = {
                "goal": state.topic,
                "knowledge": knowledge,
                "deadline": "",
            }
            result = await agent.execute(input_data) if agent else {}
            return {"project_plan_result": result.get("output")}
        except Exception as exc:
            logger.error("Project Manager node failed: %s", exc)
            state.add_error("project_manager", str(exc))
            return {"project_plan_result": {"error": str(exc)}}

    return project_manager_node


def _make_notification_node(agent: NotificationAgent | None = None) -> Any:
    """Create a LangGraph node wrapping NotificationAgent."""

    async def notification_node(state: AutonomousState) -> dict[str, Any]:
        try:
            news_items = []
            if state.research_result:
                news_items.append({
                    "title": state.topic,
                    "summary": (state.research_result or {}).get("response", "")[:200],
                })

            knowledge_items = []
            if state.knowledge_result:
                knowledge_items.append({
                    "title": (state.knowledge_result or {}).get("summary", ""),
                    "kind": (state.knowledge_result or {}).get("knowledge_type", ""),
                })

            task_items = []
            if state.project_plan_result:
                for t in (state.project_plan_result or {}).get("tasks", [])[:10]:
                    task_items.append({
                        "title": t.get("title", ""),
                        "priority": t.get("priority", "medium"),
                        "status": "pending",
                    })

            input_data = {
                "date": "",
                "news": news_items,
                "knowledge": knowledge_items,
                "tasks": task_items,
                "channels": ["wechat", "telegram", "email"],
            }
            result = await agent.execute(input_data) if agent else {}
            return {"notification_result": result.get("output")}
        except Exception as exc:
            logger.error("Notification node failed: %s", exc)
            state.add_error("notification", str(exc))
            return {"notification_result": {"error": str(exc)}}

    return notification_node


# ── Pre-wrapped nodes ────────────────────────────────────────────

research_node: Any = None
analyst_node: Any = None
translator_node: Any = None
knowledge_node: Any = None
project_manager_node: Any = None
notification_node: Any = None


def build_nodes(
    llm_client: LLMClient,
    *,
    mcp_registry: Any = None,
    notion_database_id: str = "",
    asana_project_id: str = "",
) -> tuple[Any, ...]:
    """Build all autonomous workflow nodes with injected agents.

    Returns (research, analyst, translator, knowledge, project_manager, notification).
    """
    research_agent = ResearchAgent(llm_client=llm_client, mcp_registry=mcp_registry)
    analyst_agent = AnalystAgent(llm_client=llm_client)
    translator_agent = TranslatorAgent(llm_client=llm_client)
    knowledge_agent = KnowledgeAgent(
        llm_client=llm_client,
        mcp_registry=mcp_registry,
        notion_database_id=notion_database_id,
    )
    pm_agent = ProjectManagerAgent(
        llm_client=llm_client,
        mcp_registry=mcp_registry,
        asana_project_id=asana_project_id,
    )
    notification_agent = NotificationAgent(llm_client=llm_client, mcp_registry=mcp_registry)

    return (
        _make_research_node(research_agent),
        _make_analyst_node(analyst_agent),
        _make_translator_node(translator_agent),
        _make_knowledge_node(knowledge_agent),
        _make_project_manager_node(pm_agent),
        _make_notification_node(notification_agent),
    )
