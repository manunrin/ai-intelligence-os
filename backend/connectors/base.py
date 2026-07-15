"""Abstract base for all source connectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class RawArticle:
    """Normalized article structure from any connector."""
    title: str
    url: str
    summary: str = ""
    content: str = ""
    language: str = "en"
    published_at: datetime | None = None
    author: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata_: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "summary": self.summary,
            "content": self.content,
            "language": self.language,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "author": self.author,
            "tags": self.tags,
            "metadata_": self.metadata_,
        }


class SourceConnector(ABC):
    """Base class for all data source connectors.

    Each connector implements:
    - fetch(): retrieve raw data from the source
    - parse(): convert raw data into structured items
    - normalize(): standardize items to RawArticle format

    Subclasses must override at least one of parse() or normalize().
    """

    name: str = "base_connector"
    kind: str = "unknown"

    async def run(self) -> list[RawArticle]:
        """Execute the full pipeline: fetch → parse → normalize."""
        raw = await self.fetch()
        parsed = await self.parse(raw)
        return [self.normalize(item) for item in parsed]

    @abstractmethod
    async def fetch(self) -> Any:
        """Retrieve raw data from the source.

        Returns:
            Raw data in source-specific format (bytes, dict, Response, etc.).
        """

    async def parse(self, raw_data: Any) -> list[Any]:
        """Parse raw data into intermediate structured items.

        Default implementation returns raw_data as-is; subclasses should
        override when a multi-step parse is needed.

        Args:
            raw_data: Output from fetch().

        Returns:
            List of intermediate items ready for normalization.
        """
        if isinstance(raw_data, list):
            return raw_data
        return [raw_data]

    @abstractmethod
    def normalize(self, item: Any) -> RawArticle:
        """Convert an intermediate item to a standardized RawArticle."""
