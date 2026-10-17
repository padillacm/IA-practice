"""Pruebas del módulo 13 (FinOps): precios, caché simulada, libro de costes, topes, bucles y alerta de desvío."""
import json

import pytest

pytest.importorskip("opentelemetry.sdk")

from supportops import DEFAULT_FAULT_RATES, FaultSpec, MockLLM, SupportAgent, Ticket, generate_tickets, run_tickets  # noqa: E402
from supportops.finops import (ILLUSTRATIVE_PRICES, BudgetGuard, BudgetPool, CacheSimulator, CostLedger, DowngradeLLM, FinOpsInstrumentor,  # noqa: E402
                               LoopGuard, ModelPrice, PriceTable, Usage4, cost_drift_alert, detect_loop_in_result, finops_alert_rule_json,
                               policy_prompt, semconv_usage)
from supportops.instrument import CompositeInstrumentor  # noqa: E402
from supportops.pricing import cost_usd  # noqa: E402
from supportops.telemetry import OTelInstrumentor, setup_telemetry  # noqa: E402

PROMPT = policy_prompt(2500)


def ticket(text="¿Dónde está mi pedido ORD-00012?", faults=(), tid="T-f1", cid="C-0001", tier="standard", t0=1_788_253_200.0):
    return Ticket(tid, cid, tier, "chat", text, "order_status", t0, faults=list(faults))


def test_usage_semantics():
    u = Usage4(1000, 200, cache_read=600, cache_write=100)
    assert u.uncached == 300
    with pytest.raises(ValueError):
        Usage4(100, 10, cache_read=80, cache_write=40)
    a = semconv_usage("anthropic", input_tokens=300, output_tokens=200, cache_read_input_tokens=600, cache_creation_input_tokens=100)
    assert a == u                                                       # Anthropic: input_tokens SIN caché -> el total la incluye
    assert semconv_usage("semconv", input_tokens=1000, output_tokens=200, cache_read_input_tokens=600, cache_write_input_tokens=100) == u


def test_price_table_formula_and_config(tmp_path):
    pt = PriceTable({"m": ModelPrice(2.0, 10.0, cache_read=0.2, cache_write=2.5)})
    c = pt.cost("m", Usage4(1_000_000, 100_000, cache_read=600_000, cache_write=100_000))
    assert c.input == pytest.approx(0.6) and c.cache_read == pytest.approx(0.12) and c.cache_write == pytest.approx(0.25) and c.output == pytest.approx(1.0)
    assert c.total == pytest.approx(1.97)
    assert PriceTable({"m": ModelPrice(2.0, 10.0)}).cost("m", Usage4(1000, 0, cache_read=500)).total == pytest.approx(2.0 * 1000 / 1e6)   # sin multiplicadores
    with pytest.raises(KeyError):
        pt.cost("otro", Usage4(1, 1))
    f = tmp_path / "p.json"
    f.write_text(json.dumps({"x": {"input": 1, "output": 2, "cache_read": 0.1}}))
    assert PriceTable.from_json(f).cost("x", Usage4(1_000_000, 0)).total == pytest.approx(1.0)
    assert "ILUSTRATIVOS" in ILLUSTRATIVE_PRICES.describe()


def test_reconciles_with_mock_pricing():
    for model in ("mock-small", "mock-large"):
        assert ILLUSTRATIVE_PRICES.cost(model, Usage4(1234, 567)).total == pytest.approx(cost_usd(model, 1234, 567))


