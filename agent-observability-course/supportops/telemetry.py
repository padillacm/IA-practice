"""Telemetría OpenTelemetry de referencia para SupportOps (módulos 03 y 04 la construyen paso a paso; los demás la reutilizan).

    from supportops.telemetry import setup_telemetry, OTelInstrumentor
    tel = setup_telemetry("supportops-agent")                 # OTLP/HTTP -> http://localhost:4318 (o memoria si no hay Collector)
    agent = SupportAgent(instrumentor=OTelInstrumentor(tel))
    ...
    tel.force_flush(); tel.shutdown()

Qué hay aquí
------------
* ``setup_telemetry(...) -> TelemetryHandle``: crea TracerProvider + MeterProvider + LoggerProvider con un ``Resource``
  común, exportadores OTLP/HTTP (``BatchSpanProcessor`` / ``PeriodicExportingMetricReader`` / ``BatchLogRecordProcessor``)
  y, además, copias en MEMORIA de todo lo exportado (para tests, gráficos y para inspeccionar lo que se envió).
  Tres modos: ``otlp`` (envía al Collector), ``memory`` (sin red) y ``auto`` (por defecto: si el puerto OTLP no responde,
  degrada a ``memory`` con un aviso; el notebook nunca se bloquea).
* ``OTelInstrumentor``: implementa los puntos de extensión ``Instrumentor`` de ``supportops.instrument`` (agent_run,
  llm_call, tool_call, log) con las GenAI semantic conventions (estado *Development*; spec oficial en
  github.com/open-telemetry/semantic-conventions-genai), un subconjunto mínimo de métricas GenAI y logs estructurados
  con ``trace_id``/``span_id``.

Decisiones de diseño (todas explicadas en el módulo 03/04)
---------------------------------------------------------
* Los tiempos de spans y logs son los del reloj SIMULADO (``ctx.clock``): trazas deterministas y notebooks en milisegundos.
  Con ``generate_tickets(..., start_s="live")`` la ventana simulada termina «ahora», así que Tempo/Loki las aceptan.
* Los proveedores se registran como GLOBALES (``set_global=True``) para que librerías/auto-instrumentación los vean; el
  instrumentor usa los proveedores del handle de forma explícita (no depende del global).
* La captura de contenido (prompts, respuestas, argumentos de herramientas) está APAGADA por defecto (``capture_content``).
"""
from __future__ import annotations

import json
import logging
import os
import socket
import threading
import uuid
import warnings
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator
from urllib.parse import urlparse

try:
    from opentelemetry import _logs as otel_logs
    from opentelemetry import metrics as otel_metrics
    from opentelemetry import trace as otel_trace
    from opentelemetry.sdk._logs import LoggerProvider
    from opentelemetry.sdk._logs import export as logs_export
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import InMemoryMetricReader, PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor, SpanExporter, SpanExportResult
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from opentelemetry.sdk.trace.id_generator import IdGenerator, RandomIdGenerator
    from opentelemetry.trace import SpanKind, Status, StatusCode
except ImportError as e:  # pragma: no cover
    raise ImportError('supportops.telemetry necesita el SDK de OpenTelemetry: pip install -e "agent-observability-course[otel]"') from e

from .clock import stable_hex
from .config import get_settings
from .instrument import Instrumentor, LLMCallInfo, RunContext, ToolCallInfo

DEFAULT_ENDPOINT = "http://localhost:4318"
SERVICE_VERSION = "0.1.0"
SCOPE_NAME = "supportops.telemetry"

# Límites de los atributos de contenido (captura opt-in): se truncan para no reventar el backend (spec: «likely to be large»).
DEFAULT_MAX_CONTENT_CHARS = 2000

# Boundaries recomendados por la spec GenAI (ExplicitBucketBoundaries); los de SDK por defecto están pensados para ms.
DURATION_BOUNDARIES = [0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 0.64, 1.28, 2.56, 5.12, 10.24, 20.48, 40.96, 81.92]
TOKEN_BOUNDARIES = [1, 4, 16, 64, 256, 1024, 4096, 16384, 65536, 262144, 1048576, 4194304, 16777216, 67108864]

