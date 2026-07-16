"""Task service.

TODO(Phase 6-B): Wire up TaskRepository for actual data fetching.
"""

from __future__ import annotations

from typing import Any


class TaskService:
    """Business logic for task operations.

    TODO(Phase 6-B): Replace stub with real repository-based implementation.
    """

    async def list_tasks(self, offset: int = 0, limit: int = 20) -> list[dict[str, Any]]:
        """Return paginated tasks.

        TODO(Phase 6-B): Query TaskRepository instead of returning empty list.
        """
        del offset, limit  # Unused until wired up
        return []
