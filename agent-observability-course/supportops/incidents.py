"""«Mesa de incidentes» (módulo 21): cinco incidentes de SupportOps generados con el agente REAL (mock, semilla fija) y entregados
**solo como telemetría** (spans, logs, métricas por minuto y un registro de cambios con ruido), sin pistas directas.

    from supportops import incidents as I
    b = I.build_incident("INC-A")                 # IncidentBundle: alert, spans, logs, metrics, changes, extra
    I.grade("INC-A", {"cause": "...", "start_min": 20, "end_min": 35, "culprit": "...", "evidence": {...}, "mitigation": "..."})

Casos (identificadores opacos; el orden NO revela el tipo): cascada de reintentos entre agentes, bucle de herramientas, regresión
silenciosa de prompt, tormenta de cardinalidad en métricas y trazas partidas por pérdida de contexto.

Honestidad: la verdad de cada caso está en este fichero (sistema de honor: no lo leas antes de diagnosticar) y los números salen de
simulaciones deterministas con el agente de SupportOps, no de un sistema real. Requiere ``[otel]``.
"""
from __future__ import annotations

import collections
import dataclasses
import hashlib
import statistics
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from .clock import stable_rng
from .traffic import SIM_EPOCH_S, Incident, generate_tickets

CASE_IDS = ["INC-A", "INC-B", "INC-C", "INC-D", "INC-E"]
MINUTES = 60

CAUSES: dict[str, str] = {
    "provider_outage": "El proveedor de LLM devuelve errores (5xx/429) de forma generalizada.",
    "traffic_spike": "Un pico de tráfico legítimo satura el sistema.",
    "dependency_timeout_retry_storm": "Una dependencia aguas abajo (herramienta/agente) agota plazos y los reintentos amplifican la carga.",
    "tool_loop": "El agente repite la misma llamada a una herramienta hasta agotar los pasos.",
    "silent_prompt_regression": "Una versión del prompt/modelo cambia el comportamiento sin errores ni latencia anormal (el agente deja de consultar herramientas).",
    "metric_label_cardinality": "Una etiqueta con valores casi únicos en una métrica multiplica las series activas.",
    "context_propagation_broken": "Se pierde la propagación de contexto W3C entre servicios y las trazas se parten.",
    "collector_backpressure": "El Collector/backends rechazan o descartan telemetría por saturación.",
    "model_latency_regression": "El modelo responde más despacio (latencia del proveedor) sin errores.",
    "pii_leak": "El agente filtra datos personales en sus respuestas.",
}
MITIGATIONS: dict[str, str] = {
    "rollback_release": "Revertir el último despliegue.",
    "circuit_breaker_fallback": "Disyuntor + degradación (derivar a humano) y reducir reintentos con plazo propagado.",
    "loop_guard": "Tope de llamadas repetidas por herramienta (LoopGuard) y aborto del bucle.",
    "drop_label_collector": "Eliminar la etiqueta problemática (procesador del Collector / vista del SDK) y reiniciar la serie.",
    "restore_propagation": "Restaurar la propagación de `traceparent` (cabeceras/librería de transporte).",
    "switch_provider": "Cambiar de proveedor/modelo.",
    "scale_out": "Escalar horizontalmente.",
    "raise_timeouts": "Subir los plazos (timeouts).",
}


