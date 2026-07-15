"""Knowledge Pipeline — full research → knowledge → operations workflow.

Flow:
    Article → Research → Analysis → Translation → Knowledge → Pronunciation → Project Planning → Notification
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from ...services.llm.client import LLMClient
from .builder import build_intelligence_graph
from .ops_nodes import build_nodes


def build_knowledge_pipeline_graph() -> StateGraph:
    """Build the full knowledge pipeline as a LangGraph StateGraph.

    Combines the existing intelligence graph (research → analyst → translator)
    with the new operations stages (knowledge → pronunciation → project manager → notification).

    Graph structure:
        START → research → analyst → translator → knowledge → pronunciation → project_manager → notification → END
    """
    # Build the intelligence sub-graph
    intelligence_graph = build_intelligence_graph()

    # Build operations nodes
    router = LLMClient.__new__(LLMClient)  # placeholder; real wiring done at compile time
    knowledge_fn, pronunciation_fn, pm_fn, notification_fn = build_nodes(router)

    # We compose by building a fresh graph that includes both phases
    from .operations_state import OperationsState

    graph = StateGraph(OperationsState)

    # Intelligence phase nodes (reuse the same logic)
    from .nodes import build_nodes as build_intel_nodes

    research_fn, analyst_fn, translator_fn = build_intel_nodes(router)

    graph.add_node("research", research_fn)
    graph.add_node("analyst", analyst_fn)
    graph.add_node("translator", translator_fn)
    graph.add_node("knowledge", knowledge_fn)
    graph.add_node("pronunciation", pronunciation_fn)
    graph.add_node("project_manager", pm_fn)
    graph.add_node("notification", notification_fn)

    # Edges
    graph.add_edge(START, "research")
    graph.add_edge("research", "analyst")
    graph.add_edge("analyst", "translator")
    graph.add_edge("translator", "knowledge")
    graph.add_edge("knowledge", "pronunciation")
    graph.add_edge("pronunciation", "project_manager")
    graph.add_edge("project_manager", "notification")
    graph.add_edge("notification", END)

    return graph


def compile_knowledge_pipeline(checkpoint: bool = False) -> Any:
    """Build and compile the knowledge pipeline graph.

    Args:
        checkpoint: If True, enables state checkpoints.

    Returns:
        Compiled LangGraph application.
    """
    graph = build_knowledge_pipeline_graph()
    compile_kwargs: dict[str, Any] = {}
    if checkpoint:
        from langgraph.checkpoint.memory import MemorySaver
        compile_kwargs["checkpointer"] = MemorySaver()

    return graph.compile(**compile_kwargs)
