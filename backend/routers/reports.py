"""Reports API router.

TODO(Phase 6-B): Wire up ReportService for actual data fetching.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..schemas.report import IntelligenceReportResponse
from ..schemas.response import APIResponse
from .deps import get_db
from .pagination import PaginationParams, get_pagination
from ..services.report_service import ReportService

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    responses={404: {"description": "Resource not found"}},
)


@router.get(
    "",
    summary="List intelligence reports",
    description="Return a paginated list of intelligence reports.",
    operation_id="listReports",
    response_model=APIResponse[list[IntelligenceReportResponse]],
)
async def list_reports(
    pagination: PaginationParams = Depends(get_pagination),
    db=Depends(get_db),
):
    service = ReportService()
    reports = await service.list_reports(offset=pagination.offset, limit=pagination.limit)
    return APIResponse(success=True, data=reports, error=None)
