"""SupportOps multi-agente (módulo 11): orquestador + subagentes, handoffs, propagación de contexto W3C y fallos en cascada.

Se construye ENCIMA de ``supportops.telemetry`` (``setup_telemetry`` + ``OTelInstrumentor``, autor A2): cada agente es un
*servicio* distinto (``service.name = supportops-<agente>``) con su propio ``TelemetryHandle``. Todo corre en un proceso
(tiempo simulado, determinista), salvo ``RemoteAgentProcess``, que ejecuta un subagente en un PROCESO REAL aparte.

    from supportops.multiagent import build_mesh, MultiAgentSupportOps, DelegationPolicy
    mesh = build_mesh()                                     # un handle de telemetría por agente
    system = MultiAgentSupportOps(mesh, mode="delegate")     # o mode="handoff"
    res = system.run(ticket)                                 # MultiResult; res.trace_id -> la traza de extremo a extremo
    rows = mesh.span_records(res.trace_id)                   # spans de TODOS los servicios, esquema SPAN_SCHEMA

Contenido
---------
* Propagación: ``format_traceparent`` / ``parse_traceparent`` / ``inject_manual`` / ``extract_manual`` (W3C Trace Context
  a mano, sin SDK) y ``inject_sdk`` / ``extract_sdk`` (propagador del SDK). ``propagation="none"`` rompe la cadena a propósito.
* Topologías: ``mode="delegate"`` (el orquestador conserva el control, sintetiza la respuesta) y ``mode="handoff"`` (transfiere
  la conversación al especialista; no hay síntesis). Raíz común ``invoke_workflow support_ticket`` (GenAI semconv, Development).
* Resiliencia: ``DelegationPolicy`` (timeout, reintentos con backoff, disyuntor, propagación de *deadline*, fallback humano).
* Análisis: ``span_frame``, ``agent_tree_text``, ``critical_path``, ``cost_rollup``, ``waterfall_services``.

Convenciones: agentes ``orders-agent|billing-agent|knowledge-agent|escalation-agent`` y ``supportops-orchestrator``;
``service.name = supportops-<agente>``; ``service.version = 0.1.0-m11``. Un fallo de ``ticket.faults`` con ``params["agent"]``
solo afecta a ese agente; sin ``agent`` afecta al especialista principal; ``params["sticky"]=True`` lo mantiene en los
reintentos (si no, solo se activa en el primer intento: fallo transitorio).
"""
from __future__ import annotations

import dataclasses
import json
import logging
import multiprocessing as mp
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, Sequence

from opentelemetry import context as otel_context
from opentelemetry import trace as otel_trace
from opentelemetry.context import Context
from opentelemetry.trace import Link, NonRecordingSpan, SpanContext, SpanKind, Status, StatusCode, TraceFlags, TraceState
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from .agent import SupportAgent
from .clock import SimClock, stable_hex, stable_rng
from .config import get_settings
from .faults import FaultInjector
from .instrument import CompositeInstrumentor, Instrumentor, LLMCallInfo, RunContext, ToolCallInfo
from .llm import LLMError, MockLLM
from .llm.base import count_tokens, messages_tokens
from .llm.mock import (MODEL_PROFILES, NATURAL_TAIL_FACTOR, NATURAL_TAIL_PROB, ORDER_RE, default_rules, detect_rule)
from .models import AgentResult, FaultSpec, LLMResponse, Message, Ticket, ToolCall, Usage
from .pricing import cost_usd
from .telemetry import OTelInstrumentor, TelemetryHandle, setup_telemetry
from .tools import ToolError, ToolRegistry, default_tools

SERVICE_VERSION = "0.1.0-m11"
ORCH = "supportops-orchestrator"
SPECIALISTS = ("orders-agent", "billing-agent", "knowledge-agent", "escalation-agent")
INTENT_PRIMARY = {"order_status": "orders-agent", "refund": "billing-agent", "kb_question": "knowledge-agent",
                  "escalation": "escalation-agent"}
FAIL_STATUS = ("error", "max_steps")
_log = logging.getLogger("supportops.multiagent")


def service_name(agent: str) -> str:
    """``orders-agent`` -> ``supportops-orders-agent``; el orquestador ya se llama ``supportops-orchestrator``."""
    return agent if agent == ORCH else f"supportops-{agent}"


# ---------------------------------------------------------------------------------------------------------------------
# W3C Trace Context a mano  (https://www.w3.org/TR/trace-context/)
# ---------------------------------------------------------------------------------------------------------------------
_TP_RE = re.compile(r"^(?P<ver>[0-9a-f]{2})-(?P<tid>[0-9a-f]{32})-(?P<sid>[0-9a-f]{16})-(?P<flags>[0-9a-f]{2})(?P<rest>-.*)?$")


@dataclass(frozen=True)
class TraceParent:
    version: str
    trace_id: str
    parent_id: str
    flags: str

    @property
    def sampled(self) -> bool:
        return bool(int(self.flags, 16) & 0x01)


def format_traceparent(trace_id: int | str, span_id: int | str, sampled: bool = True, version: str = "00") -> str:
    """``version-trace_id-parent_id-trace_flags`` en minúsculas hexadecimales (55 caracteres en la versión 00)."""
    t = trace_id if isinstance(trace_id, str) else format(trace_id, "032x")
    s = span_id if isinstance(span_id, str) else format(span_id, "016x")
    return f"{version}-{t}-{s}-{'01' if sampled else '00'}"


def parse_traceparent(header: str | None) -> TraceParent | None:
    """Valida una cabecera ``traceparent`` según la spec: devuelve ``None`` si es inválida (nunca lanza).

    Reglas: hex en minúsculas; versión ``ff`` prohibida; ``trace-id`` y ``parent-id`` no pueden ser todo ceros; en la versión
    ``00`` no puede haber campos extra (versiones futuras: se parsean los 4 primeros campos y se ignora el resto).
    """
    if not isinstance(header, str):
        return None
    m = _TP_RE.match(header.strip())
    if not m:
        return None
    ver, tid, sid, flags, rest = m["ver"], m["tid"], m["sid"], m["flags"], m["rest"]
    if ver == "ff" or set(tid) == {"0"} or set(sid) == {"0"}:
        return None
    if ver == "00" and rest:
        return None
    return TraceParent(ver, tid, sid, flags)


def _carrier_get(carrier: dict[str, str], key: str) -> str | None:
    for k, v in (carrier or {}).items():          # las cabeceras son insensibles a mayúsculas
        if k.lower() == key:
            return v
    return None


