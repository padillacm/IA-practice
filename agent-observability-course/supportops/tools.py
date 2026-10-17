"""Herramientas simuladas del agente (pedidos, reembolsos, base de conocimiento, escalado) y su registro.

Cada herramienta tiene: esquema (para el LLM), función, y una latencia simulada (lognormal con semilla).
Añadir una herramienta propia (módulo 01):

    registry.register(Tool(name="check_stock", description="...", parameters={...}, fn=mi_fn, latency_median_s=0.05))
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable

from . import catalog
from .kb import KnowledgeBase


class ToolError(Exception):
    """Fallo de infraestructura de una herramienta (equivale a un 5xx / timeout). ``error_type`` sigue la idea de ``error.type``."""

    def __init__(self, message: str, error_type: str = "tool_error", latency_s: float | None = None):
        super().__init__(message)
        self.error_type = error_type
        self.latency_s = latency_s          # tiempo simulado consumido antes de fallar (p. ej. un timeout)


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]                   # JSON Schema de los argumentos
    fn: Callable[..., Any]
    latency_median_s: float = 0.1                # mediana de la latencia simulada
    latency_sigma: float = 0.35                  # dispersión lognormal
    meta: dict[str, Any] = field(default_factory=dict)

    def schema(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "parameters": self.parameters}

    def sample_latency(self, rng) -> float:
        return self.latency_median_s * math.exp(rng.gauss(0.0, self.latency_sigma))


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> Tool:
        self._tools[tool.name] = tool
        return tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise ToolError(f"herramienta desconocida: {name}", "unknown_tool")
        return self._tools[name]

    def names(self) -> list[str]:
        return list(self._tools)

    def schemas(self) -> list[dict[str, Any]]:
        return [t.schema() for t in self._tools.values()]

    def __contains__(self, name: str) -> bool:
        return name in self._tools


# ----------------------------------------------------------------------------- herramientas por defecto
_KB = KnowledgeBase()


def get_order(order_id: str) -> dict[str, Any]:
    o = catalog.orders().get(order_id)
    if o is None:
        return {"found": False, "order_id": order_id}
    return {"found": True, **o}


def issue_refund(order_id: str, amount_eur: float, reason: str = "") -> dict[str, Any]:
    """Regla de negocio: solo pedidos entregados hace ≤ 30 días, importe ≤ total del pedido."""
    o = catalog.orders().get(order_id)
    if o is None:
        return {"approved": False, "reason": "order_not_found"}
    if o["status"] != "delivered":
        return {"approved": False, "reason": f"order_status_{o['status']}"}
    if (o["delivered_days_ago"] or 0) > 30:
        return {"approved": False, "reason": "outside_return_window"}
    if amount_eur > o["total_eur"] + 1e-9:
        return {"approved": False, "reason": "amount_exceeds_total"}
    return {"approved": True, "refund_id": f"RF-{order_id[-5:]}", "amount_eur": round(float(amount_eur), 2), "reason": reason}


def search_kb(query: str, k: int = 3) -> dict[str, Any]:
    return {"query": query, "results": _KB.search(query, int(k))}


def escalate_to_human(reason: str, priority: str = "normal") -> dict[str, Any]:
    return {"handoff_id": "HO-" + format(sum(map(ord, reason)) % 100000, "05d"), "queue": "tier2", "priority": priority}


def default_tools() -> ToolRegistry:
    r = ToolRegistry()
    r.register(Tool("get_order", "Consulta el estado de un pedido por su número (ORD-00000).",
                    {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]},
                    get_order, latency_median_s=0.08))
    r.register(Tool("issue_refund", "Emite un reembolso de un pedido entregado (máx. 30 días desde la entrega).",
                    {"type": "object", "properties": {"order_id": {"type": "string"}, "amount_eur": {"type": "number"},
                                                       "reason": {"type": "string"}},
                     "required": ["order_id", "amount_eur"]},
                    issue_refund, latency_median_s=0.30, latency_sigma=0.4))
    r.register(Tool("search_kb", "Busca en la base de conocimiento (políticas, garantía, guías de producto).",
                    {"type": "object", "properties": {"query": {"type": "string"}, "k": {"type": "integer"}},
                     "required": ["query"]},
                    search_kb, latency_median_s=0.05, latency_sigma=0.3))
    r.register(Tool("escalate_to_human", "Deriva el caso a una persona del equipo de soporte.",
                    {"type": "object", "properties": {"reason": {"type": "string"}, "priority": {"type": "string"}},
                     "required": ["reason"]},
                    escalate_to_human, latency_median_s=0.15))
    return r
