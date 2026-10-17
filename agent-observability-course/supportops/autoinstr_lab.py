"""Laboratorio de auto-instrumentación del módulo 06 (autor A3): ejecuta SupportOps con distintas estrategias.

Cada *variante* se ejecuta en un **subproceso limpio** (``python -m supportops.autoinstr_lab``), porque estas librerías
parchean ``openai`` de forma global y no se pueden «desinstrumentar» limpiamente: dos variantes en el mismo intérprete
se contaminarían (spans duplicados). El hijo escribe un JSON con los spans normalizados y los resultados del agente.

Variantes (``VARIANTS``)::

    manual                   hooks del Instrumentor con OpenTelemetry (invoke_agent + chat + execute_tool), reloj de pared
    openlit                  solo ``openlit.init()``                        (sin spans propios)
    openllmetry              solo ``Traceloop.init()``                      (sin spans propios)
    official                 solo ``OpenAIInstrumentor().instrument()``     (opentelemetry-instrumentation-genai-openai)
    hybrid_openlit           spans manuales invoke_agent/execute_tool + chat de OpenLIT
    hybrid_openllmetry       ídem con OpenLLMetry
    hybrid_official          ídem con la instrumentación oficial de OpenTelemetry
    openlit_decorated        openlit.init() + ``@openlit.trace`` en agent.run y en las herramientas
    openllmetry_decorated    Traceloop.init() + ``@agent`` / ``@tool`` en agent.run y en las herramientas

Requiere ``pip install openai openlit traceloop-sdk opentelemetry-instrumentation-genai-openai`` (y ``[otel]``).
Todo es determinista salvo las duraciones, que usan el reloj de pared (con ``SUPPORTOPS_REAL_SLEEP_SCALE`` pequeño).
"""
from __future__ import annotations

import argparse
import contextvars
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from typing import Any, Iterator

VARIANTS = ["manual", "openlit", "openllmetry", "official", "hybrid_openlit", "hybrid_openllmetry", "hybrid_official",
            "openlit_decorated", "openllmetry_decorated"]
LIBS = {"openlit": "openlit", "openllmetry": "openllmetry", "official": "official", "manual": None}
TOOL_FAULTS = {"tool_error": 0.10, "tool_timeout": 0.04, "tool_loop": 0.04, "hallucination": 0.04}   # sin fallos del LLM: los pone el servidor
SLEEP_SCALE = "0.01"


def lib_of(variant: str) -> str | None:
    """Librería de auto-instrumentación que usa la variante (``None`` = ninguna)."""
    for key in ("openllmetry", "openlit", "official"):
        if variant.startswith(key) or variant.endswith("_" + key):
            return key
    return None


# =====================================================================================================================
# Lado «padre»: lanza un subproceso por variante
# =====================================================================================================================
def run_variant(variant: str, n: int = 16, seed: int = 42, *, content: str = "default", error_rate: float = 0.12,
                stream: bool = False, extra: str | None = None, enrich: bool = False, sdk_retries: int = 0, timeout: float = 240.0) -> dict[str, Any]:
    """Ejecuta una variante en un subproceso y devuelve ``{"spans": [...], "results": [...], "meta": {...}}``."""
    if variant not in VARIANTS:
        raise ValueError(f"variante desconocida {variant!r}; opciones: {VARIANTS}")
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "out.json")
        cmd = [sys.executable, "-m", "supportops.autoinstr_lab", "--variant", variant, "--n", str(n), "--seed", str(seed),
               "--error-rate", str(error_rate), "--out", out, "--content", content] + (["--stream"] if stream else []) \
              + (["--extra", extra] if extra else []) + (["--enrich"] if enrich else []) + ["--sdk-retries", str(sdk_retries)]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if p.returncode != 0 or not os.path.exists(out):
            raise RuntimeError(f"la variante {variant} falló (rc={p.returncode}):\n{p.stderr[-1500:]}")
        with open(out) as f:
            return json.load(f)


