"""Pruebas del módulo 18 (muestreo, cardinalidad, coste). Las que usan Docker se saltan si no hay daemon."""
from __future__ import annotations

import math

import pytest

from supportops import sampling as S


@pytest.fixture(scope="module")
def corpus():
    return S.build_corpus(1500, seed=42)


def test_corpus_deterministic_and_sizes(corpus):
    again = S.build_corpus(1500, seed=42)
    assert [t.trace_id for t in corpus.traces] == [t.trace_id for t in again.traces]
    assert corpus.total_bytes == again.total_bytes > 0
    sm = corpus.summary()
    assert 3 < sm["spans_per_trace"] < 8 and 300 < sm["bytes_per_span"] < 900
    assert 0.0 < sm["interesting_rate"] < 0.3


def test_spans_to_otlp_roundtrip_counts(corpus):
    t = corpus.traces[0]
    req = S.spans_to_otlp(t.spans)
    n = sum(len(ss.spans) for rs in req.resource_spans for ss in rs.scope_spans)
    assert n == t.n_spans and req.ByteSize() == t.bytes


def test_head_keep_deterministic_and_ratio(corpus):
    ids = [t.trace_id for t in corpus.traces]
    assert [S.head_keep(i, 0.1) for i in ids] == [S.head_keep(i, 0.1) for i in ids]
    frac = sum(S.head_keep(i, 0.25) for i in ids) / len(ids)
    assert 0.15 < frac < 0.35
    assert all(S.head_keep(i, 1.0) for i in ids) and not any(S.head_keep(i, 0.0) for i in ids)


def test_tail_policies_semantics(corpus):
    ctx = S.TailContext()
    err = next(t for t in corpus.traces if t.error)
    ok = next(t for t in corpus.traces if not t.interesting)
    assert S.StatusCode(("ERROR",)).decide(err, ctx) == "sampled" and S.StatusCode(("ERROR",)).decide(ok, ctx) == "not_sampled"
    assert S.Latency(0).decide(ok, ctx) == "sampled" and S.Latency(10**9).decide(ok, ctx) == "not_sampled"
    assert S.SpanCount(2, 50).decide(ok, ctx) == "sampled" and S.SpanCount(1000).decide(ok, ctx) == "not_sampled"
    assert S.And((S.Latency(0), S.StatusCode(("ERROR",)))).decide(ok, ctx) == "not_sampled"
    assert S.Drop((S.Latency(0),)).decide(ok, ctx) == "dropped"
    assert S.final_decision(["sampled", "dropped"]) is False and S.final_decision(["not_sampled", "sampled"]) is True and S.final_decision(["not_sampled"]) is False


def test_tail_keeps_all_interesting_and_matches_budget(corpus):
    pol = [S.StatusCode(("ERROR",), name="errors"), S.Latency(5000, name="slow"), S.AttrCompare(name="costly"), S.Probabilistic(10, name="baseline")]
    res = S.TailSampler(pol, 30).run(corpus.traces)
    cov = S.coverage(res.kept, corpus)
    assert cov["recall_interesting_pct"] == 100.0
    assert 10 < cov["kept_bytes_pct"] < 40 and not res.dropped_too_early
    head = S.coverage(S.head_sample(corpus.traces, 0.10), corpus)
    assert head["recall_interesting_pct"] < 40


def test_tail_memory_limit_drops_before_deciding(corpus):
    pol = [S.StatusCode(("ERROR",), name="errors")]
    fast = S.rescale_rate(corpus.traces, 200)
    big = S.TailSampler(pol, 30, num_traces=10**9).run(fast)
    small = S.TailSampler(pol, 30, num_traces=50).run(fast)
    assert not big.dropped_too_early and len(small.dropped_too_early) > 0.5 * len(fast)
    assert big.peak_traces > 50
    assert S.coverage(small.kept, corpus)["recall_error_pct"] < 50


def test_peak_traces_scales_with_wait(corpus):
    pol = [S.StatusCode(("ERROR",))]
    r = S.rescale_rate(corpus.traces, 16)
    p10 = S.TailSampler(pol, 10, 10**9).run(r).peak_traces
    p30 = S.TailSampler(pol, 30, 10**9).run(r).peak_traces
    assert p30 > 2 * p10 * 0.8


def test_rescale_keeps_duration(corpus):
    r = S.rescale_rate(corpus.traces, 10)
    assert all(abs(a.duration_s - b.duration_s) < 1e-9 for a, b in zip(corpus.traces, r))
    assert max(t.start_s for t in r) < max(t.start_s for t in corpus.traces)


def test_bias_and_weights(corpus):
    pol = [S.StatusCode(("ERROR",), name="errors"), S.Latency(5000, name="slow"), S.AttrCompare(name="costly"), S.Probabilistic(10, name="baseline")]
    kept = S.TailSampler(pol, 30).run(corpus.traces).kept
    truth = S.estimate_metrics(corpus.traces)
    naive = S.estimate_metrics(kept)
    w = S.estimate_metrics(kept, S.inclusion_weights(kept, lambda t: t.interesting, 0.10))
    assert naive["error_rate"] > 4 * truth["error_rate"]
    assert abs(w["error_rate"] / truth["error_rate"] - 1) < 0.3
    assert abs(w["requests"] / len(corpus) - 1) < 0.3


