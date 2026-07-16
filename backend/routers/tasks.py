"""Tasks API router.

TODO(Phase 6-B): Wire up TaskService for actual data fetching.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..schemas.task import TaskResponse
from ..schemas.response import APIResponse
from .deps import get_db
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
    service = TaskService()
    tasks = await service.list_tasks(offset=pagination.offset, limit=pagination.limit)
    return APIResponse(success=True, data=tasks, error=None)
