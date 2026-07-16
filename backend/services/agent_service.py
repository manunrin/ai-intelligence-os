"""Agent run service.

TODO(Phase 6-B): Wire up AgentRunRepository for actual data fetching.
"""

from __future__ import annotations

from typing import Any


class AgentService:
    """Business logic for agent operations.

    TODO(Phase 6-B): Replace stub with real repository-based implementation.
    """

    async def list_agent_runs(self, offset: int = 0, limit: int = 20) -> list[dict[str, Any]]:
        """Return paginated agent runs.

        TODO(Phase 6-B): Query AgentRunRepository instead of returning empty list.
        """
        del offset, limit  # Unused until wired up
        return []
