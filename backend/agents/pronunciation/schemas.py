"""Pronunciation Agent schemas."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field


class PronunciationInput(BaseModel):
    """Input schema for PronunciationAgent."""

    text: str = Field(description="Text to generate pronunciation data for")
    languages: list[str] = Field(
        default=["zh", "en", "ja"],
        description="Target languages: 'zh' (Chinese), 'en' (English), 'ja' (Japanese)",
    )


class PronunciationOutput(BaseModel):
    """Structured pronunciation output for learning cards."""

    translations: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        description="Language code → pronunciation data mapping",
    )

    @classmethod
    def from_llm_response(cls, raw: str, languages: list[str]) -> "PronunciationOutput":
        """Parse LLM response into PronunciationOutput.

        Attempts JSON parse first; falls back to structured dict on failure.
        """
        result: dict[str, dict[str, str]] = {}

        for lang in languages:
            result[lang] = {"text": raw}

        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                for lang in languages:
                    if lang in parsed and isinstance(parsed[lang], dict):
                        result[lang] = {
                            k: str(v) for k, v in parsed[lang].items()
                        }
        except (json.JSONDecodeError, ValueError):
            pass

        return cls(translations=result)
