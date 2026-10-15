"""Dashboards de Grafana COMO CÓDIGO (módulos 09 y 10): un constructor mínimo del JSON clásico de dashboards.

    from supportops.dashkit import Dashboard, timeseries, stat, prom, loki, tempo
    d = Dashboard("mi-dashboard", "Mi dashboard", tags=["curso"])
    d.row("Tráfico")
    d.add(timeseries("Peticiones/s", [prom("sum(rate(supportops_agent_requests_total[$__rate_interval]))", "req/s")], unit="reqps"))
    d.save("stack/grafana/dashboards/10-mi-dashboard.json")          # Grafana lo recarga cada 10 s (provisioning)

Por qué existe: el JSON de un dashboard exportado desde la UI tiene cientos de líneas de ruido (ids, versiones, valores por
defecto). Aquí cada panel es una llamada de una línea, el diseño (``gridPos``) se calcula solo y el resultado es
**determinista** (misma entrada → mismo JSON, diffs limpios en git). Es una versión didáctica de lo que hacen Grafonnet o
el Grafana Foundation SDK; el JSON generado es el esquema clásico (``schemaVersion`` 39), que Grafana 13 sigue cargando.

Convenciones del curso: UIDs de datasource fijos (``prometheus``, ``loki``, ``tempo``); ``uid`` del dashboard estable (es lo
que usan los enlaces); prefijo ``NN-`` en el nombre de archivo según el módulo.
"""
from __future__ import annotations

import json
import pathlib
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = 39
DS_PROM = {"type": "prometheus", "uid": "prometheus"}
DS_LOKI = {"type": "loki", "uid": "loki"}
DS_TEMPO = {"type": "tempo", "uid": "tempo"}

# Paleta de umbrales habituales
GREEN, YELLOW, ORANGE, RED, BLUE, PURPLE = "green", "#EAB839", "orange", "red", "blue", "purple"


# ---------------------------------------------------------------------------------------------------------------------
# Consultas (targets)
# ---------------------------------------------------------------------------------------------------------------------
def prom(expr: str, legend: str = "", *, ref: str = "A", exemplar: bool = False, instant: bool = False, fmt: str | None = None,
         hide: bool = False) -> dict[str, Any]:
    """Consulta PromQL. ``exemplar=True`` pide los exemplars (rombos clicables hacia la traza) en paneles de series temporales.
    ``fmt='heatmap'`` para histogramas clásicos (``sum by (le)(rate(..._bucket[...]))``)."""
    t: dict[str, Any] = {"datasource": DS_PROM, "editorMode": "code", "expr": expr, "legendFormat": legend or "__auto",
                         "range": not instant, "instant": instant, "refId": ref}
    if exemplar:
        t["exemplar"] = True
    if fmt:
        t["format"] = fmt
    if hide:
        t["hide"] = True
    return t


def loki(expr: str, legend: str = "", *, ref: str = "A", query_type: str = "range", max_lines: int = 200) -> dict[str, Any]:
    """Consulta LogQL (logs o métrica de logs). ``query_type='instant'`` para stat/bargauge."""
    return {"datasource": DS_LOKI, "editorMode": "code", "expr": expr, "legendFormat": legend, "queryType": query_type,
            "maxLines": max_lines, "refId": ref}


def tempo(query: str, *, ref: str = "A", limit: int = 20, table_type: str = "traces", query_type: str = "traceql") -> dict[str, Any]:
    """Consulta TraceQL. ``table_type='traces'`` devuelve una fila por traza; ``'spans'`` una fila por span."""
    return {"datasource": DS_TEMPO, "queryType": query_type, "query": query, "limit": limit, "tableType": table_type,
            "filters": [], "refId": ref}


def link(title: str, url: str, *, blank: bool = True) -> dict[str, Any]:
    """Data link (enlace de datos) de un panel o campo. Admite variables (``${__data.fields.trace_id}``, ``${__url_time_range}``)."""
    return {"title": title, "url": url, "targetBlank": blank}


