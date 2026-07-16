"""Reports API router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..schemas.report import IntelligenceReportResponse
from ..schemas.report_create import ReportCreate
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
    service = ReportService(db)
    reports = await service.list_reports(offset=pagination.offset, limit=pagination.limit)
    return APIResponse(success=True, data=reports, error=None)


@router.get(
    "/{report_id}",
    summary="Get report by ID",
    description="Return a single intelligence report by its UUID.",
    operation_id="getReport",
    response_model=APIResponse[IntelligenceReportResponse],
)
async def get_report(report_id: str, db=Depends(get_db)):
    service = ReportService(db)
    report = await service.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return APIResponse(success=True, data=report, error=None)


@router.post(
    "",
    summary="Create report",
    description="Create a new intelligence report.",
    operation_id="createReport",
    response_model=APIResponse[IntelligenceReportResponse],
)
async def create_report(
    data: ReportCreate,
    db=Depends(get_db),
):
    service = ReportService(db)
    report = await service.create_report(data)
    return APIResponse(success=True, data=report, error=None)
