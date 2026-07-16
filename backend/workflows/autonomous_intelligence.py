"""Autonomous Intelligence Workflow — full end-to-end pipeline.

Flow:
    Article → Research → Analyst → Translator → Knowledge(→Notion) →
    ProjectManager(→Asana) → Notification → END
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from backend.services.llm.client import LLMClient
from backend.services.llm.router import LLMRouter
from .graph.autonomous_nodes import build_nodes
from .graph.autonomous_state import AutonomousState

logger = logging.getLogger(__name__)


def build_autonomous_intelligence_graph(
    llm_client: LLMClient | None = None,
    mcp_registry: Any = None,
    notion_database_id: str = "",
    asana_project_id: str = "",
) -> StateGraph:
    """Build the full autonomous intelligence pipeline as a LangGraph StateGraph.

    Graph structure:
        START → research → analyst → translator → knowledge → project_manager → notification → END

    Each node wraps an Agent instance. Errors are captured in state.errors
    but do not stop the pipeline.

    Args:
        llm_client: Optional pre-built LLM client. A default is created if omitted.
        mcp_registry: Optional MCPRegistry for tool calls (Notion, Asana, Browser).
        notion_database_id: Notion database ID for knowledge sync.
        asana_project_id: Asana project ID for task sync.

    Returns:
        Uncompiled StateGraph ready for .compile().
    """
    if llm_client is None:
        router = LLMRouter()
        llm_client = LLMClient(router)

    (
        research_fn,
        analyst_fn,
        translator_fn,
        knowledge_fn,
        pm_fn,
        notification_fn,
    ) = build_nodes(
        llm_client,
        mcp_registry=mcp_registry,
        notion_database_id=notion_database_id,
        asana_project_id=asana_project_id,
    )

    graph = StateGraph(AutonomousState)

    graph.add_node("research", research_fn)
    graph.add_node("analyst", analyst_fn)
    graph.add_node("translator", translator_fn)
    graph.add_node("knowledge", knowledge_fn)
    graph.add_node("project_manager", pm_fn)
    graph.add_node("notification", notification_fn)

    graph.add_edge(START, "research")
    graph.add_edge("research", "analyst")
    graph.add_edge("analyst", "translator")
    graph.add_edge("translator", "knowledge")
    graph.add_edge("knowledge", "project_manager")
    graph.add_edge("project_manager", "notification")
    graph.add_edge("notification", END)

    return graph


def compile_autonomous_intelligence(
    checkpoint: bool = False,
    **graph_kwargs: Any,
) -> Any:
    """Build and compile the autonomous intelligence graph.

    Args:
        checkpoint: If True, enables state checkpoints.
        **graph_kwargs: Passed to build_autonomous_intelligence_graph.

    Returns:
        Compiled LangGraph application.
    """
    graph = build_autonomous_intelligence_graph(**graph_kwargs)
    compile_kwargs: dict[str, Any] = {}
    if checkpoint:
        from langgraph.checkpoint.memory import MemorySaver
        compile_kwargs["checkpointer"] = MemorySaver()

    return graph.compile(**compile_kwargs)
