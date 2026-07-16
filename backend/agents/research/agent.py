"""Research Agent — gathers information from sources and produces structured findings."""

from __future__ import annotations

import logging
from typing import Any

from ...agents.base import AgentBase
from ...mcp.registry import MCPRegistry
from ...services.llm.base import ChatMessage, ChatRole
from ...services.llm.client import LLMClient

logger = logging.getLogger(__name__)


class ResearchAgent(AgentBase):
    """Collects and synthesizes information on a given topic.

    Input:  {"topic": str, "focus_areas": list[str], "sources": list[str] | None}
    Output: {"summary": str, "findings": list[str], "sources_used": list[str]}
    """

    name = "research"
    version = "0.1.0"
    description = "Researches topics using LLM knowledge and web search to produce structured findings"

    def __init__(
        self,
        llm_client: LLMClient,
        mcp_registry: MCPRegistry | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._llm_client = llm_client
        self._mcp_registry = mcp_registry

    async def _execute_impl(self, input_data: dict[str, Any]) -> dict[str, Any]:
        topic = input_data.get("topic", "")
        focus_areas = input_data.get("focus_areas", [])
        sources = input_data.get("sources")

        # ── Web research via Browser MCP ────────────────────────────
        web_results = await self._web_research(topic, focus_areas)

        messages = [
            ChatMessage(
                role=ChatRole.SYSTEM,
                content="You are a research analyst. Produce concise, factual findings.",
            ),
            ChatMessage(
                role=ChatRole.USER,
                content=self._build_prompt(topic, focus_areas, sources, web_results),
            ),
        ]

        response = await self._llm_client.chat(messages, task="research")

        return {
            "topic": topic,
            "focus_areas": focus_areas,
            "response": response.content or "",
            "web_results": web_results,
            "usage": response.usage,
        }

    async def _web_research(
        self, topic: str, focus_areas: list[str]
    ) -> list[dict[str, Any]]:
        """Search the web via Browser MCP tools for current information.

        Returns list of result dicts with title/url/snippet.
        Falls back gracefully if browser tools are unavailable.
        """
        if self._mcp_registry is None:
            logger.debug("ResearchAgent: no MCP registry configured, skipping web research")
            return []

        tool = self._mcp_registry.get_tool("browser.search")
        if tool is None:
            logger.debug("ResearchAgent: browser.search tool not registered")
            return []

        queries = [topic] + focus_areas if focus_areas else [topic]
        all_results: list[dict[str, Any]] = []

        for query in queries[:3]:  # Cap at 3 queries
            try:
                result = await tool.execute(query=query, max_results=5)
                data = result.get("data", {})
                results = data.get("results", [])
                all_results.extend(results)
            except Exception as exc:
                logger.warning("ResearchAgent: browser.search failed for '%s': %s", query, exc)

        return all_results

    @staticmethod
    def _build_prompt(
        topic: str,
        focus_areas: list[str],
        sources: list[str] | None,
        web_results: list[dict[str, Any]],
    ) -> str:
        parts: list[str] = [f"Research the following topic: {topic}"]
        if focus_areas:
            parts.append(f"Focus your analysis on these areas: {', '.join(focus_areas)}")
        if sources:
            parts.append(f"Consider these sources: {', '.join(sources)}")
        if web_results:
            parts.append("\n--- Web Search Results ---")
            for r in web_results[:10]:
                title = r.get("title", "Untitled")
                url = r.get("url", "")
                snippet = r.get("snippet", "")
                parts.append(f"- [{title}]({url}) {snippet}")
        parts.append("Provide a structured summary with key findings.")
        return "\n".join(parts)
