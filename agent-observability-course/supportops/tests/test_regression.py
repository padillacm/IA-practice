"""Pruebas del módulo 15: variantes de prompt, estadística de comparación, drift, canarios y huella estructural."""
import os

import pytest

os.environ.setdefault("LLM_PROVIDER", "mock")
from supportops import generate_tickets, DEFAULT_FAULT_RATES
from supportops.quality_eval import MockJudge
from supportops.regression import (Cusum, ReleaseGate, behavior_fingerprint, bootstrap_diff, canary_route, js_divergence, ks_2samp, mcnemar_exact,
                                   min_detectable_drop, novel_topic_tickets, peeking_false_positive_rate, psi, psi_categorical, replay, required_n_per_arm,
                                   run_version, select_golden, golden_to_tickets, sprt_bernoulli, trajectory_match, two_proportion_test, trace_shapes)

TK = generate_tickets(500, seed=42, fault_rates=DEFAULT_FAULT_RATES)


def test_v2_regression_is_silent_in_classic_metrics_but_visible_in_quality():
    j = MockJudge(42)
    out = {}
    for v in ("v1", "v2"):
        res, cases = run_version(v, TK)
        out[v] = (res, cases, sum(j.evaluate(c).scores["groundedness"].label == "pass" for c in cases) / len(cases))
    r1, r2 = out["v1"][0], out["v2"][0]
    lat = lambda r: sum(x.latency_s for x in r) / len(r)
    assert lat(r2) < lat(r1)                                  # «mejora» la latencia
    assert sum(x.status in ("error", "max_steps") for x in r2) == sum(x.status in ("error", "max_steps") for x in r1)
    assert out["v2"][2] < out["v1"][2] - 0.08                 # pero la calidad cae
    assert sum(not c.truth["grounded"] for c in out["v2"][1]) > 3 * sum(not c.truth["grounded"] for c in out["v1"][1])


def test_two_proportion_and_power():
    t = two_proportion_test(90, 100, 70, 100)
    assert t["diff"] == pytest.approx(-0.2) and t["p_value"] < 0.01 and t["ci_high"] < 0
    assert 600 < required_n_per_arm(0.90, 0.85) < 800
    assert 0.05 < min_detectable_drop(300, 0.9) < 0.09
    assert mcnemar_exact(10, 0) < 0.01 and mcnemar_exact(5, 5) == 1.0
    d, lo, hi = bootstrap_diff([0, 1, 1, 1] * 25, [0, 0, 1, 0] * 25)
    assert lo < d < hi and d < 0


def test_golden_dataset_and_gate():
    res, cases = run_version("v1", TK)
    j = MockJudge(42)
    verdicts = {c.ticket_id: j.evaluate(c) for c in cases}
    gold = select_golden(cases, verdicts, n_total=40, tools_by_ticket={r.ticket_id: r.tools_used for r in res})
    assert 20 <= len(gold) <= 40 and len({g.question for g in gold}) == len(gold)
    assert any(g.reason == "judge_fail" for g in gold) and all("@" not in g.question for g in gold)
    src = {t.ticket_id: t for t in TK}
    tk = golden_to_tickets(gold, src)
    base, cand = replay(gold, tk, "v1", j), replay(gold, tk, "v2", j)
    dec_ok, _ = ReleaseGate().decide(base, base)
    assert dec_ok == "ship"
    assert trajectory_match(["get_order"], ["search_kb", "get_order"]) and not trajectory_match(["get_order", "issue_refund"], ["issue_refund"])


def test_drift_metrics():
    import random
    r = random.Random(1)
    a = [r.gauss(0, 1) for _ in range(2000)]
    b = [r.gauss(0, 1) for _ in range(2000)]
    c = [r.gauss(0.8, 1) for _ in range(2000)]
    assert psi(a, b) < 0.05 < 0.25 < psi(a, c)
    assert ks_2samp(a, b)[1] > 0.01 and ks_2samp(a, c)[1] < 1e-6
    assert js_divergence({"x": 1, "y": 1}, {"x": 1, "y": 1}) == 0 and js_divergence({"x": 1}, {"y": 1}) == pytest.approx(1.0)
    assert psi_categorical({"a": 50, "b": 50}, {"a": 50, "b": 50}) == pytest.approx(0, abs=1e-9)
    s = [0.95] * 40 + [0.80] * 20
    i = Cusum(0.95, k=0.02, h=0.3).first_alarm(s)
    assert i is not None and 40 <= i <= 44


def test_canary_sprt_and_peeking():
    share = sum(canary_route(f"T{i}", 0.1) == "canary" for i in range(5000)) / 5000
    assert 0.08 < share < 0.12 and canary_route("T1") == canary_route("T1")
    assert sprt_bernoulli(0, 200, 0.05, 0.10)[0] == "promote"
    assert sprt_bernoulli(30, 100, 0.05, 0.10)[0] == "rollback"
    pk = peeking_false_positive_rate(trials=150)
    assert pk["fixed_sample_peeking"] > 2 * pk["nominal"] and pk["sprt"] < 0.1


def test_novel_topics_degrade_quality_and_fingerprint():
    res, cases = run_version("v1", novel_topic_tickets(40))
    j = MockJudge(42)
    assert sum(j.evaluate(c).passed for c in cases) / 40 < 0.6
    fp = behavior_fingerprint([dict(r.to_dict(), n_tool_calls=r.n_tool_calls) for r in res])
    assert fp["n"] == 40


def test_trace_shapes_from_telemetry():
    pytest.importorskip("opentelemetry.sdk")
    from supportops.telemetry import OTelInstrumentor, setup_telemetry
    from supportops.quality_eval import VersionTagInstrumentor
    tel = setup_telemetry("supportops-agent", mode="memory", set_global=False)
    res, _ = run_version("v2", TK[:60], instrumentors=[OTelInstrumentor(tel), VersionTagInstrumentor("v2")])
    shapes = trace_shapes(tel.span_records())
    assert len(shapes) == 60 and {s["version"] for s in shapes.values()} == {"v2"}
    assert sum(s["n_tool"] == 0 for s in shapes.values()) >= sum(r.n_tool_calls == 0 for r in res) - 0