def explore_url(datasource_uid: str, query: Mapping[str, Any], *, range_from: str = "${__from}", range_to: str = "${__to}") -> str:
    """URL de Explore con una consulta ya rellenada (para data links). Las llaves de variables de Grafana se respetan."""
    panes = {"a": {"datasource": datasource_uid, "queries": [{"refId": "A", "datasource": {"uid": datasource_uid}, **query}],
                   "range": {"from": range_from, "to": range_to}}}
    return "/explore?schemaVersion=1&panes=" + json.dumps(panes, separators=(",", ":"), ensure_ascii=False) + "&orgId=1"


def thresholds(*steps: tuple[float | None, str]) -> dict[str, Any]:
    """``thresholds((None,'green'),(2,'orange'),(5,'red'))`` → umbrales absolutos."""
    return {"mode": "absolute", "steps": [{"color": c, "value": v} for v, c in steps]}


# ---------------------------------------------------------------------------------------------------------------------
# Paneles
# ---------------------------------------------------------------------------------------------------------------------
def _panel(kind: str, title: str, targets: Sequence[dict[str, Any]], *, w: int, h: int, description: str = "", ds: dict[str, Any] | None = None,
           options: dict[str, Any] | None = None, defaults: dict[str, Any] | None = None, overrides: Sequence[dict[str, Any]] = (),
           links: Sequence[dict[str, Any]] = (), transformations: Sequence[dict[str, Any]] = (), repeat: str | None = None) -> dict[str, Any]:
    p: dict[str, Any] = {"type": kind, "title": title, "description": description, "gridPos": {"x": 0, "y": 0, "w": w, "h": h},
                         "targets": [dict(t) for t in targets], "options": options or {},
                         "fieldConfig": {"defaults": defaults or {}, "overrides": list(overrides)}}
    if ds is None and targets:
        ds = targets[0].get("datasource")
    if ds:
        p["datasource"] = ds
    if links:
        p["links"] = list(links)
    if transformations:
        p["transformations"] = list(transformations)
    if repeat:
        p["repeat"] = repeat
        p["repeatDirection"] = "h"
    return p


def timeseries(title: str, targets: Sequence[dict[str, Any]], *, unit: str = "short", w: int = 12, h: int = 8, description: str = "",
               stack: bool = False, fill: int = 12, min: float | None = None, max: float | None = None, legend: str = "list",
               thr: dict[str, Any] | None = None, thr_style: str = "line", links: Sequence[dict[str, Any]] = (),
               overrides: Sequence[dict[str, Any]] = (), decimals: int | None = None, log_scale: int | None = None) -> dict[str, Any]:
    custom: dict[str, Any] = {"drawStyle": "line", "lineWidth": 2, "fillOpacity": fill, "showPoints": "never", "spanNulls": True,
                              "stacking": {"mode": "normal" if stack else "none", "group": "A"},
                              "thresholdsStyle": {"mode": thr_style if thr else "off"}}
    if log_scale:
        custom["scaleDistribution"] = {"type": "log", "log": log_scale}
    d: dict[str, Any] = {"unit": unit, "custom": custom, "color": {"mode": "palette-classic"}}
    if min is not None:
        d["min"] = min
    if max is not None:
        d["max"] = max
    if decimals is not None:
        d["decimals"] = decimals
    d["thresholds"] = thr or thresholds((None, GREEN))
    opts = {"legend": {"displayMode": legend, "placement": "bottom", "showLegend": legend != "hidden"},
            "tooltip": {"mode": "multi", "sort": "desc"}}
    return _panel("timeseries", title, targets, w=w, h=h, description=description, options=opts, defaults=d, links=links, overrides=overrides)


def stat(title: str, expr_or_target: str | dict[str, Any], *, unit: str = "short", w: int = 4, h: int = 4, description: str = "",
         thr: dict[str, Any] | None = None, color_mode: str = "background", graph: str = "area", decimals: int | None = None,
         links: Sequence[dict[str, Any]] = (), reduce: str = "lastNotNull", no_value: str = "sin datos", mappings: Sequence[dict] = (),
         datasource: dict[str, Any] | None = None) -> dict[str, Any]:
    t = prom(expr_or_target, "") if isinstance(expr_or_target, str) else expr_or_target
    if datasource:
        t = {**t, "datasource": datasource}
    d: dict[str, Any] = {"unit": unit, "noValue": no_value, "thresholds": thr or thresholds((None, GREEN)), "color": {"mode": "thresholds"},
                         "mappings": list(mappings)}
    if decimals is not None:
        d["decimals"] = decimals
    opts = {"colorMode": color_mode, "graphMode": graph, "justifyMode": "auto", "textMode": "auto", "orientation": "auto",
            "reduceOptions": {"calcs": [reduce], "fields": "", "values": False}}
    return _panel("stat", title, [t], w=w, h=h, description=description, options=opts, defaults=d, links=links)


