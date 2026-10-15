"""Tráfico multi-servicio para los módulos 07 (Tempo/TraceQL) y 08 (Loki/LogQL) (autor A3). No edita ``telemetry.py``.

SupportOps v0 es **un** servicio; para practicar TraceQL estructural y *service graphs* hacen falta varios. Este módulo añade
servicios «aguas abajo» simulados, que **reciben el contexto por cabecera W3C** (``propagate.inject/extract``, como en
el módulo 03) y crean spans SERVER con su propio ``service.name``::

    supportops-agent ──chat (CLIENT)────────────▶ llm-gateway   (POST /v1/chat/completions, SERVER)
                     ──GET /orders (CLIENT)─────▶ orders-api    (SERVER) ──SELECT (CLIENT, db.system)──▶ [orders: base de datos]
                     ──GET /kb/search (CLIENT)──▶ kb-search     (SERVER)

Uso::

    from supportops.tempo_lab import run_batch, wait_for_traces
    b = run_batch(120, seed=42, live=True)          # exporta por OTLP si hay Collector; si no, solo memoria
    b.spans            # copias locales de TODOS los spans (esquema SPAN_SCHEMA): úsalas con ``traceql_mini``
    b.results          # una fila por ticket (ground truth: status, injected_faults, ...)
    b.trace_ids        # ticket_id -> trace_id
    wait_for_traces(list(b.trace_ids.values())[:5])     # polling con plazo hasta que Tempo las encuentre

Los fallos del lote (ventana de 10 min) cuentan una historia diagnosticable: fondo con ``DEFAULT_FAULT_RATES``; límite de
tasa 429 que el reintento resuelve (0:30-2:00); proveedor LLM degradado (503 persistentes) entre 3:00 y 4:30; ``get_order``
roto (upstream_500) y herramientas lentas (×8) entre 5:30 y 7:30; y bucles de herramientas entre 8:00 y 9:20.
``orders-api`` marca ERROR los spans de los pedidos que fallan.
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator, Sequence

from . import backends
from .agent import SupportAgent
from .clock import SIM_EPOCH_S, stable_rng
from .instrument import CompositeInstrumentor, Instrumentor, LLMCallInfo, RunContext, ToolCallInfo
from .telemetry import OTelInstrumentor, TelemetryHandle, setup_telemetry
from .traffic import DEFAULT_FAULT_RATES, Incident, generate_tickets, run_tickets, to_rows

__all__ = ["Batch", "run_batch", "wait_for_traces", "INCIDENT_STORY", "make_incidents", "DOWNSTREAM"]

DOWNSTREAM = {"chat": "llm-gateway", "get_order": "orders-api", "issue_refund": "orders-api", "search_kb": "kb-search"}

INCIDENT_STORY = [
    ("rate_limited", "llm_error", 30, 120, 0.5, {"status": 429, "persistent": False, "at_call": 0}),      # 1.er intento 429, el reintento funciona
    ("llm_provider_degraded", "llm_error", 180, 270, 0.7, {"status": 503, "persistent": True}),
    ("search_loop", "tool_loop", 480, 560, 0.4, {}),
    ("orders_api_broken", "tool_error", 330, 450, 0.55, {"tool": "get_order", "error_type": "upstream_500"}),
    ("tools_slow", "latency_spike", 330, 450, 0.5, {"factor": 8.0, "target": "tool"}),
]


def make_incidents() -> list[Incident]:
    return [Incident(n, k, a, b, p, dict(prm)) for n, k, a, b, p, prm in INCIDENT_STORY]


# ---------------------------------------------------------------------------------------------------------------------
class DownstreamInstrumentor(Instrumentor):
    """Crea, dentro de ``chat`` y ``execute_tool``, el span CLIENT de la llamada de red (si no existe) y su SERVER remoto.

    Debe componerse **después** de ``OTelInstrumentor``: ``CompositeInstrumentor(OTelInstrumentor(tel), DownstreamInstrumentor(...))``
    para que el span del agente esté activo en el contexto cuando se ejecute este hook.
    """

    def __init__(self, agent_handle: TelemetryHandle, services: dict[str, TelemetryHandle], seed: int = 42):
        from opentelemetry import propagate, trace
        from opentelemetry.trace import SpanKind, Status, StatusCode
        self._p, self._t, self._K, self._S, self._C = propagate, trace, SpanKind, Status, StatusCode
        self.agent, self.svc, self.seed = agent_handle, services, seed

    # -- utilidades -----------------------------------------------------------------------------------------------
    def _server(self, service: str, name: str, parent_ctx, t0: int, t1: int, attrs: dict[str, Any], error: str | None):
        tracer = self.svc[service].tracer()
        sp = tracer.start_span(name, kind=self._K.SERVER, context=parent_ctx, start_time=t0, attributes=attrs)
        if error:
            sp.set_attribute("error.type", error)
            sp.set_status(self._S(self._C.ERROR, error))
        return sp

    def _carrier_ctx(self, span) -> Any:
        carrier: dict[str, str] = {}
        with self._t.use_span(span, end_on_exit=False):
            self._p.inject(carrier)                                      # cabecera W3C `traceparent` del CLIENT
        return self._p.extract(carrier)                                  # lado servidor: reconstruye el contexto

    # -- hooks ----------------------------------------------------------------------------------------------------
    @contextmanager
    def llm_call(self, ctx: RunContext, info: LLMCallInfo) -> Iterator[None]:
        t0, err = ctx.clock.now_ns(), None
        try:
            yield
        except BaseException as e:
            err = e
            raise
        finally:
            t1 = max(ctx.clock.now_ns(), t0 + 2)
            parent = self._t.get_current_span()                          # el span `chat` (CLIENT) de OTelInstrumentor
            status = int(getattr(err, "status", 200)) if err is not None else 200
            sp = self._server("llm-gateway", "POST /v1/chat/completions", self._carrier_ctx(parent), t0 + 1, t1 - 1, {
                "http.request.method": "POST", "http.route": "/v1/chat/completions", "http.response.status_code": status,
                "gen_ai.provider.name": info.provider, "gen_ai.request.model": info.model}, f"http_{status}" if status >= 500 else None)
            sp.end(end_time=max(t1 - 1, t0 + 1))

    @contextmanager
    def tool_call(self, ctx: RunContext, info: ToolCallInfo) -> Iterator[None]:
        service = DOWNSTREAM.get(info.call.name)
        t0, err = ctx.clock.now_ns(), None
        try:
            yield
        except BaseException as e:
            err = e
            raise
        finally:
            t1 = max(ctx.clock.now_ns(), t0 + 8)
            if service is not None:
                self._remote_tool(ctx, info, service, t0, t1, err)

    def _remote_tool(self, ctx: RunContext, info: ToolCallInfo, service: str, t0: int, t1: int, err: BaseException | None) -> None:
        route = {"get_order": "/orders/{id}", "issue_refund": "/orders/{id}/refund", "search_kb": "/kb/search"}[info.call.name]
        method = "POST" if info.call.name == "issue_refund" else "GET"
        etype = getattr(err, "error_type", type(err).__name__) if err is not None else None
        status = 500 if err is not None else 200
        tracer = self.agent.tracer()
        # CLIENT en el agente (hijo del span execute_tool activo)
        client = tracer.start_span(f"{method} {route}", kind=self._K.CLIENT, start_time=t0 + 1, attributes={
            "http.request.method": method, "http.route": route, "http.response.status_code": status, "server.address": service,
            "peer.service": service, "gen_ai.tool.name": info.call.name})
        if err is not None:
            client.set_attribute("error.type", etype or "error")
            client.set_status(self._S(self._C.ERROR, etype or "error"))
        server = self._server(service, f"{method} {route}", self._carrier_ctx(client), t0 + 2, t1 - 2, {
            "http.request.method": method, "http.route": route, "http.response.status_code": status}, etype)
        if service == "orders-api":                                       # consulta SQL (CLIENT con db.system): nodo virtual en el service graph
            rng = stable_rng("sql", self.seed, ctx.ticket.ticket_id, info.step)
            span_ctx = self._t.set_span_in_context(server)
            db0 = t0 + 3
            db1 = max(db0 + 1, t0 + 3 + int((t1 - t0 - 6) * rng.uniform(0.3, 0.8)))
            db = self.svc[service].tracer().start_span("SELECT orders", kind=self._K.CLIENT, context=span_ctx, start_time=db0, attributes={
                "db.system": "postgresql", "db.name": "orders", "db.operation": "SELECT", "peer.service": "orders-db"})
            db.end(end_time=min(db1, t1 - 3))
        server.end(end_time=max(t1 - 2, t0 + 3))
        client.end(end_time=max(t1 - 1, t0 + 2))


# ---------------------------------------------------------------------------------------------------------------------
@dataclass
class Batch:
    spans: list[dict[str, Any]]
    results: list[dict[str, Any]]
    trace_ids: dict[str, str]
    meta: dict[str, Any] = field(default_factory=dict)


def run_batch(n: int = 120, seed: int = 42, *, live: bool = True, duration_s: float = 600.0, export: bool | None = None,
              endpoint: str | None = None, services: bool = True, background_faults: bool = True,
              extra: Sequence[Instrumentor] = ()) -> Batch:
    """Genera ``n`` tickets (con el relato de incidentes) y los ejecuta con instrumentación completa.

    ``live=True`` ancla la ventana para que termine ahora (necesario para Tempo/Loki). ``export=None`` exporta por OTLP si
    el Collector responde en el puerto 4318; ``export=False`` deja los spans solo en memoria (modo degradado / datos
    pregrabados). Siempre se guardan copias locales (``Batch.spans``), también cuando se exporta.
    """
    mode = "memory" if export is False else ("otlp" if export else "auto")
    kw = dict(mode=mode, endpoint=endpoint, metric_interval_s=2.0)
    agent_tel = setup_telemetry("supportops-agent", metrics=True, logs=True, **kw)
    downstream = {"llm-gateway": setup_telemetry("llm-gateway", metrics=False, logs=False, set_global=False, **kw),
                  "orders-api": setup_telemetry("orders-api", metrics=False, logs=False, set_global=False, **kw),
                  "kb-search": setup_telemetry("kb-search", metrics=False, logs=False, set_global=False, **kw)}
    otel = OTelInstrumentor(agent_tel)
    parts: list[Instrumentor] = [otel] + ([DownstreamInstrumentor(agent_tel, downstream, seed)] if services else []) + list(extra)
    instr: Instrumentor = CompositeInstrumentor(*parts) if len(parts) > 1 else otel
    agent = SupportAgent(instrumentor=instr)
    tickets = generate_tickets(n, seed, duration_s=duration_s, fault_rates=DEFAULT_FAULT_RATES if background_faults else None,
                               incidents=make_incidents(), start_s="live" if live else SIM_EPOCH_S)
    results = run_tickets(agent, tickets)
    for t in [agent_tel, *downstream.values()]:
        t.force_flush()
    spans = [s for t in [agent_tel, *downstream.values()] for s in t.span_records()]
    trace_ids = dict(otel.trace_ids)
    meta = {"mode": agent_tel.mode, "endpoint": agent_tel.endpoint, "n": n, "seed": seed, "live": live, "duration_s": duration_s,
            "window": (tickets[0].created_at, tickets[-1].created_at), "export_stats": agent_tel.span_export_stats}
    rows = to_rows(tickets, results)
    for t in [agent_tel, *downstream.values()]:
        t.shutdown()
    return Batch(sorted(spans, key=lambda s: s["start_unix_nano"]), rows, trace_ids, meta)


def wait_for_traces(trace_ids: list[str], timeout_s: float = 60.0, every_s: float = 2.0, verbose: bool = True) -> bool:
    """Polling con plazo: espera hasta que ``/api/traces/<id>`` devuelva TODAS las trazas (las nuevas tardan de unos
    segundos a ~30 s en ser consultables). Devuelve ``True`` si aparecieron todas antes del plazo."""
    deadline, pending, t0 = time.time() + timeout_s, list(trace_ids), time.time()
    while pending and time.time() < deadline:
        still = []
        for tid in pending:
            try:
                backends.tempo_trace(tid)
            except backends.BackendError:
                still.append(tid)
        pending = still
        if pending:
            time.sleep(every_s)
    if verbose:
        print(f"{len(trace_ids) - len(pending)}/{len(trace_ids)} trazas visibles en Tempo tras {time.time() - t0:.0f} s")
    return not pending


# ---------------------------------------------------------------------------------------------------------------------
# Ayudas de consulta (completan ``supportops.backends`` sin modificarlo)
# ---------------------------------------------------------------------------------------------------------------------
def tempo_metrics(traceql: str, since: str = "15m", step: str = "15s", instant: bool = False) -> dict[str, Any]:
    """``GET /api/metrics/query_range`` (o ``/api/metrics/query`` si ``instant``): TraceQL metrics, p. ej. ``{ } | rate() by (resource.service.name)``."""
    path = "/api/metrics/query" if instant else "/api/metrics/query_range"
    params: dict[str, Any] = {"q": traceql, "since": since}
    if not instant:
        params["step"] = step
    return backends._get(backends._base("tempo") + path, params, timeout=30.0)


def metrics_series(resp: dict[str, Any]) -> dict[str, list[tuple[float, float]]]:
    """Respuesta de TraceQL metrics -> ``{etiquetas: [(t_seg, valor), ...]}`` (sin muestras vacías)."""
    out: dict[str, list[tuple[float, float]]] = {}
    for s in resp.get("series", []):
        labels = ",".join(f"{l['key']}={next(iter(l['value'].values()))}" for l in s.get("labels", [])) or "total"
        pts = [(int(p["timestampMs"]) / 1000.0, float(p.get("value", 0))) for p in s.get("samples", [])]
        out[labels] = pts
    return out


def prom_range(promql: str, minutes: int = 15, step_s: int = 15) -> dict[str, list[tuple[float, float]]]:
    """``/api/v1/query_range`` de Prometheus -> ``{etiquetas: [(t_seg, valor), ...]}``."""
    now = time.time()
    d = backends._get(backends._base("prometheus") + "/api/v1/query_range",
                      {"query": promql, "start": now - minutes * 60, "end": now, "step": step_s}, timeout=20.0)
    out: dict[str, list[tuple[float, float]]] = {}
    for r in d.get("data", {}).get("result", []):
        key = ",".join(f"{k}={v}" for k, v in sorted(r["metric"].items() if "metric" in r else [])) or "total"
        out[key] = [(float(t), float(v)) for t, v in r["values"] if v not in ("NaN", "+Inf", "-Inf")]
    return out