def inject_manual(carrier: dict[str, str] | None = None, span: Any = None) -> dict[str, str]:
    """Escribe ``traceparent`` (y ``tracestate`` si existe) del span activo en ``carrier`` (un dict de cabeceras/mensaje)."""
    carrier = {} if carrier is None else carrier
    sc = (span or otel_trace.get_current_span()).get_span_context()
    if sc.is_valid:
        carrier["traceparent"] = format_traceparent(sc.trace_id, sc.span_id, bool(sc.trace_flags & TraceFlags.SAMPLED))
        if sc.trace_state:
            carrier["tracestate"] = sc.trace_state.to_header()
    return carrier


def extract_manual(carrier: dict[str, str] | None) -> Context | None:
    """Lee ``traceparent`` y devuelve un ``Context`` con ese padre REMOTO, o ``None`` si falta/es inválido."""
    tp = parse_traceparent(_carrier_get(carrier or {}, "traceparent"))
    if tp is None:
        return None
    ts_header = _carrier_get(carrier or {}, "tracestate")
    state = TraceState.from_header([ts_header]) if ts_header else TraceState()
    sc = SpanContext(int(tp.trace_id, 16), int(tp.parent_id, 16), is_remote=True,
                     trace_flags=TraceFlags(int(tp.flags, 16) & 0xFF), trace_state=state)
    return otel_trace.set_span_in_context(NonRecordingSpan(sc), Context())


_PROP = TraceContextTextMapPropagator()


def inject_sdk(carrier: dict[str, str] | None = None) -> dict[str, str]:
    carrier = {} if carrier is None else carrier
    _PROP.inject(carrier)
    return carrier


def extract_sdk(carrier: dict[str, str] | None) -> Context | None:
    ctx = _PROP.extract(carrier or {}, context=Context())
    return ctx if otel_trace.get_current_span(ctx).get_span_context().is_valid else None


@contextmanager
def attached(ctx: Context | None) -> Iterator[None]:
    """Hace ``ctx`` el contexto actual (``None`` = contexto VACÍO: simula un proceso nuevo sin padre)."""
    token = otel_context.attach(ctx if ctx is not None else Context())
    try:
        yield
    finally:
        otel_context.detach(token)


# ---------------------------------------------------------------------------------------------------------------------
# Malla de servicios (un TelemetryHandle por agente)
# ---------------------------------------------------------------------------------------------------------------------
def span_rows(handle: TelemetryHandle) -> list[dict[str, Any]]:
    """``handle.span_records()`` + ``links`` (la lista del esquema base no los trae)."""
    recs = handle.span_records()
    for r, s in zip(recs, handle.finished_spans()):
        r["links"] = [{"trace_id": format(lk.context.trace_id, "032x"), "span_id": format(lk.context.span_id, "016x"),
                       "attributes": dict(lk.attributes or {})} for lk in s.links]
    return recs


@dataclass
class Mesh:
    """Conjunto de servicios (agentes) de una prueba. ``span_records()`` los une, como haría Tempo con un ``trace_id``."""
    handles: dict[str, TelemetryHandle]
    instruments: dict[str, OTelInstrumentor] = field(default_factory=dict)
    _invoke_hist: dict[str, Any] = field(default_factory=dict)

    @property
    def mode(self) -> str:
        return next(iter(self.handles.values())).mode

    def handle(self, agent: str) -> TelemetryHandle:
        return self.handles[agent]

    def instr(self, agent: str, **kw: Any) -> OTelInstrumentor:
        if agent not in self.instruments or kw:
            self.instruments[agent] = OTelInstrumentor(self.handles[agent], **kw)
        return self.instruments[agent]

    def record_invocation(self, agent: str, seconds: float, error_type: str | None = None) -> None:
        """Histograma ``gen_ai.invoke_agent.duration`` (spec GenAI, Development) en el servicio del agente."""
        h = self.handles[agent]
        if h.meter_provider is None:
            return
        if agent not in self._invoke_hist:
            self._invoke_hist[agent] = h.meter().create_histogram(
                "gen_ai.invoke_agent.duration", unit="s", description="Duración de una invocación de agente",
                explicit_bucket_boundaries_advisory=[0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4, 12.8, 25.6, 51.2, 102.4])
        attrs = {"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": agent}
        if error_type:
            attrs["error.type"] = error_type
        self._invoke_hist[agent].record(max(seconds, 0.0), attrs)

    def span_records(self, trace_id: str | None = None) -> list[dict[str, Any]]:
        rows = [r for h in self.handles.values() for r in span_rows(h)]
        if trace_id:
            rows = [r for r in rows if r["trace_id"] == trace_id]
        return sorted(rows, key=lambda r: (r["start_unix_nano"], -(r["end_unix_nano"] or 0)))

    def log_records(self, trace_id: str | None = None) -> list[dict[str, Any]]:
        rows = [r for h in self.handles.values() for r in h.log_records()]
        return [r for r in rows if not trace_id or r["trace_id"] == trace_id]

    def metric_points(self) -> list[dict[str, Any]]:
        out = []
        for name, h in self.handles.items():
            for p in h.metric_points():
                out.append({**p, "service": h.service_name})
        return out

    def reset_local(self) -> None:
        for h in self.handles.values():
            h.reset_local()

    def force_flush(self) -> bool:
        return all([h.force_flush() for h in self.handles.values()])

    def shutdown(self) -> None:
        for h in self.handles.values():
            h.shutdown()


def build_mesh(agents: Sequence[str] = (ORCH, *SPECIALISTS), *, mode: str = "auto", endpoint: str | None = None,
               deterministic_ids: bool = False, metric_interval_s: float = 5.0) -> Mesh:
    """Crea un ``TelemetryHandle`` por agente (``set_global=False``: varios servicios en un mismo proceso de laboratorio).

    En producción cada agente sería un proceso/contenedor con su propio ``setup_telemetry``; aquí se simulan en un proceso.
    """
    handles = {a: setup_telemetry(service_name(a), mode=mode, endpoint=endpoint, set_global=False,
                                  deterministic_ids=deterministic_ids, metric_interval_s=metric_interval_s,
                                  service_version=SERVICE_VERSION, resource_attrs={"process.pid": os.getpid()})
               for a in agents}
    return Mesh(handles)


