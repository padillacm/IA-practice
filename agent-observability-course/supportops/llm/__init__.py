"""Capa de proveedor LLM agnóstica: ``get_llm()`` lee ``LLM_PROVIDER`` (mock | anthropic | openai | ollama)."""
from __future__ import annotations

from ..config import get_settings
from .base import LLMClient, LLMError, count_tokens, messages_tokens
from .mock import MODEL_PROFILES, MockLLM, Rule, ToolStep, default_rules

PROVIDERS = ("mock", "anthropic", "openai", "ollama")


def get_llm(provider: str | None = None, model: str | None = None, **kwargs) -> LLMClient:
    """Fábrica. Sin argumentos usa las variables de entorno ``LLM_PROVIDER`` (def. ``mock``) y ``LLM_MODEL``."""
    s = get_settings()
    provider = (provider or s.provider).lower()
    model = model or s.model
    if provider == "mock":
        return MockLLM(model=model or "mock-small", **kwargs)
    if provider == "anthropic":
        from .anthropic_provider import AnthropicLLM
        return AnthropicLLM(model=model, **kwargs)
    if provider == "openai":
        from .openai_provider import OpenAILLM
        return OpenAILLM(model=model, **kwargs)
    if provider == "ollama":
        from .ollama_provider import OllamaLLM
        return OllamaLLM(model=model, **kwargs)
    raise ValueError(f"LLM_PROVIDER desconocido: {provider!r}; opciones: {PROVIDERS}")


__all__ = ["get_llm", "LLMClient", "LLMError", "MockLLM", "Rule", "ToolStep", "default_rules", "MODEL_PROFILES",
           "count_tokens", "messages_tokens", "PROVIDERS"]
