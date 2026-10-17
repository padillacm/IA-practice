"""SupportOps · agente de soporte simulado para el curso «Observabilidad de agentes de IA en producción».

API pública (ver agent-observability-course/_tools/INTERFACES.md):

    from supportops import SupportAgent, get_llm, generate_tickets, run_tickets, check_stack
"""
from __future__ import annotations

from .agent import SYSTEM_PROMPT, SupportAgent
from .clock import SIM_EPOCH_S, SimClock, stable_hex, stable_rng
from .config import Settings, get_settings
from .faults import FAULT_KINDS, FaultInjector
from .instrument import CompositeInstrumentor, Instrumentor, LLMCallInfo, RunContext, ToolCallInfo
from .llm import LLMError, MockLLM, Rule, ToolStep, get_llm
from .models import AgentResult, FaultSpec, LLMResponse, Message, StepRecord, Ticket, ToolCall, Usage
from .recording import RecordingInstrumentor
from .stack import StackStatus, check_stack
from .tools import Tool, ToolError, ToolRegistry, default_tools
from .traffic import DEFAULT_FAULT_RATES, Incident, generate_tickets, run_tickets, to_rows

__version__ = "0.1.0"

__all__ = [
    "SupportAgent", "SYSTEM_PROMPT", "get_llm", "MockLLM", "Rule", "ToolStep", "LLMError", "Tool", "ToolError", "ToolRegistry",
    "default_tools", "Ticket", "FaultSpec", "AgentResult", "StepRecord", "Message", "ToolCall", "Usage", "LLMResponse",
    "generate_tickets", "run_tickets", "to_rows", "Incident", "DEFAULT_FAULT_RATES", "FAULT_KINDS", "FaultInjector",
    "Instrumentor", "CompositeInstrumentor", "RunContext", "LLMCallInfo", "ToolCallInfo", "RecordingInstrumentor",
    "SimClock", "SIM_EPOCH_S", "stable_rng", "stable_hex", "check_stack", "StackStatus", "Settings", "get_settings",
]


def __getattr__(name: str):  # importación perezosa de submódulos (evita avisos con `python -m supportops.sample_data`)
    if name in ("backends", "sample_data", "schema", "viz", "catalog", "pricing", "recording"):
        import importlib
        return importlib.import_module(f".{name}", __name__)
    raise AttributeError(name)
