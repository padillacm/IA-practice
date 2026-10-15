"""Métricas OpenTelemetry de SupportOps (módulo 09; las reutilizan los módulos 10, 13, 16 y 18).

    from supportops.telemetry import setup_telemetry, OTelInstrumentor
    from supportops.otel_metrics import MetricsInstrumentor, run_live
    tel = setup_telemetry("supportops-agent", metric_interval_s=5)
    instr = CompositeInstrumentor(OTelInstrumentor(tel, emit_metrics=False),   # 1.º: abre el span (de ahí salen los exemplars)
                                  MetricsInstrumentor(tel))                   # 2.º: registra métricas DENTRO del span activo
    agent = SupportAgent(instrumentor=instr)

Qué hay aquí
------------
* ``PriceTable`` / ``ILLUSTRATIVE_PRICES``: tabla de precios (USD por millón de tokens) **configurable e ilustrativa**: NO son
  precios reales de ningún proveedor. Cámbiala con tus tarifas (``PriceTable({...})`` o ``SUPPORTOPS_PRICES_JSON``).
* ``MetricsInstrumentor``: un ``Instrumentor`` que registra las métricas RED + GenAI + coste de SupportOps. Es independiente
  del de trazas (``OTelInstrumentor``), de modo que se compone con ``CompositeInstrumentor``. Los nombres de instrumentos y
  los *bucket boundaries* siguen la spec GenAI (estado *Development*, repo open-telemetry/semantic-conventions-genai) salvo
  las métricas propias (prefijo ``supportops.``).
* ``make_meter_provider``: ``MeterProvider`` con exportador OTLP/HTTP (Collector o Prometheus directo) y/o lector en memoria.
* ``run_live``: reparte tickets en tiempo REAL (las métricas se estampan con el reloj de pared, no con el simulado).
* ``prom_range`` / ``prom_exemplars`` / ``prom_series_count``: clientes mínimos de la API HTTP de Prometheus.
* ``metric_rows``: puntos de un ``InMemoryMetricReader`` como dicts (modo degradado, sin Docker).

Métricas (nombre OTel · tipo · unidad → nombre en Prometheus vía Collector)
---------------------------------------------------------------------------
supportops.agent.requests                     Counter {request}        → supportops_agent_requests_total
supportops.agent.active_runs                  UpDownCounter {run}      → supportops_agent_active_runs
supportops.agent.request.cost                 Histogram USD            → supportops_agent_request_cost_USD_bucket
supportops.llm.cost                           Counter USD              → supportops_llm_cost_USD_total
supportops.llm.context_utilization            Gauge 1                  → supportops_llm_context_utilization_ratio
gen_ai.invoke_agent.duration                  Histogram s              → gen_ai_invoke_agent_duration_seconds_bucket
gen_ai.invoke_agent.inference_calls           Histogram {inference_call}
gen_ai.invoke_agent.tool_calls                Histogram {tool_call}
gen_ai.client.inference.duration              Histogram s              → gen_ai_client_inference_duration_seconds_bucket
gen_ai.client.inference.usage.input_tokens    Counter {token}          → gen_ai_client_inference_usage_input_tokens_total
gen_ai.client.inference.usage.output_tokens   Counter {token}
gen_ai.client.inference.operation.input_tokens  / .output_tokens   Histogram {token}
gen_ai.execute_tool.duration                  Histogram s              → gen_ai_execute_tool_duration_seconds_bucket

Cardinalidad: los atributos son SIEMPRE de conjunto acotado (modelo, estado, intención, tier, herramienta, error.type).
``ticket_id`` / ``customer_id`` NO se usan jamás como atributo de métrica (van en spans y logs).
"""
from __future__ import annotations

import dataclasses
import json
import os
import time
import urllib.parse
import urllib.request
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator, Mapping, Sequence

from .instrument import Instrumentor, LLMCallInfo, RunContext, ToolCallInfo

__all__ = [
    "PriceTable", "ILLUSTRATIVE_PRICES", "MetricsInstrumentor", "make_meter_provider", "run_live", "metric_rows",
    "prom_api", "prom_instant", "prom_raw", "prom_range", "prom_exemplars", "prom_series_count", "MODEL_CONTEXT_WINDOW",
    "SPEC_DURATION_BOUNDARIES", "SPEC_AGENT_DURATION_BOUNDARIES", "SPEC_TOKEN_BOUNDARIES", "SPEC_CALL_COUNT_BOUNDARIES",
    "TUNED_AGENT_DURATION_BOUNDARIES", "TUNED_CHAT_DURATION_BOUNDARIES", "TUNED_TOOL_DURATION_BOUNDARIES",
    "TUNED_INPUT_TOKEN_BOUNDARIES", "TUNED_OUTPUT_TOKEN_BOUNDARIES", "TUNED_COST_BOUNDARIES",
]

