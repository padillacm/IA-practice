"""Tipos de datos compartidos (dataclasses simples, serializables a JSON con ``to_dict``)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ToolCall:
    """Petición del modelo de ejecutar una herramienta."""
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0

    def __iadd__(self, other: "Usage") -> "Usage":
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        return self

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class Message:
    """Mensaje de la conversación. role: system | user | assistant | tool."""
    role: str
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)  # solo en role=assistant
    tool_call_id: str | None = None                            # solo en role=tool
    name: str | None = None                                    # nombre de la herramienta (role=tool)


@dataclass
class LLMResponse:
    """Respuesta normalizada de cualquier proveedor."""
    content: str
    tool_calls: list[ToolCall]
    usage: Usage
    finish_reason: str               # "stop" | "tool_calls" | "length"
    model: str
    provider: str
    latency_s: float                 # latencia SIMULADA (mock) o medida (proveedores reales)
    response_id: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class FaultSpec:
    """Un fallo inyectado en un ticket. kind ∈ supportops.faults.FAULT_KINDS."""
    kind: str
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Ticket:
    """Ticket de soporte sintético. Esquema documentado en supportops.schema.TICKET_SCHEMA."""
    ticket_id: str
    customer_id: str
    tier: str                        # "standard" | "premium"
    channel: str                     # "chat" | "email" | "web"
    text: str
    intent_true: str                 # etiqueta de verdad: order_status | refund | kb_question | escalation
    created_at: float                # segundos unix (tiempo simulado)
    order_id: str | None = None
    sku: str | None = None
    contains_pii: bool = False       # el texto del cliente incluye datos personales (sintéticos)
    faults: list[FaultSpec] = field(default_factory=list)
    incident: str | None = None      # nombre del incidente que generó los fallos (si aplica)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Ticket":
        d = dict(d)
        d["faults"] = [FaultSpec(**f) for f in d.get("faults", [])]
        return cls(**d)


@dataclass
class StepRecord:
    """Un paso del agente: llamada al LLM o ejecución de herramienta."""
    index: int
    kind: str                        # "llm" | "tool"
    name: str                        # modelo (llm) o nombre de la herramienta (tool)
    start_s: float
    end_s: float
    status: str = "ok"               # "ok" | "error"
    error_type: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def latency_s(self) -> float:
        return self.end_s - self.start_s


@dataclass
class AgentResult:
    """Resultado de ``SupportAgent.run``. Incluye *ground truth* de los fallos para validar detecciones."""
    ticket_id: str
    status: str                      # "ok" | "error" | "max_steps" | "escalated"
    answer: str
    steps: list[StepRecord]
    start_s: float
    end_s: float
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    n_llm_calls: int
    n_tool_calls: int
    tools_used: list[str]
    error_type: str | None = None
    injected_faults: list[str] = field(default_factory=list)   # ground truth
    grounded: bool = True            # False si la respuesta contiene datos inventados (alucinación)
    pii_leaked: bool = False         # True si la respuesta contiene datos personales ajenos
    intent_pred: str | None = None

    @property
    def latency_s(self) -> float:
        return self.end_s - self.start_s

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["latency_s"] = self.latency_s
        return d
