"""Agent run business logic service."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.agent_run_repository import AgentRunRepository


class AgentService:
    """Business logic for agent run operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = AgentRunRepository(session)

    async def list_agent_runs(self, offset: int = 0, limit: int = 20) -> list[dict[str, Any]]:
        """Return paginated agent runs as dicts for response serialization."""
        runs = await self._repo.list_all(offset=offset, limit=limit)
        return [self._to_dict(r) for r in runs]

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
