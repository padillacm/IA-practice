"""Interfaz común de los proveedores LLM y utilidades de tokens."""
from __future__ import annotations

import json
import math
from typing import Any, Protocol

from ..models import LLMResponse, Message


class LLMError(Exception):
    """Fallo del proveedor (5xx, 429, timeout...). ``status`` imita el código HTTP; ``error_type`` es corto y de baja cardinalidad."""

    def __init__(self, message: str, status: int = 500, error_type: str = "llm_error", retryable: bool = True,
                 latency_s: float = 0.4):
        super().__init__(message)
        self.latency_s = latency_s          # tiempo (simulado) consumido antes del fallo
        self.status = status
        self.error_type = error_type
        self.retryable = retryable


class LLMClient(Protocol):
    provider: str
    model: str

    def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        *,
        system: str | None = None,
        max_tokens: int = 512,
        temperature: float = 0.0,
        call_key: tuple = ("", 0),
    ) -> LLMResponse:
        """Una llamada al modelo. ``call_key`` (ticket_id, paso) hace deterministas las latencias/tokens del mock."""
        ...


def count_tokens(text: str) -> int:
    """Aproximación documentada: ~4 caracteres por token (válida para el mock; los proveedores reales devuelven su conteo)."""
    return max(1, math.ceil(len(text) / 4))


def messages_tokens(messages: list[Message], system: str | None, tools: list[dict[str, Any]] | None) -> int:
    n = count_tokens(system or "") if system else 0
    if tools:
        n += count_tokens(json.dumps(tools, ensure_ascii=False))
    for m in messages:
        n += 4 + count_tokens(m.content or "")
        for tc in m.tool_calls:
            n += count_tokens(tc.name + json.dumps(tc.arguments, ensure_ascii=False))
    return n
