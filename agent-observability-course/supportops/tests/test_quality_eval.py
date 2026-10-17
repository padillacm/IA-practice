"""Pruebas del módulo 14: juez, muestreo, estadística y telemetría de evaluación."""
import os

import pytest

os.environ.setdefault("LLM_PROVIDER", "mock")
from supportops import SupportAgent, generate_tickets, run_tickets, DEFAULT_FAULT_RATES
from supportops.quality_eval import (CaseCollector, EvalCase, EvalScore, LLMJudge, MockJudge, OnlineEvaluator, RateSampler, RuleJudge, StratifiedSampler,
                                     build_eval_event, confusion, extract_claims, find_pii, get_judge, post_stratified_rate, required_sample_size,
                                     rogan_gladen, scrub_pii, simulate_feedback, unsupported_claims, wilson_interval)

FAULTS = {**DEFAULT_FAULT_RATES, "hallucination": 0.06}


@pytest.fixture(scope="module")
def cases():
    col = CaseCollector()
    run_tickets(SupportAgent(instrumentor=col), generate_tickets(600, seed=42, fault_rates=FAULTS))
    return col.cases


def test_claims_and_pii():
    assert ("id", "TRK00000000") in extract_claims("seguimiento TRK00000000")
    assert unsupported_claims("Reembolso de 1299,00 € (ref. RF-99999)", '{"amount_eur": 129.0}') != []
    assert unsupported_claims("Reembolso de 129.00 € del pedido ORD-00001", '{"amount_eur": 129.0, "order_id": "ORD-00001"}') == []
    assert find_pii("escribe a ana@example.com") and "[EMAIL]" in scrub_pii("ana@example.com")
    assert not find_pii("seguimiento TRK644252530")          # un tracking no es un teléfono


def test_rule_judge_is_exact_on_groundedness_and_pii(cases):
    j = RuleJudge()
    vs = [j.evaluate(c) for c in cases]
    g = confusion([v.scores["groundedness"].label == "fail" for v in vs], [not c.truth["grounded"] for c in cases])
    p = confusion([v.scores["pii_safety"].label == "fail" for v in vs], [c.truth["pii_leaked"] for c in cases])
    assert g["sensitivity"] == 1.0 and g["specificity"] == 1.0
    assert p["sensitivity"] == 1.0 and p["specificity"] == 1.0


def test_mock_judge_is_imperfect_but_deterministic(cases):
    j = MockJudge(42)
    a = [j.evaluate(c).scores["groundedness"].value for c in cases]
    b = [MockJudge(42).evaluate(c).scores["groundedness"].value for c in cases]
    assert a == b
    g = confusion([x < 0.5 for x in a], [not c.truth["grounded"] for c in cases])
    assert 0.8 < g["sensitivity"] < 1.0 and 0.9 < g["specificity"] < 1.0


def test_verbosity_bias_and_position_bias():
    j = MockJudge(42)
    base = EvalCase("x", "¿Cuál es la política de devoluciones?", "Según «Devoluciones» (KB-002): 30 días.", "30 días")
    padded = EvalCase("x", base.question, base.answer + " " + "Gracias por contactar con nosotros, estamos encantados de ayudarle. " * 4, base.context)
    assert j.evaluate(padded).scores["relevance"].value > j.evaluate(base).scores["relevance"].value
    same = "Según «Devoluciones» (KB-002): 30 días."
    first = [j.compare("¿devoluciones?", same, same + ".", key=str(i)) for i in range(60)]
    assert first.count("A") > 40                              # prefiere la primera posición ante empates


def test_llm_judge_parses_json_and_counts_parse_errors():
    j = LLMJudge(type("L", (), {"model": "mock-large"})())
    ok = j.parse("T1", 'ruido {"groundedness": {"score": 0.9, "explanation": "ok"}, "relevance": {"score": 1}, "resolution": {"score": 1}, "pii_safety": {"score": 1}}')
    assert ok.passed and ok.error is None
    bad = j.parse("T2", "no es json")
    assert bad.error == "parse_error" and not bad.passed
    assert isinstance(get_judge("rule"), RuleJudge) and isinstance(get_judge("mock"), MockJudge)


