"""Proveedor Anthropic (SDK oficial ``anthropic``). Clave SOLO por variable de entorno ``ANTHROPIC_API_KEY``.

Modelo por defecto: ``LLM_MODEL`` o, si no está definido, el valor de ``DEFAULT_MODEL`` (verifica en la documentación
de Anthropic qué modelos están disponibles hoy). NO probado contra la API real en la construcción del curso
(sin credenciales); la conversión de mensajes está cubierta por pruebas con un cliente falso.
"""
from __future__ import annotations

import json
import time
from typing import Any

from ..models import LLMResponse, Message, ToolCall, Usage
from .base import LLMError

DEFAULT_MODEL = "claude-sonnet-5-5"


def to_anthropic_messages(messages: list[Message]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in messages:
        if m.role == "system":
            continue
        if m.role == "user":
            out.append({"role": "user", "content": m.content})
        elif m.role == "assistant":
            blocks: list[dict[str, Any]] = []
            if m.content:
                blocks.append({"type": "text", "text": m.content})
            for tc in m.tool_calls:
                blocks.append({"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments})
            out.append({"role": "assistant", "content": blocks})
        elif m.role == "tool":
            block = {"type": "tool_result", "tool_use_id": m.tool_call_id, "content": m.content}
            if out and out[-1]["role"] == "user" and isinstance(out[-1]["content"], list):
                out[-1]["content"].append(block)       # varios resultados seguidos van en un único mensaje user
            else:
                out.append({"role": "user", "content": [block]})
    return out


class AnthropicLLM:
    provider = "anthropic"

    def __init__(self, model: str | None = None, client: Any = None):
        self.model = model or DEFAULT_MODEL
        if client is None:
            try:
                import anthropic
            except ImportError as e:  # pragma: no cover
                raise ImportError("pip install anthropic  (y exporta ANTHROPIC_API_KEY)") from e
            client = anthropic.Anthropic()
        self.client = client

    def chat(self, messages, tools=None, *, system=None, max_tokens: int = 512, temperature: float = 0.0,
             call_key: tuple = ("", 0)) -> LLMResponse:
        kwargs: dict[str, Any] = dict(model=self.model, max_tokens=max_tokens, temperature=temperature,
                                      messages=to_anthropic_messages(messages))
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]}
                               for t in tools]
        t0 = time.perf_counter()
        try:
            resp = self.client.messages.create(**kwargs)
        except Exception as e:  # el SDK define APIStatusError con .status_code
            status = getattr(e, "status_code", 500) or 500
            raise LLMError(str(e), status=status, error_type=type(e).__name__, retryable=status in (408, 429, 500, 502, 503, 529)) from e
        latency = time.perf_counter() - t0
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        calls = [ToolCall(id=b.id, name=b.name, arguments=dict(b.input)) for b in resp.content if getattr(b, "type", "") == "tool_use"]
        finish = {"end_turn": "stop", "tool_use": "tool_calls", "max_tokens": "length"}.get(resp.stop_reason, resp.stop_reason or "stop")
        return LLMResponse(content=text, tool_calls=calls, usage=Usage(resp.usage.input_tokens, resp.usage.output_tokens),
                           finish_reason=finish, model=getattr(resp, "model", self.model), provider="anthropic",
                           latency_s=latency, response_id=getattr(resp, "id", ""))
