"""Agent quality evaluation service.

Evaluates agent run outputs using an LLM to score quality across
four criteria: accuracy, relevance, actionability, completeness.

Features (Phase 12):
- Sampling-based cost control (evaluation_sample_rate)
- Cheaper model routing for evaluations (evaluation_model config)
- Content-hash based result caching (evaluation_cache table)
- Self-assessed confidence scoring from LLM
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random

from ...services.llm.base import ChatMessage, ChatResponse, ChatRole
from ...services.llm.client import LLMClient
from .prompts import build_autonomous_prompt, build_intelligence_prompt
from .repository import EvaluationCacheRepository
from .schemas import EvaluationResponse

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 30

_PIPELINE_PROMPTS = {
    "intelligence": build_intelligence_prompt,
    "autonomous": build_autonomous_prompt,
}


class EvaluationService:
    """Evaluate agent run quality via LLM with cost control."""

    def __init__(
        self,
        llm_client: LLMClient,
        *,
        sample_rate: float = 1.0,
        cache_ttl_seconds: int = 86400,
        evaluation_model: str = "",
    ) -> None:
        self._llm_client = llm_client
        self._sample_rate = sample_rate
        self._cache_ttl_seconds = cache_ttl_seconds
        self._evaluation_model = evaluation_model or None

    async def evaluate(
        self,
        pipeline_type: str,
        output_payload: dict,
        input_payload: dict,
        *,
        session=None,
    ) -> EvaluationResponse | None:
        """Run an LLM-based quality evaluation on a completed agent run.

        Applies sampling, cache lookup, and cheap model routing.
        Returns None if sampling skips or on any failure.
        """
        # 1. Sampling check
        if self._sample_rate < 1.0 and random.random() > self._sample_rate:
            logger.debug("Evaluation skipped by sampling (rate=%.1f)", self._sample_rate)
            return None

        # 2. Cache lookup
        content_hash = self._compute_hash(input_payload, output_payload)
        cached = None
        if session is not None:
            try:
                cache_repo = EvaluationCacheRepository(session)
                cached = await cache_repo.get_by_hash(content_hash)
                if cached and self._is_cache_fresh(cached.evaluated_at):
                    logger.info("Evaluation cache hit for hash %s", content_hash[:8])
                    return EvaluationResponse(
                        score=cached.score,
                        criteria=cached.criteria,
                        evaluator_notes=cached.evaluator_notes,
                        evaluator_confidence=None,
                        model_used=cached.model_used,
                        cached=True,
                    )
            except Exception:
                logger.warning("Cache lookup failed, proceeding to LLM", exc_info=True)

        # 3. Build prompt
        prompt_builder = _PIPELINE_PROMPTS.get(pipeline_type)
        if prompt_builder is None:
            logger.warning("No evaluation prompt for pipeline type %r", pipeline_type)
            return None

        messages = [
            ChatMessage(role=ChatRole.SYSTEM, content=msg["content"])
            for msg in prompt_builder(input_payload, output_payload)
        ]

        # 4. Call LLM with cheap model if configured
        kwargs: dict = {"temperature": 0.0}
        if self._evaluation_model:
            kwargs["model"] = self._evaluation_model
        else:
            kwargs["task"] = "evaluation"  # use models.yaml routing for cost-efficient model

        try:
            raw = await asyncio.wait_for(
                self._llm_client.chat(messages, **kwargs),
                timeout=_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.warning("Evaluation timed out for pipeline %s", pipeline_type)
            return None
        except Exception:
            logger.exception("Evaluation failed for pipeline %s", pipeline_type)
            return None

        response = self._parse_response(raw.content)
        if response is None:
            return None

        response.model_used = self._evaluation_model or raw.provider
        response.cached = False

        # 5. Store in cache
        if session is not None:
            try:
                cache_repo = EvaluationCacheRepository(session)
                await cache_repo.upsert(content_hash, pipeline_type, response)
            except Exception:
                logger.warning("Cache write failed", exc_info=True)

        return response

    @staticmethod
    def _compute_hash(input_payload: dict, output_payload: dict) -> str:
        """Compute SHA-256 hash of input+output for cache dedup."""
        combined = json.dumps(
            {"input": input_payload, "output": output_payload},
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    @staticmethod
    def _is_cache_fresh(evaluated_at) -> bool:
        """Check if cached result is within TTL."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        if evaluated_at.tzinfo is None:
            evaluated_at = evaluated_at.replace(tzinfo=timezone.utc)
        elapsed = (now - evaluated_at).total_seconds()
        return elapsed < 86400  # 24h default

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

        confidence = data.get("evaluator_confidence")
        if isinstance(confidence, (int, float)):
            confidence = float(confidence)
        elif not isinstance(confidence, float | int):
            confidence = None

        return EvaluationResponse(
            score=score,
            criteria=criteria,
            evaluator_notes=notes,
            evaluator_confidence=confidence,
            cached=False,
        )
