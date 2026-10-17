"""Pruebas del módulo 11 (multi-agente): propagación W3C, topologías, resiliencia y proceso real."""
import dataclasses

import pytest

pytest.importorskip("opentelemetry.sdk")

from supportops import FaultSpec, generate_tickets  # noqa: E402
from supportops.multiagent import (ORCH, DelegationPolicy, MultiAgentSupportOps, RemoteAgentProcess, agent_tree_text,  # noqa: E402
                                   build_mesh, cost_rollup, critical_path, extract_manual, extract_sdk, format_traceparent,
                                   inject_manual, inject_sdk, parse_traceparent, span_frame)
from opentelemetry import trace as otel_trace  # noqa: E402
from opentelemetry.trace import SpanKind  # noqa: E402

VALID = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"


@pytest.fixture(scope="module")
def refund_ticket():
    from supportops import SupportAgent
    tks = generate_tickets(120, seed=42)
    # un reembolso que de verdad llega a issue_refund (pedido entregado y dentro de plazo)
    return next(t for t in tks if t.intent_true == "refund" and t.order_id and "issue_refund" in SupportAgent().run(t).tools_used)


def with_faults(t, *faults):
    return dataclasses.replace(t, faults=list(faults))


# ------------------------------------------------------------------------------------------------ traceparent
@pytest.mark.parametrize("bad", [
    None, "", "garbage", VALID.upper(), "ff-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
    "00-00000000000000000000000000000000-00f067aa0ba902b7-01", "00-4bf92f3577b34da6a3ce929d0e0e4736-0000000000000000-01",
    "00-4bf92f3577b34da6a3ce929d0e0e47-00f067aa0ba902b7-01", VALID + "-extra", "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7",
])
def test_parse_traceparent_rejects(bad):
    assert parse_traceparent(bad) is None


def test_parse_traceparent_accepts():
    tp = parse_traceparent(VALID)
    assert tp and tp.trace_id.startswith("4bf9") and tp.sampled
    assert parse_traceparent("00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-00").sampled is False
    assert parse_traceparent("01-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01-futuro")      # versión futura: se ignora el resto
    assert format_traceparent("4bf92f3577b34da6a3ce929d0e0e4736", "00f067aa0ba902b7") == VALID


def test_manual_and_sdk_propagation_are_equivalent():
    mesh = build_mesh(mode="memory")
    span = mesh.handle(ORCH).tracer().start_span("x", kind=SpanKind.CLIENT)
    with otel_trace.use_span(span, end_on_exit=False):
        a, b = inject_manual(), inject_sdk()
    assert a["traceparent"] == b["traceparent"]
    for ctx in (extract_manual(a), extract_sdk(b)):
        sc = otel_trace.get_current_span(ctx).get_span_context()
        assert sc.is_remote and format(sc.trace_id, "032x") == format(span.get_span_context().trace_id, "032x")
    assert extract_manual({"Traceparent": "basura"}) is None and extract_sdk({}) is None


# ------------------------------------------------------------------------------------------------ topologías
def test_delegate_single_trace_across_services(refund_ticket):
    mesh = build_mesh(mode="memory")
    res = MultiAgentSupportOps(mesh).run(refund_ticket)
    rows = mesh.span_records()
    assert {r["trace_id"] for r in rows} == {res.trace_id}                     # UNA traza de extremo a extremo
    services = {r["resource"]["service.name"] for r in rows}
    assert services == {"supportops-orchestrator", "supportops-orders-agent", "supportops-knowledge-agent", "supportops-billing-agent"}
    root = [r for r in rows if r["parent_span_id"] is None]
    assert len(root) == 1 and root[0]["name"] == "invoke_workflow support_ticket"
    ids = {r["span_id"] for r in rows}
    assert all(r["parent_span_id"] in ids for r in rows if r["parent_span_id"])  # sin huérfanos
    assert res.agents_called == ["orders-agent", "knowledge-agent", "billing-agent"] and res.status == "ok"
    # cada llamada al LLM se cuenta UNA vez: la suma de spans chat == total del árbol
    roll = cost_rollup(rows)
    assert sum(v["calls"] for v in roll.values()) == res.n_llm_calls
    assert sum(v["cost_usd"] for v in roll.values()) == pytest.approx(res.cost_usd, abs=1e-5)
    # los pre-chequeos son paralelos: ambos CLIENT empiezan a la vez
    cl = [r for r in rows if r["kind"] == "CLIENT" and r["name"].startswith("invoke_agent") and "supportops.delegation.role" in r["attributes"]]
    pre = [r for r in cl if r["attributes"]["supportops.delegation.role"] == "precheck"]
    assert len(pre) == 2 and pre[0]["start_unix_nano"] == pre[1]["start_unix_nano"]
    cp = critical_path(rows)
    assert [r["name"] for r in cp][:2] == ["invoke_workflow support_ticket", "invoke_agent supportops-orchestrator"]
    # camino crítico real: enrutar -> (solo el pre-chequeo MÁS LENTO) -> facturación -> sintetizar; el pre-chequeo corto queda fuera
    top = [r for r in cp if r["resource"]["service.name"] == ORCH and r["span_id"] not in {cp[0]["span_id"], cp[1]["span_id"]}]
    assert [r["attributes"].get("gen_ai.operation.name") for r in top][0] == "chat" and top[-1]["attributes"].get("gen_ai.operation.name") == "chat"
    assert sum(1 for r in top if r["attributes"].get("supportops.delegation.role") == "precheck") == 1
    assert sum(1 for r in top if r["attributes"].get("supportops.delegation.role") not in (None, "precheck")) == 1
    assert sum((r["end_unix_nano"] - r["start_unix_nano"]) for r in top) / 1e9 == pytest.approx(res.latency_s, rel=0.02)