try:
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import InMemoryMetricReader, PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
except ImportError as e:  # pragma: no cover
    raise ImportError('supportops.otel_metrics necesita el SDK de OpenTelemetry: pip install -e "agent-observability-course[otel]"') from e

# ---------------------------------------------------------------------------------------------------------------------
# Bucket boundaries
# ---------------------------------------------------------------------------------------------------------------------
# Recomendados por la spec GenAI (ExplicitBucketBoundaries). Factor ×2 (duración) o ×4 (tokens): pensados para cubrir
# MUCHOS sistemas distintos, no para medir bien percentiles de TU agente (módulo 09, sección «buckets»).
SPEC_DURATION_BOUNDARIES = [0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 0.64, 1.28, 2.56, 5.12, 10.24, 20.48, 40.96, 81.92]
SPEC_AGENT_DURATION_BOUNDARIES = [0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4, 12.8, 25.6, 51.2, 102.4, 204.8, 409.6]
SPEC_TOKEN_BOUNDARIES = [1, 4, 16, 64, 256, 1024, 4096, 16384, 65536, 262144, 1048576, 4194304, 16777216, 67108864]
SPEC_CALL_COUNT_BOUNDARIES = [1, 2, 4, 8, 16, 32, 64, 128]

# Ajustados a la distribución medida de SupportOps (mock, semilla 42): más finos donde está la masa y el SLO.
TUNED_AGENT_DURATION_BOUNDARIES = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 7.5, 10, 20, 40]
TUNED_CHAT_DURATION_BOUNDARIES = [0.1, 0.25, 0.5, 0.6, 0.7, 0.8, 0.9, 1, 1.25, 1.5, 2, 3, 5, 10, 20]
TUNED_TOOL_DURATION_BOUNDARIES = [0.01, 0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 1, 2.5, 5, 10]
TUNED_INPUT_TOKEN_BOUNDARIES = [100, 200, 300, 350, 400, 450, 500, 600, 800, 1000, 1500, 2000, 4000, 8000]
TUNED_OUTPUT_TOKEN_BOUNDARIES = [5, 10, 15, 20, 25, 30, 40, 50, 75, 100, 200, 500]
TUNED_COST_BOUNDARIES = [5e-5, 1e-4, 1.5e-4, 2e-4, 2.5e-4, 3e-4, 4e-4, 5e-4, 7.5e-4, 1e-3, 2e-3, 5e-3]

# Ventana de contexto ILUSTRATIVA por modelo (tokens) para el gauge de utilización.
MODEL_CONTEXT_WINDOW = {"mock-small": 16_000, "mock-large": 128_000}


# ---------------------------------------------------------------------------------------------------------------------
# Precios (ilustrativos)
# ---------------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class PriceTable:
    """Tabla de precios USD por millón de tokens ``{modelo: (entrada, salida)}``.

    ⚠️ Los valores por defecto son **ILUSTRATIVOS** (coinciden con los precios simulados del mock): sirven para enseñar
    cómo se deriva coste de tokens, no son tarifas de ningún proveedor. Usa las tuyas (cambian a menudo).
    """
    prices: Mapping[str, tuple[float, float]]
    default: tuple[float, float] = (0.0, 0.0)          # modelo desconocido: coste 0 (y lo notamos en ``unknown_models``)
    note: str = "precios ILUSTRATIVOS, no reales"

    def cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        pin, pout = self.prices.get(model, self.default)
        return (input_tokens * pin + output_tokens * pout) / 1_000_000

    def knows(self, model: str) -> bool:
        return model in self.prices

    @classmethod
    def from_env(cls, var: str = "SUPPORTOPS_PRICES_JSON") -> "PriceTable":
        """``SUPPORTOPS_PRICES_JSON='{"mi-modelo": [0.5, 2.0]}'`` (USD por millón de tokens, entrada y salida)."""
        raw = os.environ.get(var)
        if not raw:
            return ILLUSTRATIVE_PRICES
        return cls({k: (float(v[0]), float(v[1])) for k, v in json.loads(raw).items()}, note=f"precios de {var}")


