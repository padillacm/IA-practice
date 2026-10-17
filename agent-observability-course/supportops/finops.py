"""Módulo 13 · FinOps de agentes: tokens -> coste, atribución, caché de prompts, presupuestos, topes y bucles caros.

Todo se construye ENCIMA de ``supportops.telemetry`` y de los puntos de extensión ``Instrumentor`` (sin tocar ``agent.py``):

    from supportops.finops import PriceTable, ILLUSTRATIVE_PRICES, FinOpsInstrumentor, CacheSimulator, CostLedger
    ledger, cache = CostLedger(), CacheSimulator(min_prefix_tokens=256)
    finops = FinOpsInstrumentor(ILLUSTRATIVE_PRICES, cache=cache, ledger=ledger, handle=tel)          # tel = setup_telemetry(...)
    agent = SupportAgent(instrumentor=CompositeInstrumentor(OTelInstrumentor(tel), finops))
    ...
    ledger.to_frame()            # una fila por ticket: cliente, tier, feature, modelo, tokens (con caché), coste y desglose

⚠️  LOS PRECIOS DE ESTE MÓDULO SON ILUSTRATIVOS. ``ILLUSTRATIVE_PRICES`` no refleja los precios de ningún proveedor ni de ninguna fecha:
sirve para que los ejemplos tengan magnitudes razonables. Los precios reales cambian con frecuencia y por modelo (incluidos los
multiplicadores de caché): cárgalos de tu proveedor con ``PriceTable.from_json(...)`` o la variable ``SUPPORTOPS_PRICES_FILE``.

Convenciones de tokens (spec GenAI, estado *Development*): ``gen_ai.usage.input_tokens`` INCLUYE los tokens de caché;
``gen_ai.usage.cache_read.input_tokens`` y ``gen_ai.usage.cache_write.input_tokens`` son SUBCONJUNTOS de la entrada. Algunas APIs
(p. ej. la de Anthropic) devuelven ``input_tokens`` SIN caché y suman aparte lectura y escritura: ``semconv_usage`` normaliza.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
import math
import os
import pathlib
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, Mapping, Sequence

from .instrument import Instrumentor, LLMCallInfo, RunContext, ToolCallInfo
from .llm import LLMError
from .llm.base import messages_tokens
from .models import AgentResult, Ticket
from .tools import ToolError

DISCLAIMER = ("PRECIOS ILUSTRATIVOS: no son de ningún proveedor ni de ninguna fecha. Cárgalos de tu proveedor "
              "(PriceTable.from_json o SUPPORTOPS_PRICES_FILE); cambian con frecuencia y por modelo.")
FINOPS_PREFIX = "supportops.finops."


# ---------------------------------------------------------------------------------------------------------------------
# Precios y desglose de coste
# ---------------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Usage4:
    """Uso con la semántica de la spec GenAI: ``input_total`` INCLUYE ``cache_read`` y ``cache_write``."""
    input_total: int
    output: int
    cache_read: int = 0
    cache_write: int = 0

    @property
    def uncached(self) -> int:
        return max(self.input_total - self.cache_read - self.cache_write, 0)

    def __post_init__(self) -> None:
        if min(self.input_total, self.output, self.cache_read, self.cache_write) < 0:
            raise ValueError("los tokens no pueden ser negativos")
        if self.cache_read + self.cache_write > self.input_total:
            raise ValueError("cache_read + cache_write no puede superar a input_total (son subconjuntos de la entrada)")


def semconv_usage(provider_style: str, **u: int) -> Usage4:
    """Normaliza el ``usage`` de una API a la semántica de la spec.

    * ``"anthropic"``: ``input_tokens`` EXCLUYE caché; total = ``input_tokens + cache_read_input_tokens + cache_creation_input_tokens``
      (documentación de *prompt caching* de Anthropic).
    * ``"semconv"``: ya viene como la spec (``input_tokens`` incluye caché; ``cache_read_input_tokens``/``cache_write_input_tokens`` subconjuntos).
    """
    if provider_style == "anthropic":
        cr, cw = int(u.get("cache_read_input_tokens", 0)), int(u.get("cache_creation_input_tokens", 0))
        return Usage4(int(u["input_tokens"]) + cr + cw, int(u["output_tokens"]), cr, cw)
    if provider_style == "semconv":
        return Usage4(int(u["input_tokens"]), int(u["output_tokens"]), int(u.get("cache_read_input_tokens", 0)), int(u.get("cache_write_input_tokens", 0)))
    raise ValueError("provider_style: 'anthropic' | 'semconv'")


@dataclass(frozen=True)
class ModelPrice:
    """USD por MILLÓN de tokens. ``cache_read``/``cache_write`` ``None`` = sin descuento/recargo (se cobran como entrada normal)."""
    input: float
    output: float
    cache_read: float | None = None
    cache_write: float | None = None

    @property
    def cr(self) -> float:
        return self.input if self.cache_read is None else self.cache_read

    @property
    def cw(self) -> float:
        return self.input if self.cache_write is None else self.cache_write


@dataclass(frozen=True)
class CostBreakdown:
    input: float          # entrada NO cacheada
    cache_read: float
    cache_write: float
    output: float

    @property
    def total(self) -> float:
        return self.input + self.cache_read + self.cache_write + self.output

    def as_dict(self) -> dict[str, float]:
        return {"input": self.input, "cache_read": self.cache_read, "cache_write": self.cache_write, "output": self.output, "total": self.total}


class PriceTable:
    """Tabla de precios configurable. ``cost(model, usage)`` aplica la fórmula con la semántica de subconjuntos de caché.

    .. math:: C = \\frac{u\\,p_{in} + r\\,p_{cr} + w\\,p_{cw} + o\\,p_{out}}{10^6},\\quad u = I - r - w
    """

    def __init__(self, prices: Mapping[str, ModelPrice], *, label: str = "ILUSTRATIVA", note: str = DISCLAIMER, default: ModelPrice | None = None):
        self.prices, self.label, self.note, self.default = dict(prices), label, note, default

    # -- construcción ---------------------------------------------------------------------------------------------
    @classmethod
    def from_dict(cls, d: Mapping[str, Mapping[str, float]], *, label: str = "CONFIGURADA", note: str = "Precios cargados por el usuario.") -> "PriceTable":
        return cls({m: ModelPrice(float(v["input"]), float(v["output"]), v.get("cache_read"), v.get("cache_write")) for m, v in d.items()}, label=label, note=note)

    @classmethod
    def from_json(cls, path: str | os.PathLike[str]) -> "PriceTable":
        return cls.from_dict(json.loads(pathlib.Path(path).read_text(encoding="utf-8")), label=f"fichero:{pathlib.Path(path).name}")

    @classmethod
    def from_env(cls, var: str = "SUPPORTOPS_PRICES_FILE") -> "PriceTable":
        p = os.environ.get(var)
        return cls.from_json(p) if p else ILLUSTRATIVE_PRICES

    def to_dict(self) -> dict[str, dict[str, float | None]]:
        return {m: {"input": p.input, "output": p.output, "cache_read": p.cache_read, "cache_write": p.cache_write} for m, p in self.prices.items()}

    # -- uso ------------------------------------------------------------------------------------------------------
    def price(self, model: str) -> ModelPrice:
        p = self.prices.get(model) or self.default
        if p is None:
            raise KeyError(f"modelo sin precio en la tabla ({self.label}): {model!r}; modelos: {sorted(self.prices)}")
        return p

    def cost(self, model: str, usage: Usage4) -> CostBreakdown:
        p = self.price(model)
        return CostBreakdown(usage.uncached * p.input / 1e6, usage.cache_read * p.cr / 1e6, usage.cache_write * p.cw / 1e6, usage.output * p.output / 1e6)

    def describe(self) -> str:
        head = f"[{self.label}] {self.note}"
        rows = [f"  {m:<14} entrada {p.input:>7.3f} · salida {p.output:>7.3f} · lectura caché {p.cr:>7.3f} · escritura caché {p.cw:>7.3f}  (USD / 1M tokens)" for m, p in self.prices.items()]
        return "\n".join([head, *rows])


# Ilustrativa: mismas magnitudes que ``supportops.pricing`` (mock) + multiplicadores de caché DE LABORATORIO (lectura 0,1×; escritura 1,25×).
ILLUSTRATIVE_PRICES = PriceTable({
    "mock-small": ModelPrice(0.25, 1.25, cache_read=0.025, cache_write=0.3125),
    "mock-large": ModelPrice(3.00, 15.00, cache_read=0.30, cache_write=3.75),
})


# ---------------------------------------------------------------------------------------------------------------------
# Caché de prompts simulada
# ---------------------------------------------------------------------------------------------------------------------
class CacheSimulator:
    """Caché de prefijos gestionada por el proveedor (modelo simplificado y determinista).

    * Una llamada con ``input_total < min_prefix_tokens`` no es cacheable (los proveedores fijan mínimos por modelo: 512-4096 tokens en la
      documentación consultada; aquí es un parámetro de laboratorio).
    * Dentro de una ejecución, la llamada ``k > 0`` LEE como prefijo toda la entrada de la llamada ``k-1`` (la conversación solo crece por el
      final) si no ha caducado el TTL; lo demás se ESCRIBE en caché.
    * La primera llamada lee el prefijo estático (sistema + herramientas) si otra ejecución con el mismo ``prefix_key`` lo usó hace menos de ``ttl_s``.
    * ``ttl_s``: 5 min por defecto; cada lectura RENUEVA la caducidad (como en la API de Anthropic, sin coste extra).
    """

    def __init__(self, enabled: bool = True, min_prefix_tokens: int = 256, ttl_s: float = 300.0):
        self.enabled, self.min_prefix_tokens, self.ttl_s = enabled, min_prefix_tokens, ttl_s
        self._warm: dict[str, float] = {}
        self._runs: dict[str, tuple[int, float]] = {}

    def step(self, run_key: str, prefix_key: str, step_idx: int, input_total: int, static_tokens: int, now_s: float) -> tuple[int, int]:
        """Devuelve ``(cache_read, cache_write)`` para esta llamada y actualiza el estado."""
        if not self.enabled or input_total < self.min_prefix_tokens:
            self._runs[run_key] = (input_total, now_s)
            return 0, 0
        read = 0
        prev = self._runs.get(run_key)
        if step_idx > 0 and prev and now_s - prev[1] <= self.ttl_s and prev[0] >= self.min_prefix_tokens:
            read = min(prev[0], input_total)
        elif static_tokens >= self.min_prefix_tokens and now_s - self._warm.get(prefix_key, -math.inf) <= self.ttl_s:
            read = min(static_tokens, input_total)
        self._warm[prefix_key] = now_s
        self._runs[run_key] = (input_total, now_s)
        return read, input_total - read

    def end_run(self, run_key: str) -> None:
        self._runs.pop(run_key, None)


def policy_prompt(target_tokens: int = 2500) -> str:
    """Prompt de sistema LARGO (políticas de la empresa incrustadas) para que la caché importe: ~``target_tokens`` tokens (≈ 4 car./token)."""
    from . import catalog
    from .agent import SYSTEM_PROMPT
    docs = "\n".join(f"[{d.doc_id}] {d.title}: {d.text}" for d in catalog.KB_DOCS)
    out, n = SYSTEM_PROMPT + "\n\nPolíticas vigentes de SupportOps (consúltalas antes de responder):\n", 0
    while len(out) < target_tokens * 4:
        n += 1
        out += f"\n## Edición {n}\n{docs}\n"
    return out[: target_tokens * 4]


# ---------------------------------------------------------------------------------------------------------------------
# Libro de costes (atribución)
# ---------------------------------------------------------------------------------------------------------------------
def is_wasted(r: AgentResult, loop: bool = False) -> bool:
    """Coste «desperdiciado»: ejecuciones que no resolvieron (error, max_steps), respondieron con datos inventados o entraron en bucle."""
    return r.status in ("error", "max_steps") or (not r.grounded) or loop


class CostLedger:
    """Una fila por ticket, con las dimensiones de atribución (cliente, tier, feature, agente, modelo) y el coste desglosado.

    ``to_frame()`` -> ``pandas.DataFrame``. ``by("feature", "tier")`` agrega (coste, tickets, coste por ticket, % del total).
    """

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def add(self, row: dict[str, Any]) -> None:
        self.rows.append(row)

    def reset(self) -> None:
        self.rows.clear()

    def to_frame(self):
        import pandas as pd
        return pd.DataFrame(self.rows)

    def by(self, *dims: str):
        df = self.to_frame()
        g = df.groupby(list(dims)).agg(tickets=("ticket_id", "count"), cost_usd=("cost_usd", "sum"), wasted_usd=("wasted_usd", "sum"),
                                       input_total=("input_total", "sum"), output=("output", "sum"))
        g["cost_per_ticket"] = g.cost_usd / g.tickets
        g["share"] = g.cost_usd / g.cost_usd.sum()
        return g.sort_values("cost_usd", ascending=False)


# ---------------------------------------------------------------------------------------------------------------------
# Instrumentor FinOps: atributos de span, métricas, logs y libro
# ---------------------------------------------------------------------------------------------------------------------
@dataclass
class _RunCost:
    steps: int = 0
    input_total: int = 0
    output: int = 0
    cache_read: int = 0
    cache_write: int = 0
    cost: dict[str, float] = field(default_factory=lambda: {"input": 0.0, "cache_read": 0.0, "cache_write": 0.0, "output": 0.0})
    static_tokens: int = 0
    models: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> float:
        return sum(self.cost.values())


class FinOpsInstrumentor(Instrumentor):
    """Calcula el coste de cada llamada con ``PriceTable`` (+ ``CacheSimulator``) y lo publica.

    * **Span ``chat``**: ``gen_ai.usage.cache_read.input_tokens``, ``gen_ai.usage.cache_write.input_tokens`` (subconjuntos de la entrada, spec)
      y ``supportops.finops.cost_usd``. **Span raíz** ``invoke_agent``: ``supportops.finops.cost_usd`` y ``.cache_hit_ratio``.
      (Nombres propios con prefijo ``supportops.finops.``: no pisan ``supportops.cost_usd``, que el instrumentor OTel rellena con los precios del mock.)
    * **Métricas** (por EJECUCIÓN, etiquetas de baja cardinalidad: modelo, feature, tier, agente): ``supportops.llm.cost`` (USD, por componente),
      ``supportops.llm.tokens`` (por tipo), ``supportops.ticket.cost`` (histograma USD), ``supportops.ticket.cost.wasted`` (USD),
      ``supportops.tickets`` (contador por estado). Cliente y ticket NO son etiquetas.
    * **Log** ``ticket costed`` con ``trace_id`` y los campos de alta cardinalidad (cliente, ticket) como atributos: la atribución por cliente
      se consulta en Loki, no en Prometheus.
    * **Libro** (``CostLedger``): una fila por ticket.

    Compónlo DESPUÉS del instrumentor OTel: ``CompositeInstrumentor(OTelInstrumentor(tel), finops)``.
    """

    def __init__(self, prices: PriceTable = ILLUSTRATIVE_PRICES, *, cache: CacheSimulator | None = None, ledger: CostLedger | None = None,
                 handle: Any = None, prefix_key_fn: Callable[[RunContext, LLMCallInfo], str] | None = None,
                 feature_fn: Callable[[RunContext, AgentResult], str] | None = None, loop_fn: Callable[[AgentResult], bool] | None = None):
        self.prices, self.cache, self.ledger = prices, cache or CacheSimulator(enabled=False), ledger if ledger is not None else CostLedger()
        self.prefix_key_fn = prefix_key_fn or (lambda ctx, info: f"{ctx.agent_name}:{info.model}")
        self.feature_fn = feature_fn or (lambda ctx, r: r.intent_pred or "unknown")
        self.loop_fn = loop_fn or (lambda r: False)
        self.h = handle
        self._logger = handle.logger() if handle is not None and getattr(handle, "logger_provider", None) is not None else None
        self._m = None
        if handle is not None and getattr(handle, "meter_provider", None) is not None:
            m = handle.meter()
            self._m = {"cost": m.create_counter("supportops.llm.cost", unit="USD", description="Coste de LLM (precios de la tabla configurada)"),
                       "tokens": m.create_counter("supportops.llm.tokens", unit="{token}", description="Tokens por tipo (entrada no cacheada, lectura/escritura de caché, salida)"),
                       "ticket": m.create_histogram("supportops.ticket.cost", unit="USD", description="Coste por ticket",
                                                    explicit_bucket_boundaries_advisory=[0.0001, 0.0003, 0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0]),
                       "wasted": m.create_counter("supportops.ticket.cost.wasted", unit="USD", description="Coste de tickets no resueltos, alucinados o en bucle"),
                       "tickets": m.create_counter("supportops.tickets", unit="{ticket}", description="Tickets por estado")}

    # -- hooks ---------------------------------------------------------------------------------------------------
    def agent_run(self, ctx: RunContext):                                   # type: ignore[override]
        from contextlib import contextmanager

        @contextmanager
        def cm() -> Iterator[None]:
            ctx.state["finops"] = _RunCost()
            yield
            self._finish(ctx)
        return cm()

    def llm_call(self, ctx: RunContext, info: LLMCallInfo):                  # type: ignore[override]
        from contextlib import contextmanager
        from opentelemetry import trace as otel_trace

        @contextmanager
        def cm() -> Iterator[None]:
            yield
            r = info.response
            if r is None:
                return
            rc: _RunCost = ctx.state["finops"]
            static = r.usage.input_tokens - messages_tokens(info.messages or [], None, None)
            rc.static_tokens = max(rc.static_tokens, static)
            read, write = self.cache.step(ctx.run_id, self.prefix_key_fn(ctx, info), rc.steps, r.usage.input_tokens, max(static, 0), ctx.clock.now_s())
            usage = Usage4(r.usage.input_tokens, r.usage.output_tokens, read, write)
            c = self.prices.cost(r.model, usage)
            rc.steps += 1
            rc.input_total += usage.input_total; rc.output += usage.output; rc.cache_read += read; rc.cache_write += write
            for k, v in c.as_dict().items():
                if k != "total":
                    rc.cost[k] += v
            rc.models[r.model] = rc.models.get(r.model, 0) + 1
            ctx.state["finops_last_cost"] = c.total
            ctx.state["finops_calls"] = rc.steps
            span = otel_trace.get_current_span()
            if span.is_recording():
                span.set_attributes({"gen_ai.usage.cache_read.input_tokens": read, "gen_ai.usage.cache_write.input_tokens": write,
                                     FINOPS_PREFIX + "cost_usd": round(c.total, 8)})
        return cm()

    # -- cierre de la ejecución ----------------------------------------------------------------------------------
    def _finish(self, ctx: RunContext) -> None:
        from opentelemetry import trace as otel_trace
        rc: _RunCost = ctx.state["finops"]
        r, t = ctx.result, ctx.ticket
        self.cache.end_run(ctx.run_id)
        if r is None:
            return
        loop = bool(self.loop_fn(r))
        wasted = is_wasted(r, loop)
        feature = self.feature_fn(ctx, r)
        model = max(rc.models, key=rc.models.get) if rc.models else ctx.model
        hit = rc.cache_read / rc.input_total if rc.input_total else 0.0
        row = {"ticket_id": t.ticket_id, "customer_id": t.customer_id, "tier": t.tier, "channel": t.channel, "feature": feature, "agent": ctx.agent_name,
               "model": model, "status": r.status, "grounded": r.grounded, "loop": loop, "n_llm": r.n_llm_calls, "n_tool": r.n_tool_calls,
               "input_total": rc.input_total, "uncached": rc.input_total - rc.cache_read - rc.cache_write, "cache_read": rc.cache_read, "cache_write": rc.cache_write,
               "output": rc.output, "cost_usd": rc.total, "cost_input": rc.cost["input"], "cost_cache_read": rc.cost["cache_read"],
               "cost_cache_write": rc.cost["cache_write"], "cost_output": rc.cost["output"], "wasted_usd": rc.total if wasted else 0.0,
               "cache_hit_ratio": hit, "t_start": r.start_s, "latency_s": r.latency_s, "error_type": r.error_type,
               "budget_blocked": r.error_type == "budget_exceeded"}
        self.ledger.add(row)
        span = otel_trace.get_current_span()
        if span.is_recording():
            span.set_attributes({FINOPS_PREFIX + "cost_usd": round(rc.total, 8), FINOPS_PREFIX + "cache_hit_ratio": round(hit, 4),
                                 FINOPS_PREFIX + "wasted": wasted, FINOPS_PREFIX + "feature": feature})
        if self._m is not None:
            base = {"gen_ai.request.model": model, "supportops.feature": feature, "supportops.customer.tier": t.tier, "gen_ai.agent.name": ctx.agent_name}
            for comp, v in rc.cost.items():
                self._m["cost"].add(v, {**base, "supportops.cost.component": comp})
            for typ, n in (("input", rc.input_total - rc.cache_read - rc.cache_write), ("cache_read", rc.cache_read), ("cache_write", rc.cache_write), ("output", rc.output)):
                self._m["tokens"].add(n, {**base, "gen_ai.token.type": typ})
            self._m["ticket"].record(rc.total, {**base, "supportops.outcome": r.status})
            self._m["tickets"].add(1, {**base, "supportops.outcome": r.status})
            if wasted:
                self._m["wasted"].add(rc.total, base)
        if self._logger is not None:
            from opentelemetry import _logs as otel_logs
            self._logger.emit(timestamp=ctx.clock.now_ns(), severity_number=otel_logs.SeverityNumber.INFO, severity_text="INFO", body="ticket costed",
                              attributes={"supportops.ticket.id": t.ticket_id, "supportops.customer.id": t.customer_id, "supportops.customer.tier": t.tier,
                                          "supportops.feature": feature, "gen_ai.request.model": model, "supportops.finops.cost_usd": round(rc.total, 8),
                                          "supportops.finops.wasted": wasted, "supportops.status": r.status, "gen_ai.usage.input_tokens": rc.input_total,
                                          "gen_ai.usage.output_tokens": rc.output})

    def log(self, ctx: RunContext, level: int, message: str, fields: dict[str, Any]) -> None:
        return None


# ---------------------------------------------------------------------------------------------------------------------
# Presupuestos y topes (Instrumentors que rechazan ANTES de la llamada: el agente los captura como un error del proveedor)
# ---------------------------------------------------------------------------------------------------------------------
@dataclass
class BudgetPool:
    """Presupuesto de un periodo (p. ej. 30 días). ``burn_rate`` = fracción de presupuesto gastada / fracción de periodo transcurrida."""
    limit_usd: float
    period_s: float = 30 * 86400.0
    spent_usd: float = 0.0

    def add(self, usd: float) -> None:
        self.spent_usd += usd

    def burn_rate(self, elapsed_s: float) -> float:
        return (self.spent_usd / self.limit_usd) / max(elapsed_s / self.period_s, 1e-12)

    def forecast_usd(self, elapsed_s: float) -> float:
        """Gasto proyectado al final del periodo si el ritmo actual se mantiene."""
        return self.spent_usd * self.period_s / max(elapsed_s, 1e-12)

    def remaining_usd(self) -> float:
        return self.limit_usd - self.spent_usd

    def register_metrics(self, meter: Any, elapsed_fn: Callable[[], float], name: str = "monthly") -> None:
        """Publica el presupuesto como gauges asíncronos: ``supportops.budget.spent``, ``.limit`` (USD) y ``.burn_rate`` (adimensional)."""
        from opentelemetry.metrics import Observation
        attrs = {"supportops.budget.name": name}
        meter.create_observable_gauge("supportops.budget.spent", callbacks=[lambda o: [Observation(self.spent_usd, attrs)]], unit="USD",
                                      description="Gasto acumulado del presupuesto")
        meter.create_observable_gauge("supportops.budget.limit", callbacks=[lambda o: [Observation(self.limit_usd, attrs)]], unit="USD",
                                      description="Límite del presupuesto del periodo")
        meter.create_observable_gauge("supportops.budget.burn_rate", callbacks=[lambda o: [Observation(self.burn_rate(elapsed_fn()), attrs)]], unit="1",
                                      description="Ritmo de gasto relativo al ritmo lineal permitido (1 = justo en presupuesto)")


class BudgetGuard(Instrumentor):
    """Tope de gasto por ticket (y, opcional, por cliente y día). Rechaza la SIGUIENTE llamada a LLM cuando se ha alcanzado el tope.

    Lanza ``LLMError(error_type="budget_exceeded", status=429, retryable=False)`` antes de la llamada: el agente la trata como un fallo del
    proveedor (``status="error"``), el span ``chat`` queda ``ERROR`` con ``error.type=budget_exceeded`` y no se gasta nada más.
    Orden en el Composite: ``CompositeInstrumentor(OTelInstrumentor(...), BudgetGuard(...), FinOpsInstrumentor(...))``: el guard rechaza ANTES de la llamada
    (con el span OTel ya abierto, para que quede registrado) y, al terminar la llamada, FinOps (más interno) ya ha calculado su coste real (con caché).
    Si FinOps no está o va fuera, usa una cota superior sin caché. Los premium pueden tener más tope: ``tier_multiplier``.
    El tope se evalúa ENTRE llamadas: una llamada ya iniciada no se interrumpe (puede pasarse del tope por una llamada).
    """

    def __init__(self, prices: PriceTable = ILLUSTRATIVE_PRICES, *, per_ticket_usd: float | None = None, per_customer_day_usd: float | None = None,
                 tier_multiplier: Mapping[str, float] | None = None, pool: BudgetPool | None = None, pool_stop_ratio: float | None = None):
        self.prices, self.per_ticket_usd, self.per_customer_day_usd = prices, per_ticket_usd, per_customer_day_usd
        self.tier_multiplier = dict(tier_multiplier or {})
        self.customer_spend: dict[tuple[str, int], float] = defaultdict(float)
        self.pool, self.pool_stop_ratio = pool, pool_stop_ratio
        self.blocked: list[tuple[str, str]] = []                      # (ticket_id, motivo)
        self._run_spend: dict[str, float] = {}

    def run_spent(self, ticket_id: str) -> float:
        return self._run_spend.get(ticket_id, 0.0)

    def ratio(self, ticket_id: str) -> float:
        return self.run_spent(ticket_id) / self.per_ticket_usd if self.per_ticket_usd else 0.0

    def _deny(self, ctx: RunContext, why: str) -> None:
        self.blocked.append((ctx.ticket.ticket_id, why))
        raise LLMError(f"presupuesto agotado ({why})", status=429, error_type="budget_exceeded", retryable=False, latency_s=0.0)

    def llm_call(self, ctx: RunContext, info: LLMCallInfo):                  # type: ignore[override]
        from contextlib import contextmanager

        @contextmanager
        def cm() -> Iterator[None]:
            t = ctx.ticket
            mult = self.tier_multiplier.get(t.tier, 1.0)
            spent = self.run_spent(t.ticket_id)
            if self.per_ticket_usd is not None and spent >= self.per_ticket_usd * mult:
                self._deny(ctx, "tope por ticket")
            day = int(ctx.clock.now_s() // 86400)
            if self.per_customer_day_usd is not None and self.customer_spend[(t.customer_id, day)] >= self.per_customer_day_usd * mult:
                self._deny(ctx, "tope diario del cliente")
            if self.pool is not None and self.pool_stop_ratio is not None and self.pool.spent_usd >= self.pool.limit_usd * self.pool_stop_ratio:
                self._deny(ctx, "presupuesto global")
            yield
            r = info.response
            if r is not None:
                n_done = ctx.state.get("budget_calls", 0) + 1
                ctx.state["budget_calls"] = n_done
                # coste real de ESTA llamada si FinOpsInstrumentor ya la contó (debe ir DENTRO del guard en el Composite); si no, cota superior sin caché
                usd = ctx.state.get("finops_last_cost") if ctx.state.get("finops_calls") == n_done else None
                if usd is None:
                    usd = self.prices.cost(r.model, Usage4(r.usage.input_tokens, r.usage.output_tokens)).total
                self._run_spend[t.ticket_id] = spent + usd
                self.customer_spend[(t.customer_id, day)] += usd
                if self.pool is not None:
                    self.pool.add(usd)
        return cm()


class DowngradeLLM:
    """Degradación de modelo: usa ``cheap`` en lugar de ``primary`` cuando el gasto del ticket supera ``soft_ratio`` del tope (``BudgetGuard``).

    Conserva ``provider``/``model`` del principal (así el agente y los spans declaran el modelo configurado); el span ``chat`` mostrará en
    ``gen_ai.response.model`` el que respondió de verdad.
    """

    def __init__(self, primary: Any, cheap: Any, guard: BudgetGuard, soft_ratio: float = 0.5):
        self.primary, self.cheap, self.guard, self.soft_ratio = primary, cheap, guard, soft_ratio
        self.provider, self.model = primary.provider, primary.model
        self.downgrades = 0

    def chat(self, messages, tools=None, **kw):
        tid = kw.get("call_key", ("", 0))[0]
        if self.guard.ratio(tid) >= self.soft_ratio:
            self.downgrades += 1
            return self.cheap.chat(messages, tools, **kw)
        return self.primary.chat(messages, tools, **kw)


class LoopGuard(Instrumentor):
    """Corta los bucles de herramientas.

    La llamada idéntica (mismo nombre y argumentos) nº ``max_repeats + 1`` se rechaza ANTES de ejecutarse con
    ``ToolError(error_type="loop_detected")`` y se marca la ejecución; la SIGUIENTE llamada a LLM se rechaza con
    ``LLMError(error_type="loop_detected")`` (no retryable). Sin esto último, un modelo «obsesionado» seguiría pidiendo la misma herramienta y
    gastando tokens hasta ``max_steps``: cortar solo la herramienta ahorra latencia de herramienta, no tokens.
    """

    def __init__(self, max_repeats: int = 2):
        self.max_repeats = max_repeats
        self.tripped: list[str] = []

    def tool_call(self, ctx: RunContext, info: ToolCallInfo):                # type: ignore[override]
        from contextlib import contextmanager

        @contextmanager
        def cm() -> Iterator[None]:
            seen: dict[str, int] = ctx.state.setdefault("loop_seen", {})
            key = info.call.name + "|" + json.dumps(info.call.arguments, sort_keys=True, default=str)
            seen[key] = seen.get(key, 0) + 1
            if seen[key] > self.max_repeats:
                self.tripped.append(ctx.ticket.ticket_id)
                ctx.state["loop_tripped"] = True
                raise ToolError(f"llamada repetida {seen[key]} veces: posible bucle", "loop_detected", latency_s=0.0)
            yield
        return cm()

    def llm_call(self, ctx: RunContext, info: LLMCallInfo):                  # type: ignore[override]
        from contextlib import contextmanager

        @contextmanager
        def cm() -> Iterator[None]:
            if ctx.state.get("loop_tripped"):
                raise LLMError("bucle de herramientas detectado: ejecución abortada", status=499, error_type="loop_detected", retryable=False, latency_s=0.0)
            yield
        return cm()


def detect_loop_in_result(r: AgentResult, min_repeats: int = 3) -> tuple[bool, int]:
    """Detección POST-HOC sobre ``AgentResult.steps``: ¿hay ``min_repeats`` o más llamadas idénticas (herramienta + argumentos) en la ejecución?"""
    seen: dict[str, int] = {}
    for s in r.steps:
        if s.kind == "tool":
            k = s.name + "|" + json.dumps(s.attributes.get("arguments", {}), sort_keys=True, default=str)
            seen[k] = seen.get(k, 0) + 1
    worst = max(seen.values(), default=0)
    return worst >= min_repeats, worst


# ---------------------------------------------------------------------------------------------------------------------
# Detección de desvío de coste (alerta)
# ---------------------------------------------------------------------------------------------------------------------
def cost_drift_alert(series: Sequence[float], *, baseline_n: int = 10, ratio: float = 1.6, persist: int = 3) -> int | None:
    """Índice del primer punto en que salta la alerta de desvío: ``persist`` puntos CONSECUTIVOS con valor ≥ ``ratio`` × la mediana de los
    primeros ``baseline_n`` puntos (línea base). Devuelve ``None`` si no salta. Los puntos ``NaN`` rompen la racha."""
    import statistics
    base = [x for x in series[:baseline_n] if x == x]
    if len(base) < max(3, baseline_n // 2):
        return None
    thr = ratio * statistics.median(base)
    run = 0
    for i in range(baseline_n, len(series)):
        v = series[i]
        run = run + 1 if (v == v and v >= thr) else 0
        if run >= persist:
            return i
    return None


def finops_alert_rule_json(folder_uid: str, *, datasource_uid: str = "prometheus", ratio: float = 1.6, for_: str = "5m") -> dict[str, Any]:
    """Regla de alerta de Grafana (API de aprovisionamiento ``POST /api/v1/provisioning/alert-rules``): «coste por ticket (10 min) > ratio × el de
    hace 1 hora». Usa las métricas de ``FinOpsInstrumentor``. Estructura verificada contra el stack del curso (Grafana 13)."""
    cur = "sum(rate(supportops_ticket_cost_USD_sum[10m])) / sum(rate(supportops_ticket_cost_USD_count[10m]))"
    base = "sum(rate(supportops_ticket_cost_USD_sum[10m] offset 1h)) / sum(rate(supportops_ticket_cost_USD_count[10m] offset 1h))"
    return {"title": "FinOps · desvío del coste por ticket", "ruleGroup": "finops", "folderUID": folder_uid, "noDataState": "OK", "execErrState": "OK",
            "for": for_, "condition": "C",
            "labels": {"curso": "finops"}, "annotations": {"summary": "El coste por ticket se ha disparado frente a hace una hora"},
            "data": [
                {"refId": "A", "relativeTimeRange": {"from": 600, "to": 0}, "datasourceUid": datasource_uid,
                 "model": {"expr": f"({cur}) / ({base})", "instant": True, "intervalMs": 1000, "maxDataPoints": 43200, "refId": "A"}},
                {"refId": "C", "relativeTimeRange": {"from": 600, "to": 0}, "datasourceUid": "__expr__",
                 "model": {"type": "threshold", "expression": "A", "conditions": [{"evaluator": {"type": "gt", "params": [ratio]}}], "refId": "C"}}]}


__all__ = ["DISCLAIMER", "Usage4", "semconv_usage", "ModelPrice", "CostBreakdown", "PriceTable", "ILLUSTRATIVE_PRICES", "CacheSimulator", "policy_prompt",
           "CostLedger", "is_wasted", "FinOpsInstrumentor", "BudgetPool", "BudgetGuard", "DowngradeLLM", "LoopGuard", "detect_loop_in_result",
           "cost_drift_alert", "finops_alert_rule_json"]
