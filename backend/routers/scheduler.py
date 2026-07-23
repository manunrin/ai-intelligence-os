"""Scheduler API router — CRUD for scheduled jobs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..rate_limiter import limiter
from ..schemas.error import ErrorResponse
from ..schemas.response import APIResponse
from .deps import get_current_user, get_runtime_service, get_scheduler_service
from ..services.scheduler.service import SchedulerService


router = APIRouter(
    prefix="/scheduler/jobs",
    tags=["scheduler"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Unauthorized — invalid or missing token"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Resource not found"},
        409: {"model": ErrorResponse, "description": "Conflict — duplicate name"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)


# ── List scheduled jobs ───────────────────────────────────────────────

@router.get(
    "/",
    summary="List scheduled jobs",
    description="Return all scheduled jobs.",
    operation_id="listScheduledJobs",
    response_model=APIResponse[list[dict[str, Any]]],
)
async def list_jobs(
    current_user: Any = Depends(get_current_user),
    scheduler: SchedulerService = Depends(get_scheduler_service),
):
    jobs = await scheduler.list_jobs()
    return APIResponse(success=True, data=jobs, error=None)


# ── Create scheduled job ──────────────────────────────────────────────

@router.post(
    "/",
    summary="Create scheduled job",
    description="Create a new scheduled job and register it with APScheduler.",
    operation_id="createScheduledJob",
    response_model=APIResponse[dict[str, Any]],
)
@limiter.limit("20/hour")
async def create_job(
    body: dict[str, Any],
    request: Request,
    current_user: Any = Depends(get_current_user),
    scheduler: SchedulerService = Depends(get_scheduler_service),
):
    try:
        job = await scheduler.create_job(
            name=body["name"],
            cron_expression=body["cron_expression"],
            job_type=body["job_type"],
            input_payload=body.get("input_payload"),
            user_id=current_user.id,
        )
    except ValueError as exc:
        detail = str(exc)
        if "already exists" in detail:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)
    return APIResponse(success=True, data=job, error=None)


# ── Update scheduled job ──────────────────────────────────────────────

@router.put(
    "/{job_id}",
    summary="Update scheduled job",
    description="Update a scheduled job by its UUID.",
    operation_id="updateScheduledJob",
    response_model=APIResponse[dict[str, Any]],
)
@limiter.limit("20/hour")
async def update_job(
    job_id: str,
    body: dict[str, Any],
    request: Request,
    current_user: Any = Depends(get_current_user),
    scheduler: SchedulerService = Depends(get_scheduler_service),
):
    try:
        job = await scheduler.update_job(
            job_id,
            name=body.get("name"),
            cron_expression=body.get("cron_expression"),
            job_type=body.get("job_type"),
            enabled=body.get("enabled"),
            input_payload=body.get("input_payload"),
        )
    except ValueError as exc:
        detail = str(exc)
        if "not found" in detail:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        if "already exists" in detail:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)
    return APIResponse(success=True, data=job, error=None)


# ── Delete scheduled job ──────────────────────────────────────────────

@router.delete(
    "/{job_id}",
    summary="Delete scheduled job",
    description="Remove a scheduled job by its UUID.",
    operation_id="deleteScheduledJob",
    response_model=APIResponse[None],
)
@limiter.limit("20/hour")
async def delete_job(
    job_id: str,
    request: Request,
    current_user: Any = Depends(get_current_user),
    scheduler: SchedulerService = Depends(get_scheduler_service),
):
    try:
        await scheduler.delete_job(job_id)
    except ValueError as exc:
        if "not found" in str(exc):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
        raise
    return APIResponse(success=True, data=None, error=None)


# ── Trigger scheduled job now ─────────────────────────────────────────

@router.post(
    "/{job_id}/trigger",
    summary="Trigger scheduled job now",
    description="Manually trigger a scheduled job immediately.",
    operation_id="triggerScheduledJob",
    response_model=APIResponse[dict[str, Any]],
)
@limiter.limit("10/hour")
async def trigger_job(
    job_id: str,
    request: Request,
    current_user: Any = Depends(get_current_user),
    scheduler: SchedulerService = Depends(get_scheduler_service),
):
    try:
        job = await scheduler.trigger_job_now(job_id)
    except ValueError as exc:
        if "not found" in str(exc):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
        raise
    return APIResponse(success=True, data=job, error=None)