def build_dataset(path: str, n: int = 24, seed: int = 42) -> dict[str, Any]:
    """Genera el conjunto pregrabado del módulo 06 (modo degradado): todas las variantes y las pruebas de trampas. ~2 min."""
    import gzip
    runs: dict[str, Any] = {}
    for v in VARIANTS:
        runs[v] = run_variant(v, n, seed)
    for v in ("openlit", "openllmetry", "official", "hybrid_openlit", "hybrid_openllmetry", "hybrid_official", "openlit_decorated", "openllmetry_decorated"):
        runs[f"off:{v}"] = run_variant(v, n, seed, content="off")
    runs["on:official"] = run_variant("official", n, seed, content="on")
    for v in ("openlit", "openllmetry", "official"):
        runs[f"enrich:{v}"] = run_variant(v, n, seed, enrich=True)
        runs[f"stream:{v}"] = run_variant(v, 2, seed, stream=True)
    runs["both"] = run_variant("openlit", n, seed, extra="official")
    for v in ("official", "openlit"):
        runs[f"retries2:{v}"] = run_variant(v, n, seed, sdk_retries=2, error_rate=0.3)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump({"n": n, "seed": seed, "runs": runs}, f, default=str)
    return runs


def bench_variant(lib: str | None, calls: int = 300) -> dict[str, float]:
    """Microbenchmark del coste por llamada ``chat.completions.create`` (ms): mediana y p95, con el servidor falso sin latencia."""
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "bench.json")
        cmd = [sys.executable, "-m", "supportops.autoinstr_lab", "--bench", str(calls), "--variant", lib or "manual", "--out", out]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if p.returncode != 0 or not os.path.exists(out):
            raise RuntimeError(f"bench {lib} falló:\n{p.stderr[-1500:]}")
        with open(out) as f:
            return json.load(f)


# =====================================================================================================================
# Lado «hijo»
# =====================================================================================================================
def _norm_attr(v: Any) -> Any:
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    if isinstance(v, (list, tuple)):
        return [_norm_attr(x) for x in v]
    return str(v)


def normalize_spans(finished: list[Any]) -> list[dict[str, Any]]:
    """ReadableSpan -> dict con el esquema del curso (``supportops.schema.SPAN_SCHEMA``) más ``scope``."""
    out = []
    for s in finished:
        c = s.get_span_context()
        out.append({
            "trace_id": f"{c.trace_id:032x}", "span_id": f"{c.span_id:016x}",
            "parent_span_id": f"{s.parent.span_id:016x}" if s.parent else None,
            "name": s.name, "kind": s.kind.name, "start_unix_nano": s.start_time, "end_unix_nano": s.end_time,
            "status": s.status.status_code.name, "status_message": s.status.description,
            "attributes": {k: _norm_attr(v) for k, v in dict(s.attributes or {}).items()},
            "events": [{"name": e.name, "attributes": {k: _norm_attr(v) for k, v in dict(e.attributes or {}).items() if k != "exception.stacktrace"}} for e in s.events],
            "scope": s.instrumentation_scope.name if s.instrumentation_scope else None,
            "resource": {k: _norm_attr(v) for k, v in dict(s.resource.attributes).items()},
        })
    return sorted(out, key=lambda x: x["start_unix_nano"])


