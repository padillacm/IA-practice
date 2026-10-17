"""Laboratorio de logs para el módulo 08 (Loki/LogQL) (autor A3). No edita ``telemetry.py``.

Tres formas de que los logs de SupportOps lleguen a Loki, para comparar en la lección:

1. **OTLP** (la de producción moderna): ``OTelInstrumentor`` de A2 (``setup_telemetry(logs=True)``) → Collector → Loki (``/otlp``).
   ``service_name="supportops-agent"``; el cuerpo es el mensaje y los campos viajan como *structured metadata*.
2. **JSON en el cuerpo** (la forma clásica con ``logging``): ``JsonLogInstrumentor`` empuja una línea JSON por evento con
   el cliente mínimo ``LokiPusher`` (API HTTP ``/loki/api/v1/push``). ``service_name="supportops-agent-json"``.
3. **logfmt de acceso** de los servicios aguas abajo (``llm-gateway``, ``orders-api``, ``kb-search``): ``AccessLogInstrumentor``.
   ``service_name="<servicio>-access"``. Útil para practicar ``| logfmt`` y ``unwrap`` (latencias).

Todas las líneas llevan ``trace_id`` (del span activo): como *structured metadata* y dentro del cuerpo. Los tiempos son los del
reloj simulado del agente, por lo que hay que enviarlas con ``run_batch(..., live=True, extra=[...])`` (ventana que termina ahora).

Uso::

    from supportops.loki_lab import LokiPusher, JsonLogInstrumentor, AccessLogInstrumentor, wait_for_logs
    from supportops.tempo_lab import run_batch
    push = LokiPusher()
    b = run_batch(120, 42, live=True, extra=[JsonLogInstrumentor(push), AccessLogInstrumentor(push)])
    push.flush()
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections import defaultdict
from contextlib import contextmanager
from typing import Any, Iterator

from . import backends
from .instrument import Instrumentor, LLMCallInfo, RunContext, ToolCallInfo
from .stack import services

__all__ = ["run_logs_batch", "loki_range", "loki_stats", "LokiPusher", "JsonLogInstrumentor", "AccessLogInstrumentor", "wait_for_logs", "logfmt", "LEVELS"]

LEVELS = {10: "debug", 20: "info", 30: "warn", 40: "error", 50: "critical"}


def logfmt(d: dict[str, Any]) -> str:
    """Serializa un dict a ``clave=valor`` (comillas si el valor tiene espacios o comillas), como pide el parser ``| logfmt``."""
    out = []
    for k, v in d.items():
        s = str(v)
        out.append(f'{k}="{s.replace(chr(34), chr(39))}"' if (" " in s or "=" in s or '"' in s or not s) else f"{k}={s}")
    return " ".join(out)


class LokiPusher:
    """Cliente mínimo de la API de ingesta de Loki (JSON, sin dependencias): agrupa por *stream* y envía por lotes.

    ``labels`` son las etiquetas de ÍNDICE del stream (pocas y de baja cardinalidad); ``metadata`` es *structured metadata*
    por línea (alta cardinalidad permitida: ``trace_id``, ``ticket_id``...). Todos los valores deben ser ``str``.
    """

    def __init__(self, url: str | None = None, max_batch: int = 1000, timeout: float = 10.0):
        self.url = (url or services()["loki"]["ui"]).rstrip("/") + "/loki/api/v1/push"
        self.max_batch, self.timeout = max_batch, timeout
        self._buf: dict[tuple, list[list[Any]]] = defaultdict(list)
        self._all: dict[tuple, list[list[Any]]] = defaultdict(list)       # copia permanente (flush no la borra)
        self._n = 0
        self.sent = 0
        self.requests = 0

    def add(self, ts_ns: int, line: str, labels: dict[str, str], metadata: dict[str, str] | None = None) -> None:
        key = tuple(sorted(labels.items()))
        entry: list[Any] = [str(int(ts_ns)), line]
        if metadata:
            entry.append({k: str(v) for k, v in metadata.items()})
        self._buf[key].append(entry)
        self._all[key].append(entry)
        self._n += 1
        if self._n >= self.max_batch:
            self.flush()

    def payload(self) -> dict[str, Any]:
        return {"streams": [{"stream": dict(k), "values": sorted(v, key=lambda e: int(e[0]))} for k, v in self._buf.items()]}

    def full_payload(self) -> dict[str, Any]:
        """Todo lo añadido desde el principio (aunque ya se haya enviado): para analizar con ``logql_mini`` y comparar con Loki."""
        return {"streams": [{"stream": dict(k), "values": sorted(v, key=lambda e: int(e[0]))} for k, v in self._all.items()]}

    def flush(self) -> int:
        if not self._n:
            return 0
        body = json.dumps(self.payload()).encode()
        req = urllib.request.Request(self.url, data=body, method="POST", headers={"Content-Type": "application/json"})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(req, timeout=self.timeout) as r:
                r.read()
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Loki rechazó el lote ({e.code}): {e.read()[:300].decode(errors='replace')}") from e
        n = self._n
        self.sent += n
        self.requests += 1
        self._buf.clear()
        self._n = 0
        return n


def _trace_ctx(ctx: RunContext) -> tuple[str, str]:
    """(trace_id, span_id) del span activo (OTel); si no hay, el trace_id que dejó el instrumentor en ``ctx.state``."""
    try:
        from opentelemetry import trace
        sc = trace.get_current_span().get_span_context()
        if sc.is_valid:
            return format(sc.trace_id, "032x"), format(sc.span_id, "016x")
    except ImportError:  # pragma: no cover
        pass
    return str(ctx.state.get("trace_id", "")), ""


class JsonLogInstrumentor(Instrumentor):
    """Una línea JSON por evento del agente (``logging`` estructurado) → Loki. Componer DESPUÉS de ``OTelInstrumentor``."""

    def __init__(self, pusher: LokiPusher, service: str = "supportops-agent-json", env: str = "lab"):
        self.p, self.labels = pusher, {"service_name": service, "deployment_environment_name": env}

    def log(self, ctx: RunContext, level: int, message: str, fields: dict[str, Any]) -> None:
        trace_id, span_id = _trace_ctx(ctx)
        lvl = LEVELS.get(level, "info")
        doc = {"level": lvl, "msg": message, "ticket_id": ctx.ticket.ticket_id, "tier": ctx.ticket.tier, "channel": ctx.ticket.channel, **fields,
               "trace_id": trace_id, "span_id": span_id}
        meta = {"trace_id": trace_id, "span_id": span_id, "ticket_id": ctx.ticket.ticket_id}
        self.p.add(ctx.clock.now_ns(), json.dumps(doc, ensure_ascii=False, default=str), self.labels, {k: v for k, v in meta.items() if v})


class AccessLogInstrumentor(Instrumentor):
    """Logs de acceso en **logfmt** de los servicios aguas abajo (mismo reparto de rutas que ``tempo_lab``)."""

    ROUTES = {"get_order": ("orders-api", "GET", "/orders/{id}"), "issue_refund": ("orders-api", "POST", "/orders/{id}/refund"),
              "search_kb": ("kb-search", "GET", "/kb/search")}

    def __init__(self, pusher: LokiPusher, env: str = "lab"):
        self.p, self.env = pusher, env

    def _emit(self, ctx: RunContext, service: str, method: str, route: str, status: int, t0: int, t1: int, extra: dict[str, Any]) -> None:
        trace_id, _ = _trace_ctx(ctx)
        level = "error" if status >= 500 else ("warn" if status >= 400 else "info")
        line = logfmt({"level": level, "method": method, "route": route, "status": status, "duration_ms": round((t1 - t0) / 1e6, 1), **extra,
                       "trace_id": trace_id})
        self.p.add(t1, line, {"service_name": f"{service}-access", "deployment_environment_name": self.env}, {"trace_id": trace_id} if trace_id else None)

    @contextmanager
    def llm_call(self, ctx: RunContext, info: LLMCallInfo) -> Iterator[None]:
        t0, err = ctx.clock.now_ns(), None
        try:
            yield
        except BaseException as e:
            err = e
            raise
        finally:
            self._emit(ctx, "llm-gateway", "POST", "/v1/chat/completions", int(getattr(err, "status", 200)) if err else 200, t0,
                       max(ctx.clock.now_ns(), t0 + 1), {"model": info.model, "attempt": info.attempt})

    @contextmanager
    def tool_call(self, ctx: RunContext, info: ToolCallInfo) -> Iterator[None]:
        t0, err = ctx.clock.now_ns(), None
        try:
            yield
        except BaseException as e:
            err = e
            raise
        finally:
            r = self.ROUTES.get(info.call.name)
            if r:
                self._emit(ctx, r[0], r[1], r[2], 500 if err else 200, t0, max(ctx.clock.now_ns(), t0 + 1),
                           {"error": getattr(err, "error_type", "")} if err else {})


def wait_for_logs(logql: str, min_count: int = 1, timeout_s: float = 60.0, every_s: float = 2.0, minutes: int = 30, verbose: bool = True) -> int:
    """Polling con plazo hasta que ``logql`` devuelva al menos ``min_count`` líneas (Loki tarda unos segundos en indexar)."""
    t0, n = time.time(), 0
    while time.time() - t0 < timeout_s:
        try:
            n = len(backends.loki_query(logql, minutes=minutes, limit=5000))
        except backends.BackendError:
            n = 0
        if n >= min_count:
            break
        time.sleep(every_s)
    if verbose:
        print(f"{n} líneas visibles en Loki tras {time.time() - t0:.0f} s (esperadas ≥ {min_count})")
    return n


# ---------------------------------------------------------------------------------------------------------------------
def run_logs_batch(n: int = 120, seed: int = 42, *, live: bool = True, export: bool | None = None, duration_s: float = 600.0):
    """Lote de SupportOps con trazas (OTLP) **y** logs por las tres rutas. Devuelve ``(Batch, LokiPusher)``.

    Si ``export`` no es ``False`` y Loki responde, se envían a Loki los logs JSON y de acceso (``pusher.flush()``); los logs OTLP
    viajan por el Collector con ``OTelInstrumentor``. Con ``export=False`` todo queda en memoria (``pusher.payload()``).
    """
    from .tempo_lab import run_batch
    push = LokiPusher()
    b = run_batch(n, seed, live=live, export=export, duration_s=duration_s, extra=[JsonLogInstrumentor(push), AccessLogInstrumentor(push)])
    if export is not False:
        try:
            push.flush()
        except Exception as e:  # noqa: BLE001  (sin Loki: dejamos el payload en memoria)
            print(f"(no se pudo enviar a Loki: {str(e)[:100]})")
    return b, push


def loki_range(logql: str, minutes: int = 15, step_s: int = 15) -> dict[str, list[tuple[float, float]]]:
    """Consulta de MÉTRICAS (``rate(...)``, ``sum by``, ``quantile_over_time``) -> ``{etiquetas: [(t_seg, valor), ...]}``."""
    now = time.time_ns()
    d = backends._get(backends._base("loki") + "/loki/api/v1/query_range",
                      {"query": logql, "start": now - minutes * 60 * 10**9, "end": now, "step": step_s}, timeout=30.0)
    out: dict[str, list[tuple[float, float]]] = {}
    for r in d.get("data", {}).get("result", []):
        key = ",".join(f"{k}={v}" for k, v in sorted(r["metric"].items())) or "total"
        out[key] = [(float(t), float(v)) for t, v in r["values"] if v not in ("NaN", "+Inf", "-Inf")]
    return out


def loki_stats(logql: str, minutes: int = 30) -> dict[str, Any]:
    """Estadísticas de ejecución de una consulta de logs (``data.stats.summary``: bytes procesados, líneas, tiempo)."""
    now = time.time_ns()
    d = backends._get(backends._base("loki") + "/loki/api/v1/query_range",
                      {"query": logql, "start": now - minutes * 60 * 10**9, "end": now + 60 * 10**9, "limit": 5000}, timeout=30.0)
    s = d.get("data", {}).get("stats", {}).get("summary", {})
    return {"bytes_processed": s.get("totalBytesProcessed"), "lines_processed": s.get("totalLinesProcessed"), "exec_time_s": s.get("execTime"),
            "lines_returned": sum(len(r["values"]) for r in d.get("data", {}).get("result", []))}
