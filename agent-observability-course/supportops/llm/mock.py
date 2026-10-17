"""LLM simulado y determinista. Es el valor por defecto (``LLM_PROVIDER=mock``) y el que usan las rúbricas.

No es un modelo de lenguaje: es una *política por reglas* que decide qué herramienta llamar (según palabras clave
del ticket) y redacta la respuesta final con plantillas a partir de los resultados de las herramientas. Lo que SÍ
imita bien es el comportamiento observable de un LLM en producción: latencia (TTFT + tokens), conteo de tokens que
crece con el contexto, finish reasons, e identificadores de respuesta.

Extender con una herramienta nueva (módulo 01)::

    mock.add_rule(Rule("stock", keywords=("stock", "disponible"), steps=[ToolStep("check_stock", args=...)], answer=...))
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from ..clock import stable_hex, stable_rng
from ..config import get_settings
from ..models import LLMResponse, Message, ToolCall, Usage
from .base import count_tokens, messages_tokens

ORDER_RE = re.compile(r"ORD-\d{5}")
SKU_RE = re.compile(r"SKU-\d{4}")

# (mediana TTFT en s, s por token de salida, s por token de entrada)
MODEL_PROFILES: dict[str, tuple[float, float, float]] = {
    "mock-small": (0.35, 0.012, 0.00004),
    "mock-large": (0.70, 0.030, 0.00008),
}
NATURAL_TAIL_PROB = 0.02   # fracción de llamadas lentas "naturales" (cola pesada), sin fallo inyectado
NATURAL_TAIL_FACTOR = 3.0


def _first_sentences(text: str, n: int = 2) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(parts[:n])


@dataclass
class ToolStep:
    """Un paso de herramienta dentro de una regla. ``args(text, results)`` construye los argumentos."""
    tool: str
    args: Callable[[str, dict[str, Any]], dict[str, Any]]
    when: Callable[[str, dict[str, Any]], bool] = lambda text, results: True


@dataclass
class Rule:
    intent: str
    keywords: tuple[str, ...]
    steps: list[ToolStep]
    answer: Callable[[str, dict[str, Any]], str]
    needs: Callable[[str], bool] = lambda text: True        # requisito (p. ej. que haya número de pedido)
    missing_answer: str = "¿Puede indicarme el dato que falta para ayudarle?"
    clarify: bool = False                                   # si falta el requisito: True = pedir el dato; False = probar otra regla
    priority: int = 0                                       # mayor = se evalúa antes

    def score(self, text: str) -> int:
        low = text.lower()
        return sum(1 for k in self.keywords if k in low)


# ---------------------------------------------------------------- reglas por defecto
def _order_id(text: str) -> str:
    m = ORDER_RE.search(text)
    return m.group(0) if m else ""


def _ans_order_status(text: str, r: dict[str, Any]) -> str:
    o = r.get("get_order", {})
    if not o.get("found"):
        return f"No encuentro el pedido {_order_id(text)}. ¿Puede comprobar el número?"
    st = o["status"]
    if st == "delivered":
        return f"Su pedido {o['order_id']} figura como entregado (transportista {o['carrier']}, seguimiento {o['tracking']})."
    if st == "shipped":
        return (f"Su pedido {o['order_id']} está en camino con {o['carrier']} (seguimiento {o['tracking']}); "
                f"llegará en unos {o['eta_days']} días.")
    if st == "processing":
        return f"Su pedido {o['order_id']} se está preparando en el almacén; saldrá en {o['eta_days']} días aprox."
    return f"Su pedido {o['order_id']} está cancelado. Si no lo esperaba, puedo derivarle con una persona."


def _ans_refund(text: str, r: dict[str, Any]) -> str:
    o, rf = r.get("get_order", {}), r.get("issue_refund")
    if not o.get("found"):
        return f"No encuentro el pedido {_order_id(text)}, así que no puedo tramitar el reembolso."
    if rf is None:
        return (f"El pedido {o['order_id']} está en estado «{o['status']}» y todavía no se puede reembolsar. "
                "Si aún no lo ha recibido, puede cancelarlo o esperar a la entrega.")
    if rf.get("approved"):
        return (f"He aprobado el reembolso de {rf['amount_eur']:.2f} € del pedido {o['order_id']} "
                f"(ref. {rf['refund_id']}). Lo recibirá en 5 días laborables.")
    return (f"No he podido reembolsar el pedido {o['order_id']}: {rf.get('reason')}. "
            "Nuestra política permite devoluciones durante 30 días desde la entrega.")


def _ans_kb(text: str, r: dict[str, Any]) -> str:
    res = r.get("search_kb", {}).get("results", [])
    if not res:
        return "No he encontrado información sobre eso en nuestra base de conocimiento. ¿Quiere que le derive con una persona?"
    top = res[0]
    return f"Según «{top['title']}» ({top['doc_id']}): {_first_sentences(top['text'])}"


def _ans_escalate(text: str, r: dict[str, Any]) -> str:
    h = r.get("escalate_to_human", {})
    return f"Entiendo. He derivado su caso a una persona del equipo (ref. {h.get('handoff_id', 'HO-?')}); le contactará en breve."


def default_rules() -> list[Rule]:
    return [
        Rule("escalation", ("humano", "persona real", "queja", "abogado", "reclamación", "supervisor", "inaceptable", "denuncia"),
             [ToolStep("escalate_to_human", lambda t, r: {"reason": t[:120], "priority": "high"})], _ans_escalate, priority=30),
        Rule("refund", ("reembols", "devolver", "solicito la devol", "dinero"),
             [ToolStep("get_order", lambda t, r: {"order_id": _order_id(t)}),
              ToolStep("issue_refund",
                       lambda t, r: {"order_id": _order_id(t), "amount_eur": r["get_order"]["total_eur"], "reason": "solicitud del cliente"},
                       when=lambda t, r: r.get("get_order", {}).get("found") and r["get_order"]["status"] == "delivered")],
             _ans_refund, needs=lambda t: bool(_order_id(t)),
             missing_answer="Para tramitar el reembolso necesito su número de pedido (formato ORD-00000).", clarify=True, priority=20),
        Rule("order_status", ("pedido", "envío", "envio", "enviado", "seguimiento", "tracking", "llega", "dónde está", "estado"),
             [ToolStep("get_order", lambda t, r: {"order_id": _order_id(t)})], _ans_order_status,
             needs=lambda t: bool(_order_id(t)),
             missing_answer="¿Me indica su número de pedido (formato ORD-00000) para consultar el estado?", priority=10),
        Rule("kb_question", (), [ToolStep("search_kb", lambda t, r: {"query": t, "k": 3})], _ans_kb, priority=0),
    ]


def detect_rule(rules: list[Rule], text: str) -> Rule:
    """Elige la regla con mayor prioridad entre las que tienen alguna palabra clave; si no, la de fallback (sin keywords)."""
    cands = [r for r in rules if r.keywords and r.score(text) > 0]
    for r in sorted(cands, key=lambda r: (-r.priority, -r.score(text))):
        if r.needs(text) or r.clarify:
            return r
    fallback = [r for r in rules if not r.keywords]
    return fallback[0]


class MockLLM:
    provider = "mock"

    def __init__(self, model: str = "mock-small", seed: int | None = None, rules: list[Rule] | None = None):
        if model not in MODEL_PROFILES:
            raise ValueError(f"modelo mock desconocido: {model}; usa {list(MODEL_PROFILES)}")
        self.model = model
        self.seed = get_settings().seed if seed is None else seed
        self.rules = rules if rules is not None else default_rules()

    def add_rule(self, rule: Rule) -> None:
        self.rules.append(rule)

    # -- política ---------------------------------------------------------------------------------
    def _decide(self, messages: list[Message]) -> tuple[str, list[tuple[str, dict[str, Any]]], Rule]:
        user_text = next((m.content for m in messages if m.role == "user"), "")
        rule = detect_rule(self.rules, user_text)
        results: dict[str, Any] = {}
        n_done: dict[str, int] = {}
        for m in messages:
            if m.role == "tool" and m.name:
                n_done[m.name] = n_done.get(m.name, 0) + 1
                try:
                    results[m.name] = json.loads(m.content)
                except json.JSONDecodeError:
                    results[m.name] = {"error": m.content}
        if not rule.needs(user_text):
            return rule.missing_answer, [], rule
        for step in rule.steps:
            if n_done.get(step.tool, 0) >= 1:
                continue
            if not step.when(user_text, results):
                continue
            return "", [(step.tool, step.args(user_text, results))], rule
        if any(isinstance(v, dict) and v.get("error") for v in results.values()):
            return "Ahora mismo no puedo completar la gestión por un problema técnico. Voy a derivarle con una persona.", [], rule
        return rule.answer(user_text, results), [], rule

    # -- API --------------------------------------------------------------------------------------
    def chat(self, messages, tools=None, *, system=None, max_tokens: int = 512, temperature: float = 0.0,
             call_key: tuple = ("", 0)) -> LLMResponse:
        rng = stable_rng("mock-llm", self.seed, *call_key)
        text, calls, rule = self._decide(messages)
        tool_calls = [ToolCall(id="call_" + stable_hex(8, self.seed, *call_key, i), name=n, arguments=a)
                      for i, (n, a) in enumerate(calls)]
        in_tok = messages_tokens(messages, system, tools)
        out_tok = count_tokens(text) if text else sum(12 + count_tokens(json.dumps(c.arguments, ensure_ascii=False)) for c in tool_calls)
        finish = "length" if out_tok > max_tokens else ("tool_calls" if tool_calls else "stop")
        out_tok = min(out_tok, max_tokens)
        ttft, per_out, per_in = MODEL_PROFILES[self.model]
        lat = ttft * math.exp(rng.gauss(0, 0.25)) + out_tok * per_out * math.exp(rng.gauss(0, 0.15)) + in_tok * per_in
        if rng.random() < NATURAL_TAIL_PROB:
            lat *= NATURAL_TAIL_FACTOR
        return LLMResponse(
            content=text, tool_calls=tool_calls, usage=Usage(in_tok, out_tok), finish_reason=finish, model=self.model,
            provider="mock", latency_s=round(lat, 4), response_id="resp_" + stable_hex(12, self.seed, *call_key),
            meta={"intent": rule.intent},
        )
