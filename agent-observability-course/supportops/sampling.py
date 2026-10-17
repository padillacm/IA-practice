"""Módulo 18 · escala, muestreo y coste del propio stack de observabilidad.

Todo en librería estándar (+ ``opentelemetry-proto`` solo para ``spans_to_otlp`` y el laboratorio con Docker):

* ``build_corpus``: un lote determinista de trazas de SupportOps (mock, semilla fija) con fallos, latencias y costes, y su tamaño OTLP real.
* Muestreo **head** (``head_keep``, por ``trace_id``) y **tail** (``TailSampler`` + políticas con los MISMOS nombres y claves que el
  ``tail_sampling`` del Collector contrib 0.162): simulador con memoria acotada (``num_traces``), ``decision_wait`` y descartes tempranos.
* Sesgo de las métricas derivadas del muestreo y su corrección por probabilidad de inclusión (``estimate_metrics``).
* Cardinalidad (``series_estimate``, ``count_series``) y tormentas de cardinalidad.
* Modelo de coste del propio stack (``StackCostModel``) y de retención por niveles (``retention_cost``).
* Generadores de configuración validables: ``collector_config`` (tail sampling + span metrics), ``loki_limits_yaml``, ``tempo_overrides_yaml``.
* ``SamplingLab``: Collector contrib en un contenedor efímero para comprobar contra el binario real lo que el simulador predice.

Los precios son ILUSTRATIVOS y configurables. Las claves de configuración están verificadas con el README del procesador
(``opentelemetry-collector-contrib`` v0.162.0, ``processor/tailsamplingprocessor``, estabilidad *beta* para trazas).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import pathlib
import re
import shutil
import statistics
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Sequence

SLOW_S = 5.0            # umbral de latencia del SLO del módulo 16
COSTLY_USD = 0.0005     # umbral de coste del SLO del módulo 16
COLLECTOR_IMAGE = os.environ.get("OTELCOL_IMAGE", "otel/opentelemetry-collector-contrib:0.162.0")


# =====================================================================================================================
# 1. Spans -> OTLP (tamaño real en el cable) y corpus de trazas
# =====================================================================================================================
_KIND = {"UNSPECIFIED": 0, "INTERNAL": 1, "SERVER": 2, "CLIENT": 3, "PRODUCER": 4, "CONSUMER": 5}
_STATUS = {"UNSET": 0, "OK": 1, "ERROR": 2}


def _anyvalue(v: Any):
    from opentelemetry.proto.common.v1.common_pb2 import AnyValue
    if isinstance(v, bool):
        return AnyValue(bool_value=v)
    if isinstance(v, int):
        return AnyValue(int_value=v)
    if isinstance(v, float):
        return AnyValue(double_value=v)
    return AnyValue(string_value=str(v))


def spans_to_otlp(spans: Sequence[Mapping[str, Any]]):
    """Convierte spans con el esquema ``SPAN_SCHEMA`` (``RecordingInstrumentor``) en un ``ExportTraceServiceRequest`` (protobuf)."""
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
    from opentelemetry.proto.common.v1.common_pb2 import KeyValue
    req = ExportTraceServiceRequest()
    by_res: dict[str, Any] = {}
    for s in spans:
        key = json.dumps(s["resource"], sort_keys=True)
        if key not in by_res:
            rs = req.resource_spans.add()
            for k, v in s["resource"].items():
                rs.resource.attributes.append(KeyValue(key=k, value=_anyvalue(v)))
            sc = rs.scope_spans.add()
            sc.scope.name = s.get("scope", "supportops")
            by_res[key] = sc
        sp = by_res[key].spans.add()
        sp.trace_id = bytes.fromhex(s["trace_id"])
        sp.span_id = bytes.fromhex(s["span_id"])
        if s.get("parent_span_id"):
            sp.parent_span_id = bytes.fromhex(s["parent_span_id"])
        sp.name = s["name"]
        sp.kind = _KIND.get(s.get("kind", "INTERNAL"), 1)
        sp.start_time_unix_nano = int(s["start_unix_nano"])
        sp.end_time_unix_nano = int(s["end_unix_nano"] or s["start_unix_nano"])
        for k, v in s.get("attributes", {}).items():
            sp.attributes.append(KeyValue(key=k, value=_anyvalue(v)))
        sp.status.code = _STATUS.get(s.get("status", "UNSET"), 0)
        if s.get("status_message"):
            sp.status.message = s["status_message"]
        for ev in s.get("events", []):
            e = sp.events.add()
            e.name = ev["name"]
            e.time_unix_nano = int(ev.get("time_unix_nano", s["end_unix_nano"] or 0))
            for k, v in ev.get("attributes", {}).items():
                e.attributes.append(KeyValue(key=k, value=_anyvalue(v)))
    return req


@dataclass
class Trace:
    trace_id: str
    spans: list[dict[str, Any]]
    ticket_id: str
    start_s: float
    end_s: float
    status: str                      # estado del agente: ok | degraded | escalated | error | max_steps
    error: bool                      # span raíz con status ERROR
    cost_usd: float
    n_llm: int
    n_tool: int
    bytes: int = 0                   # tamaño OTLP/protobuf SIN comprimir de TODOS sus spans
    truth: dict[str, Any] = field(default_factory=dict)       # verdad de laboratorio: fallos inyectados, alucinación, PII

    @property
    def duration_s(self) -> float:
        return self.end_s - self.start_s

    @property
    def n_spans(self) -> int:
        return len(self.spans)

    @property
    def slow(self) -> bool:
        return self.duration_s >= SLOW_S

    @property
    def costly(self) -> bool:
        return self.cost_usd > COSTLY_USD

    @property
    def has_error_span(self) -> bool:
        """Algún span con status ERROR (un fallo recuperado por un reintento o un fallback también cuenta: es lo que ve la política ``status_code``)."""
        return any(s["status"] == "ERROR" for s in self.spans)

    @property
    def interesting(self) -> bool:
        """Lo que un ingeniero querría ver siempre: con algún span en error, lentas o caras (todo observable en la telemetría)."""
        return self.has_error_span or self.slow or self.costly

    @property
    def root(self) -> dict[str, Any]:
        return next(s for s in self.spans if not s.get("parent_span_id"))


@dataclass
class Corpus:
    traces: list[Trace]
    duration_s: float
    seed: int

    def __len__(self) -> int:
        return len(self.traces)

    @property
    def total_spans(self) -> int:
        return sum(t.n_spans for t in self.traces)

    @property
    def total_bytes(self) -> int:
        return sum(t.bytes for t in self.traces)

    def by_id(self) -> dict[str, Trace]:
        return {t.trace_id: t for t in self.traces}

    def summary(self) -> dict[str, float]:
        n = len(self.traces)
        return {"traces": n, "spans": self.total_spans, "spans_per_trace": self.total_spans / n, "bytes_per_span": self.total_bytes / self.total_spans,
                "bytes_per_trace": self.total_bytes / n, "error_rate": sum(t.error for t in self.traces) / n,
                "error_span_rate": sum(t.has_error_span for t in self.traces) / n, "slow_rate": sum(t.slow for t in self.traces) / n, "costly_rate": sum(t.costly for t in self.traces) / n,
                "interesting_rate": sum(t.interesting for t in self.traces) / n}


def build_corpus(n: int = 1500, seed: int = 42, duration_s: float = 900.0, fault_rates: Mapping[str, float] | None = None, incidents: Sequence[Any] = (),
                 start_s: float | str | None = None, measure_bytes: bool = True) -> Corpus:
    """Ejecuta SupportOps (mock, semilla fija) sobre ``n`` tickets repartidos en ``duration_s`` s y devuelve las trazas con su tamaño OTLP.
    Determinista: mismos tickets, mismos fallos, mismos ids. ``incidents``: ventanas de fallo elevado (``supportops.Incident``)."""
    from .agent import SupportAgent
    from .clock import SIM_EPOCH_S
    from .recording import RecordingInstrumentor
    from .traffic import DEFAULT_FAULT_RATES, generate_tickets
    rates = DEFAULT_FAULT_RATES if fault_rates is None else fault_rates
    tickets = generate_tickets(n, seed=seed, duration_s=duration_s, fault_rates=rates, incidents=incidents, start_s=SIM_EPOCH_S if start_s is None else start_s)
    rec = RecordingInstrumentor()
    agent = SupportAgent(instrumentor=rec)
    traces: list[Trace] = []
    for tk in tickets:
        rec.reset()
        res = agent.run(tk)
        spans = [dict(s) for s in rec.spans]
        root = next(s for s in spans if not s.get("parent_span_id"))
        tr = Trace(root["trace_id"], spans, tk.ticket_id, min(s["start_unix_nano"] for s in spans) / 1e9, max(s["end_unix_nano"] for s in spans) / 1e9,
                   res.status, root["status"] == "ERROR", float(res.cost_usd), res.n_llm_calls, res.n_tool_calls,
                   truth={"faults": list(res.injected_faults), "grounded": res.grounded, "pii_leaked": res.pii_leaked})
        if measure_bytes:
            tr.bytes = spans_to_otlp(spans).ByteSize()
        traces.append(tr)
    traces.sort(key=lambda t: t.end_s)
    return Corpus(traces, duration_s, seed)


# =====================================================================================================================
# 2. Muestreo head (por trace_id)
# =====================================================================================================================
def trace_randomness(trace_id: str) -> int:
    """56 bits menos significativos del trace_id (la aleatoriedad que usa el muestreo consistente de OpenTelemetry)."""
    return int(trace_id[-14:], 16)


def head_keep(trace_id: str, ratio: float) -> bool:
    """Decisión *head* determinista por ``trace_id`` (estilo ``TraceIdRatioBased``): todos los servicios que ven el mismo trace_id deciden igual."""
    return trace_randomness(trace_id) < ratio * (1 << 56)


def head_sample(traces: Iterable[Trace], ratio: float) -> list[Trace]:
    return [t for t in traces if head_keep(t.trace_id, ratio)]


# =====================================================================================================================
# 3. Muestreo tail: políticas con la semántica y las claves del procesador tail_sampling
# =====================================================================================================================
class Policy:
    """Una política devuelve 'sampled' | 'not_sampled' | 'dropped'. ``to_config()`` da el dict que va en ``tail_sampling.policies``."""
    name: str = "policy"
    type: str = ""

    def decide(self, t: Trace, ctx: "TailContext") -> str:
        raise NotImplementedError

    def body(self) -> dict[str, Any]:
        return {}

    def to_config(self) -> dict[str, Any]:
        out: dict[str, Any] = {"name": self.name, "type": self.type}
        b = self.body()
        if b:
            out[self.type] = b
        return out


@dataclass
class TailContext:
    salt: str = ""
    rate: dict[str, float] = field(default_factory=dict)      # estado de cubos de tokens por política


@dataclass
class AlwaysSample(Policy):
    name: str = "always"
    type: str = "always_sample"

    def decide(self, t, ctx):
        return "sampled"


@dataclass
class Latency(Policy):
    threshold_ms: float = 5000.0
    upper_threshold_ms: float | None = None
    name: str = "latency"
    type: str = "latency"

    def decide(self, t, ctx):
        ms = t.duration_s * 1000
        return "sampled" if ms >= self.threshold_ms and (self.upper_threshold_ms is None or ms <= self.upper_threshold_ms) else "not_sampled"

    def body(self):
        b: dict[str, Any] = {"threshold_ms": int(self.threshold_ms)}
        if self.upper_threshold_ms is not None:
            b["upper_threshold_ms"] = int(self.upper_threshold_ms)
        return b


@dataclass
class StatusCode(Policy):
    status_codes: tuple[str, ...] = ("ERROR",)
    name: str = "errors"
    type: str = "status_code"

    def decide(self, t, ctx):
        return "sampled" if any(s["status"] in self.status_codes for s in t.spans) else "not_sampled"

    def body(self):
        return {"status_codes": list(self.status_codes)}


@dataclass
class NumericAttribute(Policy):
    """``numeric_attribute``. ⚠️ En el Collector 0.162 ``min_value``/``max_value`` son **int64** (``config.go``): un decimal se trunca y, medido con
    0.162.0, un atributo *double* con ``max_value`` sin fijar hace caer el procesador (SIGSEGV en ``EvaluateWithThreshold``). Para costes en USD usa
    ``AttrCompare`` (OTTL) o un atributo entero (micro-USD)."""
    key: str = "supportops.cost_usd"
    min_value: float | None = None
    max_value: float | None = None
    name: str = "numeric"
    type: str = "numeric_attribute"

    def decide(self, t, ctx):
        for s in t.spans:
            v = s.get("attributes", {}).get(self.key)
            if isinstance(v, (int, float)) and not isinstance(v, bool) and (self.min_value is None or v >= self.min_value) and (self.max_value is None or v <= self.max_value):
                return "sampled"
        return "not_sampled"

    def body(self):
        for v in (self.min_value, self.max_value):
            if v is not None and int(v) != v:
                raise ValueError("numeric_attribute usa int64 en el Collector: usa un atributo entero o AttrCompare (OTTL)")
        b: dict[str, Any] = {"key": self.key}
        if self.min_value is not None:
            b["min_value"] = int(self.min_value)
        if self.max_value is not None:
            b["max_value"] = int(self.max_value)
        return b


@dataclass
class AttrCompare(Policy):
    """Comparación de un atributo de span con ``ottl_condition`` (admite decimales): ``attributes["clave"] > valor``. Es lo que sustituye a
    ``numeric_attribute`` para costes fraccionarios."""
    key: str = "supportops.cost_usd"
    op: str = ">"
    value: float = 0.0005
    name: str = "attr_compare"
    type: str = "ottl_condition"

    def decide(self, t, ctx):
        import operator
        fn = {">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le, "==": operator.eq, "!=": operator.ne}[self.op]
        for sp in t.spans:
            v = sp.get("attributes", {}).get(self.key)
            if isinstance(v, (int, float)) and not isinstance(v, bool) and fn(v, self.value):
                return "sampled"
        return "not_sampled"

    def body(self):
        return {"error_mode": "ignore", "span": [f'attributes["{self.key}"] {self.op} {self.value}']}


@dataclass
class StringAttribute(Policy):
    key: str = "supportops.status"
    values: tuple[str, ...] = ()
    enabled_regex_matching: bool = False
    invert_match: bool = False
    name: str = "string"
    type: str = "string_attribute"

    def decide(self, t, ctx):
        hit = False
        for s in t.spans:
            v = s.get("attributes", {}).get(self.key)
            if v is None:
                continue
            if self.enabled_regex_matching:
                hit = any(re.fullmatch(p, str(v)) for p in self.values)
            else:
                hit = str(v) in self.values
            if hit:
                break
        return "sampled" if hit != self.invert_match else "not_sampled"

    def body(self):
        b: dict[str, Any] = {"key": self.key, "values": list(self.values)}
        if self.enabled_regex_matching:
            b["enabled_regex_matching"] = True
        if self.invert_match:
            b["invert_match"] = True
        return b


@dataclass
class Probabilistic(Policy):
    sampling_percentage: float = 10.0
    hash_salt: str = ""
    name: str = "baseline"
    type: str = "probabilistic"

    def decide(self, t, ctx):
        h = int.from_bytes(hashlib.sha256((self.hash_salt + t.trace_id).encode()).digest()[:8], "big") / 2**64
        return "sampled" if h < self.sampling_percentage / 100.0 else "not_sampled"

    def body(self):
        b: dict[str, Any] = {"sampling_percentage": self.sampling_percentage}
        if self.hash_salt:
            b["hash_salt"] = self.hash_salt
        return b


@dataclass
class SpanCount(Policy):
    min_spans: int = 1
    max_spans: int | None = None
    name: str = "span_count"
    type: str = "span_count"

    def decide(self, t, ctx):
        return "sampled" if t.n_spans >= self.min_spans and (self.max_spans is None or t.n_spans <= self.max_spans) else "not_sampled"

    def body(self):
        b: dict[str, Any] = {"min_spans": self.min_spans}
        if self.max_spans is not None:
            b["max_spans"] = self.max_spans
        return b


@dataclass
class RateLimiting(Policy):
    """Cubo de tokens en SPANS por segundo (``rate_limiting``). El reloj de la simulación es el de decisión del trazo."""
    spans_per_second: int = 100
    burst_capacity: int | None = None
    name: str = "rate"
    type: str = "rate_limiting"

    def decide(self, t, ctx):
        cap = self.burst_capacity or 2 * self.spans_per_second
        now = ctx.rate.get(f"{self.name}:now", t.end_s)
        tokens = ctx.rate.get(f"{self.name}:tokens", float(cap))
        last = ctx.rate.get(f"{self.name}:last", t.end_s)
        tokens = min(cap, tokens + max(0.0, t.end_s - last) * self.spans_per_second)
        ctx.rate[f"{self.name}:last"] = max(last, t.end_s)
        if tokens >= t.n_spans:
            ctx.rate[f"{self.name}:tokens"] = tokens - t.n_spans
            return "sampled"
        ctx.rate[f"{self.name}:tokens"] = tokens
        return "not_sampled"

    def body(self):
        b: dict[str, Any] = {"spans_per_second": self.spans_per_second}
        if self.burst_capacity:
            b["burst_capacity"] = self.burst_capacity
        return b


@dataclass
class And(Policy):
    subs: tuple[Policy, ...] = ()
    name: str = "and"
    type: str = "and"

    def decide(self, t, ctx):
        return "sampled" if all(p.decide(t, ctx) == "sampled" for p in self.subs) else "not_sampled"

    def body(self):
        return {"and_sub_policy": [p.to_config() for p in self.subs]}


@dataclass
class Drop(Policy):
    """Descarta si TODAS las subpolíticas coinciden (``drop``); gana sobre cualquier ``sampled``."""
    subs: tuple[Policy, ...] = ()
    name: str = "drop"
    type: str = "drop"

    def decide(self, t, ctx):
        return "dropped" if all(p.decide(t, ctx) == "sampled" for p in self.subs) else "not_sampled"

    def body(self):
        return {"drop_sub_policy": [p.to_config() for p in self.subs]}


def final_decision(decisions: Sequence[str]) -> bool:
    """Flujo de decisión del procesador: si alguna política dice *dropped* → no; si alguna *sampled* → sí; en otro caso no."""
    if "dropped" in decisions:
        return False
    return "sampled" in decisions


@dataclass
class TailResult:
    kept: list[Trace]
    dropped_too_early: list[Trace]
    by_policy: Counter
    peak_traces: int
    peak_bytes: int
    n_in: int

    @property
    def kept_ratio(self) -> float:
        return len(self.kept) / max(1, self.n_in)


class TailSampler:
    """Simulador del procesador ``tail_sampling``: agrupa por trace_id, espera ``decision_wait_s`` desde el primer span, evalúa las políticas y
    mantiene como máximo ``num_traces`` trazas en memoria (circular: al llegar la N+1 se pierde la más antigua SIN decisión → ``dropped_too_early``)."""

    def __init__(self, policies: Sequence[Policy], decision_wait_s: float = 30.0, num_traces: int = 50_000, salt: str = ""):
        self.policies, self.decision_wait_s, self.num_traces, self.salt = list(policies), decision_wait_s, num_traces, salt

    def run(self, traces: Iterable[Trace]) -> TailResult:
        ts = sorted(traces, key=lambda t: t.start_s)
        ctx = TailContext(salt=self.salt)
        active: list[Trace] = []          # en orden de llegada
        lost: list[Trace] = []
        kept: list[Trace] = []
        by_policy: Counter = Counter()
        peak_n = peak_b = 0
        cur_b = 0

        def finish(until: float) -> None:
            nonlocal cur_b
            while active and active[0].start_s + self.decision_wait_s <= until:
                tr = active.pop(0)
                cur_b -= tr.bytes
                ds = [p.decide(tr, ctx) for p in self.policies]
                if final_decision(ds):
                    kept.append(tr)
                for p, d in zip(self.policies, ds):
                    if d == "sampled":
                        by_policy[p.name] += 1

        for tr in ts:
            finish(tr.start_s)
            active.append(tr)
            cur_b += tr.bytes
            if len(active) > self.num_traces:
                old = active.pop(0)
                cur_b -= old.bytes
                lost.append(old)
            peak_n, peak_b = max(peak_n, len(active)), max(peak_b, cur_b)
        finish(float("inf"))
        return TailResult(kept, lost, by_policy, peak_n, peak_b, len(ts))


def rescale_rate(traces: Sequence[Trace], factor: float) -> list[Trace]:
    """Comprime la línea de tiempo ×``factor`` (misma cantidad de trazas, ``factor`` veces más tráfico) CONSERVANDO la duración de cada traza."""
    import dataclasses
    t0 = min(t.start_s for t in traces)
    out = []
    for t in traces:
        ns = t0 + (t.start_s - t0) / factor
        out.append(dataclasses.replace(t, start_s=ns, end_s=ns + t.duration_s))
    return out


def tail_policy_config(policies: Sequence[Policy]) -> list[dict[str, Any]]:
    return [p.to_config() for p in policies]


# =====================================================================================================================
# 4. Evaluación: cobertura, coste y sesgo de las métricas derivadas
# =====================================================================================================================
def coverage(kept: Sequence[Trace], corpus: Corpus) -> dict[str, float]:
    ids = {t.trace_id for t in kept}
    out: dict[str, float] = {"kept_traces_pct": 100 * len(ids) / len(corpus), "kept_spans_pct": 100 * sum(t.n_spans for t in kept) / corpus.total_spans,
                             "kept_bytes_pct": 100 * sum(t.bytes for t in kept) / corpus.total_bytes}
    for name, fn in (("error", lambda t: t.error), ("error_span", lambda t: t.has_error_span), ("slow", lambda t: t.slow), ("costly", lambda t: t.costly), ("interesting", lambda t: t.interesting)):
        pop = [t for t in corpus.traces if fn(t)]
        out[f"recall_{name}_pct"] = 100 * sum(t.trace_id in ids for t in pop) / len(pop) if pop else float("nan")
    return out


def weighted_quantile(values: Sequence[float], weights: Sequence[float], q: float) -> float:
    pairs = sorted(zip(values, weights))
    tot = sum(w for _, w in pairs)
    acc = 0.0
    for v, w in pairs:
        acc += w
        if acc >= q * tot:
            return v
    return pairs[-1][0]


def estimate_metrics(traces: Sequence[Trace], weights: Mapping[str, float] | None = None) -> dict[str, float]:
    """Métricas «derivadas de trazas» (lo que haría un span-metrics DESPUÉS del muestreo): nº de peticiones, tasa de error, coste medio y p50/p95.
    ``weights``: trace_id → peso (1/probabilidad de inclusión) para corregir el sesgo; sin pesos, cada traza vale 1."""
    w = [weights.get(t.trace_id, 1.0) if weights is not None else 1.0 for t in traces]
    tot = sum(w)
    d = [t.duration_s for t in traces]
    return {"requests": tot, "error_rate": sum(wi for wi, t in zip(w, traces) if t.error) / tot, "mean_cost_usd": sum(wi * t.cost_usd for wi, t in zip(w, traces)) / tot,
            "p50_s": weighted_quantile(d, w, 0.5), "p95_s": weighted_quantile(d, w, 0.95)}


def inclusion_weights(kept: Sequence[Trace], keep_all: Callable[[Trace], bool], base_ratio: float) -> dict[str, float]:
    """Pesos de Horvitz-Thompson para una política «guardar siempre lo que cumple ``keep_all``; el resto con probabilidad ``base_ratio``».
    Una traza que cumple ``keep_all`` pesa 1 (probabilidad de inclusión 1); una del estrato base pesa 1/base_ratio."""
    return {t.trace_id: (1.0 if keep_all(t) else 1.0 / base_ratio) for t in kept}


# =====================================================================================================================
# 5. Cardinalidad
# =====================================================================================================================
def series_estimate(dims: Mapping[str, int]) -> int:
    """Cota superior del nº de series de una métrica: producto de las cardinalidades de cada etiqueta."""
    out = 1
    for v in dims.values():
        out *= max(1, int(v))
    return out


def count_series(prom_text: str, prefix: str = "") -> dict[str, int]:
    """Cuenta series distintas por nombre de métrica en un texto de exposición de Prometheus (p. ej. el exporter ``prometheus`` del Collector)."""
    series: dict[str, set[str]] = defaultdict(set)
    for ln in prom_text.splitlines():
        if not ln or ln.startswith("#"):
            continue
        m = re.match(r"([a-zA-Z_:][a-zA-Z0-9_:]*)(\{[^}]*\})?\s", ln)
        if m and m.group(1).startswith(prefix):
            series[m.group(1)].add(m.group(2) or "")
    return {k: len(v) for k, v in series.items()}


def storm_growth(n_requests: int, unique_ratio: float, base_series: int = 40, bytes_per_series: float = 2800.0) -> dict[str, float]:
    """Modelo mínimo de una tormenta: si cada petición añade una etiqueta casi única, las series crecen ≈ ``unique_ratio × peticiones``.
    ``bytes_per_series`` ≈ memoria por serie activa: medido con Prometheus v3.15 real y OTLP (30 000 series → +84 MB de RSS ≈ 2,8 KB/serie; con 10 000
    ≈ 1,2 KB/serie por el efecto del GC): mide la tuya (``prometheus_tsdb_head_series`` y ``process_resident_memory_bytes``)."""
    series = base_series + unique_ratio * n_requests
    return {"series": series, "head_memory_mb": series * bytes_per_series / 1e6}


# =====================================================================================================================
# 6. Coste del propio stack
# =====================================================================================================================
@dataclass
class StackCostModel:
    @classmethod
    def from_corpus(cls, corpus: "Corpus", tickets_per_day: float, **kw: Any) -> "StackCostModel":
        """Parámetros de volumen MEDIDOS en un corpus (spans por traza y bytes OTLP por span)."""
        sm = corpus.summary()
        params: dict[str, Any] = {"spans_per_trace": sm["spans_per_trace"], "bytes_per_span": sm["bytes_per_span"]}
        params.update(kw)                          # lo que pases (p. ej. el escenario de producción supuesto) tiene prioridad sobre lo medido
        return cls(tickets_per_day=tickets_per_day, **params)

    """Volumen diario y coste mensual del stack para N tickets/día. TODOS los precios son ILUSTRATIVOS (parámetros): pon los de tu proveedor."""
    tickets_per_day: float = 1_000_000
    spans_per_trace: float = 6.0
    bytes_per_span: float = 600.0                 # OTLP sin comprimir (medido por ``Corpus.summary``)
    trace_compress: float = 0.25                  # ratio medio de compresión en Tempo (parquet+zstd): PARÁMETRO a medir
    log_lines_per_ticket: float = 4.0
    bytes_per_log_line: float = 450.0
    log_compress: float = 0.15                    # Loki comprime los chunks (típico 5-10×): PARÁMETRO
    metric_series: float = 5_000
    scrape_interval_s: float = 15.0
    bytes_per_sample: float = 1.5                 # Prometheus: «1-2 bytes por muestra» (docs de almacenamiento)
    trace_keep: float = 1.0                       # fracción de trazas conservada tras el muestreo
    log_keep: float = 1.0
    price_gb_month_hot: float = 0.10              # ILUSTRATIVO: disco SSD / almacenamiento caliente
    price_gb_month_cold: float = 0.023            # ILUSTRATIVO: almacenamiento de objetos
    ingest_price_gb: float = 0.0                  # ILUSTRATIVO: 0 en autoalojado; en SaaS suele ser el mayor coste

    def daily_gb(self) -> dict[str, float]:
        tr = self.tickets_per_day * self.spans_per_trace * self.bytes_per_span / 1e9
        lg = self.tickets_per_day * self.log_lines_per_ticket * self.bytes_per_log_line / 1e9
        mt = self.metric_series * (86400 / self.scrape_interval_s) * self.bytes_per_sample / 1e9
        return {"traces_ingest": tr * self.trace_keep, "traces_stored": tr * self.trace_keep * self.trace_compress, "logs_ingest": lg * self.log_keep,
                "logs_stored": lg * self.log_keep * self.log_compress, "metrics_stored": mt}

    def monthly_cost(self, retention_days: Mapping[str, float], hot_days: Mapping[str, float] | None = None) -> dict[str, float]:
        d = self.daily_gb()
        hot_days = hot_days or {}
        out: dict[str, float] = {}
        for sig, key_in, key_st in (("traces", "traces_ingest", "traces_stored"), ("logs", "logs_ingest", "logs_stored"), ("metrics", None, "metrics_stored")):
            days = retention_days.get(sig, 7)
            hot = min(days, hot_days.get(sig, days))
            gb_resident = d[key_st] * hot * 1.0
            gb_cold = d[key_st] * max(0.0, days - hot)
            c = gb_resident * self.price_gb_month_hot + gb_cold * self.price_gb_month_cold
            if key_in:
                c += d[key_in] * 30 * self.ingest_price_gb
            out[sig] = c
        out["total"] = sum(out.values())
        return out


def retention_cost(daily_gb: float, tiers: Sequence[tuple[str, float, float]]) -> list[dict[str, float | str]]:
    """``tiers``: (nombre, días en ese nivel, precio USD/GB-mes). Devuelve GB residentes y coste mensual por nivel (régimen estacionario)."""
    rows = []
    for name, days, price in tiers:
        gb = daily_gb * days
        rows.append({"tier": name, "days": days, "resident_gb": gb, "usd_per_month": gb * price})
    return rows


# =====================================================================================================================
# 7. Generadores de configuración (validables con las herramientas oficiales)
# =====================================================================================================================
def _yaml(obj: Any, indent: int = 0) -> str:
    """Serializador YAML mínimo (dict/list/str/num/bool) para no depender de PyYAML en Colab."""
    pad = "  " * indent
    if isinstance(obj, dict):
        lines = []
        for k, v in obj.items():
            if isinstance(v, (dict, list)) and v:
                lines.append(f"{pad}{k}:\n{_yaml(v, indent + 1)}")
            else:
                lines.append(f"{pad}{k}: {_scalar(v)}")
        return "\n".join(lines)
    if isinstance(obj, list):
        lines = []
        for v in obj:
            if isinstance(v, dict) and v:
                first, *rest = _yaml(v, indent + 1).split("\n")
                lines.append(f"{pad}- {first.strip()}")
                lines += rest
            elif isinstance(v, list):
                lines.append(f"{pad}-\n{_yaml(v, indent + 1)}")
            else:
                lines.append(f"{pad}- {_scalar(v)}")
        return "\n".join(lines)
    return f"{pad}{_scalar(obj)}"


def _scalar(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "null"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, (dict, list)):
        return "{}" if isinstance(v, dict) else "[]"
    s = str(v)
    looks_numeric = re.fullmatch(r"[-+]?(\d[\d_]*)(\.\d+)?([eE][-+]?\d+)?|0x[0-9a-fA-F]+|[-+]?\.(inf|nan)|~", s, re.I) is not None
    return json.dumps(s, ensure_ascii=False) if (re.search(r"[:#{}\[\],&*!|>'\"%@`]", s) or s == "" or s.strip() != s or looks_numeric
                                                  or s.lower() in ("true", "false", "null", "yes", "no", "on", "off", "y", "n")) else s


def to_yaml(obj: Any) -> str:
    return _yaml(obj) + "\n"


def collector_config(policies: Sequence[Policy] | None, *, decision_wait: str = "2s", num_traces: int = 50_000, expected_new_traces_per_sec: int = 0,
                     decision_cache: tuple[int, int] | None = None, spanmetrics: bool = True, file_traces: str = "/out/traces.jsonl",
                     internal_metrics_port: int = 8888, prometheus_port: int = 8889, sampling_on: bool = True, extra_processor: dict | None = None) -> str:
    """Collector de laboratorio: OTLP/HTTP → [span_metrics + forward] → tail_sampling → exportador ``file``.
    Las métricas RED se calculan **antes** del muestreo (pipeline ``traces/in``) y salen por ``prometheus`` (puerto ``prometheus_port``): así NO están sesgadas."""
    ts: dict[str, Any] = {"decision_wait": decision_wait, "num_traces": num_traces, "expected_new_traces_per_sec": expected_new_traces_per_sec,
                          "policies": tail_policy_config(policies or [])}
    if decision_cache:
        ts["decision_cache"] = {"sampled_cache_size": decision_cache[0], "non_sampled_cache_size": decision_cache[1]}
    if extra_processor:
        ts.update(extra_processor)
    cfg: dict[str, Any] = {
        "receivers": {"otlp": {"protocols": {"http": {"endpoint": "0.0.0.0:4318"}}}},
        "processors": {"tail_sampling": ts} if sampling_on else {},
        "connectors": {"forward": {}},
        "exporters": {"file/traces": {"path": file_traces}, "prometheus": {"endpoint": f"0.0.0.0:{prometheus_port}"}},
        "service": {"telemetry": {"metrics": {"level": "detailed", "readers": [{"pull": {"exporter": {"prometheus": {"host": "0.0.0.0", "port": internal_metrics_port}}}}]}},
                    "pipelines": {}},
    }
    if spanmetrics:
        cfg["connectors"]["span_metrics"] = {"histogram": {"explicit": {"buckets": ["100ms", "500ms", "1s", "2s", "5s", "10s"]}},
                                              "dimensions": [{"name": "supportops.status"}], "metrics_flush_interval": "2s"}
    first = ["forward"] + (["span_metrics"] if spanmetrics else [])
    cfg["service"]["pipelines"]["traces/in"] = {"receivers": ["otlp"], "exporters": first}
    cfg["service"]["pipelines"]["traces/sampled"] = {"receivers": ["forward"], "processors": ["tail_sampling"] if sampling_on else [], "exporters": ["file/traces"]}
    if spanmetrics:
        cfg["service"]["pipelines"]["metrics/red"] = {"receivers": ["span_metrics"], "exporters": ["prometheus"]}
    return to_yaml(cfg)


def loki_limits_yaml(*, ingestion_rate_mb: float = 4, ingestion_burst_size_mb: float = 6, per_stream_rate_limit: str = "3MB", max_label_names_per_series: int = 15,
                     max_streams_per_user: int = 0, retention_period: str = "744h", reject_old_samples_max_age: str = "168h") -> dict[str, Any]:
    """Bloque ``limits_config`` de Loki (claves verificadas con ``loki -verify-config``)."""
    lim: dict[str, Any] = {"ingestion_rate_mb": ingestion_rate_mb, "ingestion_burst_size_mb": ingestion_burst_size_mb, "per_stream_rate_limit": per_stream_rate_limit,
                           "max_label_names_per_series": max_label_names_per_series, "retention_period": retention_period,
                           "reject_old_samples": True, "reject_old_samples_max_age": reject_old_samples_max_age}
    if max_streams_per_user:
        lim["max_streams_per_user"] = max_streams_per_user
    return {"limits_config": lim}


def tempo_overrides_yaml(*, max_bytes_per_trace: int = 5_000_000, rate_limit_bytes: int = 15_000_000, burst_size_bytes: int = 20_000_000, block_retention: str | None = None,
                         tenant: str | None = None) -> dict[str, Any]:
    """Overrides de Tempo (formato ``overrides: defaults: global/ingestion``). Claves comprobadas con Tempo 3.1 (``-config.verify``)."""
    d: dict[str, Any] = {"ingestion": {"rate_strategy": "local", "rate_limit_bytes": rate_limit_bytes, "burst_size_bytes": burst_size_bytes},
                         "global": {"max_bytes_per_trace": max_bytes_per_trace}}
    if block_retention:
        d["compaction"] = {"block_retention": block_retention}
    return {"overrides": {"defaults": d}} if tenant is None else {"overrides": {"per_tenant_override_config": ""}}


# =====================================================================================================================
# 8. Laboratorio con el Collector real (Docker)
# =====================================================================================================================
def docker_ok() -> bool:
    try:
        return subprocess.run(["docker", "info"], capture_output=True, timeout=10).returncode == 0
    except Exception:
        return False


def validate_collector_config(config: str, image: str = COLLECTOR_IMAGE) -> tuple[bool, str]:
    """``otelcol-contrib validate`` con el binario real en un contenedor efímero (sin red, sin puertos)."""
    d = pathlib.Path(tempfile.mkdtemp(prefix="otelcol-val-"))
    try:
        (d / "c.yaml").write_text(config)
        os.chmod(d / "c.yaml", 0o644)
        r = subprocess.run(["docker", "run", "--rm", "--network", "none", "-v", f"{d / 'c.yaml'}:/c.yaml:ro", image, "validate", "--config=/c.yaml"],
                           capture_output=True, text=True, timeout=120)
        return r.returncode == 0, (r.stdout + r.stderr)[-1500:]
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _host_port(name: str, port: int, timeout_s: float = 15.0) -> int:
    """Puerto de host que Docker asignó a ``port/tcp`` del contenedor ``name``. Reintenta con plazo: justo tras ``docker run -d`` la tabla de puertos puede
    estar aún vacía (carrera observada en R3); si el contenedor ya murió, falla enseguida con sus logs."""
    t0, last = time.time(), ""
    while time.time() - t0 < timeout_s:
        r = subprocess.run(["docker", "port", name, f"{port}/tcp"], capture_output=True, text=True)
        for ln in r.stdout.splitlines():
            m = re.search(r":(\d+)\s*$", ln.strip())
            if m:
                return int(m.group(1))
        last = (r.stderr or r.stdout).strip()
        if subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", name], capture_output=True, text=True).stdout.strip() == "false":
            break
        time.sleep(0.3)
    logs = subprocess.run(["docker", "logs", "--tail", "20", name], capture_output=True, text=True)
    raise RuntimeError(f"Docker no publicó el puerto {port} de {name}: {last}\n{(logs.stdout + logs.stderr)[-600:]}")


def _docker_run(args: Sequence[str], attempts: int = 3) -> None:
    """``docker run -d`` con reintentos (p. ej. «port is already allocated» o el daemon ocupado tras otro laboratorio). ``args`` sin el ``run -d``."""
    err = ""
    for k in range(attempts):
        r = subprocess.run(["docker", "run", "-d", *args], capture_output=True, text=True)
        if r.returncode == 0:
            return
        err = r.stderr[:500]
        name = args[args.index("--name") + 1] if "--name" in args else ""
        if name:
            subprocess.run(["docker", "rm", "-f", name], capture_output=True)
        time.sleep(1.5 * (k + 1))
    raise RuntimeError(err)


def _http_retry(opener: Any, url: str, *, tries: int = 4, timeout: float = 5.0) -> bytes:
    for k in range(tries):
        try:
            return opener.open(url, timeout=timeout).read()
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError):
            if k == tries - 1:
                raise
            time.sleep(0.5 * (k + 1))
    raise RuntimeError("inalcanzable")


class SamplingLab:
    """Collector contrib 0.162 en un contenedor efímero con puertos aleatorios (no choca con el stack). ``with SamplingLab(cfg) as lab:``
    ``lab.send(spans)`` (OTLP/HTTP protobuf), ``lab.kept_trace_ids()``, ``lab.internal()`` (métricas otelcol_*), ``lab.red_metrics()`` (span_metrics)."""

    def __init__(self, config: str, image: str = COLLECTOR_IMAGE):
        self.config, self.image = config, image
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="sampling-lab-"))
        (self.dir / "out").mkdir()
        os.chmod(self.dir / "out", 0o777)
        (self.dir / "config.yaml").write_text(config)
        os.chmod(self.dir / "config.yaml", 0o644)
        self.name = f"sampling-lab-{uuid.uuid4().hex[:8]}"
        self.port: dict[int, int] = {}
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def __enter__(self) -> "SamplingLab":
        cmd = ["docker", "run", "-d", "--name", self.name, "-p", "127.0.0.1::4318", "-p", "127.0.0.1::8888", "-p", "127.0.0.1::8889",
               "-v", f"{self.dir / 'config.yaml'}:/etc/otelcol-contrib/config.yaml:ro", "-v", f"{self.dir / 'out'}:/out", self.image, "--config=/etc/otelcol-contrib/config.yaml"]
        _docker_run(cmd[3:])
        try:
            for p in (4318, 8888, 8889):
                self.port[p] = _host_port(self.name, p)
        except Exception:
            self.__exit__()
            raise
        ready = False
        # listo = el log lo dice Y el receptor OTLP responde a una petición vacía (con plazo; no se continúa a ciegas)
        t0 = time.time()
        while time.time() - t0 < 40:
            if self.exited():
                break
            if "Everything is ready" in self.logs():
                try:
                    self._opener.open(urllib.request.Request(f"http://127.0.0.1:{self.port[4318]}/v1/traces", data=b"", headers={"Content-Type": "application/x-protobuf"}), timeout=3).read()
                    ready = True
                    break
                except Exception:      # noqa: BLE001 - el puerto publicado aún no reenvía: se reintenta
                    pass
            time.sleep(0.25)
        if self.exited() or not ready:
            msg = self.logs()[-1200:]
            self.__exit__()
            raise RuntimeError("el Collector no arrancó (o no abrió OTLP en 40 s):\n" + msg)
        return self

    def exited(self) -> bool:
        return subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", self.name], capture_output=True, text=True).stdout.strip() != "true"

    def logs(self) -> str:
        r = subprocess.run(["docker", "logs", self.name], capture_output=True, text=True)
        return r.stdout + r.stderr

    def send(self, spans: Sequence[Mapping[str, Any]], batch_traces: int = 50, pause_s: float = 0.0) -> int:
        """Envía los spans agrupados por trazas completas en lotes OTLP/HTTP (protobuf). Devuelve el nº de lotes."""
        by_trace: dict[str, list] = defaultdict(list)
        for s in spans:
            by_trace[s["trace_id"]].append(s)
        ids = list(by_trace)
        n = 0
        for i in range(0, len(ids), batch_traces):
            chunk = [s for tid in ids[i:i + batch_traces] for s in by_trace[tid]]
            body = spans_to_otlp(chunk).SerializeToString()
            req = urllib.request.Request(f"http://127.0.0.1:{self.port[4318]}/v1/traces", data=body, headers={"Content-Type": "application/x-protobuf"})
            for k in range(4):
                try:
                    self._opener.open(req, timeout=20).read()
                    break
                except (urllib.error.URLError, ConnectionError, TimeoutError):
                    if k == 3 or self.exited():
                        raise
                    time.sleep(0.5 * (k + 1))
            n += 1
            if pause_s:
                time.sleep(pause_s)
        return n

    def _read_lines(self) -> list[dict]:
        p = self.dir / "out" / "traces.jsonl"
        out = []
        for l in (p.read_text().splitlines() if p.exists() else []):
            try:
                out.append(json.loads(l))
            except json.JSONDecodeError:          # última línea a medio escribir por el Collector
                pass
        return out

    def kept_spans(self) -> list[dict[str, Any]]:
        out = []
        for line in self._read_lines():
            for rs in line.get("resourceSpans", []):
                for ss in rs.get("scopeSpans", []):
                    out += ss.get("spans", [])
        return out

    def kept_trace_ids(self) -> set[str]:
        return {s["traceId"] for s in self.kept_spans()}

    def wait_settled(self, timeout_s: float = 30.0, quiet_s: float = 3.0) -> int:
        """Espera a que el nº de spans exportados deje de crecer (el Collector decide tras ``decision_wait``)."""
        t0, last, last_change = time.time(), -1, time.time()
        while time.time() - t0 < timeout_s:
            n = len(self.kept_spans())
            if n != last:
                last, last_change = n, time.time()
            elif time.time() - last_change >= quiet_s:
                break
            time.sleep(0.5)
        return last

    def _scrape(self, port: int) -> str:
        return _http_retry(self._opener, f"http://127.0.0.1:{self.port[port]}/metrics").decode()

    def internal(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for ln in self._scrape(8888).splitlines():
            if ln.startswith("otelcol_"):
                name, val = ln.rsplit(" ", 1)
                name = re.sub(r"\{.*\}", "", name)
                out[name] = out.get(name, 0.0) + float(val)
        return out

    def internal_labeled(self, prefix: str) -> list[tuple[str, float]]:
        res = []
        for ln in self._scrape(8888).splitlines():
            if ln.startswith(prefix):
                name, val = ln.rsplit(" ", 1)
                res.append((name, float(val)))
        return res

    def red_text(self) -> str:
        return self._scrape(8889)

    def red_metrics(self) -> dict[str, float]:
        """Total de ``traces_span_metrics_calls_total`` por ``status_code`` y por ``supportops_status`` (RED calculado ANTES del muestreo)."""
        calls: dict[str, float] = defaultdict(float)
        for ln in self.red_text().splitlines():
            if ln.startswith("traces_span_metrics_calls_total{") and 'span_name="invoke_agent' in ln:
                labels, val = ln.rsplit(" ", 1)
                m = re.search(r'status_code="([^"]+)"', labels)
                calls[m.group(1) if m else "?"] += float(val)
        return dict(calls)

    def __exit__(self, *a: Any) -> None:
        subprocess.run(["docker", "rm", "-f", self.name], capture_output=True)
        shutil.rmtree(self.dir, ignore_errors=True)


# =====================================================================================================================
# 8b. Laboratorio de backends (Loki, Tempo, Prometheus) en contenedores efímeros: multi-tenant, límites y tormentas de cardinalidad
# =====================================================================================================================
LOKI_IMAGE = os.environ.get("LOKI_IMAGE", "grafana/loki:3.7.8")
TEMPO_IMAGE = os.environ.get("TEMPO_IMAGE", "grafana/tempo:3.1.0")
PROM_IMAGE = os.environ.get("PROM_IMAGE", "prom/prometheus:v3.15.0")

LOKI_LAB_CONFIG = """auth_enabled: {auth}
server:
  http_listen_port: 3100
  log_level: warn
