"""Mini motor de TraceQL en Python puro (módulo 07, autor A3): evalúa un SUBCONJUNTO de TraceQL sobre spans en memoria.

Para qué sirve:
- **Pedagogía**: implementar a mano la semántica de TraceQL (se evalúa **una traza cada vez**; ``{...}`` selecciona
  spans; ``&&`` *entre* spansets no es lo mismo que ``&&`` *dentro* de las llaves; los operadores estructurales devuelven
  el lado derecho) antes de usar Tempo.
- **Modo degradado**: el proyecto del módulo 07 se puede resolver y evaluar sin stack, sobre spans pregrabados.
- Se validó contra Tempo 3.1 real con una batería de consultas (ver ``07_tempo_traceql`` y ``tests/test_traceql_mini.py``).

Subconjunto soportado (el resto lanza ``TraceQLSyntaxError``)::

    spanset      :=  '{' [expr] '}'
    expr         :=  comparaciones con && || ! ( ) y aritmética + - * /  sobre campos y literales
    campos       :=  name | status | kind | duration | span:name|status|kind|duration|id|parentID|childCount
                     trace:duration|rootName|rootService|id | event:name | instrumentation:name
                     span.<attr> | resource.<attr> | event.<attr> | .<attr> (sin ámbito: span y luego resource)
    operadores   :=  =  !=  >  >=  <  <=  =~  !~  (las regex están ancladas, como en Tempo)
    literales    :=  enteros, decimales, "cadenas", duraciones (ns us ms s m h), true/false, nil, error|ok|unset, server|client|...
    combinar     :=  {A} && {B}   {A} || {B}                         (lógicos entre spansets)
                     {A} >> {B}  {A} > {B}  {A} << {B}  {A} < {B}  {A} ~ {B}   (estructurales: devuelven el lado derecho)
    pipeline     :=  spanset | count() cmp N | avg|max|min|sum(campo) cmp V | by(campo) | select(...) | coalesce()

NO soportado: operadores estructurales con ``&`` o ``!``, funciones de métricas (``rate()``...), ``with(...)``, ``topk``.
Diferencias conocidas con Tempo: no hay muestreo ni límite de resultados; los ``select`` se ignoran (solo afectan a la
presentación); los enteros/decimales se comparan como números de Python.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable

__all__ = ["TraceQLSyntaxError", "parse", "search", "TraceHit", "ticket_ids", "evaluate_trace"]


class TraceQLSyntaxError(ValueError):
    pass


# ---------------------------------------------------------------------------------------------------------------------
# Tokenizador
# ---------------------------------------------------------------------------------------------------------------------
_DUR = {"ns": 1, "us": 1_000, "µs": 1_000, "ms": 1_000_000, "s": 1_000_000_000, "m": 60_000_000_000, "h": 3_600_000_000_000}
_TOKEN = re.compile(r"""
    (?P<ws>\s+)
  | (?P<dur>\d+(?:\.\d+)?(?:ns|us|µs|ms|s|m|h)(?![A-Za-z0-9_]))
  | (?P<num>\d+(?:\.\d+)?)
  | (?P<str>"(?:\\.|[^"\\])*")
  | (?P<op>&>>|&<<|&>|&<|&~|!>>|!<<|!>|!<|!~|>>|<<|>=|<=|!=|=~|&&|\|\||[{}()|,=<>~!+\-*/])
  | (?P<id>[A-Za-z_.][A-Za-z0-9_.:]*)
