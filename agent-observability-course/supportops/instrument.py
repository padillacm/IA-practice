"""PUNTOS DE EXTENSIÓN para observabilidad. El agente v0 NO está instrumentado: llama a un ``Instrumentor`` que por
defecto no hace nada. El módulo 03 implementa uno con OpenTelemetry; ``recording.RecordingInstrumentor`` es otro, sin
dependencias, que guarda spans/logs en memoria (útil para enseñar el modelo de datos y para los datos pregrabados).

Contrato (los tres son *context managers*; el agente rellena los objetos ``info`` dentro del bloque ``with``):

    with instr.agent_run(ctx):                     # 1 por ticket  -> span raíz  (invoke_agent)
        with instr.llm_call(ctx, info):            # 1 por llamada al LLM       (chat)
            ...                                     #   el agente rellena info.response / info.error
        with instr.tool_call(ctx, info):           # 1 por herramienta          (execute_tool)
            ...                                     #   el agente rellena info.result / info.error

Si el bloque lanza una excepción, ésta atraviesa el ``yield`` del instrumentor (puedes registrarla) y se vuelve a
lanzar: el agente la captura fuera. Los tiempos simulados están en ``ctx.clock`` (``now_ns()``): úsalos como
``start_time``/``end_time`` de tus spans para obtener trazas deterministas, o ``SUPPORTOPS_REAL_SLEEP_SCALE`` para
que el reloj de pared avance de verdad.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator

from .clock import SimClock
from .models import AgentResult, LLMResponse, Message, Ticket, ToolCall

logger = logging.getLogger("supportops.agent")
logging.getLogger("supportops").addHandler(logging.NullHandler())   # silencio por defecto; tú decides dónde van los logs


@dataclass
class RunContext:
    """Contexto de una ejecución del agente (compartido por todos los hooks). ``state`` es libre para el instrumentor."""
    ticket: Ticket
    agent_name: str
    clock: SimClock
    model: str
    provider: str
    run_id: str
    state: dict[str, Any] = field(default_factory=dict)
    result: AgentResult | None = None       # se rellena al terminar (visible al salir del bloque agent_run)


@dataclass
class LLMCallInfo:
    step: int                               # índice del paso del agente (0, 1, 2...)
    attempt: int                            # 0 = primer intento, 1 = reintento...
    model: str
    provider: str
    n_messages: int
    max_tokens: int
    temperature: float
    messages: list[Message] | None = None   # el prompt completo (PRIVACIDAD: captúralo solo si lo decides, módulo 20)
    response: LLMResponse | None = None
    error: Exception | None = None


@dataclass
class ToolCallInfo:
    step: int
    call: ToolCall
    result: Any = None
    error: Exception | None = None


class Instrumentor:
    """Instrumentor nulo (no-op). Subclasifícalo y sobrescribe lo que necesites."""

    @contextmanager
    def agent_run(self, ctx: RunContext) -> Iterator[None]:
        yield

    @contextmanager
    def llm_call(self, ctx: RunContext, info: LLMCallInfo) -> Iterator[None]:
        yield

    @contextmanager
    def tool_call(self, ctx: RunContext, info: ToolCallInfo) -> Iterator[None]:
        yield

    def log(self, ctx: RunContext, level: int, message: str, fields: dict[str, Any]) -> None:
        """Se invoca por cada log del agente (además de ``logging.getLogger('supportops.agent')``)."""


class CompositeInstrumentor(Instrumentor):
    """Encadena varios instrumentores (p. ej. OTel + Recording). El primero es el más externo."""

    def __init__(self, *items: Instrumentor):
        self.items = list(items)

    @contextmanager
    def _stack(self, method: str, *args: Any) -> Iterator[None]:
        from contextlib import ExitStack
        with ExitStack() as st:
            for it in self.items:
                st.enter_context(getattr(it, method)(*args))
            yield

    def agent_run(self, ctx):  # type: ignore[override]
        return self._stack("agent_run", ctx)

    def llm_call(self, ctx, info):  # type: ignore[override]
        return self._stack("llm_call", ctx, info)

    def tool_call(self, ctx, info):  # type: ignore[override]
        return self._stack("tool_call", ctx, info)

    def log(self, ctx, level, message, fields):
        for it in self.items:
            it.log(ctx, level, message, fields)