# ---------------------------------------------------------------------------------------------------------------------
# LLM «guionizado» (enrutador y sintetizador del orquestador): mismas latencias/tokens que el mock, texto decidido por código
# ---------------------------------------------------------------------------------------------------------------------
class ScriptedLLM:
    provider = "mock"

    def __init__(self, model: str, respond: Callable[[list[Message]], str], seed: int | None = None):
        self.model, self.respond = model, respond
        self.seed = get_settings().seed if seed is None else seed

    def chat(self, messages: list[Message], tools: list[dict[str, Any]] | None = None, *, system: str | None = None,
             max_tokens: int = 512, temperature: float = 0.0, call_key: tuple = ("", 0)) -> LLMResponse:
        text = self.respond(messages)
        rng = stable_rng("scripted-llm", self.seed, self.model, *call_key)
        in_tok = messages_tokens(messages, system, tools)
        out_tok = min(count_tokens(text), max_tokens)
        ttft, per_out, per_in = MODEL_PROFILES[self.model]
        import math
        lat = ttft * math.exp(rng.gauss(0, 0.25)) + out_tok * per_out * math.exp(rng.gauss(0, 0.15)) + in_tok * per_in
        if rng.random() < NATURAL_TAIL_PROB:
            lat *= NATURAL_TAIL_FACTOR
        return LLMResponse(content=text, tool_calls=[], usage=Usage(in_tok, out_tok), finish_reason="stop", model=self.model,
                           provider="mock", latency_s=round(lat, 4), response_id="resp_" + stable_hex(12, self.seed, *call_key),
                           meta={})


@dataclass(frozen=True)
class AgentDef:
    name: str
    tools: tuple[str, ...]
    model: str
    system_prompt: str


AGENT_DEFS: dict[str, AgentDef] = {
    "orders-agent": AgentDef("orders-agent", ("get_order",), "mock-small",
                             "Eres el agente de pedidos de SupportOps. Solo consultas el estado de pedidos con get_order. "
                             "Responde en español, breve y sin inventar datos."),
    "billing-agent": AgentDef("billing-agent", ("get_order", "issue_refund"), "mock-large",
                              "Eres el agente de facturación de SupportOps. Puedes consultar pedidos y emitir reembolsos "
                              "(solo pedidos entregados hace 30 días o menos). Verifica antes de reembolsar; no inventes datos."),
    "knowledge-agent": AgentDef("knowledge-agent", ("search_kb",), "mock-small",
                                "Eres el agente de conocimiento de SupportOps. Respondes solo con lo que devuelve search_kb "
                                "(políticas, garantía, guías). Si no hay información, dilo."),
    "escalation-agent": AgentDef("escalation-agent", ("escalate_to_human",), "mock-small",
                                 "Eres el agente de escalado de SupportOps. Derivas el caso a una persona con "
                                 "escalate_to_human y confirmas la referencia al cliente."),
}

ROUTER_SYSTEM = ("Eres el enrutador del orquestador de SupportOps. Clasifica el ticket y elige UN agente especialista: "
                 "orders-agent (estado de pedidos), billing-agent (reembolsos), knowledge-agent (políticas y guías), "
                 "escalation-agent (quejas, pedir una persona). Responde solo JSON: {\"intent\":..., \"agent\":...}.")
SYNTH_SYSTEM = ("Eres el orquestador de SupportOps. Con los resultados de los agentes especialistas redacta la respuesta final "
                "al cliente en español, breve y amable. No añadas datos que no estén en los resultados.")


def make_specialist(name: str, instr: Instrumentor | None, seed: int | None = None) -> SupportAgent:
    """Un ``SupportAgent`` con herramientas restringidas, su propio modelo y semilla (así no comparten ruido de latencia)."""
    d = AGENT_DEFS[name]
    full = default_tools()
    reg = ToolRegistry()
    for t in d.tools:
        reg.register(full.get(t))
    s = get_settings().seed if seed is None else seed
    llm = MockLLM(d.model, seed=int(stable_hex(6, s, name), 16))
    return SupportAgent(llm=llm, tools=reg, instrumentor=instr, name=name, system_prompt=d.system_prompt)


# ---------------------------------------------------------------------------------------------------------------------
# Resiliencia: política de delegación, disyuntor, deadline
# ---------------------------------------------------------------------------------------------------------------------
@dataclass
class DelegationPolicy:
    timeout_s: float = 12.0                # plazo de cada delegación, medido por el orquestador (tiempo simulado)
    max_retries: int = 1                   # reintentos TRAS el primer intento
    backoff_s: float = 0.5                 # espera antes de cada reintento (se duplica en cada uno)
    breaker_threshold: int = 0             # 0 = sin disyuntor; N = abrir tras N fallos consecutivos del mismo agente
    breaker_cooldown_s: float = 60.0
    propagate_deadline: bool = False       # el subagente deja de trabajar al vencer el plazo (no queda «trabajo zombi»)
    fallback_to_human: bool = True         # si el principal falla del todo, derivar a escalation-agent
    best_effort_prechecks: bool = True     # un fallo en los pre-chequeos paralelos no aborta el reembolso


class CircuitBreaker:
    """Disyuntor por agente en tiempo simulado: closed -> open (tras N fallos seguidos) -> half-open tras el cooldown."""

    def __init__(self, threshold: int, cooldown_s: float):
        self.threshold, self.cooldown_s = threshold, cooldown_s
        self.failures, self.opened_at = 0, None

    def allow(self, now_s: float) -> bool:
        if not self.threshold or self.opened_at is None:
            return True
        return now_s - self.opened_at >= self.cooldown_s             # half-open: deja pasar una prueba

    def record(self, ok: bool, now_s: float) -> None:
        if not self.threshold:
            return
        if ok:
            self.failures, self.opened_at = 0, None
        else:
            self.failures += 1
            if self.failures >= self.threshold:
                self.opened_at = now_s


class DeadlineGuard(Instrumentor):
    """Propagación de *deadline*: antes de CADA llamada a LLM/herramienta comprueba el plazo absoluto y, si venció, no la hace.

    Se compone DESPUÉS del instrumentor OTel (``CompositeInstrumentor(otel, guard)``) para que el intento rechazado quede
    registrado como un span con ``error.type=deadline_exceeded``. Una llamada ya iniciada no se interrumpe.
    """

    def __init__(self, deadline_s: float):
        self.deadline_s = deadline_s

    @contextmanager
    def llm_call(self, ctx: RunContext, info: LLMCallInfo) -> Iterator[None]:
        if ctx.clock.now_s() >= self.deadline_s:
            raise LLMError("deadline exceeded", status=504, error_type="deadline_exceeded", retryable=False, latency_s=0.0)
        yield

    @contextmanager
    def tool_call(self, ctx: RunContext, info: ToolCallInfo) -> Iterator[None]:
        if ctx.clock.now_s() >= self.deadline_s:
            raise ToolError("deadline exceeded", "deadline_exceeded", latency_s=0.0)
        yield


