"""Knowledge API router."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..schemas.knowledge import KnowledgeItemResponse
from ..schemas.response import APIResponse
from .deps import get_db
from .pagination import PaginationParams, get_pagination
from ..services.knowledge_service import KnowledgeService

router = APIRouter(
    prefix="/knowledge",
    tags=["knowledge"],
    responses={404: {"description": "Resource not found"}},
)


@router.get(
    "",
    summary="List knowledge items",
    description="Return a paginated list of knowledge items.",
    operation_id="listKnowledgeItems",
    response_model=APIResponse[list[KnowledgeItemResponse]],
)
async def list_knowledge(
    pagination: PaginationParams = Depends(get_pagination),
    db=Depends(get_db),
):
    service = KnowledgeService(db)
    items = await service.list_knowledge_items(
        offset=pagination.offset, limit=pagination.limit
    )
    return APIResponse(success=True, data=items, error=None)