def make_wall_instrumentor(tracer: Any, chat: bool = True):
    """Instrumentor manual con **reloj de pared** (spans ``invoke_agent`` / ``chat`` / ``execute_tool``).

    ``chat=False`` desactiva el span ``chat`` para que lo ponga una librería de auto-instrumentación (modo híbrido).
    """
    from opentelemetry.trace import SpanKind, Status, StatusCode

    from .instrument import Instrumentor

    class WallClockOTel(Instrumentor):
        @contextmanager
        def agent_run(self, ctx) -> Iterator[None]:
            t = ctx.ticket
            with tracer.start_as_current_span(f"invoke_agent {ctx.agent_name}", kind=SpanKind.INTERNAL, attributes={
                    "gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": ctx.agent_name, "gen_ai.conversation.id": t.ticket_id,
                    "supportops.ticket.id": t.ticket_id, "supportops.customer.tier": t.tier, "supportops.channel": t.channel}) as span:
                yield
                r = ctx.result
                if r is not None:
                    span.set_attributes({"supportops.status": r.status, "supportops.llm_calls": r.n_llm_calls,
                                         "supportops.tool_calls": r.n_tool_calls, "supportops.cost_usd": r.cost_usd})
                    if r.status in ("error", "max_steps"):
                        span.set_status(Status(StatusCode.ERROR, r.status))
                        span.set_attribute("error.type", r.error_type or r.status)

        @contextmanager
        def llm_call(self, ctx, info) -> Iterator[None]:
            if not chat:
                yield
                return
            with tracer.start_as_current_span(f"chat {info.model}", kind=SpanKind.CLIENT, attributes={
                    "gen_ai.operation.name": "chat", "gen_ai.provider.name": info.provider, "gen_ai.request.model": info.model,
                    "supportops.step": info.step, "supportops.attempt": info.attempt}) as span:
                try:
                    yield
                finally:
                    if info.error is not None:
                        span.set_attribute("error.type", getattr(info.error, "error_type", type(info.error).__name__))
                r = info.response
                if r is not None:
                    span.set_attributes({"gen_ai.response.model": r.model, "gen_ai.response.id": r.response_id,
                                         "gen_ai.response.finish_reasons": [r.finish_reason],
                                         "gen_ai.usage.input_tokens": r.usage.input_tokens, "gen_ai.usage.output_tokens": r.usage.output_tokens})

        @contextmanager
        def tool_call(self, ctx, info) -> Iterator[None]:
            with tracer.start_as_current_span(f"execute_tool {info.call.name}", kind=SpanKind.INTERNAL, attributes={
                    "gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": info.call.name, "gen_ai.tool.call.id": info.call.id,
                    "gen_ai.tool.type": "function", "supportops.step": info.step}):
                yield                                   # una excepción de la herramienta marca el span ERROR sola

    return WallClockOTel()


_TICKET: "contextvars.ContextVar[dict[str, str] | None]" = contextvars.ContextVar("supportops_ticket", default=None)


def make_enrich_processor():
    """``SpanProcessor`` que copia el ticket activo (ContextVar) a CADA span que nazca, sea de quien sea (técnica de extensión)."""
    from opentelemetry.sdk.trace import SpanProcessor

    class TicketContextProcessor(SpanProcessor):
        def on_start(self, span, parent_context=None):             # el span aún es mutable: aquí SÍ se pueden añadir atributos
            t = _TICKET.get()
            if t:
                span.set_attributes({"supportops.ticket.id": t["ticket"], "gen_ai.conversation.id": t["ticket"],
                                     "supportops.customer.tier": t["tier"]})

    return TicketContextProcessor()


def make_context_setter():
    """Instrumentor sin spans que solo publica el ticket en un ContextVar (lo lee ``TicketContextProcessor``)."""
    from .instrument import Instrumentor

    class TicketContextSetter(Instrumentor):
        @contextmanager
        def agent_run(self, ctx) -> Iterator[None]:
            tok = _TICKET.set({"ticket": ctx.ticket.ticket_id, "tier": ctx.ticket.tier})
            try:
                yield
            finally:
                _TICKET.reset(tok)

    return TicketContextSetter()


