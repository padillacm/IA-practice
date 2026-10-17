"""Pruebas del módulo 12 (MCP): servidor de pedidos, puente observable, errores, idempotencia y confianza en el contexto remoto."""
import asyncio
import contextvars
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

pytest.importorskip("opentelemetry.sdk")
pytest.importorskip("mcp")

from opentelemetry import trace as otel_trace  # noqa: E402

from supportops import MockLLM, SupportAgent, Ticket, default_tools, generate_tickets  # noqa: E402
from supportops.instrument import CompositeInstrumentor  # noqa: E402
from supportops.mcp_orders import (McpServerProcess, McpToolBridge, McpToolSpanEnricher, OrdersBackend, WallClockInstrumentor,  # noqa: E402
                                   build_server, redact_args, tools_fingerprint, tracking_rule)
from supportops.telemetry import setup_telemetry  # noqa: E402
from supportops.tools import ToolError  # noqa: E402


@pytest.fixture(scope="module")
def tel():
    os_env = __import__("os").environ
    os_env.setdefault("LLM_PROVIDER", "mock")
    return setup_telemetry("supportops-agent", mode="memory")


@pytest.fixture(scope="module")
def server():
    sp = McpServerProcess(time_scale=0.02)
    with McpToolBridge(sp.params(), read_timeout_s=3.0) as br:
        yield sp, br


def wait_server_spans(sp, n, timeout=3.0):
    t = time.time()
    while time.time() - t < timeout:
        rows = sp.spans()
        if len(rows) >= n:
            return rows
        time.sleep(0.05)
    return sp.spans()


# ------------------------------------------------------------------------------------------------ funciones puras
def test_redact_args_allowlist_and_pii():
    out = redact_args("issue_refund", {"order_id": "ORD-00001", "amount_eur": 10.5, "reason": "mi correo es ana@example.com", "idempotency_key": "abc"})
    assert out == {"order_id": "ORD-00001", "amount_eur": 10.5, "reason": "<redacted>", "idempotency_key": "<redacted>"}
    assert redact_args("get_order", {"order_id": "ORD-00001 ana@example.com"})["order_id"] == "ORD-00001 <email>"
    assert redact_args("desconocida", {"x": 1}) == {"x": "<redacted>"}


def test_tools_fingerprint_detects_rug_pull():
    async def tools(mode):
        from mcp import Client
        async with Client(build_server(mode)) as c:
            return (await c.list_tools()).tools
    a, b, c = (asyncio.run(tools(m)) for m in ("normal", "normal", "poisoned"))
    assert tools_fingerprint(a) == tools_fingerprint(b) != tools_fingerprint(c)


def test_server_annotations_and_tools():
    async def go():
        from mcp import Client
        async with Client(build_server("normal")) as cl:
            return {t.name: t.annotations for t in (await cl.list_tools()).tools}
    ann = asyncio.run(go())
    assert ann["get_order"].read_only_hint is True and ann["issue_refund"].destructive_hint is True and ann["issue_refund"].idempotent_hint is False


# ------------------------------------------------------------------------------------------------ proceso real
def test_trace_joins_agent_and_server(server, tel):
    sp, br = server
    sp.reset_spans()
    tracer = tel.tracer()
    with tracer.start_as_current_span("execute_tool get_order") as s:
        out = br.call("get_order", {"order_id": "ORD-00001"})
    assert out["found"] and out["order_id"] == "ORD-00001"
    tid = format(s.get_span_context().trace_id, "032x")
    srv = [r for r in wait_server_spans(sp, 2) if r["trace_id"] == tid]
    names = {r["name"] for r in srv}
    assert {"tools/call get_order", "SELECT orders-db"} <= names                              # dos procesos, una traza
    cli = next(r for r in tel.span_records() if r["trace_id"] == tid and r["name"] == "MCP send tools/call get_order")
    top = next(r for r in srv if r["name"] == "tools/call get_order")
    assert cli["kind"] == "CLIENT" and top["kind"] == "SERVER" and top["parent_span_id"] == cli["span_id"]     # el CLIENT del SDK es el padre
    assert top["resource"]["service.name"] == "supportops-orders-mcp" and top["resource"]["process.pid"] != cli["resource"].get("process.pid", -1)
    assert top["attributes"]["gen_ai.tool.name"] == "get_order" and top["attributes"]["gen_ai.operation.name"] == "execute_tool"
    assert top["attributes"]["network.transport"] == "pipe" and top["attributes"]["supportops.tool.read_only"] is True
    assert "gen_ai.tool.name" not in cli["attributes"] and cli["name"] != "tools/call get_order"      # desviaciones del SDK frente a la spec