def test_cache_simulator_rules():
    c = CacheSimulator(min_prefix_tokens=100, ttl_s=300)
    assert c.step("r1", "p", 0, 50, 40, 0.0) == (0, 0)                  # por debajo del mínimo: no cacheable
    assert c.step("r2", "p", 0, 500, 400, 0.0) == (0, 500)              # prefijo frío: se escribe todo
    assert c.step("r2", "p", 1, 700, 400, 1.0) == (500, 200)            # misma ejecución: lee la entrada previa, escribe el resto
    assert c.step("r3", "p", 0, 520, 400, 100.0) == (400, 120)          # otra ejecución con prefijo caliente: lee el estático
    assert c.step("r4", "p", 0, 520, 400, 100.0 + 301 + 100) == (0, 520)   # caducado (TTL)
    assert CacheSimulator(enabled=False).step("r", "p", 0, 9999, 9000, 0.0) == (0, 0)


def run_agent(tel, fin, tickets, extra=(), llm=None):
    agent = SupportAgent(llm=llm, system_prompt=PROMPT, instrumentor=CompositeInstrumentor(OTelInstrumentor(tel), *extra, fin))
    return run_tickets(agent, tickets)


def test_finops_instrumentor_ledger_spans_and_metrics():
    tel = setup_telemetry("supportops-agent", mode="memory", set_global=False)
    led = CostLedger()
    fin = FinOpsInstrumentor(ILLUSTRATIVE_PRICES, cache=CacheSimulator(min_prefix_tokens=256), ledger=led, handle=tel)
    tks = generate_tickets(40, seed=3, fault_rates=None)
    rs = run_agent(tel, fin, tks)
    df = led.to_frame()
    assert len(df) == 40 and df.cost_usd.sum() > 0
    assert (df.cache_read + df.cache_write <= df.input_total).all() and (df.uncached >= 0).all()
    assert df.cache_hit_ratio.mean() > 0.5                                # prompt largo + tráfico denso: la caché funciona
    # coste con caché < coste sin caché de las mismas ejecuciones
    nocache = sum(ILLUSTRATIVE_PRICES.cost(r.model, Usage4(r.input_tokens, r.output_tokens)).total for r in rs)
    assert df.cost_usd.sum() < nocache * 0.5
    spans = tel.span_records()
    chats = [s for s in spans if s["name"].startswith("chat")]
    assert chats and all("supportops.finops.cost_usd" in s["attributes"] and "gen_ai.usage.cache_read.input_tokens" in s["attributes"] for s in chats)
    roots = [s for s in spans if s["name"].startswith("invoke_agent")]
    assert sum(s["attributes"]["supportops.finops.cost_usd"] for s in roots) == pytest.approx(df.cost_usd.sum(), abs=1e-6)
    assert sum(s["attributes"]["supportops.finops.cost_usd"] for s in chats) == pytest.approx(df.cost_usd.sum(), abs=1e-6)     # hojas = raíces: sin doble conteo
    pts = [p for p in tel.metric_points() if p["name"] == "supportops.llm.cost"]
    assert sum(p["value"] for p in pts) == pytest.approx(df.cost_usd.sum(), abs=1e-6)
    assert all("supportops.customer.id" not in p["attributes"] for p in tel.metric_points())              # cardinalidad: el cliente NO es etiqueta
    logs = [l for l in tel.log_records() if l["body"] == "ticket costed"]
    assert len(logs) == 40 and all(l["trace_id"] for l in logs) and "supportops.customer.id" in logs[0]["attributes"]


