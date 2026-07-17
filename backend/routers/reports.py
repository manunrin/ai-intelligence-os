"""Reports API router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from ..schemas.error import ErrorResponse
from ..schemas.report import IntelligenceReportResponse
from ..schemas.report_create import ReportCreate
from ..schemas.response import APIResponse
from .deps import get_current_user, get_db
from .pagination import PaginationParams, get_pagination
from ..services.report_service import ReportService


def _make_report_service(db, request):
    import sys
    mod = sys.modules[__name__]
    cls = getattr(mod, "ReportService", ReportService)
    return cls(db)


router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Unauthorized — invalid or missing token"},
        403: {"model": ErrorResponse, "description": "Forbidden — account deactivated or insufficient role"},
        404: {"model": ErrorResponse, "description": "Resource not found"},
        409: {"model": ErrorResponse, "description": "Conflict"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)


@router.get(
    "",
    summary="List intelligence reports",
    description="Return a paginated list of intelligence reports.",
    operation_id="listReports",
    response_model=APIResponse[list[IntelligenceReportResponse]],
)
async def list_reports(
    request: Request,
    pagination: PaginationParams = Depends(get_pagination),
    current_user: Any = Depends(get_current_user),
    db=Depends(get_db),
):
    service = _make_report_service(db, request)
    reports = await service.list_reports(
        offset=pagination.offset, limit=pagination.limit, user_id=current_user.id
    )
    return APIResponse(success=True, data=reports, error=None)


@router.get(
    "/{report_id}",
    summary="Get report by ID",
    description="Return a single intelligence report by its UUID.",
    operation_id="getReport",
    response_model=APIResponse[IntelligenceReportResponse],
)
async def get_report(
    request: Request,
    report_id: str,
    current_user: Any = Depends(get_current_user),
    db=Depends(get_db),
):
    service = _make_report_service(db, request)
    report = await service.get_report(report_id, user_id=current_user.id)
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
    request: Request,
    data: ReportCreate,
    current_user: Any = Depends(get_current_user),
    db=Depends(get_db),
):
    service = _make_report_service(db, request)
    report = await service.create_report(data, user_id=current_user.id)
    return APIResponse(success=True, data=report, error=None)