# finish_reason del LLMResponse de SupportOps -> valores del enum de la spec (FinishReason en gen-ai-output-messages.json)
FINISH_REASON_MAP = {"stop": "stop", "length": "length", "tool_calls": "tool_call", "tool_use": "tool_call",
                     "content_filter": "content_filter", "error": "error"}

SEVERITY_NUMBER = {logging.DEBUG: 5, logging.INFO: 9, logging.WARNING: 13, logging.ERROR: 17, logging.CRITICAL: 21}
SEVERITY_TEXT = {logging.DEBUG: "DEBUG", logging.INFO: "INFO", logging.WARNING: "WARN", logging.ERROR: "ERROR",
                 logging.CRITICAL: "FATAL"}

# Campos libres del agente (``self._log(..., **fields)``) -> nombres de atributo namespaced
LOG_FIELD_MAP = {"ticket_id": "supportops.ticket.id", "error_type": "error.type", "channel": "supportops.channel",
                 "tier": "supportops.customer.tier"}


# ---------------------------------------------------------------------------------------------------------------------
# Identificadores deterministas (opcionales, para tests y datos reproducibles)
# ---------------------------------------------------------------------------------------------------------------------
class _Ids(IdGenerator):
    """Generador de ids: aleatorio (como ``RandomIdGenerator``) o determinista.

    En modo determinista el instrumentor anuncia el trace_id del próximo span raíz con ``begin_trace`` y los span_id se
    derivan de (trace_id, contador). No es seguro entre hilos: úsalo solo en laboratorios/tests secuenciales.
    """

    def __init__(self, deterministic: bool = False):
        self.deterministic = deterministic
        self._rand = RandomIdGenerator()
        self._pending: str | None = None
        self._current: str | None = None
        self._n = 0

    def begin_trace(self, trace_hex: str) -> None:
        self._pending = trace_hex

    def generate_trace_id(self) -> int:
        if self.deterministic and self._pending:
            self._current, self._pending, self._n = self._pending, None, 0
            return int(self._current, 16)
        return self._rand.generate_trace_id()

    def generate_span_id(self) -> int:
        if self.deterministic and self._current:
            self._n += 1
            return int(stable_hex(16, self._current, self._n), 16) or 1
        return self._rand.generate_span_id()


# ---------------------------------------------------------------------------------------------------------------------
# Handle
# ---------------------------------------------------------------------------------------------------------------------
class _CountingSpanExporter(SpanExporter):
    """Envuelve un exportador y cuenta lotes enviados/fallidos (la telemetría nunca debe romper la app, pero sí avisar)."""

    def __init__(self, inner: SpanExporter, stats: dict[str, int]):
        self.inner, self.stats = inner, stats

    def export(self, spans):  # type: ignore[override]
        try:
            res = self.inner.export(spans)
        except Exception:  # noqa: BLE001
            res = SpanExportResult.FAILURE
        key = "ok" if res == SpanExportResult.SUCCESS else "failed"
        self.stats[key] = self.stats.get(key, 0) + 1
        self.stats[key + "_spans"] = self.stats.get(key + "_spans", 0) + len(spans)
        return res

    def shutdown(self) -> None:
        self.inner.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return self.inner.force_flush(timeout_millis)