def test_budget_guard_caps_loops_and_tier_multiplier():
    tel = setup_telemetry("supportops-agent", mode="memory", set_global=False)
    loop = [FaultSpec("tool_loop")]
    led = CostLedger()
    fin = FinOpsInstrumentor(ILLUSTRATIVE_PRICES, ledger=led, handle=tel)
    guard = BudgetGuard(ILLUSTRATIVE_PRICES, per_ticket_usd=0.003, tier_multiplier={"premium": 2.0})
    t1, t2, t3 = ticket(faults=loop, tid="T-a"), ticket(faults=loop, tid="T-b", tier="premium"), ticket(tid="T-c")
    base = {r.ticket_id: r for r in run_tickets(SupportAgent(system_prompt=PROMPT), [t1, t2, t3])}
    run_agent(tel, fin, [t1, t2, t3], extra=[guard])
    df = led.to_frame().set_index("ticket_id")
    assert df.loc["T-a", "status"] == "error" and df.loc["T-a", "error_type"] == "budget_exceeded" and df.loc["T-a", "budget_blocked"]
    assert df.loc["T-a", "cost_usd"] < base["T-a"].cost_usd and df.loc["T-a", "cost_usd"] < 0.003 + 0.001      # tope + a lo sumo una llamada
    assert df.loc["T-b", "cost_usd"] > df.loc["T-a", "cost_usd"]            # el premium tiene el doble de tope
    assert df.loc["T-c", "status"] == "ok"
    assert ("T-a", "tope por ticket") in guard.blocked
    errs = [s for s in tel.span_records() if s["attributes"].get("error.type") == "budget_exceeded"]
    assert errs and errs[0]["name"].startswith("chat")


def test_downgrade_llm_switches_model_after_soft_ratio():
    tel = setup_telemetry("supportops-agent", mode="memory", set_global=False)
    guard = BudgetGuard(ILLUSTRATIVE_PRICES, per_ticket_usd=0.02)
    dl = DowngradeLLM(MockLLM("mock-large"), MockLLM("mock-small"), guard, soft_ratio=0.3)
    led = CostLedger()
    run_agent(tel, FinOpsInstrumentor(ILLUSTRATIVE_PRICES, ledger=led, handle=tel), [ticket(faults=[FaultSpec("tool_loop")])], extra=[guard], llm=dl)
    models = [s["attributes"].get("gen_ai.response.model") for s in tel.span_records() if s["name"].startswith("chat") and "gen_ai.response.model" in s["attributes"]]
    assert models[0] == "mock-large" and "mock-small" in models and dl.downgrades >= 1


def test_loop_guard_and_post_hoc_detection():
    tel = setup_telemetry("supportops-agent", mode="memory", set_global=False)
    led = CostLedger()
    lg = LoopGuard(max_repeats=2)
    tk = ticket(faults=[FaultSpec("tool_loop")], tid="T-l")
    r_free = run_tickets(SupportAgent(system_prompt=PROMPT), [tk])[0]
    assert detect_loop_in_result(r_free) == (True, r_free.n_tool_calls) or detect_loop_in_result(r_free)[0]
    rs = run_agent(tel, FinOpsInstrumentor(ILLUSTRATIVE_PRICES, ledger=led, handle=tel), [tk], extra=[lg])
    assert lg.tripped == ["T-l"] and rs[0].n_tool_calls <= 3 and rs[0].n_llm_calls <= 4 and rs[0].error_type == "loop_detected" and rs[0].cost_usd < r_free.cost_usd
    ok = run_tickets(SupportAgent(), [ticket(tid="T-ok")])[0]
    assert detect_loop_in_result(ok)[0] is False


def test_pool_burn_rate_and_alert_rule():
    p = BudgetPool(limit_usd=100.0, period_s=30 * 86400)
    p.add(10.0)
    assert p.burn_rate(3 * 86400) == pytest.approx(1.0) and p.forecast_usd(3 * 86400) == pytest.approx(100.0)
    p.add(10.0)
    assert p.burn_rate(3 * 86400) == pytest.approx(2.0) and p.remaining_usd() == pytest.approx(80.0)
    assert cost_drift_alert([1.0] * 10 + [1.0, 1.0, 1.9, 1.9, 1.9]) == 14 and cost_drift_alert([1.0] * 30) is None
    assert cost_drift_alert([1.0] * 10 + [2.0, 1.0, 2.0, 1.0, 2.0, 1.0, 2.0]) is None            # racha rota: sin alerta
    rule = finops_alert_rule_json("fld", ratio=1.6)
    assert rule["condition"] == "C" and rule["data"][0]["model"]["expr"].count("offset 1h") == 2 and rule["folderUID"] == "fld"
