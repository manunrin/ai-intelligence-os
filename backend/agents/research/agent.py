"""Research Agent — gathers information from sources and produces structured findings."""

from __future__ import annotations

import logging
from typing import Any

from ...agents.base import AgentBase
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
    description = "Researches topics using LLM knowledge and produces structured findings"

    def __init__(self, llm_client: LLMClient, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._llm_client = llm_client

    async def _execute_impl(self, input_data: dict[str, Any]) -> dict[str, Any]:
        topic = input_data.get("topic", "")
        focus_areas = input_data.get("focus_areas", [])
        sources = input_data.get("sources")

        messages = [
            ChatMessage(
                role=ChatRole.SYSTEM,
                content="You are a research analyst. Produce concise, factual findings.",
            ),
            ChatMessage(
                role=ChatRole.USER,
                content=self._build_prompt(topic, focus_areas, sources),
            ),
        ]

        response = await self._llm_client.chat(messages, task="research")

        return {
            "topic": topic,
            "focus_areas": focus_areas,
            "response": response.content or "",
            "usage": response.usage,
        }

    @staticmethod
    def _build_prompt(topic: str, focus_areas: list[str], sources: list[str] | None) -> str:
        parts = [f"Research the following topic: {topic}"]
        if focus_areas:
            parts.append(f"Focus your analysis on these areas: {', '.join(focus_areas)}")
        if sources:
            parts.append(f"Consider these sources: {', '.join(sources)}")
        parts.append("Provide a structured summary with key findings.")
        return "\n".join(parts)
