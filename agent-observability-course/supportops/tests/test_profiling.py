"""Pruebas del módulo 17 (profiling). Las que necesitan Pyroscope real se saltan si no está en :4040."""
from __future__ import annotations

import gzip
import time
from collections import Counter

import pytest

from supportops import profiling as P


def test_pprof_roundtrip():
    rows = [(("main", "a", "b"), 30, {"span_id": "x1"}), (("main", "a", "c"), 10, {}), (("main", "d"), 5, {"k": "v"})]
    raw = P.encode_pprof(rows, period_ns=10_000_000, duration_ns=123)
    assert raw[:2] == b"\x1f\x8b"
    d = P.decode_pprof(raw)
    assert d["sample_type"] == [("cpu", "nanoseconds")] and d["period"] == 10_000_000 and d["duration_ns"] == 123
    got = sorted((s, v[0], l) for s, v, l in d["samples"])
    assert got == sorted((tuple(s), v, l) for s, v, l in rows)
    assert P.decode_pprof(P.encode_pprof(rows, gzip_it=False))["samples"] == d["samples"]


def test_folded_roundtrip_and_times():
    st = Counter({("a", "b", "c"): 6, ("a", "b"): 2, ("a", "d"): 2})
    assert P.parse_folded(P.folded_text(st)) == st
    assert P.self_time(st) == Counter({"c": 6, "b": 2, "d": 2})
    tt = P.total_time(st)
    assert tt["a"] == 10 and tt["b"] == 8 and tt["c"] == 6


def test_flame_rows_widths():
    st = Counter({("a", "b", "c"): 6, ("a", "b"): 2, ("a", "d"): 2})
    rows = P.flame_rows(st)
    by = {(r.depth, r.name): r for r in rows}
    assert by[(0, "a")].width == 10 and by[(1, "b")].width == 8 and by[(2, "c")].width == 6
    assert by[(1, "b")].self_n == 2 and by[(1, "d")].x == 8


def test_flamebearer_to_stacks():
    # total 10: a(10) -> b(8: self 2) -> c(6), a -> d(2)
    fb = {"names": ["total", "a", "b", "c", "d"], "total": 10,
          "levels": [[0, 10, 0, 0], [0, 10, 0, 1], [0, 8, 2, 2, 0, 2, 2, 4], [0, 6, 6, 3]]}
    assert P.flamebearer_to_stacks(fb) == Counter({("a", "b", "c"): 6, ("a", "b"): 2, ("a", "d"): 2})


def test_pii_scanners_agree_and_luhn():
    text = "Contacta ops7@supportops.example o a.b+c@x.org, tarjeta 4111 1111 1111 1111 y pedido 1234 5678."
    assert P.scan_pii_slow(text) == P.scan_pii_fast(text) == {"emails": 2, "cards": 1}
    assert P.luhn_ok("4111111111111111") and not P.luhn_ok("4111111111111112")
    big = P.policy_text()
    assert P.scan_pii_slow(big) == P.scan_pii_fast(big)
    assert P.count_tokens_slow(big) == P.count_tokens_fast(big)


def test_sampler_finds_hot_function():
    def hot():
        t = time.perf_counter()
        x = 0
        while time.perf_counter() - t < 0.4:
            x += 1
        return x

    with P.SamplingProfiler(hz=200, mode="cpu") as p:
        hot()
    assert p.total >= 10
    assert P.self_time(p.stacks()).most_common(1)[0][0].endswith("hot")


def test_sampler_wall_sees_sleep_cpu_does_not():
    def idle():
        time.sleep(0.4)

    w = P.SamplingProfiler(hz=100, mode="wall")
    c = P.SamplingProfiler(hz=100, mode="cpu")
    with w, c:
        idle()
    assert w.total >= 10 and c.total <= 2


def test_sampler_tags():
    p = P.SamplingProfiler(hz=300, mode="wall")
    with p:
        with p.tag(span_id="abc"):
            time.sleep(0.15)
        time.sleep(0.1)
    assert p.tag_values("span_id")["abc"] >= 5
    assert p.total > p.tag_values("span_id")["abc"]
    assert sum(p.stacks(span_id="abc").values()) == p.tag_values("span_id")["abc"]


def test_workload_fast_is_equivalent_and_faster():
    a = P.run_workload("slow", n=30)
    b = P.run_workload("fast", n=30)
    assert [r.status for r in a.results] == [r.status for r in b.results]
    assert [r.input_tokens for r in a.results] == [r.input_tokens for r in b.results]
    assert a.rerank_order == b.rerank_order and len(a.rerank_order) > 3
    assert abs(a.pii_found["emails"] - b.pii_found["emails"]) <= 2 + a.pii_found["emails"] // 100   # ventanas de fusión de correos en los bordes
    assert a.cpu_s > 3 * b.cpu_s


def test_profile_attributes_pii_scan():
    p = P.SamplingProfiler(hz=300, mode="cpu")
    s = P.run_workload("slow", n=40, profiler=p)
    top = P.self_time(p.stacks()).most_common(1)[0][0]
    assert top.endswith("scan_pii_slow")
    sh = P.stage_shares(p.stacks())
    assert abs(sh["pii_scan"] - s.stage_share()["pii_scan"]) < 0.2


def test_custom_hooks_and_amdahl():
    s = P.run_workload("slow", n=10, scan_fn=P.scan_pii_fast, tokens_fn=P.count_tokens_fast)
    assert s.pii_found["emails"] > 0
    assert P.amdahl_speedup(0.5, 2) == pytest.approx(4 / 3)
    assert P.amdahl_speedup(0.9, 1e9) == pytest.approx(10, rel=1e-3)


def test_cost_model():
    m = P.profile_cost_model(100, 100, 50_000, 10, 30)
    assert m["profiles_per_day"] == 864_000 and m["ingest_mb_per_day"] == pytest.approx(43_200)


def test_dashboard_lints():
    from supportops.dashkit import lint
    d = P.profiling_dashboard()
    assert lint(d.to_dict()) == []


pyro = P.PyroscopeClient()


@pytest.mark.skipif(not pyro.ready(), reason="Pyroscope no está en :4040")
def test_live_push_and_query():
    p = P.SamplingProfiler(hz=300, mode="cpu")
    P.run_workload("slow", n=25, profiler=p)
    app = f"pytest-{int(time.time())}"
    pyro.push_connect({"service_name": app, "variant": "slow"}, p.to_pprof())
    assert pyro.wait_for('{service_name="%s"}' % app, timeout_s=60) > 0
    st = pyro.stacks('{service_name="%s"}' % app)
    assert P.self_time(st).most_common(1)[0][0].endswith("scan_pii_slow")