@dataclass
class IncidentBundle:
    case_id: str
    alert: str                              # texto neutral de la alerta que despertó a la guardia
    t0: float                               # segundos unix del minuto 0
    minutes: int
    spans: list[dict[str, Any]]             # esquema SPAN_SCHEMA (+ resource.service.name en ``resource``)
    logs: list[dict[str, Any]]              # esquema LOG_SCHEMA
    metrics: list[dict[str, Any]]           # una fila por minuto (columnas según el caso)
    changes: list[dict[str, Any]]           # registro de cambios: minuto, tipo, servicio, descripción (¡con ruido!)
    extra: dict[str, Any] = field(default_factory=dict)

    def minute_of(self, unix_nano: int) -> int:
        return int((unix_nano / 1e9 - self.t0) // 60)

    def summary(self) -> str:
        return (f"{self.case_id}: {len(self.spans)} spans · {len(self.logs)} logs · {len(self.metrics)} filas de métricas · {len(self.changes)} cambios\n"
                f"ALERTA: {self.alert}")


# =====================================================================================================================
# Utilidades de análisis (las usa la solución de referencia; son públicas por si las quieres reutilizar)
# =====================================================================================================================
def pct(xs: Sequence[float], q: float) -> float:
    xs = sorted(xs)
    if not xs:
        return float("nan")
    k = (len(xs) - 1) * q / 100
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def find_window(x: Sequence[float], min_len: int = 5) -> tuple[int, int, float]:
    """Ventana ``[a, b)`` cuya media difiere más del resto (estadístico t; ``min_len`` minutos dentro y fuera). Con ~4 tickets/min el ruido por minuto es alto: esto
    detecta saltos y ventanas sin umbrales. Si la mejor ventana empieza en 0 y no cubre la serie se devuelve su complemento ``(b, n)``."""
    import numpy as np
    x = np.asarray(x, float)
    n = len(x)
    sd = x.std() or 1.0
    c = np.concatenate([[0], np.cumsum(x)])
    best, win = 0.0, (0, n)
    for a in range(0, n - min_len + 1):
        for b in range(a + min_len, n + 1):
            n_in, n_out = b - a, n - (b - a)
            if n_out < min_len:
                continue
            m_in, m_out = (c[b] - c[a]) / n_in, (c[n] - (c[b] - c[a])) / n_out
            t = (m_in - m_out) / (sd * np.sqrt(1 / n_in + 1 / n_out))
            if abs(t) > abs(best):
                best, win = t, (a, b)
    if win[0] == 0 and win[1] < n:
        win = (win[1], n)
    return win[0], win[1], float(best)


def minute_table(rows: Sequence[Mapping[str, Any]], t0: float, minutes: int = MINUTES, *, status_key: str = "status", lat_key: str = "latency_s", cost_key: str = "cost_usd",
                 start_key: str = "start_s", extra: Mapping[str, Callable[[list], float]] | None = None) -> list[dict[str, Any]]:
    """Resume filas por ticket en una fila por minuto: n, error_rate (``error|degraded|max_steps``), p95_s, cost_per_ticket, y columnas extra."""
    by: dict[int, list] = collections.defaultdict(list)
    for r in rows:
        m = int((r[start_key] - t0) // 60)
        if 0 <= m < minutes:
            by[m].append(r)
    out = []
    for m in range(minutes):
        g = by.get(m, [])
        row = {"minute": m, "n": len(g), "error_rate": (sum(r[status_key] in ("error", "degraded", "max_steps") for r in g) / len(g)) if g else 0.0,
               "p95_s": round(pct([r[lat_key] for r in g], 95), 3) if g else 0.0,
               "cost_per_ticket": round(statistics.mean(r[cost_key] for r in g), 6) if g else 0.0}
        for k, fn in (extra or {}).items():
            row[k] = round(fn(g), 4) if g else 0.0
        out.append(row)
    return out


def trace_table(spans: Sequence[Mapping[str, Any]], t0: float) -> list[dict[str, Any]]:
    """Una fila por traza: raíz, nº de servicios, nº de spans, nº de ``chat``, nº de ``execute_tool``, tokens de las hojas ``chat`` y minuto de inicio."""
    by: dict[str, list] = collections.defaultdict(list)
    for s in spans:
        by[s["trace_id"]].append(s)
    rows = []
    for tid, ss in by.items():
        ids = {s["span_id"] for s in ss}
        roots = [s for s in ss if not s["parent_span_id"] or s["parent_span_id"] not in ids]
        root = min(roots, key=lambda s: s["start_unix_nano"]) if roots else ss[0]
        chats = [s for s in ss if s["name"].startswith("chat")]
        tools = [s for s in ss if s["name"].startswith("execute_tool")]
        rows.append({"trace_id": tid, "root": root["name"], "root_has_parent": bool(root["parent_span_id"]), "n_services": len({(s.get("resource") or {}).get("service.name") for s in ss}),
                     "n_spans": len(ss), "n_chat": len(chats), "n_tools": len(tools), "tools": [s["name"].split(" ", 1)[1] for s in sorted(tools, key=lambda s: s["start_unix_nano"])],
                     "tokens": sum(int(c["attributes"].get("gen_ai.usage.input_tokens", 0)) + int(c["attributes"].get("gen_ai.usage.output_tokens", 0)) for c in chats),
                     "start_min": int((root["start_unix_nano"] / 1e9 - t0) // 60), "error": any(s["status"] == "ERROR" for s in ss)})
    return sorted(rows, key=lambda r: r["start_min"])


def _rows_single(tickets, results):
    from .traffic import to_rows
    return to_rows(tickets, results)


def _bundle_telemetry(tel_or_mesh) -> tuple[list[dict], list[dict]]:
    spans = tel_or_mesh.span_records()
    logs = tel_or_mesh.log_records()
    return spans, logs


def _noise_changes(rng, minutes: int, k: int = 3) -> list[dict[str, Any]]:
    pool = [("config", "grafana", "Actualiza el dashboard «Salud del agente» (paneles de coste)"), ("deploy", "supportops-knowledge-agent", "Nueva versión: ajusta el texto de los snippets de la KB"),
            ("config", "prometheus", "Rota los TLS del scrape de métricas"), ("deploy", "docs-site", "Publica la nueva guía de devoluciones (web pública)"),
            ("infra", "loki", "Compactación programada"), ("flag", "supportops-agent", "Activa la nueva cabecera de respuesta HTML (marca)"),
            ("config", "otel-collector", "Recarga la configuración (sin cambios de procesadores)"), ("infra", "kafka-billing", "Mantenimiento planificado de brokers (sin impacto esperado)")]
    picks = rng.sample(pool, k)
    return [{"minute": rng.randint(2, minutes - 3), "kind": a, "service": b, "desc": c} for a, b, c in picks]


# =====================================================================================================================
# Generadores de los cinco incidentes
# =====================================================================================================================
# ``variant="mesa"`` = los incidentes del proyecto; ``variant="lesson"`` = manifestaciones DISTINTAS de las mismas familias de fallo, para los ejemplos
# resueltos de la lección (otro agente afectado, otras ventanas, otra etiqueta), de modo que la mesa no quede «gastada».
PARAMS: dict[str, dict[str, dict[str, Any]]] = {
    "mesa": {"INC-A": {"agent": "billing-agent", "start": 20, "end": 35, "tool": "get_order"}, "INC-B": {"start": 25, "end": 45, "prob": 0.5},
             "INC-C": {"rollout_start": 15, "full_at": 30, "canary": 0.25}, "INC-D": {"change": 30, "label": "customer_id"}, "INC-E": {"break": 20}},
    "lesson": {"INC-A": {"agent": "orders-agent", "start": 25, "end": 40, "tool": "get_order"}, "INC-B": {"start": 32, "end": 50, "prob": 0.45},
               "INC-C": {"rollout_start": 22, "full_at": 22, "canary": 1.0}, "INC-D": {"change": 35, "label": "conversation_id"}, "INC-E": {"break": 28}},
}
def _mesh_run(seed: int, n: int, incidents: Sequence[Incident], propagation_by_minute: Callable[[float], str], policy=None, fault_rates=None):
    from .multiagent import DelegationPolicy, MultiAgentSupportOps, build_mesh
    mesh = build_mesh(mode="memory")
    pol = policy or DelegationPolicy(timeout_s=6.0, max_retries=2, backoff_s=0.5)
    systems = {p: MultiAgentSupportOps(mesh, mode="delegate", policy=pol, propagation=p) for p in ("sdk", "none")}
    tickets = generate_tickets(n, seed, duration_s=MINUTES * 60, fault_rates=fault_rates or {"latency_spike": 0.02, "llm_error": 0.01, "tool_error": 0.01}, incidents=list(incidents), pii_rate=0.0)
    t0 = SIM_EPOCH_S
    results = []
    for t in tickets:
        results.append((t, systems[propagation_by_minute((t.created_at - t0) / 60)].run(t)))
    mesh.force_flush()
    return mesh, results


def _gen_cascade(seed: int, n: int, prm: Mapping[str, Any]) -> IncidentBundle:
    rng = stable_rng("incident-A", seed)
    inc = Incident("dependency-timeouts", "tool_timeout", prm["start"] * 60, prm["end"] * 60, 1.0, {"tool": prm["tool"], "timeout_s": 8.0, "agent": prm["agent"], "sticky": True})
    mesh, res = _mesh_run(seed, n, [inc], lambda m: "sdk")
    rows = [dict(r.to_row(), tier=t.tier, intent_true=t.intent_true) for t, r in res]
    metrics = minute_table(rows, SIM_EPOCH_S, extra={"attempts_per_ticket": lambda g: statistics.mean(r["attempts"] for r in g), "timeouts": lambda g: sum(r["timeouts"] for r in g),
                                                       "escalated_share": lambda g: sum(r["status"] == "escalated" for r in g) / len(g)})
    spans, logs = _bundle_telemetry(mesh)
    changes = _noise_changes(rng, MINUTES, 3) + [{"minute": 18, "kind": "deploy", "service": "llm-gateway", "desc": "Ajusta límites de tasa por cliente (config)"}]
    b = IncidentBundle("INC-A", "ALERTA: p95 de invoke_workflow > 8 s durante 5 min y subida de escalados a humano. Los errores 5xx del proveedor LLM no han cambiado.", SIM_EPOCH_S, MINUTES, spans, logs, metrics,
                       sorted(changes, key=lambda c: c["minute"]), {"tickets": rows, "params": dict(prm)})
    mesh.shutdown()
    return b


def loop_tickets(seed: int = 42, n: int = 240, variant: str = "mesa"):
    """Los tickets (con los fallos inyectados) del incidente de bucle: sirven para **re-ejecutar** el incidente con una mitigación y medir su efecto."""
    prm = PARAMS[variant]["INC-B"]
    inc = Incident("loop", "tool_loop", prm["start"] * 60, prm["end"] * 60, prm["prob"], {})
    return generate_tickets(n, seed, duration_s=MINUTES * 60, fault_rates={"latency_spike": 0.02, "llm_error": 0.01, "tool_error": 0.01}, incidents=[inc], pii_rate=0.0)


def _gen_loop(seed: int, n: int, prm: Mapping[str, Any]) -> IncidentBundle:
    from .agent import SupportAgent
    from .telemetry import OTelInstrumentor, setup_telemetry
    rng = stable_rng("incident-B", seed)
    tickets = loop_tickets(seed, n, "lesson" if prm is PARAMS["lesson"]["INC-B"] else "mesa")
    tel = setup_telemetry("supportops-agent", mode="memory", set_global=False, metrics=False)
    agent = SupportAgent(instrumentor=OTelInstrumentor(tel, emit_metrics=False), max_steps=6)
    results = [agent.run(t) for t in tickets]
    tel.force_flush()
    rows = _rows_single(tickets, results)
    metrics = minute_table(rows, SIM_EPOCH_S, start_key="created_at", extra={"llm_calls_per_ticket": lambda g: statistics.mean(r["n_llm_calls"] for r in g), "tool_calls_per_ticket": lambda g: statistics.mean(r["n_tool_calls"] for r in g),
                                                     "max_steps_share": lambda g: sum(r["status"] == "max_steps" for r in g) / len(g)})
    spans, logs = tel.span_records(), tel.log_records()
    changes = _noise_changes(rng, MINUTES, 3) + [{"minute": prm["start"] - 1, "kind": "deploy", "service": "kb-search", "desc": "Reindexación de la base de conocimiento (índice nuevo)"}]
    b = IncidentBundle("INC-B", "ALERTA: coste por ticket ≥ 2× la línea base durante 10 min y la tasa de tickets sin resolver crece. La latencia del proveedor LLM es normal.", SIM_EPOCH_S, MINUTES, spans, logs, metrics,
                       sorted(changes, key=lambda c: c["minute"]), {"tickets": rows, "params": dict(prm)})
    tel.shutdown()
    return b


def _gen_silent(seed: int, n: int, prm: Mapping[str, Any]) -> IncidentBundle:
    from .quality_eval import VersionTagInstrumentor
    from .regression import make_agent
    from .telemetry import OTelInstrumentor, setup_telemetry
    rng = stable_rng("incident-C", seed)
    tickets = generate_tickets(n, seed, duration_s=MINUTES * 60, fault_rates={"latency_spike": 0.02, "llm_error": 0.01, "tool_error": 0.01}, pii_rate=0.0)
    tel = setup_telemetry("supportops-agent", mode="memory", set_global=False, metrics=False)
    agents = {v: make_agent(v, instrumentors=[OTelInstrumentor(tel, emit_metrics=False), VersionTagInstrumentor(v)])[0] for v in ("v1", "v2")}
    rollout = lambda m: 0.0 if m < prm["rollout_start"] else (prm["canary"] if m < prm["full_at"] else 1.0)
    results, versions, grounded = [], {}, {}
    for t in tickets:
        m = (t.created_at - SIM_EPOCH_S) / 60
        v = "v2" if stable_rng("rollout", seed, t.ticket_id).random() < rollout(m) else "v1"
        r = agents[v].run(t)
        results.append(r)
        versions[t.ticket_id] = v
        grounded[t.ticket_id] = r.grounded
    tel.force_flush()
    rows = _rows_single(tickets, results)
    for r in rows:
        r["version"] = versions[r["ticket_id"]]
        fb = stable_rng("feedback", seed, r["ticket_id"])
        r["thumbs_down"] = int(fb.random() < (0.30 if not grounded[r["ticket_id"]] else 0.04))      # feedback SINTÉTICO: los inventados molestan más
    metrics = minute_table(rows, SIM_EPOCH_S, start_key="created_at", extra={"thumbs_down_rate": lambda g: sum(r["thumbs_down"] for r in g) / len(g), "tool_calls_per_ticket": lambda g: statistics.mean(r["n_tool_calls"] for r in g)})
    spans, logs = tel.span_records(), tel.log_records()
    changes = _noise_changes(rng, MINUTES, 3) + [{"minute": prm["rollout_start"], "kind": "deploy", "service": "supportops-agent", "desc": "Despliegue de la versión de prompt «v2» (progresivo)" if prm["canary"] < 1 else "Despliegue de la versión de prompt «v2» (100 %)"}]
    b = IncidentBundle("INC-C", "AVISO (ticket): las valoraciones negativas de los clientes (👎) suben ≈ 60 % frente a ayer. No hay alertas de errores ni de latencia.", SIM_EPOCH_S, MINUTES, spans, logs, metrics,
                       sorted(changes, key=lambda c: c["minute"]), {"tickets": [{k: v for k, v in r.items() if k != "grounded"} for r in rows], "params": dict(prm)})
    tel.shutdown()
    return b


def _gen_cardinality(seed: int, n: int, prm: Mapping[str, Any]) -> IncidentBundle:
    from .agent import SupportAgent
    rng = stable_rng("incident-D", seed)
    n = max(n, 480)
    tickets = generate_tickets(n, seed, duration_s=MINUTES * 60, fault_rates={"latency_spike": 0.02, "llm_error": 0.04, "tool_error": 0.03}, pii_rate=0.0)
    agent = SupportAgent()
    results = [agent.run(t) for t in tickets]
    rows = _rows_single(tickets, results)
    CHANGE, LABEL = prm["change"], prm["label"]
    inventory = [{"metric": "supportops_agent_requests_total", "type": "counter", "labels_before": ["status", "intent", "tier"], "labels_after": ["status", "intent", "tier", LABEL], "series_per_combination": 1},
                 {"metric": "supportops_agent_request_duration_seconds", "type": "histogram", "labels_before": ["intent"], "labels_after": ["intent", LABEL], "series_per_combination": 14},
                 {"metric": "supportops_llm_cost_usd_total", "type": "counter", "labels_before": ["model"], "labels_after": ["model"], "series_per_combination": 1}]
    series_rows, label_values = [], {}
    STALE = 5
    for m in range(MINUTES):
        window = [r for r in rows if m - STALE < (r["created_at"] - SIM_EPOCH_S) / 60 <= m + 1]
        after = m >= CHANGE
        for inv in inventory:
            labels = inv["labels_after"] if after else inv["labels_before"]
            combos = {tuple(r.get({"status": "status", "intent": "intent_true", "tier": "tier", "customer_id": "customer_id", "conversation_id": "ticket_id", "model": "model"}[l]) for l in labels) for r in window}
            series_rows.append({"minute": m, "metric": inv["metric"], "active_series": len(combos) * inv["series_per_combination"]})
            if m in (CHANGE - 5, 55):
                label_values.setdefault(m, {})[inv["metric"]] = {l: len({r.get({"status": "status", "intent": "intent_true", "tier": "tier", "customer_id": "customer_id", "conversation_id": "ticket_id", "model": "model"}[l]) for r in window}) for l in labels}
    total = collections.defaultdict(int)
    for s in series_rows:
        total[s["minute"]] += s["active_series"]
    metrics = []
    for m in range(MINUTES):
        g = [r for r in rows if int((r["created_at"] - SIM_EPOCH_S) // 60) == m]
        series = total[m]
        metrics.append({"minute": m, "requests": len(g), "active_series": series, "scrape_duration_s": round(0.08 + series * 0.00035, 3), "prometheus_rss_mb": round(310 + series * 0.0028 * 1024 / 1024 * 1.0, 1),
                        "ingest_samples_per_s": round(series / 15, 1), "error_rate": round(sum(r["status"] in ("error", "degraded", "max_steps") for r in g) / max(len(g), 1), 4)})
    changes = _noise_changes(rng, MINUTES, 3) + [{"minute": CHANGE - 1, "kind": "deploy", "service": "supportops-agent", "desc": "Release 0.1.0-rc3: cambios de instrumentación (atributos de métricas y dashboards)"}]
    b = IncidentBundle("INC-D", "ALERTA: memoria de Prometheus al 85 %, duración del scrape > 10 s y series activas ×6 en 30 minutos. El tráfico es normal.", SIM_EPOCH_S, MINUTES, [], [], metrics,
                       sorted(changes, key=lambda c: c["minute"]), {"series_by_metric": series_rows, "metric_inventory": inventory, "label_values": label_values,
                                                                      "params": dict(prm), "note": "Valores de memoria y duración de scrape: modelo simple (≈ 2,8 KB/serie, medido en el módulo 18) — no de un Prometheus real."})
    return b


def _gen_broken(seed: int, n: int, prm: Mapping[str, Any]) -> IncidentBundle:
    rng = stable_rng("incident-E", seed)
    BREAK = prm["break"]
    mesh, res = _mesh_run(seed, n, [], lambda m: "sdk" if m < BREAK else "none", fault_rates={"latency_spike": 0.02, "llm_error": 0.01})
    rows = [dict(r.to_row(), tier=t.tier, intent_true=t.intent_true) for t, r in res]
    spans, logs = _bundle_telemetry(mesh)
    tt = trace_table(spans, SIM_EPOCH_S)
    by_min: dict[int, list] = collections.defaultdict(list)
    for r in tt:
        by_min[r["start_min"]].append(r)
    metrics = []
    for m in range(MINUTES):
        g = by_min.get(m, [])
        k = [r for r in rows if int((r["start_s"] - SIM_EPOCH_S) // 60) == m]
        metrics.append({"minute": m, "tickets": len(k), "traces": len(g), "traces_per_ticket": round(len(g) / max(len(k), 1), 3), "spans_per_trace": round(statistics.mean(r["n_spans"] for r in g), 2) if g else 0.0,
                        "cost_per_trace_tokens": round(statistics.mean(r["tokens"] for r in g), 1) if g else 0.0, "error_rate": round(sum(r["status"] in ("error", "degraded") for r in k) / max(len(k), 1), 4),
                        "p95_s": round(pct([r["end_s"] - r["start_s"] for r in k], 95), 3) if k else 0.0})
    changes = _noise_changes(rng, MINUTES, 3) + [{"minute": BREAK, "kind": "infra", "service": "ingress-gateway", "desc": "Actualización de la imagen base del gateway interno (sin cambios funcionales anunciados)"},
                                                  {"minute": BREAK + 1, "kind": "config", "service": "otel-collector", "desc": "Recarga de configuración"}]
    b = IncidentBundle("INC-E", "AVISO: las aristas del grafo de servicios (orquestador → agentes) desaparecen y «coste por traza» cae ≈ 60 %. No hay errores ni cambios de latencia.", SIM_EPOCH_S, MINUTES, spans, logs, metrics,
                       sorted(changes, key=lambda c: c["minute"]), {"tickets": rows, "params": dict(prm)})
    mesh.shutdown()
    return b


_GENERATORS = {"INC-A": _gen_cascade, "INC-B": _gen_loop, "INC-C": _gen_silent, "INC-D": _gen_cardinality, "INC-E": _gen_broken}
_CACHE: dict[tuple, IncidentBundle] = {}


def build_incident(case_id: str, seed: int = 42, n: int = 240, variant: str = "mesa") -> IncidentBundle:
    """Genera (y cachea) el incidente. Determinista para la misma ``seed``. ``variant="lesson"``: ejemplos resueltos de la lección (no se corrigen con ``grade``)."""
    if case_id not in _GENERATORS:
        raise KeyError(f"caso desconocido {case_id}; usa uno de {CASE_IDS}")
    key = (case_id, seed, n, variant)
    if key not in _CACHE:
        _CACHE[key] = _GENERATORS[case_id](seed, n, PARAMS[variant][case_id])
    return _CACHE[key]


# =====================================================================================================================
# Corrección (sistema de honor): la verdad vive aquí; no la leas antes de diagnosticar
# =====================================================================================================================
def _h(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


_TRUTH = {"INC-A": ("dependency_timeout_retry_storm", (20, 35), "supportops-billing-agent", {"circuit_breaker_fallback"}),
          "INC-B": ("tool_loop", (25, 45), None, {"loop_guard", "rollback_release"}),
          "INC-C": ("silent_prompt_regression", (15, 59), "v2", {"rollback_release"}),
          "INC-D": ("metric_label_cardinality", (30, 59), "customer_id", {"drop_label_collector", "rollback_release"}),
          "INC-E": ("context_propagation_broken", (20, 59), None, {"restore_propagation", "rollback_release"})}
_KEYS = {k: _h(k, v[0]) for k, v in _TRUTH.items()}


def reference_facts(case_id: str, b: IncidentBundle | None = None) -> dict[str, Any]:
    """Cifras de verdad calculadas con el método de referencia sobre los datos del paquete (las usa ``grade`` con tolerancia)."""
    b = b or build_incident(case_id)
    prm = b.extra.get("params") or PARAMS["mesa"][case_id]
    if case_id == "INC-A":
        tt = {r["trace_id"]: r["start_min"] for r in trace_table(b.spans, b.t0)}
        att = collections.Counter()
        for s in b.spans:
            if s["name"] == f"invoke_agent {prm['agent']}" and s["kind"] == "CLIENT":
                att[s["trace_id"]] += 1
        inw = [v for t, v in att.items() if prm["start"] <= tt[t] < prm["end"]]
        out = [v for t, v in att.items() if tt[t] < prm["start"]]
        return {"retry_amplification": statistics.mean(inw) / statistics.mean(out), "culprit": f"supportops-{prm['agent']}"}
    if case_id == "INC-B":
        tt = trace_table(b.spans, b.t0)
        loops = [r for r in tt if r["n_tools"] >= 5 and len(set(r["tools"])) == 1]
        tool = collections.Counter(r["tools"][0] for r in loops).most_common(1)[0][0]
        cost = lambda lo, hi: statistics.mean(r["cost_usd"] for r in b.extra["tickets"] if lo <= (r["created_at"] - b.t0) / 60 < hi)
        return {"loop_traces": len(loops), "cost_ratio": cost(prm["start"], prm["end"]) / cost(0, prm["start"]), "culprit": tool}
    if case_id == "INC-C":
        rows = [r for r in b.extra["tickets"] if r["intent_true"] in ("order_status", "refund")]
        share = lambda lo, hi: statistics.mean(r["n_tool_calls"] == 0 for r in rows if lo <= (r["created_at"] - b.t0) / 60 < hi)
        return {"no_tool_share_before": share(0, prm["rollout_start"]), "no_tool_share_after": share(max(prm["full_at"], prm["rollout_start"]), 60), "culprit": "v2"}
    if case_id == "INC-D":
        m = b.metrics
        before = statistics.mean(r["active_series"] for r in m[prm["change"] - 10:prm["change"] - 1]); after = statistics.mean(r["active_series"] for r in m[-5:])
        return {"series_growth": after / before, "culprit": prm["label"]}
    if case_id == "INC-E":
        tt = trace_table(b.spans, b.t0)
        after = [r for r in tt if r["start_min"] >= prm["break"] + 2]
        return {"orphan_share_after": statistics.mean(not (r["root"].startswith("invoke_workflow")) for r in after), "culprit": None}
    raise KeyError(case_id)


_TOL = {"retry_amplification": 0.25, "cost_ratio": 0.25, "loop_traces": 0.30, "series_growth": 0.30, "no_tool_share_after": 0.35, "orphan_share_after": 0.10, "no_tool_share_before": 0.60}


def grade(case_id: str, diagnosis: Mapping[str, Any], bundle: IncidentBundle | None = None) -> dict[str, Any]:
    """Corrige un diagnóstico ``{"cause", "start_min", "end_min", "culprit", "evidence": {...}, "mitigation"}``.

    Puntúa 5 comprobaciones: causa raíz (clave de ``CAUSES``), ventana (inicio ±4 min), culpable (servicio/etiqueta/versión/herramienta), evidencia numérica (tolerancia
    relativa: 25-35 %) y mitigación. ``evidence`` usa las claves de ``reference_facts`` del caso (se listan en ``evidence_keys``)."""
    cause, window, culprit_true, mits = _TRUTH[case_id]
    facts = reference_facts(case_id, bundle)
    ev = diagnosis.get("evidence") or {}
    ev_keys = [k for k in facts if k not in ("culprit", "no_tool_share_before")]
    ev_ok = {}
    for k in ev_keys:
        v, t = ev.get(k), facts[k]
        ev_ok[k] = v is not None and abs(float(v) - t) <= _TOL.get(k, 0.3) * max(abs(t), 1e-9) + (0.03 if t < 0.2 else 0.0)
    culprit_ok = culprit_true is None or str(diagnosis.get("culprit", "")).lower() == str(facts.get("culprit", culprit_true)).lower()
    if case_id == "INC-B":                                     # el culpable (herramienta) se deduce de los datos
        culprit_ok = str(diagnosis.get("culprit", "")).lower() == str(facts["culprit"]).lower()
    checks = {"causa raíz": _h(case_id, str(diagnosis.get("cause"))) == _KEYS[case_id], "inicio ±4 min": abs(int(diagnosis.get("start_min", -99)) - window[0]) <= 4,
              "culpable": culprit_ok, "evidencia numérica": all(ev_ok.values()) and bool(ev_ok), "mitigación": diagnosis.get("mitigation") in mits}
    return {"case": case_id, "checks": checks, "score": sum(checks.values()), "of": len(checks), "evidence_detail": ev_ok, "evidence_keys": ev_keys}


def evidence_keys(case_id: str) -> list[str]:
    return [k for k in reference_facts(case_id) if k not in ("culprit", "no_tool_share_before")]


__all__ = ["find_window", "PARAMS", "loop_tickets", "CASE_IDS", "CAUSES", "MITIGATIONS", "IncidentBundle", "build_incident", "grade", "reference_facts", "evidence_keys", "minute_table", "trace_table", "pct"]
