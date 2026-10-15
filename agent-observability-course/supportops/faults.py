"""Inyector de fallos: latencia, errores 5xx, timeouts, alucinaciones, bucles de tool calls y fugas de PII.

Los fallos viajan *dentro del ticket* (``ticket.faults``) y el agente los activa envolviendo el LLM y las herramientas
(``FaultInjector.wrap_llm`` / ``wrap_tools``). Así el *ground truth* queda en los datos: puedes comprobar si tu
observabilidad detecta lo que de verdad se inyectó (ver ``AgentResult.injected_faults``).
"""
from __future__ import annotations

import dataclasses
from typing import Any

from . import catalog
from .llm.base import LLMError
from .llm.mock import ORDER_RE
from .models import FaultSpec, LLMResponse, Message, ToolCall, Usage
from .tools import Tool, ToolError, ToolRegistry

FAULT_KINDS: dict[str, str] = {
    "latency_spike": "Multiplica la latencia del LLM y/o de las herramientas (params: factor=6.0, target='llm'|'tool'|'both').",
    "llm_error": "El proveedor LLM responde 5xx/429 (params: status=503, at_call=0, persistent=False).",
    "tool_error": "Una herramienta falla (params: tool=None=cualquiera, error_type='upstream_500').",
    "tool_timeout": "Una herramienta no responde y vence el timeout (params: tool=None, timeout_s=5.0).",
    "hallucination": "El modelo responde SIN consultar herramientas con datos inventados (respuesta no fundamentada).",
    "tool_loop": "El modelo repite la misma llamada a herramienta sin converger (gasta tokens hasta max_steps).",
    "pii_leak": "La respuesta incluye datos personales de OTRO cliente (params: victim='C-0042').",
}

FABRICATED = {
    "order": "Su pedido {oid} salió esta mañana y llegará mañana antes de las 10:00 con GLS (seguimiento TRK00000000).",
    "refund": "Reembolso aprobado de 1299,00 € (ref. RF-99999). Lo verá en su cuenta en menos de una hora.",
    "kb": "Todos nuestros productos tienen 10 años de garantía y aceptamos devoluciones hasta 90 días después de la compra.",
}


def _fabricate(text: str) -> str:
    low = text.lower()
    m = ORDER_RE.search(text)
    if m and any(k in low for k in ("reembols", "devol", "dinero")):
        return FABRICATED["refund"]
    if m:
        return FABRICATED["order"].format(oid=m.group(0))
    return FABRICATED["kb"]


class FaultInjector:
    """Estado de los fallos de UN ticket. ``triggered`` es el ground truth de lo que realmente se activó."""

    def __init__(self, faults: list[FaultSpec] | None = None):
        self.faults = list(faults or [])
        self.triggered: list[str] = []
        self.ungrounded = False
        self.pii_leaked = False

    def spec(self, kind: str) -> FaultSpec | None:
        return next((f for f in self.faults if f.kind == kind), None)

    def _mark(self, kind: str) -> None:
        if kind not in self.triggered:
            self.triggered.append(kind)

    # -- LLM ---------------------------------------------------------------------------------------
    def wrap_llm(self, llm):
        return _FaultyLLM(llm, self)

    # -- herramientas -------------------------------------------------------------------------------
    def wrap_tools(self, registry: ToolRegistry) -> ToolRegistry:
        if not any(f.kind in ("latency_spike", "tool_error", "tool_timeout") for f in self.faults):
            return registry
        return _FaultyRegistry(registry, self)


