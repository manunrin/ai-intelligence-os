"""OpenAI Blog RSS connector."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

try:
    import feedparser
except ImportError:
    feedparser = None  # type: ignore[assignment]

from ..base import RawArticle, SourceConnector

logger = logging.getLogger(__name__)


class OpenAIBlogRssConnector(SourceConnector):
    """Fetches and normalizes articles from the OpenAI blog RSS feed."""

    name = "openai_blog_rss"
    kind = "rss"

    def __init__(self, url: str = "https://openai.com/blog/rss.xml") -> None:
        self._url = url

    async def fetch(self) -> Any:
        """Fetch the RSS feed XML."""
        if feedparser is None:
            raise ImportError("feedparser is required for RSS connectors. Install with: pip install feedparser")
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(self._url)
            response.raise_for_status()
            return response.text

    def parse(self, raw_data: str) -> list[dict[str, Any]]:
        """Parse RSS XML into individual entry dicts."""
        feed = feedparser.parse(raw_data)
        if feed.bozo and not feed.entries:
            logger.warning("RSS feed parsing warning: %s", feed.bozo_exception)
        return feed.entries

    def normalize(self, entry: dict[str, Any]) -> RawArticle:
        """Convert an RSS entry to a standardized RawArticle."""
        published_str = entry.get("published") or entry.get("updated") or ""
        published_at = None
        if published_str:
            try:
                published_at = datetime.strptime(published_str[:19], "%Y-%m-%dT%H:%M:%S")
                published_at = published_at.replace(tzinfo=timezone.utc)
            except ValueError:
                pass

        summary = entry.get("summary", "") or entry.get("description", "")
        # Strip HTML tags for plain-text summary
        import re
        summary = re.sub(r"<[^>]+>", "", summary).strip()

        return RawArticle(
            title=entry.get("title", ""),
            url=entry["link"],
            summary=summary,
            language="en",
            published_at=published_at,
            author=entry.get("author"),
            tags=[tag.term for tag in entry.get("tags", [])],
            metadata_={"source_type": "rss", "feed_url": self._url},
        )
