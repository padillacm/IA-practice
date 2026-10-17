"""SupportOps v0: agente de soporte con bucle LLM + herramientas. SIN observabilidad (eso llega en el módulo 03).

El bucle (el corazón de cualquier agente)::

    mensajes = [ticket]
    repetir hasta max_steps:
        respuesta = llm(mensajes, herramientas)
        si no pide herramientas -> respuesta final
        por cada herramienta pedida: ejecutarla y añadir el resultado a los mensajes
"""
from __future__ import annotations

import json
import logging
from typing import Any

from .clock import SimClock, stable_hex, stable_rng
from .config import get_settings
from .faults import FaultInjector
from .instrument import Instrumentor, LLMCallInfo, RunContext, ToolCallInfo, logger
from .llm import LLMClient, LLMError, get_llm
from .models import AgentResult, Message, StepRecord, Ticket, Usage
from .pricing import cost_usd
from .tools import ToolError, ToolRegistry, default_tools

SYSTEM_PROMPT = (
    "Eres el asistente de soporte de SupportOps, una tienda online de hardware. Responde en español, con amabilidad y "
    "brevedad. Usa las herramientas para consultar pedidos, tramitar reembolsos y buscar en la base de conocimiento; "
    "no inventes datos. Si el cliente pide hablar con una persona o el caso es delicado, escala a un humano."
)
FALLBACK_ANSWER = "Lo siento, no he podido resolver su consulta ahora mismo. Un compañero revisará su caso."


