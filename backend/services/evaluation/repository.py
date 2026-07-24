"""Repository for agent evaluation persistence and caching."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import AgentEvaluation, EvaluationCache
from .schemas import EvaluationResponse


class AgentEvaluationRepository:
    """CRUD operations for agent quality evaluations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **kwargs: Any) -> AgentEvaluation:
        instance = AgentEvaluation(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def get_by_run_id(self, run_id: uuid.UUID) -> AgentEvaluation | None:
        stmt = select(AgentEvaluation).where(
            AgentEvaluation.agent_run_id == run_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_run_ids(self, run_ids: list[uuid.UUID]) -> list[AgentEvaluation]:
        if not run_ids:
            return []
        stmt = select(AgentEvaluation).where(
            AgentEvaluation.agent_run_id.in_(run_ids)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class EvaluationCacheRepository:
    """CRUD operations for evaluation cache."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_hash(self, content_hash: str) -> EvaluationCache | None:
        stmt = select(EvaluationCache).where(
            EvaluationCache.content_hash == content_hash
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(self, content_hash: str, pipeline_type: str, response: EvaluationResponse) -> None:
        """Insert or update cache entry (upsert)."""
        from datetime import datetime, timezone

        existing = await self.get_by_hash(content_hash)
        if existing is not None:
            existing.score = response.score or 0
            existing.criteria = response.criteria or {}
            existing.evaluator_notes = response.evaluator_notes
            existing.model_used = response.model_used
        else:
            instance = EvaluationCache(
                id=uuid.uuid4().hex[:32],
                content_hash=content_hash,
                pipeline_type=pipeline_type,
                score=response.score or 0,
                criteria=response.criteria or {},
                evaluator_notes=response.evaluator_notes,
                model_used=response.model_used,
                evaluated_at=datetime.now(timezone.utc),
            )
            self.session.add(instance)
        await self.session.flush()
