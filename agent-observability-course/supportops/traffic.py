"""Simulador de tráfico: usuarios sintéticos, llegadas con patrón diario, mezcla de intenciones y fallos inyectados.

Determinista: ``generate_tickets(seed=42)`` produce SIEMPRE los mismos tickets. Esquema en ``supportops.schema``.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from . import catalog
from .clock import SIM_EPOCH_S, stable_rng
from .models import AgentResult, FaultSpec, Ticket

INTENT_MIX = {"order_status": 0.35, "refund": 0.20, "kb_question": 0.35, "escalation": 0.10}

# Tasas base de fallos por ticket (entorno "con problemas normales"). fault_rates=None -> sin fallos.
DEFAULT_FAULT_RATES: dict[str, float] = {
    "latency_spike": 0.05, "llm_error": 0.03, "tool_error": 0.04, "tool_timeout": 0.01,
    "hallucination": 0.04, "tool_loop": 0.02, "pii_leak": 0.02,
}

TEMPLATES: dict[str, list[str]] = {
    "order_status": [
        "Hola, ¿dónde está mi pedido {oid}? Lo pedí hace unos días.",
        "Buenas, quiero saber el estado del pedido {oid}.",
        "¿Cuándo llega el pedido {oid}? Necesito el seguimiento.",
        "El envío {oid} sigue sin llegar, ¿me pueden decir algo?",
        "Pedido {oid}: ¿ya ha salido del almacén?",
        "Hola! tracking del pedido {oid} por favor",
    ],
    "refund": [
        "Quiero devolver el pedido {oid} y que me devuelvan el dinero.",
        "Me gustaría un reembolso del pedido {oid}, el producto no es lo que esperaba.",
        "Solicito la devolución de {oid}. ¿Cómo se tramita el reembolso?",
        "El {oid} llegó defectuoso. Quiero mi dinero de vuelta.",
        "Hola, quiero devolver un producto y no encuentro dónde. Es el pedido {oid}.",
        "Quiero un reembolso, pero no me acuerdo del número de pedido.",
    ],
    "kb_question": [
        "¿Cuántos años de garantía tienen los productos?",
        "¿Cuál es la política de devoluciones?",
        "¿Cuánto tarda el envío estándar y cuánto cuesta el urgente?",
        "Mi tarjeta gráfica parpadea tras instalarla, ¿cómo actualizo los drivers?",
        "¿Cómo configuro el router Wi-Fi 7 que compré?",
        "¿Puedo cambiar la dirección de entrega de mi pedido?",
        "¿Qué métodos de pago aceptan y cómo descargo la factura?",
        "¿La fuente de 750 W es compatible con mi tarjeta gráfica?",
        "¿Cómo actualizo el firmware del teclado mecánico?",
    ],
    "escalation": [
        "Esto es inaceptable, quiero hablar con una persona real ya.",
        "Voy a presentar una queja formal por el pedido {oid}. Pásenme con un supervisor.",
        "Quiero hablar con un humano, el bot no me entiende.",
        "Si no me solucionan lo del pedido {oid} acudiré a un abogado.",
    ],
}


@dataclass
class Incident:
    """Ventana temporal con una tasa elevada de un tipo de fallo (p. ej. «proveedor LLM degradado de 10:15 a 10:35»)."""
    name: str
    kind: str                       # uno de supportops.faults.FAULT_KINDS
    start_s: float                  # segundos desde el inicio del tráfico
    end_s: float
    prob: float = 0.8               # probabilidad de que un ticket dentro de la ventana sufra el fallo
    params: dict[str, Any] = field(default_factory=dict)


def _diurnal_times(rng, n: int, duration_s: float, start_s: float) -> list[float]:
    """n instantes con intensidad 1 + 0.5·sin(·) (pico a mitad de la ventana), por rechazo."""
    out: list[float] = []
    while len(out) < n:
        u = rng.random()
        if rng.random() <= (1 - 0.5 * math.cos(2 * math.pi * u)) / 1.5:
            out.append(start_s + u * duration_s)
    return sorted(out)


def _make_faults(rng, ticket_idx: int, t_off: float, fault_rates, incidents: Sequence[Incident], customer_ids: list[str],
                 cid: str) -> tuple[list[FaultSpec], str | None]:
    faults: list[FaultSpec] = []
    incident_name = None

    def params_for(kind: str, override: dict[str, Any] | None = None) -> dict[str, Any]:
        p: dict[str, Any]
        if kind == "latency_spike":
            p = {"factor": rng.choice([4.0, 6.0, 10.0]), "target": rng.choice(["llm", "tool", "both"])}
        elif kind == "llm_error":
            p = {"status": rng.choice([503, 503, 429, 500]), "at_call": 0, "persistent": rng.random() < 0.4}
        elif kind == "tool_error":
            p = {"tool": None, "error_type": "upstream_500"}
        elif kind == "tool_timeout":
            p = {"tool": None, "timeout_s": 5.0}
        elif kind == "pii_leak":
            victim = rng.choice([c for c in customer_ids if c != cid])
            p = {"victim": victim}
        else:
            p = {}
        p.update(override or {})
        return p

    for kind, rate in (fault_rates or {}).items():
        if rng.random() < rate:
            faults.append(FaultSpec(kind, params_for(kind)))
    for inc in incidents:
        if inc.start_s <= t_off < inc.end_s and rng.random() < inc.prob:
            if not any(f.kind == inc.kind for f in faults):
                faults.append(FaultSpec(inc.kind, params_for(inc.kind, inc.params)))
            else:
                for f in faults:
                    if f.kind == inc.kind:
                        f.params.update(inc.params)
            incident_name = inc.name
    return faults, incident_name


def generate_tickets(
    n: int = 200,
    seed: int = 42,
    duration_s: float = 3600.0,
    fault_rates: dict[str, float] | None = None,
    incidents: Sequence[Incident] = (),
    start_s: float | str = SIM_EPOCH_S,
    intent_mix: dict[str, float] | None = None,
    pii_rate: float = 0.06,
) -> list[Ticket]:
    """Genera ``n`` tickets ordenados en el tiempo. ``fault_rates=DEFAULT_FAULT_RATES`` activa fallos de fondo.

    ``start_s``: segundos unix de inicio. Por defecto ``SIM_EPOCH_S`` (2026-09-01T09:00Z, datos reproducibles y pregrabados).
    ``start_s="live"`` ancla la ventana para que TERMINE ahora: úsalo al enviar telemetría al stack real (Tempo/Loki
    rechazan o descartan datos muy antiguos; no envíes tiempos del pasado lejano).
    """
    if start_s == "live":
        start_s = time.time() - duration_s - 5.0
    rng = stable_rng("traffic", seed)
    mix = intent_mix or INTENT_MIX
    intents, weights = list(mix), list(mix.values())
    cids = list(catalog.customers())
    zipf = [1 / (i + 1) ** 1.1 for i in range(len(cids))]      # pocos clientes muy activos (cola larga)
    orders_by_customer: dict[str, list[str]] = {}
    for oid, o in catalog.orders().items():
        orders_by_customer.setdefault(o["customer_id"], []).append(oid)
    all_orders = list(catalog.orders())
    start_s = float(start_s)
    times = _diurnal_times(rng, n, duration_s, start_s)
    tickets: list[Ticket] = []
    for i, t in enumerate(times):
        cid = rng.choices(cids, weights=zipf)[0]
        cust = catalog.customers()[cid]
        intent = rng.choices(intents, weights=weights)[0]
        oid = rng.choice(orders_by_customer.get(cid) or all_orders)
        text = rng.choice(TEMPLATES[intent]).format(oid=oid)
        pii = rng.random() < pii_rate
        if pii:
            text += f" Mi correo es {cust['email']} y mi teléfono {cust['phone']}."
        faults, inc = _make_faults(rng, i, t - start_s, fault_rates, incidents, cids, cid)
        tickets.append(Ticket(
            ticket_id=f"T-{seed:02d}{i + 1:05d}", customer_id=cid, tier=cust["tier"],
            channel=rng.choices(["chat", "email", "web"], weights=[6, 2, 2])[0], text=text, intent_true=intent,
            created_at=round(t, 3), order_id=oid if oid in text else None,
            contains_pii=pii, faults=faults, incident=inc,
        ))
    return tickets


def run_tickets(agent, tickets: Iterable[Ticket]) -> list[AgentResult]:
    """Ejecuta el agente sobre los tickets, en orden. (Tiempo simulado: tarda milisegundos de pared.)"""
    return [agent.run(t) for t in tickets]


def to_rows(tickets: Sequence[Ticket], results: Sequence[AgentResult]) -> list[dict[str, Any]]:
    """Registros planos (uno por ticket) listos para ``pandas.DataFrame``. Esquema: ``schema.RUN_RECORD_SCHEMA``."""
    rows = []
    for t, r in zip(tickets, results):
        rows.append({
            "ticket_id": t.ticket_id, "customer_id": t.customer_id, "tier": t.tier, "channel": t.channel,
            "intent_true": t.intent_true, "intent_pred": r.intent_pred, "created_at": t.created_at,
            "contains_pii": t.contains_pii, "incident": t.incident,
            "status": r.status, "error_type": r.error_type, "latency_s": round(r.latency_s, 4),
            "n_llm_calls": r.n_llm_calls, "n_tool_calls": r.n_tool_calls, "tools_used": ",".join(r.tools_used),
            "input_tokens": r.input_tokens, "output_tokens": r.output_tokens, "cost_usd": r.cost_usd,
            "model": r.model, "provider": r.provider,
            "injected_faults": ",".join(r.injected_faults), "grounded": r.grounded, "pii_leaked": r.pii_leaked,
            "answer": r.answer,
        })
    return rows
