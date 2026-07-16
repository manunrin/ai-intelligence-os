"""Knowledge items API router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..schemas.knowledge import KnowledgeItemResponse
from ..schemas.knowledge_create import KnowledgeItemCreate, KnowledgeItemUpdate
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


@router.get(
    "/{item_id}",
    summary="Get knowledge item by ID",
    description="Return a single knowledge item by its UUID.",
    operation_id="getKnowledgeItem",
    response_model=APIResponse[KnowledgeItemResponse],
)
async def get_knowledge_item(item_id: str, db=Depends(get_db)):
    service = KnowledgeService(db)
    item = await service.get_knowledge_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    return APIResponse(success=True, data=item, error=None)


@router.post(
    "",
    summary="Create knowledge item",
    description="Create a new persisted knowledge entry.",
    operation_id="createKnowledgeItem",
    response_model=APIResponse[KnowledgeItemResponse],
)
async def create_knowledge_item(
    data: KnowledgeItemCreate,
    db=Depends(get_db),
):
    service = KnowledgeService(db)
    item = await service.create_knowledge_item(data)
    return APIResponse(success=True, data=item, error=None)


@router.put(
    "/{item_id}",
    summary="Update knowledge item",
    description="Update an existing knowledge item by its UUID.",
    operation_id="updateKnowledgeItem",
    response_model=APIResponse[KnowledgeItemResponse],
)
async def update_knowledge_item(
    item_id: str,
    data: KnowledgeItemUpdate,
    db=Depends(get_db),
):
    service = KnowledgeService(db)
    item = await service.update_knowledge_item(item_id, data)
    if item is None:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    return APIResponse(success=True, data=item, error=None)


@router.delete(
    "/{item_id}",
    summary="Delete knowledge item",
    description="Delete a knowledge item by its UUID.",
    operation_id="deleteKnowledgeItem",
    response_model=APIResponse[None],
)
async def delete_knowledge_item(item_id: str, db=Depends(get_db)):
    service = KnowledgeService(db)
    deleted = await service.delete_knowledge_item(item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    return APIResponse(success=True, data=None, error=None)
