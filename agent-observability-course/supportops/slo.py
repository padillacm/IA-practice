"""SLIs, SLOs, presupuesto de error y alertas por *burn rate* multiventana para agentes (módulo 16).  Requiere numpy.

Contenido
* ``SLO`` y ``DEFAULT_SLOS``: disponibilidad, latencia, calidad y coste de SupportOps (cada uno con su definición de «evento bueno»).
* ``events_from_run``: convierte una ejecución del agente (+ juez) en eventos por ticket con los 4 SLIs.
* Series y burn rate: ``bin_events``, ``burn_series``, ``MultiWindowPolicy``/``GOOGLE_POLICIES``, ``fire_series``, ``alert_quality``.
* Presupuesto: ``budget_report``, ``simulate_month`` (binomial; la vista de 30 días no se puede simular con el agente completo).
* ``simulate_day``: 24 h de tráfico REAL del agente con un incidente de proveedor LLM y una regresión silenciosa de prompt.
* Prometheus/Grafana: ``sli_promql``, ``burn_promql``, ``grafana_burn_rule``, ``rules_yaml`` (alertas provisionadas).
* ``render_postmortem``: plantilla de postmortem sin culpa a partir de un diccionario.

Los multiplicadores 14,4 / 6 / 1 y las ventanas 1 h/5 min, 6 h/30 min, 3 d/6 h son los de «Alerting on SLOs» (Google SRE Workbook, cap. 5).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from .clock import SIM_EPOCH_S, stable_rng

# =====================================================================================================================
# Definición de SLOs
# =====================================================================================================================
BASELINE_FAULTS = {"llm_error": 0.002, "tool_error": 0.002, "tool_timeout": 0.0005, "latency_spike": 0.02, "hallucination": 0.01,
                   "tool_loop": 0.002, "pii_leak": 0.001}


@dataclass(frozen=True)
class SLO:
    name: str
    sli: str                      # availability | latency | quality | cost
    objective: float              # p. ej. 0.99
    threshold: float | None       # umbral del evento bueno (latencia en s, coste en USD)
    description: str
    window_days: int = 30

    @property
    def budget(self) -> float:
        return 1.0 - self.objective


DEFAULT_SLOS: dict[str, SLO] = {
    "availability": SLO("availability", "availability", 0.99, None, "El ticket termina `ok` o `escalated` (no error, degradado ni max_steps)"),
    "latency": SLO("latency", "latency", 0.97, 5.0, "El ticket se resuelve en ≤ 5 s (extremo a extremo, `invoke_agent`)"),
    "quality": SLO("quality", "quality", 0.95, None, "La respuesta evaluada está fundamentada (groundedness ≥ 0,5) en una muestra uniforme del 25 %"),
    "cost": SLO("cost", "cost", 0.98, 0.0005, "El ticket cuesta ≤ 0,0005 USD (precios ilustrativos)"),
}


def sli_good(slo: SLO, row: Mapping[str, Any]) -> bool | None:
    """¿Es bueno el evento? ``None`` = el evento no cuenta para este SLI (p. ej. ticket no evaluado por el juez)."""
    if slo.sli == "availability":
        return row["status"] in ("ok", "escalated")
    if slo.sli == "latency":
        return row["latency_s"] <= (slo.threshold or 0)
    if slo.sli == "cost":
        return row["cost_usd"] <= (slo.threshold or 0)
    if slo.sli == "quality":
        return row.get("quality_good")
    raise ValueError(slo.sli)


def events_from_run(tickets: Sequence[Any], results: Sequence[Any], cases: Sequence[Any] | None = None, judge: Any | None = None, *,
                    eval_rate: float = 0.25, version: str = "v1", salt: str = "slo-sample") -> list[dict[str, Any]]:
    """Un evento por ticket: tiempo, estado, latencia, coste y —en una muestra uniforme determinista— la calidad según el juez."""
    from .quality_eval import MockJudge, RateSampler
    sampler = RateSampler(eval_rate, salt)
    judge = judge or MockJudge()
    rows = []
    for i, (t, r) in enumerate(zip(tickets, results)):
        row = {"t": r.end_s, "ticket_id": t.ticket_id, "status": r.status, "latency_s": r.latency_s, "cost_usd": r.cost_usd, "version": version,
               "incident": t.incident, "quality_good": None}
        if cases is not None:
            c = cases[i]
            if sampler.decide(c)[0]:
                row["quality_good"] = bool(judge.evaluate(c).scores["groundedness"].label == "pass")
        rows.append(row)
    return rows


# =====================================================================================================================
# Series y burn rate
# =====================================================================================================================
def bin_events(rows: Sequence[Mapping[str, Any]], slo: SLO, *, t0: float, n_bins: int, step_s: float = 60.0) -> tuple[np.ndarray, np.ndarray]:
    """(buenos, totales) por intervalo de ``step_s`` segundos para un SLO."""
    good, total = np.zeros(n_bins), np.zeros(n_bins)
    for r in rows:
        g = sli_good(slo, r)
        if g is None:
            continue
        i = int((r["t"] - t0) // step_s)
        if 0 <= i < n_bins:
            total[i] += 1
            good[i] += bool(g)
    return good, total


def trailing_sum(x: np.ndarray, width: int) -> np.ndarray:
    c = np.cumsum(np.insert(x, 0, 0.0))
    idx = np.arange(1, len(x) + 1)
    return c[idx] - c[np.maximum(idx - width, 0)]


def burn_series(good: np.ndarray, total: np.ndarray, width: int, objective: float, min_events: int = 5) -> np.ndarray:
    """Burn rate con ventana móvil de ``width`` intervalos: ``(1 − buenos/totales) / (1 − objetivo)``. NaN si hay < ``min_events`` eventos."""
    g, t = trailing_sum(good, width), trailing_sum(total, width)
    with np.errstate(divide="ignore", invalid="ignore"):
        bad_ratio = np.where(t >= min_events, 1.0 - g / t, np.nan)
    return bad_ratio / (1.0 - objective)


@dataclass(frozen=True)
class MultiWindowPolicy:
    name: str
    factor: float                 # burn rate mínimo
    long_min: int                 # ventana larga (minutos)
    short_min: int                # ventana corta (minutos) ≈ 1/12 de la larga
    severity: str                 # page | ticket

    def budget_consumed(self, window_days: int = 30) -> float:
        """Fracción del presupuesto del periodo que se consume si el burn rate se mantiene durante la ventana larga."""
        return self.factor * self.long_min / (window_days * 24 * 60)


GOOGLE_POLICIES = (
    MultiWindowPolicy("fast-burn", 14.4, 60, 5, "page"),
    MultiWindowPolicy("medium-burn", 6.0, 6 * 60, 30, "page"),
    MultiWindowPolicy("slow-burn", 1.0, 3 * 24 * 60, 6 * 60, "ticket"),
)
# Ventanas COMPRIMIDAS para el laboratorio en vivo (no esperamos 1 h): mismos factores, ventanas de minutos.
LAB_POLICIES = (
    MultiWindowPolicy("fast-burn", 14.4, 5, 1, "page"),
    MultiWindowPolicy("slow-burn", 3.0, 15, 3, "ticket"),
)


def fire_series(good: np.ndarray, total: np.ndarray, objective: float, policy: MultiWindowPolicy, step_min: float = 1.0) -> np.ndarray:
    """True en los intervalos donde la política dispara: burn(larga) ≥ factor **y** burn(corta) ≥ factor."""
    wl, ws = int(policy.long_min / step_min), max(1, int(policy.short_min / step_min))
    bl, bs = burn_series(good, total, wl, objective), burn_series(good, total, ws, objective)
    return (np.nan_to_num(bl, nan=0.0) >= policy.factor) & (np.nan_to_num(bs, nan=0.0) >= policy.factor)


def threshold_fire_series(good: np.ndarray, total: np.ndarray, bad_ratio: float, width: int, min_events: int = 5) -> np.ndarray:
    """Alerta ingenua: tasa de error en una ventana > umbral fijo (el anti-patrón con el que comparamos)."""
    g, t = trailing_sum(good, width), trailing_sum(total, width)
    with np.errstate(divide="ignore", invalid="ignore"):
        br = np.where(t >= min_events, 1.0 - g / t, 0.0)
    return br > bad_ratio


def alert_quality(fire: np.ndarray, incident: np.ndarray, step_min: float = 1.0, reset_slack_min: int = 0) -> dict[str, Any]:
    """Calidad de una alerta frente a la verdad (máscara booleana del incidente): detectó (recall), tiempo hasta detectar (TTD, min),
    precisión por intervalo (fracción de intervalos disparados que están dentro del incidente + holgura de reajuste) y nº de intervalos falsos."""
    inc = incident.copy()
    if reset_slack_min:
        k = int(reset_slack_min / step_min)
        idx = np.where(incident)[0]
        for i in idx:
            inc[i:i + k + 1] = True
    fired = fire.astype(bool)
    start = int(np.argmax(incident)) if incident.any() else None
    hit = np.where(fired & incident)[0]
    ttd = float((hit[0] - start) * step_min) if len(hit) else None
    fp = int((fired & ~inc).sum())
    return {"detected": bool(len(hit)), "ttd_min": ttd, "precision": float((fired & inc).sum() / fired.sum()) if fired.sum() else float("nan"),
            "false_intervals": fp, "fired_intervals": int(fired.sum())}


def pages_per_week(fire: np.ndarray, step_min: float = 1.0, min_gap_min: int = 30) -> float:
    """Nº de *páginas* (inicios de episodios separados por ≥ ``min_gap_min`` minutos) normalizado a una semana."""
    idx = np.where(fire)[0]
    if not len(idx):
        return 0.0
    starts = 1 + int((np.diff(idx) * step_min >= min_gap_min).sum())
    return starts * (7 * 24 * 60) / (len(fire) * step_min)


# =====================================================================================================================
# Presupuesto de error
# =====================================================================================================================
def budget_report(good: float, total: float, objective: float, *, elapsed_frac: float = 1.0) -> dict[str, float]:
    """Estado del presupuesto sobre ``total`` eventos observados. ``elapsed_frac`` = fracción del periodo transcurrida (para proyectar)."""
    bad = total - good
    allowed = (1 - objective) * total
    consumed = bad / allowed if allowed else float("inf")
    burn_avg = consumed / elapsed_frac if elapsed_frac else float("inf")
    return {"sli": good / total if total else float("nan"), "bad": bad, "allowed_bad": allowed, "consumed": consumed, "remaining": 1 - consumed,
            "avg_burn_rate": burn_avg, "exhaustion_frac": (1 / burn_avg if burn_avg > 0 else float("inf"))}


def simulate_month(seed: int = 42, days: int = 30, per_min: float = 4.0, base_bad: float = 0.004,
                   incidents: Sequence[tuple[float, float, float, float]] = ()) -> tuple[np.ndarray, np.ndarray]:
    """Mes de SLI de disponibilidad por minuto con conteos binomiales (no con el agente completo: 43 200 min × tráfico serían demasiado).
    ``incidents`` = (día, hora, duración en min, tasa de fallo durante el incidente). Devuelve (buenos, totales) por minuto."""
    rng = np.random.default_rng(seed)
    n = days * 24 * 60
    minute_of_day = np.arange(n) % (24 * 60)
    lam = per_min * (1 + 0.5 * np.sin(2 * np.pi * (minute_of_day / (24 * 60) - 0.3)))
    total = rng.poisson(lam).astype(float)
    p_bad = np.full(n, base_bad)
    for day, hour, dur, rate in incidents:
        s = int(day * 24 * 60 + hour * 60)
        p_bad[s:s + int(dur)] = rate
    bad = rng.binomial(total.astype(int), p_bad).astype(float)
    return total - bad, total


# =====================================================================================================================
# Un día de tráfico real con incidentes
# =====================================================================================================================
@dataclass
class DayScenario:
    hours: float = 24.0
    tickets_per_min: float = 2.0
    outage: tuple[float, float, float] = (10.0, 10.75, 0.65)       # (hora inicio, hora fin, prob. de error del proveedor) — incidente PAGEABLE
    regression: tuple[float, float] = (6.0, 14.0)                  # (despliegue v2, rollback) — regresión silenciosa de prompt
    slow_tools: tuple[float, float, float] | None = None           # (inicio, fin, factor) opcional


def simulate_day(seed: int = 42, scenario: DayScenario | None = None, *, with_quality: bool = True, judge: Any | None = None) -> dict[str, Any]:
    """Ejecuta el AGENTE sobre un día sintético (tiempo simulado) con un fallo masivo del proveedor LLM y una regresión de prompt (v2).
    Devuelve ``{"rows", "tickets", "results", "cases", "t0", "n_bins", "truth": {...}}``; ``truth`` guarda las ventanas reales de los incidentes."""
    from .quality_eval import MockJudge
    from .regression import PROMPT_VERSIONS, make_agent
    from .traffic import Incident, generate_tickets
    sc = scenario or DayScenario()
    dur = sc.hours * 3600
    n = int(sc.hours * 60 * sc.tickets_per_min)
    incs = [Incident("llm_provider_outage", "llm_error", sc.outage[0] * 3600, sc.outage[1] * 3600, prob=sc.outage[2], params={"status": 503, "persistent": True})]
    if sc.slow_tools:
        incs.append(Incident("tools_slow", "latency_spike", sc.slow_tools[0] * 3600, sc.slow_tools[1] * 3600, prob=0.8,
                             params={"factor": sc.slow_tools[2], "target": "tool"}))
    from .traffic import generate_tickets as gen
    tickets = gen(n, seed=seed, duration_s=dur, fault_rates=BASELINE_FAULTS, incidents=incs, start_s=SIM_EPOCH_S)
    agents = {v: make_agent(v, seed=seed) for v in ("v1", "v2")}
    judge = judge or MockJudge(seed)
    results, cases, versions = [], [], []
    for t in tickets:
        h = (t.created_at - SIM_EPOCH_S) / 3600
        v = "v2" if sc.regression[0] <= h < sc.regression[1] else "v1"
        agent, col = agents[v]
        results.append(agent.run(t))
        cases.append(col.cases[-1])
        versions.append(v)
    rows: list[dict[str, Any]] = []
    from .quality_eval import RateSampler
    sampler = RateSampler(0.25, "slo-sample")
    for t, r, c, v in zip(tickets, results, cases, versions):
        row = {"t": r.end_s, "ticket_id": t.ticket_id, "status": r.status, "latency_s": r.latency_s, "cost_usd": r.cost_usd, "version": v,
               "incident": t.incident, "quality_good": None, "intent": t.intent_true, "n_tool_calls": r.n_tool_calls, "n_llm_calls": r.n_llm_calls,
               "truth_ungrounded": not c.truth["grounded"]}
        if with_quality and sampler.decide(c)[0]:
            row["quality_good"] = bool(judge.evaluate(c).scores["groundedness"].label == "pass")
        rows.append(row)
    n_bins = int(math.ceil(sc.hours * 60)) + 30
    truth = {"outage": (sc.outage[0] * 60, sc.outage[1] * 60), "regression": (sc.regression[0] * 60, sc.regression[1] * 60)}
    return {"rows": rows, "tickets": tickets, "results": results, "cases": cases, "t0": SIM_EPOCH_S, "n_bins": n_bins, "truth": truth, "scenario": sc,
            "prompt_versions": PROMPT_VERSIONS}


def minute_mask(start_min: float, end_min: float, n_bins: int) -> np.ndarray:
    m = np.zeros(n_bins, dtype=bool)
    m[int(start_min):int(math.ceil(end_min))] = True
    return m


# =====================================================================================================================
# Prometheus / Grafana
# =====================================================================================================================
SVC = 'service_name="supportops-agent"'


def sli_promql(kind: str, window: str, objective_threshold: float | None = None) -> str:
    """Ratio de eventos buenos en ``window`` (PromQL sobre las métricas de los módulos 09 y 14)."""
    if kind == "availability":
        return f'sum(rate(supportops_agent_requests_total{{{SVC},supportops_status=~"ok|escalated"}}[{window}])) / sum(rate(supportops_agent_requests_total{{{SVC}}}[{window}]))'
    if kind == "latency":
        le = _fmt_le(objective_threshold if objective_threshold is not None else 5.0)
        return f'sum(rate(gen_ai_invoke_agent_duration_seconds_bucket{{{SVC},le="{le}"}}[{window}])) / sum(rate(gen_ai_invoke_agent_duration_seconds_count{{{SVC}}}[{window}]))'
    if kind == "cost":
        le = _fmt_le(objective_threshold if objective_threshold is not None else 0.0005)
        return f'sum(rate(supportops_agent_request_cost_USD_bucket{{{SVC},le="{le}"}}[{window}])) / sum(rate(supportops_agent_request_cost_USD_count{{{SVC}}}[{window}]))'
    if kind == "quality":
        return ('sum(rate(supportops_eval_results_total{gen_ai_evaluation_name="groundedness",gen_ai_evaluation_score_label="pass"}[%s])) / '
                'sum(rate(supportops_eval_results_total{gen_ai_evaluation_name="groundedness"}[%s]))' % (window, window))
    raise ValueError(kind)


def _fmt_le(x: float) -> str:
    return repr(float(x))      # Prometheus expone `le="5.0"` (no `5`) y `le="0.0005"`


def burn_promql(slo: SLO, window: str) -> str:
    return f"(1 - ({sli_promql(slo.sli, window, slo.threshold)})) / {slo.budget:.6g}"


def grafana_burn_rule(slo: SLO, policy: MultiWindowPolicy, *, dashboard_uid: str, panel_id: int, folder: str = "Curso observabilidad de agentes",
                      long_w: str | None = None, short_w: str | None = None, for_: str = "0s", team: str = "plataforma",
                      runbook: str | None = None, receiver_labels: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Regla de alerta de Grafana (formato de *provisioning*) para una política de burn rate multiventana.

    Consultas A (ventana larga) y B (corta) → reduce C/D → math E (``$C > f && $D > f``) → umbral F. El enlace al dashboard va en
    ``annotations.__dashboardUid__`` y ``__panelId__``; el grupo se evalúa cada múltiplo de 10 s."""
    lw, sw = long_w or f"{policy.long_min}m", short_w or f"{policy.short_min}m"
    def q(ref: str, w: str) -> dict[str, Any]:
        return {"refId": ref, "relativeTimeRange": {"from": 600, "to": 0}, "datasourceUid": "prometheus",
                "model": {"refId": ref, "expr": burn_promql(slo, w), "instant": True, "intervalMs": 15000, "maxDataPoints": 43200}}
    def red(ref: str, src: str) -> dict[str, Any]:
        return {"refId": ref, "datasourceUid": "__expr__", "model": {"refId": ref, "type": "reduce", "expression": src, "reducer": "last", "settings": {"mode": "dropNN"}}}
    uid = f"slo-{slo.name}-{policy.name}"
    return {
        "uid": uid, "title": f"SLO {slo.name} · {policy.name} (×{policy.factor:g})", "condition": "F", "for": for_,
        "noDataState": "OK", "execErrState": "Error", "isPaused": False,
        "data": [q("A", lw), q("B", sw), red("C", "A"), red("D", "B"),
                 {"refId": "E", "datasourceUid": "__expr__", "model": {"refId": "E", "type": "math", "expression": f"$C > {policy.factor:g} && $D > {policy.factor:g}"}},
                 {"refId": "F", "datasourceUid": "__expr__", "model": {"refId": "F", "type": "threshold", "expression": "E", "conditions": [{"evaluator": {"type": "gt", "params": [0]}}]}}],
        "annotations": {"__dashboardUid__": dashboard_uid, "__panelId__": str(panel_id),
                        "summary": f"SLO {slo.name}: burn rate ≥ {policy.factor:g}× en {lw} y {sw}",
                        "description": (f"El SLO «{slo.description}» (objetivo {slo.objective:.2%}) consume presupuesto a ≥ {policy.factor:g}× el ritmo sostenible "
                                        f"en la ventana larga ({lw}) y en la corta ({sw}). Burn rate largo: {{{{ humanize $values.C.Value }}}}×."),
                        "runbook_url": runbook or f"https://example.com/runbooks/slo-{slo.name}"},
        "labels": {"severity": policy.severity, "team": team, "service": "supportops-agent", "slo": slo.name, **(receiver_labels or {})},
    }


