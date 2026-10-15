"""Servidor local «compatible con OpenAI» sobre el LLM simulado (módulo 06 en adelante; autor A3).

Sirve para probar **auto-instrumentación** (OpenLIT, OpenLLMetry...) sin API keys ni red: esas librerías parchean el
*cliente* oficial (``openai``), así que necesitamos un cliente real hablando con *algo* por HTTP. Este servidor expone
``POST /v1/chat/completions`` (con y sin ``stream``) y ``GET /v1/models`` y responde con la política determinista de
``MockLLM``. Solo usa la librería estándar (el cliente ``openai`` se instala aparte: ``pip install openai``).

Uso::

    from supportops.openai_compat import FakeOpenAIServer, make_openai_llm
    with FakeOpenAIServer(error_rate=0.1) as srv:           # puerto libre en 127.0.0.1
        llm = make_openai_llm(srv)                          # OpenAILLM de supportops apuntando al servidor
        agent = SupportAgent(llm=llm)

Detalles:
- Determinista: la «clave de llamada» del mock sale del texto del usuario y del nº de turnos previos; los errores
  (``error_rate``) también (SHA-256 + semilla + nº de intento): misma secuencia de peticiones => mismos fallos, y un
  reintento tiene una «tirada» independiente.
- ``sleep_scale > 0`` duerme ``latencia_simulada * sleep_scale`` segundos reales por petición (para que un SDK que mide
  el reloj de pared vea duraciones distintas de cero).
- Los tokens de ``usage`` son los del mock (≈ caracteres/4), no los de un tokenizador real.
- NO es un servidor de producción: un hilo por petición, sin autenticación (acepta cualquier ``Authorization``).
"""
from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable

from .clock import stable_hex, stable_rng
from .config import get_settings
from .llm.mock import MockLLM
from .models import Message, ToolCall

__all__ = ["FakeOpenAIServer", "make_openai_llm", "request_to_messages"]


def request_to_messages(payload: dict[str, Any]) -> tuple[list[Message], str | None]:
    """Convierte ``messages`` de Chat Completions al modelo interno ``Message`` (y extrae el system prompt)."""
    system: str | None = None
    out: list[Message] = []
    names: dict[str, str] = {}
    for m in payload.get("messages", []):
        role, content = m.get("role"), m.get("content")
        if isinstance(content, list):           # content parts [{type:'text', text:...}]
            content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
        content = content or ""
        if role in ("system", "developer"):
            system = content
        elif role == "assistant":
            calls = []
            for tc in m.get("tool_calls") or []:
                fn = tc.get("function", {})
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                calls.append(ToolCall(tc.get("id", ""), fn.get("name", ""), args))
                names[tc.get("id", "")] = fn.get("name", "")
            out.append(Message("assistant", content, calls))
        elif role == "tool":
            out.append(Message("tool", content, tool_call_id=m.get("tool_call_id"), name=names.get(m.get("tool_call_id", ""))))
        else:
            out.append(Message("user", content))
    return out, system


