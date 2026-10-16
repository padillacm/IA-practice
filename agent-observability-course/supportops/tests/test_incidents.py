"""Pruebas de la mesa de incidentes (módulo 21). Requieren [otel]."""
import pytest

pytest.importorskip("opentelemetry.sdk")
from supportops import incidents as I


@pytest.mark.parametrize("case", I.CASE_IDS)
def test_deterministic_and_graded(case):
    a, b = I.build_incident(case, 42), I.build_incident(case, 42)
    assert a is b                                              # caché
    f = I.reference_facts(case, a)
    cause, (start, _end), culprit, mits = I._TRUTH[case]
    perfect = {"cause": cause, "start_min": start, "end_min": _end, "culprit": f.get("culprit"), "mitigation": sorted(mits)[0],
               "evidence": {k: v for k, v in f.items() if k not in ("culprit", "no_tool_share_before")}}
    g = I.grade(case, perfect, a)
    assert g["score"] == g["of"], g
    wrong = dict(perfect, cause="traffic_spike", mitigation="scale_out")
    g2 = I.grade(case, wrong, a)
    assert not g2["checks"]["causa raíz"] and not g2["checks"]["mitigación"]


def test_signals_present_without_hints():
    a = I.build_incident("INC-A"); e = I.build_incident("INC-E"); d = I.build_incident("INC-D")
    assert a.metrics and all("root_cause" not in k for k in a.metrics[0])
    assert I.reference_facts("INC-A", a)["retry_amplification"] > 1.8                  # los reintentos amplifican
    assert I.reference_facts("INC-E", e)["orphan_share_after"] > 0.4                   # trazas partidas
    assert I.reference_facts("INC-D", d)["series_growth"] > 3                          # tormenta de cardinalidad
    b = I.build_incident("INC-B"); assert I.reference_facts("INC-B", b)["cost_ratio"] > 1.8
    c = I.build_incident("INC-C"); assert I.reference_facts("INC-C", c)["no_tool_share_after"] > 0.15