def test_weighted_quantile():
    assert S.weighted_quantile([1, 2, 3], [1, 1, 1], 0.5) == 2
    assert S.weighted_quantile([1, 2, 3], [10, 1, 1], 0.5) == 1


def test_numeric_attribute_rejects_decimals_and_config_shapes():
    with pytest.raises(ValueError):
        S.NumericAttribute("k", 0.0005).to_config()
    assert S.NumericAttribute("k", 500).to_config() == {"name": "numeric", "type": "numeric_attribute", "numeric_attribute": {"key": "k", "min_value": 500}}
    assert S.AttrCompare().to_config()["ottl_condition"]["span"] == ['attributes["supportops.cost_usd"] > 0.0005']
    cfg = S.And((S.Latency(100), S.StatusCode(("ERROR",)))).to_config()
    assert [p["type"] for p in cfg["and"]["and_sub_policy"]] == ["latency", "status_code"]


def test_collector_config_structure_and_yaml():
    yaml = pytest.importorskip("yaml")
    txt = S.collector_config([S.StatusCode(("ERROR",), name="e"), S.Probabilistic(10, name="b")])
    d = yaml.safe_load(txt)
    assert d["processors"]["tail_sampling"]["policies"][0]["status_code"]["status_codes"] == ["ERROR"]
    assert d["service"]["pipelines"]["traces/in"]["exporters"] == ["forward", "span_metrics"]
    assert d["service"]["pipelines"]["traces/sampled"]["processors"] == ["tail_sampling"]
    assert yaml.safe_load(S.to_yaml({"a": [{"b": 1, "c": "x: y"}], "d": {"e": True}})) == {"a": [{"b": 1, "c": "x: y"}], "d": {"e": True}}


def test_cardinality_and_costs():
    assert S.series_estimate({"a": 4, "b": 5, "c": 3}) == 60
    txt = 'foo_total{a="1"} 3\nfoo_total{a="2"} 4\nbar{x="1",y="2"} 1\n# HELP\n'
    assert S.count_series(txt) == {"foo_total": 2, "bar": 1}
    assert S.storm_growth(1000, 1.0)["series"] == 1040
    m = S.StackCostModel(tickets_per_day=1_000_000, spans_per_trace=10, bytes_per_span=1000)
    assert m.daily_gb()["traces_ingest"] == pytest.approx(10.0)
    half = S.StackCostModel(tickets_per_day=1_000_000, spans_per_trace=10, bytes_per_span=1000, trace_keep=0.5)
    assert half.monthly_cost({"traces": 7})["traces"] == pytest.approx(0.5 * m.monthly_cost({"traces": 7})["traces"])
    rc = S.retention_cost(10, [("hot", 7, 0.1), ("cold", 23, 0.02)])
    assert rc[0]["usd_per_month"] == pytest.approx(7.0) and rc[1]["resident_gb"] == 230


def test_pareto_front():
    assert S.pareto_front([(1, 1), (2, 3), (3, 2), (0.5, 0.2)]) == [0, 1, 3]


def test_dashboard_lints():
    import sys, pathlib
    from supportops.dashkit import lint
    import json
    d = json.loads((pathlib.Path(__file__).resolve().parents[2] / "stack" / "grafana" / "dashboards" / "18-escala-coste.json").read_text())
    assert lint(d) == []


needs_docker = pytest.mark.skipif(not S.docker_ok(), reason="sin daemon de Docker")


@needs_docker
def test_collector_validate_and_real_tail_matches_simulator(corpus):
    pol = [S.StatusCode(("ERROR",), name="errors"), S.Latency(5000, name="slow"), S.AttrCompare(name="costly"), S.Probabilistic(10, name="baseline")]
    ok, msg = S.validate_collector_config(S.collector_config(pol))
    assert ok, msg
    bad, _ = S.validate_collector_config("receivers: {}\nservice: {pipelines: {traces: {receivers: [nope]}}}\n")
    assert not bad
    r = S.run_collector_experiment(corpus, pol, decision_wait="2s")
    assert not r["crashed"] and r["coverage"]["recall_interesting_pct"] == 100.0
    sim = S.TailSampler(pol, 2).run(corpus.traces)
    for name in ("errors", "slow", "costly"):
        assert r["per_policy"].get(name, 0) == sim.by_policy.get(name, 0)
    red_err = r["red"].get("STATUS_CODE_ERROR", 0) / sum(r["red"].values())
    truth = sum(t.error for t in corpus.traces) / len(corpus)
    assert red_err == pytest.approx(truth)


@needs_docker
def test_numeric_attribute_double_crashes_collector(corpus):
    probe = S.numeric_attribute_probe(S.Corpus(corpus.traces[:150], corpus.duration_s, 42))
    assert probe["double + min_value decimal (0.0005)"].startswith("CRASH") and probe["ottl_condition  > 0.0005"].startswith("ok")
