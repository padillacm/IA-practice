"""Pruebas del mini motor TraceQL (autor A3). Ejecutar: pytest agent-observability-course/supportops/tests/test_traceql_mini.py"""
import pytest

from supportops.traceql_mini import TraceQLSyntaxError, parse, search, ticket_ids


def sp(tid, sid, parent, name, svc="a", kind="INTERNAL", status="UNSET", dur_ms=10, start=0, **attrs):
    return {"trace_id": tid, "span_id": sid, "parent_span_id": parent, "name": name, "kind": kind, "status": status, "status_message": None,
            "start_unix_nano": start * 1_000_000, "end_unix_nano": (start + dur_ms) * 1_000_000, "attributes": attrs, "events": [],
            "resource": {"service.name": svc}, "scope": "t"}


def mk():
    t1 = [sp("t1", "a", None, "root", "front", "SERVER", dur_ms=100, **{"http.status_code": 200}),
          sp("t1", "b", "a", "db", "back", "CLIENT", dur_ms=40, start=5, **{"db.system": "postgresql"}),
          sp("t1", "c", "a", "cache", "front", "CLIENT", status="ERROR", dur_ms=5, start=50)]
    t2 = [sp("t2", "d", None, "root", "front", "SERVER", dur_ms=300, **{"http.status_code": 500}),
          sp("t2", "e", "d", "db", "back", "CLIENT", status="ERROR", dur_ms=250, start=10),
          sp("t2", "f", "e", "retry", "back", "INTERNAL", dur_ms=1, start=20)]
    return t1 + t2


def ids(q, spans=None):
    return sorted(h.trace_id for h in search(spans or mk(), q))


def test_selectors():
    assert ids('{ resource.service.name = "front" }') == ["t1", "t2"]
    assert ids("{ status = error }") == ["t1", "t2"]
    assert ids("{ span.http.status_code >= 500 }") == ["t2"]
    assert ids('{ name =~ "d." }') == ["t1", "t2"]               # regex anclada: "d." = 'db'
    assert ids('{ name =~ "d" }') == []
    assert ids("{ duration > 200ms }") == ["t2"]
    assert ids("{ trace:duration > 250ms }") == ["t2"]
    assert ids("{ span.db.system = nil }") == ["t1", "t2"]
    assert ids("{ span.db.system != nil }") == ["t1"]
    assert ids('{ .db.system = "postgresql" }') == ["t1"]
    assert ids("{ kind = server && span.http.status_code = 200 }") == ["t1"]


def test_missing_attribute_never_matches_comparisons():
    assert ids('{ span.http.status_code != 200 }') == ["t2"]       # t1 tiene un span con 200 y otros SIN atributo: no cuentan


def test_logical_between_spansets_vs_inside_braces():
    assert ids('{ span.db.system = "postgresql" } && { status = error }') == ["t1"]
    assert ids('{ span.db.system = "postgresql" && status = error }') == []   # ningún span cumple ambas
    assert ids('{ span.http.status_code = 200 } || { span.http.status_code = 500 }') == ["t1", "t2"]


def test_structural():
    assert ids('{ name = "root" } >> { status = error }') == ["t1", "t2"]
    assert ids('{ name = "root" } > { status = error }') == ["t1", "t2"]        # el error es hijo directo de la raíz en ambas trazas
    assert ids('{ name = "root" } > { name = "retry" }') == []                  # retry es nieto de la raíz en t2: no es hijo directo
    assert ids('{ name = "root" } >> { name = "retry" }') == ["t2"]
    hits = search(mk(), '{ name = "db" } > { name = "retry" }')
    assert [h.trace_id for h in hits] == ["t2"] and [s["name"] for s in hits[0].spansets[0]] == ["retry"]   # devuelve el lado derecho
    assert ids('{ name = "db" } ~ { name = "cache" }') == ["t1"]
    assert ids('{ name = "retry" } << { name = "root" }') == ["t2"]


def test_pipeline():
    assert ids("{ } | count() > 3") == []
    assert ids("{ } | count() >= 3") == ["t1", "t2"]
    assert ids("{ } | max(duration) > 200ms") == ["t2"]
    assert ids("{ } | avg(duration) > 100ms") == ["t2"]
    assert ids("{ status = error } | by(resource.service.name) | count() >= 1") == ["t1", "t2"]
    assert ids("{ kind = client } | by(resource.service.name) | count() > 1") == []


def test_syntax_errors():
    for bad in ["{ name = }", "{ bogus = 1 }", "{ name = 'x' }", "{ } | rate()", "{ } &>> { }"]:
        with pytest.raises(TraceQLSyntaxError):
            search(mk(), bad)


def test_ticket_ids():
    spans = mk()
    spans[0]["attributes"]["supportops.ticket.id"] = "T-1"
    spans[3]["attributes"]["supportops.ticket.id"] = "T-2"
    assert ticket_ids(spans, search(spans, "{ status = error }")) == ["T-1", "T-2"]


def test_parse_returns_ast():
    ast, stages = parse("{ span.x = 1 } | count() > 2")
    assert ast[0] == "filter" and stages[0][0] == "count"
