"""Articles API router."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..schemas.article import ArticleResponse
from ..schemas.response import APIResponse
from .deps import get_db
from .pagination import PaginationParams, get_pagination
from ..services.article_service import ArticleService

router = APIRouter(
    prefix="/articles",
    tags=["articles"],
    responses={404: {"description": "Resource not found"}},
)


@router.get(
    "",
    summary="List articles",
    description="Return a paginated list of intelligence articles.",
    operation_id="listArticles",
    response_model=APIResponse[list[ArticleResponse]],
)
async def list_articles(
    pagination: PaginationParams = Depends(get_pagination),
    db=Depends(get_db),
):
    service = ArticleService(db)
    articles = await service.list_articles(offset=pagination.offset, limit=pagination.limit)
    return APIResponse(success=True, data=articles, error=None)