# ---------------------------------------------------------------------------------------------------------------------
# Orquestador
# ---------------------------------------------------------------------------------------------------------------------
@dataclass
class MultiResult:
    ticket_id: str
    mode: str
    status: str                          # ok | degraded | escalated | error
    answer: str
    trace_id: str
    start_s: float
    end_s: float
    intent: str | None = None
    primary: str | None = None
    agents_called: list[str] = field(default_factory=list)        # un elemento por intento (con repeticiones)
    attempts: int = 0
    retries: int = 0
    timeouts: int = 0
    fallback_used: bool = False
    zombie_s: float = 0.0                # trabajo del subagente DESPUÉS de que el orquestador abandonara (timeout)
    input_tokens: int = 0                # árbol completo
    output_tokens: int = 0
    cost_usd: float = 0.0
    n_llm_calls: int = 0
    n_tool_calls: int = 0
    per_agent: dict[str, dict[str, float]] = field(default_factory=dict)
    injected_faults: list[str] = field(default_factory=list)
    grounded: bool = True
    pii_leaked: bool = False
    error_type: str | None = None

    @property
    def latency_s(self) -> float:
        return self.end_s - self.start_s

    def to_row(self) -> dict[str, Any]:
        d = dataclasses.asdict(self)
        d["latency_s"] = self.latency_s
        d["agents_called"] = ",".join(self.agents_called)
        d["injected_faults"] = ",".join(self.injected_faults)
        d.pop("per_agent")
        return d


def _tp(t: Ticket, **kw: Any) -> Ticket:
    return dataclasses.replace(t, **kw)