ILLUSTRATIVE_PRICES = PriceTable({"mock-small": (0.25, 1.25), "mock-large": (3.00, 15.00)})


# ---------------------------------------------------------------------------------------------------------------------
# MeterProvider
# ---------------------------------------------------------------------------------------------------------------------
def make_meter_provider(
    service_name: str = "supportops-agent",
    *,
    otlp_endpoint: str | None = "http://localhost:4318/v1/metrics",
    memory: bool = True,
    interval_s: float = 5.0,
    views: Sequence[Any] = (),
    resource_attrs: Mapping[str, Any] | None = None,
    instance_id: str | None = None,
    exporter_kwargs: Mapping[str, Any] | None = None,
) -> tuple[MeterProvider, InMemoryMetricReader | None]:
    """``MeterProvider`` con lector periódico OTLP/HTTP (si ``otlp_endpoint``) y/o ``InMemoryMetricReader``.

    ``otlp_endpoint`` es la URL COMPLETA de metrics: ``http://localhost:4318/v1/metrics`` (Collector) o
    ``http://localhost:9090/api/v1/otlp/v1/metrics`` (OTLP directo a Prometheus).
    """
    attrs = {"service.name": service_name, "service.version": "0.1.0",
             "service.instance.id": instance_id or f"{service_name}-lab"}
    attrs.update(resource_attrs or {})
    readers: list[Any] = []
    mem = None
    if otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        readers.append(PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=otlp_endpoint, **dict(exporter_kwargs or {})),
                                                     export_interval_millis=int(interval_s * 1000)))
    if memory:
        mem = InMemoryMetricReader()
        readers.append(mem)
    return MeterProvider(resource=Resource.create(attrs), metric_readers=readers, views=list(views)), mem


# ---------------------------------------------------------------------------------------------------------------------
# MetricsInstrumentor
# ---------------------------------------------------------------------------------------------------------------------
def _err_type(exc: BaseException) -> str:
    return str(getattr(exc, "error_type", None) or type(exc).__qualname__)


