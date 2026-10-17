"""Clientes mínimos (solo ``urllib``) para consultar el stack local desde un notebook: Tempo, Loki, Prometheus, Grafana.

Todos aceptan ``minutes`` (ventana hacia atrás desde ahora) y devuelven ``dict`` ya decodificado. Si el servicio no está
disponible lanzan ``BackendError`` (usa ``check_stack()`` antes). Los tiempos son de pared (hora real): para datos
enviados con ``generate_tickets(start_s="live")``.
"""
from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .stack import services


class BackendError(RuntimeError):
    pass


def _get(url: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None, timeout: float = 10.0) -> Any:
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(url, headers=headers or {})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=timeout) as r:
            body = r.read()
    except urllib.error.HTTPError as e:
        raise BackendError(f"{e.code} en {url}: {e.read()[:300].decode(errors='replace')}") from e
    except Exception as e:
        raise BackendError(f"no puedo conectar con {url}: {e}. ¿Está el stack arriba? (check_stack())") from e
    return json.loads(body) if body else {}


def _base(name: str) -> str:
    return services()[name]["ui"].rstrip("/")


def tempo_search(traceql: str, minutes: int = 60, limit: int = 20) -> dict[str, Any]:
    """GET /api/search con una consulta TraceQL. Tras enviar trazas espera de unos segundos a ~30 s (live-store) antes de verlas."""
    now = int(time.time())
    return _get(_base("tempo") + "/api/search", {"q": traceql, "start": now - minutes * 60, "end": now + 60, "limit": limit})


def tempo_trace(trace_id: str) -> dict[str, Any]:
    """GET /api/traces/<id> (formato OTLP/JSON: batches -> scopeSpans -> spans)."""
    return _get(_base("tempo") + f"/api/traces/{trace_id}")


def loki_query(logql: str, minutes: int = 60, limit: int = 100, direction: str = "backward") -> list[dict[str, Any]]:
    """GET /loki/api/v1/query_range. Devuelve una lista plana de {timestamp_ns, line, labels}."""
    now = time.time_ns()
    d = _get(_base("loki") + "/loki/api/v1/query_range",
             {"query": logql, "start": now - minutes * 60 * 10**9, "end": now + 60 * 10**9, "limit": limit, "direction": direction})
    out = []
    for stream in d.get("data", {}).get("result", []):
        for ts, line in stream["values"]:
            out.append({"timestamp_ns": int(ts), "line": line, "labels": stream["stream"]})
    return sorted(out, key=lambda x: x["timestamp_ns"])


def prom_query(promql: str) -> list[dict[str, Any]]:
    """GET /api/v1/query (instantánea). Devuelve la lista ``result`` de Prometheus ({metric, value})."""
    return _get(_base("prometheus") + "/api/v1/query", {"query": promql}).get("data", {}).get("result", [])


def grafana_api(path: str, user: str = "admin", password: str = "admin") -> Any:
    """GET autenticado (basic auth del laboratorio) a la API de Grafana, p. ej. ``grafana_api('/api/datasources')``."""
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return _get(_base("grafana") + path, headers={"Authorization": f"Basic {token}"})


def grafana_post(path: str, payload: dict[str, Any], user: str = "admin", password: str = "admin") -> Any:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    req = urllib.request.Request(_base("grafana") + path, data=json.dumps(payload).encode(), method="POST",
                                 headers={"Authorization": f"Basic {token}", "Content-Type": "application/json"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=10) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raise BackendError(f"{e.code}: {e.read()[:300].decode(errors='replace')}") from e
