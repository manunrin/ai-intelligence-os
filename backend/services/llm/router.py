"""LLM router — provider selection, model routing, and fallback."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, AsyncIterator

import yaml

from ...config import get_settings
from ...metrics import counter, histogram
from ...trace import set_attr, start_span
from .base import ChatMessage, ChatResponse, EmbeddingResponse, LLMProvider
from .providers.anthropic import AnthropicProvider
from .providers.compatible import CompatibleProvider
from .providers.litellm import LiteLLMProvider
from .providers.ollama import OllamaProvider
from .providers.openai import OpenAIProvider

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "models.yaml"


class LLMRouter:
    """Routes LLM requests to the appropriate provider and model.

    Responsibilities:
    - Load provider configurations from models.yaml
    - Select provider based on task type or explicit model name
    - Manage provider lifecycle (register, discover, health check)
    - Execute fallback chains when primary provider fails

    Configuration example (config/models.yaml):
        summary:
          primary: openai/gpt-4o
          fallback: [anthropic/claude-sonnet-4-20250514]
        translation:
          primary: compatible/qwen-translate
          fallback: []
        local:
          primary: ollama/mistral
          fallback: []
    """

    def __init__(self, config_path: Path | None = None) -> None:
        self._providers: dict[str, LLMProvider] = {}
        self._routing_rules: dict[str, list[tuple[str, str]]] = {}  # task → [(provider_name, model)]
        self._default_provider: str = "openai"
        self._default_model: str = "gpt-4o"
        self._config_path = config_path or _CONFIG_PATH
        self._load_config()
        self._register_providers()

    def _load_config(self) -> None:
        """Load routing rules from models.yaml."""
        if not self._config_path.exists():
            logger.warning("models.yaml not found at %s — using defaults", self._config_path)
            return

        try:
            with open(self._config_path) as f:
                config = yaml.safe_load(f) or {}
        except Exception as exc:
            logger.error("Failed to load models.yaml: %s", exc)
            return

        self._routing_rules = config.get("routing", {})
        self._default_provider = config.get("defaults", {}).get("provider", self._default_provider)
        self._default_model = config.get("defaults", {}).get("model", self._default_model)

    def _register_providers(self) -> None:
        """Register all known providers with their settings."""
        settings = get_settings()

        # OpenAI
        if api_key := settings.openai_api_key:
            self.register(OpenAIProvider(api_key=api_key))

        # Anthropic
        if api_key := settings.anthropic_api_key:
            self.register(AnthropicProvider(api_key=api_key))

        # Ollama
        if base_url := settings.ollama_base_url:
            self.register(OllamaProvider(base_url=base_url))

        # Compatible (Qwen, DeepSeek, etc.)
        if base_url := settings.compatible_api_base:
            self.register(CompatibleProvider(
                api_base=settings.compatible_api_base,
                api_key=settings.compatible_api_key,
            ))

        # LiteLLM Gateway
        if gateway_url := settings.litellm_gateway_url:
            self.register(LiteLLMProvider(
                api_base=gateway_url,
                api_key=settings.litellm_api_key or None,
            ))

    def register(self, provider: LLMProvider) -> None:
        """Register a provider instance."""
        self._providers[provider.name] = provider
        logger.info("Registered LLM provider: %s", provider.name)

    def get_provider(self, name: str) -> LLMProvider | None:
        """Lookup a provider by name."""
        return self._providers.get(name)

    def list_providers(self) -> list[str]:
        """Return names of all registered providers."""
        return list(self._providers.keys())

    def _resolve_route(self, task: str | None, model: str | None) -> tuple[str, str] | None:
        """Resolve which provider and model to use.

        Priority:
        1. Explicit model string (format: "provider/model")
        2. Explicit model string (just model name — uses default provider)
        3. Task-based routing rule
        4. Default provider + model
        """
        if model:
            if "/" in model:
                parts = model.split("/", 1)
                provider_name, model_name = parts[0], parts[1]
                if provider_name in self._providers:
                    return (provider_name, model_name)
                logger.warning("Unknown provider in model string: %s", provider_name)
            return (self._default_provider, model)

        if task and task in self._routing_rules:
            for provider_name, model_name in self._routing_rules[task]:
                if provider_name in self._providers:
                    return (provider_name, model_name)
            logger.warning("No registered provider matches task route: %s", task)

        return (self._default_provider, self._default_model)

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        task: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """Execute a chat request with automatic routing and fallback."""
        route = self._resolve_route(task, model)
        if route is None:
            raise ValueError(f"No route found for task={task}, model={model}")

        provider_name, model_name = route
        provider = self._providers.get(provider_name)
        if provider is None:
            raise ValueError(f"Provider '{provider_name}' not registered")

        return await self._execute_with_fallback(
            provider, model_name, messages,
            temperature=temperature, max_tokens=max_tokens, **kwargs,
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        task: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream a chat completion with automatic routing and fallback.

        Tries primary provider first. Falls back to full response only if no
        tokens were yielded yet. If streaming fails after partial output, the
        error propagates immediately to avoid duplicated responses.
        """
        route = self._resolve_route(task, model)
        if route is None:
            raise ValueError(f"No route found for task={task}, model={model}")

        provider_name, model_name = route
        provider = self._providers.get(provider_name)
        if provider is None:
            raise ValueError(f"Provider '{provider_name}' not registered")

        tokens_yielded = False
        try:
            async for token in provider.stream(messages, model=model_name, **kwargs):
                tokens_yielded = True
                yield token
            return
        except Exception as exc:
            if tokens_yielded:
                logger.warning("Streaming failed after partial output from '%s', propagating error", provider.name)
                raise
            logger.warning("Primary provider '%s' failed during streaming before yielding tokens: %s", provider.name, exc)

        # Fallback: try full chat response if no tokens were streamed
        logger.info("Falling back to full response from provider '%s'", provider.name)
        try:
            response = await self._execute_with_fallback(
                provider, model_name, messages,
                temperature=temperature, max_tokens=max_tokens, **kwargs,
            )
            if response.content:
                yield response.content
        except Exception as exc:
            logger.error("Fallback chat failed: %s", exc)
            raise

    async def embedding(self, text: str, *, model: str | None = None, **kwargs: Any) -> EmbeddingResponse:
        """Execute an embedding request with provider selection."""
        # For embeddings, use the "embedding" task route if no explicit model is given
        if model is None:
            provider_name, model_name = self._resolve_route("embedding", None) or (self._default_provider, self._default_model)
        else:
            provider_name, model_name = self._resolve_route(None, model) or (self._default_provider, self._default_model)

        provider = self._providers.get(provider_name)
        if provider is None:
            raise ValueError(f"Provider '{provider_name}' not registered")
        return await provider.embedding(text, model=model_name, **kwargs)

    async def _execute_with_fallback(
        self,
        primary_provider: LLMProvider,
        primary_model: str,
        messages: list[ChatMessage],
        **kwargs: Any,
    ) -> ChatResponse:
        """Try primary provider, then fall back through configured chain."""
        import time as _time
        task = kwargs.pop("_task", None)
        fallback_chain = []

        if task and task in self._routing_rules:
            for prov_name, model_name in self._routing_rules[task]:
                if prov_name != primary_provider.name:
                    fallback_chain.append((prov_name, model_name))

        start = _time.monotonic()
        final_provider = primary_provider.name
        final_model = primary_model
        result_status = "failed"
        response = None

        with start_span("llm.chat", attributes={
            "llm.system": primary_provider.name,
            "llm.request.model": primary_model,
        }) as span:
            # Try primary
            try:
                response = await primary_provider.chat(messages, model=primary_model, **kwargs)
                result_status = "success"
                final_provider = primary_provider.name
                final_model = primary_model
                set_attr(span, "llm.response.model", primary_model)
            except Exception as exc:
                logger.warning("Primary provider '%s' failed: %s", primary_provider.name, exc)
                set_attr(span, "error.type", type(exc).__name__)

            # Try fallbacks
            if response is None:
                for fallback_name, fallback_model in fallback_chain:
                    fallback_provider = self._providers.get(fallback_name)
                    if fallback_provider is None:
                        continue
                    try:
                        logger.info("Falling back to provider '%s'", fallback_name)
                        response = await fallback_provider.chat(messages, model=fallback_model, **kwargs)
                        result_status = "success"
                        final_provider = fallback_name
                        final_model = fallback_model
                        set_attr(span, "llm.fallback.used", True)
                        set_attr(span, "llm.fallback.provider", fallback_name)
                        break
                    except Exception as fb_exc:
                        logger.warning("Fallback provider '%s' also failed: %s", fallback_name, fb_exc)

            elapsed = _time.monotonic() - start
            counter("llm_requests_total", labels={"provider": final_provider, "model": final_model, "status": result_status})
            histogram("llm_request_duration_seconds", elapsed, labels={"provider": final_provider, "model": final_model, "status": result_status})

        if response is not None:
            return response

        raise RuntimeError(
            f"All providers failed. Primary: {primary_provider.name}/{primary_model}. "
            f"Fallbacks attempted: {len(fallback_chain)}."
        )

    async def check_health(self) -> dict[str, bool]:
        """Health check all registered providers."""
        results = {}
        for name, provider in self._providers.items():
            try:
                results[name] = await provider.health_check()
            except Exception:
                results[name] = False
        return results