class MultiAgentSupportOps:
    """SupportOps multi-agente. ``mode``: ``delegate`` (hub-and-spoke con síntesis) o ``handoff`` (transferencia al especialista).

    ``propagation``: ``sdk`` (propagador W3C del SDK) · ``manual`` (``inject_manual``/``extract_manual``) · ``none`` (no se
    propaga: cada subagente abre una traza nueva, el bug clásico).
    ``misroute_rate``: probabilidad (determinista por ticket) de que el enrutador elija un especialista equivocado.
    """

    def __init__(self, mesh: Mesh, *, mode: str = "delegate", policy: DelegationPolicy | None = None,
                 propagation: str = "sdk", misroute_rate: float = 0.0, prechecks: bool = True):
        if mode not in ("delegate", "handoff"):
            raise ValueError("mode debe ser 'delegate' o 'handoff'")
        if propagation not in ("sdk", "manual", "none"):
            raise ValueError("propagation debe ser 'sdk', 'manual' o 'none'")
        self.mesh, self.mode, self.policy = mesh, mode, policy or DelegationPolicy()
        self.propagation, self.misroute_rate, self.prechecks = propagation, misroute_rate, prechecks
        self.breakers: dict[str, CircuitBreaker] = {}
        self._meter = None
        h = mesh.handle(ORCH)
        if h.meter_provider is not None:
            m = h.meter()
            self._m_attempts = m.create_counter("supportops.delegation.attempts", unit="{attempt}",
                                                description="Intentos de delegación del orquestador a subagentes")
            self._m_handoffs = m.create_counter("supportops.handoffs", unit="{handoff}",
                                                description="Transferencias de control a un especialista")
        else:
            self._m_attempts = self._m_handoffs = None

    # -- propagación -----------------------------------------------------------------------------------------------
    def _carrier(self) -> dict[str, str]:
        if self.propagation == "none":
            return {}
        return inject_manual() if self.propagation == "manual" else inject_sdk()

    def _remote_context(self, carrier: dict[str, str]) -> Context | None:
        if self.propagation == "none":
            return None
        return extract_manual(carrier) if self.propagation == "manual" else extract_sdk(carrier)

    # -- una llamada a un subagente (con su span CLIENT en el orquestador) --------------------------------------------
    def _faults_for(self, agent: str, ticket: Ticket, attempt: int, primary: bool) -> list[FaultSpec]:
        out = []
        for f in ticket.faults:
            tgt = f.params.get("agent")
            applies = tgt == agent or (tgt is None and primary)
            if applies and (attempt == 0 or f.params.get("sticky")):
                out.append(f)
        return out

    def _attempt(self, st: "_State", agent: str, task_text: str, t0_s: float, *, primary: bool, attempt: int,
                 deadline_abs_s: float | None) -> tuple[AgentResult | None, float, str | None]:
        """Un intento de delegación. Devuelve (resultado del subagente | None, instante de fin en el orquestador, error)."""
        pol, tracer = self.policy, self.mesh.handle(ORCH).tracer()
        br = self.breakers.setdefault(agent, CircuitBreaker(pol.breaker_threshold, pol.breaker_cooldown_s))
        t0_ns = int(round(t0_s * 1e9))
        attrs = {"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": agent, "gen_ai.provider.name": "supportops",
                 "gen_ai.conversation.id": st.ticket.ticket_id, "supportops.ticket.id": st.ticket.ticket_id,
                 "supportops.delegation.attempt": attempt, "supportops.delegation.role": "primary" if primary else "precheck",
                 "supportops.delegation.timeout_s": pol.timeout_s}
        span = tracer.start_span(f"invoke_agent {agent}", kind=SpanKind.CLIENT, start_time=t0_ns, attributes=attrs)
        if not br.allow(t0_s):
            span.set_attribute("error.type", "circuit_open")
            span.set_status(Status(StatusCode.ERROR, "circuit breaker open"))
            span.end(end_time=t0_ns)
            self._count(agent, "circuit_open")
            return None, t0_s, "circuit_open"
        res: AgentResult | None = None
        with otel_trace.use_span(span, end_on_exit=False, record_exception=False, set_status_on_exception=False):
            carrier = self._carrier()
            sub_ticket = _tp(st.ticket, created_at=t0_s, text=task_text, faults=self._faults_for(agent, st.ticket, attempt, primary))
            instr: Instrumentor = self.mesh.instr(agent)
            if pol.propagate_deadline and deadline_abs_s is not None:
                instr = CompositeInstrumentor(instr, DeadlineGuard(deadline_abs_s))
            sub = make_specialist(agent, instr)
            with attached(self._remote_context(carrier)):          # <- el «otro proceso» extrae el contexto de la cabecera
                res = sub.run(sub_ticket)
        self.mesh.record_invocation(agent, res.latency_s, res.error_type if res.status in FAIL_STATUS else None)
        elapsed = res.latency_s
        err: str | None = None
        if elapsed > pol.timeout_s:
            err, end_s = "timeout", t0_s + pol.timeout_s
            st.zombie_s += elapsed - pol.timeout_s                 # el subagente siguió trabajando (y gastando) tras el abandono
            st.timeouts += 1
        else:
            end_s = t0_s + elapsed
            if res.status in FAIL_STATUS:
                err = res.error_type or res.status
        st.account(agent, res)
        if err:
            span.set_attribute("error.type", err)
            span.set_status(Status(StatusCode.ERROR, err))
        span.set_attribute("supportops.sub.status", res.status)
        span.end(end_time=int(round(end_s * 1e9)))
        br.record(err is None, end_s)
        self._count(agent, "ok" if err is None else ("timeout" if err == "timeout" else "error"))
        return res, end_s, err

    def _count(self, agent: str, outcome: str) -> None:
        if self._m_attempts is not None:
            self._m_attempts.add(1, {"gen_ai.agent.name": agent, "supportops.outcome": outcome, "supportops.mode": self.mode})

    def _call_with_retries(self, st: "_State", agent: str, task_text: str, t0_s: float, *, primary: bool,
                           allow_retry: bool = True) -> tuple[AgentResult | None, float, str | None]:
        pol = self.policy
        t = t0_s
        deadline = t0_s + pol.timeout_s
        res, err = None, None
        for attempt in range(1 + (pol.max_retries if allow_retry else 0)):
            if attempt:
                st.retries += 1
                t += pol.backoff_s * (2 ** (attempt - 1))
                deadline = t + pol.timeout_s
            res, t, err = self._attempt(st, agent, task_text, t, primary=primary, attempt=attempt, deadline_abs_s=deadline)
            if err is None:
                break
            if err == "circuit_open":
                break
        return res, t, err

    # -- el orquestador ---------------------------------------------------------------------------------------------
    def run(self, ticket: Ticket | str) -> MultiResult:
        if isinstance(ticket, str):
            ticket = Ticket("T-adhoc-0001", "C-0001", "standard", "chat", ticket, "unknown", 1_788_253_200.0)
        s = get_settings()
        st = _State(ticket)
        clock = SimClock(start_s=ticket.created_at, sleep_scale=s.sleep_scale)
        h = self.mesh.handle(ORCH)
        if h.ids.deterministic:
            h.begin_trace(stable_hex(32, s.seed, ticket.ticket_id))
        wf = h.tracer().start_span("invoke_workflow support_ticket", kind=SpanKind.INTERNAL, start_time=clock.now_ns(), attributes={
            "gen_ai.operation.name": "invoke_workflow", "gen_ai.workflow.name": "support_ticket",
            "gen_ai.conversation.id": ticket.ticket_id, "supportops.ticket.id": ticket.ticket_id,
            "supportops.customer.id": ticket.customer_id, "supportops.customer.tier": ticket.tier,
            "supportops.channel": ticket.channel, "supportops.topology": self.mode})
        trace_id = format(wf.get_span_context().trace_id, "032x")
        with otel_trace.use_span(wf, end_on_exit=False, record_exception=False, set_status_on_exception=False):
            answer, status, intent, primary, error_type = self._orchestrate(st, clock)
        grounded = all(r.grounded for r in st.results)
        pii = any(r.pii_leaked for r in st.results)
        injected = sorted({f for r in st.results for f in r.injected_faults} | set(st.orch_faults))
        tin = st.own_in + sum(r.input_tokens for r in st.results)
        tout = st.own_out + sum(r.output_tokens for r in st.results)
        cost = st.own_cost + sum(r.cost_usd for r in st.results)
        wf.set_attributes({"supportops.status": status, "supportops.tree.cost_usd": round(cost, 6),
                           "supportops.tree.input_tokens": tin, "supportops.tree.output_tokens": tout,
                           "supportops.tree.agent_calls": len(st.agents_called), "supportops.tree.retries": st.retries,
                           "supportops.tree.timeouts": st.timeouts})
        if status in ("error",):
            wf.set_attribute("error.type", error_type or "error")
            wf.set_status(Status(StatusCode.ERROR, status))
        wf.end(end_time=clock.now_ns())
        per_agent = {a: dict(v) for a, v in st.per_agent.items()}
        per_agent[ORCH] = {"cost_usd": st.own_cost, "input_tokens": st.own_in, "output_tokens": st.own_out,
                           "llm_calls": st.own_llm_calls, "latency_s": 0.0}
        return MultiResult(
            ticket.ticket_id, self.mode, status, answer, trace_id, clock.start_s, clock.now_s(), intent=intent, primary=primary,
            agents_called=list(st.agents_called), attempts=len(st.agents_called), retries=st.retries, timeouts=st.timeouts,
            fallback_used=st.fallback_used, zombie_s=round(st.zombie_s, 4), input_tokens=tin, output_tokens=tout,
            cost_usd=round(cost, 6), n_llm_calls=st.own_llm_calls + sum(r.n_llm_calls for r in st.results),
            n_tool_calls=sum(r.n_tool_calls for r in st.results), per_agent=per_agent, injected_faults=injected,
            grounded=grounded, pii_leaked=pii, error_type=error_type)

    def run_many(self, tickets: Sequence[Ticket]) -> list[MultiResult]:
        return [self.run(t) for t in tickets]

    # -- piezas ---------------------------------------------------------------------------------------------------
    def _orchestrate(self, st: "_State", clock: SimClock) -> tuple[str, str, str | None, str | None, str | None]:
        t, s = st.ticket, get_settings()
        instr = self.mesh.instr(ORCH)
        octx = RunContext(t, ORCH, clock, "mock-small", "mock", run_id=stable_hex(12, s.seed, t.ticket_id, "orch"))
        orch_faults = [f for f in t.faults if f.params.get("agent") == ORCH]
        inj = FaultInjector(orch_faults)
        intent, primary, clarify, answer, status, error_type = None, None, None, "", "ok", None
        with instr.agent_run(octx):
            instr.log(octx, logging.INFO, "ticket recibido por el orquestador", {"ticket_id": t.ticket_id, "channel": t.channel,
                                                                                "tier": t.tier})
            # ---------------------------------------------------------------- 1) enrutado (LLM pequeño)
            def respond_route(msgs: list[Message]) -> str:
                rule = detect_rule(default_rules(), msgs[0].content)
                ok = rule.needs(msgs[0].content)
                agent = INTENT_PRIMARY[rule.intent]
                if self.misroute_rate and stable_rng("misroute", s.seed, t.ticket_id).random() < self.misroute_rate:
                    agent = next(a for a in SPECIALISTS if a != agent)
                return json.dumps({"intent": rule.intent, "agent": agent, "clarify": (not ok and rule.clarify),
                                   "clarify_text": rule.missing_answer if (not ok and rule.clarify) else ""}, ensure_ascii=False)
            router = inj.wrap_llm(ScriptedLLM("mock-small", respond_route))
            try:
                resp = self._llm_step(st, octx, instr, router, [Message("user", t.text)], ROUTER_SYSTEM, 0)
                route = json.loads(resp.content)
                intent, primary, clarify = route["intent"], route["agent"], route["clarify_text"] if route["clarify"] else None
            except LLMError as e:
                instr.log(octx, logging.WARNING, "enrutador no disponible: escalado directo", {"error_type": e.error_type})
                intent, primary, error_type = "unknown", "escalation-agent", e.error_type
            st.orch_faults = list(inj.triggered)
            # ---------------------------------------------------------------- 2a) pregunta aclaratoria: sin subagentes
            if clarify:
                answer = clarify
            # ---------------------------------------------------------------- 2b) handoff
            elif self.mode == "handoff":
                self._handoff(st, octx, instr, clock, primary)
            # ---------------------------------------------------------------- 2c) delegación
            else:
                answer, status = self._delegate(st, octx, instr, clock, intent or "", primary)
            octx.result = st.own_result(t, status if self.mode == "delegate" else "ok", answer or "(transferido)", intent, error_type)
        if self.mode == "handoff" and not clarify:
            answer, status = self._run_handoff_target(st, clock, primary)
        return answer, status, intent, primary, error_type

    def _llm_step(self, st: "_State", ctx: RunContext, instr: OTelInstrumentor, llm: Any, messages: list[Message], system: str,
                  step: int) -> LLMResponse:
        info = LLMCallInfo(step, 0, llm.model, llm.provider, len(messages), 256, 0.0, messages)
        t0 = ctx.clock.now_s()
        try:
            with instr.llm_call(ctx, info):
                try:
                    resp = llm.chat(messages, None, system=system, max_tokens=256, temperature=0.0,
                                    call_key=(st.ticket.ticket_id, "orch", step))
                except LLMError as e:
                    ctx.clock.advance(e.latency_s)
                    info.error = e
                    raise
                ctx.clock.advance(resp.latency_s)
                info.response = resp
        except LLMError:
            st.own_llm_calls += 1
            raise
        st.own_llm_calls += 1
        st.own_in += resp.usage.input_tokens
        st.own_out += resp.usage.output_tokens
        st.own_cost += cost_usd(resp.model, resp.usage.input_tokens, resp.usage.output_tokens)
        return resp

    def _delegate(self, st: "_State", octx: RunContext, instr: OTelInstrumentor, clock: SimClock, intent: str,
                  primary: str) -> tuple[str, str]:
        t, pol = st.ticket, self.policy
        m_oid = ORDER_RE.search(t.text)
        oid = m_oid.group(0) if m_oid else None
        ctx_lines: list[str] = []
        # ---- pre-chequeos en PARALELO (solo reembolsos con número de pedido): ambos arrancan en el mismo instante
        if self.prechecks and primary == "billing-agent" and oid:
            t0 = clock.now_s()
            ends = []
            for agent, text in (("orders-agent", f"Estado del pedido {oid}"),
                                ("knowledge-agent", "¿Cuál es la política de devoluciones de la tienda?")):
                res, end_s, err = self._call_with_retries(st, agent, text, t0, primary=False, allow_retry=False)
                ends.append(end_s)
                if res is not None and err is None:
                    ctx_lines.append(f"[{agent}] {res.answer}")
                elif not pol.best_effort_prechecks:
                    clock.advance(max(ends) - clock.now_s())
                    return self._failure(st, octx, instr, clock, "precheck_failed")
            clock.advance(max(max(ends) - clock.now_s(), 0.0))              # join: el orquestador espera al más lento
        # ---- agente principal (con contexto de los pre-chequeos: el prompt crece -> más tokens)
        task = t.text + ("\n\nContexto de otros agentes:\n" + "\n".join(ctx_lines) if ctx_lines else "")
        res, end_s, err = self._call_with_retries(st, primary, task, clock.now_s(), primary=True)
        clock.advance(max(end_s - clock.now_s(), 0.0))
        if err is not None or res is None:
            return self._failure(st, octx, instr, clock, err or "error")
        # ---- síntesis (LLM grande): lee TODAS las respuestas de los agentes
        findings = "\n".join(ctx_lines + [f"[{primary}] {res.answer}"])
        synth = ScriptedLLM("mock-large", lambda msgs, a=res.answer: a)
        self._llm_step(st, octx, instr, synth, [Message("user", t.text), Message("user", "Resultados de los agentes:\n" + findings)],
                       SYNTH_SYSTEM, 1)
        instr.log(octx, logging.INFO, "respuesta sintetizada", {"status": res.status})
        return res.answer, res.status

    def _failure(self, st: "_State", octx: RunContext, instr: OTelInstrumentor, clock: SimClock, why: str) -> tuple[str, str]:
        """El principal falló del todo: fallback a una persona (escalation-agent) o error."""
        instr.log(octx, logging.WARNING, "subagente principal falló", {"error_type": why})
        if self.policy.fallback_to_human:
            st.fallback_used = True
            res, end_s, err = self._call_with_retries(st, "escalation-agent", "Escalar a una persona: " + st.ticket.text,
                                                      clock.now_s(), primary=False, allow_retry=False)
            clock.advance(max(end_s - clock.now_s(), 0.0))
            if res is not None and err is None:
                return res.answer, "escalated"
        return ("Lo siento, no he podido resolver su consulta ahora mismo. Un compañero revisará su caso.", "error")

    def _handoff(self, st: "_State", octx: RunContext, instr: OTelInstrumentor, clock: SimClock, target: str) -> None:
        """Handoff = el orquestador «llama» a una herramienta de transferencia y termina; el especialista continúa."""
        call = ToolCall("handoff_" + stable_hex(8, st.ticket.ticket_id), f"transfer_to_{target}", {"agent": target})
        info = ToolCallInfo(1, call)
        with instr.tool_call(octx, info):
            clock.advance(0.004)
            info.result = {"transferred_to": target}
        if self._m_handoffs is not None:
            self._m_handoffs.add(1, {"supportops.target_agent": target})

    def _run_handoff_target(self, st: "_State", clock: SimClock, target: str) -> tuple[str, str]:
        res, end_s, err = self._call_with_retries(st, target, st.ticket.text, clock.now_s(), primary=True)
        clock.advance(max(end_s - clock.now_s(), 0.0))
        if err is not None or res is None:
            return self._failure_handoff(st, clock, err or "error")
        return res.answer, res.status

    def _failure_handoff(self, st: "_State", clock: SimClock, why: str) -> tuple[str, str]:
        if self.policy.fallback_to_human and st.agents_called[-1] != "escalation-agent":
            st.fallback_used = True
            res, end_s, err = self._call_with_retries(st, "escalation-agent", "Escalar a una persona: " + st.ticket.text,
                                                      clock.now_s(), primary=False, allow_retry=False)
            clock.advance(max(end_s - clock.now_s(), 0.0))
            if res is not None and err is None:
                return res.answer, "escalated"
        return ("Lo siento, no he podido resolver su consulta ahora mismo. Un compañero revisará su caso.", "error")


