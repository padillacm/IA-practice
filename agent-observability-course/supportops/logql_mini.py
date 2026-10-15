"""Mini motor de LogQL (consultas de LOGS) en Python puro (módulo 08, autor A3).

Evalúa un SUBCONJUNTO de LogQL sobre entradas en memoria, con el mismo modelo que Loki: cada entrada pertenece a un *stream*
(etiquetas de índice), tiene una línea y *structured metadata*. Sirve para (1) entender el pipeline de una consulta de logs
(selector → filtros de línea → parsers → filtros de etiqueta) implementándolo, y (2) corregir el proyecto del módulo sin stack
(validado contra Loki 3.7 con una batería de consultas: ver la lección).

Soportado::

    {a="x", b!="y", c=~"re", d!~"re"}                 selector de stream (obligatorio, al menos un matcher)
    |= "texto"   != "texto"   |~ "regex"   !~ "regex"  filtros de línea (también con `backticks`)
    | json       | logfmt                              parsers (json aplana objetos anidados con «_»)
    | etiqueta op valor   (op: = != > >= < <= =~ !~)   filtros de etiqueta; varios con `and`, `or` o coma
    La structured metadata (p. ej. trace_id) se comporta como etiquetas desde el principio del pipeline.

NO soportado (lanza ``LogQLSyntaxError``): consultas de métricas (``rate``, ``sum by``, ``quantile_over_time``...),
``line_format``, ``label_format``, ``pattern``, ``regexp``, ``unpack``, ``drop``, ``keep``, ``| unwrap``, duraciones/bytes como valores.
Las regex se anclan como en Prometheus/Loki (``=~`` hace *fullmatch*; los filtros de línea ``|~`` buscan en cualquier parte).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

__all__ = ["LogQLSyntaxError", "Entry", "query", "entries_from_payload", "parse_logfmt"]


class LogQLSyntaxError(ValueError):
    pass


@dataclass
class Entry:
    ts_ns: int
    line: str
    labels: dict[str, str]                       # etiquetas del stream
    metadata: dict[str, str] = field(default_factory=dict)
    parsed: dict[str, str] = field(default_factory=dict)

    def all_labels(self) -> dict[str, str]:
        return {**self.labels, **self.metadata, **self.parsed}


def entries_from_payload(payload: dict[str, Any]) -> list[Entry]:
    """Payload de ``LokiPusher.payload()`` (API de push JSON) -> entradas."""
    out = []
    for st in payload["streams"]:
        for v in st["values"]:
            out.append(Entry(int(v[0]), v[1], dict(st["stream"]), dict(v[2]) if len(v) > 2 else {}))
    return sorted(out, key=lambda e: e.ts_ns)


_LOGFMT = re.compile(r'([\w.\-]+)=(?:"((?:\\.|[^"\\])*)"|(\S*))')


def parse_logfmt(line: str) -> dict[str, str]:
    return {m.group(1): (m.group(2) if m.group(2) is not None else m.group(3)).replace('\\"', '"') for m in _LOGFMT.finditer(line)}


def _flatten(obj: Any, prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(_flatten(v, f"{prefix}_{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        out[prefix] = json.dumps(obj, ensure_ascii=False)
    elif obj is None:
        out[prefix] = ""
    elif isinstance(obj, bool):
        out[prefix] = "true" if obj else "false"
    else:
        out[prefix] = str(obj)
    return out


# ---------------------------------------------------------------------------------------------------------------------
_STR = r'(?:"(?:\\.|[^"\\])*"|`[^`]*`)'
_SEL = re.compile(r"\s*\{(.*?)\}\s*", re.S)
_MATCHER = re.compile(rf"\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*(=~|!~|!=|=)\s*({_STR})\s*,?")
_STAGE_LINE = re.compile(rf"\s*(\|=|\|~|!=|!~)\s*({_STR})")
_STAGE_PARSER = re.compile(r"\s*\|\s*(json|logfmt)\b")
_STAGE_LABEL = re.compile(rf"\s*\|\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*(=~|!~|!=|>=|<=|=|>|<)\s*({_STR}|-?\d+(?:\.\d+)?)((?:\s+(?:and|or)\s+[a-zA-Z_][a-zA-Z0-9_]*\s*(?:=~|!~|!=|>=|<=|=|>|<)\s*(?:{_STR}|-?\d+(?:\.\d+)?)|\s*,\s*[a-zA-Z_][a-zA-Z0-9_]*\s*(?:=~|!~|!=|>=|<=|=|>|<)\s*(?:{_STR}|-?\d+(?:\.\d+)?))*)")
_LABEL_ITEM = re.compile(rf"([a-zA-Z_][a-zA-Z0-9_]*)\s*(=~|!~|!=|>=|<=|=|>|<)\s*({_STR}|-?\d+(?:\.\d+)?)")


def _unq(s: str) -> str:
    if s[0] == "`":
        return s[1:-1]
    return bytes(s[1:-1], "utf-8").decode("unicode_escape") if "\\" in s else s[1:-1]


def _cmp(op: str, have: str | None, want: str, numeric: bool) -> bool:
    if have is None:
        have = ""
    if op == "=~":
        return re.fullmatch(want, have) is not None
    if op == "!~":
        return re.fullmatch(want, have) is None
    if numeric:
        try:
            a, b = float(have), float(want)
        except ValueError:
            return False
        return {"=": a == b, "!=": a != b, ">": a > b, ">=": a >= b, "<": a < b, "<=": a <= b}[op]
    return {"=": have == want, "!=": have != want}.get(op, False)


def compile_query(q: str):
    m = _SEL.match(q)
    if not m or not m.group(1).strip():
        raise LogQLSyntaxError(f"falta el selector de stream `{{...}}` al principio: {q!r}")
    matchers, pos, body = [], 0, m.group(1)
    while pos < len(body.rstrip()):
        mm = _MATCHER.match(body, pos)
        if not mm:
            raise LogQLSyntaxError(f"matcher no válido en el selector cerca de {body[pos:]!r}")
        matchers.append((mm.group(1), mm.group(2), _unq(mm.group(3))))
        pos = mm.end()
    rest, pos, stages = q[m.end():], 0, []
    while pos < len(rest):
        if not rest[pos:].strip():
            break
        for rx, kind in ((_STAGE_LINE, "line"), (_STAGE_PARSER, "parser"), (_STAGE_LABEL, "label")):
            sm = rx.match(rest, pos)
            if sm:
                if kind == "line":
                    stages.append(("line", sm.group(1), _unq(sm.group(2))))
                elif kind == "parser":
                    stages.append(("parser", sm.group(1)))
                else:
                    first = (sm.group(1), sm.group(2), sm.group(3))
                    tail = sm.group(4) or ""
                    items = [first] + [(i.group(1), i.group(2), i.group(3)) for i in _LABEL_ITEM.finditer(tail)]
                    joiners = re.findall(r"\b(and|or)\b|,", tail)
                    mode = "or" if "or" in joiners else "and"
                    stages.append(("label", mode, [(k, op, v) for k, op, v in items]))
                pos = sm.end()
                break
        else:
            raise LogQLSyntaxError(f"etapa de pipeline no soportada cerca de {rest[pos:pos + 40]!r} (el mini motor no hace métricas, line_format, pattern, drop...)")
    return matchers, stages


def query(entries: Iterable[Entry], logql: str, limit: int | None = None, direction: str = "backward") -> list[Entry]:
    """Evalúa una consulta de LOGS sobre ``entries``. Devuelve copias con ``parsed`` relleno (orden como Loki: más recientes primero)."""
    matchers, stages = compile_query(logql)
    out: list[Entry] = []
    for e in sorted(entries, key=lambda x: x.ts_ns, reverse=(direction == "backward")):
        lab = {**e.labels}
        if not all(_cmp(op, lab.get(k, ""), v, False) for k, op, v in matchers):
            continue
        cur = Entry(e.ts_ns, e.line, e.labels, e.metadata, {})
        keep = True
        for st in stages:
            if st[0] == "line":
                op, txt = st[1], st[2]
                hit = (txt in cur.line) if op in ("|=", "!=") else (re.search(txt, cur.line) is not None)
                if (op in ("|=", "|~")) != hit:
                    keep = False; break
            elif st[0] == "parser":
                try:
                    cur.parsed.update(_flatten(json.loads(cur.line)) if st[1] == "json" else parse_logfmt(cur.line))
                except json.JSONDecodeError:
                    cur.parsed["__error__"] = "JSONParserErr"
            else:
                mode, items = st[1], st[2]
                labs = cur.all_labels()
                res = [_cmp(op, labs.get(k), _unq(v) if v[0] in "\"`" else v, v[0] not in "\"`" and op not in ("=~", "!~")) for k, op, v in items]
                if not (any(res) if mode == "or" else all(res)):
                    keep = False; break
        if keep:
            out.append(cur)
            if limit and len(out) >= limit:
                break
    return out
