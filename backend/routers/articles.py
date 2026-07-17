"""Articles API router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from ..schemas.error import ErrorResponse
from ..schemas.article import ArticleResponse
from ..schemas.article_create import ArticleCreate, ArticleUpdate
from ..schemas.response import APIResponse
from .deps import get_current_user, get_db
from .pagination import PaginationParams, get_pagination
from ..services.article_service import ArticleService


def _make_article_service(db, request):
    import sys
    mod = sys.modules[__name__]
    cls = getattr(mod, "ArticleService", ArticleService)
    return cls(db)


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
    request: Request,
    pagination: PaginationParams = Depends(get_pagination),
    current_user: Any = Depends(get_current_user),
    db=Depends(get_db),
):
    service = _make_article_service(db, request)
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
    request: Request,
    article_id: str,
    current_user: Any = Depends(get_current_user),
    db=Depends(get_db),
):
    service = _make_article_service(db, request)
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
async def create_article(
    request: Request,
    data: ArticleCreate,
    current_user: Any = Depends(get_current_user),
    db=Depends(get_db),
):
    service = _make_article_service(db, request)
    article = await service.create_article(data, user_id=current_user.id)
    return APIResponse(success=True, data=article, error=None)


@router.put(
    "/{article_id}",
    summary="Update article",
    description="Update an existing article by its UUID.",
    operation_id="updateArticle",
    response_model=APIResponse[ArticleResponse],
)
async def update_article(
    request: Request,
    article_id: str,
    data: ArticleUpdate,
    current_user: Any = Depends(get_current_user),
    db=Depends(get_db),
):
    service = _make_article_service(db, request)
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
async def delete_article(
    request: Request,
    article_id: str,
    current_user: Any = Depends(get_current_user),
    db=Depends(get_db),
):
    service = _make_article_service(db, request)
    deleted = await service.delete_article(article_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Article not found")
    return APIResponse(success=True, data=None, error=None)
