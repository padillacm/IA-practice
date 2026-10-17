"""Proveedor Ollama (local, API HTTP ``/api/chat``). Sin dependencias: usa ``urllib``. Requiere ``LLM_MODEL`` (un modelo
con soporte de herramientas descargado con ``ollama pull``). Host por ``OLLAMA_HOST`` (por defecto http://localhost:11434).
NO probado contra un servidor real durante la construcción del curso; la conversión se prueba con un transporte falso.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Callable

from ..config import get_settings
from ..models import LLMResponse, Message, ToolCall, Usage
from .base import LLMError


def to_ollama_messages(messages: list[Message], system: str | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if system:
        out.append({"role": "system", "content": system})
    for m in messages:
        if m.role == "assistant" and m.tool_calls:
            out.append({"role": "assistant", "content": m.content, "tool_calls": [
                {"function": {"name": tc.name, "arguments": tc.arguments}} for tc in m.tool_calls]})
        elif m.role == "tool":
            out.append({"role": "tool", "content": m.content, "tool_name": m.name})
        elif m.role != "system":
            out.append({"role": m.role, "content": m.content})
    return out


class OllamaLLM:
    provider = "ollama"

    def __init__(self, model: str | None = None, host: str | None = None,
                 transport: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None):
        if not model:
            raise ValueError("Define LLM_MODEL (p. ej. export LLM_MODEL=<modelo descargado con ollama pull>)")
        self.model = model
        self.host = (host or get_settings().ollama_host).rstrip("/")
        self._transport = transport or self._http

    def _http(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            raise LLMError(str(e), status=e.code, error_type="HTTPError") from e
        except Exception as e:
            raise LLMError(str(e), status=503, error_type=type(e).__name__) from e

    def chat(self, messages, tools=None, *, system=None, max_tokens: int = 512, temperature: float = 0.0,
             call_key: tuple = ("", 0)) -> LLMResponse:
        payload: dict[str, Any] = {"model": self.model, "messages": to_ollama_messages(messages, system), "stream": False,
                                   "options": {"temperature": temperature, "num_predict": max_tokens}}
        if tools:
            payload["tools"] = [{"type": "function", "function": t} for t in tools]
        t0 = time.perf_counter()
        data = self._transport(f"{self.host}/api/chat", payload)
        latency = time.perf_counter() - t0
        msg = data.get("message", {})
        calls = [ToolCall(id=f"call_{i}", name=tc["function"]["name"], arguments=dict(tc["function"].get("arguments", {})))
                 for i, tc in enumerate(msg.get("tool_calls", []) or [])]
        finish = "tool_calls" if calls else ("length" if data.get("done_reason") == "length" else "stop")
        return LLMResponse(content=msg.get("content", ""), tool_calls=calls,
                           usage=Usage(data.get("prompt_eval_count", 0), data.get("eval_count", 0)), finish_reason=finish,
                           model=self.model, provider="ollama", latency_s=latency)
