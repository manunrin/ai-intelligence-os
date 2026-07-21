"""Knowledge items API router."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from ..schemas.error import ErrorResponse
from ..schemas.knowledge import KnowledgeItemResponse
from ..schemas.knowledge_create import KnowledgeItemCreate, KnowledgeItemUpdate
from ..schemas.response import APIResponse
from ..schemas.rag import RAGRequest, RAGResponse, RAGSource
from ..schemas.search import SearchRequest, SearchResponse, SearchResult
from .deps import get_current_user, get_db, get_embedding_client, get_knowledge_service, get_llm_provider, get_vector_service
from .pagination import PaginationParams, get_pagination
from ..services.knowledge_service import KnowledgeItemService
from ..services.rag.generator import RagGenerator
from ..services.rag.retriever import RagRetriever
from ..rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/knowledge",
    tags=["knowledge"],
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
    summary="List knowledge items",
    description="Return a paginated list of knowledge items.",
    operation_id="listKnowledgeItems",
    response_model=APIResponse[list[KnowledgeItemResponse]],
)
async def list_knowledge(
    pagination: PaginationParams = Depends(get_pagination),
    current_user: Any = Depends(get_current_user),
    service: KnowledgeItemService = Depends(get_knowledge_service),
):
    items = await service.list_knowledge_items(
        offset=pagination.offset, limit=pagination.limit, user_id=current_user.id
    )
    return APIResponse(success=True, data=items, error=None)


@router.get(
    "/{item_id}",
    summary="Get knowledge item by ID",
    description="Return a single knowledge item by its UUID.",
    operation_id="getKnowledgeItem",
    response_model=APIResponse[KnowledgeItemResponse],
)
async def get_knowledge_item(
    item_id: str,
    current_user: Any = Depends(get_current_user),
    service: KnowledgeItemService = Depends(get_knowledge_service),
):
    item = await service.get_knowledge_item(item_id, user_id=current_user.id)
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
@limiter.limit("100/hour")
async def create_knowledge_item(
    data: KnowledgeItemCreate,
    request: Request,
    current_user: Any = Depends(get_current_user),
    service: KnowledgeItemService = Depends(get_knowledge_service),
):
    item = await service.create_knowledge_item(data, user_id=current_user.id)
    return APIResponse(success=True, data=item, error=None)


@router.put(
    "/{item_id}",
    summary="Update knowledge item",
    description="Update an existing knowledge item by its UUID.",
    operation_id="updateKnowledgeItem",
    response_model=APIResponse[KnowledgeItemResponse],
)
@limiter.limit("100/hour")
async def update_knowledge_item(
    item_id: str,
    request: Request,
    data: KnowledgeItemUpdate,
    current_user: Any = Depends(get_current_user),
    service: KnowledgeItemService = Depends(get_knowledge_service),
):
    item = await service.update_knowledge_item(item_id, data, user_id=current_user.id)
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
@limiter.limit("100/hour")
async def delete_knowledge_item(
    item_id: str,
    request: Request,
    current_user: Any = Depends(get_current_user),
    service: KnowledgeItemService = Depends(get_knowledge_service),
):
    deleted = await service.delete_knowledge_item(item_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    return APIResponse(success=True, data=None, error=None)


@router.post(
    "/search",
    summary="Semantic knowledge search",
    description="Search knowledge items using vector similarity.",
    operation_id="searchKnowledge",
    response_model=APIResponse[SearchResponse],
)
@limiter.limit("100/hour")
async def search_knowledge(
    body: SearchRequest,
    request: Request,
    db=Depends(get_db),
    embedding_client=Depends(get_embedding_client),
    vector_service=Depends(get_vector_service),
):
    """Perform semantic search over knowledge items.

    Uses RagRetriever which chains:
        Query → Embed → Vector Search → DB Fetch → Ranked Results

    Falls back to keyword search if embedding or vector store is unavailable.
    """
    retriever = RagRetriever(
        session=db,
        embedding_client=embedding_client,
        vector_service=vector_service,
    )

    results = await retriever.retrieve(
        query=body.query,
        limit=body.limit,
        score_threshold=body.score_threshold,
        kind_filter=body.kind_filter,
        tag_filter=body.tag_filter,
    )

    search_results = [
        SearchResult(
            knowledge_id=r.knowledge_id,
            title=r.title,
            content=r.content,
            kind=r.kind,
            score=r.score,
            tags=r.tags,
        )
        for r in results
    ]

    return APIResponse(
        success=True,
        data=SearchResponse(results=search_results),
        error=None,
    )


@router.post(
    "/rag",
    summary="RAG question answering",
    description="Generate an answer from retrieved knowledge items using LLM.",
    operation_id="ragQuestionAnswering",
    response_model=APIResponse[RAGResponse],
)
@limiter.limit("50/hour")
async def rag_question_answering(
    body: RAGRequest,
    request: Request,
    db=Depends(get_db),
    embedding_client=Depends(get_embedding_client),
    vector_service=Depends(get_vector_service),
    llm_provider=Depends(get_llm_provider),
):
    """Perform RAG question answering over knowledge items.

    Uses RagRetriever to fetch relevant context, then RagGenerator to synthesize
    an answer with LLM. Falls back to keyword search if embedding or vector store
    is unavailable.
    """
    retriever = RagRetriever(
        session=db,
        embedding_client=embedding_client,
        vector_service=vector_service,
    )

    # Retrieve context with optional kind/tag filters
    context = await retriever.retrieve(
        query=body.query,
        limit=body.limit,
        kind_filter=body.kind_filter,
        tag_filter=body.tag_filter,
    )

    if not context:
        return APIResponse(
            success=True,
            data=RAGResponse(
                answer="No relevant knowledge items found for your query.",
                sources=[],
                query=body.query,
            ),
            error=None,
        )

    # Generate answer
    generator = RagGenerator(provider=llm_provider)

    try:
        result = await generator.generate(
            query=body.query,
            context=context,
            system_prompt=body.system_prompt,
        )
    except Exception as exc:
        logger.warning("RAG generation failed: %s", exc)
        return APIResponse(
            success=False,
            data=None,
            error=ErrorResponse(
                code="RAG_GENERATION_FAILED",
                message=f"Failed to generate answer: {str(exc)}",
            ),
        )

    # Format sources
    sources = [
        RAGSource(knowledge_id=s["knowledge_id"], title=s["title"])
        for s in result.get("sources", [])
    ]

    return APIResponse(
        success=True,
        data=RAGResponse(
            answer=result.get("answer", ""),
            sources=sources,
            query=body.query,
        ),
        error=None,
    )


@router.post(
    "/rag/stream",
    summary="RAG question answering (streaming)",
    description="Stream RAG answers token by token via Server-Sent Events.",
    operation_id="ragQuestionAnsweringStream",
)
@limiter.limit("50/hour")
async def rag_question_answering_stream(
    body: RAGRequest,
    request: Request,
    db=Depends(get_db),
    embedding_client=Depends(get_embedding_client),
    vector_service=Depends(get_vector_service),
    llm_provider=Depends(get_llm_provider),
):
    """Perform streaming RAG question answering over knowledge items.

    Uses RagRetriever to fetch relevant context, then RagGenerator to synthesize
    an answer with LLM, streaming tokens as Server-Sent Events.
    """
    retriever = RagRetriever(
        session=db,
        embedding_client=embedding_client,
        vector_service=vector_service,
    )

    context = await retriever.retrieve(
        query=body.query,
        limit=body.limit,
        kind_filter=body.kind_filter,
        tag_filter=body.tag_filter,
    )

    if not context:
        async def empty_stream():
            yield "data: {}\n\n"
        return StreamingResponse(
            empty_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    generator = RagGenerator(provider=llm_provider)

    async def event_stream():
        try:
            async for event in generator.generate_stream(
                query=body.query,
                context=context,
                system_prompt=body.system_prompt,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:
            logger.warning("RAG streaming failed: %s", exc)
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
