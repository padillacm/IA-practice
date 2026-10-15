"""RecordingInstrumentor: instrumentor SIN dependencias que guarda spans y logs en memoria con el mismo modelo de datos
que OpenTelemetry (trace_id, span_id, parent, atributos, eventos, status, resource). Sirve para:
  * enseñar el modelo de datos antes de usar el SDK (módulos 02-03),
  * generar los datos pregrabados del modo degradado (``supportops.sample_data``),
  * tests y rúbricas deterministas (los tiempos son los del reloj simulado).

Atributos ``gen_ai.*``: las GenAI semantic conventions están en estado *Development* (inestables) y se han movido al
repositorio open-telemetry/semantic-conventions-genai. Aquí solo se usan nombres verificados contra su registro de
atributos; el módulo 04 los estudia a fondo.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterator

from .clock import stable_hex
from .config import get_settings
from .instrument import Instrumentor, LLMCallInfo, RunContext, ToolCallInfo

RESOURCE = {"service.name": "supportops-agent", "service.version": "0.1.0", "deployment.environment.name": "lab"}
SEVERITY = {logging.DEBUG: ("DEBUG", 5), logging.INFO: ("INFO", 9), logging.WARNING: ("WARN", 13),
            logging.ERROR: ("ERROR", 17), logging.CRITICAL: ("FATAL", 21)}


class RecordingInstrumentor(Instrumentor):
    def __init__(self, resource: dict[str, Any] | None = None):
        self.resource = dict(resource or RESOURCE)
        self.spans: list[dict[str, Any]] = []
        self.logs: list[dict[str, Any]] = []
        self._stack: list[dict[str, Any]] = []
        self._n = 0

    def reset(self) -> None:
        self.spans, self.logs, self._stack, self._n = [], [], [], 0

    # -- utilidades ---------------------------------------------------------------------------------
    def _open(self, ctx: RunContext, name: str, kind: str, attrs: dict[str, Any]) -> dict[str, Any]:
        self._n += 1
        parent = self._stack[-1] if self._stack else None
        trace_id = parent["trace_id"] if parent else stable_hex(32, get_settings().seed, ctx.ticket.ticket_id)
        span = {"trace_id": trace_id, "span_id": stable_hex(16, trace_id, self._n),
                "parent_span_id": parent["span_id"] if parent else None, "name": name, "kind": kind,
                "start_unix_nano": ctx.clock.now_ns(), "end_unix_nano": None, "status": "UNSET", "status_message": None,
                "attributes": attrs, "events": [], "resource": self.resource, "scope": "supportops.recording"}
        self.spans.append(span)
        self._stack.append(span)
        return span

    def _close(self, ctx: RunContext, span: dict[str, Any], error: BaseException | None = None) -> None:
        span["end_unix_nano"] = ctx.clock.now_ns()
        if error is not None:
            span["status"], span["status_message"] = "ERROR", str(error)[:200]
            span["attributes"]["error.type"] = getattr(error, "error_type", type(error).__name__)
            span["events"].append({"name": "exception", "time_unix_nano": span["end_unix_nano"],
                                   "attributes": {"exception.type": type(error).__name__, "exception.message": str(error)[:200]}})
        self._stack.pop()

    # -- hooks --------------------------------------------------------------------------------------
    @contextmanager
    def agent_run(self, ctx: RunContext) -> Iterator[None]:
        t = ctx.ticket
        span = self._open(ctx, f"invoke_agent {ctx.agent_name}", "INTERNAL", {
            "gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": ctx.agent_name,
            "gen_ai.conversation.id": t.ticket_id, "gen_ai.provider.name": ctx.provider,
            "supportops.ticket.id": t.ticket_id, "supportops.customer.id": t.customer_id,
            "supportops.customer.tier": t.tier, "supportops.channel": t.channel})
        try:
            yield
        except BaseException as e:
            self._close(ctx, span, e)
            raise
        r = ctx.result
        if r is not None:
            a = span["attributes"]
            a.update({"gen_ai.usage.input_tokens": r.input_tokens, "gen_ai.usage.output_tokens": r.output_tokens,
                      "supportops.status": r.status, "supportops.cost_usd": r.cost_usd,
                      "supportops.llm_calls": r.n_llm_calls, "supportops.tool_calls": r.n_tool_calls})
            if r.intent_pred:
                a["supportops.intent"] = r.intent_pred
            if r.status in ("error", "max_steps"):
                span["status"] = "ERROR"
                span["status_message"] = r.status
                a["error.type"] = r.error_type or r.status
        self._close(ctx, span)

    @contextmanager
    def llm_call(self, ctx: RunContext, info: LLMCallInfo) -> Iterator[None]:
        span = self._open(ctx, f"chat {info.model}", "CLIENT", {
            "gen_ai.operation.name": "chat", "gen_ai.provider.name": info.provider, "gen_ai.request.model": info.model,
            "gen_ai.request.max_tokens": info.max_tokens, "gen_ai.request.temperature": info.temperature,
            "supportops.step": info.step, "supportops.attempt": info.attempt})
        try:
            yield
        except BaseException as e:
            self._close(ctx, span, e)
            if info.attempt >= 0 and getattr(e, "status", None):
                span["attributes"]["http.response.status_code"] = e.status
            raise
        r = info.response
        if r is not None:
            span["attributes"].update({
                "gen_ai.response.model": r.model, "gen_ai.response.id": r.response_id,
                "gen_ai.response.finish_reasons": [r.finish_reason],
                "gen_ai.usage.input_tokens": r.usage.input_tokens, "gen_ai.usage.output_tokens": r.usage.output_tokens})
        self._close(ctx, span)

    @contextmanager
    def tool_call(self, ctx: RunContext, info: ToolCallInfo) -> Iterator[None]:
        span = self._open(ctx, f"execute_tool {info.call.name}", "INTERNAL", {
            "gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": info.call.name,
            "gen_ai.tool.call.id": info.call.id, "gen_ai.tool.type": "function", "supportops.step": info.step})
        try:
            yield
        except BaseException as e:
            self._close(ctx, span, e)
            raise
        self._close(ctx, span)

    def log(self, ctx: RunContext, level: int, message: str, fields: dict[str, Any]) -> None:
        sev, num = SEVERITY.get(level, ("INFO", 9))
        cur = self._stack[-1] if self._stack else None
        self.logs.append({"time_unix_nano": ctx.clock.now_ns(), "severity_text": sev, "severity_number": num, "body": message,
                          "attributes": dict(fields), "trace_id": cur["trace_id"] if cur else None,
                          "span_id": cur["span_id"] if cur else None, "resource": self.resource})