def _attrs(d: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in dict(d or {}).items():
        out[k] = list(v) if isinstance(v, (tuple, list)) else v
    return out


@dataclass
class TelemetryHandle:
    """Resultado de ``setup_telemetry``. Expone los proveedores, copias en memoria y utilidades de flush/shutdown."""
    service_name: str
    mode: str                                    # "otlp" | "memory"
    endpoint: str | None
    resource: Resource
    tracer_provider: Any = None
    meter_provider: Any = None
    logger_provider: Any = None
    ids: _Ids = field(default_factory=_Ids)
    span_export_stats: dict[str, int] = field(default_factory=dict)
    reason: str = ""                             # por qué se eligió este modo (p. ej. «Collector no responde»)
    _span_mem: InMemorySpanExporter | None = None
    _metric_mem: InMemoryMetricReader | None = None
    _log_mem: Any = None
    _closed: bool = False

    # -- acceso a proveedores -------------------------------------------------------------------------------------
    def tracer(self, name: str = SCOPE_NAME):
        return (self.tracer_provider or otel_trace.NoOpTracerProvider()).get_tracer(name)

    def meter(self, name: str = SCOPE_NAME):
        return (self.meter_provider or otel_metrics.NoOpMeterProvider()).get_meter(name)

    def logger(self, name: str = SCOPE_NAME):
        return (self.logger_provider or otel_logs.NoOpLoggerProvider()).get_logger(name)

    def logging_handler(self, level: int = logging.NOTSET) -> logging.Handler:
        """Handler de ``logging`` estándar que reenvía los LogRecord al pipeline OTel (módulo 08). Añádelo a un logger tuyo."""
        from opentelemetry.sdk._logs import LoggingHandler
        return LoggingHandler(level=level, logger_provider=self.logger_provider)

    def begin_trace(self, trace_hex: str) -> None:
        """Con ``deterministic_ids=True`` fija el trace_id del próximo span raíz (no hace nada si no)."""
        self.ids.begin_trace(trace_hex)

    # -- ciclo de vida --------------------------------------------------------------------------------------------
    def force_flush(self, timeout_s: float = 10.0) -> bool:
        """Vacía los buffers (spans, métricas, logs). Devuelve True si todo se exportó dentro del plazo."""
        ok = True
        ms = int(timeout_s * 1000)
        for p in (self.tracer_provider, self.meter_provider, self.logger_provider):
            if p is not None:
                try:
                    ok = bool(p.force_flush(ms)) and ok
                except Exception:  # noqa: BLE001
                    ok = False
        return ok

    def shutdown(self, timeout_s: float = 10.0) -> None:
        """Flush final y cierre. Idempotente. Llámalo SIEMPRE al terminar un script (los lotes pendientes se perderían)."""
        if self._closed:
            return
        self.force_flush(timeout_s)
        for p in (self.tracer_provider, self.meter_provider, self.logger_provider):
            if p is not None:
                try:
                    p.shutdown()
                except Exception:  # noqa: BLE001
                    pass
        self._closed = True

    def __enter__(self) -> "TelemetryHandle":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.shutdown()

    # -- copias en memoria -----------------------------------------------------------------------------------------
    def reset_local(self) -> None:
        """Vacía las copias en memoria (no afecta a lo ya enviado al Collector)."""
        if self._span_mem:
            self._span_mem.clear()
        if self._log_mem:
            self._log_mem.clear()
        if self._metric_mem:
            self._metric_mem.collect()          # collect() con cumulativo no resetea; las métricas son acumulativas

    def finished_spans(self) -> list[Any]:
        return list(self._span_mem.get_finished_spans()) if self._span_mem else []

    def span_records(self) -> list[dict[str, Any]]:
        """Spans terminados como dicts con el mismo esquema que ``supportops.schema.SPAN_SCHEMA`` (usable por ``viz.waterfall``)."""
        out = []
        for s in self.finished_spans():
            ctx = s.get_span_context()
            parent = s.parent
            out.append({
                "trace_id": format(ctx.trace_id, "032x"), "span_id": format(ctx.span_id, "016x"),
                "parent_span_id": format(parent.span_id, "016x") if parent else None,
                "name": s.name, "kind": s.kind.name, "start_unix_nano": s.start_time, "end_unix_nano": s.end_time,
                "status": s.status.status_code.name, "status_message": s.status.description,
                "attributes": _attrs(s.attributes),
                "events": [{"name": e.name, "time_unix_nano": e.timestamp, "attributes": _attrs(e.attributes)} for e in s.events],
                "resource": _attrs(s.resource.attributes), "scope": s.instrumentation_scope.name if s.instrumentation_scope else "",
            })
        return out

    def log_records(self) -> list[dict[str, Any]]:
        """Logs exportados como dicts con el esquema de ``supportops.schema.LOG_SCHEMA``."""
        out = []
        for item in (self._log_mem.get_finished_logs() if self._log_mem else []):
            r = getattr(item, "log_record", item)
            res = getattr(item, "resource", None) or getattr(r, "resource", None)
            tid, sid = getattr(r, "trace_id", None), getattr(r, "span_id", None)
            out.append({
                "time_unix_nano": r.timestamp, "severity_text": r.severity_text,
                "severity_number": r.severity_number.value if r.severity_number else None, "body": r.body,
                "attributes": _attrs(r.attributes), "trace_id": format(tid, "032x") if tid else None,
                "span_id": format(sid, "016x") if sid else None, "resource": _attrs(res.attributes) if res else {},
            })
        return out

    def metric_points(self) -> list[dict[str, Any]]:
        """Puntos de métricas acumulados (``name, unit, type, attributes, value|count|sum``) leídos del lector en memoria."""
        if not self._metric_mem:
            return []
        data = self._metric_mem.get_metrics_data()
        out = []
        for rm in (data.resource_metrics if data else []):
            for sm in rm.scope_metrics:
                for m in sm.metrics:
                    for p in m.data.data_points:
                        row: dict[str, Any] = {"name": m.name, "unit": m.unit, "attributes": _attrs(p.attributes)}
                        if hasattr(p, "bucket_counts"):
                            row.update(type="histogram", count=p.count, sum=p.sum, bucket_counts=list(p.bucket_counts),
                                       explicit_bounds=list(p.explicit_bounds))
                        else:
                            row.update(type="sum", value=p.value)
                        out.append(row)
        return out


# ---------------------------------------------------------------------------------------------------------------------
# setup_telemetry
# ---------------------------------------------------------------------------------------------------------------------
_SETUP_LOCK = threading.Lock()
_WARNED: set[str] = set()


def _reset_globals() -> None:
    """Permite volver a registrar los proveedores globales al re-ejecutar una celda de notebook.

    La API de OTel prohíbe sobrescribir el proveedor global (solo se puede fijar UNA vez por proceso); en un notebook
    eso es incómodo. Esto toca atributos PRIVADOS de la API: es un truco de laboratorio/tests, no de producción.
    """
    from opentelemetry._logs import _internal as _l
    from opentelemetry.metrics import _internal as _m
    from opentelemetry.util._once import Once
    for mod, once, prov in ((otel_trace, "_TRACER_PROVIDER_SET_ONCE", "_TRACER_PROVIDER"),
                            (_m, "_METER_PROVIDER_SET_ONCE", "_METER_PROVIDER"),
                            (_l, "_LOGGER_PROVIDER_SET_ONCE", "_LOGGER_PROVIDER")):
        if hasattr(mod, once) and hasattr(mod, prov):
            setattr(mod, once, Once())
            setattr(mod, prov, None)


def _reachable(endpoint: str, timeout_s: float = 0.5) -> bool:
    u = urlparse(endpoint)
    host, port = u.hostname or "localhost", u.port or (443 if u.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except OSError:
        return False


def _warn_once(key: str, msg: str) -> None:
    if key not in _WARNED:
        _WARNED.add(key)
        print(msg)


def setup_telemetry(
    service_name: str,
    *,
    traces: bool = True,
    metrics: bool = True,
    logs: bool = True,
    endpoint: str | None = None,
    resource_attrs: dict[str, Any] | None = None,
    mode: str = "auto",
    keep_local: bool = True,
    set_global: bool = True,
    deterministic_ids: bool = False,
    metric_interval_s: float = 5.0,
    export_timeout_s: float = 5.0,
    service_version: str = SERVICE_VERSION,
) -> TelemetryHandle:
    """Configura trazas, métricas y logs OpenTelemetry (SDK Python) y devuelve un ``TelemetryHandle``.

    * ``endpoint``: base OTLP/HTTP (por defecto ``OTEL_EXPORTER_OTLP_ENDPOINT`` o ``http://localhost:4318``); se añaden
      ``/v1/traces|metrics|logs``. Desde otro contenedor: ``http://otel-collector:4318``.
    * ``mode``: ``"otlp"`` (siempre exporta), ``"memory"`` (solo memoria, sin red), ``"auto"`` (si el puerto no responde,
      degrada a memoria y lo avisa una vez).
    * ``keep_local``: además de exportar, guarda copias en memoria (``handle.span_records()``, ``log_records()``, ``metric_points()``).
    * ``resource_attrs``: se suman a ``service.name``, ``service.version`` y ``service.instance.id``. (``deployment.environment.name``
      lo añade el Collector del curso; pásalo aquí si exportas sin Collector.)
    * ``deterministic_ids``: trace_id/span_id reproducibles (para tests; no lo uses en producción).
    * ``metric_interval_s``: periodo de exportación de métricas (OTel usa 60 s por defecto; aquí 5 s para laboratorios).
    """
    endpoint = (endpoint or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT") or DEFAULT_ENDPOINT).rstrip("/")
    reason = ""
    if mode == "auto":
        if _reachable(endpoint):
            mode = "otlp"
        else:
            mode = "memory"
            reason = f"nada escucha en {endpoint}: modo degradado (solo memoria). Levanta el stack: docker compose --profile core up -d"
            _warn_once("degraded:" + endpoint, "⚠️ setup_telemetry: " + reason)
    if mode not in ("otlp", "memory"):
        raise ValueError("mode debe ser 'auto', 'otlp' o 'memory'")

    attrs: dict[str, Any] = {"service.name": service_name, "service.version": service_version,
                             "service.instance.id": f"{service_name}-{uuid.uuid4().hex[:8]}"}
    attrs.update(resource_attrs or {})
    resource = Resource.create(attrs)
    ids = _Ids(deterministic_ids)
    h = TelemetryHandle(service_name, mode, endpoint if mode == "otlp" else None, resource, ids=ids, reason=reason)
    with _SETUP_LOCK:
        if set_global:
            _reset_globals()
        # ----------------------------------------------------------------------------------------------- trazas
        if traces:
            tp = TracerProvider(resource=resource, id_generator=ids)
            if mode == "otlp":
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
                exp = _CountingSpanExporter(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces", timeout=export_timeout_s),
                                            h.span_export_stats)
                tp.add_span_processor(BatchSpanProcessor(exp, schedule_delay_millis=1000, export_timeout_millis=int(export_timeout_s * 1000)))
            if keep_local or mode == "memory":
                h._span_mem = InMemorySpanExporter()
                tp.add_span_processor(SimpleSpanProcessor(h._span_mem))
            h.tracer_provider = tp
            if set_global:
                otel_trace.set_tracer_provider(tp)
        # --------------------------------------------------------------------------------------------- métricas
        if metrics:
            readers: list[Any] = []
            if mode == "otlp":
                from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
                readers.append(PeriodicExportingMetricReader(
                    OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics", timeout=export_timeout_s),
                    export_interval_millis=int(metric_interval_s * 1000), export_timeout_millis=int(export_timeout_s * 1000)))
            if keep_local or mode == "memory":
                h._metric_mem = InMemoryMetricReader()
                readers.append(h._metric_mem)
            mp = MeterProvider(resource=resource, metric_readers=readers)
            h.meter_provider = mp
            if set_global:
                otel_metrics.set_meter_provider(mp)
        # ------------------------------------------------------------------------------------------------- logs
        if logs:
            lp = LoggerProvider(resource=resource)
            if mode == "otlp":
                from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
                lp.add_log_record_processor(logs_export.BatchLogRecordProcessor(
                    OTLPLogExporter(endpoint=f"{endpoint}/v1/logs", timeout=export_timeout_s),
                    schedule_delay_millis=1000, export_timeout_millis=int(export_timeout_s * 1000)))
            if keep_local or mode == "memory":
                mem_cls = getattr(logs_export, "InMemoryLogRecordExporter", None) or logs_export.InMemoryLogExporter
                h._log_mem = mem_cls()
                lp.add_log_record_processor(logs_export.SimpleLogRecordProcessor(h._log_mem))
            h.logger_provider = lp
            if set_global:
                otel_logs.set_logger_provider(lp)
    return h


# ---------------------------------------------------------------------------------------------------------------------
# Conversión de contenido a la forma de la spec (gen-ai-input-messages.json / gen-ai-output-messages.json)
# ---------------------------------------------------------------------------------------------------------------------
def _clip(text: Any, limit: int) -> str:
    s = text if isinstance(text, str) else json.dumps(text, ensure_ascii=False, default=str)
    return s if len(s) <= limit else s[:limit] + f"…[+{len(s) - limit} car.]"


def messages_to_semconv(messages: list[Any], limit: int = DEFAULT_MAX_CONTENT_CHARS) -> list[dict[str, Any]]:
    """``list[Message]`` de SupportOps -> mensajes de entrada en el formato de la spec (``role`` + ``parts``)."""
    out: list[dict[str, Any]] = []
    for m in messages:
        parts: list[dict[str, Any]] = []
        if m.role == "tool":
            parts.append({"type": "tool_call_response", "id": m.tool_call_id, "response": _clip(m.content, limit)})
        else:
            if m.content:
                parts.append({"type": "text", "content": _clip(m.content, limit)})
            for tc in m.tool_calls:
                parts.append({"type": "tool_call", "id": tc.id, "name": tc.name, "arguments": tc.arguments})
        out.append({"role": m.role, "parts": parts})
    return out


def response_to_semconv(resp: Any, limit: int = DEFAULT_MAX_CONTENT_CHARS) -> list[dict[str, Any]]:
    """``LLMResponse`` -> ``gen_ai.output.messages`` (una elección) con ``finish_reason`` normalizado."""
    parts: list[dict[str, Any]] = []
    if resp.content:
        parts.append({"type": "text", "content": _clip(resp.content, limit)})
    for tc in resp.tool_calls:
        parts.append({"type": "tool_call", "id": tc.id, "name": tc.name, "arguments": tc.arguments})
    return [{"role": "assistant", "parts": parts, "finish_reason": normalize_finish_reason(resp.finish_reason)}]


def normalize_finish_reason(reason: str | None) -> str:
    return FINISH_REASON_MAP.get(reason or "", reason or "error")


def error_type_of(exc: BaseException) -> str:
    """``error.type`` de baja cardinalidad: el código del proveedor/herramienta si existe, si no el nombre de la excepción."""
    return str(getattr(exc, "error_type", None) or type(exc).__qualname__)


# ---------------------------------------------------------------------------------------------------------------------
# OTelInstrumentor
# ---------------------------------------------------------------------------------------------------------------------
class OTelInstrumentor(Instrumentor):
    """``Instrumentor`` de SupportOps con spans GenAI, métricas mínimas y logs correlacionados.

    Parámetros
    ----------
    handle : ``TelemetryHandle`` devuelto por ``setup_telemetry``.
    capture_content : si True, añade ``gen_ai.input.messages`` / ``gen_ai.output.messages`` (chat) y
        ``gen_ai.tool.call.arguments`` / ``.result`` (herramientas) como JSON. **Apagado por defecto** (privacidad y coste;
        módulo 04 y 20).
    redact : función opcional ``str -> str`` aplicada al JSON de contenido antes de guardarlo.
    emit_metrics : emite ``gen_ai.client.inference.duration`` y ``gen_ai.client.inference.usage.{input,output}_tokens``.
        Ponlo a False si compones con otro instrumentor de métricas (p. ej. el del módulo 09) para no contar doble.
    extra_attributes : atributos fijos añadidos a TODOS los spans (p. ej. ``{"supportops.release": "2026.10"}``).

    Convenciones: ``invoke_agent`` es INTERNAL (agente en el mismo proceso), ``chat`` es CLIENT, ``execute_tool`` es INTERNAL.
    Tras ejecutar un ticket, ``instr.trace_ids[ticket_id]`` guarda su trace_id (hex de 32) para buscarlo en Tempo.
    """

    def __init__(self, handle: TelemetryHandle, *, capture_content: bool = False, redact: Callable[[str], str] | None = None,
                 emit_metrics: bool = True, max_content_chars: int = DEFAULT_MAX_CONTENT_CHARS,
                 extra_attributes: dict[str, Any] | None = None):
        self.h = handle
        self.tracer = handle.tracer()
        self.logger = handle.logger()
        self.capture_content, self.redact = capture_content, redact
        self.max_content_chars = max_content_chars
        self.extra = dict(extra_attributes or {})
        self.trace_ids: dict[str, str] = {}
        self.emit_metrics = emit_metrics and handle.meter_provider is not None
        if self.emit_metrics:
            m = handle.meter()
            self._dur = m.create_histogram("gen_ai.client.inference.duration", unit="s",
                                           description="Duración de la operación de inferencia GenAI",
                                           explicit_bucket_boundaries_advisory=DURATION_BOUNDARIES)
            self._in_tok = m.create_counter("gen_ai.client.inference.usage.input_tokens", unit="{token}",
                                            description="Tokens de entrada usados")
            self._out_tok = m.create_counter("gen_ai.client.inference.usage.output_tokens", unit="{token}",
                                             description="Tokens de salida usados")

    # -- utilidades -----------------------------------------------------------------------------------------------
    def _content(self, obj: Any) -> str:
        s = json.dumps(obj, ensure_ascii=False, default=str)
        return self.redact(s) if self.redact else s

    @contextmanager
    def _span(self, ctx: RunContext, name: str, kind: SpanKind, attrs: dict[str, Any]) -> Iterator[Any]:
        """Abre un span con el tiempo simulado, lo deja activo en el contexto y lo cierra con ``end_time`` simulado."""
        t0 = ctx.clock.now_ns()
        span = self.tracer.start_span(name, kind=kind, attributes={**attrs, **self.extra}, start_time=t0)
        try:
            with otel_trace.use_span(span, end_on_exit=False, record_exception=False, set_status_on_exception=False):
                yield span
        finally:
            span.end(end_time=max(ctx.clock.now_ns(), t0))

    @staticmethod
    def _fail(span: Any, exc: BaseException, ctx: RunContext) -> str:
        etype = error_type_of(exc)
        span.set_attribute("error.type", etype)
        span.record_exception(exc, attributes={"exception.escaped": True}, timestamp=ctx.clock.now_ns())
        span.set_status(Status(StatusCode.ERROR, str(exc)[:200]))
        return etype

    # -- hooks ----------------------------------------------------------------------------------------------------
    @contextmanager
    def agent_run(self, ctx: RunContext) -> Iterator[None]:
        t = ctx.ticket
        if self.h.ids.deterministic:
            self.h.begin_trace(stable_hex(32, get_settings().seed, t.ticket_id))
        attrs = {"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": ctx.agent_name,
                 "gen_ai.conversation.id": t.ticket_id, "gen_ai.request.model": ctx.model,
                 "supportops.ticket.id": t.ticket_id, "supportops.customer.id": t.customer_id,
                 "supportops.customer.tier": t.tier, "supportops.channel": t.channel}
        with self._span(ctx, f"invoke_agent {ctx.agent_name}", SpanKind.INTERNAL, attrs) as span:
            tid = format(span.get_span_context().trace_id, "032x")
            ctx.state["trace_id"] = tid
            self.trace_ids[t.ticket_id] = tid
            try:
                yield
            except BaseException as e:
                self._fail(span, e, ctx)
                raise
            r = ctx.result
            if r is not None:
                span.set_attributes({"gen_ai.usage.input_tokens": r.input_tokens, "gen_ai.usage.output_tokens": r.output_tokens,
                                     "supportops.status": r.status, "supportops.cost_usd": r.cost_usd,
                                     "supportops.llm_calls": r.n_llm_calls, "supportops.tool_calls": r.n_tool_calls})
                if r.intent_pred:
                    span.set_attribute("supportops.intent", r.intent_pred)
                if r.status in ("error", "max_steps"):
                    span.set_attribute("error.type", r.error_type or r.status)
                    span.set_status(Status(StatusCode.ERROR, r.status))

    @contextmanager
    def llm_call(self, ctx: RunContext, info: LLMCallInfo) -> Iterator[None]:
        attrs = {"gen_ai.operation.name": "chat", "gen_ai.provider.name": info.provider, "gen_ai.request.model": info.model,
                 "gen_ai.request.max_tokens": info.max_tokens, "gen_ai.request.temperature": info.temperature,
                 "gen_ai.conversation.id": ctx.ticket.ticket_id, "supportops.step": info.step, "supportops.attempt": info.attempt}
        t0 = ctx.clock.now_s()
        with self._span(ctx, f"chat {info.model}", SpanKind.CLIENT, attrs) as span:
            if self.capture_content and info.messages is not None:
                span.set_attribute("gen_ai.input.messages", self._content(messages_to_semconv(info.messages, self.max_content_chars)))
            err_type = None
            try:
                yield
            except BaseException as e:
                err_type = self._fail(span, e, ctx)
                status = getattr(e, "status", None)
                if status:
                    span.set_attribute("http.response.status_code", int(status))
                raise
            finally:
                r = info.response
                if r is not None and err_type is None:
                    fr = normalize_finish_reason(r.finish_reason)
                    span.set_attributes({"gen_ai.response.model": r.model, "gen_ai.response.id": r.response_id,
                                         "gen_ai.response.finish_reasons": [fr],
                                         "gen_ai.usage.input_tokens": r.usage.input_tokens,
                                         "gen_ai.usage.output_tokens": r.usage.output_tokens})
                    if self.capture_content:
                        span.set_attribute("gen_ai.output.messages", self._content(response_to_semconv(r, self.max_content_chars)))
                if self.emit_metrics:
                    self._record_metrics(ctx, info, err_type, ctx.clock.now_s() - t0)

    def _record_metrics(self, ctx: RunContext, info: LLMCallInfo, err_type: str | None, dur: float) -> None:
        r = info.response
        battrs: dict[str, Any] = {"gen_ai.operation.name": "chat", "gen_ai.provider.name": info.provider,
                                  "gen_ai.request.model": info.model}
        if r is not None:
            battrs["gen_ai.response.model"] = r.model
        if err_type:
            battrs["error.type"] = err_type
        # duración = la del reloj simulado (coincide con la del span, como pide la spec)
        self._dur.record(max(dur, 0.0), battrs)
        tok_attrs = {k: v for k, v in battrs.items() if k != "error.type"}
        if r is not None:
            self._in_tok.add(r.usage.input_tokens, {**tok_attrs, "gen_ai.token.modality": "text"})
            self._out_tok.add(r.usage.output_tokens, {**tok_attrs, "gen_ai.token.modality": "text"})
        else:                                   # spec: fallo sin uso -> 0 con modality=unknown
            self._in_tok.add(0, {**tok_attrs, "gen_ai.token.modality": "unknown"})
            self._out_tok.add(0, {**tok_attrs, "gen_ai.token.modality": "unknown"})

    @contextmanager
    def tool_call(self, ctx: RunContext, info: ToolCallInfo) -> Iterator[None]:
        attrs = {"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": info.call.name,
                 "gen_ai.tool.call.id": info.call.id, "gen_ai.tool.type": "function",
                 "gen_ai.agent.name": ctx.agent_name, "gen_ai.conversation.id": ctx.ticket.ticket_id,
                 "supportops.step": info.step}
        with self._span(ctx, f"execute_tool {info.call.name}", SpanKind.INTERNAL, attrs) as span:
            if self.capture_content:
                span.set_attribute("gen_ai.tool.call.arguments", self._content(info.call.arguments))
            try:
                yield
            except BaseException as e:
                self._fail(span, e, ctx)
                raise
            if self.capture_content and info.result is not None:
                span.set_attribute("gen_ai.tool.call.result", _clip(self._content(info.result), self.max_content_chars))

    def log(self, ctx: RunContext, level: int, message: str, fields: dict[str, Any]) -> None:
        attrs: dict[str, Any] = {"supportops.ticket.id": ctx.ticket.ticket_id}
        for k, v in fields.items():
            attrs[LOG_FIELD_MAP.get(k, f"supportops.{k}")] = v
        # ``context`` por defecto = contexto actual: dentro de un span activo el SDK rellena trace_id/span_id/trace_flags
        self.logger.emit(timestamp=ctx.clock.now_ns(), severity_number=otel_logs.SeverityNumber(SEVERITY_NUMBER.get(level, 9)),
                         severity_text=SEVERITY_TEXT.get(level, "INFO"), body=message, attributes=attrs)
