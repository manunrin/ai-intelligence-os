"""Pronunciation Agent — multilingual learning card generator.

Supports Chinese (pinyin), English (IPA phonetic), and Japanese (kana + romaji).
Used to generate AI-powered pronunciation cards from news content.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ...agents.base import AgentBase
from ...agents.pronunciation.schemas import PronunciationInput, PronunciationOutput
from ...services.llm.base import ChatMessage, ChatRole
from ...services.llm.client import LLMClient

logger = logging.getLogger(__name__)


class PronunciationAgent(AgentBase):
    """Generates multilingual pronunciation data for learning cards.

    Input:  {"text": str, "languages": list[str]}  — languages ∈ {"zh", "en", "ja"}
    Output: {"translations": dict[str, {"text": str, ...}]}
    """

    name = "pronunciation"
    version = "0.1.0"
    description = "Generates multilingual pronunciation guides (pinyin, IPA, kana) for AI learning cards"

    SUPPORTED_LANGUAGES = {"zh", "en", "ja"}

    def __init__(self, llm_client: LLMClient, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._llm_client = llm_client

    async def _execute_impl(self, input_data: dict[str, Any]) -> dict[str, Any]:
        validated = PronunciationInput.model_validate(input_data)

        messages = [
            ChatMessage(
                role=ChatRole.SYSTEM,
                content=(
                    "You are a multilingual pronunciation specialist. For any given text, generate accurate "
                    "pronunciation guides in Chinese (pinyin), English (IPA), and Japanese (kana + romaji)."
                ),
            ),
            ChatMessage(
                role=ChatRole.USER,
                content=self._build_prompt(validated),
            ),
        ]

        response = await self._llm_client.chat(messages, task="translation")

        output = PronunciationOutput.from_llm_response(
            raw=response.content or "",
            languages=validated.languages,
        )

        return {
            "translations": output.translations,
            "usage": response.usage,
        }

    @staticmethod
    def _build_prompt(data: PronunciationInput) -> str:
        langs = ", ".join(data.languages) if data.languages else "all supported"
        return (
            f"Generate pronunciation data for the following text in these languages: {langs}.\n\n"
            f"Text: {data.text}\n\n"
            "Return JSON with keys matching the requested languages.\n"
            "- zh: text (original), pinyin (with tone numbers)\n"
            "- en: text (original), phonetic (IPA)\n"
            "- ja: text (original), kana (hiragana), romaji (HEPBURN)"
        )
