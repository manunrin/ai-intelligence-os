"""Articles API router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from ..schemas.error import ErrorResponse
from ..schemas.article import ArticleResponse
from ..schemas.article_create import ArticleCreate, ArticleUpdate
from ..schemas.response import APIResponse
from .deps import get_current_user, get_article_service
from .pagination import PaginationParams, get_pagination
from ..services.article_service import ArticleService
from ..rate_limiter import limiter

router = APIRouter(
    prefix="/articles",
    tags=["articles"],
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
    summary="List articles",
    description="Return a paginated list of intelligence articles.",
    operation_id="listArticles",
    response_model=APIResponse[list[ArticleResponse]],
)
async def list_articles(
    pagination: PaginationParams = Depends(get_pagination),
    current_user: Any = Depends(get_current_user),
    service: ArticleService = Depends(get_article_service),
):
    articles = await service.list_articles(
        offset=pagination.offset, limit=pagination.limit, user_id=current_user.id
    )
    return APIResponse(success=True, data=articles, error=None)


@router.get(
    "/{article_id}",
    summary="Get article by ID",
    description="Return a single article by its UUID.",
    operation_id="getArticle",
    response_model=APIResponse[ArticleResponse],
)
async def get_article(
    article_id: str,
    current_user: Any = Depends(get_current_user),
    service: ArticleService = Depends(get_article_service),
):
    article = await service.get_article(article_id, user_id=current_user.id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return APIResponse(success=True, data=article, error=None)


@router.post(
    "",
    summary="Create article",
    description="Create a new intelligence article.",
    operation_id="createArticle",
    response_model=APIResponse[ArticleResponse],
)
@limiter.limit("100/hour")
async def create_article(
    data: ArticleCreate,
    request: Request,
    current_user: Any = Depends(get_current_user),
    service: ArticleService = Depends(get_article_service),
):
    article = await service.create_article(data, user_id=current_user.id)
    return APIResponse(success=True, data=article, error=None)


@router.put(
    "/{article_id}",
    summary="Update article",
    description="Update an existing article by its UUID.",
    operation_id="updateArticle",
    response_model=APIResponse[ArticleResponse],
)
@limiter.limit("100/hour")
async def update_article(
    article_id: str,
    request: Request,
    data: ArticleUpdate,
    current_user: Any = Depends(get_current_user),
    service: ArticleService = Depends(get_article_service),
):
    article = await service.update_article(article_id, data, user_id=current_user.id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return APIResponse(success=True, data=article, error=None)


@router.delete(
    "/{article_id}",
    summary="Delete article",
    description="Delete an article by its UUID.",
    operation_id="deleteArticle",
    response_model=APIResponse[None],
)
@limiter.limit("100/hour")
async def delete_article(
    article_id: str,
    request: Request,
    current_user: Any = Depends(get_current_user),
    service: ArticleService = Depends(get_article_service),
):
    deleted = await service.delete_article(article_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Article not found")
    return APIResponse(success=True, data=None, error=None)