class MetricsInstrumentor(Instrumentor):
    """Registra métricas RED + GenAI + coste. Componlo DESPUÉS del instrumentor de trazas para que haya un span activo
    cuando se registra cada medición (así el SDK adjunta exemplars con ``trace_id``/``span_id``).

    Parámetros
    ----------
    provider : ``MeterProvider`` o cualquier objeto con ``.meter_provider`` (p. ej. ``TelemetryHandle``).
    prices : ``PriceTable`` para derivar el coste. ``boundaries``: ``"tuned"`` (por defecto) o ``"spec"``.
    include_tier : añade ``supportops.customer.tier`` (2 valores) a las métricas de petición. Pon ``False`` para reducir series.
    extra_request_attrs : atributos extra POR PETICIÓN (¡cuidado con la cardinalidad!): callable ``ctx -> dict``.
    """

    def __init__(self, provider: Any = None, *, prices: PriceTable = ILLUSTRATIVE_PRICES, boundaries: str = "tuned",
                 include_tier: bool = True, extra_request_attrs: Any = None, scope: str = "supportops.metrics"):
        mp = getattr(provider, "meter_provider", provider)
        if mp is None:
            from opentelemetry import metrics
            mp = metrics.get_meter_provider()
        self.prices, self.include_tier, self.extra_request_attrs = prices, include_tier, extra_request_attrs
        tuned = boundaries == "tuned"
        b_agent = TUNED_AGENT_DURATION_BOUNDARIES if tuned else SPEC_AGENT_DURATION_BOUNDARIES
        b_chat = TUNED_CHAT_DURATION_BOUNDARIES if tuned else SPEC_DURATION_BOUNDARIES
        b_tool = TUNED_TOOL_DURATION_BOUNDARIES if tuned else SPEC_DURATION_BOUNDARIES
        b_in = TUNED_INPUT_TOKEN_BOUNDARIES if tuned else SPEC_TOKEN_BOUNDARIES
        b_out = TUNED_OUTPUT_TOKEN_BOUNDARIES if tuned else SPEC_TOKEN_BOUNDARIES
        m = mp.get_meter(scope, "0.1.0")
        self.requests = m.create_counter("supportops.agent.requests", unit="{request}",
                                         description="Peticiones (tickets) atendidas por el agente, por estado final")
        self.active = m.create_up_down_counter("supportops.agent.active_runs", unit="{run}",
                                               description="Ejecuciones del agente en curso")
        self.req_cost = m.create_histogram("supportops.agent.request.cost", unit="USD", description="Coste por petición (precios ilustrativos)",
                                           explicit_bucket_boundaries_advisory=TUNED_COST_BOUNDARIES)
        self.llm_cost = m.create_counter("supportops.llm.cost", unit="USD", description="Coste acumulado de inferencia (precios ilustrativos)")
        self.ctx_util = m.create_gauge("supportops.llm.context_utilization", unit="1",
                                       description="Fracción de la ventana de contexto usada por la última llamada")
        self.agent_dur = m.create_histogram("gen_ai.invoke_agent.duration", unit="s", description="Duración de una invocación del agente",
                                            explicit_bucket_boundaries_advisory=b_agent)
        self.inf_calls = m.create_histogram("gen_ai.invoke_agent.inference_calls", unit="{inference_call}",
                                            description="Llamadas al LLM por invocación", explicit_bucket_boundaries_advisory=SPEC_CALL_COUNT_BOUNDARIES)
        self.tool_calls = m.create_histogram("gen_ai.invoke_agent.tool_calls", unit="{tool_call}",
                                             description="Llamadas a herramientas por invocación", explicit_bucket_boundaries_advisory=SPEC_CALL_COUNT_BOUNDARIES)
        self.chat_dur = m.create_histogram("gen_ai.client.inference.duration", unit="s", description="Duración de la inferencia GenAI",
                                           explicit_bucket_boundaries_advisory=b_chat)
        self.in_tok = m.create_counter("gen_ai.client.inference.usage.input_tokens", unit="{token}", description="Tokens de entrada usados")
        self.out_tok = m.create_counter("gen_ai.client.inference.usage.output_tokens", unit="{token}", description="Tokens de salida usados")
        self.op_in = m.create_histogram("gen_ai.client.inference.operation.input_tokens", unit="{token}",
                                        description="Tokens de entrada por operación", explicit_bucket_boundaries_advisory=b_in)
        self.op_out = m.create_histogram("gen_ai.client.inference.operation.output_tokens", unit="{token}",
                                         description="Tokens de salida por operación", explicit_bucket_boundaries_advisory=b_out)
        self.tool_dur = m.create_histogram("gen_ai.execute_tool.duration", unit="s", description="Duración de una herramienta",
                                           explicit_bucket_boundaries_advisory=b_tool)
        self.unknown_models: set[str] = set()

    # ------------------------------------------------------------------------------------------------ hooks
    def _run_attrs(self, ctx: RunContext) -> dict[str, Any]:
        a: dict[str, Any] = {"gen_ai.agent.name": ctx.agent_name}
        if self.include_tier:
            a["supportops.customer.tier"] = ctx.ticket.tier
        if self.extra_request_attrs:
            a.update(self.extra_request_attrs(ctx))
        return a

    @contextmanager
    def agent_run(self, ctx: RunContext) -> Iterator[None]:
        base = self._run_attrs(ctx)
        self.active.add(1, {"gen_ai.agent.name": ctx.agent_name})
        try:
            yield
        finally:
            self.active.add(-1, {"gen_ai.agent.name": ctx.agent_name})
            r = ctx.result
            if r is not None:
                failed = r.status in ("error", "max_steps")
                req_attrs = {**base, "supportops.status": r.status, "supportops.intent": r.intent_pred or "unknown"}
                self.requests.add(1, req_attrs)
                dur_attrs = {**base, "gen_ai.request.model": r.model}
                if failed:
                    dur_attrs["error.type"] = r.error_type or r.status
                self.agent_dur.record(r.latency_s, dur_attrs)
                self.inf_calls.record(r.n_llm_calls, base)
                self.tool_calls.record(r.n_tool_calls, base)
                self.req_cost.record(self.prices.cost(r.model, r.input_tokens, r.output_tokens), {"gen_ai.request.model": r.model})

    @contextmanager
    def llm_call(self, ctx: RunContext, info: LLMCallInfo) -> Iterator[None]:
        t0 = ctx.clock.now_s()
        err: str | None = None
        try:
            yield
        except BaseException as e:
            err = _err_type(e)
            raise
        finally:
            r = info.response
            battrs: dict[str, Any] = {"gen_ai.operation.name": "chat", "gen_ai.provider.name": info.provider,
                                      "gen_ai.request.model": info.model}
            hattrs = dict(battrs)
            if err:
                hattrs["error.type"] = err
            self.chat_dur.record(max(ctx.clock.now_s() - t0, 0.0), hattrs)
            tok = {**battrs, "gen_ai.token.modality": "text" if r is not None else "unknown"}
            tin = r.usage.input_tokens if r is not None else 0
            tout = r.usage.output_tokens if r is not None else 0
            self.in_tok.add(tin, tok)
            self.out_tok.add(tout, tok)
            if r is not None:
                self.op_in.record(tin, battrs)
                self.op_out.record(tout, battrs)
                if not self.prices.knows(info.model):
                    self.unknown_models.add(info.model)
                self.llm_cost.add(self.prices.cost(info.model, tin, tout), {"gen_ai.request.model": info.model})
                win = MODEL_CONTEXT_WINDOW.get(info.model)
                if win:
                    self.ctx_util.set(tin / win, {"gen_ai.request.model": info.model})

    @contextmanager
    def tool_call(self, ctx: RunContext, info: ToolCallInfo) -> Iterator[None]:
        t0 = ctx.clock.now_s()
        err: str | None = None
        try:
            yield
        except BaseException as e:
            err = _err_type(e)
            raise
        finally:
            a: dict[str, Any] = {"gen_ai.tool.name": info.call.name, "gen_ai.agent.name": ctx.agent_name}
            if err:
                a["error.type"] = err
            self.tool_dur.record(max(ctx.clock.now_s() - t0, 0.0), a)