@dataclass
class _State:
    ticket: Ticket
    results: list[AgentResult] = field(default_factory=list)
    agents_called: list[str] = field(default_factory=list)
    per_agent: dict[str, dict[str, float]] = field(default_factory=dict)
    retries: int = 0
    timeouts: int = 0
    zombie_s: float = 0.0
    fallback_used: bool = False
    own_in: int = 0
    own_out: int = 0
    own_cost: float = 0.0
    own_llm_calls: int = 0
    orch_faults: list[str] = field(default_factory=list)

    def account(self, agent: str, res: AgentResult) -> None:
        self.results.append(res)
        self.agents_called.append(agent)
        d = self.per_agent.setdefault(agent, {"cost_usd": 0.0, "input_tokens": 0, "output_tokens": 0, "llm_calls": 0, "latency_s": 0.0})
        d["cost_usd"] += res.cost_usd
        d["input_tokens"] += res.input_tokens
        d["output_tokens"] += res.output_tokens
        d["llm_calls"] += res.n_llm_calls
        d["latency_s"] += res.latency_s

    def own_result(self, t: Ticket, status: str, answer: str, intent: str | None, error_type: str | None) -> AgentResult:
        """Resultado del orquestador SOLO con su propio consumo (la spec cuenta cada llamada una sola vez en el árbol)."""
        return AgentResult(t.ticket_id, status, answer, [], 0.0, 0.0, "mock-small", "mock", self.own_in, self.own_out,
                           round(self.own_cost, 6), self.own_llm_calls, 0, [], error_type=error_type, intent_pred=intent)