def _setup(variant: str, content: str, extra: str | None = None, enrich: bool = False) -> tuple[Any, Any]:
    """Configura proveedor/instrumentación. Devuelve (exporter en memoria, tracer para spans manuales)."""
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    lib = lib_of(variant)
    mem = InMemorySpanExporter()
    if content != "default":                      # "default": no tocamos nada y cada librería usa SU valor por defecto
        on = content == "on"
        os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = ("span_only" if lib == "official" else "true") if on else ("no_content" if lib == "official" else "false")
        os.environ["TRACELOOP_TRACE_CONTENT"] = "true" if on else "false"
    resource = Resource.create({"service.name": "supportops-agent", "service.version": "0.1.0-m06", "deployment.environment.name": "lab"})
    if lib == "openllmetry":
        from traceloop.sdk import Traceloop
        Traceloop.init(app_name="supportops-agent", disable_batch=True, exporter=mem, telemetry_enabled=False,
                       resource_attributes={"service.version": "0.1.0-m06", "deployment.environment.name": "lab"})
        tp = trace.get_tracer_provider()
    else:
        tp = TracerProvider(resource=resource)
        tp.add_span_processor(SimpleSpanProcessor(mem))
        trace.set_tracer_provider(tp)
        if lib == "openlit":
            import openlit
            kw = {} if content == "default" else {"capture_message_content": content == "on"}
            openlit.init(application_name="supportops-agent", environment="lab", disable_metrics=True, disable_events=True, **kw)
        elif lib == "official":
            from opentelemetry.instrumentation.genai.openai import OpenAIInstrumentor
            OpenAIInstrumentor().instrument(tracer_provider=tp)
    if extra == "official" and lib != "official":                       # dos librerías a la vez (trampa)
        from opentelemetry.instrumentation.genai.openai import OpenAIInstrumentor
        OpenAIInstrumentor().instrument(tracer_provider=tp)
    if enrich:
        tp.add_span_processor(make_enrich_processor())
    return mem, tp.get_tracer("supportops.manual")


def _child_run(a: argparse.Namespace) -> None:
    from .instrument import CompositeInstrumentor
    os.environ.setdefault("LLM_PROVIDER", "mock")
    os.environ["SUPPORTOPS_REAL_SLEEP_SCALE"] = SLEEP_SCALE
    variant, content = a.variant, a.content
    mem, tracer = _setup(variant, content, a.extra, a.enrich)

    from .agent import SupportAgent
    from .instrument import Instrumentor
    from .llm.mock import MockLLM
    from .openai_compat import FakeOpenAIServer, make_openai_llm
    from .traffic import generate_tickets, run_tickets, to_rows

    srv = FakeOpenAIServer(MockLLM("mock-small", seed=a.seed), error_rate=a.error_rate, sleep_scale=float(SLEEP_SCALE)).start()
    try:
        llm = make_openai_llm(srv, max_retries=a.sdk_retries)
        lib = lib_of(variant)
        if variant == "manual":
            instr: Instrumentor = make_wall_instrumentor(tracer, chat=True)
        elif variant.startswith("hybrid_"):
            instr = make_wall_instrumentor(tracer, chat=False)
        else:
            instr = Instrumentor()
        if a.enrich:
            instr = CompositeInstrumentor(make_context_setter(), instr)
        agent = SupportAgent(llm=llm, instrumentor=instr)
        if variant == "openllmetry_decorated":
            from traceloop.sdk.decorators import agent as tl_agent, tool as tl_tool
            for name, tool in agent.tools._tools.items():
                tool.fn = tl_tool(name=name)(tool.fn)
            agent.run = tl_agent(name="supportops-agent")(agent.run)            # type: ignore[method-assign]
        elif variant == "openlit_decorated":
            import openlit
            for name, tool in agent.tools._tools.items():
                tool.fn = openlit.trace(tool.fn)
            agent.run = openlit.trace(agent.run)                                # type: ignore[method-assign]
        tickets = generate_tickets(a.n, seed=a.seed, duration_s=600, fault_rates=TOOL_FAULTS, pii_rate=0.25)
        t0 = time.perf_counter()
        results = run_tickets(agent, tickets)
        wall = time.perf_counter() - t0
        stream_info = None
        if a.stream:
            stream_info = _stream_probe(srv)
        rows = to_rows(tickets, results)
        for r in rows:
            for k in list(r):
                if not isinstance(r[k], (str, int, float, bool, type(None))):
                    r[k] = json.dumps(r[k], default=str, ensure_ascii=False)
        spans = normalize_spans(mem.get_finished_spans())
        meta = {"variant": variant, "lib": lib, "n": a.n, "seed": a.seed, "wall_s": wall, "content": content, "stream": stream_info,
                "server_requests": len(srv.requests), "extra": a.extra, "enrich": a.enrich, "sdk_retries": a.sdk_retries, "versions": _versions()}
    finally:
        srv.stop()
    with open(a.out, "w") as f:
        json.dump({"spans": spans, "results": rows, "meta": meta}, f, default=str)


