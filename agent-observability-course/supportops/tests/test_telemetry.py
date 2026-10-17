"""Pruebas de supportops.telemetry (setup_telemetry + OTelInstrumentor). No necesitan red ni Docker.

Se saltan si no está instalado el SDK de OpenTelemetry (extra ``[otel]``).
"""
import http.server
import json
import threading

import pytest

pytest.importorskip("opentelemetry.sdk")

from supportops import (CompositeInstrumentor, DEFAULT_FAULT_RATES, FaultSpec, RecordingInstrumentor, SupportAgent, Ticket,  # noqa: E402
                        generate_tickets, run_tickets)
from supportops.telemetry import (OTelInstrumentor, normalize_finish_reason, setup_telemetry)  # noqa: E402


def ticket(text, faults=(), tid="T-tel-1"):
    return Ticket(tid, "C-0001", "premium", "chat", text, "x", 1_788_253_200.0, faults=list(faults))


@pytest.fixture()
def tel():
    h = setup_telemetry("supportops-agent", mode="memory", deterministic_ids=True)
    yield h
    h.shutdown()


def run(tel, n=30, seed=1, **kw):
    instr = OTelInstrumentor(tel, **kw)
    results = run_tickets(SupportAgent(instrumentor=instr), generate_tickets(n, seed, fault_rates=DEFAULT_FAULT_RATES))
    return instr, results


def test_span_tree_matches_agent_steps(tel):
    instr, results = run(tel, 20)
    spans = tel.span_records()
    roots = [s for s in spans if s["parent_span_id"] is None]
    assert len(roots) == len(results) == 20
    assert all(s["name"] == "invoke_agent supportops-agent" and s["kind"] == "INTERNAL" for s in roots)
    by_trace: dict[str, list] = {}
    for s in spans:
        by_trace.setdefault(s["trace_id"], []).append(s)
    for r in results:
        tid = instr.trace_ids[r.ticket_id]
        tspans = by_trace[tid]
        assert sum(s["name"].startswith("chat ") for s in tspans) == r.n_llm_calls   # incluye los intentos fallidos
        assert sum(s["name"].startswith("execute_tool ") for s in tspans) == r.n_tool_calls
        root = next(s for s in tspans if s["parent_span_id"] is None)
        assert (root["end_unix_nano"] - root["start_unix_nano"]) / 1e9 == pytest.approx(r.latency_s, abs=1e-6)
        ids = {s["span_id"] for s in tspans}
        assert all(s["parent_span_id"] in ids for s in tspans if s["parent_span_id"])


def test_genai_attributes_and_kinds(tel):
    run(tel, 20)
    spans = tel.span_records()
    chat = [s for s in spans if s["name"].startswith("chat ")]
    tools = [s for s in spans if s["name"].startswith("execute_tool ")]
    assert chat and tools
    assert all(s["kind"] == "CLIENT" and s["attributes"]["gen_ai.operation.name"] == "chat"
               and s["attributes"]["gen_ai.provider.name"] == "mock" and s["attributes"]["gen_ai.request.model"] == "mock-small"
               for s in chat)
    ok_chat = [s for s in chat if s["status"] != "ERROR"]
    assert all(s["attributes"]["gen_ai.response.finish_reasons"][0] in ("stop", "tool_call") for s in ok_chat)
    assert all("gen_ai.usage.input_tokens" in s["attributes"] for s in ok_chat)
    assert all(s["kind"] == "INTERNAL" and s["attributes"]["gen_ai.tool.name"] == s["name"].split(" ", 1)[1] for s in tools)
    # el tipo de span NO usa atributos de la spec antigua
    assert not any("gen_ai.system" in s["attributes"] for s in spans)


def test_logs_are_correlated_with_traces(tel):
    instr, _ = run(tel, 25)
    logs = tel.log_records()
    assert logs and all(lg["trace_id"] and lg["span_id"] for lg in logs)
    known = {s["trace_id"] for s in tel.span_records()}
    assert {lg["trace_id"] for lg in logs} <= known
    assert all(lg["attributes"]["supportops.ticket.id"] for lg in logs)
    assert {lg["severity_text"] for lg in logs} <= {"INFO", "WARN", "ERROR"}