def test_samplers_are_consistent_and_weighted(cases):
    s = StratifiedSampler()
    d1 = [s.decide(c) for c in cases]
    assert d1 == [s.decide(c) for c in cases]
    assert all(p == 1.0 for ok, p, st in d1 if st == "error")
    assert abs(sum(ok for ok, _, _ in [RateSampler(0.2).decide(c) for c in cases]) / len(cases) - 0.2) < 0.06


def test_post_stratification_beats_naive(cases):
    ev = OnlineEvaluator(RuleJudge(), StratifiedSampler())
    for c in cases:
        ev.submit(c)
    ev.run_pending()
    est = ev.estimate_quality()
    truth = sum(not c.truth_bad for c in cases) / len(cases)
    rule = RuleJudge()
    full = sum(rule.evaluate(c).passed for c in cases) / len(cases)
    assert abs(est["estimate"] - full) < abs(est["naive"] - full)
    assert abs(est["estimate"] - full) < 0.04 and truth > 0


def test_stats():
    lo, hi = wilson_interval(8, 10)
    assert lo < 0.8 < hi
    assert required_sample_size(0.5, 0.05) == 385
    assert abs(rogan_gladen(0.10, 0.9, 0.95) - 0.0588) < 1e-3
    with pytest.raises(ValueError):
        rogan_gladen(0.1, 0.5, 0.4)
    est, se = post_stratified_rate({"a": (9, 10), "b": (5, 10)}, {"a": 900, "b": 100})
    assert abs(est - (0.9 * 0.9 + 0.1 * 0.5)) < 1e-12 and se > 0


def test_event_follows_semconv_names(cases):
    attrs = build_eval_event(cases[0], "groundedness", EvalScore.of(1.0, "ok"))
    assert attrs["gen_ai.evaluation.name"] == "groundedness" and attrs["gen_ai.evaluation.score.label"] == "pass"
    assert isinstance(attrs["gen_ai.evaluation.score.value"], float)


def test_feedback_has_response_bias(cases):
    fb = simulate_feedback(cases)
    by = {f.ticket_id: f.rating for f in fb}
    bad = [c for c in cases if c.truth_bad]
    good = [c for c in cases if not c.truth_bad]
    assert sum(c.ticket_id in by for c in bad) / len(bad) > 3 * sum(c.ticket_id in by for c in good) / len(good)


def test_online_evaluator_emits_telemetry():
    pytest.importorskip("opentelemetry.sdk")
    from supportops.telemetry import OTelInstrumentor, setup_telemetry
    from supportops.regression import event_records
    from supportops.instrument import CompositeInstrumentor
    ta = setup_telemetry("supportops-agent", mode="memory", set_global=False)
    te = setup_telemetry("supportops-evaluator", mode="memory", set_global=False)
    ev = OnlineEvaluator(MockJudge(), RateSampler(1.0), te)
    col = CaseCollector(on_case=ev.submit)
    agent = SupportAgent(instrumentor=CompositeInstrumentor(OTelInstrumentor(ta), col))
    run_tickets(agent, generate_tickets(10, seed=3))
    ev.run_pending()
    ta.force_flush(); te.force_flush()
    spans_a = {s["span_id"]: s for s in ta.span_records()}
    events = event_records(te)
    assert len(events) == 10 * 4
    for e in events[:8]:                                      # el evento cuelga del span `chat` evaluado
        assert spans_a[e["span_id"]]["name"].startswith("chat ")
    ev_spans = [s for s in te.span_records() if s["name"] == "supportops.evaluate"]
    assert len(ev_spans) == 10 and all(s["parent_span_id"] is None for s in ev_spans)
    chats = [s for s in te.span_records() if s["name"].startswith("chat ")]
    assert len(chats) == 10
    pts = {p["name"] for p in te.metric_points()}
    assert {"supportops.eval.results", "supportops.eval.cost", "supportops.eval.population"} <= pts