def test_thread_without_context_breaks_the_trace(server, tel):
    sp, br = server
    sp.reset_spans()
    with tel.tracer().start_as_current_span("agente") as s:
        tid = format(s.get_span_context().trace_id, "032x")
        with ThreadPoolExecutor(1) as ex:
            ex.submit(br.call, "get_order", {"order_id": "ORD-00005"}).result()
            ex.submit(contextvars.copy_context().run, br.call, "get_order", {"order_id": "ORD-00006"}).result()
    rows = [r for r in wait_server_spans(sp, 4) if r["name"] == "tools/call get_order"]
    assert len(rows) == 2 and sum(r["trace_id"] == tid for r in rows) == 1                     # solo el que copió el contexto se une


def test_timeout_leaves_zombie_work_on_server(server, tel):
    sp, br = server
    sp.reset_spans()
    with tel.tracer().start_as_current_span("agente") as s:
        t0 = time.perf_counter()
        with pytest.raises(ToolError) as ei:
            br.call("track_shipment", {"order_id": "ORD-00017"}, timeout_s=0.1)         # pedido 17: transportista ×25 (≈ 0,15 s reales)
        waited = time.perf_counter() - t0
    assert ei.value.error_type == "timeout" and waited < 0.5
    time.sleep(0.5)
    tid = format(s.get_span_context().trace_id, "032x")
    cli = next(r for r in tel.span_records() if r["trace_id"] == tid and r["name"].startswith("MCP send tools/call"))
    srv = next(r for r in sp.spans() if r["trace_id"] == tid and r["name"] == "tools/call track_shipment")
    assert cli["status"] == "ERROR" and srv["status"] != "ERROR"
    assert srv["end_unix_nano"] > cli["end_unix_nano"]                                          # el servidor siguió trabajando tras el abandono


def test_tool_error_is_not_a_client_error_span(server, tel):
    sp, br = server
    sp.reset_spans()
    with tel.tracer().start_as_current_span("agente") as s:
        with pytest.raises(ToolError) as ei:
            br.call("track_shipment", {"order_id": "ORD-00013"})                               # múltiplo de 13: el transportista devuelve 503
        with pytest.raises(ToolError) as ej:
            br.call("nope", {})
    assert ei.value.error_type == "tool_error" and "503" in str(ei.value) and ej.value.error_type == "tool_error"
    tid = format(s.get_span_context().trace_id, "032x")
    cli = [r for r in tel.span_records() if r["trace_id"] == tid and r["name"].startswith("MCP send tools/call")]
    assert all(r["status"] != "ERROR" for r in cli)                                             # isError no marca el span cliente (desviación)
    srv = [r for r in wait_server_spans(sp, 4) if r["trace_id"] == tid and r["name"].startswith("tools/call")]
    assert srv and all(r["status"] == "ERROR" and r["attributes"]["error.type"] == "tool_error" for r in srv)


def test_idempotency_key_prevents_double_refund(server):
    sp, br = server
    base = br.call("refund_stats")["applied"]
    reg = default_tools()
    br.register_tools(reg, ["issue_refund"])
    pay = {"order_id": "ORD-00010", "amount_eur": 5.0, "reason": "prueba"}
    with pytest.raises(ToolError) as ei:                                                       # 1.º intento: el cliente se rinde antes de que acabe el pago
        br.call("issue_refund", {**pay, "idempotency_key": "k1"}, timeout_s=0.001)
    assert ei.value.error_type == "timeout"
    time.sleep(0.4)
    r2 = reg.get("issue_refund").fn(**pay)                                                      # reintento (el puente añade una clave estable)
    assert r2["deduplicated"] is False                                                         # clave distinta: se aplica de nuevo (duplicado real)
    r3 = br.call("issue_refund", {**pay, "idempotency_key": "k1"})
    assert r3["deduplicated"] is True                                                          # misma clave -> no se vuelve a ejecutar
    assert br.call("refund_stats")["applied"] - base == 2                                      # k1 (abandonado pero ejecutado) + la clave del puente


def test_audit_event_for_destructive_tool(server):
    sp, br = server
    sp.reset_spans()
    br.call("issue_refund", {"order_id": "ORD-00011", "amount_eur": 1.0, "idempotency_key": "audit-1"})
    rows = [r for r in wait_server_spans(sp, 3) if r["name"] == "tools/call issue_refund"]
    ev = [e for r in rows for e in r["events"] if e["name"] == "supportops.audit"]
    assert ev and ev[0]["attributes"]["tool"] == "issue_refund" and ev[0]["attributes"]["outcome"] == "ok"


