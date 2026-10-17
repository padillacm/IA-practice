"""Pruebas rápidas del paquete: determinismo, fallos, adaptadores de proveedores (con clientes falsos)."""
import json
from types import SimpleNamespace as NS

import pytest

from supportops import (DEFAULT_FAULT_RATES, FaultSpec, Incident, RecordingInstrumentor, SupportAgent, Ticket, check_stack,
                        default_tools, generate_tickets, get_llm, run_tickets, to_rows)
from supportops import sample_data as sd
from supportops.llm import MockLLM, Rule, ToolStep
from supportops.llm.anthropic_provider import AnthropicLLM, to_anthropic_messages
from supportops.llm.ollama_provider import OllamaLLM
from supportops.llm.openai_provider import OpenAILLM, to_openai_messages
from supportops.models import Message, ToolCall
from supportops.tools import Tool


def ticket(text, faults=(), tid="T-test"):
    return Ticket(tid, "C-0001", "standard", "chat", text, "x", 1_788_253_200.0, faults=list(faults))


def test_determinism():
    a = [r.to_dict() for r in run_tickets(SupportAgent(), generate_tickets(60, 1, fault_rates=DEFAULT_FAULT_RATES))]
    b = [r.to_dict() for r in run_tickets(SupportAgent(), generate_tickets(60, 1, fault_rates=DEFAULT_FAULT_RATES))]
    assert a == b


