"""Esquemas documentados de los datos del curso (tráfico, registros de ejecución, spans y logs pregrabados)."""
from __future__ import annotations

from typing import Any

TICKET_SCHEMA: dict[str, str] = {
    "ticket_id": "str · «T-<seed 2 díg><n 5 díg>»",
    "customer_id": "str · «C-0001»..«C-0200» (distribución Zipf: pocos clientes muy activos)",
    "tier": "str · standard | premium",
    "channel": "str · chat | email | web",
    "text": "str · mensaje del cliente (español). Puede contener PII sintética si contains_pii=True",
    "intent_true": "str · order_status | refund | kb_question | escalation (verdad de terreno)",
    "created_at": "float · segundos unix SIMULADOS (origen 2026-09-01T09:00:00Z)",
    "order_id": "str|None · «ORD-00001»..«ORD-00600» si el texto lo menciona",
    "sku": "str|None · reservado",
    "contains_pii": "bool · el texto del cliente incluye correo/teléfono (sintéticos)",
    "faults": "list[{kind, params}] · fallos inyectados en este ticket (ver supportops.faults.FAULT_KINDS)",
    "incident": "str|None · nombre del incidente (ventana temporal) que originó el fallo",
}

RUN_RECORD_SCHEMA: dict[str, str] = {
    "ticket_id": "str", "customer_id": "str", "tier": "str", "channel": "str", "intent_true": "str",
    "intent_pred": "str|None · intención detectada por el mock",
    "created_at": "float · segundos unix simulados", "contains_pii": "bool", "incident": "str|None",
    "status": "str · ok | degraded | escalated | error | max_steps",
    "error_type": "str|None · server_error | rate_limit | timeout ...",
    "latency_s": "float · duración simulada del invoke_agent",
    "n_llm_calls": "int", "n_tool_calls": "int", "tools_used": "str · CSV",
    "input_tokens": "int", "output_tokens": "int", "cost_usd": "float · precios simulados (pricing.py)",
    "model": "str", "provider": "str",
    "injected_faults": "str · CSV de fallos realmente activados (ground truth)",
    "grounded": "bool · False si la respuesta contiene datos inventados",
    "pii_leaked": "bool · True si la respuesta contiene datos personales de otro cliente",
    "answer": "str",
}

SPAN_SCHEMA: dict[str, str] = {
    "trace_id": "str · 32 hex", "span_id": "str · 16 hex", "parent_span_id": "str|None",
    "name": "str · p. ej. «invoke_agent supportops-agent», «chat mock-small», «execute_tool get_order»",
    "kind": "str · INTERNAL | CLIENT", "start_unix_nano": "int", "end_unix_nano": "int",
    "status": "str · UNSET | OK | ERROR", "status_message": "str|None",
    "attributes": "dict · gen_ai.* (spec en estado Development) + supportops.*",
    "events": "list[{name, time_unix_nano, attributes}]",
    "resource": "dict · service.name='supportops-agent', service.version, deployment.environment.name",
    "scope": "str · nombre del instrumentation scope",
}

LOG_SCHEMA: dict[str, str] = {
    "time_unix_nano": "int", "severity_text": "str · INFO | WARN | ERROR", "severity_number": "int · 9 | 13 | 17",
    "body": "str", "attributes": "dict", "trace_id": "str|None", "span_id": "str|None", "resource": "dict",
}

METRIC_SCHEMA: dict[str, str] = {
    "minute": "int · minutos desde el inicio del tráfico", "requests": "int", "errors": "int",
    "p50_latency_s": "float", "p95_latency_s": "float", "input_tokens": "int", "output_tokens": "int", "cost_usd": "float",
}


def describe(schema: dict[str, str]) -> str:
    w = max(len(k) for k in schema)
    return "\n".join(f"{k:<{w}}  {v}" for k, v in schema.items())


def validate_ticket(d: dict[str, Any]) -> list[str]:
    """Devuelve la lista de problemas (vacía si el dict cumple el esquema mínimo)."""
    problems = [f"falta {k}" for k in ("ticket_id", "customer_id", "tier", "channel", "text", "intent_true", "created_at") if k not in d]
    if d.get("tier") not in (None, "standard", "premium"):
        problems.append("tier inválido")
    return problems
