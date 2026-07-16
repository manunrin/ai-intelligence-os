"""Agent runs API router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from ..schemas.agent_run import AgentRunResponse
from ..schemas.response import APIResponse
from .deps import get_current_user, get_db
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
    service = AgentService(db)
    runs = await service.list_agent_runs(offset=pagination.offset, limit=pagination.limit)
    return APIResponse(success=True, data=runs, error=None)


@router.post(
    "/{agent_id}/run",
    summary="Run agent",
    description="Trigger an agent workflow execution by agent ID.",
    operation_id="runAgent",
    response_model=APIResponse[AgentRunResponse],
)
async def run_agent(
    agent_id: str,
    body: dict[str, Any] | None = None,
    current_user: Any = Depends(get_current_user),
    db=Depends(get_db),
):
    """Trigger agent execution.

    Accepts an optional JSON body as input_payload for the agent workflow.
    The agent_id path parameter identifies which agent to execute.
    """
    service = AgentService(db)
    result = await service.run_agent(agent_id, input_payload=body)
    return APIResponse(success=True, data=result, error=None)
