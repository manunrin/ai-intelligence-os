"""Agent quality evaluation service.

Evaluates agent run outputs using an LLM to score quality across
four criteria: accuracy, relevance, actionability, completeness.

Evaluation runs outside the LangGraph pipeline — triggered after
executor completion with graceful failure (never blocks run finalization).
"""

from __future__ import annotations

import json
import logging

from ...services.llm.base import ChatMessage, ChatRole
from ...services.llm.client import LLMClient
from .prompts import build_autonomous_prompt, build_intelligence_prompt
from .schemas import EvaluationResponse

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 30

_PIPELINE_PROMPTS = {
    "intelligence": build_intelligence_prompt,
    "autonomous": build_autonomous_prompt,
}


class EvaluationService:
    """Evaluate agent run quality via LLM."""

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def evaluate(
        self,
        pipeline_type: str,
        output_payload: dict,
        input_payload: dict,
    ) -> EvaluationResponse | None:
        """Run an LLM-based quality evaluation on a completed agent run.

        Returns None on any failure (timeout, parse error, missing LLM).
        """
        prompt_builder = _PIPELINE_PROMPTS.get(pipeline_type)
        if prompt_builder is None:
            logger.warning("No evaluation prompt for pipeline type %r", pipeline_type)
            return None

        try:
            import asyncio

            messages = [
                ChatMessage(
                    role=ChatRole.SYSTEM,
                    content=msg["content"],
                )
                for msg in prompt_builder(input_payload, output_payload)
            ]

            raw = await asyncio.wait_for(
                self._llm_client.chat(messages, temperature=0.0),
                timeout=_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.warning("Evaluation timed out for pipeline %s", pipeline_type)
            return None
        except Exception:
            logger.exception("Evaluation failed for pipeline %s", pipeline_type)
            return None

        return self._parse_response(raw.content)

    @staticmethod
    def _parse_response(content: str | None) -> EvaluationResponse | None:
        """Parse LLM JSON output into EvaluationResponse."""
        if not content:
            return None

        try:
            data = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            logger.warning("LLM returned non-JSON evaluation output")
            return None

        score = data.get("score")
        if isinstance(score, (int, float)):
            score = float(score)
        else:
            score = None

        criteria_raw = data.get("criteria")
        criteria: dict[str, float] | None = None
        if isinstance(criteria_raw, dict):
            criteria = {}
            for key, val in criteria_raw.items():
                if isinstance(val, (int, float)):
                    criteria[key] = float(val)

        notes = data.get("evaluator_notes")
        if not isinstance(notes, str):
            notes = None

        return EvaluationResponse(
            score=score,
            criteria=criteria,
            evaluator_notes=notes,
        )
