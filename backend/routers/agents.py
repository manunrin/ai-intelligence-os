"""Agent runs API router."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from ..schemas.agent_run import (
    AgentRunRequest,
    AgentRunResponse,
    AgentRunWithStages,
)
from ..schemas.error import ErrorResponse
from ..schemas.response import APIResponse
from .deps import get_current_user, get_runtime_service_with_event_pub
from .pagination import PaginationParams, get_pagination
from ..services.agent_runtime_service import (
    AgentRuntimeService,
    AgentRunNotFoundError,
)
from ..services.agent_runtime_service import _run_to_dict
from ..rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/agents",
    tags=["agents"],
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


# ── List available agent pipelines ──────────────────────────────────

@router.get(
    "/",
    summary="List available agents",
    description="Return available agent types and their descriptions.",
    operation_id="listAgents",
    response_model=APIResponse[list[dict[str, Any]]],
)
async def list_agents():
    pipelines = [
        {
            "type": "intelligence",
            "name": "Daily Intelligence",
            "description": "Research → Analyze → Translate",
            "nodes": 3,
        },
        {
            "type": "autonomous",
            "name": "Autonomous Intelligence",
            "description": "Full pipeline with knowledge extraction and project planning",
            "nodes": 6,
        },
    ]
    return APIResponse(success=True, data=pipelines, error=None)


# ── List agent runs ─────────────────────────────────────────────────

@router.get(
    "/runs",
    summary="List agent runs",
    description="Return a paginated list of agent execution records.",
    operation_id="listAgentRuns",
    response_model=APIResponse[list[AgentRunResponse]],
)
async def list_agent_runs(
    pagination: PaginationParams = Depends(get_pagination),
    current_user: Any = Depends(get_current_user),
    service: AgentRuntimeService = Depends(get_runtime_service_with_event_pub),
):
    runs = await service.list_agent_runs(
        current_user.id, offset=pagination.offset, limit=pagination.limit
    )
    return APIResponse(success=True, data=runs, error=None)


# ── Get single run by ID ────────────────────────────────────────────

@router.get(
    "/runs/{run_id}",
    summary="Get agent run",
    description="Return a single agent run with stage progress details.",
    operation_id="getAgentRun",
    response_model=APIResponse[AgentRunWithStages],
)
async def get_agent_run(
    run_id: str,
    current_user: Any = Depends(get_current_user),
    service: AgentRuntimeService = Depends(get_runtime_service_with_event_pub),
):
    result = await service.get_run(run_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")
    return APIResponse(success=True, data=result, error=None)


# ── Submit agent run (async) ────────────────────────────────────────

@router.post(
    "/run",
    summary="Submit agent run",
    description="Asynchronously submit an agent workflow for execution. Returns immediately with run ID.",
    operation_id="submitAgentRun",
    response_model=APIResponse[AgentRunResponse],
)
@limiter.limit("20/hour")
async def submit_agent_run(
    body: AgentRunRequest,
    request: Request,
    current_user: Any = Depends(get_current_user),
    service: AgentRuntimeService = Depends(get_runtime_service_with_event_pub),
):
    # Merge input_payload with convenience fields
    payload = dict(body.input_payload)
    payload["_agent_type"] = body.agent_type
    if body.topic:
        payload["topic"] = body.topic
    if body.source_id:
        payload["source_id"] = body.source_id

    run = await service.submit(
        agent_type=body.agent_type,
        input_payload=payload,
        user_id=current_user.id,
    )
    return APIResponse(success=True, data=run, error=None)


# ── SSE streaming endpoint ──────────────────────────────────────────

@router.get(
    "/runs/{run_id}/stream",
    summary="Stream agent progress",
    description="Stream agent execution progress as Server-Sent Events.",
    operation_id="streamAgentProgress",
)
async def stream_agent_status(
    run_id: str,
    current_user: Any = Depends(get_current_user),
    service: AgentRuntimeService = Depends(get_runtime_service_with_event_pub),
):
    async def event_stream():
        async for event_str in service.stream_events(run_id):
            yield event_str

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Cancel agent run ────────────────────────────────────────────────

@router.post(
    "/runs/{run_id}/cancel",
    summary="Cancel agent run",
    description="Cancel a running agent execution.",
    operation_id="cancelAgentRun",
    response_model=APIResponse[dict[str, Any]],
)
@limiter.limit("20/hour")
async def cancel_agent_run(
    run_id: str,
    request: Request,
    current_user: Any = Depends(get_current_user),
    service: AgentRuntimeService = Depends(get_runtime_service_with_event_pub),
):
    result = await service.cancel_run(run_id, user_id=current_user.id)
    return APIResponse(success=True, data=result, error=None)


# ── Backward-compatible: POST /{agent_id}/run ───────────────────────

@router.post(
    "/{agent_id}/run",
    summary="Run agent (legacy)",
    description="Trigger an agent workflow execution by agent ID. Deprecated — use POST /run instead.",
    operation_id="runAgent",
    response_model=APIResponse[AgentRunResponse],
)
async def run_agent(
    agent_id: str,
    body: dict[str, Any] | None = None,
    current_user: Any = Depends(get_current_user),
    service: AgentRuntimeService = Depends(get_runtime_service_with_event_pub),
):
    """Legacy endpoint — delegates to runtime service with 'intelligence' pipeline type."""
    payload = body or {}
    payload.setdefault("agent_id", agent_id)
    run = await service.submit(
        agent_type="intelligence",
        input_payload=payload,
        user_id=current_user.id,
    )
    return APIResponse(success=True, data=run, error=None)
