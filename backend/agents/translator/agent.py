"""Translator Agent — translates content across languages."""

from __future__ import annotations

import logging
from typing import Any

from ...agents.base import AgentBase
from ...services.llm.base import ChatMessage, ChatRole
from ...services.llm.client import LLMClient

logger = logging.getLogger(__name__)


class TranslatorAgent(AgentBase):
    """Translates content into target languages with quality assessment.

    Input:  {"content": str, "target_languages": list[str], "source_language": str | None}
    Output: {"translations": dict[str, str], "confidence_scores": dict[str, float]}
    """

    name = "translator"
    version = "0.1.0"
    description = "Translates content into multiple target languages with confidence scoring"

    def __init__(self, llm_client: LLMClient, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._llm_client = llm_client

    async def _execute_impl(self, input_data: dict[str, Any]) -> dict[str, Any]:
        content = input_data.get("content", "")
        target_languages = input_data.get("target_languages", ["zh-CN", "ja"])
        source_language = input_data.get("source_language")

        messages = [
            ChatMessage(
                role=ChatRole.SYSTEM,
                content=(
                    "You are a professional translator. Translate accurately while preserving "
                    "context, tone, and technical terminology."
                ),
            ),
            ChatMessage(role=ChatRole.USER, content=self._build_prompt(content, target_languages, source_language)),
        ]

        response = await self._llm_client.chat(messages, task="translation")

        return {
            "source_language": source_language,
            "target_languages": target_languages,
            "response": response.content or "",
            "usage": response.usage,
        }

    @staticmethod
    def _build_prompt(content: str, target_languages: list[str], source_language: str | None) -> str:
        lines = [f"Translate the following content into the target languages: {', '.join(target_languages)}"]
        if source_language:
            lines.append(f"Source language: {source_language}")
        lines.extend([f"\nContent:\n{content}", "\nFor each language provide: translation text and a confidence score 0.0-1.0."])
        return "\n".join(lines)