def _stream_probe(srv: Any) -> dict[str, Any]:
    """Una llamada en *streaming* con y sin ``include_usage``: ¿ve la librería los tokens?"""
    import openai
    c = openai.OpenAI(base_url=srv.base_url, api_key="sk-fake", max_retries=0)
    out = {}
    for flag in (False, True):
        kw = {"stream_options": {"include_usage": True}} if flag else {}
        s = c.chat.completions.create(model="mock-small", messages=[{"role": "user", "content": "¿Cuál es la política de devoluciones?"}], stream=True, **kw)
        text = "".join((ch.choices[0].delta.content or "") for ch in s if ch.choices)
        out["with_usage" if flag else "without_usage"] = len(text)
    return out


def _versions() -> dict[str, str]:
    from importlib import metadata
    v = {}
    for p in ("openai", "openlit", "traceloop-sdk", "opentelemetry-sdk", "opentelemetry-instrumentation-genai-openai"):
        try:
            v[p] = metadata.version(p)
        except metadata.PackageNotFoundError:
            pass
    return v


def _child_bench(a: argparse.Namespace) -> None:
    os.environ.setdefault("LLM_PROVIDER", "mock")
    variant = a.variant
    lib = lib_of(variant)
    t_imp = time.perf_counter()
    _setup(variant if lib else "manual", content="default")
    import openai

    from .openai_compat import FakeOpenAIServer
    init_s = time.perf_counter() - t_imp
    srv = FakeOpenAIServer().start()
    try:
        c = openai.OpenAI(base_url=srv.base_url, api_key="sk-fake", max_retries=0)
        msgs = [{"role": "user", "content": "Hola, ¿dónde está mi pedido ORD-00012?"}]
        for _ in range(20):                                                     # calentamiento
            c.chat.completions.create(model="mock-small", messages=msgs)
        ts = []
        for _ in range(a.bench):
            t = time.perf_counter()
            c.chat.completions.create(model="mock-small", messages=msgs)
            ts.append((time.perf_counter() - t) * 1000)
    finally:
        srv.stop()
    ts.sort()
    with open(a.out, "w") as f:
        json.dump({"lib": lib, "init_s": init_s, "median_ms": statistics.median(ts), "p95_ms": ts[int(0.95 * len(ts)) - 1], "calls": len(ts)}, f)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--variant", default="manual")
    ap.add_argument("--n", type=int, default=16)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--error-rate", type=float, default=0.12)
    ap.add_argument("--content", choices=["default", "on", "off"], default="default",
                    help="default = cada librería con SU valor por defecto; on/off = forzar captura de prompts/completions")
    ap.add_argument("--stream", action="store_true")
    ap.add_argument("--extra", choices=["official"], default=None, help="instrumenta además con la librería oficial (trampa: doble instrumentación)")
    ap.add_argument("--enrich", action="store_true", help="añade TicketContextProcessor (técnica de extensión)")
    ap.add_argument("--sdk-retries", type=int, default=0, help="max_retries del cliente openai (por defecto del SDK: 2)")
    ap.add_argument("--bench", type=int, default=0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    (_child_bench if a.bench else _child_run)(a)


if __name__ == "__main__":
    main()
