"""Articles API router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..schemas.article import ArticleResponse
from ..schemas.article_create import ArticleCreate, ArticleUpdate
from ..schemas.response import APIResponse
from .deps import get_current_user, get_db
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


@router.get(
    "/{article_id}",
    summary="Get article by ID",
    description="Return a single article by its UUID.",
    operation_id="getArticle",
    response_model=APIResponse[ArticleResponse],
)
async def get_article(article_id: str, db=Depends(get_db)):
    service = ArticleService(db)
    article = await service.get_article(article_id)
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
    data: ArticleCreate,
    current_user: Any = Depends(get_current_user),
    db=Depends(get_db),
):
    service = ArticleService(db)
    article = await service.create_article(data)
    return APIResponse(success=True, data=article, error=None)


@router.put(
    "/{article_id}",
    summary="Update article",
    description="Update an existing article by its UUID.",
    operation_id="updateArticle",
    response_model=APIResponse[ArticleResponse],
)
async def update_article(
    article_id: str,
    data: ArticleUpdate,
    current_user: Any = Depends(get_current_user),
    db=Depends(get_db),
):
    service = ArticleService(db)
    article = await service.update_article(article_id, data)
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
async def delete_article(article_id: str, current_user: Any = Depends(get_current_user), db=Depends(get_db)):
    service = ArticleService(db)
    deleted = await service.delete_article(article_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Article not found")
    return APIResponse(success=True, data=None, error=None)
