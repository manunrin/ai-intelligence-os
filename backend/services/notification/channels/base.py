"""Base class and result type for notification channels."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar


@dataclass
class DeliveryResult:
    """Result of a single channel delivery attempt."""

    success: bool
    channel: str
    message: str = ""


class ChannelBase(ABC):
    """Abstract base for notification delivery channels."""

    name: ClassVar[str]

    @property
    @abstractmethod
    def is_enabled(self) -> bool:
        """Whether this channel has valid configuration."""

    @abstractmethod
    async def send(self, content: str) -> DeliveryResult:
        """Send content via this channel. Returns delivery result."""
