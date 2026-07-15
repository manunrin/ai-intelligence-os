"""Daily intelligence workflow — research, analyze, translate pipeline."""

from __future__ import annotations

from .builder import compile_intelligence_graph


def run_daily_intelligence(topic: str, **kwargs) -> dict:
    """Execute the full daily intelligence pipeline.

    This is the entry point for scheduled daily workflows. It compiles
    the LangGraph state machine and runs it with the given topic.

    Args:
        topic: The research topic for today's intelligence cycle.
        **kwargs: Additional state fields passed to the graph (focus_areas,
            target_languages, source_language).

    Returns:
        Final state after the pipeline completes.
    """
    app = compile_intelligence_graph()
    initial_state = {
        "topic": topic,
        **kwargs,
    }
    return app.invoke(initial_state)