def gauge(title: str, expr: str, *, unit: str = "percentunit", min: float = 0, max: float = 1, w: int = 4, h: int = 5,
          thr: dict[str, Any] | None = None, description: str = "") -> dict[str, Any]:
    d = {"unit": unit, "min": min, "max": max, "thresholds": thr or thresholds((None, GREEN), (0.8 * max, RED)), "color": {"mode": "thresholds"}}
    opts = {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False}, "showThresholdLabels": False, "showThresholdMarkers": True}
    return _panel("gauge", title, [prom(expr, "", instant=True)], w=w, h=h, description=description, options=opts, defaults=d)


def bargauge(title: str, targets: Sequence[dict[str, Any]], *, unit: str = "short", w: int = 8, h: int = 8, description: str = "",
             thr: dict[str, Any] | None = None, min: float | None = 0, max: float | None = None, display: str = "gradient") -> dict[str, Any]:
    d: dict[str, Any] = {"unit": unit, "thresholds": thr or thresholds((None, BLUE)), "color": {"mode": "thresholds"}}
    if min is not None:
        d["min"] = min
    if max is not None:
        d["max"] = max
    opts = {"displayMode": display, "orientation": "horizontal", "showUnfilled": True, "valueMode": "color", "namePlacement": "auto",
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False}}
    return _panel("bargauge", title, targets, w=w, h=h, description=description, options=opts, defaults=d)


def heatmap(title: str, expr: str, *, unit: str = "s", w: int = 12, h: int = 8, description: str = "", exemplar: bool = False,
            scheme: str = "Oranges", log: int = 2) -> dict[str, Any]:
    """Heatmap de un histograma clásico: ``expr`` = ``sum by (le) (increase(..._bucket[$__rate_interval]))`` (formato heatmap)."""
    opts = {"calculate": False, "cellGap": 1, "color": {"mode": "scheme", "scheme": scheme, "fill": "dark-orange", "scale": "exponential",
                                                          "exponent": 0.5, "steps": 64, "reverse": False},
            "yAxis": {"axisPlacement": "left", "unit": unit, "reverse": False}, "legend": {"show": True},
            "tooltip": {"mode": "single", "yHistogram": False, "showColorScale": False}, "exemplars": {"color": "rgba(255,0,255,0.7)"},
            "rowsFrame": {"layout": "auto"}}
    return _panel("heatmap", title, [prom(expr, "{{le}}", fmt="heatmap", exemplar=exemplar)], w=w, h=h, description=description,
                  options=opts, defaults={"custom": {"scaleDistribution": {"type": "linear"}}})


def table(title: str, targets: Sequence[dict[str, Any]], *, w: int = 24, h: int = 8, description: str = "",
          overrides: Sequence[dict[str, Any]] = (), transformations: Sequence[dict[str, Any]] = (), links: Sequence[dict[str, Any]] = (),
          sort_by: str | None = None, desc: bool = True, unit: str = "short") -> dict[str, Any]:
    opts: dict[str, Any] = {"showHeader": True, "cellHeight": "sm", "footer": {"show": False}}
    if sort_by:
        opts["sortBy"] = [{"displayName": sort_by, "desc": desc}]
    return _panel("table", title, targets, w=w, h=h, description=description, options=opts,
                  defaults={"unit": unit, "custom": {"align": "auto", "cellOptions": {"type": "auto"}, "inspect": False}},
                  overrides=overrides, transformations=transformations, links=links)


def logs(title: str, expr: str, *, w: int = 24, h: int = 10, description: str = "", ref: str = "A", wrap: bool = True,
         links: Sequence[dict[str, Any]] = ()) -> dict[str, Any]:
    opts = {"showTime": True, "showLabels": False, "showCommonLabels": False, "wrapLogMessage": wrap, "prettifyLogMessage": False,
            "enableLogDetails": True, "dedupStrategy": "none", "sortOrder": "Descending", "enableInfiniteScrolling": False}
    return _panel("logs", title, [loki(expr, ref=ref)], w=w, h=h, description=description, options=opts, links=links)