""", re.X)


@dataclass
class Tok:
    kind: str
    text: str
    pos: int


def _tokenize(q: str) -> list[Tok]:
    out, pos = [], 0
    while pos < len(q):
        m = _TOKEN.match(q, pos)
        if not m:
            raise TraceQLSyntaxError(f"carácter inesperado {q[pos]!r} en la posición {pos}: {q!r}")
        pos = m.end()
        k = m.lastgroup
        if k != "ws":
            out.append(Tok(k, m.group(), m.start()))
    out.append(Tok("eof", "", len(q)))
    return out


# ---------------------------------------------------------------------------------------------------------------------
# Parser (descenso recursivo). AST con tuplas:
#   spansets : ("filter", expr|None) | ("and", a, b) | ("or", a, b) | ("struct", op, a, b)
#   expr     : ("lit", v) | ("field", name) | ("cmp", op, a, b) | ("and"/"or", a, b) | ("not", a) | ("arith", op, a, b)
#   stage    : ("count", cmp, v) | ("agg", fn, expr, cmp, v) | ("by", expr) | ("select", [..]) | ("coalesce",)
# ---------------------------------------------------------------------------------------------------------------------
STRUCT_OPS = {">>", ">", "<<", "<", "~"}
ENUMS = {"error", "ok", "unset", "server", "client", "internal", "producer", "consumer", "unspecified"}


class _Parser:
    def __init__(self, q: str):
        self.q, self.t, self.i = q, _tokenize(q), 0

    def peek(self) -> Tok:
        return self.t[self.i]

    def take(self, text: str | None = None) -> Tok:
        tk = self.t[self.i]
        if text is not None and tk.text != text:
            raise TraceQLSyntaxError(f"se esperaba {text!r} y llegó {tk.text or 'fin de la consulta'!r} (posición {tk.pos}): {self.q!r}")
        self.i += 1
        return tk

    def at(self, *texts: str) -> bool:
        return self.peek().text in texts and self.peek().kind in ("op", "id")

    # -- nivel pipeline ------------------------------------------------------------------------------------------
    def parse(self):
        node = self.spanset_expr()
        stages = []
        while self.at("|"):
            self.take()
            stages.append(self.stage())
        if self.peek().kind != "eof":
            raise TraceQLSyntaxError(f"texto sobrante {self.peek().text!r} (posición {self.peek().pos}): {self.q!r}")
        return node, stages

    def stage(self):
        tk = self.take()
        if tk.kind != "id":
            raise TraceQLSyntaxError(f"etapa de pipeline inesperada {tk.text!r}")
        name = tk.text
        self.take("(")
        if name == "count":
            self.take(")")
            op, v = self.cmp_tail()
            return ("count", op, v)
        if name in ("avg", "max", "min", "sum"):
            e = self.expr()
            self.take(")")
            op, v = self.cmp_tail()
            return ("agg", name, e, op, v)
        if name == "by":
            e = self.expr()
            self.take(")")
            return ("by", e)
        if name == "select":
            fields = [self.expr()]
            while self.at(","):
                self.take()
                fields.append(self.expr())
            self.take(")")
            return ("select", fields)
        if name == "coalesce":
            self.take(")")
            return ("coalesce",)
        raise TraceQLSyntaxError(f"función de pipeline no soportada: {name}()")

    def cmp_tail(self):
        op = self.take().text
        if op not in ("=", "!=", ">", ">=", "<", "<="):
            raise TraceQLSyntaxError(f"operador de comparación esperado tras la función, llegó {op!r}")
        return op, self.add()

    # -- spansets ------------------------------------------------------------------------------------------------
    def spanset_expr(self):
        left = self.struct()
        while self.at("&&", "||"):
            op = self.take().text
            right = self.struct()
            left = ("and" if op == "&&" else "or", left, right)
        return left

    def struct(self):
        left = self.atom()
        while self.peek().kind == "op" and self.peek().text in STRUCT_OPS:
            op = self.take().text
            left = ("struct", op, left, self.atom())
        if self.peek().kind == "op" and self.peek().text[:1] in "&!" and self.peek().text not in ("&&", "!=", "!~") and len(self.peek().text) > 1:
            raise TraceQLSyntaxError(f"operador estructural {self.peek().text!r} no soportado en el mini motor")
        return left

    def atom(self):
        if self.at("("):
            self.take()
            node = self.spanset_expr()
            self.take(")")
            return node
        self.take("{")
        if self.at("}"):
            self.take()
            return ("filter", None)
        e = self.expr()
        self.take("}")
        return ("filter", e)

    # -- expresiones dentro de {} --------------------------------------------------------------------------------
    def expr(self):
        left = self.and_()
        while self.at("||"):
            self.take()
            left = ("or", left, self.and_())
        return left

    def and_(self):
        left = self.cmp()
        while self.at("&&"):
            self.take()
            left = ("and", left, self.cmp())
        return left

    def cmp(self):
        if self.at("!"):
            self.take()
            return ("not", self.cmp())
        left = self.add()
        if self.peek().kind == "op" and self.peek().text in ("=", "!=", ">", ">=", "<", "<=", "=~", "!~"):
            op = self.take().text
            return ("cmp", op, left, self.add())
        return left

    def add(self):
        left = self.mul()
        while self.peek().kind == "op" and self.peek().text in ("+", "-"):
            op = self.take().text
            left = ("arith", op, left, self.mul())
        return left

    def mul(self):
        left = self.unary()
        while self.peek().kind == "op" and self.peek().text in ("*", "/"):
            op = self.take().text
            left = ("arith", op, left, self.unary())
        return left

    def unary(self):
        tk = self.take()
        if tk.kind == "op" and tk.text == "(":
            e = self.expr()
            self.take(")")
            return e
        if tk.kind == "op" and tk.text == "-":
            nxt = self.take()
            if nxt.kind in ("num", "dur"):
                return ("lit", -_lit(nxt))
            raise TraceQLSyntaxError("signo '-' solo antes de un número")
        if tk.kind in ("num", "dur"):
            return ("lit", _lit(tk))
        if tk.kind == "str":
            return ("lit", bytes(tk.text[1:-1], "utf-8").decode("unicode_escape") if "\\" in tk.text else tk.text[1:-1])
        if tk.kind == "id":
            if tk.text in ("true", "false"):
                return ("lit", tk.text == "true")
            if tk.text == "nil":
                return ("lit", None)
            if tk.text in ENUMS:
                return ("enum", tk.text)
            return ("field", tk.text)
        raise TraceQLSyntaxError(f"token inesperado {tk.text!r} (posición {tk.pos}): {self.q!r}")


def _lit(tk: Tok):
    if tk.kind == "dur":
        m = re.fullmatch(r"(\d+(?:\.\d+)?)(ns|us|µs|ms|s|m|h)", tk.text)
        return int(float(m.group(1)) * _DUR[m.group(2)])
    return float(tk.text) if "." in tk.text else int(tk.text)


def parse(query: str):
    """Devuelve ``(spanset_ast, [etapas])`` o lanza ``TraceQLSyntaxError``."""
    return _Parser(query).parse()


# ---------------------------------------------------------------------------------------------------------------------
# Contexto de traza y evaluación
# ---------------------------------------------------------------------------------------------------------------------
@dataclass
class _Trace:
    spans: list[dict]
    by_id: dict = field(default_factory=dict)
    children: dict = field(default_factory=dict)
    root: dict | None = None
    t0: int = 0
    t1: int = 0

    def __post_init__(self) -> None:
        self.by_id = {s["span_id"]: s for s in self.spans}
        for s in self.spans:
            self.children.setdefault(s.get("parent_span_id"), []).append(s)
        roots = [s for s in self.spans if not s.get("parent_span_id") or s["parent_span_id"] not in self.by_id]
        self.root = min(roots, key=lambda s: s["start_unix_nano"]) if roots else None
        self.t0 = min(s["start_unix_nano"] for s in self.spans)
        self.t1 = max(s["end_unix_nano"] for s in self.spans)


_MISSING = object()


def _field(span: dict, name: str, tr: _Trace):
    """Valor de un campo para un span (lista si es multivaluado, como los eventos); ``_MISSING`` si no existe."""
    if name in ("name", "span:name"):
        return span["name"]
    if name in ("status", "span:status"):
        return span["status"].lower()
    if name in ("kind", "span:kind"):
        return span["kind"].lower()
    if name in ("duration", "span:duration"):
        return span["end_unix_nano"] - span["start_unix_nano"]
    if name == "span:id":
        return span["span_id"]
    if name == "span:parentID":
        return span.get("parent_span_id") or ""
    if name == "span:childCount":
        return len(tr.children.get(span["span_id"], []))
    if name == "span:statusMessage":
        return span.get("status_message") or ""
    if name == "trace:duration":
        return tr.t1 - tr.t0
    if name == "trace:rootName":
        return tr.root["name"] if tr.root else _MISSING
    if name == "trace:rootService":
        return tr.root["resource"].get("service.name", _MISSING) if tr.root else _MISSING
    if name == "trace:id":
        return span["trace_id"]
    if name == "instrumentation:name":
        return span.get("scope") or _MISSING
    if name == "event:name":
        return [e["name"] for e in span.get("events", [])] or _MISSING
    if name.startswith("event."):
        vals = [e["attributes"][name[6:]] for e in span.get("events", []) if name[6:] in e.get("attributes", {})]
        return vals or _MISSING
    if name.startswith("span."):
        return span["attributes"].get(name[5:], _MISSING)
    if name.startswith("resource."):
        return span["resource"].get(name[9:], _MISSING)
    if name.startswith("."):
        a = span["attributes"].get(name[1:], _MISSING)
        return a if a is not _MISSING else span["resource"].get(name[1:], _MISSING)
    raise TraceQLSyntaxError(f"campo desconocido o sin ámbito: {name!r} (usa span.<attr>, resource.<attr>, name, status, duration...)")


def _eval(e, span: dict, tr: _Trace):
    k = e[0]
    if k == "lit":
        return e[1]
    if k == "enum":
        return e[1]
    if k == "field":
        return _field(span, e[1], tr)
    if k == "arith":
        a, b = _eval(e[2], span, tr), _eval(e[3], span, tr)
        if a is _MISSING or b is _MISSING:
            return _MISSING
        return {"+": a + b, "-": a - b, "*": a * b, "/": (a / b if b else _MISSING)}[e[1]]
    if k == "not":
        return not _truthy(_eval(e[1], span, tr))
    if k == "and":
        return _truthy(_eval(e[1], span, tr)) and _truthy(_eval(e[2], span, tr))
    if k == "or":
        return _truthy(_eval(e[1], span, tr)) or _truthy(_eval(e[2], span, tr))
    if k == "cmp":
        return _compare(e[1], _eval(e[2], span, tr), _eval(e[3], span, tr))
    raise TraceQLSyntaxError(f"expresión no evaluable: {e}")


def _truthy(v) -> bool:
    return v is True or (v is not _MISSING and v is not None and v is not False and bool(v))


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _compare(op: str, a, b) -> bool:
    if b is None:                                              # comparación con nil
        present = a is not _MISSING and a is not None
        return (not present) if op == "=" else present if op == "!=" else False
    if a is _MISSING or b is _MISSING or a is None:
        return False                                           # un atributo ausente no cumple ninguna comparación (salvo con nil)
    vals = a if isinstance(a, list) else [a]                   # arrays: = y =~ "alguno"; != y !~ "ninguno"
    if op in ("=", "=~"):
        return any(_one(op, v, b) for v in vals)
    if op in ("!=", "!~"):
        return not any(_one("=" if op == "!=" else "=~", v, b) for v in vals)
    return any(_one(op, v, b) for v in vals)


def _one(op: str, a, b) -> bool:
    if op == "=~":
        return re.fullmatch(str(b), str(a)) is not None        # anclada en ambos extremos, como Tempo
    if _num(a) and _num(b):
        pass
    elif isinstance(a, str) and isinstance(b, str):
        pass
    elif isinstance(a, bool) and isinstance(b, bool):
        pass
    else:
        a, b = str(a), str(b)
    return {"=": a == b, "!=": a != b, ">": a > b, ">=": a >= b, "<": a < b, "<=": a <= b}[op]


# -- spansets -----------------------------------------------------------------------------------------------------
Spanset = list  # lista de spans (dicts)


def _eval_spanset(node, inp: list[Spanset], tr: _Trace) -> list[Spanset]:
    k = node[0]
    if k == "filter":
        out = []
        for ss in inp:
            kept = [s for s in ss if node[1] is None or _truthy(_eval(node[1], s, tr))]
            if kept:
                out.append(kept)
        return out
    if k in ("and", "or"):
        a, b = _eval_spanset(node[1], inp, tr), _eval_spanset(node[2], inp, tr)
        if (k == "and" and a and b) or (k == "or" and (a or b)):
            seen, merged = set(), []
            for s in [x for ss in a + b for x in ss]:
                if s["span_id"] not in seen:
                    seen.add(s["span_id"]); merged.append(s)
            return [merged]
        return []
    if k == "struct":
        op, left, right = node[1], _eval_spanset(node[2], inp, tr), _eval_spanset(node[3], inp, tr)
        lsp = {s["span_id"]: s for ss in left for s in ss}
        out = []
        for rs in right:
            kept = [s for s in rs if _related(op, s, lsp, tr)]
            if kept:
                out.append(kept)
        return out
    raise TraceQLSyntaxError(f"nodo de spanset desconocido: {k}")


def _ancestors(s: dict, tr: _Trace):
    seen = set()
    p = s.get("parent_span_id")
    while p and p in tr.by_id and p not in seen:
        seen.add(p); yield tr.by_id[p]; p = tr.by_id[p].get("parent_span_id")


def _related(op: str, s: dict, left: dict[str, dict], tr: _Trace) -> bool:
    """¿El span ``s`` (lado derecho) tiene la relación ``op`` con algún span del lado izquierdo?"""
    if op == ">":       # s es hijo directo de un span izquierdo
        return s.get("parent_span_id") in left
    if op == ">>":      # s es descendiente de un span izquierdo
        return any(a["span_id"] in left for a in _ancestors(s, tr))
    if op == "<":       # s es padre directo de un span izquierdo
        return any(c["span_id"] in left for c in tr.children.get(s["span_id"], []))
    if op == "<<":      # s es ancestro de un span izquierdo
        return any(any(a["span_id"] == s["span_id"] for a in _ancestors(l, tr)) for l in left.values())
    if op == "~":       # s tiene un hermano izquierdo (otro span con el mismo padre)
        return any(l["span_id"] != s["span_id"] and l.get("parent_span_id") == s.get("parent_span_id") for l in left.values())
    raise TraceQLSyntaxError(f"operador estructural no soportado: {op}")


def _scalar(stage, ss: Spanset, tr: _Trace):
    if stage[0] == "count":
        return len(ss)
    vals = [v for v in (_eval(stage[2], s, tr) for s in ss) if _num(v)]
    if not vals:
        return None
    return {"avg": sum(vals) / len(vals), "max": max(vals), "min": min(vals), "sum": sum(vals)}[stage[1]]


def _run_stages(stages, sets: list[Spanset], tr: _Trace) -> list[Spanset]:
    for st in stages:
        if st[0] in ("count", "agg"):
            op, rhs = (st[1], st[2]) if st[0] == "count" else (st[3], st[4])
            keep = []
            for ss in sets:
                v = _scalar(st, ss, tr)
                if v is not None and _compare(op, v, _eval(rhs, ss[0], tr)):
                    keep.append(ss)
            sets = keep
        elif st[0] == "by":
            groups: dict[Any, Spanset] = {}
            for ss in sets:
                for s in ss:
                    v = _field_value(st[1], s, tr)
                    groups.setdefault(repr(v), []).append(s)
            sets = list(groups.values())
        elif st[0] == "coalesce":
            sets = [[s for ss in sets for s in ss]] if sets else []
        elif st[0] == "select":
            pass
    return sets


def _field_value(e, s, tr):
    v = _eval(e, s, tr)
    return None if v is _MISSING else v


def evaluate_trace(ast, spans: list[dict]) -> list[Spanset]:
    """Evalúa una consulta ya parseada sobre UNA traza (lista de spans). Devuelve los spansets resultantes."""
    node, stages = ast
    tr = _Trace(spans)
    sets = _eval_spanset(node, [list(spans)], tr)
    return _run_stages(stages, sets, tr)


# ---------------------------------------------------------------------------------------------------------------------
@dataclass
class TraceHit:
    trace_id: str
    spansets: list[list[dict]]
    root_name: str
    root_service: str
    start_ns: int
    duration_ms: float

    @property
    def matched_spans(self) -> int:
        return sum(len(s) for s in self.spansets)


def search(spans: Iterable[dict], query: str, limit: int | None = None) -> list[TraceHit]:
    """Equivalente a ``GET /api/search?q=...`` sobre spans en memoria. Ordena por inicio descendente (más reciente primero)."""
    ast = parse(query)
    by_trace: dict[str, list[dict]] = {}
    for s in spans:
        by_trace.setdefault(s["trace_id"], []).append(s)
    hits = []
    for tid, ss in by_trace.items():
        sets = evaluate_trace(ast, ss)
        if sets:
            tr = _Trace(ss)
            hits.append(TraceHit(tid, sets, tr.root["name"] if tr.root else "", tr.root["resource"].get("service.name", "") if tr.root else "",
                                 tr.t0, (tr.t1 - tr.t0) / 1e6))
    hits.sort(key=lambda h: -h.start_ns)
    return hits[:limit] if limit else hits


def ticket_ids(spans: Iterable[dict], hits: Iterable[TraceHit]) -> list[str]:
    """Tickets (``supportops.ticket.id`` del span raíz de cada traza) de los resultados: sirve para comparar mini motor y Tempo."""
    roots: dict[str, str] = {}
    for s in spans:
        if not s.get("parent_span_id") and "supportops.ticket.id" in s["attributes"]:
            roots[s["trace_id"]] = s["attributes"]["supportops.ticket.id"]
    return sorted(roots[h.trace_id] for h in hits if h.trace_id in roots)