# ---------------------------------------------------------------------------------------------------------------------
# Tráfico en tiempo real
# ---------------------------------------------------------------------------------------------------------------------
def run_live(agent: Any, tickets: Sequence[Any], seconds: float, *, progress_every: float = 0.0) -> list[Any]:
    """Ejecuta ``tickets`` repartidos en ``seconds`` segundos de tiempo REAL (respeta la forma de la llegada).

    Las métricas OTel se estampan con el reloj de pared al exportar, así que para ver series temporales en Prometheus
    hay que dejar pasar tiempo real. Cada ticket se «reancla» a ``time.time()`` (``created_at``) para que sus spans caigan
    en la ventana actual de Tempo/Loki. Los ``Incident`` de ``generate_tickets`` están en segundos relativos al inicio.
    """
    if not tickets:
        return []
    base = tickets[0].created_at
    span = max(tickets[-1].created_at - base, 1e-9)
    t_start = time.time()
    out = []
    last_msg = t_start
    for t in tickets:
        target = t_start + (t.created_at - base) / span * seconds
        wait = target - time.time()
        if wait > 0:
            time.sleep(wait)
        out.append(agent.run(dataclasses.replace(t, created_at=round(time.time(), 3))))
        if progress_every and time.time() - last_msg >= progress_every:
            print(f"  … {len(out)}/{len(tickets)} tickets ({time.time() - t_start:.0f}s)")
            last_msg = time.time()
    return out


# ---------------------------------------------------------------------------------------------------------------------
# Clientes mínimos de la API HTTP de Prometheus (solo urllib)
# ---------------------------------------------------------------------------------------------------------------------
PROM_URL = os.environ.get("PROMETHEUS_URL", "http://localhost:9090")


def _prom(path: str, params: Mapping[str, Any], timeout: float = 15.0) -> dict[str, Any]:
    url = f"{PROM_URL}{path}?" + urllib.parse.urlencode(params)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url, timeout=timeout) as r:
        return json.loads(r.read())


def prom_api(path: str, **params: Any) -> dict[str, Any]:
    """GET genérico a la API de Prometheus, p. ej. ``prom_api('/api/v1/label/__name__/values')`` o ``prom_api('/api/v1/status/tsdb')``."""
    return _prom(path, params)


def prom_instant(promql: str, at: float | None = None) -> list[dict[str, Any]]:
    """Consulta instantánea: lista ``[{metric: {...}, value: float}]`` (vacía si no hay datos). Lanza si PromQL es inválido."""
    d = _prom("/api/v1/query", {"query": promql, **({"time": at} if at else {})})
    if d.get("status") != "success":
        raise ValueError(d.get("error", d))
    out = []
    for r in d["data"]["result"]:
        v = r.get("value")
        out.append({"metric": r["metric"], "value": float(v[1]) if v else None, "histogram": r.get("histogram")})
    return out