def traces_table(title: str, traceql: str, *, w: int = 24, h: int = 9, description: str = "", limit: int = 20) -> dict[str, Any]:
    """Tabla de trazas (TraceQL). Cada fila lleva el ``traceID`` con enlace a la vista de la traza en Explore."""
    return _panel("table", title, [tempo(traceql, limit=limit)], w=w, h=h, description=description,
                  options={"showHeader": True, "cellHeight": "sm", "footer": {"show": False}},
                  defaults={"custom": {"align": "auto", "cellOptions": {"type": "auto"}}})


def text(title: str, markdown: str, *, w: int = 24, h: int = 3) -> dict[str, Any]:
    return {"type": "text", "title": title, "gridPos": {"x": 0, "y": 0, "w": w, "h": h}, "transparent": False,
            "options": {"mode": "markdown", "content": markdown}}


# ---------------------------------------------------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------------------------------------------------
def var_query(name: str, query: str, *, label: str | None = None, multi: bool = True, all_: bool = True, ds: dict[str, Any] = DS_PROM,
              regex: str = "", sort: int = 1, description: str = "", current: str | None = None) -> dict[str, Any]:
    """Variable de consulta. Con Prometheus ``query`` suele ser ``label_values(metrica, etiqueta)``; con ``all_=True`` el
    valor «All» se expande a una regex ``.*`` (o a la lista de valores si ``allValue`` no se define)."""
    v: dict[str, Any] = {"name": name, "label": label or name, "type": "query", "datasource": ds, "refresh": 2, "sort": sort,
                         "query": {"query": query, "refId": f"var-{name}"} if ds is not DS_PROM else {"query": query, "qryType": 1, "refId": f"var-{name}"},
                         "regex": regex, "multi": multi, "includeAll": all_, "description": description, "hide": 0, "skipUrlSync": False}
    if all_:
        v["allValue"] = ".*"
    if current:
        v["current"] = {"text": current, "value": current}
    return v


def var_custom(name: str, values: Sequence[str], *, label: str | None = None, default: str | None = None, multi: bool = False) -> dict[str, Any]:
    d = default if default is not None else values[0]
    return {"name": name, "label": label or name, "type": "custom", "query": ",".join(values), "multi": multi, "includeAll": False,
            "current": {"text": d, "value": d}, "options": [{"text": x, "value": x, "selected": x == d} for x in values], "hide": 0}


def var_interval(name: str = "agg", values: Sequence[str] = ("1m", "5m", "15m"), default: str = "5m") -> dict[str, Any]:
    return {"name": name, "label": "Ventana", "type": "interval", "query": ",".join(values), "auto": False,
            "current": {"text": default, "value": default}, "options": [{"text": x, "value": x, "selected": x == default} for x in values], "hide": 0}


def var_datasource(name: str, kind: str, *, label: str | None = None) -> dict[str, Any]:
    return {"name": name, "label": label or name, "type": "datasource", "query": kind, "refresh": 1, "hide": 0, "multi": False,
            "includeAll": False, "options": [], "current": {}}