# ---------------------------------------------------------------------------------------------------------------------
# Un subagente en un PROCESO REAL (cola de tareas con cabeceras de propagación)
# ---------------------------------------------------------------------------------------------------------------------
def _worker_main(agent: str, req: Any, resp: Any, mode: str) -> None:           # pragma: no cover  (corre en otro proceso)
    os.environ.setdefault("LLM_PROVIDER", "mock")
    tel = setup_telemetry(service_name(agent), mode=mode, set_global=False, service_version=SERVICE_VERSION,
                          resource_attrs={"process.pid": os.getpid()}, logs=False, metrics=False)
    instr = OTelInstrumentor(tel)
    tracer = tel.tracer()
    while True:
        task = req.get()
        if task is None:
            break
        ticket = Ticket.from_dict(task["ticket"])
        carrier, link_mode = task["headers"], task["link_mode"]
        parent = extract_sdk(carrier) if task["propagation"] == "sdk" else extract_manual(carrier)
        start_ns = int(round(task["start_s"] * 1e9))
        links = [Link(otel_trace.get_current_span(parent).get_span_context())] if (parent and link_mode in ("link", "both")) else []
        ctx_parent = parent if (parent and link_mode in ("parent", "both")) else None
        span = tracer.start_span(f"process {task['queue']}", context=ctx_parent if ctx_parent else Context(), kind=SpanKind.CONSUMER,
                                 start_time=start_ns, links=links, attributes={
                                     "messaging.system": "supportops-queue", "messaging.destination.name": task["queue"],
                                     "messaging.operation.type": "process", "messaging.operation.name": "process",
                                     "messaging.message.id": task["message_id"]})
        sub_ticket = dataclasses.replace(ticket, created_at=task["start_s"])
        with otel_trace.use_span(span, end_on_exit=False, record_exception=False, set_status_on_exception=False):
            res = make_specialist(agent, instr).run(sub_ticket)
        span.end(end_time=int(round(res.end_s * 1e9)))
        tel.force_flush()
        resp.put({"spans": span_rows(tel), "result": res.to_dict(), "pid": os.getpid()})
        tel.reset_local()


class RemoteAgentProcess:
    """Un especialista en un proceso del sistema operativo distinto, alimentado por una cola (``multiprocessing.Queue``).

    ``call(...)`` publica un mensaje con las cabeceras de propagación y espera la respuesta. El proceso hijo crea su propio
    ``TelemetryHandle`` y devuelve sus spans (en producción los exportaría él mismo por OTLP).
    ``link_mode``: ``parent`` (el consumidor es hijo del productor) · ``link`` (nueva traza + *span link*, patrón de mensajería
    de la spec) · ``both`` · ``none`` (cabeceras ignoradas).
    """

    def __init__(self, agent: str = "orders-agent", *, mode: str = "memory"):
        ctx = mp.get_context("spawn")
        self.agent, self.req, self.resp = agent, ctx.Queue(), ctx.Queue()
        self.proc = ctx.Process(target=_worker_main, args=(agent, self.req, self.resp, mode), daemon=True)
        self.proc.start()
        self._n = 0

    def call(self, ticket: Ticket, headers: dict[str, str], start_s: float, *, queue: str = "supportops.tasks",
             link_mode: str = "parent", propagation: str = "sdk", timeout_s: float = 60.0) -> dict[str, Any]:
        self._n += 1
        self.req.put({"ticket": ticket.to_dict(), "headers": headers, "start_s": start_s, "queue": queue,
                      "link_mode": link_mode, "propagation": propagation, "message_id": f"msg-{self._n:04d}"})
        return self.resp.get(timeout=timeout_s)

    def close(self) -> None:
        try:
            self.req.put(None)
            self.proc.join(timeout=10)
        finally:
            if self.proc.is_alive():
                self.proc.terminate()

    def __enter__(self) -> "RemoteAgentProcess":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