def test_default_provider_is_mock(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert get_llm().provider == "mock"
    monkeypatch.setenv("LLM_PROVIDER", "nope")
    with pytest.raises(ValueError):
        get_llm()


@pytest.mark.parametrize("text,tool", [("¿Dónde está mi pedido ORD-00012?", "get_order"), ("¿Cuántos años de garantía?", "search_kb"),
                                       ("Quiero hablar con un humano", "escalate_to_human")])
def test_routing(text, tool):
    r = SupportAgent().run(text)
    assert tool in r.tools_used and r.status in ("ok", "escalated") and r.grounded


def test_refund_flow_and_clarification():
    assert SupportAgent().run("Quiero un reembolso del pedido ORD-00020").tools_used[:2] == ["get_order", "issue_refund"]
    r = SupportAgent().run("Quiero un reembolso, no recuerdo el número")
    assert r.n_tool_calls == 0 and "número de pedido" in r.answer


@pytest.mark.parametrize("kind,params,check", [
    ("llm_error", {"persistent": True}, lambda r: r.status == "error"),
    ("llm_error", {"persistent": False}, lambda r: r.status == "ok" and r.n_llm_calls >= 3),
    ("tool_error", {}, lambda r: r.status == "degraded"),
    ("tool_timeout", {}, lambda r: r.latency_s > 5),
    ("hallucination", {}, lambda r: (not r.grounded) and r.n_tool_calls == 0),
    ("tool_loop", {}, lambda r: r.status == "max_steps" and r.n_tool_calls >= 5),
    ("pii_leak", {"victim": "C-0042"}, lambda r: r.pii_leaked and "@example.com" in r.answer),
    ("latency_spike", {"factor": 10.0}, lambda r: r.latency_s > 8),
])
def test_faults(kind, params, check):
    r = SupportAgent().run(ticket("¿Dónde está mi pedido ORD-00012?", [FaultSpec(kind, params)]))
    assert kind in r.injected_faults, r
    assert check(r), r


def test_recording_instrumentor_links_logs_and_spans():
    rec = RecordingInstrumentor()
    SupportAgent(instrumentor=rec).run("¿Dónde está mi pedido ORD-00012?")
    root = rec.spans[0]
    assert root["parent_span_id"] is None and root["name"].startswith("invoke_agent")
    assert {s["trace_id"] for s in rec.spans} == {root["trace_id"]}
    assert all(l["trace_id"] == root["trace_id"] for l in rec.logs)
    names = [s["name"] for s in rec.spans]
    assert any(n.startswith("chat ") for n in names) and "execute_tool get_order" in names


def test_new_tool_and_rule():
    reg = default_tools()
    reg.register(Tool("check_stock", "stock", {"type": "object", "properties": {"sku": {"type": "string"}}}, lambda sku: {"sku": sku, "units": 3}))
    llm = MockLLM()
    llm.add_rule(Rule("stock", ("stock", "disponible"), [ToolStep("check_stock", lambda t, r: {"sku": "SKU-1001"})],
                      lambda t, r: f"Quedan {r['check_stock']['units']} unidades.", priority=50))
    r = SupportAgent(llm=llm, tools=reg).run("¿Hay stock disponible del teclado?")
    assert r.tools_used == ["check_stock"] and "3 unidades" in r.answer


def test_traffic_schema_and_incident():
    tk = generate_tickets(200, 7, incidents=[Incident("x", "llm_error", 0, 3600, prob=1.0)])
    assert all(t.faults and t.incident == "x" for t in tk)
    rows = to_rows(tk[:3], run_tickets(SupportAgent(), tk[:3]))
    assert set(rows[0]) >= {"ticket_id", "latency_s", "cost_usd", "injected_faults", "grounded"}


def test_sample_data_consistent():
    runs, spans = sd.load_runs(), sd.load_spans()
    roots = [s for s in spans if s["parent_span_id"] is None]
    assert len(roots) == len(runs) == sd.load_meta()["n_tickets"]
    assert sum(1 for _ in sd.load_tickets()) == len(runs)


def test_check_stack_degraded_message(capsys, monkeypatch):
    monkeypatch.setenv("STACK_HOST", "127.0.0.1")
    monkeypatch.setattr("supportops.stack.services", lambda: {"tempo": {"profile": "core", "url": "http://127.0.0.1:9/x", "ui": "u"}})
    monkeypatch.setattr("supportops.stack.PROFILES", {"core": ["tempo"]})
    st = check_stack("core", timeout=0.2)
    out = capsys.readouterr().out
    assert st.degraded and "docker compose" in out and "--profile core up -d" in out and "MODO DEGRADADO" in out


def test_provider_adapters():
    msgs = [Message("user", "hola"), Message("assistant", "", [ToolCall("c1", "get_order", {"order_id": "ORD-00001"})]),
            Message("tool", '{"ok": 1}', tool_call_id="c1", name="get_order")]
    am = to_anthropic_messages(msgs)
    assert am[1]["content"][0]["type"] == "tool_use" and am[2]["content"][0]["type"] == "tool_result"
    om = to_openai_messages(msgs, "sys")
    assert om[0]["role"] == "system" and om[2]["tool_calls"][0]["function"]["name"] == "get_order"

    fake_a = NS(messages=NS(create=lambda **kw: NS(content=[NS(type="tool_use", id="t1", name="get_order", input={"order_id": "x"})],
                                                    stop_reason="tool_use", usage=NS(input_tokens=5, output_tokens=2), model="m", id="r")))
    r = AnthropicLLM("m", client=fake_a).chat([Message("user", "hi")], default_tools().schemas())
    assert r.tool_calls[0].name == "get_order" and r.finish_reason == "tool_calls" and r.usage.total == 7

    fn = NS(name="search_kb", arguments=json.dumps({"query": "q"}))
    fake_o = NS(chat=NS(completions=NS(create=lambda **kw: NS(choices=[NS(message=NS(content=None, tool_calls=[NS(id="x", function=fn)]), finish_reason="tool_calls")],
                                                              usage=NS(prompt_tokens=3, completion_tokens=1), model="m", id="r"))))
    r = OpenAILLM("m", client=fake_o).chat([Message("user", "hi")], default_tools().schemas())
    assert r.tool_calls[0].arguments == {"query": "q"}

    r = OllamaLLM("m", transport=lambda url, p: {"message": {"content": "ok"}, "prompt_eval_count": 4, "eval_count": 2}).chat([Message("user", "hi")])
    assert r.content == "ok" and r.usage.total == 6
    with pytest.raises(ValueError):
        OpenAILLM(None)
