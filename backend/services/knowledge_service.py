"""Knowledge item service.

TODO(Phase 6-B): Wire up KnowledgeItemRepository for actual data fetching.
"""

from __future__ import annotations

from typing import Any


class KnowledgeService:
    """Business logic for knowledge operations.

    TODO(Phase 6-B): Replace stub with real repository-based implementation.
    """

    async def list_knowledge_items(self, offset: int = 0, limit: int = 20) -> list[dict[str, Any]]:
        """Return paginated knowledge items.

        TODO(Phase 6-B): Query KnowledgeItemRepository instead of returning empty list.
        """
        del offset, limit  # Unused until wired up
        return []