# ---------------------------------------------------------------------------------------------------------------------
# Análisis de trazas (sobre filas con el esquema SPAN_SCHEMA)
# ---------------------------------------------------------------------------------------------------------------------
def span_frame(rows: Sequence[dict[str, Any]]):
    """DataFrame con columnas derivadas: service, agent, op, dur_s, tokens, cost…"""
    import pandas as pd
    out = []
    for r in rows:
        a = r["attributes"]
        out.append({
            "trace_id": r["trace_id"], "span_id": r["span_id"], "parent": r["parent_span_id"], "name": r["name"], "kind": r["kind"],
            "service": r["resource"].get("service.name", "?"), "op": a.get("gen_ai.operation.name"),
            "agent": a.get("gen_ai.agent.name"), "start_ns": r["start_unix_nano"], "end_ns": r["end_unix_nano"],
            "dur_s": ((r["end_unix_nano"] or r["start_unix_nano"]) - r["start_unix_nano"]) / 1e9,
            "status": r["status"], "error_type": a.get("error.type"),
            "in_tok": a.get("gen_ai.usage.input_tokens", 0) or 0, "out_tok": a.get("gen_ai.usage.output_tokens", 0) or 0,
            "cost": a.get("supportops.cost_usd", 0.0) or 0.0, "n_links": len(r.get("links", [])), "pid": r["resource"].get("process.pid"),
        })
    return pd.DataFrame(out)


def _children(rows: Sequence[dict[str, Any]]) -> tuple[dict[str | None, list[dict[str, Any]]], dict[str, dict[str, Any]]]:
    by_id = {r["span_id"]: r for r in rows}
    kids: dict[str | None, list[dict[str, Any]]] = {}
    for r in rows:
        p = r["parent_span_id"] if r["parent_span_id"] in by_id else None
        kids.setdefault(p, []).append(r)
    for v in kids.values():
        v.sort(key=lambda x: (x["start_unix_nano"], -(x["end_unix_nano"] or 0)))
    return kids, by_id


def agent_tree_text(rows: Sequence[dict[str, Any]], *, ops: tuple[str, ...] = ("invoke_workflow", "invoke_agent", "execute_tool"),
                    show_chat: bool = False) -> str:
    """Árbol de agentes en texto: solo operaciones de agente/herramienta (y opcionalmente chat) con duración y estado."""
    kids, _ = _children(rows)
    lines: list[str] = []

    def walk(pid: str | None, depth: int) -> None:
        for r in kids.get(pid, []):
            op = r["attributes"].get("gen_ai.operation.name")
            keep = op in ops or (show_chat and op == "chat")
            nd = depth + 1 if keep else depth
            if keep:
                dur = ((r["end_unix_nano"] or r["start_unix_nano"]) - r["start_unix_nano"]) / 1e9
                err = f"  ✖ {r['attributes'].get('error.type')}" if r["status"] == "ERROR" else ""
                svc = r["resource"].get("service.name", "?")
                lines.append(f"{'  ' * depth}{r['name']}  [{r['kind'][:3]}·{svc.replace('supportops-', '')}]  {dur:.2f}s{err}")
            walk(r["span_id"], nd)

    walk(None, 0)
    return "\n".join(lines)


def critical_path(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Camino crítico (aprox.): desde la raíz, en cada nivel el hijo que termina el último (el que «sostiene» al padre)."""
    kids, _ = _children(rows)
    roots = kids.get(None, [])
    if not roots:
        return []
    path, node = [], max(roots, key=lambda r: r["end_unix_nano"] or 0)
    while node:
        path.append(node)
        ch = kids.get(node["span_id"], [])
        node = max(ch, key=lambda r: r["end_unix_nano"] or 0) if ch else None
    return path


def cost_rollup(rows: Sequence[dict[str, Any]], price_fn: Callable[[str, int, int], float] = cost_usd) -> dict[str, dict[str, float]]:
    """Coste por servicio contando SOLO los spans ``chat`` (hojas): cada llamada al LLM se cuenta una única vez."""
    out: dict[str, dict[str, float]] = {}
    for r in rows:
        a = r["attributes"]
        if a.get("gen_ai.operation.name") != "chat":
            continue
        svc = r["resource"].get("service.name", "?")
        d = out.setdefault(svc, {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0})
        i, o = a.get("gen_ai.usage.input_tokens", 0) or 0, a.get("gen_ai.usage.output_tokens", 0) or 0
        d["calls"] += 1
        d["input_tokens"] += i
        d["output_tokens"] += o
        d["cost_usd"] += price_fn(a.get("gen_ai.response.model") or a.get("gen_ai.request.model", ""), i, o)
    return out


def service_palette(rows: Sequence[dict[str, Any]]) -> dict[str, str]:
    colors = ["#2a6fdb", "#e8833a", "#2f9e63", "#8e5bd0", "#c2409a", "#0f9fb0", "#6b7280"]
    svcs = sorted({r["resource"].get("service.name", "?") for r in rows}, key=lambda s: (s != ORCH, s))
    return {s: colors[i % len(colors)] for i, s in enumerate(svcs)}


def waterfall_services(rows: Sequence[dict[str, Any]], ax: Any = None, title: str = "", hide_chat: bool = False) -> Any:
    """Cascada de una traza multi-servicio: color por ``service.name``, contorno rojo = ERROR, ▸ = span de otro servicio que enlaza."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    rows = [r for r in rows if not (hide_chat and r["attributes"].get("gen_ai.operation.name") == "chat")]
    kids, by_id = _children(rows)
    ordered: list[tuple[int, dict[str, Any]]] = []

    def walk(pid: str | None, d: int) -> None:
        for r in kids.get(pid, []):
            ordered.append((d, r))
            walk(r["span_id"], d + 1)

    walk(None, 0)
    pal = service_palette(rows)
    t0 = min(r["start_unix_nano"] for r in rows)
    if ax is None:
        fig, ax = plt.subplots(figsize=(11, 0.34 * len(ordered) + 1.4))
        fig.subplots_adjust(left=0.36)
    for i, (d, r) in enumerate(ordered):
        st = (r["start_unix_nano"] - t0) / 1e9
        du = ((r["end_unix_nano"] or r["start_unix_nano"]) - r["start_unix_nano"]) / 1e9
        err = r["status"] == "ERROR"
        ax.barh(i, max(du, 0.02), left=st, color=pal[r["resource"].get("service.name", "?")], alpha=0.9, height=0.62,
                edgecolor="#d64545" if err else "none", linewidth=2 if err else 0)
        ax.annotate(r["name"], xy=(0, i), xycoords=("axes fraction", "data"), xytext=(-330 + 10 * d, 0), textcoords="offset points",
                    ha="left", va="center", fontsize=7.5)
        ax.text(st + du, i, f" {du:.2f}s", va="center", fontsize=7, color="#6b7280")
    ax.set_yticks([])
    ax.invert_yaxis()
    ax.set_xlabel("tiempo simulado desde el inicio (s)")
    ax.grid(axis="y", visible=False)
    ax.legend(handles=[Patch(color=c, label=s.replace("supportops-", "")) for s, c in pal.items()], loc="lower right", fontsize=7.5,
              ncol=2)
    if title:
        ax.set_title(title)
    return ax
