"""Report service.

TODO(Phase 6-B): Wire up IntelligenceReportRepository for actual data fetching.
"""

from __future__ import annotations

from typing import Any


class ReportService:
    """Business logic for report operations.

    TODO(Phase 6-B): Replace stub with real repository-based implementation.
    """

    async def list_reports(self, offset: int = 0, limit: int = 20) -> list[dict[str, Any]]:
        """Return paginated reports.

        TODO(Phase 6-B): Query IntelligenceReportRepository instead of returning empty list.
        """
        del offset, limit  # Unused until wired up
        return []
