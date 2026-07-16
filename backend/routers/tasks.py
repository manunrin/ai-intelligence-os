"""Tasks API router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..schemas.response import APIResponse
from ..schemas.task import TaskResponse
from ..schemas.task_create import TaskCreate, TaskUpdate
from .deps import get_current_user, get_db
from .pagination import PaginationParams, get_pagination
from ..services.task_service import TaskService

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    responses={404: {"description": "Resource not found"}},
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
    db=Depends(get_db),
):
    service = TaskService(db)
    tasks = await service.list_tasks(offset=pagination.offset, limit=pagination.limit)
    return APIResponse(success=True, data=tasks, error=None)


@router.get(
    "/{task_id}",
    summary="Get task by ID",
    description="Return a single task by its UUID.",
    operation_id="getTask",
    response_model=APIResponse[TaskResponse],
)
async def get_task(task_id: str, db=Depends(get_db)):
    service = TaskService(db)
    task = await service.get_task(task_id)
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
async def create_task(
    data: TaskCreate,
    current_user: Any = Depends(get_current_user),
    db=Depends(get_db),
):
    service = TaskService(db)
    task = await service.create_task(data)
    return APIResponse(success=True, data=task, error=None)


@router.put(
    "/{task_id}",
    summary="Update task",
    description="Update an existing task by its UUID.",
    operation_id="updateTask",
    response_model=APIResponse[TaskResponse],
)
async def update_task(
    task_id: str,
    data: TaskUpdate,
    current_user: Any = Depends(get_current_user),
    db=Depends(get_db),
):
    service = TaskService(db)
    task = await service.update_task(task_id, data)
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
async def delete_task(task_id: str, current_user: Any = Depends(get_current_user), db=Depends(get_db)):
    service = TaskService(db)
    deleted = await service.delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return APIResponse(success=True, data=None, error=None)
