"""LangGraph node wrappers that delegate to existing Agent instances."""

from __future__ import annotations

import logging
from typing import Any

from ...agents.analyst.agent import AnalystAgent
from ...agents.base import AgentBase
from ...agents.research.agent import ResearchAgent
from ...agents.translator.agent import TranslatorAgent
from ...services.llm.client import LLMClient
from .state import IntelligenceState

logger = logging.getLogger(__name__)


def _make_research_node(agent: ResearchAgent | None = None):
    """Create a LangGraph node function wrapping ResearchAgent."""

    async def research_node(state: IntelligenceState) -> dict[str, Any]:
        try:
            input_data = {
                "topic": state.topic,
                "focus_areas": state.focus_areas,
            }
            result = await agent.execute(input_data)
            return {"research_result": result.get("output")}
        except Exception as exc:
            logger.error("Research node failed: %s", exc)
            state.add_error("research", str(exc))
            return {"research_result": {"error": str(exc)}}

    return research_node


def _make_analyst_node(agent: AnalystAgent | None = None):
    """Create a LangGraph node function wrapping AnalystAgent."""

    async def analyst_node(state: IntelligenceState) -> dict[str, Any]:
        try:
            research_output = (state.research_result or {}).get("response", "")
            if not research_output:
                raise ValueError("No research output to analyze")
            input_data = {"content": research_output}
            result = await agent.execute(input_data)
            return {"analysis_result": result.get("output")}
        except Exception as exc:
            logger.error("Analyst node failed: %s", exc)
            state.add_error("analysis", str(exc))
            return {"analysis_result": {"error": str(exc)}}

    return analyst_node


def _make_translator_node(agent: TranslatorAgent | None = None):
    """Create a LangGraph node function wrapping TranslatorAgent."""

    async def translator_node(state: IntelligenceState) -> dict[str, Any]:
        try:
            analysis_output = (state.analysis_result or {}).get("response", "")
            if not analysis_output:
                raise ValueError("No analysis output to translate")
            input_data = {
                "content": analysis_output,
                "target_languages": state.target_languages,
                "source_language": state.source_language,
            }
            result = await agent.execute(input_data)
            return {"translation_result": result.get("output")}
        except Exception as exc:
            logger.error("Translator node failed: %s", exc)
            state.add_error("translation", str(exc))
            return {"translation_result": {"error": str(exc)}}

    return translator_node


# ── Pre-wrapped nodes (use when agents are constructed externally) ──

research_node: Any = None
analyst_node: Any = None
translator_node: Any = None


def build_nodes(
    llm_client: LLMClient,
    research_agent: ResearchAgent | None = None,
    analyst_agent: AnalystAgent | None = None,
    translator_agent: TranslatorAgent | None = None,
) -> tuple[Any, Any, Any]:
    """Build all node functions with injected agents.

    Returns (research_node, analyst_node, translator_node).
    """
    research_agent = research_agent or ResearchAgent(llm_client=llm_client)
    analyst_agent = analyst_agent or AnalystAgent(llm_client=llm_client)
    translator_agent = translator_agent or TranslatorAgent(llm_client=llm_client)

    r = _make_research_node(research_agent)
    a = _make_analyst_node(analyst_agent)
    t = _make_translator_node(translator_agent)
    return r, a, t