def prom_raw(selector_with_range: str, at: float | None = None) -> list[dict[str, Any]]:
    """Muestras CRUDAS de un selector de rango (``metrica{...}[2m]``): ``[{metric, samples: [(t, v)]}]``. Sirve para
    comprobar a mano lo que hacen ``rate`` o ``histogram_quantile`` sobre las mismas muestras."""
    d = _prom("/api/v1/query", {"query": selector_with_range, **({"time": at} if at else {})})
    return [{"metric": r["metric"], "samples": [(float(t), float(v)) for t, v in r["values"]]} for r in d["data"]["result"]]


def prom_range(promql: str, minutes: float = 10, step_s: float = 15, end: float | None = None) -> list[dict[str, Any]]:
    """``query_range`` → lista de series ``{metric, t: [epoch s], v: [float]}`` (NaN se descartan)."""
    end = end or time.time()
    d = _prom("/api/v1/query_range", {"query": promql, "start": end - minutes * 60, "end": end, "step": step_s})
    if d.get("status") != "success":
        raise ValueError(d.get("error", d))
    out = []
    for r in d["data"]["result"]:
        pts = [(float(t), float(v)) for t, v in r["values"] if v not in ("NaN", "+Inf", "-Inf")]
        out.append({"metric": r["metric"], "t": [p[0] for p in pts], "v": [p[1] for p in pts]})
    return out


def prom_exemplars(selector: str, minutes: float = 10) -> list[dict[str, Any]]:
    """Exemplars almacenados para un selector (p. ej. ``gen_ai_invoke_agent_duration_seconds_bucket``).
    Devuelve ``[{series: {...}, trace_id, span_id, value, ts}]``."""
    end = time.time()
    d = _prom("/api/v1/query_exemplars", {"query": selector, "start": end - minutes * 60, "end": end})
    out = []
    for s in d.get("data", []):
        for e in s["exemplars"]:
            out.append({"series": s["seriesLabels"], "trace_id": e["labels"].get("trace_id"), "span_id": e["labels"].get("span_id"),
                        "value": float(e["value"]), "ts": float(e["timestamp"])})
    return out


def prom_series_count(match: str | None = None) -> int:
    """Número de series de la *head* (``prometheus_tsdb_head_series``) o, con ``match``, las que casan con el selector."""
    if match is None:
        r = prom_instant("prometheus_tsdb_head_series")
        return int(r[0]["value"]) if r else 0
    end = time.time()
    d = _prom("/api/v1/series", {"match[]": match, "start": end - 3600, "end": end})
    return len(d.get("data", []))


# ---------------------------------------------------------------------------------------------------------------------
# Modo degradado: puntos del lector en memoria como dicts
# ---------------------------------------------------------------------------------------------------------------------
def metric_rows(reader: InMemoryMetricReader) -> list[dict[str, Any]]:
    """Aplana ``reader.get_metrics_data()`` en filas: ``name, unit, kind, attributes, value | count,sum,bounds,buckets, exemplars``."""
    data = reader.get_metrics_data()
    rows: list[dict[str, Any]] = []
    for rm in (data.resource_metrics if data else []):
        for sm in rm.scope_metrics:
            for m in sm.metrics:
                kind = type(m.data).__name__.lower()          # sum | gauge | histogram | exponentialhistogram
                for p in m.data.data_points:
                    row: dict[str, Any] = {"name": m.name, "unit": m.unit, "kind": kind, "attributes": dict(p.attributes or {}),
                                           "monotonic": getattr(m.data, "is_monotonic", None)}
                    if hasattr(p, "bucket_counts"):
                        row.update(count=p.count, sum=p.sum, bounds=list(p.explicit_bounds), buckets=list(p.bucket_counts))
                    elif hasattr(p, "scale"):          # histograma exponencial
                        row.update(count=p.count, sum=p.sum, scale=p.scale, zero_count=p.zero_count,
                                   positive={"offset": p.positive.offset, "counts": list(p.positive.bucket_counts)})
                    else:
                        row["value"] = p.value
                    ex = getattr(p, "exemplars", None) or []
                    row["exemplars"] = [{"trace_id": format(e.trace_id, "032x") if e.trace_id else None,
                                         "span_id": format(e.span_id, "016x") if e.span_id else None, "value": e.value} for e in ex]
                    rows.append(row)
    return rows