def test_metrics_match_results(tel):
    instr, results = run(tel, 30)
    points = tel.metric_points()
    n_chat = sum(s["name"].startswith("chat ") for s in tel.span_records())
    dur = [p for p in points if p["name"] == "gen_ai.client.inference.duration"]
    assert sum(p["count"] for p in dur) == n_chat and dur[0]["explicit_bounds"][0] == 0.01
    assert any("error.type" in p["attributes"] for p in dur)                      # los fallos son una serie aparte
    tok = lambda n: sum(p["value"] for p in points if p["name"] == n)             # noqa: E731
    assert tok("gen_ai.client.inference.usage.input_tokens") == sum(r.input_tokens for r in results)
    assert tok("gen_ai.client.inference.usage.output_tokens") == sum(r.output_tokens for r in results)


def test_emit_metrics_false(tel):
    run(tel, 5, emit_metrics=False)
    assert tel.metric_points() == []


def test_errors_set_status_and_exception_event(tel):
    t = ticket("¿Dónde está mi pedido ORD-00007?", [FaultSpec("llm_error", {"status": 503, "persistent": True})])
    instr = OTelInstrumentor(tel)
    res = SupportAgent(instrumentor=instr).run(t)
    assert res.status == "error"
    spans = tel.span_records()
    chat_err = [s for s in spans if s["name"].startswith("chat ") and s["status"] == "ERROR"]
    assert len(chat_err) == 2                                       # intento + reintento
    assert all(s["attributes"]["http.response.status_code"] == 503 and s["attributes"]["error.type"] for s in chat_err)
    assert chat_err[0]["events"][0]["name"] == "exception"
    # los eventos usan el reloj SIMULADO (dentro del intervalo del span), no el de pared
    ev = chat_err[0]["events"][0]
    assert chat_err[0]["start_unix_nano"] <= ev["time_unix_nano"] <= chat_err[0]["end_unix_nano"]
    root = next(s for s in spans if s["parent_span_id"] is None)
    assert root["status"] == "ERROR" and root["attributes"]["error.type"]
    assert [p for p in tel.metric_points() if p["name"] == "gen_ai.client.inference.duration" and "error.type" in p["attributes"]]


def test_tool_error(tel):
    t = ticket("¿Dónde está mi pedido ORD-00007?", [FaultSpec("tool_error", {"tool": "get_order", "error_type": "upstream_500"})])
    SupportAgent(instrumentor=OTelInstrumentor(tel)).run(t)
    bad = [s for s in tel.span_records() if s["name"] == "execute_tool get_order"]
    assert bad and bad[0]["status"] == "ERROR" and bad[0]["attributes"]["error.type"] == "upstream_500"


def test_content_capture_is_opt_in(tel):
    t = ticket("¿Dónde está mi pedido ORD-00007?")
    SupportAgent(instrumentor=OTelInstrumentor(tel)).run(t)
    assert not any(k.startswith(("gen_ai.input", "gen_ai.output", "gen_ai.tool.call.arg", "gen_ai.tool.call.res"))
                   for s in tel.span_records() for k in s["attributes"])
    tel.reset_local()
    SupportAgent(instrumentor=OTelInstrumentor(tel, capture_content=True, redact=lambda s: s.replace("ORD-00007", "ORD-XXXXX"))).run(t)
    chat = next(s for s in tel.span_records() if s["name"].startswith("chat "))
    msgs = json.loads(chat["attributes"]["gen_ai.input.messages"])
    assert msgs[0]["role"] == "user" and msgs[0]["parts"][0]["type"] == "text"
    assert "ORD-00007" not in chat["attributes"]["gen_ai.input.messages"]          # el redactor actuó
    out = json.loads(chat["attributes"]["gen_ai.output.messages"])
    assert out[0]["finish_reason"] in ("stop", "tool_call")


def test_deterministic_ids_and_no_leak_between_runs():
    def once():
        h = setup_telemetry("supportops-agent", mode="memory", deterministic_ids=True)
        SupportAgent(instrumentor=OTelInstrumentor(h)).run(ticket("hola"))
        recs = h.span_records()
        h.shutdown()
        return [(s["trace_id"], s["span_id"], s["name"]) for s in recs]
    assert once() == once()


