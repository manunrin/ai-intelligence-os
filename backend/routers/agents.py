"""Agent runs API router.

TODO(Phase 6-B): Wire up AgentService for actual data fetching.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..schemas.agent_run import AgentRunResponse
from ..schemas.response import APIResponse
from .deps import get_db
from .pagination import PaginationParams, get_pagination
from ..services.agent_service import AgentService

router = APIRouter(
    prefix="/agents",
    tags=["agents"],
    responses={404: {"description": "Resource not found"}},
)


@router.get(
    "/runs",
    summary="List agent runs",
    description="Return a paginated list of agent execution records.",
    operation_id="listAgentRuns",
    response_model=APIResponse[list[AgentRunResponse]],
)
async def list_agent_runs(
    pagination: PaginationParams = Depends(get_pagination),
    db=Depends(get_db),
):
    service = AgentService()
    runs = await service.list_agent_runs(offset=pagination.offset, limit=pagination.limit)
    return APIResponse(success=True, data=runs, error=None)