# ---------------------------------------------------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------------------------------------------------
class Dashboard:
    """Acumula paneles y calcula ``gridPos`` (24 columnas; los paneles se colocan de izquierda a derecha y saltan de fila)."""

    def __init__(self, uid: str, title: str, *, tags: Iterable[str] = (), description: str = "", refresh: str = "10s",
                 time_from: str = "now-30m", time_to: str = "now", timezone: str = "browser", graph_tooltip: int = 1):
        if len(uid) > 40:
            raise ValueError("uid ≤ 40 caracteres")
        self.d: dict[str, Any] = {
            "uid": uid, "title": title, "description": description, "tags": list(tags), "timezone": timezone, "schemaVersion": SCHEMA_VERSION,
            "version": 1, "editable": True, "graphTooltip": graph_tooltip, "refresh": refresh, "time": {"from": time_from, "to": time_to},
            "timepicker": {}, "templating": {"list": []}, "annotations": {"list": [{
                "builtIn": 1, "datasource": {"type": "grafana", "uid": "-- Grafana --"}, "enable": True, "hide": True,
                "iconColor": "rgba(0, 211, 255, 1)", "name": "Annotations & Alerts", "type": "dashboard"}]},
            "links": [], "panels": []}
        self._x = self._y = self._row_h = 0
        self._id = 0

    # -- construcción ---------------------------------------------------------------------------------------------
    def variable(self, v: dict[str, Any]) -> "Dashboard":
        self.d["templating"]["list"].append(v)
        return self

    def dash_link(self, title: str, url: str, *, tags: Sequence[str] = (), keep_time: bool = True, include_vars: bool = True,
                  as_dropdown: bool = False, icon: str = "external link") -> "Dashboard":
        """Enlace del dashboard: a una URL (``url``) o a otros dashboards con ciertos ``tags`` (``as_dropdown``)."""
        if tags:
            self.d["links"].append({"title": title, "type": "dashboards", "tags": list(tags), "asDropdown": as_dropdown,
                                    "keepTime": keep_time, "includeVars": include_vars, "icon": icon, "targetBlank": False})
        else:
            self.d["links"].append({"title": title, "type": "link", "url": url, "keepTime": keep_time, "includeVars": include_vars,
                                    "icon": icon, "targetBlank": False, "tooltip": title})
        return self

    def row(self, title: str, *, collapsed: bool = False) -> "Dashboard":
        self._flush_row()
        self._id += 1
        self.d["panels"].append({"type": "row", "id": self._id, "title": title, "collapsed": collapsed, "panels": [],
                                 "gridPos": {"x": 0, "y": self._y, "w": 24, "h": 1}})
        self._y += 1
        return self

    def _flush_row(self) -> None:
        if self._x:
            self._y += self._row_h
        self._x, self._row_h = 0, 0

    def add(self, *panels: dict[str, Any]) -> "Dashboard":
        for p in panels:
            gp = p["gridPos"]
            if self._x + gp["w"] > 24:
                self._flush_row()
            gp["x"], gp["y"] = self._x, self._y
            self._x += gp["w"]
            self._row_h = max(self._row_h, gp["h"])
            self._id += 1
            p["id"] = self._id
            self.d["panels"].append(p)
        return self

    # -- salida ---------------------------------------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return json.loads(json.dumps(self.d))

    def to_json(self) -> str:
        return json.dumps(self.d, indent=2, ensure_ascii=False, sort_keys=False) + "\n"

    def save(self, path: str | pathlib.Path) -> pathlib.Path:
        p = pathlib.Path(path)
        p.write_text(self.to_json(), encoding="utf-8")
        return p


# ---------------------------------------------------------------------------------------------------------------------
# Lint y API
# ---------------------------------------------------------------------------------------------------------------------
def walk_panels(d: Mapping[str, Any]) -> Iterable[dict[str, Any]]:
    for p in d.get("panels", []):
        yield p
        yield from p.get("panels", [])


def lint(d: Mapping[str, Any]) -> list[str]:
    """Reglas de higiene de un dashboard (devuelve la lista de problemas; vacía = OK)."""
    problems: list[str] = []
    if not d.get("uid"):
        problems.append("falta uid estable")
    if not d.get("title"):
        problems.append("falta title")
    if not d.get("tags"):
        problems.append("sin tags (no se podrá enlazar por tags)")
    ids = [p.get("id") for p in walk_panels(d)]
    if len(ids) != len(set(ids)):
        problems.append("ids de panel duplicados")
    for p in walk_panels(d):
        if p["type"] == "row":
            continue
        t = p.get("title") or ""
        if not t.strip():
            problems.append(f"panel {p.get('id')} sin título")
        if p["type"] != "text":
            if not p.get("description"):
                problems.append(f"«{t}»: sin description (qué mide y cómo leerlo)")
            for tg in p.get("targets", []):
                ds = tg.get("datasource") or p.get("datasource") or {}
                if not ds.get("uid"):
                    problems.append(f"«{t}»: target sin datasource.uid")
                expr = tg.get("expr", "")
                if "rate(" in expr and "[" in expr:
                    import re
                    for m in re.finditer(r"rate\([^)]*?\[([^\]]+)\]", expr):
                        if m.group(1) not in ("$__rate_interval", "$agg") and not m.group(1).endswith("m") and not m.group(1).endswith("h"):
                            problems.append(f"«{t}»: ventana de rate rara «{m.group(1)}»")
    return problems
