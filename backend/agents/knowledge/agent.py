"""Knowledge Agent — converts analyzed content into structured knowledge."""

from __future__ import annotations

import logging
from typing import Any

from ...agents.base import AgentBase
from ...agents.knowledge.schemas import KnowledgeInput, KnowledgeOutput
from ...services.llm.base import ChatMessage, ChatRole
from ...services.llm.client import LLMClient

logger = logging.getLogger(__name__)


class KnowledgeAgent(AgentBase):
    """Converts research/analysis content into structured knowledge entries.

    Input:  {"title": str, "content": str, "analysis": str, "source": str, "tags": list[str]}
    Output: {"knowledge_type": str, "summary": str, "key_points": list[str], "tags": list[str]}
    """

    name = "knowledge"
    version = "0.1.0"
    description = "Converts analyzed content into structured knowledge with summaries and key points"

    def __init__(self, llm_client: LLMClient, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._llm_client = llm_client

    async def _execute_impl(self, input_data: dict[str, Any]) -> dict[str, Any]:
        # Validate input
        validated = KnowledgeInput.model_validate(input_data)

        messages = [
            ChatMessage(
                role=ChatRole.SYSTEM,
                content="You are a knowledge extraction engine. Convert raw content into structured, searchable knowledge entries.",
            ),
            ChatMessage(
                role=ChatRole.USER,
                content=self._build_prompt(validated),
            ),
        ]

        response = await self._llm_client.chat(messages, task="analysis")

        output = KnowledgeOutput.from_llm_response(
            raw=response.content or "",
            title=validated.title,
            source=validated.source,
        )

        return {
            "knowledge_type": output.kind,
            "summary": output.summary,
            "key_points": output.key_points,
            "tags": output.tags,
            "notion_structure": output.notion_structure,
            "usage": response.usage,
        }

    @staticmethod
    def _build_prompt(data: KnowledgeInput) -> str:
        parts: list[str] = []
        parts.append(f"Title: {data.title}")
        if data.content:
            parts.append(f"Content:\n{data.content}")
        if data.analysis:
            parts.append(f"Analysis:\n{data.analysis}")
        if data.tags:
            parts.append(f"Tags: {', '.join(data.tags)}")
        parts.append(f"Source: {data.source}")
        return "\n".join(parts)