class SupportAgent:
    def __init__(
        self,
        llm: LLMClient | None = None,
        tools: ToolRegistry | None = None,
        instrumentor: Instrumentor | None = None,
        *,
        name: str = "supportops-agent",
        system_prompt: str = SYSTEM_PROMPT,
        max_steps: int | None = None,
        llm_retries: int = 1,
        max_tokens: int = 512,
        temperature: float = 0.0,
    ):
        s = get_settings()
        self.llm = llm or get_llm()
        self.tools = tools or default_tools()
        self.instr = instrumentor or Instrumentor()
        self.name, self.system_prompt = name, system_prompt
        self.max_steps = max_steps or s.max_steps
        self.llm_retries = llm_retries
        self.max_tokens, self.temperature = max_tokens, temperature
        self._adhoc = 0

    # ------------------------------------------------------------------------------------------------
    def _log(self, ctx: RunContext, level: int, msg: str, **fields: Any) -> None:
        logger.log(level, msg, extra={"supportops": fields})
        self.instr.log(ctx, level, msg, fields)

    def run(self, ticket: Ticket | str) -> AgentResult:
        if isinstance(ticket, str):
            self._adhoc += 1
            ticket = Ticket(f"T-adhoc-{self._adhoc:04d}", "C-0001", "standard", "chat", ticket, "unknown", 1_788_253_200.0)
        s = get_settings()
        clock = SimClock(start_s=ticket.created_at, sleep_scale=s.sleep_scale)
        inj = FaultInjector(ticket.faults)
        llm = inj.wrap_llm(self.llm)
        tools = inj.wrap_tools(self.tools)
        ctx = RunContext(ticket, self.name, clock, self.llm.model, self.llm.provider,
                         run_id=stable_hex(12, s.seed, ticket.ticket_id))
        messages = [Message("user", ticket.text)]
        steps: list[StepRecord] = []
        usage, cost = Usage(), 0.0
        tools_used: list[str] = []
        answer, status, error_type, intent_pred = "", "max_steps", None, None
        tool_errors = 0
        llm_idx = 0

        with self.instr.agent_run(ctx):
            self._log(ctx, logging.INFO, "ticket recibido", ticket_id=ticket.ticket_id, channel=ticket.channel, tier=ticket.tier)
            for step in range(self.max_steps):
                # ---------------------------------------------------------------- llamada al LLM (con reintentos)
                resp, attempt = None, 0
                while resp is None:
                    info = LLMCallInfo(step, attempt, self.llm.model, self.llm.provider, len(messages), self.max_tokens,
                                       self.temperature, messages=messages)
                    t0 = clock.now_s()
                    try:
                        with self.instr.llm_call(ctx, info):
                            try:
                                resp = llm.chat(messages, self.tools.schemas(), system=self.system_prompt,
                                                max_tokens=self.max_tokens, temperature=self.temperature,
                                                call_key=(ticket.ticket_id, llm_idx))
                            except LLMError as e:
                                clock.advance(e.latency_s)
                                info.error = e
                                raise
                            clock.advance(resp.latency_s)
                            info.response = resp
                    except LLMError as e:
                        steps.append(StepRecord(len(steps), "llm", self.llm.model, t0, clock.now_s(), "error", e.error_type,
                                                attributes={"attempt": attempt, "http.status": e.status}))
                        llm_idx += 1
                        self._log(ctx, logging.WARNING, "error del proveedor LLM", step=step, attempt=attempt, status=e.status)
                        if e.retryable and attempt < self.llm_retries:
                            attempt += 1
                            clock.advance(0.5 * (2 ** (attempt - 1)))     # backoff exponencial simulado
                            continue
                        status, error_type = "error", e.error_type
                        answer = FALLBACK_ANSWER
                        break
                    llm_idx += 1
                    usage += resp.usage
                    cost += cost_usd(resp.model, resp.usage.input_tokens, resp.usage.output_tokens)
                    steps.append(StepRecord(len(steps), "llm", resp.model, t0, clock.now_s(), "ok", None,
                                            resp.usage.input_tokens, resp.usage.output_tokens, resp.finish_reason,
                                            {"attempt": attempt, "response_id": resp.response_id}))
                    if intent_pred is None:
                        intent_pred = resp.meta.get("intent")
                if resp is None:
                    break
                # ---------------------------------------------------------------- respuesta final o herramientas
                if not resp.tool_calls:
                    answer = resp.content
                    status = "escalated" if "escalate_to_human" in tools_used else ("degraded" if tool_errors else "ok")
                    break
                messages.append(Message("assistant", resp.content, resp.tool_calls))
                for call in resp.tool_calls:
                    tinfo = ToolCallInfo(step, call)
                    t0 = clock.now_s()
                    lat_rng = stable_rng("tool-latency", s.seed, ticket.ticket_id, len(steps))
                    tools_used.append(call.name)
                    st, etype, payload = "ok", None, None
                    try:
                        with self.instr.tool_call(ctx, tinfo):
                            try:
                                tool = tools.get(call.name)
                                clock.advance(tool.sample_latency(lat_rng))
                                try:
                                    payload = tool.fn(**call.arguments)
                                except TypeError as e:
                                    raise ToolError(f"argumentos inválidos: {e}", "invalid_arguments") from e
                                tinfo.result = payload
                            except ToolError as e:
                                if e.latency_s:
                                    clock.advance(e.latency_s)
                                tinfo.error = e
                                raise
                    except ToolError as e:
                        st, etype, tool_errors = "error", e.error_type, tool_errors + 1
                        payload = {"error": str(e), "error_type": e.error_type}
                        self._log(ctx, logging.WARNING, "error de herramienta", step=step, tool=call.name, error_type=etype)
                    steps.append(StepRecord(len(steps), "tool", call.name, t0, clock.now_s(), st, etype,
                                            attributes={"arguments": call.arguments}))
                    messages.append(Message("tool", json.dumps(payload, ensure_ascii=False, default=str),
                                            tool_call_id=call.id, name=call.name))
            else:
                answer = FALLBACK_ANSWER
            if status == "max_steps":
                answer = answer or FALLBACK_ANSWER
            result = AgentResult(
                ticket_id=ticket.ticket_id, status=status, answer=answer, steps=steps, start_s=clock.start_s, end_s=clock.now_s(),
                model=self.llm.model, provider=self.llm.provider, input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens, cost_usd=round(cost, 6),
                n_llm_calls=sum(1 for x in steps if x.kind == "llm"), n_tool_calls=sum(1 for x in steps if x.kind == "tool"),
                tools_used=tools_used, error_type=error_type, injected_faults=list(inj.triggered),
                grounded=not inj.ungrounded, pii_leaked=inj.pii_leaked, intent_pred=intent_pred,
            )
            ctx.result = result
            self._log(ctx, logging.INFO if status in ("ok", "escalated") else logging.WARNING, "ticket resuelto",
                      ticket_id=ticket.ticket_id, status=status, latency_s=round(result.latency_s, 3))
        return result
