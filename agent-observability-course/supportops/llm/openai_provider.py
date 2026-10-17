"""Proveedor OpenAI (SDK ``openai``, Chat Completions con tools). Clave SOLO por ``OPENAI_API_KEY``.

Requiere ``LLM_MODEL`` (no fijamos un modelo por defecto: cambian con frecuencia). También sirve para servidores
compatibles con la API de OpenAI (``OPENAI_BASE_URL``). NO probado contra la API real (sin credenciales); la
conversión de mensajes está cubierta con un cliente falso.
"""
from __future__ import annotations

import json
import time
from typing import Any

from ..models import LLMResponse, Message, ToolCall, Usage
from .base import LLMError


def to_openai_messages(messages: list[Message], system: str | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if system:
        out.append({"role": "system", "content": system})
    for m in messages:
        if m.role == "assistant" and m.tool_calls:
            out.append({"role": "assistant", "content": m.content or None, "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.name, "arguments": json.dumps(tc.arguments, ensure_ascii=False)}}
                for tc in m.tool_calls]})
        elif m.role == "tool":
            out.append({"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content})
        elif m.role != "system":
            out.append({"role": m.role, "content": m.content})
    return out


class OpenAILLM:
    provider = "openai"

    def __init__(self, model: str | None = None, client: Any = None):
        if not model:
            raise ValueError("Define LLM_MODEL (p. ej. export LLM_MODEL=<modelo disponible en tu cuenta>)")
        self.model = model
        if client is None:
            try:
                import openai
            except ImportError as e:  # pragma: no cover
                raise ImportError("pip install openai  (y exporta OPENAI_API_KEY)") from e
            client = openai.OpenAI()
        self.client = client

    def chat(self, messages, tools=None, *, system=None, max_tokens: int = 512, temperature: float = 0.0,
             call_key: tuple = ("", 0)) -> LLMResponse:
        kwargs: dict[str, Any] = dict(model=self.model, messages=to_openai_messages(messages, system),
                                      temperature=temperature, max_completion_tokens=max_tokens)
        if tools:
            kwargs["tools"] = [{"type": "function", "function": t} for t in tools]
        t0 = time.perf_counter()
        try:
            resp = self.client.chat.completions.create(**kwargs)
        except Exception as e:
            status = getattr(e, "status_code", 500) or 500
            raise LLMError(str(e), status=status, error_type=type(e).__name__, retryable=status in (408, 429, 500, 502, 503)) from e
        latency = time.perf_counter() - t0
        ch = resp.choices[0]
        calls = [ToolCall(id=tc.id, name=tc.function.name, arguments=json.loads(tc.function.arguments or "{}"))
                 for tc in (ch.message.tool_calls or [])]
        finish = {"tool_calls": "tool_calls", "stop": "stop", "length": "length"}.get(ch.finish_reason, ch.finish_reason or "stop")
        return LLMResponse(content=ch.message.content or "", tool_calls=calls,
                           usage=Usage(resp.usage.prompt_tokens, resp.usage.completion_tokens), finish_reason=finish,
                           model=getattr(resp, "model", self.model), provider="openai", latency_s=latency,
                           response_id=getattr(resp, "id", ""))