common:
  instance_addr: 127.0.0.1
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory
schema_config:
  configs:
    - from: 2024-04-01
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h
limits_config:
{limits}
analytics:
  reporting_enabled: false
"""

TEMPO_LAB_CONFIG = """multitenancy_enabled: {mt}
stream_over_http_enabled: true
server:
  http_listen_port: 3200
distributor:
  receivers:
    otlp:
      protocols:
        http:
          endpoint: 0.0.0.0:4318
live_store:
  wal:
    ingestion_time_range_slack: 15m
  max_trace_idle: 5s
  max_block_duration: 1m
backend_scheduler:
  provider:
    compaction:
      compaction:
        compaction_window: 1h
        block_retention: 24h
storage:
  trace:
    backend: local
    wal:
      path: /var/tempo/wal
    local:
      path: /var/tempo/blocks
{overrides}
usage_report:
  reporting_enabled: false
"""


def loki_lab_config(limits: Mapping[str, Any] | None = None, auth: bool = True) -> str:
    lim = {"allow_structured_metadata": True, "reject_old_samples": True, "reject_old_samples_max_age": "168h", **(limits or {})}
    return LOKI_LAB_CONFIG.format(auth="true" if auth else "false", limits="\n".join("  " + l for l in to_yaml(lim).splitlines()))


def tempo_lab_config(overrides: Mapping[str, Any] | None = None, multitenancy: bool = True) -> str:
    ov = to_yaml({"overrides": {"defaults": overrides}}) if overrides else ""
    return TEMPO_LAB_CONFIG.format(mt="true" if multitenancy else "false", overrides=ov.rstrip())


class BackendLab:
    """Contenedor efímero (Loki, Tempo o Prometheus) con puertos de host aleatorios. ``with BackendLab('loki', config) as lab:`` → ``lab.url`` (API HTTP),
    ``lab.extra_url`` (OTLP/HTTP de Tempo). Salud: ``/ready`` (Prometheus: ``/-/ready``)."""

    def __init__(self, kind: str, config: str, extra_args: Sequence[str] = ()):
        self.kind, self.config, self.extra_args = kind, config, list(extra_args)
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix=f"lab-{kind}-"))
        self.cfg = self.dir / "config.yaml"
        self.cfg.write_text(config)
        os.chmod(self.cfg, 0o644)
        self.name = f"lab-{kind}-{uuid.uuid4().hex[:8]}"
        self.url = self.extra_url = ""
        self._op = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def __enter__(self) -> "BackendLab":
        k = self.kind
        if k == "loki":
            cmd = ["-p", "127.0.0.1::3100", "-v", f"{self.cfg}:/etc/loki.yaml:ro", LOKI_IMAGE, "-config.file=/etc/loki.yaml"]
            ports, health = [3100], "/ready"
        elif k == "tempo":
            cmd = ["-p", "127.0.0.1::3200", "-p", "127.0.0.1::4318", "-v", f"{self.cfg}:/etc/tempo.yaml:ro", TEMPO_IMAGE, "-config.file=/etc/tempo.yaml"]
            ports, health = [3200, 4318], "/ready"
        elif k == "prometheus":
            cmd = ["-p", "127.0.0.1::9090", "-v", f"{self.cfg}:/etc/prometheus/prometheus.yml:ro", PROM_IMAGE, "--config.file=/etc/prometheus/prometheus.yml",
                   "--web.enable-otlp-receiver", "--storage.tsdb.path=/prometheus", *self.extra_args]
            ports, health = [9090], "/-/ready"
        else:
            raise ValueError(k)
        _docker_run(["--name", self.name, *cmd])
        try:
            mapped = {p: _host_port(self.name, p) for p in ports}
        except Exception:
            self.__exit__()
            raise
        self.url = f"http://127.0.0.1:{mapped[ports[0]]}"
        if k == "tempo":
            self.extra_url = f"http://127.0.0.1:{mapped[4318]}"
        t0 = time.time()
        while time.time() - t0 < 120:
            try:
                if self._op.open(self.url + health, timeout=2).status == 200:
                    return self
            except Exception:
                pass
            time.sleep(1.5)
        logs = self.logs()[-800:]
        self.__exit__()
        raise RuntimeError(f"{k} no arrancó:\n{logs}")

    def logs(self) -> str:
        r = subprocess.run(["docker", "logs", self.name], capture_output=True, text=True)
        return r.stdout + r.stderr

    def _req(self, url: str, data: bytes | None = None, headers: Mapping[str, str] | None = None) -> tuple[int, bytes]:
        req = urllib.request.Request(url, data=data, headers=dict(headers or {}))
        for k in range(3):
            try:
                with self._op.open(req, timeout=30) as r:
                    return r.status, r.read()
            except urllib.error.HTTPError as e:
                return e.code, e.read()
            except (urllib.error.URLError, ConnectionError, TimeoutError):    # el puerto publicado puede tardar en reenviar: se reintenta (no afecta a los códigos 4xx/5xx)
                if k == 2:
                    raise
                time.sleep(1.0 * (k + 1))
        raise RuntimeError("inalcanzable")

    def metrics(self, prefix: str = "") -> dict[str, float]:
        _, body = self._req(self.url + "/metrics")
        out: dict[str, float] = {}
        for ln in body.decode().splitlines():
            if ln and not ln.startswith("#") and ln.startswith(prefix):
                name, val = ln.rsplit(" ", 1)
                out[name] = float(val)
        return out

    # ---- Loki
    def loki_push(self, tenant: str | None, streams: Sequence[Mapping[str, Any]]) -> tuple[int, str]:
        """``streams``: ``[{"stream": {label: valor}, "values": [[ts_ns, línea], ...]}]``."""
        h = {"Content-Type": "application/json", **({"X-Scope-OrgID": tenant} if tenant else {})}
        code, body = self._req(self.url + "/loki/api/v1/push", json.dumps({"streams": list(streams)}).encode(), h)
        return code, body.decode(errors="replace")[:240]

    def loki_count(self, tenant: str | None, logql: str, minutes: int = 30) -> tuple[int, int]:
        """(código HTTP, nº de líneas devueltas por ``query_range``)."""
        now = time.time_ns()
        q = urllib.parse.urlencode({"query": logql, "start": now - minutes * 60 * 10**9, "end": now + 10**9, "limit": 5000})
        code, body = self._req(self.url + "/loki/api/v1/query_range?" + q, headers={"X-Scope-OrgID": tenant} if tenant else {})
        if code != 200:
            return code, 0
        return code, sum(len(r["values"]) for r in json.loads(body)["data"]["result"])

    # ---- Tempo
    def tempo_send(self, tenant: str | None, spans: Sequence[Mapping[str, Any]]) -> tuple[int, str]:
        h = {"Content-Type": "application/x-protobuf", **({"X-Scope-OrgID": tenant} if tenant else {})}
        code, body = self._req(self.extra_url + "/v1/traces", spans_to_otlp(spans).SerializeToString(), h)
        return code, body.decode(errors="replace")[:200]

    def tempo_search(self, tenant: str | None, q: str = "{}", limit: int = 200) -> tuple[int, int]:
        code, body = self._req(self.url + "/api/search?" + urllib.parse.urlencode({"q": q, "limit": limit}), headers={"X-Scope-OrgID": tenant} if tenant else {})
        return code, (len(json.loads(body).get("traces", [])) if code == 200 else 0)

    def __exit__(self, *a: Any) -> None:
        subprocess.run(["docker", "rm", "-f", self.name], capture_output=True)
        shutil.rmtree(self.dir, ignore_errors=True)


PROM_LAB_CONFIG = "global:\n  scrape_interval: 15s\n"


def storm_experiment(n_series: int, *, bounded: bool, interval_s: float = 2.0, settle_s: float = 8.0) -> dict[str, float]:
    """Envía por OTLP a un Prometheus real un contador con ``n_series`` valores distintos de la etiqueta ``ticket_id`` (tormenta) o, con ``bounded=True``,
    sin esa etiqueta (un *View* del SDK que solo permite ``intent``). Devuelve ``prometheus_tsdb_head_series`` y la memoria (RSS) antes y después."""
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.metrics.view import View
    from opentelemetry.sdk.resources import Resource
    with BackendLab("prometheus", PROM_LAB_CONFIG) as prom:
        def stat() -> tuple[float, float]:
            m = prom.metrics()
            return m.get("prometheus_tsdb_head_series", 0.0), m.get("process_resident_memory_bytes", 0.0)
        prev = -1.0
        for _ in range(8):                # el RSS del arranque aún se mueve: se espera a que se estabilice (±1 MB entre lecturas a 2 s) antes de medir la línea base
            s0, r0 = stat()
            if abs(r0 - prev) < 1e6:
                break
            prev = r0
            time.sleep(2)
        views = [View(instrument_name="supportops.requests", attribute_keys={"intent"})] if bounded else []
        reader = PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=prom.url + "/api/v1/otlp/v1/metrics"), export_interval_millis=int(interval_s * 1000))
        mp = MeterProvider(resource=Resource.create({"service.name": "storm-lab"}), metric_readers=[reader], views=views)
        c = mp.get_meter("storm").create_counter("supportops.requests")
        intents = ("order_status", "refund", "kb_question", "escalation")
        for i in range(n_series):
            c.add(1, {"intent": intents[i % 4], "ticket_id": f"T-{i:07d}"})
        mp.force_flush()
        time.sleep(settle_s)
        s1, r1 = stat()
        mp.shutdown()
    return {"head_series_before": s0, "head_series_after": s1, "rss_mb_before": r0 / 1e6, "rss_mb_after": r1 / 1e6, "series_added": s1 - s0}


# =====================================================================================================================
# 8c. Experimentos reutilizables (los usan la lección, el proyecto y el grabador de datos pregrabados)
# =====================================================================================================================
def run_collector_experiment(corpus: Corpus, policies: Sequence[Policy], *, decision_wait: str = "2s", num_traces: int = 50_000, settle_s: float = 40.0,
                             spans: Sequence[Mapping[str, Any]] | None = None, attempts: int = 3, **cfg_kw: Any) -> dict[str, Any]:
    """Envía el corpus al Collector real con ``tail_sampling`` y devuelve lo conservado, las métricas internas del procesador y el RED calculado antes del muestreo.
    Robusto: si el Collector no cae pero no conservó nada (arranque lento, envío perdido) repite hasta ``attempts`` veces; el resultado lleva ``attempts_used``."""
    res: dict[str, Any] = {}
    for k in range(1, max(1, attempts) + 1):
        res = _run_collector_once(corpus, policies, decision_wait=decision_wait, num_traces=num_traces, settle_s=settle_s, spans=spans, **cfg_kw)
        res["attempts_used"] = k
        if res["crashed"] or res["n_kept"] > 0:
            break
    return res


def _run_collector_once(corpus: Corpus, policies: Sequence[Policy], *, decision_wait: str, num_traces: int, settle_s: float,
                        spans: Sequence[Mapping[str, Any]] | None, **cfg_kw: Any) -> dict[str, Any]:
    sp = list(spans) if spans is not None else [s for t in corpus.traces for s in t.spans]
    cfg = collector_config(policies, decision_wait=decision_wait, num_traces=num_traces, **cfg_kw)
    with SamplingLab(cfg) as lab:
        lab.send(sp)
        lab.wait_settled(timeout_s=settle_s + float(decision_wait.rstrip('s')), quiet_s=float(decision_wait.rstrip('s')) + 3.0)
        time.sleep(1.0)
        crashed = lab.exited()
        ids = lab.kept_trace_ids()
        internal = {}
        if not crashed:
            for _ in range(10):        # las métricas internas del procesador pueden tardar en aparecer en /metrics: se sondea (≤ 10 s) en vez de leer una vez
                internal = lab.internal()
                if "otelcol_processor_tail_sampling_sampling_traces_on_memory" in internal:
                    break
                time.sleep(1.0)
        per_policy = {}
        if not crashed:
            for name, val in lab.internal_labeled("otelcol_processor_tail_sampling_count_traces_sampled"):
                m = re.search(r'decision="([^"]+)",policy="([^"]+)"', name)
                if m and m.group(1) == "sampled":
                    per_policy[m.group(2)] = per_policy.get(m.group(2), 0) + val
        red = {} if crashed else lab.red_metrics()
        logs = lab.logs()[-600:] if crashed else ""
    by = corpus.by_id()
    kept = [by[i] for i in ids if i in by]
    return {"crashed": crashed, "kept_ids": sorted(ids), "n_kept": len(kept), "coverage": coverage(kept, corpus) if kept else {}, "per_policy": per_policy,
            "internal": {k: v for k, v in internal.items() if "tail_sampling" in k or k == "otelcol_receiver_accepted_spans"}, "red": red, "crash_log": logs}


def numeric_attribute_probe(corpus: Corpus) -> dict[str, str]:
    """Reproduce con el Collector real la trampa de ``numeric_attribute`` (int64): sobre un atributo *double* (``supportops.cost_usd``) con ``min_value`` solo
    el procesador cae (SIGSEGV en 0.162.0); ``ottl_condition`` con decimales funciona."""
    out: dict[str, str] = {}
    spans = [s for t in corpus.traces[:300] for s in t.spans]
    cases: dict[str, str] = {}
    for label, min_value in (("double + min_value decimal (0.0005)", 0.0005), ("double + min_value=0", 0)):
        raw = {"name": "c", "type": "numeric_attribute", "numeric_attribute": {"key": "supportops.cost_usd", "min_value": min_value}}   # to_config() lo prohíbe: se escribe a mano
        cases[label] = collector_config(None).replace("    policies: []", "    policies:\n" + "\n".join("      " + l for l in to_yaml([raw]).splitlines()))
    cases["ottl_condition  > 0.0005"] = collector_config([AttrCompare(name="c")])
    for label, cfg in cases.items():
        with SamplingLab(cfg) as lab:
            lab.send(spans)
            time.sleep(5)
            out[label] = "CRASH (SIGSEGV)" if lab.exited() else f"ok · {len(lab.kept_trace_ids())} trazas conservadas"
    return out


def backends_experiment(corpus: Corpus | None = None) -> dict[str, Any]:
    """Loki y Tempo reales con multi-tenant y límites bajos: aislamiento por ``X-Scope-OrgID``, rechazo sin tenant y los tres errores de límites."""
    import copy
    res: dict[str, Any] = {"loki": {}, "tempo": {}}
    now = time.time_ns()

    def streams(n: int, extra: Mapping[str, str] | None = None, size: int = 50) -> list[dict]:
        return [{"stream": {"service_name": "supportops", "ticket": f"t{i}", **(extra or {})}, "values": [[str(now + i), "x" * size]]} for i in range(n)]
    lim = {"ingestion_rate_mb": 1, "ingestion_burst_size_mb": 1, "per_stream_rate_limit": "512KB", "max_label_names_per_series": 8, "max_streams_per_user": 20}
    with BackendLab("loki", loki_lab_config(lim, auth=True)) as lk:
        r = res["loki"]
        r["A: 10 streams"] = lk.loki_push("tenantA", streams(10))[0]
        r["B: 10 streams"] = lk.loki_push("tenantB", streams(10))[0]
        code, body = lk.loki_push("tenantA", streams(30))
        r["A: +30 streams (límite 20)"] = code
        r["_msg_streams"] = body
        code, body = lk.loki_push("tenantC", streams(1, {f"l{i}": "v" for i in range(10)}))
        r["C: 11 etiquetas (límite 8)"] = code
        r["_msg_labels"] = body
        r["sin tenant (X-Scope-OrgID ausente)"] = lk.loki_push(None, streams(1))[0]
        time.sleep(2)
        r["líneas visibles para A"] = lk.loki_count("tenantA", '{service_name="supportops"}')[1]
        r["líneas visibles para B"] = lk.loki_count("tenantB", '{service_name="supportops"}')[1]
        r["líneas visibles para tenant desconocido"] = lk.loki_count("tenantZ", '{service_name="supportops"}')[1]
        t0 = time.time()
        codes = [lk.loki_push("tenantD", streams(1, size=200_000))[0] for _ in range(8)]
        r["ráfaga 8 × 200 KB en < 1 s (límite 1 MB/s)"] = sorted(set(codes))
        r["_burst_seconds"] = round(time.time() - t0, 2)
    corpus = corpus or build_corpus(60, start_s="live", duration_s=60)
    small = [t for t in corpus.traces if t.bytes < 2500][:10]
    root = small[0].spans[0]
    big_spans = []
    for k in range(30):
        for sp in small[0].spans:
            d = copy.deepcopy(sp)
            d["span_id"] = "%016x" % (int(sp["span_id"], 16) + k * 7919 + 1)
            d["parent_span_id"] = sp["parent_span_id"] if k == 0 else root["span_id"]
            big_spans.append(d)
    ov = {"global": {"max_bytes_per_trace": 3000}, "ingestion": {"rate_limit_bytes": 200000, "burst_size_bytes": 200000}}
    with BackendLab("tempo", tempo_lab_config(ov, multitenancy=True)) as tp:
        r = res["tempo"]
        r["A: 5 trazas pequeñas"] = tp.tempo_send("tenantA", [s for t in small[:5] for s in t.spans])[0]
        r["B: 5 trazas pequeñas"] = tp.tempo_send("tenantB", [s for t in small[5:10] for s in t.spans])[0]
        r["A: 1 traza de %d bytes (límite 3000)" % spans_to_otlp(big_spans).ByteSize()] = tp.tempo_send("tenantA", big_spans)[0]
        r["sin tenant"] = tp.tempo_send(None, small[0].spans)[0]
        deadline = time.time() + 45
        a = b = 0
        while time.time() < deadline:
            a, b = tp.tempo_search("tenantA")[1], tp.tempo_search("tenantB")[1]
            if a >= 5 and b >= 5:
                break
            time.sleep(3)
        r["trazas visibles para A"], r["trazas visibles para B"] = a, b
        r["búsqueda sin tenant"] = tp.tempo_search(None)[0]
        r["descartes"] = {k.split("{")[1].rstrip("}"): v for k, v in tp.metrics("tempo_discarded_spans_total").items()}
    return res


# =====================================================================================================================
# 9. Utilidades de presentación
# =====================================================================================================================
def fmt_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1000:
            return f"{n:.1f} {unit}"
        n /= 1000
    return f"{n:.1f} PB"


def pareto_front(points: Sequence[tuple[float, float]]) -> list[int]:
    """Índices de los puntos no dominados (menos coste, más cobertura). ``points`` = (coste, cobertura)."""
    idx = []
    for i, (c, v) in enumerate(points):
        if not any((c2 <= c and v2 >= v and (c2 < c or v2 > v)) for j, (c2, v2) in enumerate(points) if j != i):
            idx.append(i)
    return idx
