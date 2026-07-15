"""Async event publisher with subscriber registry."""

from __future__ import annotations

import logging
from typing import Any

from .event import BaseEvent

logger = logging.getLogger(__name__)


class EventPublisher:
    """Manages event subscribers and dispatches domain events.

    Subscribers register for specific event types. When an event is published,
    all matching subscribers receive it asynchronously (in-process, synchronous
    dispatch for now — easily extensible to async later).
    """

    def __init__(self) -> None:
        self._subscribers: dict[type[BaseEvent], list[Any]] = {}

    def subscribe(self, event_type: type[BaseEvent], callback) -> None:
        """Register a callback for a specific event type.

        Args:
            event_type: The BaseEvent subclass to listen for.
            callback: Async or sync function accepting the event instance.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        logger.debug("Subscriber registered for %s", event_type.__name__)

    async def publish(self, event: BaseEvent) -> None:
        """Dispatch an event to all matching subscribers.

        Args:
            event: The domain event instance.
        """
        handlers = self._subscribers.get(type(event), [])
        if not handlers:
            logger.debug("No subscribers for %s", type(event).__name__)
            return

        logger.info("Publishing %s (%s)", type(event).__name__, event.event_id)
        for handler in handlers:
            try:
                if callable(handler):
                    result = handler(event)
                    if hasattr(result, "__await__"):
                        await result
            except Exception as exc:
                logger.error(
                    "Event handler failed for %s: %s",
                    type(event).__name__,
                    exc,
                    exc_info=True,
                )
