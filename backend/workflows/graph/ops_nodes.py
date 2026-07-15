"""LangGraph nodes for the knowledge pipeline operations stages."""

from __future__ import annotations

import logging
from typing import Any

from ...agents.knowledge.agent import KnowledgeAgent
from ...agents.notification.agent import NotificationAgent
from ...agents.pronunciation.agent import PronunciationAgent
from ...agents.project_manager.agent import ProjectManagerAgent
from ...services.llm.client import LLMClient
from ...workflows.graph.operations_state import OperationsState

logger = logging.getLogger(__name__)


def _make_knowledge_node(agent: KnowledgeAgent | None = None):
    """Create a LangGraph node wrapping KnowledgeAgent."""

    async def knowledge_node(state: OperationsState) -> dict[str, Any]:
        try:
            analysis_output = (state.analysis_result or {}).get("response", "")
            if not analysis_output:
                raise ValueError("No analysis output to convert to knowledge")
            input_data = {
                "title": state.topic,
                "content": analysis_output,
                "source": "daily_intelligence_pipeline",
                "tags": state.focus_areas[:5],
            }
            result = await agent.execute(input_data)
            return {"knowledge_result": result.get("output")}
        except Exception as exc:
            logger.error("Knowledge node failed: %s", exc)
            state.add_error("knowledge", str(exc))
            return {"knowledge_result": {"error": str(exc)}}

    return knowledge_node


def _make_pronunciation_node(agent: PronunciationAgent | None = None):
    """Create a LangGraph node wrapping PronunciationAgent."""

    async def pronunciation_node(state: OperationsState) -> dict[str, Any]:
        try:
            content = (state.knowledge_result or {}).get("summary", "")
            if not content:
                raise ValueError("No knowledge summary for pronunciation")
            input_data = {
                "text": content,
                "languages": [lang.split("-")[0] for lang in state.target_languages],
            }
            result = await agent.execute(input_data)
            return {"pronunciation_result": result.get("output")}
        except Exception as exc:
            logger.error("Pronunciation node failed: %s", exc)
            state.add_error("pronunciation", str(exc))
            return {"pronunciation_result": {"error": str(exc)}}

    return pronunciation_node


def _make_project_manager_node(agent: ProjectManagerAgent | None = None):
    """Create a LangGraph node wrapping ProjectManagerAgent."""

    async def project_manager_node(state: OperationsState) -> dict[str, Any]:
        try:
            knowledge = (state.knowledge_result or {}).get("notion_structure", "")
            if not knowledge:
                raise ValueError("No knowledge structure for project planning")
            input_data = {
                "goal": state.topic,
                "knowledge": knowledge,
                "deadline": "",
            }
            result = await agent.execute(input_data)
            return {"project_plan_result": result.get("output")}
        except Exception as exc:
            logger.error("Project Manager node failed: %s", exc)
            state.add_error("project_manager", str(exc))
            return {"project_plan_result": {"error": str(exc)}}

    return project_manager_node


def _make_notification_node(agent: NotificationAgent | None = None):
    """Create a LangGraph node wrapping NotificationAgent."""

    async def notification_node(state: OperationsState) -> dict[str, Any]:
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
            result = await agent.execute(input_data)
            return {"notification_result": result.get("output")}
        except Exception as exc:
            logger.error("Notification node failed: %s", exc)
            state.add_error("notification", str(exc))
            return {"notification_result": {"error": str(exc)}}

    return notification_node


# ── Pre-wrapped nodes ────────────────────────────────────────────

knowledge_node: Any = None
pronunciation_node: Any = None
project_manager_node: Any = None
notification_node: Any = None


def build_nodes(llm_client: LLMClient) -> tuple[Any, Any, Any, Any]:
    """Build all operations nodes with injected LLM client.

    Returns (knowledge_node, pronunciation_node, project_manager_node, notification_node).
    """
    knowledge_fn = _make_knowledge_node(KnowledgeAgent(llm_client=llm_client))
    pronunciation_fn = _make_pronunciation_node(PronunciationAgent(llm_client=llm_client))
    pm_fn = _make_project_manager_node(ProjectManagerAgent(llm_client=llm_client))
    notification_fn = _make_notification_node(NotificationAgent(llm_client=llm_client))
    return knowledge_fn, pronunciation_fn, pm_fn, notification_fn
