"""Backfill embeddings for existing knowledge items.

This script reads all knowledge_items from the database, generates embeddings
using the configured embedding provider (Ollama bge-m3 by default), and
upserts vectors into Qdrant.

Usage:
    python scripts/backfill_embeddings.py              # skip items with embeddings
    python scripts/backfill_embeddings.py --force      # rebuild collection and embed all items
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.database.models.knowledge_item import KnowledgeItem
from backend.services.embedding.client import EmbeddingClient
from backend.services.embedding.base import LLMGatewayEmbeddingProvider
from backend.services.llm.router import LLMRouter
from backend.services.vector.qdrant import QdrantVectorService, QdrantPoint
from backend.config import get_settings


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def backfill_embeddings(force: bool = False):
    """Generate embeddings for knowledge items."""
    settings = get_settings()

    # Use host URLs when running outside Docker
    db_url = settings.database_url.replace(
        "postgresql://",
        "postgresql+asyncpg://"
    ).replace(
        "@postgres:",
        "@localhost:"
    )
    qdrant_url = settings.qdrant_url.replace("http://qdrant:6333", "http://localhost:6333")

    # Initialize components
    llm_router = LLMRouter()
    embedding_provider = LLMGatewayEmbeddingProvider(llm_router)
    embedding_client = EmbeddingClient(provider=embedding_provider)

    vector_service = QdrantVectorService(url=qdrant_url)

    if force:
        logger.info("Force mode: deleting and recreating Qdrant collection")
        try:
            await vector_service._client.delete(f"/collections/{vector_service._collection}")
            logger.info("Deleted existing collection '%s'", vector_service._collection)
        except Exception as exc:
            logger.warning("Could not delete collection (may not exist): %s", exc)

    await vector_service.ensure_collection()

    # Setup database session with local URL
    engine = create_async_engine(db_url)
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session_factory() as session:
            # Query all knowledge items
            result = await session.execute(
                __import__("sqlalchemy").select(KnowledgeItem)
            )
            items = result.scalars().all()

            total = len(items)
            processed = 0
            skipped = 0
            failed = 0

            logger.info(f"Found {total} knowledge items")

            for item in items:
                # Skip items that already have embeddings (unless force mode)
                if not force and item.embedding is not None:
                    skipped += 1
                    logger.debug(f"Skipping {item.id} (already embedded)")
                    continue

                try:
                    # Generate embedding for title + content
                    text = f"{item.title}\n{item.content}"
                    emb_result = await embedding_client.embed(text)

                    # Update database - store embedding metadata
                    item.embedding = emb_result.model
                    item.embedding_model = emb_result.model
                    item.embedding_dimension = len(emb_result.embedding)
                    session.add(item)
                    await session.commit()

                    # Upsert to Qdrant
                    point = QdrantPoint(
                        id=str(item.id),
                        vector=emb_result.embedding,
                        payload={
                            "title": item.title,
                            "kind": item.kind,
                            "tags": item.tags or [],
                            "user_id": str(item.user_id) if item.user_id else None,
                        },
                    )
                    await vector_service.upsert([point])

                    processed += 1
                    logger.info(
                        f"[{processed}/{total}] Embedded {item.id}: {item.title[:50]}..."
                    )

                except Exception as exc:
                    failed += 1
                    logger.error(
                        f"Failed to embed {item.id}: {exc}", exc_info=True
                    )

            logger.info(f"\nBackfill complete:")
            logger.info(f"  Total: {total}")
            logger.info(f"  Processed: {processed}")
            logger.info(f"  Skipped (already embedded): {skipped}")
            logger.info(f"  Failed: {failed}")

    finally:
        await engine.dispose()
        await vector_service.close()


def main():
    parser = argparse.ArgumentParser(description="Backfill embeddings for knowledge items")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete and recreate the Qdrant collection, then embed all items",
    )
    args = parser.parse_args()

    asyncio.run(backfill_embeddings(force=args.force))


if __name__ == "__main__":
    main()
