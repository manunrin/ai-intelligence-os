"""Qdrant vector store client — upsert, search, delete operations."""

from __future__ import annotations

import logging
import time as _time
from typing import Any
from uuid import UUID

import httpx

from ...metrics import counter, histogram
from ...trace import start_span

logger = logging.getLogger(__name__)


class QdrantPoint:
    """A single point stored in Qdrant."""

    def __init__(
        self,
        id: str | UUID,
        vector: list[float],
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.id = str(id)
        self.vector = vector
        self.payload = payload or {}


class QdrantVectorService:
    """Thin httpx-based client for Qdrant vector operations.

    Manages collections for semantic search over KnowledgeItems.
    """

    DEFAULT_COLLECTION = "knowledge_items"
    DEFAULT_VECTOR_SIZE = 1024  # bge-m3 embedding dimension

    def __init__(
        self,
        url: str = "http://localhost:6333",
        api_key: str | None = None,
        collection_name: str | None = None,
        vector_size: int = DEFAULT_VECTOR_SIZE,
    ) -> None:
        self._url = url.rstrip("/")
        self._api_key = api_key
        self._collection = collection_name or self.DEFAULT_COLLECTION
        self._vector_size = vector_size
        headers: dict[str, str] = {}
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        self._client = httpx.AsyncClient(
            base_url=self._url,
            headers=headers,
            timeout=httpx.Timeout(30.0),
        )

    async def ensure_collection(self) -> None:
        """Create the collection if it does not already exist."""
        try:
            resp = await self._client.get(f"/collections/{self._collection}")
            if resp.status_code == 200:
                return
            if resp.status_code == 404:
                pass  # Collection does not exist; create it below.
            else:
                resp.raise_for_status()
                return
        except httpx.HTTPError as exc:
            logger.error(
                "Failed to check Qdrant collection '%s': %s",
                self._collection,
                exc,
            )
            raise

        try:
            await self._client.put(
                f"/collections/{self._collection}",
                json={
                    "vectors": {
                        "size": self._vector_size,
                        "distance": "Cosine",
                    }
                },
            )
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Failed to create Qdrant collection '%s': %s",
                self._collection,
                exc.response.text,
            )
            raise
        logger.info("Created Qdrant collection '%s' (%d-dim)", self._collection, self._vector_size)

    async def upsert(self, points: list[QdrantPoint]) -> None:
        """Upsert multiple points into the collection."""
        if not points:
            return
        with start_span("vector.upsert", attributes={
            "db.system": "qdrant",
            "db.collection": self._collection,
        }) as span:
            start = _time.monotonic()
            try:
                payloads = [
                    {"id": p.id, "vector": p.vector, "payload": p.payload}
                    for p in points
                ]
                resp = await self._client.put(
                    f"/collections/{self._collection}/points",
                    json={"points": payloads},
                )
                resp.raise_for_status()
                elapsed = _time.monotonic() - start
                counter("vector_operations_total", labels={"operation": "upsert", "status": "success"})
                histogram("vector_operation_duration_seconds", elapsed, labels={"operation": "upsert", "status": "success"})
                logger.info("Upserted %d points into '%s'", len(points), self._collection)
            except Exception as exc:
                elapsed = _time.monotonic() - start
                counter("vector_operations_total", labels={"operation": "upsert", "status": "failed"})
                histogram("vector_operation_duration_seconds", elapsed, labels={"operation": "upsert", "status": "failed"})
                if hasattr(exc, "response"):
                    logger.error(
                        "Qdrant upsert failed with status %s: %s",
                        exc.response.status_code,
                        exc.response.text,
                    )
                raise

    async def search(
        self,
        query_vector: list[float],
        limit: int = 10,
        score_threshold: float | None = None,
        filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic search by vector."""
        with start_span("vector.search", attributes={
            "db.system": "qdrant",
            "db.collection": self._collection,
            "db.query.limit": str(limit),
        }) as span:
            start = _time.monotonic()
            try:
                params: dict[str, Any] = {
                    "limit": limit,
                }
                if score_threshold is not None:
                    params["score_threshold"] = score_threshold
                body: dict[str, Any] = {"vector": query_vector, "with_payload": True}
                if filter:
                    body["filter"] = filter

                resp = await self._client.post(
                    f"/collections/{self._collection}/points/search",
                    params=params,
                    json=body,
                )
                data = resp.json()
                results: list[dict[str, Any]] = []
                for hit in data.get("result", []):
                    results.append({
                        "id": hit.get("id"),
                        "score": hit.get("score"),
                        "payload": hit.get("payload", {}),
                    })
                elapsed = _time.monotonic() - start
                counter("vector_search_total", labels={"status": "success"})
                histogram("vector_search_duration_seconds", elapsed, labels={"status": "success"})
                return results
            except Exception as exc:
                elapsed = _time.monotonic() - start
                counter("vector_search_total", labels={"status": "failed"})
                histogram("vector_search_duration_seconds", elapsed, labels={"status": "failed"})
                raise

    async def delete(self, point_ids: list[str | UUID]) -> None:
        """Delete specific points by ID.

        Args:
            point_ids: List of point IDs to remove.
        """
        if not point_ids:
            return
        ids_str = [str(i) for i in point_ids]
        await self._client.post(
            f"/collections/{self._collection}/points/delete",
            json={"points": ids_str},
        )
        logger.info("Deleted %d points from '%s'", len(ids_str), self._collection)

    async def health_check(self) -> bool:
        """Check if Qdrant is reachable."""
        try:
            resp = await self._client.get("/health")
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.warning("Qdrant health check failed: %s", exc)
            return False

    async def close(self) -> None:
        await self._client.aclose()