def test_handoff_is_flatter_and_cheaper(refund_ticket):
    m1, m2 = build_mesh(mode="memory"), build_mesh(mode="memory")
    d = MultiAgentSupportOps(m1, mode="delegate").run(refund_ticket)
    h = MultiAgentSupportOps(m2, mode="handoff").run(refund_ticket)
    assert h.agents_called == ["billing-agent"] and h.cost_usd < d.cost_usd and h.latency_s < d.latency_s
    rows = m2.span_records(h.trace_id)
    names = [r["name"] for r in rows]
    assert "execute_tool transfer_to_billing-agent" in names
    orch_root = next(r for r in rows if r["name"] == "invoke_agent supportops-orchestrator")
    bill_cli = next(r for r in rows if r["name"] == "invoke_agent billing-agent" and r["kind"] == "CLIENT")
    assert bill_cli["parent_span_id"] != orch_root["span_id"]                  # hermano, no hijo: el control se transfirió
    assert bill_cli["start_unix_nano"] >= orch_root["end_unix_nano"]


def test_clarification_needs_no_subagents():
    t = dataclasses.replace(generate_tickets(10, seed=1)[0], text="Quiero un reembolso, pero no me acuerdo del número de pedido.")
    mesh = build_mesh(mode="memory")
    res = MultiAgentSupportOps(mesh).run(t)
    assert res.agents_called == [] and "ORD" in res.answer


def test_no_propagation_fragments_the_trace(refund_ticket):
    mesh = build_mesh(mode="memory")
    MultiAgentSupportOps(mesh, propagation="none").run(refund_ticket)
    assert len({r["trace_id"] for r in mesh.span_records()}) > 1
    sub_roots = [r for r in mesh.span_records() if r["parent_span_id"] is None and r["kind"] == "INTERNAL"
                 and r["resource"]["service.name"].endswith("-agent")]
    assert sub_roots                                                            # subagentes huérfanos


# ------------------------------------------------------------------------------------------------ resiliencia
def _slow_billing(t):
    return with_faults(t, FaultSpec("tool_timeout", {"tool": "issue_refund", "timeout_s": 9.0, "agent": "billing-agent", "sticky": True}))


def test_timeout_retry_fallback_and_zombie(refund_ticket):
    mesh = build_mesh(mode="memory")
    res = MultiAgentSupportOps(mesh, policy=DelegationPolicy(timeout_s=12, max_retries=2)).run(_slow_billing(refund_ticket))
    assert res.status == "escalated" and res.fallback_used and res.timeouts == 3
    assert res.agents_called.count("billing-agent") == 3 and res.zombie_s > 0
    rows = mesh.span_records(res.trace_id)
    errs = [r for r in rows if r["kind"] == "CLIENT" and r["attributes"].get("error.type") == "timeout"]
    assert len(errs) == 3 and all(r["status"] == "ERROR" for r in errs)
    # el subagente termina DESPUÉS de que el cliente abandonara
    cli = errs[0]
    sub = next(r for r in rows if r["parent_span_id"] == cli["span_id"])
    assert sub["end_unix_nano"] > cli["end_unix_nano"]


def test_transient_fault_only_hits_first_attempt(refund_ticket):
    f = FaultSpec("llm_error", {"status": 503, "at_call": 0, "persistent": True, "agent": "billing-agent"})   # no sticky
    mesh = build_mesh(mode="memory")
    res = MultiAgentSupportOps(mesh).run(with_faults(refund_ticket, f))
    assert res.retries == 1 and res.status == "ok" and res.agents_called.count("billing-agent") == 2


def test_circuit_breaker_fails_fast(refund_ticket):
    mesh = build_mesh(mode="memory")
    sys_ = MultiAgentSupportOps(mesh, policy=DelegationPolicy(timeout_s=12, max_retries=0, breaker_threshold=2))
    bad = _slow_billing(refund_ticket)
    rs = [sys_.run(dataclasses.replace(bad, ticket_id=f"T-b{i}", created_at=bad.created_at + i)) for i in range(4)]
    assert [r.agents_called.count("billing-agent") for r in rs] == [1, 1, 0, 0]                 # tras 2 fallos seguidos el disyuntor se abre: ya no se llama al agente
    assert all(r.status == "escalated" for r in rs)
    fast = [r for r in mesh.span_records() if r["attributes"].get("error.type") == "circuit_open"]
    assert len(fast) >= 1 and all(r["end_unix_nano"] == r["start_unix_nano"] for r in fast)


