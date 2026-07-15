"""Analyst Agent — evaluates importance, impact, and categorization of intelligence."""

from __future__ import annotations

import logging
from typing import Any

from ...agents.base import AgentBase
from ...services.llm.base import ChatMessage, ChatRole
from ...services.llm.client import LLMClient

logger = logging.getLogger(__name__)


class AnalystAgent(AgentBase):
    """Analyzes content for importance, category, and business impact.

    Input:  {"content": str, "category_hint": str | None}
    Output: {"importance_score": float, "category": str, "impact": str, "reasoning": str}
    """

    name = "analyst"
    version = "0.1.0"
    description = "Analyzes intelligence items for importance, category, and impact assessment"

    def __init__(self, llm_client: LLMClient, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._llm_client = llm_client

    async def _execute_impl(self, input_data: dict[str, Any]) -> dict[str, Any]:
        content = input_data.get("content", "")
        category_hint = input_data.get("category_hint")

        messages = [
            ChatMessage(
                role=ChatRole.SYSTEM,
                content=(
                    "You are an intelligence analyst. Evaluate content on multiple dimensions "
                    "and provide scored assessments with reasoning."
                ),
            ),
            ChatMessage(role=ChatRole.USER, content=self._build_prompt(content, category_hint)),
        ]

        response = await self._llm_client.chat(messages, task="analysis")

        return {
            "content_length": len(content),
            "response": response.content or "",
            "usage": response.usage,
        }

    @staticmethod
    def _build_prompt(content: str, category_hint: str | None) -> str:
        lines = [f"Analyze the following content:\n\n{content}"]
        if category_hint:
            lines.append(f"\nCategory hint: {category_hint}")
        lines.extend([
            "\nEvaluate along these dimensions:",
            "- Technical Impact (1-10)",
            "- Business Impact (1-10)",
            "- Trend Signal Strength (1-10)",
            "- Urgency (low/medium/high/critical)",
            "Provide scored assessments with brief reasoning.",
        ])
        return "\n".join(lines)
