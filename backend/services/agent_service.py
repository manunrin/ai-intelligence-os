"""Agent run business logic service."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.agent_run_repository import AgentRunRepository

logger = logging.getLogger(__name__)


class AgentService:
    """Business logic for agent run operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = AgentRunRepository(session)

    async def list_agent_runs(self, offset: int = 0, limit: int = 20) -> list[dict[str, Any]]:
        """Return paginated agent runs as dicts for response serialization."""
        runs = await self._repo.list_all(offset=offset, limit=limit)
        return [self._to_dict(r) for r in runs]

    async def run_agent(self, agent_id: str, input_payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Trigger an agent workflow execution by agent ID.

        Creates an AgentRun record with status 'running', logs the trigger,
        and returns the run record as a dict.
        """
        from datetime import datetime, timezone
        import uuid

        run_id = uuid.uuid4()
        kwargs: dict[str, Any] = {
            "id": run_id,
            "agent_id": uuid.UUID(agent_id),
            "workflow_id": None,
            "status": "running",
            "input_payload": input_payload or {},
            "output_payload": None,
            "error_message": None,
            "started_at": datetime.now(timezone.utc),
            "finished_at": None,
            "duration_ms": None,
        }
        run = await self._repo.create(**kwargs)
        logger.info("Agent run triggered: agent=%s run=%s", agent_id, str(run_id))
        return self._to_dict(run)

    @staticmethod
    def _to_dict(run: Any) -> dict[str, Any]:
        """Convert ORM model to serializable dict."""
        return {
            "id": str(run.id),
            "agent_id": str(run.agent_id),
            "workflow_id": str(run.workflow_id) if run.workflow_id else None,
            "status": run.status,
            "input_payload": run.input_payload,
            "output_payload": run.output_payload,
            "error_message": run.error_message,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        }