def test_deadline_propagation_stops_work(refund_ticket):
    f = FaultSpec("latency_spike", {"factor": 8.0, "target": "llm", "agent": "billing-agent", "sticky": True})
    t = with_faults(refund_ticket, f)
    m1, m2 = build_mesh(mode="memory"), build_mesh(mode="memory")
    a = MultiAgentSupportOps(m1, policy=DelegationPolicy(timeout_s=8, max_retries=0, fallback_to_human=False)).run(t)
    b = MultiAgentSupportOps(m2, policy=DelegationPolicy(timeout_s=8, max_retries=0, fallback_to_human=False, propagate_deadline=True)).run(t)
    assert b.zombie_s < a.zombie_s and b.cost_usd < a.cost_usd
    assert any(r["attributes"].get("error.type") == "deadline_exceeded" for r in m2.span_records())


def test_determinism_and_frame(refund_ticket):
    a = MultiAgentSupportOps(build_mesh(mode="memory")).run(refund_ticket)
    b = MultiAgentSupportOps(build_mesh(mode="memory")).run(refund_ticket)
    assert (a.latency_s, a.cost_usd, a.input_tokens) == (b.latency_s, b.cost_usd, b.input_tokens)
    mesh = build_mesh(mode="memory")
    r = MultiAgentSupportOps(mesh).run(refund_ticket)
    df = span_frame(mesh.span_records(r.trace_id))
    assert df.service.nunique() == 4
    assert "invoke_workflow" in agent_tree_text(mesh.span_records(r.trace_id))


# ------------------------------------------------------------------------------------------------ proceso real
def test_real_process_propagation(refund_ticket):
    import os
    mesh = build_mesh(mode="memory")
    prod = mesh.handle(ORCH).tracer().start_span("publish supportops.tasks", kind=SpanKind.PRODUCER)
    with otel_trace.use_span(prod, end_on_exit=False):
        hdr = inject_manual()
    prod.end()
    tid = format(prod.get_span_context().trace_id, "032x")
    with RemoteAgentProcess("orders-agent") as w:
        out = w.call(refund_ticket, hdr, refund_ticket.created_at, propagation="manual", link_mode="parent")
        assert out["pid"] != os.getpid() and all(s["trace_id"] == tid for s in out["spans"])
        cons = next(s for s in out["spans"] if s["kind"] == "CONSUMER")
        assert cons["parent_span_id"] == format(prod.get_span_context().span_id, "016x")
        out2 = w.call(refund_ticket, hdr, refund_ticket.created_at, link_mode="link")
        cons2 = next(s for s in out2["spans"] if s["kind"] == "CONSUMER")
        assert cons2["trace_id"] != tid and cons2["parent_span_id"] is None and cons2["links"][0]["trace_id"] == tid


def test_hard_cancel_leaves_no_zombie(refund_ticket):
    t = _slow_billing(refund_ticket)
    soft = MultiAgentSupportOps(build_mesh(mode="memory"), policy=DelegationPolicy(timeout_s=6, max_retries=0, propagate_deadline=True, fallback_to_human=False)).run(t)
    hard = MultiAgentSupportOps(build_mesh(mode="memory"), policy=DelegationPolicy(timeout_s=6, max_retries=0, propagate_deadline=True,
                                                                                    cancel_in_flight=True, fallback_to_human=False)).run(t)
    assert soft.zombie_s > 0 and hard.zombie_s == 0 and hard.timeouts == 1 and hard.cost_usd <= soft.cost_usd


def test_escalation_fallback_uses_the_right_tool(refund_ticket):
    mesh = build_mesh(mode="memory")
    res = MultiAgentSupportOps(mesh, policy=DelegationPolicy(timeout_s=12, max_retries=0)).run(_slow_billing(refund_ticket))
    assert res.status == "escalated"
    assert not any(r["attributes"].get("error.type") == "unknown_tool" for r in mesh.span_records())


def test_baggage_travels_with_sdk_propagation():
    from opentelemetry import baggage
    mesh = build_mesh(mode="memory")
    ctx = baggage.set_baggage("supportops.customer.tier", "premium")
    from opentelemetry import context as c
    tok = c.attach(ctx)
    try:
        hdr = inject_sdk()
    finally:
        c.detach(tok)
    assert "premium" in hdr.get("baggage", "") and "traceparent" not in hdr      # sin span activo no hay traceparent
    assert "baggage" not in inject_manual()                                       # a mano solo viaja traceparent