def test_random_ids_by_default():
    h = setup_telemetry("supportops-agent", mode="memory")
    a = SupportAgent(instrumentor=OTelInstrumentor(h))
    a.run(ticket("hola", tid="T-a")); a.run(ticket("hola", tid="T-a"))
    tids = {s["trace_id"] for s in h.span_records()}
    h.shutdown()
    assert len(tids) == 2


def test_auto_degrades_to_memory_when_nothing_listens(capsys):
    h = setup_telemetry("svc", endpoint="http://127.0.0.1:9", mode="auto")
    assert h.mode == "memory" and "degradado" in h.reason and h.endpoint is None
    h.shutdown()


def test_setup_twice_replaces_globals():
    from opentelemetry import trace
    h1 = setup_telemetry("a", mode="memory"); h2 = setup_telemetry("b", mode="memory")
    assert trace.get_tracer_provider() is h2.tracer_provider and h1.tracer_provider is not h2.tracer_provider
    h1.shutdown(); h2.shutdown()


def test_signals_can_be_disabled():
    h = setup_telemetry("svc", mode="memory", traces=False, metrics=False, logs=False)
    SupportAgent(instrumentor=OTelInstrumentor(h)).run(ticket("hola"))
    assert h.span_records() == [] and h.log_records() == [] and h.metric_points() == []
    h.shutdown()


def test_composes_with_recording_instrumentor(tel):
    rec = RecordingInstrumentor()
    SupportAgent(instrumentor=CompositeInstrumentor(OTelInstrumentor(tel), rec)).run(ticket("¿Dónde está mi pedido ORD-00007?"))
    assert len(rec.spans) == len(tel.span_records())
    assert [s["name"] for s in rec.spans] == sorted([s["name"] for s in rec.spans], key=lambda _: 0)  # mismos nombres
    assert {s["name"] for s in rec.spans} == {s["name"] for s in tel.span_records()}


def test_normalize_finish_reason():
    assert normalize_finish_reason("tool_calls") == "tool_call" and normalize_finish_reason("stop") == "stop"


def test_otlp_http_roundtrip_against_a_fake_collector():
    """El exportador OTLP/HTTP real envía protobuf a /v1/traces, /v1/metrics y /v1/logs (servidor falso local)."""
    from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest
    from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import ExportMetricsServiceRequest
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
    got: dict[str, bytes] = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            body = self.rfile.read(int(self.headers["Content-Length"]))
            if self.headers.get("Content-Encoding") == "gzip":
                import gzip
                body = gzip.decompress(body)
            got[self.path] = body
            self.send_response(200); self.send_header("Content-Type", "application/x-protobuf"); self.end_headers()

        def log_message(self, *a):  # silencio
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    h = setup_telemetry("svc-otlp", endpoint=f"http://127.0.0.1:{srv.server_port}", mode="otlp")
    assert h.mode == "otlp"
    SupportAgent(instrumentor=OTelInstrumentor(h)).run(ticket("¿Dónde está mi pedido ORD-00007?"))
    assert h.force_flush(5)
    h.shutdown()
    srv.shutdown()
    tr = ExportTraceServiceRequest(); tr.ParseFromString(got["/v1/traces"])
    names = {s.name for rs in tr.resource_spans for ss in rs.scope_spans for s in ss.spans}
    assert "invoke_agent supportops-agent" in names and any(n.startswith("chat ") for n in names)
    svc = {a.key: a.value.string_value for a in tr.resource_spans[0].resource.attributes}
    assert svc["service.name"] == "svc-otlp"
    ExportMetricsServiceRequest().ParseFromString(got["/v1/metrics"])
    lg = ExportLogsServiceRequest(); lg.ParseFromString(got["/v1/logs"])
    recs = [r for rl in lg.resource_logs for sl in rl.scope_logs for r in sl.log_records]
    assert recs and all(len(r.trace_id) == 16 and len(r.span_id) == 8 for r in recs)
    assert h.span_export_stats.get("ok", 0) >= 1 and not h.span_export_stats.get("failed")
