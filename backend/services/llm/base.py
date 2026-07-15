"""Abstract interface for all LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ChatRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ChatMessage:
    """Single message in a chat turn."""
    role: ChatRole
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


@dataclass
class ChatResponse:
    """Response from a chat completion."""
    content: str | None = None
    finish_reason: str | None = None
    usage: dict[str, int] = field(default_factory=dict)
    raw: dict[str, Any] | None = None


@dataclass
class EmbeddingResponse:
    """Response from an embedding call."""
    embeddings: list[list[float]] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)
    raw: dict[str, Any] | None = None


class LLMProvider(ABC):
    """Interface that all LLM providers must implement.

    Each provider wraps a specific LLM service (OpenAI, Anthropic, Ollama, etc.)
    and exposes a unified interface for chat completions and embeddings.
    """

    # Override in subclasses
    name: str = "base_provider"
    version: str = "0.1.0"

    @abstractmethod
    async def chat(self, messages: list[ChatMessage], model: str, **kwargs: Any) -> ChatResponse:
        """Send a chat completion request.

        Args:
            messages: Ordered list of chat messages.
            model: Model identifier to use.
            **kwargs: Provider-specific parameters (temperature, max_tokens, etc.).

        Returns:
            ChatResponse with assistant's reply.
        """

    @abstractmethod
    async def embedding(self, text: str, model: str, **kwargs: Any) -> EmbeddingResponse:
        """Generate an embedding vector for the given text.

        Args:
            text: Input text to embed.
            model: Embedding model identifier.
            **kwargs: Provider-specific parameters.

        Returns:
            EmbeddingResponse with vector array.
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is reachable and healthy.

        Returns:
            True if the provider is operational, False otherwise.
        """

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
