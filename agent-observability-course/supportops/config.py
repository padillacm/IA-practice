"""Configuración por variables de entorno (las API keys SOLO se leen de aquí, nunca de notebooks)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

DEFAULT_SEED = 42


def _f(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    provider: str = field(default_factory=lambda: os.environ.get("LLM_PROVIDER", "mock").lower())
    model: str | None = field(default_factory=lambda: os.environ.get("LLM_MODEL") or None)
    seed: int = field(default_factory=lambda: int(_f("SUPPORTOPS_SEED", DEFAULT_SEED)))
    sleep_scale: float = field(default_factory=lambda: _f("SUPPORTOPS_REAL_SLEEP_SCALE", 0.0))
    max_steps: int = field(default_factory=lambda: int(_f("SUPPORTOPS_MAX_STEPS", 6)))
    ollama_host: str = field(default_factory=lambda: os.environ.get("OLLAMA_HOST", "http://localhost:11434"))


def get_settings() -> Settings:
    """Lee el entorno en el momento de la llamada (así `os.environ[...] = ...` en un notebook surte efecto)."""
    return Settings()