def test_agent_end_to_end_with_wall_clock(server, tel, monkeypatch):
    sp, br = server
    monkeypatch.setenv("SUPPORTOPS_REAL_SLEEP_SCALE", "0.02")
    sp.reset_spans()
    reg = default_tools()
    names = br.register_tools(reg, ["get_order", "track_shipment", "issue_refund"])
    llm = MockLLM("mock-small")
    llm.add_rule(tracking_rule())
    agent = SupportAgent(llm=llm, tools=reg, instrumentor=CompositeInstrumentor(WallClockInstrumentor(tel), McpToolSpanEnricher(names)))
    t = Ticket("T-mcp-1", "C-0001", "standard", "chat", "¿Dónde está mi pedido ORD-00002? Quiero el seguimiento.", "order_status", time.time())
    t0 = time.time()
    res = agent.run(t)
    assert res.tools_used == ["get_order", "track_shipment"] and time.time() - t0 < 5
    tid = tel.span_records()[-1]["trace_id"]
    rows = [r for r in tel.span_records() if r["trace_id"] == tid]
    root = next(r for r in rows if r["name"].startswith("invoke_agent"))
    assert abs(root["start_unix_nano"] / 1e9 - t0) < 5                                         # reloj de pared, no simulado
    tool = next(r for r in rows if r["name"] == "execute_tool track_shipment")
    assert tool["attributes"]["gen_ai.tool.type"] == "extension" and tool["attributes"]["supportops.mcp.server"] == "supportops-orders-mcp"
    srv = [r for r in wait_server_spans(sp, 6) if r["trace_id"] == tid]
    assert {"tools/call get_order", "tools/call track_shipment", "GET carrier-api"} <= {r["name"] for r in srv}


def test_context_policy_link_starts_new_trace_with_link(tel):
    sp = McpServerProcess(context_policy="link")
    with McpToolBridge(sp.params(), read_timeout_s=3.0) as br:
        with tel.tracer().start_as_current_span("agente") as s:
            br.call("get_order", {"order_id": "ORD-00001"})
        tid, sid = format(s.get_span_context().trace_id, "032x"), format(s.get_span_context().span_id, "016x")
        rows = [r for r in wait_server_spans(sp, 2) if r["name"] == "tools/call get_order"]
    assert rows and rows[0]["trace_id"] != tid and rows[0]["parent_span_id"] is None                   # no se confía en el padre remoto
    assert len(rows[0]["links"]) == 1 and rows[0]["links"][0]["trace_id"] == tid                       # pero queda enlazado al llamador


def test_capture_args_is_opt_in_and_redacted(tel):
    for capture in (False, True):
        sp = McpServerProcess(capture_args=capture)
        with McpToolBridge(sp.params(), read_timeout_s=3.0) as br:
            br.call("get_order", {"order_id": "ORD-00001"})
            rows = [r for r in wait_server_spans(sp, 2) if r["name"] == "tools/call get_order"]
        has = "gen_ai.tool.call.arguments" in rows[0]["attributes"]
        assert has is capture
        if capture:
            assert rows[0]["attributes"]["gen_ai.tool.call.arguments"] == '{"order_id": "ORD-00001"}'


# ------------------------------------------------------------------------------------------------ en proceso
def test_middleware_records_spec_metric_in_process():
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import InMemoryMetricReader
    reader = InMemoryMetricReader()
    meter = MeterProvider(metric_readers=[reader]).get_meter("t")
    be = OrdersBackend()

    async def go():
        from mcp import Client
        async with Client(build_server("normal", meter=meter, backend=be)) as cl:
            await cl.call_tool("get_order", {"order_id": "ORD-00001"})
            await cl.call_tool("nope", {})
    asyncio.run(go())
    pts = [p for rm in reader.get_metrics_data().resource_metrics for sm in rm.scope_metrics for m in sm.metrics for p in m.data.data_points
           if m.name == "mcp.server.operation.duration"]
    got = {(p.attributes["gen_ai.tool.name"], p.attributes.get("error.type")): p.count for p in pts}
    assert got == {("get_order", None): 1, ("nope", "tool_error"): 1}


def test_error_class_caller_vs_server_in_process(tel):
    tel.reset_local()

    async def go():
        from mcp import Client
        async with Client(build_server("normal")) as cl:
            await cl.call_tool("nope", {})
            await cl.call_tool("get_order", {})                                   # argumentos inválidos
            await cl.call_tool("track_shipment", {"order_id": "ORD-00013"})       # fallo del transportista
    asyncio.run(go())
    cls = {}
    for r in tel.span_records():
        if r["name"].startswith("tools/call"):
            cls.setdefault(r["attributes"]["gen_ai.tool.name"], []).append(r["attributes"].get("supportops.error.class"))
    assert cls["nope"] == ["caller"] and cls["get_order"] == ["caller"] and cls["track_shipment"] == ["server"]