class FakeOpenAIServer:
    """Servidor HTTP en un hilo. Úsalo como context manager o con ``start()``/``stop()``."""

    def __init__(self, llm: MockLLM | None = None, host: str = "127.0.0.1", port: int = 0, error_rate: float = 0.0,
                 error_status: int = 503, sleep_scale: float = 0.0, seed: int | None = None):
        self.llm = llm or MockLLM("mock-small")
        self.error_rate, self.error_status, self.sleep_scale = error_rate, error_status, sleep_scale
        self.seed = get_settings().seed if seed is None else seed
        self.requests: list[dict[str, Any]] = []          # bitácora (para comprobar qué vio el servidor)
        self._attempts: dict[tuple, int] = {}             # nº de veces que ha llegado la misma petición (reintentos)
        self._srv = ThreadingHTTPServer((host, port), self._handler())
        self._thread: threading.Thread | None = None

    # -- ciclo de vida --------------------------------------------------------------------------------
    @property
    def base_url(self) -> str:
        host, port = self._srv.server_address[:2]
        return f"http://{host}:{port}/v1"

    def start(self) -> "FakeOpenAIServer":
        self._thread = threading.Thread(target=self._srv.serve_forever, daemon=True, name="fake-openai")
        self._thread.start()
        return self

    def stop(self) -> None:
        self._srv.shutdown()
        self._srv.server_close()

    def __enter__(self) -> "FakeOpenAIServer":
        return self.start()

    def __exit__(self, *exc: Any) -> None:
        self.stop()

    # -- lógica ---------------------------------------------------------------------------------------
    def _complete(self, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        msgs, system = request_to_messages(payload)
        user_text = next((m.content for m in msgs if m.role == "user"), "")
        step = sum(m.role == "assistant" for m in msgs)
        key = (stable_hex(10, user_text), step)
        self.requests.append({"model": payload.get("model"), "stream": bool(payload.get("stream")), "n_messages": len(msgs), "step": step})
        attempt = self._attempts[key] = self._attempts.get(key, -1) + 1      # un reintento tiene otra «tirada» que el primer intento
        if self.error_rate and stable_rng("fake-openai-error", self.seed, *key, attempt).random() < self.error_rate:
            return self.error_status, {"error": {"message": f"upstream {self.error_status} (inyectado)", "type": "server_error", "code": None}}
        tools = [t.get("function", t) for t in payload.get("tools") or []]
        r = self.llm.chat(msgs, tools or None, system=system, max_tokens=int(payload.get("max_completion_tokens") or payload.get("max_tokens") or 512),
                          call_key=key)
        if self.sleep_scale:
            time.sleep(r.latency_s * self.sleep_scale)
        message: dict[str, Any] = {"role": "assistant", "content": r.content or None}
        if r.tool_calls:
            message["tool_calls"] = [{"id": c.id, "type": "function",
                                      "function": {"name": c.name, "arguments": json.dumps(c.arguments, ensure_ascii=False)}} for c in r.tool_calls]
        return 200, {"id": r.response_id.replace("resp_", "chatcmpl-"), "object": "chat.completion", "created": int(time.time()),
                     "model": payload.get("model") or r.model, "system_fingerprint": "fp_supportops_mock",
                     "choices": [{"index": 0, "message": message, "finish_reason": r.finish_reason}],
                     "usage": {"prompt_tokens": r.usage.input_tokens, "completion_tokens": r.usage.output_tokens,
                               "total_tokens": r.usage.total}}

    def _handler(self) -> type[BaseHTTPRequestHandler]:
        server = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a: Any) -> None:     # silencio
                pass

            def _send(self, status: int, body: dict[str, Any]) -> None:
                raw = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self) -> None:  # noqa: N802
                if self.path.rstrip("/").endswith("/models"):
                    self._send(200, {"object": "list", "data": [{"id": server.llm.model, "object": "model", "owned_by": "supportops"}]})
                else:
                    self._send(404, {"error": {"message": "not found"}})

            def do_POST(self) -> None:  # noqa: N802
                n = int(self.headers.get("Content-Length") or 0)
                payload = json.loads(self.rfile.read(n) or b"{}")
                if not self.path.rstrip("/").endswith("/chat/completions"):
                    return self._send(404, {"error": {"message": "solo /v1/chat/completions"}})
                status, body = server._complete(payload)
                if status != 200 or not payload.get("stream"):
                    return self._send(status, body)
                self._stream(payload, body)

            def _stream(self, payload: dict[str, Any], body: dict[str, Any]) -> None:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.end_headers()
                base = {k: body[k] for k in ("id", "created", "model", "system_fingerprint")}
                base["object"] = "chat.completion.chunk"
                msg, fr = body["choices"][0]["message"], body["choices"][0]["finish_reason"]

                def emit(obj: dict[str, Any]) -> None:
                    self.wfile.write(b"data: " + json.dumps(obj).encode() + b"\n\n")
                    self.wfile.flush()

                emit({**base, "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}]})
                if msg.get("tool_calls"):
                    for i, tc in enumerate(msg["tool_calls"]):
                        emit({**base, "choices": [{"index": 0, "delta": {"tool_calls": [{"index": i, "id": tc["id"], "type": "function",
                              "function": {"name": tc["function"]["name"], "arguments": tc["function"]["arguments"]}}]}, "finish_reason": None}]})
                else:
                    words = (msg.get("content") or "").split(" ")
                    for i, w in enumerate(words):
                        emit({**base, "choices": [{"index": 0, "delta": {"content": w + (" " if i < len(words) - 1 else "")}, "finish_reason": None}]})
                emit({**base, "choices": [{"index": 0, "delta": {}, "finish_reason": fr}]})
                if (payload.get("stream_options") or {}).get("include_usage"):
                    emit({**base, "choices": [], "usage": body["usage"]})
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
                self.close_connection = True

        return Handler


def make_openai_llm(server: FakeOpenAIServer, model: str | None = None, max_retries: int = 0,
                    on_create: Callable[[Any], None] | None = None):
    """``OpenAILLM`` de SupportOps con un cliente ``openai.OpenAI`` real apuntando al servidor falso.

    ``max_retries=0`` evita reintentos ocultos del SDK (el agente ya reintenta una vez; ver módulo 06).
    """
    import openai  # noqa: PLC0415 (import perezoso: dependencia opcional)

    from .llm.openai_provider import OpenAILLM

    client = openai.OpenAI(base_url=server.base_url, api_key="sk-fake-no-es-una-clave-real", max_retries=max_retries, timeout=10.0)
    if on_create:
        on_create(client)
    return OpenAILLM(model=model or server.llm.model, client=client)
