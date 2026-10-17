"""Pruebas del módulo 16: SLOs, burn rate multiventana, presupuesto y alertas provisionadas."""
import os

import numpy as np
import pytest
import yaml

os.environ.setdefault("LLM_PROVIDER", "mock")
from supportops.slo import (DEFAULT_SLOS, GOOGLE_POLICIES, LAB_POLICIES, MultiWindowPolicy, alert_quality, bin_events, budget_report, burn_promql, burn_series,
                            fire_series, grafana_burn_rule, minute_mask, pages_per_week, render_postmortem, rules_yaml, simulate_day, simulate_month,
                            sli_promql, threshold_fire_series)


def test_burn_rate_arithmetic():
    good, total = np.array([98.0] * 10), np.array([100.0] * 10)       # 2 % malos con objetivo 99,9 % → burn 20
    assert burn_series(good, total, 5, 0.999)[-1] == pytest.approx(20.0)
    assert GOOGLE_POLICIES[0].budget_consumed() == pytest.approx(0.02, rel=0.01)
    assert GOOGLE_POLICIES[1].budget_consumed() == pytest.approx(0.05, rel=0.01)
    assert GOOGLE_POLICIES[2].budget_consumed() == pytest.approx(0.10, rel=0.01)
    assert all(p.short_min * 12 == p.long_min for p in GOOGLE_POLICIES)


def test_multiwindow_resets_fast_and_ignores_blips():
    n = 400
    total = np.full(n, 100.0)
    good = total.copy()
    good[100:130] = 40                                                  # incidente de 30 min con 60 % de fallos
    inc = minute_mask(100, 130, n)
    p = MultiWindowPolicy("fast", 14.4, 60, 5, "page")
    f = fire_series(good, total, 0.99, p)
    q = alert_quality(f, inc, reset_slack_min=5)
    # 14,4 % de 60 min con 60 % de fallos = 14,4 min hasta superar el umbral largo
    assert q["detected"] and 14 <= q["ttd_min"] <= 15 and q["precision"] > 0.5
    g2 = total.copy(); g2[200:202] = 20                                  # 2 min de fallos (80 %): una ráfaga, no un incidente
    assert not fire_series(g2, total, 0.99, p).any()
    assert threshold_fire_series(good, total, 0.05, 5).sum() >= f.sum()   # la ingenua dispara al menos tanto


def test_budget_report():
    r = budget_report(good=9_950, total=10_000, objective=0.995)
    assert r["consumed"] == pytest.approx(1.0) and r["remaining"] == pytest.approx(0.0, abs=1e-12)
    r2 = budget_report(good=9_990, total=10_000, objective=0.99, elapsed_frac=0.5)
    assert r2["avg_burn_rate"] == pytest.approx(0.2) and r2["exhaustion_frac"] == pytest.approx(5.0)


def test_simulate_month_and_day_are_deterministic():
    g, t = simulate_month(1, incidents=[(3, 4, 60, 0.5)])
    g2, t2 = simulate_month(1, incidents=[(3, 4, 60, 0.5)])
    assert (g == g2).all() and len(g) == 30 * 24 * 60
    assert (t[3 * 1440 + 240: 3 * 1440 + 300] - g[3 * 1440 + 240: 3 * 1440 + 300]).sum() > 0.4 * t[3 * 1440 + 240: 3 * 1440 + 300].sum()
    d = simulate_day(7)
    d2 = simulate_day(7)
    assert [r["status"] for r in d["rows"]] == [r["status"] for r in d2["rows"]]


def test_incident_day_pages_on_availability_but_not_on_quality_regression():
    d = simulate_day(42)
    nb = d["n_bins"]
    av = DEFAULT_SLOS["availability"]
    g, t = bin_events(d["rows"], av, t0=d["t0"], n_bins=nb)
    inc = minute_mask(*d["truth"]["outage"], nb)
    q = alert_quality(fire_series(g, t, av.objective, GOOGLE_POLICIES[0]), inc, reset_slack_min=60)
    assert q["detected"] and q["ttd_min"] <= 15 and q["false_intervals"] == 0
    ql = DEFAULT_SLOS["quality"]
    gq, tq = bin_events(d["rows"], ql, t0=d["t0"], n_bins=nb)
    assert not fire_series(gq, tq, ql.objective, GOOGLE_POLICIES[0]).any()    # la regresión de calidad es lenta: no despierta a nadie
    reg = slice(int(d["truth"]["regression"][0]) + 60, int(d["truth"]["regression"][1]))
    assert 1 - gq[reg].sum() / tq[reg].sum() > 2 * ql.budget                    # …pero consume presupuesto > 2× el sostenible


def test_promql_and_grafana_rule_shape():
    for k, s in DEFAULT_SLOS.items():
        assert "rate(" in sli_promql(s.sli, "5m", s.threshold) and "/" in burn_promql(s, "5m")
    r = grafana_burn_rule(DEFAULT_SLOS["availability"], LAB_POLICIES[0], dashboard_uid="slo-agente", panel_id=3)
    assert r["annotations"]["__dashboardUid__"] == "slo-agente" and r["annotations"]["__panelId__"] == "3"
    assert r["condition"] == "F" and [d["refId"] for d in r["data"]] == list("ABCDEF")
    y = yaml.safe_load(rules_yaml([r], interval="30s"))
    assert y["groups"][0]["interval"] == "30s"
    with pytest.raises(ValueError):
        rules_yaml([r], interval="15s")


def test_pages_per_week_and_postmortem():
    f = np.zeros(2880, bool); f[100:120] = True; f[1500:1510] = True
    assert pages_per_week(f) == pytest.approx(2 * 7 / 2)
    md = render_postmortem({"title": "t", "summary": "s", "impact": ["i"], "timeline": [("10:00", "e")], "root_cause": "r", "actions": [("a", "equipo", "1 sem", "prevenir")]})
    assert "## Cronología" in md and "| a | equipo |" in md
