"""LangGraph StateGraph builder for the intelligence pipeline."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from ...services.llm.client import LLMClient
from ...services.llm.router import LLMRouter
from .nodes import build_nodes
from .state import IntelligenceState


def build_intelligence_graph() -> StateGraph:
    """Build the daily intelligence pipeline as a LangGraph StateGraph.

    Graph structure:
        START → research → analyst → translator → END

    Each node wraps an Agent instance and reads/writes IntelligenceState.
    Errors are captured in state.errors but do not stop the pipeline.
    """
    graph = StateGraph(IntelligenceState)

    # Build nodes with their agent dependencies
    router = LLMRouter()
    client = LLMClient(router)
    research_fn, analyst_fn, translator_fn = build_nodes(client)

    # Add nodes to the graph
    graph.add_node("research", research_fn)
    graph.add_node("analyst", analyst_fn)
    graph.add_node("translator", translator_fn)

    # Define edges
    graph.add_edge(START, "research")
    graph.add_edge("research", "analyst")
    graph.add_edge("analyst", "translator")
    graph.add_edge("translator", END)

    return graph


def compile_intelligence_graph(
    checkpointer: Any = None,
    checkpoint: bool = False,
) -> Any:
    """Build and compile the graph into an executable application.

    Args:
        checkpointer: Optional LangGraph checkpointer for persistent state.
            If provided, it takes precedence over ``checkpoint``.
        checkpoint: If True and no checkpointer is provided, enables
            in-memory checkpoints via MemorySaver.

    Returns:
        Compiled LangGraph application (RunnableGenerator).
    """
    graph = build_intelligence_graph()
    compile_kwargs: dict[str, Any] = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer
    elif checkpoint:
        from langgraph.checkpoint.memory import MemorySaver
        compile_kwargs["checkpointer"] = MemorySaver()

    return graph.compile(**compile_kwargs)
