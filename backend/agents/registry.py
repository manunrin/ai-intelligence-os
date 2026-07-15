"""Unified agent registry — centralizes all agent definitions."""

from __future__ import annotations

from typing import Any

from .base import AgentBase


class AgentRegistry:
    """Central registry for all AI agents.

    Agents register themselves via the ``name`` class attribute.
    The registry provides lookup by name and full listing.
    """

    _agents: dict[str, type[AgentBase]] = {}

    @classmethod
    def register(cls, agent_cls: type[AgentBase]) -> None:
        """Register an agent class by its ``name``."""
        cls._agents[agent_cls.name] = agent_cls

    @classmethod
    def get(cls, name: str) -> type[AgentBase] | None:
        """Lookup an agent class by name."""
        return cls._agents.get(name)

    @classmethod
    def list_all(cls) -> dict[str, type[AgentBase]]:
        """Return all registered agent classes."""
        return dict(cls._agents)

    @classmethod
    def instantiate(cls, name: str, **kwargs: Any) -> AgentBase | None:
        """Instantiate a registered agent by name with the given kwargs."""
        agent_cls = cls._agents.get(name)
        if agent_cls is None:
            return None
        return agent_cls(**kwargs)


# ── Auto-register built-in agents ──────────────────────────────────

from ..agents.knowledge.agent import KnowledgeAgent       # noqa: E402
from ..agents.pronunciation.agent import PronunciationAgent  # noqa: E402
from ..agents.project_manager.agent import ProjectManagerAgent  # noqa: E402
from ..agents.notification.agent import NotificationAgent   # noqa: E402

for _agent_cls in (KnowledgeAgent, PronunciationAgent, ProjectManagerAgent, NotificationAgent):
    AgentRegistry.register(_agent_cls)

del _agent_cls
