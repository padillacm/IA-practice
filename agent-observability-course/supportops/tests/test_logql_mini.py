"""Pruebas del mini motor LogQL (autor A3)."""
import os
import pytest
os.environ.setdefault("LLM_PROVIDER", "mock")
from supportops import logql_mini as lq


def E(ts, line, svc="a", **meta):
    return lq.Entry(ts, line, {"service_name": svc}, dict(meta))


DATA = [E(1, '{"level":"info","msg":"ok","ticket_id":"T1","n":5}', "agent", trace_id="t1"),
        E(2, '{"level":"error","msg":"boom","ticket_id":"T2","n":9}', "agent", trace_id="t2"),
        E(3, 'level=info method=GET route=/orders status=200 duration_ms=12.5', "gw", trace_id="t1"),
        E(4, 'level=error method=POST route=/chat status=503 duration_ms=840', "gw", trace_id="t2"),
        E(5, 'level=warn method=POST route=/chat status=429 duration_ms=90 msg="too many"', "gw", trace_id="t3")]


def n(q):
    return len(lq.query(DATA, q))


def test_selectors_and_line_filters():
    assert n('{service_name="gw"}') == 3
    assert n('{service_name=~"a.*"}') == 2
    assert n('{service_name!="gw"}') == 2
    assert n('{service_name="gw"} |= "503"') == 1
    assert n('{service_name="gw"} != "POST"') == 1
    assert n('{service_name="gw"} |~ "status=(429|503)"') == 2
    assert n('{service_name="gw"} !~ "route=/chat"') == 1


def test_parsers_and_label_filters():
    assert n('{service_name="agent"} | json | level="error"') == 1
    assert n('{service_name="agent"} | json | n > 6') == 1
    assert n('{service_name="gw"} | logfmt | status >= 500') == 1
    assert n('{service_name="gw"} | logfmt | status >= 400 and route="/chat"') == 2
    assert n('{service_name="gw"} | logfmt | status = 200 or status = 503') == 2
    assert n('{service_name="gw"} | logfmt | duration_ms > 100') == 1
    assert n('{service_name="gw"} | logfmt | route=~"/ch.*"') == 2


def test_structured_metadata_is_label():
    assert n('{service_name=~".+"} | trace_id="t1"') == 2
    assert n('{service_name="gw"} | logfmt | trace_id="t2" | status >= 500') == 1


def test_order_and_limit():
    r = lq.query(DATA, '{service_name="gw"}')
    assert [e.ts_ns for e in r] == [5, 4, 3]
    assert len(lq.query(DATA, '{service_name="gw"}', limit=2)) == 2


def test_errors():
    for bad in ['{service_name="gw"} | line_format "x"', 'rate({service_name="gw"}[1m])', 'service_name="gw"', '{}']:
        with pytest.raises(lq.LogQLSyntaxError):
            lq.query(DATA, bad)


def test_entries_from_payload():
    from supportops.loki_lab import LokiPusher
    p = LokiPusher("http://127.0.0.1:1")
    p.add(10, "hola", {"service_name": "x"}, {"trace_id": "t"})
    es = lq.entries_from_payload(p.payload())
    assert es[0].metadata == {"trace_id": "t"} and es[0].labels == {"service_name": "x"}