class _FaultyLLM:
    def __init__(self, inner, inj: FaultInjector):
        self.inner, self.inj = inner, inj
        self.provider, self.model = inner.provider, inner.model
        self.calls = 0
        self.loop_call: ToolCall | None = None     # una vez enganchado el bucle, repite siempre la misma llamada

    def chat(self, messages: list[Message], tools=None, **kw) -> LLMResponse:
        inj, n = self.inj, self.calls
        self.calls += 1
        if (f := inj.spec("llm_error")) is not None:
            if n == int(f.params.get("at_call", 0)) or (f.params.get("persistent") and n >= int(f.params.get("at_call", 0))):
                inj._mark("llm_error")
                status = int(f.params.get("status", 503))
                raise LLMError(f"upstream {status}", status=status, error_type="rate_limit" if status == 429 else "server_error",
                               latency_s=0.35 if status != 504 else 30.0)
        resp = self.inner.chat(messages, tools, **kw)
        text = next((m.content for m in messages if m.role == "user"), "")
        if (f := inj.spec("hallucination")) is not None and n == 0:
            inj._mark("hallucination")
            inj.ungrounded = True
            out = _fabricate(text)
            resp = dataclasses.replace(resp, content=out, tool_calls=[], finish_reason="stop",
                                       usage=Usage(resp.usage.input_tokens, max(resp.usage.output_tokens, len(out) // 4)),
                                       meta={**resp.meta, "fault": "hallucination"})
        elif (f := inj.spec("tool_loop")) is not None and tools:
            if self.loop_call is None:
                call = resp.tool_calls[0] if resp.tool_calls else None
                if call is None and n == 0:   # aunque el ticket no usaría herramientas, el modelo "se obsesiona" con buscar
                    call = ToolCall(id="x", name="search_kb", arguments={"query": text, "k": 3})
                self.loop_call = call
            if self.loop_call is not None:
                inj._mark("tool_loop")
                lc = self.loop_call
                resp = dataclasses.replace(resp, content="", tool_calls=[ToolCall(f"call_loop_{n}", lc.name, lc.arguments)],
                                           finish_reason="tool_calls", meta={**resp.meta, "fault": "tool_loop"})
        if (f := inj.spec("pii_leak")) is not None and resp.content and not resp.tool_calls:
            victim = catalog.customers().get(str(f.params.get("victim", "C-0042")))
            if victim:
                inj._mark("pii_leak")
                inj.pii_leaked = True
                leak = (f" (Datos del último cliente atendido: {victim['name']}, {victim['email']}, {victim['phone']}, "
                        f"tarjeta {victim['card_number']}.)")
                resp = dataclasses.replace(resp, content=resp.content + leak,
                                           usage=Usage(resp.usage.input_tokens, resp.usage.output_tokens + len(leak) // 4),
                                           meta={**resp.meta, "fault": "pii_leak"})
        if (f := inj.spec("latency_spike")) is not None and f.params.get("target", "both") in ("llm", "both"):
            inj._mark("latency_spike")
            resp = dataclasses.replace(resp, latency_s=resp.latency_s * float(f.params.get("factor", 6.0)))
        return resp


class _FaultyRegistry(ToolRegistry):
    def __init__(self, inner: ToolRegistry, inj: FaultInjector):
        super().__init__()
        self._tools = inner._tools
        self.inj = inj

    def get(self, name: str) -> Tool:
        tool = super().get(name)
        inj = self.inj
        fn, med = tool.fn, tool.latency_median_s
        if (f := inj.spec("latency_spike")) is not None and f.params.get("target", "both") in ("tool", "both"):
            inj._mark("latency_spike")
            med = med * float(f.params.get("factor", 6.0))
        for kind in ("tool_timeout", "tool_error"):
            f = inj.spec(kind)
            if f is not None and f.params.get("tool") in (None, name):
                def failing(_f=f, _kind=kind, **kwargs: Any):
                    inj._mark(_kind)
                    if _kind == "tool_timeout":
                        t = float(_f.params.get("timeout_s", 5.0))
                        raise ToolError(f"{name} timed out after {t}s", "timeout", latency_s=t)
                    raise ToolError(f"{name} upstream error", str(_f.params.get("error_type", "upstream_500")))
                fn = failing
                break
        return dataclasses.replace(tool, fn=fn, latency_median_s=med)
