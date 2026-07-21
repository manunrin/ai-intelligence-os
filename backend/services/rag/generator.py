"""RAG generator — synthesizes answers from retrieved knowledge + LLM."""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from ..llm.base import ChatMessage, ChatRole, LLMProvider
from ..llm.router import LLMRouter

logger = logging.getLogger(__name__)


class RagGenerator:
    """Generates answers by combining retrieved context with LLM inference.

    Accepts either an LLMProvider or LLMRouter instance. Both expose .chat() and .stream().
    """

    def __init__(self, provider_or_router: LLMProvider | LLMRouter, model: str = "gpt-4o") -> None:
        self._provider_or_router = provider_or_router
        self._model = model

    async def generate(
        self,
        query: str,
        context: list[Any],
        *,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> dict[str, str]:
        """Generate an answer from retrieved context.

        Args:
            query: User's original question.
            context: List of RetrievalResult from RagRetriever.
            system_prompt: Optional custom system message.
            **kwargs: Passed to the provider (temperature, max_tokens, etc.).

        Returns:
            Dict with keys: answer, sources, query
        """
        if system_prompt is None:
            system_prompt = (
                "You are a helpful analyst. Answer the user's question based only "
                "on the provided context. If the context does not contain enough "
                "information, say so clearly."
            )

        messages = [
            ChatMessage(role=ChatRole.SYSTEM, content=system_prompt),
            ChatMessage(role=ChatRole.USER, content=self._build_user_message(query, context)),
        ]

        response = await self._provider_or_router.chat(messages, model=self._model, **kwargs)

        sources = [
            {"knowledge_id": ctx.knowledge_id, "title": ctx.title}
            for ctx in context
        ]

        return {
            "answer": response.content or "",
            "sources": sources,
            "query": query,
        }

    async def generate_stream(
        self,
        query: str,
        context: list[Any],
        *,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream an answer token by token from retrieved context.

        Yields dicts:
            {"type": "token", "content": str} — incremental text chunk
            {"type": "done", "sources": [...]} — final event with source citations
            {"type": "error", "message": str} — on provider/stream failure

        Args:
            query: User's original question.
            context: List of RetrievalResult from RagRetriever.
            system_prompt: Optional custom system message.
            **kwargs: Passed to the provider (temperature, max_tokens, etc.).
        """
        if system_prompt is None:
            system_prompt = (
                "You are a helpful analyst. Answer the user's question based only "
                "on the provided context. If the context does not contain enough "
                "information, say so clearly."
            )

        messages = [
            ChatMessage(role=ChatRole.SYSTEM, content=system_prompt),
            ChatMessage(role=ChatRole.USER, content=self._build_user_message(query, context)),
        ]

        sources = [
            {"knowledge_id": ctx.knowledge_id, "title": ctx.title}
            for ctx in context
        ]

        try:
            async for token in self._provider_or_router.stream(messages, model=self._model, **kwargs):
                yield {"type": "token", "content": token}
        except NotImplementedError:
            logger.info("Provider %s does not support streaming, falling back to full response", self._provider_or_router.name)
            try:
                response = await self._provider_or_router.chat(messages, model=self._model, **kwargs)
                full_text = response.content or ""
                if full_text:
                    yield {"type": "token", "content": full_text}
            except Exception as exc:
                logger.warning("RAG generation failed during stream fallback: %s", exc)
                yield {"type": "error", "message": f"Failed to generate answer: {str(exc)}"}
            finally:
                yield {"type": "done", "sources": sources}
            return

        except Exception as exc:
            logger.warning("RAG generation failed during streaming: %s", exc)
            yield {"type": "error", "message": f"Failed to generate answer: {str(exc)}"}

        yield {"type": "done", "sources": sources}

    @staticmethod
    def _build_user_message(query: str, context: list[Any]) -> str:
        """Format context chunks into a single user message."""
        parts: list[str] = []
        for i, chunk in enumerate(context, 1):
            title = getattr(chunk, "title", "Unknown")
            content = getattr(chunk, "content", "")
            kind = getattr(chunk, "kind", "unknown")
            parts.append(f"[{i}] ({kind}) {title}:\n{content}")

        context_text = "\n\n".join(parts)
        return (
            f"Context:\n{context_text}\n\nQuestion: {query}"
        )
