"""Tasks API router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from ..schemas.error import ErrorResponse
from ..schemas.response import APIResponse
from ..schemas.task import TaskResponse
from ..schemas.task_create import TaskCreate, TaskUpdate
from .deps import get_current_user, get_task_service
from .pagination import PaginationParams, get_pagination
from ..services.task_service import TaskService
from ..rate_limiter import limiter

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
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
    summary="List tasks",
    description="Return a paginated list of tasks.",
    operation_id="listTasks",
    response_model=APIResponse[list[TaskResponse]],
)
async def list_tasks(
    pagination: PaginationParams = Depends(get_pagination),
    current_user: Any = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    tasks = await service.list_tasks(
        offset=pagination.offset, limit=pagination.limit, user_id=current_user.id
    )
    return APIResponse(success=True, data=tasks, error=None)


@router.get(
    "/{task_id}",
    summary="Get task by ID",
    description="Return a single task by its UUID.",
    operation_id="getTask",
    response_model=APIResponse[TaskResponse],
)
async def get_task(
    task_id: str,
    current_user: Any = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    task = await service.get_task(task_id, user_id=current_user.id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return APIResponse(success=True, data=task, error=None)


@router.post(
    "",
    summary="Create task",
    description="Create a new actionable task.",
    operation_id="createTask",
    response_model=APIResponse[TaskResponse],
)
@limiter.limit("100/hour")
async def create_task(
    data: TaskCreate,
    request: Request,
    current_user: Any = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    task = await service.create_task(data, user_id=current_user.id)
    return APIResponse(success=True, data=task, error=None)


@router.put(
    "/{task_id}",
    summary="Update task",
    description="Update an existing task by its UUID.",
    operation_id="updateTask",
    response_model=APIResponse[TaskResponse],
)
@limiter.limit("100/hour")
async def update_task(
    task_id: str,
    request: Request,
    data: TaskUpdate,
    current_user: Any = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    task = await service.update_task(task_id, data, user_id=current_user.id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return APIResponse(success=True, data=task, error=None)


@router.delete(
    "/{task_id}",
    summary="Delete task",
    description="Delete a task by its UUID.",
    operation_id="deleteTask",
    response_model=APIResponse[None],
)
@limiter.limit("100/hour")
async def delete_task(
    task_id: str,
    request: Request,
    current_user: Any = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    deleted = await service.delete_task(task_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return APIResponse(success=True, data=None, error=None)
