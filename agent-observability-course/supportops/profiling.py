"""Módulo 17 · profiling continuo: muestreador de pila a mano, codificador pprof, cliente de Pyroscope y rutas calientes de SupportOps.

Piezas (solo librería estándar; numpy opcional para la variante rápida):

* ``SamplingProfiler``: perfilador por muestreo en Python puro (``sys._current_frames`` + un hilo) con modo ``wall`` o ``cpu`` y
  etiquetas por hilo (``set_tag``). Es la versión «a mano» de lo que hacen py-spy / ``pyroscope-io``.
* ``Folded``/``folded_text``/``flame_rows``: pilas plegadas («folded stacks») y la geometría de un flamegraph.
* ``encode_pprof``/``decode_pprof``: formato pprof (protobuf) codificado a mano, el idioma común de los perfiladores.
* ``PyroscopeClient``: cliente HTTP mínimo de Pyroscope 2.x (empuje por ``/ingest`` y Connect-RPC, consultas de flamegraph y etiquetas).
* ``HotPathInstrumentor``: tres rutas calientes realistas de un agente (serialización del contexto, escaneo/parseo de PII y
  *embeddings*) en versión ``slow`` y ``fast`` (la corrección), con cronómetros por etapa como verdad de referencia.
* ``run_workload``: ejecuta SupportOps con la ruta caliente y mide CPU real (``time.process_time``).
* ``profiling_dashboard``: dashboard ``17-profiling.json`` (Grafana, datasource Pyroscope).

Nota de honestidad: las latencias del LLM de SupportOps son *simuladas* (no consumen CPU), por lo que las rutas calientes de
este módulo son el trabajo REAL de «fontanería» que rodea al modelo en un agente de producción.
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import json
import math
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Iterator, Mapping, Sequence

from .instrument import Instrumentor

Stack = tuple[str, ...]            # raíz -> hoja

# =====================================================================================================================
# 1. Perfilador por muestreo a mano
# =====================================================================================================================
_THIS_FILE = __file__


def _frame_label(frame) -> str:
    code = frame.f_code
    mod = frame.f_globals.get("__name__", "?")
    qual = getattr(code, "co_qualname", code.co_name)
    return f"{mod}.{qual}"


class SamplingProfiler:
    """Perfilador estadístico: cada ``1/hz`` s mira la pila de los hilos objetivo y cuenta cada pila vista.

    ``mode='wall'`` cuenta SIEMPRE (incluye esperas: I/O, ``sleep``, locks); ``mode='cpu'`` solo cuenta si el hilo consumió CPU desde la
    muestra anterior (reloj de CPU del hilo, ``time.pthread_getcpuclockid``; en Linux/macOS). Las etiquetas (``set_tag``) viajan con
    cada muestra: es el mecanismo con el que Pyroscope filtra por ``span_id`` o ``tenant``.

    >>> p = SamplingProfiler(hz=500); p.start(); sum(i * i for i in range(300_000)); p.stop(); p.total > 0
    True
    """

    def __init__(self, hz: float = 200.0, mode: str = "wall", thread_ids: Iterable[int] | None = None, max_depth: int = 64,
                 include_self: bool = False):
        if mode not in ("wall", "cpu"):
            raise ValueError("mode debe ser 'wall' o 'cpu'")
        if mode == "cpu" and not hasattr(time, "pthread_getcpuclockid"):
            raise RuntimeError("el modo cpu necesita time.pthread_getcpuclockid (Linux/macOS)")
        self.hz, self.mode, self.max_depth, self.include_self = float(hz), mode, max_depth, include_self
        self.thread_ids = set(thread_ids) if thread_ids else None       # None = el hilo que llama a start()
        self.samples: Counter[tuple[tuple[tuple[str, str], ...], Stack]] = Counter()
        self.tags: dict[int, dict[str, str]] = defaultdict(dict)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._t0 = self._t1 = 0.0
        self._last_cpu: dict[int, float] = {}
        self.n_ticks = 0
        self.overrun_ticks = 0
        self.sampler_cpu_s = 0.0

    # ----- etiquetas
    def set_tag(self, key: str, value: str, thread_id: int | None = None) -> None:
        self.tags[thread_id or threading.get_ident()][key] = str(value)

    def clear_tag(self, key: str, thread_id: int | None = None) -> None:
        self.tags[thread_id or threading.get_ident()].pop(key, None)

    @contextmanager
    def tag(self, **tags: str) -> Iterator[None]:
        for k, v in tags.items():
            self.set_tag(k, v)
        try:
            yield
        finally:
            for k in tags:
                self.clear_tag(k)

    # ----- ciclo de vida
    def start(self) -> "SamplingProfiler":
        if self._thread is not None:
            raise RuntimeError("ya iniciado")
        if self.thread_ids is None:
            self.thread_ids = {threading.get_ident()}
        self._stop.clear()
        self._t0 = time.perf_counter()
        self._thread = threading.Thread(target=self._run, name="sampling-profiler", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> "SamplingProfiler":
        if self._thread is not None:
            self._stop.set()
            self._thread.join(timeout=2.0)
            self._thread = None
            self._t1 = time.perf_counter()
        return self

    def __enter__(self) -> "SamplingProfiler":
        return self.start()

    def __exit__(self, *exc: object) -> None:
        self.stop()

    @property
    def duration_s(self) -> float:
        return (self._t1 or time.perf_counter()) - self._t0

    # ----- bucle de muestreo
    def _cpu_now(self, tid: int) -> float | None:
        try:
            return time.clock_gettime(time.pthread_getcpuclockid(tid))
        except Exception:
            return None

    def _run(self) -> None:
        period = 1.0 / self.hz
        me = threading.get_ident()
        c0 = time.thread_time()
        nxt = time.perf_counter()
        while not self._stop.is_set():
            nxt += period
            self.n_ticks += 1
            frames = sys._current_frames()
            for tid in list(self.thread_ids or ()):
                fr = frames.get(tid)
                if fr is None or tid == me:
                    continue
                if self.mode == "cpu":
                    now = self._cpu_now(tid)
                    last = self._last_cpu.get(tid)
                    self._last_cpu[tid] = now if now is not None else 0.0
                    if now is None or last is None or (now - last) < 0.25 * period:
                        continue
                stack: list[str] = []
                f = fr
                while f is not None and len(stack) < self.max_depth:
                    if self.include_self or f.f_code.co_filename != _THIS_FILE or f.f_code.co_name not in ("_run",):
                        stack.append(_frame_label(f))
                    f = f.f_back
                stack.reverse()
                self.samples[(tuple(sorted(self.tags.get(tid, {}).items())), tuple(stack))] += 1
            delay = nxt - time.perf_counter()
            if delay > 0:
                self._stop.wait(delay)
            else:
                self.overrun_ticks += 1
                nxt = time.perf_counter()
        self.sampler_cpu_s += time.thread_time() - c0

    # ----- resultados
    @property
    def total(self) -> int:
        return sum(self.samples.values())

    def stacks(self, **where: str) -> Counter[Stack]:
        """Pilas -> nº de muestras, opcionalmente filtradas por etiqueta (``stacks(span_id='ab12')``)."""
        out: Counter[Stack] = Counter()
        for (tags, stack), n in self.samples.items():
            d = dict(tags)
            if all(d.get(k) == v for k, v in where.items()):
                out[stack] += n
        return out

    def tag_values(self, key: str) -> Counter[str]:
        c: Counter[str] = Counter()
        for (tags, _), n in self.samples.items():
            v = dict(tags).get(key)
            if v is not None:
                c[v] += n
        return c

    def sample_period_ns(self) -> int:
        return int(1e9 / self.hz)

    def to_pprof(self, **where: str) -> bytes:
        rows = [(stack, n * self.sample_period_ns(), dict(tags)) for (tags, stack), n in self.samples.items()
                if all(dict(tags).get(k) == v for k, v in where.items())]
        return encode_pprof(rows, sample_type=("cpu" if self.mode == "cpu" else "wall", "nanoseconds"), period_ns=self.sample_period_ns(),
                            duration_ns=int(self.duration_s * 1e9), time_nanos=int((time.time() - self.duration_s) * 1e9))


# =====================================================================================================================
# 2. Pilas plegadas y geometría de flamegraph
# =====================================================================================================================
def folded_text(stacks: Mapping[Stack, int]) -> str:
    """Formato «folded» de Brendan Gregg: ``a;b;c 12`` por línea (la raíz a la izquierda)."""
    return "\n".join(f"{';'.join(s)} {n}" for s, n in sorted(stacks.items()))


def parse_folded(text: str) -> Counter[Stack]:
    out: Counter[Stack] = Counter()
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        stack, _, n = line.rpartition(" ")
        out[tuple(stack.split(";"))] += int(n)
    return out


def self_time(stacks: Mapping[Stack, int]) -> Counter[str]:
    """Muestras donde la función es la HOJA (tiempo propio, *self*)."""
    c: Counter[str] = Counter()
    for s, n in stacks.items():
        if s:
            c[s[-1]] += n
    return c


def total_time(stacks: Mapping[Stack, int]) -> Counter[str]:
    """Muestras en las que la función aparece en la pila (tiempo inclusivo, *total*); cuenta una vez por muestra aunque haya recursión."""
    c: Counter[str] = Counter()
    for s, n in stacks.items():
        for fn in set(s):
            c[fn] += n
    return c


@dataclass
class FlameRect:
    depth: int
    x: float          # inicio (en muestras)
    width: float      # muestras (tiempo total del nodo)
    name: str
    self_n: float


def flame_rows(stacks: Mapping[Stack, int]) -> list[FlameRect]:
    """Convierte pilas en rectángulos de flamegraph: ancho = muestras del nodo, hijos ordenados por nombre (convención de los flamegraphs)."""
    tree: dict[str, Any] = {"n": 0, "self": 0, "kids": {}}
    for stack, n in stacks.items():
        node = tree
        node["n"] += n
        for fn in stack:
            node = node["kids"].setdefault(fn, {"n": 0, "self": 0, "kids": {}})
            node["n"] += n
        node["self"] += n
    out: list[FlameRect] = []

    def walk(node: dict[str, Any], name: str, depth: int, x: float) -> None:
        if depth >= 0:
            out.append(FlameRect(depth, x, node["n"], name, node["self"]))
        cx = x
        for k in sorted(node["kids"]):
            walk(node["kids"][k], k, depth + 1, cx)
            cx += node["kids"][k]["n"]

    walk(tree, "all", -1, 0.0)
    return out


def flamebearer_to_stacks(fb: Mapping[str, Any]) -> Counter[Stack]:
    """Reconstruye pilas desde el formato *flamebearer* (``names`` + ``levels`` con deltas) que devuelve Pyroscope."""
    names, levels = fb["names"], fb["levels"]
    # nodos: por nivel, secuencia de (x_offset_delta, total, self, name_idx)
    abs_levels: list[list[tuple[int, int, int, int]]] = []
    for lv in levels:
        x, row = 0, []
        for i in range(0, len(lv), 4):
            x += lv[i]
            row.append((x, lv[i + 1], lv[i + 2], lv[i + 3]))
            x += lv[i + 1]
        abs_levels.append(row)
    out: Counter[Stack] = Counter()

    def walk(depth: int, x0: int, x1: int, path: tuple[str, ...]) -> None:
        if depth >= len(abs_levels):
            return
        for (x, tot, slf, ni) in abs_levels[depth]:
            if x >= x0 and x + tot <= x1:
                p = path + (names[ni],)
                if slf:
                    out[p] += slf
                walk(depth + 1, x, x + tot, p)

    root = abs_levels[0][0] if abs_levels and abs_levels[0] else None
    if root is None:
        return out
    # nivel 0 = «total»; empezamos en el nivel 1 con el rango del nodo raíz
    x, tot, slf, ni = root
    if slf:
        out[(names[ni],)] += slf
    walk(1, x, x + tot, ())
    return out


# =====================================================================================================================
# 3. pprof (protobuf) a mano
# =====================================================================================================================
def _varint(n: int) -> bytes:
    if n < 0:
        n += 1 << 64
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _tag(num: int, wire: int) -> bytes:
    return _varint((num << 3) | wire)


def _f_varint(num: int, v: int) -> bytes:
    return _tag(num, 0) + _varint(v)


def _f_bytes(num: int, b: bytes) -> bytes:
    return _tag(num, 2) + _varint(len(b)) + b


def _packed(num: int, values: Iterable[int]) -> bytes:
    return _f_bytes(num, b"".join(_varint(v) for v in values))


def encode_pprof(rows: Iterable[tuple[Sequence[str], int, Mapping[str, str]]], *, sample_type: tuple[str, str] = ("cpu", "nanoseconds"),
                 period_ns: int = 10_000_000, duration_ns: int = 0, time_nanos: int | None = None, gzip_it: bool = True) -> bytes:
    """Codifica ``(pila raíz->hoja, valor, etiquetas)`` como ``perftools.profiles.Profile`` (pprof). ``gzip_it`` lo comprime (así lo envían los SDK).

    Campos (profile.proto): sample_type=1, sample=2, mapping=3, location=4, function=5, string_table=6, time_nanos=9, duration_nanos=10,
    period_type=11, period=12. En ``Sample`` los ``location_id`` van de la HOJA a la raíz.
    """
    strings: list[str] = [""]
    sidx: dict[str, int] = {"": 0}

    def s(x: str) -> int:
        if x not in sidx:
            sidx[x] = len(strings)
            strings.append(x)
        return sidx[x]

    func_ids: dict[str, int] = {}
    loc_ids: dict[str, int] = {}
    functions: list[bytes] = []
    locations: list[bytes] = []
    samples: list[bytes] = []

    def loc(name: str) -> int:
        if name not in loc_ids:
            fid = len(func_ids) + 1
            func_ids[name] = fid
            functions.append(_f_varint(1, fid) + _f_varint(2, s(name)) + _f_varint(3, s(name)))
            lid = len(loc_ids) + 1
            loc_ids[name] = lid
            locations.append(_f_varint(1, lid) + _f_bytes(4, _f_varint(1, fid) + _f_varint(2, 0)))
        return loc_ids[name]

    st_type, st_unit = s(sample_type[0]), s(sample_type[1])
    for stack, value, labels in rows:
        body = _packed(1, [loc(fn) for fn in reversed(list(stack))]) + _packed(2, [int(value)])
        for k, v in labels.items():
            body += _f_bytes(3, _f_varint(1, s(str(k))) + _f_varint(2, s(str(v))))
        samples.append(body)
    out = _f_bytes(1, _f_varint(1, st_type) + _f_varint(2, st_unit))
    out += b"".join(_f_bytes(2, x) for x in samples)
    out += b"".join(_f_bytes(4, x) for x in locations)
    out += b"".join(_f_bytes(5, x) for x in functions)
    out += b"".join(_f_bytes(6, x.encode()) for x in strings)
    out += _f_varint(9, int(time_nanos if time_nanos is not None else time.time() * 1e9))
    out += _f_varint(10, int(duration_ns))
    out += _f_bytes(11, _f_varint(1, st_type) + _f_varint(2, st_unit))
    out += _f_varint(12, int(period_ns))
    return gzip.compress(out, 6, mtime=0) if gzip_it else out


def _read_varint(b: bytes, i: int) -> tuple[int, int]:
    shift = n = 0
    while True:
        c = b[i]
        i += 1
        n |= (c & 0x7F) << shift
        if not c & 0x80:
            return n, i
        shift += 7


def _fields(b: bytes) -> Iterator[tuple[int, int, Any]]:
    i = 0
    while i < len(b):
        key, i = _read_varint(b, i)
        num, wire = key >> 3, key & 7
        if wire == 0:
            v, i = _read_varint(b, i)
        elif wire == 2:
            ln, i = _read_varint(b, i)
            v, i = b[i:i + ln], i + ln
        elif wire == 1:
            v, i = b[i:i + 8], i + 8
        elif wire == 5:
            v, i = b[i:i + 4], i + 4
        else:
            raise ValueError(f"wire type {wire} no soportado")
        yield num, wire, v


def _unpack(b: bytes) -> list[int]:
    out, i = [], 0
    while i < len(b):
        v, i = _read_varint(b, i)
        out.append(v)
    return out


def decode_pprof(data: bytes) -> dict[str, Any]:
    """Decodifica un pprof (con o sin gzip) a ``{'sample_type', 'period', 'duration_ns', 'samples': [(pila raíz->hoja, [valores], etiquetas)]}``."""
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    strings: list[str] = []
    funcs: dict[int, int] = {}
    locs: dict[int, list[int]] = {}
    raw_samples: list[tuple[list[int], list[int], dict[int, int]]] = []
    sample_types: list[tuple[int, int]] = []
    period = duration = 0
    for num, wire, v in _fields(data):
        if num == 6:
            strings.append(v.decode())
        elif num == 1:
            d = {n: x for n, _, x in _fields(v)}
            sample_types.append((d.get(1, 0), d.get(2, 0)))
        elif num == 5:
            d = {n: x for n, _, x in _fields(v)}
            funcs[d[1]] = d.get(2, 0)
        elif num == 4:
            lid, fids = 0, []
            for n, _, x in _fields(v):
                if n == 1:
                    lid = x
                elif n == 4:
                    fids += [y for m, _, y in _fields(x) if m == 1]
            locs[lid] = fids
        elif num == 2:
            ids: list[int] = []
            vals: list[int] = []
            labs: dict[int, int] = {}
            for n, w, x in _fields(v):
                if n == 1:
                    ids += _unpack(x) if w == 2 else [x]
                elif n == 2:
                    vals += _unpack(x) if w == 2 else [x]
                elif n == 3:
                    d = {m: y for m, _, y in _fields(x)}
                    labs[d.get(1, 0)] = d.get(2, 0)
            raw_samples.append((ids, vals, labs))
        elif num == 12:
            period = v
        elif num == 10:
            duration = v
    samples = []
    for ids, vals, labs in raw_samples:
        stack = tuple(strings[funcs[f]] for lid in reversed(ids) for f in locs[lid])
        samples.append((stack, vals, {strings[k]: strings[x] for k, x in labs.items()}))
    return {"sample_type": [(strings[a], strings[b]) for a, b in sample_types], "period": period, "duration_ns": duration, "samples": samples}


# =====================================================================================================================
# 4. Cliente HTTP de Pyroscope 2.x
# =====================================================================================================================
PYROSCOPE_URL = os.environ.get("PYROSCOPE_URL", "http://localhost:4040")
CPU_PROFILE_TYPE = "process_cpu:cpu:nanoseconds:cpu:nanoseconds"


class PyroscopeError(RuntimeError):
    pass


class PyroscopeClient:
    """Cliente mínimo (urllib) de la API de Pyroscope. Pyroscope 2.x expone: ingesta compatible ``POST /ingest`` y Connect-RPC
    (``/push.v1.PusherService/Push``, ``/querier.v1.QuerierService/*``) con cuerpos JSON."""

    def __init__(self, base: str = PYROSCOPE_URL, tenant: str | None = None, timeout: float = 10.0):
        self.base, self.tenant, self.timeout = base.rstrip("/"), tenant, timeout

    def _req(self, path: str, body: bytes | None = None, headers: Mapping[str, str] | None = None, method: str | None = None) -> bytes:
        h = dict(headers or {})
        if self.tenant:
            h["X-Scope-OrgID"] = self.tenant
        req = urllib.request.Request(self.base + path, data=body, headers=h, method=method or ("POST" if body is not None else "GET"))
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            raise PyroscopeError(f"{e.code} {path}: {e.read()[:300].decode(errors='replace')}") from e
        except urllib.error.URLError as e:
            raise PyroscopeError(f"sin conexión con {self.base}: {e.reason}") from e

    def _rpc(self, service_method: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        raw = self._req("/" + service_method, json.dumps(payload).encode(), {"Content-Type": "application/json"})
        return json.loads(raw or b"{}")

    # ----- estado
    def ready(self) -> bool:
        try:
            return self._req("/ready").strip().lower().startswith(b"ready")
        except PyroscopeError:
            return False

    # ----- escritura
    def push_connect(self, labels: Mapping[str, str], pprof_gz: bytes, profile_type: str = "process_cpu") -> None:
        """Empuje Connect-RPC (``push.v1.PusherService/Push``): ``rawProfile`` es el pprof en base64. ``__name__`` = tipo de perfil."""
        series = {"series": [{"labels": [{"name": "__name__", "value": profile_type}, *({"name": k, "value": v} for k, v in labels.items())],
                              "samples": [{"ID": str(uuid.uuid4()), "rawProfile": base64.b64encode(pprof_gz).decode()}]}]}
        self._rpc("push.v1.PusherService/Push", series)

    def push_ingest(self, app: str, labels: Mapping[str, str], pprof: bytes, from_s: float, until_s: float, sample_rate: int = 100) -> None:
        """Ingesta compatible con los SDK (``/ingest``): pprof en un formulario *multipart* (campo ``profile``)."""
        name = app + ("{" + ",".join(f"{k}={v}" for k, v in labels.items()) + "}" if labels else "")
        q = urllib.parse.urlencode({"name": name, "from": int(from_s), "until": int(until_s), "format": "pprof", "sampleRate": sample_rate,
                                    "spyName": "supportops"})
        boundary = uuid.uuid4().hex
        body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"profile\"; filename=\"profile.pprof\"\r\n"
                f"Content-Type: application/octet-stream\r\n\r\n").encode() + pprof + f"\r\n--{boundary}--\r\n".encode()
        self._req("/ingest?" + q, body, {"Content-Type": f"multipart/form-data; boundary={boundary}"})

    # ----- lectura
    def profile_types(self, minutes: int = 60) -> list[str]:
        now = int(time.time() * 1000)
        r = self._rpc("querier.v1.QuerierService/ProfileTypes", {"start": now - minutes * 60_000, "end": now})
        return [p["ID"] for p in r.get("profileTypes", [])]

    def label_names(self, selector: str = "{}", profile_type: str = CPU_PROFILE_TYPE, minutes: int = 60) -> list[str]:
        now = int(time.time() * 1000)
        r = self._rpc("querier.v1.QuerierService/LabelNames", {"matchers": [self._matcher(selector, profile_type)], "start": now - minutes * 60_000, "end": now})
        return r.get("names", [])

    def label_values(self, name: str, selector: str = "{}", profile_type: str = CPU_PROFILE_TYPE, minutes: int = 60) -> list[str]:
        now = int(time.time() * 1000)
        r = self._rpc("querier.v1.QuerierService/LabelValues", {"name": name, "matchers": [self._matcher(selector, profile_type)],
                                                                "start": now - minutes * 60_000, "end": now})
        return r.get("names", [])

    @staticmethod
    def _matcher(selector: str, profile_type: str) -> str:
        sel = selector.strip()
        name = profile_type.split(":")[0]
        inner = sel[1:-1].strip() if sel.startswith("{") else sel
        return "{" + f'__name__="{name}"' + (", " + inner if inner else "") + "}"

    def flamegraph(self, selector: str = "{}", profile_type: str = CPU_PROFILE_TYPE, minutes: int = 15, *, start_ms: int | None = None,
                   end_ms: int | None = None, max_nodes: int = 16384) -> dict[str, Any]:
        """``SelectMergeStacktraces``: perfil agregado como flamebearer (``names``, ``levels``, ``total``, ``maxSelf``)."""
        end = end_ms or int(time.time() * 1000)
        start = start_ms or end - minutes * 60_000
        r = self._rpc("querier.v1.QuerierService/SelectMergeStacktraces", {
            "profileTypeID": profile_type, "labelSelector": selector, "start": start, "end": end, "maxNodes": max_nodes})
        fg = r.get("flamegraph") or {}
        fg.setdefault("names", [])
        fg.setdefault("levels", [])
        fg["levels"] = [[int(x) for x in lv.get("values", [])] if isinstance(lv, dict) else [int(x) for x in lv] for lv in fg["levels"]]
        fg["total"] = int(fg.get("total", 0))
        return fg

    def stacks(self, selector: str = "{}", profile_type: str = CPU_PROFILE_TYPE, minutes: int = 15, **kw: Any) -> Counter[Stack]:
        return flamebearer_to_stacks(self.flamegraph(selector, profile_type, minutes, **kw))

    def series_total(self, selector: str, profile_type: str = CPU_PROFILE_TYPE, minutes: int = 15, step_s: int = 15,
                     group_by: Sequence[str] = ()) -> list[dict[str, Any]]:
        """``SelectSeries``: serie temporal del valor total del perfil (útil para dibujar «CPU por servicio»)."""
        end = int(time.time() * 1000)
        r = self._rpc("querier.v1.QuerierService/SelectSeries", {"profileTypeID": profile_type, "labelSelector": selector, "start": end - minutes * 60_000,
                                                                "end": end, "step": float(step_s), "groupBy": list(group_by)})
        return r.get("series", [])

    def wait_for(self, selector: str, profile_type: str = CPU_PROFILE_TYPE, timeout_s: float = 60.0, min_total: int = 1, minutes: int = 15) -> int:
        """Sondea hasta que el perfil existe (Pyroscope tarda segundos en hacer visible lo que se acaba de empujar). Devuelve el total o 0."""
        t0, total = time.time(), 0
        while time.time() - t0 < timeout_s:
            try:
                total = self.flamegraph(selector, profile_type, minutes)["total"]
            except PyroscopeError:
                total = 0
            if total >= min_total:
                return total
            time.sleep(2.0)
        return total


# =====================================================================================================================
# 5. Rutas calientes de un agente (versión lenta y versión corregida)
# =====================================================================================================================
POLICY_LINES = [
    "Política {i}: confirma el número de pedido antes de actuar; nunca reveles datos de otro cliente; si el importe supera 200 EUR escala a un humano.",
    "Guía {i}: usa herramientas para consultar pedidos, reembolsos y base de conocimiento; contacto de auditoría ops{i}@supportops.example, línea 600 {i:03d} 123.",
    "Regla {i}: responde en español, con tono amable, en menos de 80 palabras; cita el documento de la base de conocimiento cuando lo uses.",
]


def policy_text(n_blocks: int = 24) -> str:
    """Prompt de sistema largo y determinista (≈ 10 KB con 24 bloques): lo habitual en agentes reales (políticas, ejemplos, esquema de herramientas)."""
    return "\n".join(line.format(i=i) for i in range(n_blocks) for line in POLICY_LINES)


def few_shot_examples(n: int = 450) -> list[dict[str, Any]]:
    """Ejemplos *few-shot* estructurados (lo que muchos agentes anexan en cada llamada). Muchos nodos pequeños = JSON caro de serializar."""
    return [{"role": "user" if i % 2 == 0 else "assistant", "content": f"Ejemplo {i}: pedido ORD-{10000 + i:05d} entregado hace {i % 28 + 1} días.",
             "meta": {"intent": ("order_status", "refund", "kb_question", "escalation")[i % 4], "score": round((i % 10) / 10, 1), "tags": ["demo", f"k{i % 7}"]}}
            for i in range(n)]


_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_DIGITS_RE = re.compile(r"\d(?:[ -]?\d){12,18}")


def luhn_ok(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = ord(ch) - 48
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0 and len(digits) >= 13


def scan_pii_slow(text: str) -> dict[str, int]:
    """ANTI-PATRÓN: recorre carácter a carácter en Python (lo hace mucha fontanería «casera»). O(n) con una constante enorme."""
    emails = cards = 0
    n, i = len(text), 0
    email_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._%+-")
    while i < n:
        ch = text[i]
        if ch == "@":
            j = i - 1
            while j >= 0 and text[j] in email_chars:
                j -= 1
            k = i + 1
            while k < n and (text[k] in email_chars or text[k] == "."):
                k += 1
            if i - j > 1 and "." in text[i + 1:k]:
                emails += 1
            i = k
        elif ch.isdigit():
            j, digits = i, []
            while j < n and (text[j].isdigit() or (text[j] in " -" and j + 1 < n and text[j + 1].isdigit())):
                if text[j].isdigit():
                    digits.append(text[j])
                j += 1
            if len(digits) >= 13 and luhn_ok("".join(digits)):
                cards += 1
            i = max(j, i + 1)
        else:
            i += 1
    return {"emails": emails, "cards": cards}


def scan_pii_fast(text: str) -> dict[str, int]:
    emails = len(_EMAIL_RE.findall(text))
    cards = sum(1 for m in _DIGITS_RE.finditer(text) if luhn_ok(re.sub(r"\D", "", m.group())))
    return {"emails": emails, "cards": cards}


def count_tokens_slow(text: str) -> int:
    """Estimador de tokens casero: parte cada palabra en trozos de 4 caracteres, uno a uno."""
    n = 0
    for word in text.split():
        pieces = [word[i:i + 4] for i in range(0, len(word), 4)]
        n += len(pieces)
    return n


def count_tokens_fast(text: str) -> int:
    return sum(-(-len(w) // 4) for w in text.split())


EXAMPLES = few_shot_examples()


def serialize_slow(system: str, messages: Sequence[Any]) -> str:
    """Reserializa SIEMPRE todo el historial (con ``indent`` y ``sort_keys``) en cada llamada al LLM: O(pasos²) con el historial."""
    payload = {"system": system, "examples": EXAMPLES, "messages": [asdict(m) if hasattr(m, "__dataclass_fields__") else m for m in messages]}
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str)


EMBED_DIM = 256


def embed_slow(text: str, dim: int = EMBED_DIM) -> list[float]:
    """Embedding por *feature hashing* de 3- y 4-gramas de caracteres (MD5 por n-grama) en Python puro: determinista y caro."""
    t = " " + re.sub(r"\s+", " ", text.lower()) + " "
    v = [0.0] * dim
    for n in (3, 4):
        for i in range(len(t) - n + 1):
            h = int(hashlib.md5(t[i:i + n].encode()).hexdigest()[:8], 16)
            v[h % dim] += 1.0 if (h >> 31) & 1 else -1.0
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / norm for x in v]


def cosine_slow(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _kb_docs() -> list[dict[str, Any]]:
    from .catalog import KB_DOCS
    return [{"doc_id": d.doc_id, "title": d.title, "text": d.text} for d in KB_DOCS]


class _Rerank:
    """Reordena los resultados de ``search_kb`` por similitud de embedding entre la pregunta y el documento."""

    def __init__(self, variant: str):
        self.variant = variant
        self._doc_emb: dict[str, Any] = {}
        self._np = None
        if variant == "fast":
            try:
                import numpy as np
                self._np = np
            except Exception:  # sin numpy: la variante rápida sigue cacheando
                self._np = None

    def rank(self, query: str, docs: Sequence[Mapping[str, Any]]) -> list[tuple[str, float]]:
        if self.variant == "slow":
            q = embed_slow(query)
            scored = [(d["doc_id"], cosine_slow(q, embed_slow(d["title"] + " " + d["text"]))) for d in docs]
        else:
            q = embed_slow(query)                    # la pregunta es corta y distinta cada vez: no se cachea
            scored = []
            for d in docs:
                key = d["doc_id"]
                if key not in self._doc_emb:         # el documento es el mismo siempre: se calcula UNA vez
                    e = embed_slow(d["title"] + " " + d["text"])
                    self._doc_emb[key] = self._np.asarray(e) if self._np is not None else e
                e = self._doc_emb[key]
                scored.append((key, float(self._np.dot(self._np.asarray(q), e)) if self._np is not None else cosine_slow(q, e)))
        scored.sort(key=lambda x: (-round(x[1], 9), x[0]))
        return scored


class HotPathInstrumentor(Instrumentor):
    """Fontanería con CPU real alrededor del LLM y las herramientas. ``variant='slow'`` es el código «ingenuo»; ``'fast'`` aplica las tres correcciones:

    1. **Serialización**: ``slow`` reserializa todo el historial en cada llamada; ``fast`` cachea el JSON por mensaje (compacto).
    2. **Escaneo/parseo de PII y recuento de tokens**: ``slow`` recorre carácter a carácter; ``fast`` usa regex precompilada y analiza una sola vez los
       fragmentos ya vistos (el prompt de sistema es el mismo en todas las llamadas).
    3. **Embeddings**: ``slow`` recalcula el embedding de los documentos de la KB en cada búsqueda; ``fast`` los cachea.

    Los cronómetros por etapa (``stage_s``) son la verdad de referencia con la que se valida lo que dice el perfilador.
    """

    STAGES = ("serialize", "pii_scan", "tokens", "embed_rerank")

    def __init__(self, variant: str = "slow", system_prompt: str | None = None):
        if variant not in ("slow", "fast"):
            raise ValueError("variant ∈ {slow, fast}")
        self.variant = variant
        self.system = system_prompt if system_prompt is not None else policy_text()
        self.stage_s: Counter[str] = Counter()
        self.calls: Counter[str] = Counter()
        self.pii_found = Counter()
        self.rerank = _Rerank(variant)
        self.rerank_order: dict[str, list[str]] = {}
        self._chunk_cache: dict[tuple, tuple[str, int, dict[str, int]]] = {}
        self._pc = time.perf_counter

    # ----- etapas
    def _prepare_slow(self, messages: Sequence[Any]) -> None:
        t = self._pc()
        body = serialize_slow(self.system, messages)
        self.stage_s["serialize"] += self._pc() - t
        t = self._pc()
        found = scan_pii_slow(body)
        self.stage_s["pii_scan"] += self._pc() - t
        t = self._pc()
        count_tokens_slow(body)
        self.stage_s["tokens"] += self._pc() - t
        self.pii_found.update(found)

    def _chunk(self, key: tuple, render) -> tuple[str, int, dict[str, int]]:
        hit = self._chunk_cache.get(key)
        if hit is not None:
            return hit
        t = self._pc()
        text = render()
        self.stage_s["serialize"] += self._pc() - t
        t = self._pc()
        found = scan_pii_fast(text)
        self.stage_s["pii_scan"] += self._pc() - t
        t = self._pc()
        ntok = count_tokens_fast(text)
        self.stage_s["tokens"] += self._pc() - t
        self._chunk_cache[key] = (text, ntok, found)
        return self._chunk_cache[key]

    def _prepare_fast(self, messages: Sequence[Any]) -> None:
        total = {"emails": 0, "cards": 0}
        parts = [self._chunk(("system", hash(self.system)), lambda: json.dumps(self.system, ensure_ascii=False)),
                 self._chunk(("examples", len(EXAMPLES)), lambda: json.dumps(EXAMPLES, ensure_ascii=False, separators=(",", ":")))]
        for m in messages:
            d = asdict(m) if hasattr(m, "__dataclass_fields__") else m
            key = (d.get("role"), d.get("content"), d.get("tool_call_id"), len(d.get("tool_calls") or ()))
            parts.append(self._chunk(key, lambda d=d: json.dumps(d, ensure_ascii=False, default=str, separators=(",", ":"))))
        for _, _, found in parts:
            for k, v in found.items():
                total[k] += v
        self.pii_found.update(total)

    # ----- hooks
    @contextmanager
    def llm_call(self, ctx, info) -> Iterator[None]:   # type: ignore[override]
        if info.messages is not None:
            (self._prepare_slow if self.variant == "slow" else self._prepare_fast)(info.messages)
            self.calls["llm_prepare"] += 1
        yield

    @contextmanager
    def tool_call(self, ctx, info) -> Iterator[None]:   # type: ignore[override]
        yield
        if info.call.name == "search_kb" and isinstance(info.result, dict) and info.result.get("results"):
            t = self._pc()
            ranked = self.rerank.rank(str(info.call.arguments.get("query", "")), _kb_docs())
            self.stage_s["embed_rerank"] += self._pc() - t
            self.rerank_order[ctx.ticket.ticket_id] = [d for d, _ in ranked]
            self.calls["rerank"] += 1


@dataclass
class WorkloadStats:
    variant: str
    n_tickets: int
    cpu_s: float
    wall_s: float
    stage_s: dict[str, float]
    calls: dict[str, int]
    results: list[Any] = field(default_factory=list, repr=False)
    rerank_order: dict[str, list[str]] = field(default_factory=dict, repr=False)
    pii_found: dict[str, int] = field(default_factory=dict)

    @property
    def ms_per_ticket(self) -> float:
        return 1000 * self.cpu_s / max(1, self.n_tickets)

    def stage_share(self) -> dict[str, float]:
        tot = sum(self.stage_s.values()) or 1.0
        return {k: v / tot for k, v in self.stage_s.items()}


def run_workload(variant: str = "slow", n: int = 60, seed: int = 42, *, profiler: Any = None, extra: Sequence[Instrumentor] = (),
                 tags: Mapping[str, str] | None = None, tickets: Sequence[Any] | None = None, warmup: int = 3) -> WorkloadStats:
    """Ejecuta ``n`` tickets de SupportOps (mock, semilla fija) con la ruta caliente ``variant``. Mide CPU de proceso real.

    ``profiler``: cualquier objeto con ``start()/stop()`` (``SamplingProfiler``) que rodea SOLO la parte medida. ``extra``: instrumentores
    adicionales (OTel, etc.; el de OTel debe ir primero para que el span esté activo). ``warmup`` tickets previos (sin medir) calientan cachés/imports.
    """
    from .agent import SupportAgent
    from .instrument import CompositeInstrumentor
    from .traffic import generate_tickets
    hot = HotPathInstrumentor(variant)
    instr = CompositeInstrumentor(*extra, hot) if extra else hot
    agent = SupportAgent(instrumentor=instr)
    tk = list(tickets) if tickets is not None else generate_tickets(n + warmup, seed=seed, fault_rates=None)
    for t in tk[:warmup]:
        agent.run(t)
    hot.stage_s.clear()
    hot.calls.clear()
    hot.pii_found.clear()
    hot.rerank_order.clear()
    measured = tk[warmup:warmup + n]
    if profiler is not None:
        profiler.start()
    c0, w0 = time.process_time(), time.perf_counter()
    results = []
    for t in measured:
        if tags:
            with (profiler.tag(**tags) if hasattr(profiler, "tag") else _null()):
                results.append(agent.run(t))
        else:
            results.append(agent.run(t))
    cpu, wall = time.process_time() - c0, time.perf_counter() - w0
    if profiler is not None:
        profiler.stop()
    return WorkloadStats(variant, len(measured), cpu, wall, dict(hot.stage_s), dict(hot.calls), results, dict(hot.rerank_order), dict(hot.pii_found))


@contextmanager
def _null() -> Iterator[None]:
    yield


# =====================================================================================================================
# 6. Utilidades de análisis
# =====================================================================================================================
def diff_self(before: Mapping[Stack, int], after: Mapping[Stack, int], top: int = 12) -> list[dict[str, Any]]:
    """Perfil diferencial por función (tiempo propio): fracción antes/después, y cambio en muestras normalizadas por el total de ANTES."""
    sb, sa = self_time(before), self_time(after)
    tb, ta = sum(sb.values()) or 1, sum(sa.values()) or 1
    rows = []
    for fn in set(sb) | set(sa):
        rows.append({"function": fn, "before": sb.get(fn, 0), "after": sa.get(fn, 0), "before_pct": 100 * sb.get(fn, 0) / tb,
                     "after_pct": 100 * sa.get(fn, 0) / ta, "delta_abs": (sa.get(fn, 0) - sb.get(fn, 0))})
    rows.sort(key=lambda r: -abs(r["delta_abs"]))
    return rows[:top]


def stage_of(stack: Stack) -> str:
    """Etapa de la ruta caliente a la que pertenece una pila (por las funciones de ESTE módulo que contiene). ``other`` = el resto del agente."""
    names = " ".join(stack)
    if "serialize_slow" in names or "json.encoder" in names or "json.dumps" in names:
        return "serialize"
    if "scan_pii" in names or "luhn_ok" in names:
        return "pii_scan"
    if "count_tokens" in names:
        return "tokens"
    if "embed_slow" in names or "cosine_slow" in names or "_Rerank" in names:
        return "embed_rerank"
    return "other"


def stage_shares(stacks: Mapping[Stack, int]) -> dict[str, float]:
    c: Counter[str] = Counter()
    for s, n in stacks.items():
        c[stage_of(s)] += n
    tot = sum(c.values()) or 1
    return {k: v / tot for k, v in c.items()}


def amdahl_speedup(fraction: float, local_speedup: float) -> float:
    """Aceleración global al acelerar ``local_speedup`` veces una parte que ocupa ``fraction`` del tiempo (Amdahl)."""
    return 1.0 / ((1.0 - fraction) + fraction / local_speedup)


def profile_cost_model(n_services: int, hz: float, bytes_per_profile: float, interval_s: float, retention_days: float, labels_per_series: int = 6) -> dict[str, float]:
    """Modelo aproximado del coste de perfilar en continuo: ingesta (MB/día) y almacenamiento (GB) para ``n_services`` réplicas."""
    profiles_per_day = 86400 / interval_s * n_services
    mb_day = profiles_per_day * bytes_per_profile / 1e6
    return {"profiles_per_day": profiles_per_day, "ingest_mb_per_day": mb_day, "storage_gb": mb_day * retention_days / 1000,
            "samples_per_s_total": hz * n_services}


def have_pyroscope_sdk() -> bool:
    try:
        import pyroscope  # noqa: F401
        return True
    except Exception:
        return False


# =====================================================================================================================
# 7. Dashboard 17 (Grafana, datasource Pyroscope)
# =====================================================================================================================
DS_PYROSCOPE = {"type": "grafana-pyroscope-datasource", "uid": "pyroscope"}


def pyro_target(label_selector: str, profile_type: str = CPU_PROFILE_TYPE, *, ref: str = "A", query_type: str = "both", group_by: Sequence[str] = ()) -> dict[str, Any]:
    return {"datasource": DS_PYROSCOPE, "refId": ref, "queryType": query_type, "profileTypeId": profile_type, "labelSelector": label_selector,
            "groupBy": list(group_by), "maxNodes": 1024}


def flamegraph_panel(title: str, targets: Sequence[dict[str, Any]], *, w: int = 24, h: int = 14, description: str = "") -> dict[str, Any]:
    from .dashkit import _panel
    return _panel("flamegraph", title, targets, w=w, h=h, description=description, ds=DS_PYROSCOPE)


def profiling_dashboard():
    from .dashkit import Dashboard, prom, stat, text, thresholds, timeseries, traces_table
    d = Dashboard("profiling", "17 · Profiling continuo (Pyroscope)", tags=["curso", "profiling", "pyroscope"], time_from="now-30m",
                  description="Cuarto pilar: perfiles de CPU de SupportOps en Pyroscope, comparación lenta vs rápida y salto traza ↔ perfil.")
    d.add(text("Cómo leer este dashboard", "Los perfiles los envía el notebook del módulo 17 (`pyroscope-io`, etiquetas `service_name=supportops-agent`, `variant=slow|fast`, `span_id`, `trace_id`). "
               "**Ancho = tiempo de CPU** (muestras); el eje vertical es la profundidad de la pila; lo que está ARRIBA y ANCHO es lo que consume. "
               "El panel de series muestra cuánta CPU consume cada variante; desde las trazas lentas puedes saltar al perfil de ese `span_id`.", h=3))
    sel = '{service_name="supportops-agent"}'
    d.row("CPU por variante del código")
    d.add(timeseries("CPU de perfil por variante (muestras/s agregadas)", [pyro_target(sel, query_type="metrics", group_by=["variant"])], w=24, h=7, unit="short",
                     description="Valor total del perfil de CPU de `supportops-agent` agrupado por la etiqueta `variant` (slow = ingenuo, fast = corregido)."))
    d.row("Flamegraphs")
    d.add(flamegraph_panel("Flamegraph · variant=slow (ingenuo)", [pyro_target('{service_name="supportops-agent",variant="slow"}', query_type="profile")], w=12, h=14,
                           description="Perfil de CPU de la versión ingenua: serialización del historial, escaneo de PII carácter a carácter y embeddings sin caché dominan."),
          flamegraph_panel("Flamegraph · variant=fast (corregido)", [pyro_target('{service_name="supportops-agent",variant="fast"}', query_type="profile")], w=12, h=14,
                           description="Perfil tras las correcciones: el trabajo propio del agente deja de ser el cuello de botella."))
    d.row("Traza ↔ perfil")
    d.add(traces_table("Trazas del agente con perfil asociado (`pyroscope.profile.id`)",
                       '{ resource.service.name = "supportops-agent" && span.pyroscope.profile.id != "" }', w=24, h=8,
                       description="Spans raíz marcados por `PyroscopeSpanProcessor` con `pyroscope.profile.id` (=span_id). Abre una traza y usa «Profiles for this span» para ver su flamegraph."))
    return d