def rules_yaml(rules: Sequence[dict[str, Any]], *, group: str = "supportops-slo", folder: str = "Curso observabilidad de agentes", interval: str = "30s",
               header: str = "") -> str:
    import yaml
    if int(interval.rstrip("s")) % 10 or not interval.endswith("s"):
        raise ValueError("el intervalo del grupo debe ser un múltiplo de 10 s (tick del planificador de Grafana)")
    doc = {"apiVersion": 1, "groups": [{"orgId": 1, "name": group, "folder": folder, "interval": interval, "rules": list(rules)}]}
    return header + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100000)


# =====================================================================================================================
# Postmortem sin culpa
# =====================================================================================================================
POSTMORTEM_SECTIONS = ("Resumen", "Impacto", "Cronología", "Causa raíz y factores contribuyentes", "Qué fue bien", "Qué fue mal", "Dónde hubo suerte", "Acciones")


def render_postmortem(d: Mapping[str, Any]) -> str:
    """Postmortem sin culpa en Markdown desde un diccionario (``title, summary, impact, timeline[(hora, evento)], root_cause, contributing,
    went_well, went_wrong, lucky, actions[(acción, responsable, plazo, tipo)]``). Sin nombres de personas en las causas: sistemas y procesos."""
    L = [f"# Postmortem · {d['title']}", "", f"**Estado:** {d.get('status', 'borrador')} · **Severidad:** {d.get('severity', 'SEV-2')} · **Autores:** {d.get('authors', 'equipo de plataforma')}", ""]
    L += ["## Resumen", d["summary"], "", "## Impacto"] + [f"- {x}" for x in d["impact"]] + ["", "## Cronología (hora simulada)"]
    L += ["| Hora | Evento |", "|---|---|"] + [f"| {h} | {e} |" for h, e in d["timeline"]]
    L += ["", "## Causa raíz y factores contribuyentes", d["root_cause"], ""] + [f"- {x}" for x in d.get("contributing", [])]
    L += ["", "## Qué fue bien"] + [f"- {x}" for x in d.get("went_well", [])] + ["", "## Qué fue mal"] + [f"- {x}" for x in d.get("went_wrong", [])]
    L += ["", "## Dónde hubo suerte"] + [f"- {x}" for x in d.get("lucky", [])] + ["", "## Acciones", "| Acción | Responsable | Plazo | Tipo |", "|---|---|---|---|"]
    L += [f"| {a} | {o} | {p} | {k} |" for a, o, p, k in d["actions"]]
    return "\n".join(L) + "\n"
