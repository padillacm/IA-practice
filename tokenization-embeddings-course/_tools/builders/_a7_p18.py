"""Proyecto 18 · Servicio Políglota (plantilla con TODOs + solución tras SPOILER) y README del módulo 18."""
import _a7_common as C
from _a7_common import hint

# Valores medidos por la solución de referencia (FAST_DEV_RUN=True, corpus sintético + stdlib, fallbacks v1/v2, semilla 42).
REF = {"hib_filtro": 0.882, "hib": 0.864, "hit_zipf": 0.805, "adapt50": 0.817, "v1": 0.786, "v2": 0.861}

SERVICE_TEMPLATE = C.CODE_SERVICE
_EMB_SOL = SERVICE_TEMPLATE[SERVICE_TEMPLATE.index("    def embebe_query"):SERVICE_TEMPLATE.index("    def _rangos_densos")]
_BUS_SOL = SERVICE_TEMPLATE[SERVICE_TEMPLATE.index("    def buscar"):SERVICE_TEMPLATE.index("    def metricas")]
SERVICE_TEMPLATE = SERVICE_TEMPLATE.replace(_EMB_SOL, '''    def embebe_query(self, texto, nombre):
        """Devuelve el vector (1, d) de la query para la versión `nombre`, usando la caché.
        Si la versión tiene adaptador W, aplica v @ W y renormaliza."""
        # TODO 2a: clave = clave_cache(nombre, texto); si está en self.cache, devuélvela; si no, calcula con
        #          self.versiones[nombre]["emb"].encode_queries([texto]), aplica W si existe (l2n(v @ W)) y guárdala.
        raise NotImplementedError("TODO 2a: embebe_query")

''').replace(_BUS_SOL, '''    def buscar(self, texto, k: int = 10, lang=None, modo: str = "hibrido", version: str = "prod"):
        """Devuelve [(doc_id, score_rrf)] top-k. modo: 'denso' | 'bm25' | 'hibrido'. lang: filtro DURO por idioma.
        Registra la latencia en self.lat_ms (ms)."""
        # TODO 2b: 1) resuelve el alias (self.alias.get(version, version)); 2) cand = índices con self.lang == lang (o None);
        #          3) listas de rangos con self._rangos_densos / self._rangos_bm25 según el modo;
        #          4) RRF: score[i] += 1/(self.rrf_k + rango + 1); 5) top-k por (-score, i); 6) guarda la latencia.
        raise NotImplementedError("TODO 2b: buscar")

''')
assert "TODO 2a" in SERVICE_TEMPLATE and "TODO 2b" in SERVICE_TEMPLATE

CACHE_TEMPLATE = r'''
from collections import OrderedDict

def normaliza_query(texto: str) -> str:
    """NFC + minúsculas + espacios colapsados."""
    # TODO 1a
    raise NotImplementedError("TODO 1a: normaliza_query")

def clave_cache(version: str, texto: str) -> str:
    """sha1 de 'version + separador + texto normalizado' (hexdigest)."""
    # TODO 1b
    raise NotImplementedError("TODO 1b: clave_cache")

class LRUCache:
    """Caché LRU con contadores hits/misses y propiedad hit_rate."""
    def __init__(self, capacidad: int):
        self.cap, self.d, self.hits, self.misses = capacidad, OrderedDict(), 0, 0
    def get(self, k):
        # TODO 1c: si está, muévela al final (más reciente), suma un hit y devuélvela; si no, suma un miss y devuelve None
        raise NotImplementedError("TODO 1c: LRUCache.get")
    def put(self, k, v):
        # TODO 1d: inserta/actualiza como más reciente; si se supera la capacidad, expulsa la MENOS reciente
        raise NotImplementedError("TODO 1d: LRUCache.put")
    @property
    def hit_rate(self) -> float:
        n = self.hits + self.misses
        return self.hits / n if n else 0.0
'''

TESTS_1 = r'''
def test_cache():
    assert normaliza_query("  Cómo   INVALIDAR\tla caché ") == "cómo invalidar la caché"
    assert normaliza_query("café") == normaliza_query("café"), "NFC: 'e' + tilde combinante == 'é'"
    assert clave_cache("v1", "Hola  Mundo") == clave_cache("v1", "hola mundo"), "la normalización va antes del hash"
    assert clave_cache("v1", "hola") != clave_cache("v2", "hola"), "¡la versión debe ir en la clave!"
    c = LRUCache(2); c.put("a", 1); c.put("b", 2); assert c.get("a") == 1
    c.put("c", 3)                                   # expulsa 'b' (la menos reciente: 'a' se acaba de usar)
    assert c.get("b") is None and c.get("a") == 1 and c.get("c") == 3, "orden LRU incorrecto"
    assert (c.hits, c.misses) == (3, 1) and abs(c.hit_rate - 0.75) < 1e-12
    return "✅ test_cache OK"
corre(test_cache)
'''

BUILD_SERVICE = r'''
def construye_servicio(cache_cap=2048):
    s = ServicioPoliglota(docs, BM25_IDX, cache_cap=cache_cap)
    for v in ("v1", "v2"):
        s.registrar_version(v, VERS[v], EMB[v]["D"])
    s.alias["prod"] = "v2"
    return s

def ndcg_servicio(s, **kw) -> np.ndarray:
    """nDCG@10 por query sirviendo TODAS las queries a través del servicio (como en producción)."""
    run = {qid: [d for d, _ in s.buscar(t, k=10, **kw)] for qid, t in zip(qids, q_texts)}
    return ndcg_por_query(run)

def test_servicio():
    s = construye_servicio()
    r = s.buscar(q_texts[0], k=10, lang="code")
    assert len(r) == 10 and all(doc_lang[doc_ids.index(d)] == "code" for d, _ in r), "el filtro de idioma no se respeta"
    assert all(r[i][1] >= r[i + 1][1] for i in range(len(r) - 1)), "resultados no ordenados por score"
    hib = ndcg_servicio(s).mean()
    s2 = construye_servicio()
    run_f = {qid: [d for d, _ in s2.buscar(t, k=10, lang=str(l))] for qid, t, l in zip(qids, q_texts, q_lang)}
    hib_f = ndcg_por_query(run_f).mean()
    RES.update(hib=hib, hib_filtro=hib_f)
    assert hib >= REF["hib"] - 0.02, f"nDCG híbrido {hib:.3f} < {REF['hib'] - 0.02:.3f}"
    assert s.cache.misses == len(set(clave_cache('v2', t) for t in q_texts)), "cada query distinta debe ser un miss la 1ª vez"
    return f"✅ test_servicio OK · híbrido={hib:.3f} · híbrido+filtro idioma={hib_f:.3f}"
'''


def project(nb):
    nb.md(nb.badge() + f"""

# Proyecto 18 · Servicio Políglota: caché, versionado y plan de migración medido

| | |
|---|---|
| **Nivel** | 🟠 Avanzado |
| **Duración estimada** | ≈ 2 h |
| **GPU recomendada** | No necesaria (CPU, `FAST_DEV_RUN = True`, ≈ 1–2 min de ejecución) |
| **Prerrequisitos** | Lección 18 (caché, migración, filtros, costes) · módulos 13 (RRF), 14 (FAISS), 15 (bootstrap pareado) |
| **Conecta con** | Módulo 17 (privacidad de los vectores que sirves) · Módulo 19 (decisiones de diseño) · **Módulo 20** (este servicio es la capa de servicio del capstone) |

## 🏢 Contexto de negocio
Eres ML engineer en **Políglota Labs**. Mañana se abre la beta: el buscador debe funcionar como **servicio** y no como notebook.
La CTO pide tres cosas: *«(1) una API con caché y filtro por idioma que no se rompa cuando cambiemos de modelo; (2) números de latencia;
(3) un plan para migrar de v1 a v2 con costes y calidad medidos: ¿re-embebemos todo, usamos un adaptador o esperamos?»*

## 📦 Dataset
Corpus Políglota canónico (`carga_corpus` del módulo 00: Wikipedia ES/EN + CodeSearchNet; sin red, **corpus sintético** + funciones reales de la stdlib, con aviso).
Embedders v1/v2: `multilingual-e5-small` / `multilingual-e5-base` si hay hub; si no, los fallbacks TF-IDF+SVD de la lección (espacios incompatibles).
Los umbrales numéricos están **calibrados con la solución de referencia** en `FAST_DEV_RUN=True`, corpus sintético y fallbacks (semilla 42). Con modelos o datos reales el notebook imprime tus cifras y aplica solo los chequeos estructurales.

## 🎯 Entregables y rúbrica (100 puntos)
| # | Entregable | Criterio objetivo (calibrado con la solución) | Puntos |
|---|---|---|---|
| 1 | Caché LRU + clave con versión y normalización | `test_cache` pasa (orden LRU, contadores, NFC, versión en la clave) | 15 |
| 2 | `ServicioPoliglota.buscar` (denso + BM25 + RRF + filtro) | filtro respetado; nDCG@10 híbrido ≥ {REF['hib'] - 0.02:.3f} (ref. {REF['hib']:.3f}) | 25 |
| 3 | Latencia y caché | p50 en caliente ≤ p50 en frío; hit rate con tráfico Zipf ≥ {REF['hit_zipf'] - 0.05:.3f} (ref. {REF['hit_zipf']:.3f}) | 15 |
| 4 | Adaptador v2→v1 servido como versión | nDCG@10 con 50 % de pares ≥ {REF['adapt50'] - 0.03:.3f} (ref. {REF['adapt50']:.3f}) y < nDCG de v2 completo | 20 |
| 5 | Plan de migración | dict con costes (API y GPU, supuestos explícitos), 2 tests pareados y una decisión coherente con la regla | 20 |
| 6 | Reflexión | 3 respuestas concretas al final | 5 |
""")
    nb.md("## 0. Preparación (celdas dadas)")
    nb.code(C.CODE_PIP)
    nb.code(C.CODE_SETUP)
    for src in C.src_corpus_cells():
        nb.code(src)
    nb.code(C.SRC_METRICS)
    nb.code(C.SRC_BM25)
    nb.code(C.STATS_SRC)
    nb.code(C.CODE_EMBEDDER_TOOLS)
    nb.code(C.CODE_LOAD)
    nb.code(C.CODE_HELPERS)
    nb.code(C.CODE_VERSIONES)
    nb.code(C.CODE_CORRE + f"\nREF = {REF!r}\nRES = {{}}   # aquí se guardan tus resultados para la rúbrica\n")

    # ── TODO 1
    nb.md("## 1. Caché de embeddings de query (TODO 1)\nImplementa la normalización, la clave (con **versión**) y una LRU con `OrderedDict`. Repasa §4 de la lección.")
    nb.md(hint("La clave debe cambiar si cambia la versión y **no** debe cambiar con mayúsculas/espacios/forma Unicode. La LRU es un `OrderedDict` donde el final es «lo más reciente».",
               "`unicodedata.normalize('NFC', t).lower().split()` + `' '.join(...)`; `hashlib.sha1(f'{version}\\x00{norm}'.encode()).hexdigest()`; `self.d.move_to_end(k)` y `self.d.popitem(last=False)`."))
    nb.code(CACHE_TEMPLATE)
    nb.code(TESTS_1)

    # ── TODO 2
    nb.md("## 2. El servicio (TODO 2)\nTe damos el esqueleto: índice FAISS por versión, BM25 compartido, alias `prod`, generación de candidatos con filtro **dentro** de la búsqueda (`IDSelectorBatch`) y métricas. Te faltan `embebe_query` (con caché y adaptador opcional) y `buscar` (fusión RRF).")
    nb.md(hint("`buscar` no calcula scores densos ni BM25 a mano: llama a `_rangos_densos` / `_rangos_bm25`, que ya devuelven índices de documento ordenados. Tu trabajo es fusionarlos con RRF y medir el tiempo.",
               "`listas = []`; `if modo in ('denso','hibrido'): listas.append(self._rangos_densos(texto, nombre, cand))`; `for lst in listas: for r, i in enumerate(lst): score[i] = score.get(i, 0) + 1/(self.rrf_k + r + 1)`; `top = sorted(score, key=lambda i: (-score[i], i))[:k]`."))
    nb.code(SERVICE_TEMPLATE)
    nb.code(BUILD_SERVICE + "\ncorre(test_servicio)\n")

    # ── TODO 3
    nb.md("## 3. Latencia y caché bajo tráfico (TODO 3)\nMide p50/p99 con batch = 1 en **frío** (caché vacía) y en **caliente** (las mismas queries otra vez), y el hit rate con tráfico Zipf (`trafico_zipf`, dado).")
    nb.code(r'''
def trafico_zipf(n, universo, s=1.1, p_variante=0.35, seed=SEED):
    """(Dado) n queries Zipf sobre un universo de intenciones, con variantes de mayúsculas/espacios."""
    rng = np.random.default_rng(seed)
    p = 1.0 / np.arange(1, len(universo) + 1) ** s; p /= p.sum()
    out = []
    for i in rng.choice(len(universo), size=n, p=p):
        t = universo[i]
        if rng.random() < p_variante:
            t = rng.choice([t.upper(), t.capitalize(), "  " + t, t.replace(" ", "  "), t + " "])
        out.append(t)
    return out
UNIVERSO = [q_texts[i % len(q_texts)] + ("" if i < len(q_texts) else f" {i // len(q_texts)}") for i in range(3000)]
''')
    nb.md(hint("Frío: servicio nuevo, recorre `q_texts` una vez. Caliente: recorre `q_texts` otra vez **en el mismo servicio**. `s.lat_ms` guarda las latencias en orden: sepáralas por tramos.",
               "`s = construye_servicio(); for t in q_texts: s.buscar(t)`; `frio = np.array(s.lat_ms)`; repite y toma `np.array(s.lat_ms[len(q_texts):])`. Hit rate: servicio con `cache_cap=1024`, recorre `trafico_zipf(5000, UNIVERSO)` y lee `s.cache.hit_rate`."))
    nb.code(r'''
def mide_latencias() -> dict:
    """Devuelve {"frio_p50","frio_p99","caliente_p50","caliente_p99","hit_rate_zipf"} (ms y fracción)."""
    # TODO 3
    raise NotImplementedError("TODO 3: mide_latencias")

def test_latencias():
    m = mide_latencias(); RES.update(m)
    assert m["caliente_p50"] <= m["frio_p50"], "la caché no está acelerando nada: ¿guardas y lees con la misma clave?"
    assert m["hit_rate_zipf"] >= REF["hit_zipf"] - 0.05, f"hit rate {m['hit_rate_zipf']:.3f} bajo: ¿normalizas antes de hashear?"
    return "✅ test_latencias OK · " + " · ".join(f"{k}={v:.3f}" for k, v in m.items())
corre(test_latencias)
''')

    # ── TODO 4
    nb.md("## 4. Adaptador v2 → v1 servido como versión (TODO 4)\nAjusta $W$ con el 50 % de los documentos embebidos con ambas versiones (ridge, $\\lambda=0.1$), regístralo en el servicio como versión `v2→v1` **sobre el índice v1** y mide nDCG@10 sirviendo en modo denso.")
    nb.md(hint("Es la fórmula cerrada de ridge de la lección: $W=(A^\\top A+\\lambda I)^{-1}A^\\top B$ con $A$ = embeddings v2 y $B$ = embeddings v1 de los **mismos** textos.",
               "`np.linalg.solve(A.T @ A + lam * np.eye(A.shape[1]), A.T @ B)`; Procrustes: `U, _, Vt = np.linalg.svd(A.T @ B, full_matrices=False); W = U @ Vt`. Luego `s.registrar_adaptador('v2→v1', VERS['v2'], W, sobre='v1')` y `ndcg_servicio(s, modo='denso', version='v2→v1')`."))
    nb.code(r'''
def ajusta_adaptador(A, B, lam: float = 0.1, metodo: str = "ridge"):
    """W tal que A @ W ≈ B. metodo: 'ridge' | 'procrustes'."""
    # TODO 4a
    raise NotImplementedError("TODO 4a: ajusta_adaptador")

def evalua_adaptador(frac: float = 0.5, seed: int = SEED) -> dict:
    """Devuelve {"v1": nDCG, "v2": nDCG, "adaptador": nDCG, "pq": {...por query...}} sirviendo por el servicio en modo denso."""
    # TODO 4b: muestra frac de documentos con np.random.default_rng(seed).choice(..., replace=False), ajusta W,
    #          registra 'v2→v1' y evalúa las tres versiones con ndcg_servicio(s, modo="denso", version=...)
    raise NotImplementedError("TODO 4b: evalua_adaptador")

def test_adaptador():
    r = evalua_adaptador(0.5); RES.update(adapt50=r["adaptador"], v1=r["v1"], v2=r["v2"], _pq=r["pq"])
    A = np.random.default_rng(0).normal(size=(50, 6)); Rm = np.linalg.qr(np.random.default_rng(1).normal(size=(6, 6)))[0]
    assert np.allclose(ajusta_adaptador(A, A @ Rm, metodo="procrustes"), Rm, atol=1e-6), "Procrustes debe recuperar una rotación exacta"
    assert r["adaptador"] >= REF["adapt50"] - 0.03, f"adaptador {r['adaptador']:.3f} demasiado bajo"
    assert r["adaptador"] < r["v2"], "un adaptador lineal no debería superar al re-embedding completo"
    return f"✅ test_adaptador OK · v1={r['v1']:.3f} · adaptador(50 %)={r['adaptador']:.3f} · v2={r['v2']:.3f}"
corre(test_adaptador)
''')

    # ── TODO 5
    nb.md(r"""## 5. Plan de migración con números (TODO 5)
Devuelve un `dict` con: `tokens_corpus_prod`, `coste_api_usd` (por proveedor), `coste_gpu_usd`, `horas_gpu`, `supuestos` (texto), `v2_vs_v1` y `v2_vs_adaptador` (salidas de `paired_bootstrap` sobre nDCG por query) y `decision`.

**Regla de decisión** (la que pide la CTO):
* si el IC95 de `v2 − v1` **no** excluye el 0 → `"quedarse en v1"`;
* si lo excluye y el IC95 de `v2 − adaptador` también → `"re-embedding blue/green (adaptador solo como puente)"`;
* si `v2 − v1` lo excluye pero `v2 − adaptador` no → `"adaptador"`.

Escenario de producción: 10 M de chunks de 400 tokens. Precios (oct-2026, verifícalos): 0.02, 0.13 y 0.15 $/1M; GPU **supuesta** 0.80 $/h, 20 000 tok/s, 60 % de utilización.""")
    nb.md(hint("Reutiliza `RES['_pq']` (nDCG por query de v1, v2 y adaptador que guardó el TODO 4) y `paired_bootstrap(a, b)` del módulo 15.",
               "`d = paired_bootstrap(pq['v2'], pq['v1'])`; «excluye el 0» ⇔ `d['ci_low'] > 0`. Costes: `T = 10_000_000 * 400`; `T / 1e6 * precio` y `T / (20_000 * 3600 * 0.6) * 0.80`."))
    nb.code(r'''
PRECIOS_API = {"OpenAI text-embedding-3-small": 0.02, "OpenAI text-embedding-3-large": 0.13, "Google gemini-embedding-001": 0.15}

def plan_migracion(pq: dict) -> dict:
    # TODO 5
    raise NotImplementedError("TODO 5: plan_migracion")

def test_plan():
    if "_pq" not in RES:
        raise NotImplementedError("completa antes el TODO 4 (guarda los nDCG por query)")
    p = plan_migracion(RES["_pq"]); RES["plan"] = p
    for k in ("tokens_corpus_prod", "coste_api_usd", "coste_gpu_usd", "horas_gpu", "supuestos", "v2_vs_v1", "v2_vs_adaptador", "decision"):
        assert k in p, f"falta la clave {k}"
    assert abs(p["coste_api_usd"]["OpenAI text-embedding-3-small"] - 80.0) < 1e-6 and abs(p["coste_gpu_usd"] - 74.07) < 0.01
    a, b = p["v2_vs_v1"]["ci_low"] > 0, p["v2_vs_adaptador"]["ci_low"] > 0
    esperada = "quedarse en v1" if not a else ("re-embedding blue/green (adaptador solo como puente)" if b else "adaptador")
    assert p["decision"] == esperada, f"decisión incoherente con la regla: {p['decision']!r} vs {esperada!r}"
    return f"✅ test_plan OK · decisión: {p['decision']}"
corre(test_plan)
''')
    nb.md("## 6. (Opcional) El servicio detrás de HTTP\nSi `fastapi` y `httpx` están instalados, esta celda expone tu servicio con FastAPI y lo prueba en proceso con `TestClient`. En Colab puedes lanzarlo con `uvicorn` en segundo plano.")
    nb.code(C.CODE_FASTAPI)
    nb.code(r'''
def prueba_api():
    if not FASTAPI_OK:
        return "omitido"
    cli = TestClient(crea_app(construye_servicio()))
    assert cli.get("/health").json()["prod"] == "v2"
    r = cli.post("/search", json={"q": q_texts[0], "k": 5, "lang": "es"}).json()
    assert r["version"] == "v2" and len(r["results"]) == 5
    return f"✅ API OK · /search -> {r['results'][:2]} · /metrics -> {cli.get('/metrics').json()['n']} peticiones"
corre(prueba_api)
''')
    nb.code(r'''
def rubrica():
    filas = [("1 caché", 15, corre(test_cache)), ("2 servicio", 25, corre(test_servicio)), ("3 latencia", 15, corre(test_latencias)),
             ("4 adaptador", 20, corre(test_adaptador)), ("5 plan", 20, corre(test_plan))]
    total = sum(p for _, p, ok in filas if ok)
    print("\n".join(f"{'✅' if ok else '⬜'} {n:12s} {p:3d} pts" for n, p, ok in filas))
    print(f"Puntuación automática: {total}/95 (+5 de la reflexión, la revisa una persona)")
    if corpus["source"] != "synthetic":
        print("ℹ️ Datos reales: los umbrales numéricos están calibrados con el corpus sintético; compara tus cifras con criterio.")
rubrica()
''')

    # ── SPOILER
    nb.md("---\n## ⛔ SPOILER — intenta resolverlo primero\nA partir de aquí está la **solución de referencia** completa. Ejecutarla redefine tus funciones y vuelve a pasar la rúbrica.")
    nb.code(C.CODE_CACHE)
    nb.code(C.CODE_SERVICE)
    nb.code(C.CODE_ADAPTER)
    nb.code(r'''
def mide_latencias() -> dict:
    s = construye_servicio()
    for t in q_texts: s.buscar(t)
    for t in q_texts: s.buscar(t)
    lat = np.array(s.lat_ms); n = len(q_texts)
    z = construye_servicio(cache_cap=1024)
    for t in trafico_zipf(5000, UNIVERSO): z.buscar(t)
    return {"frio_p50": float(np.percentile(lat[:n], 50)), "frio_p99": float(np.percentile(lat[:n], 99)),
            "caliente_p50": float(np.percentile(lat[n:], 50)), "caliente_p99": float(np.percentile(lat[n:], 99)),
            "hit_rate_zipf": z.cache.hit_rate}

def evalua_adaptador(frac: float = 0.5, seed: int = SEED) -> dict:
    idx = np.random.default_rng(seed).choice(len(doc_texts), int(frac * len(doc_texts)), replace=False)
    W = ajusta_adaptador(EMB["v2"]["D"][idx], EMB["v1"]["D"][idx], lam=0.1)
    s = construye_servicio(); s.registrar_adaptador("v2→v1", VERS["v2"], W, sobre="v1")
    pq = {v: ndcg_servicio(s, modo="denso", version=n) for v, n in (("v1", "v1"), ("v2", "v2"), ("adaptador", "v2→v1"))}
    return {"v1": pq["v1"].mean(), "v2": pq["v2"].mean(), "adaptador": pq["adaptador"].mean(), "pq": pq}

def plan_migracion(pq: dict) -> dict:
    T = 10_000_000 * 400
    usd_h, tok_s, util = 0.80, 20_000, 0.6
    a, b = paired_bootstrap(pq["v2"], pq["v1"]), paired_bootstrap(pq["v2"], pq["adaptador"])
    if a["ci_low"] <= 0:
        dec = "quedarse en v1"
    elif b["ci_low"] > 0:
        dec = "re-embedding blue/green (adaptador solo como puente)"
    else:
        dec = "adaptador"
    return {"tokens_corpus_prod": T, "coste_api_usd": {k: T / 1e6 * p for k, p in PRECIOS_API.items()},
            "coste_gpu_usd": T / (tok_s * 3600 * util) * usd_h, "horas_gpu": T / (tok_s * 3600 * util),
            "supuestos": f"precios API estándar oct-2026; GPU SUPUESTA {usd_h} $/h, {tok_s} tok/s, utilización {util}; 10 M chunks x 400 tokens",
            "v2_vs_v1": a, "v2_vs_adaptador": b, "decision": dec}
''')
    nb.code(r'''
rubrica()
print(json.dumps({k: (v if not isinstance(v, dict) else {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items()})
                  for k, v in RES["plan"].items()}, indent=1, ensure_ascii=False))
''')
    nb.code(r'''
# Figura del informe: calidad por ruta de migración + latencias del servicio
fig, axs = plt.subplots(1, 2, figsize=(11, 3.8))
nombres = ["v1 (prod actual)", "adaptador v2→v1 (50 %)", "v2 re-embedding"]
vals = [RES["v1"], RES["adapt50"], RES["v2"]]
cis = [bootstrap_ci(RES["_pq"][k]) for k in ("v1", "adaptador", "v2")]
axs[0].bar(nombres, vals, color=[GRIS, NARANJA, AZUL], yerr=[[v - c[1] for v, c in zip(vals, cis)], [c[2] - v for v, c in zip(vals, cis)]], capsize=4)
axs[0].set_ylabel("nDCG@10 (IC95 bootstrap)"); axs[0].set_title("Rutas de migración servidas por el servicio"); axs[0].tick_params(axis="x", labelsize=8)
axs[1].bar(["frío p50", "frío p99", "caliente p50", "caliente p99"], [RES["frio_p50"], RES["frio_p99"], RES["caliente_p50"], RES["caliente_p99"]],
           color=[NARANJA, NARANJA, AZUL, AZUL]); axs[1].set_ylabel("ms por query (CPU, batch=1)"); axs[1].set_title("Latencia del servicio")
plt.tight_layout(); plt.show()
''')
    nb.md(r"""> 👀 **Qué debes observar:** el adaptador queda entre v1 y v2 con IC que se solapan con v1: es un puente, no un destino. La latencia en caliente baja un orden de magnitud porque se salta el embedder (aquí, una llamada individual a TF-IDF+SVD de scikit-learn cuesta ~10 ms; con un embedder neuronal en una GPU remota el ahorro por acierto incluye además el viaje de red).

## 🚀 Retos extra
1. **Caché de documentos por contenido**: simula 3 releases de la documentación donde cambia el 10 % de los chunks y mide cuántos tokens re-embebes con caché `hash(texto)+versión` vs sin ella.
2. **Qdrant como backend** del servicio (named vectors `v1`/`v2` en una sola colección, alias de colección para `prod`) y compara resultados con FAISS.
3. **Boost de idioma en vez de filtro duro**: suma un término $\beta\cdot[\text{lang(doc)}=\text{lang(query)}]$ al score RRF y elige $\beta$ por validación cruzada.
4. **Micro-batching real**: un hilo que agrupe peticiones concurrentes (cola + `max_wait`) delante de `encode_queries` y mide p99 con un generador de carga Poisson.
5. **Interleaving en el servicio**: un endpoint `/search?experimento=v1_vs_v2` que devuelva la lista *team-draft* y registre a qué equipo pertenece cada resultado.

## 🤔 Reflexión (5 pts, la revisa una persona)
1. ¿Qué parte del plan cambia si el texto original de los documentos **ya no está disponible** (solo guardaste vectores)?
2. Tu servicio usa filtro **duro** de idioma. Describe una query real de Políglota donde eso empeora el resultado y cómo lo detectarías en producción.
3. ¿Qué tres métricas pondrías en el panel de la beta y con qué umbral de alerta cada una? (Conecta con §9–§10 de la lección.)

**Siguiente:** en el módulo 19 convertirás estas decisiones en árboles de decisión y casos de *system design*; en el 20, este servicio será la capa de servicio de Políglota completo.
""")


README = r"""# Módulo 18 · Embeddings y retrieval en producción

**Nivel:** 🟠 Avanzado · **Duración:** ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) · **Cómputo:** CPU (0 unidades de Colab); T4 opcional para medir throughput real

| Archivo | Contenido |
|---|---|
| [`18_produccion.ipynb`](18_produccion.ipynb) | Lección: costes API vs GPU (fórmulas, precios fechados oct-2026, punto de equilibrio) · batching y padding medidos con un encoder Transformer · micro-batching dinámico (simulación de colas, p50/p99) · *tail at scale* con fan-out y hedged requests · TEI y vLLM (referencia + cliente) · caché LRU con versión en la clave (hit rate con tráfico Zipf, bug de caché sin versión) · **migración v1→v2 medida**: re-embedding vs adaptadores ridge/Procrustes (query-side y doc-side) con test pareado · cuantización int8/binaria + rescoring · **Qdrant en modo local** (named vectors por versión, filtros; respaldo FAISS) · híbrido + filtro por idioma · inversión de embeddings y ruido (privacidad vs utilidad) · drift sin etiquetas (top-1, PSI) · A/B vs team-draft interleaving (potencia) |
| [`18_proyecto_produccion.ipynb`](18_proyecto_produccion.ipynb) | Proyecto **Servicio Políglota**: `ServicioPoliglota` con caché LRU versionada, FAISS por versión, BM25, RRF, filtro por idioma, alias `prod`, adaptador servido como versión, latencias frío/caliente, plan de migración con costes y tests pareados, API FastAPI opcional. TODOs, pistas 🪜, rúbrica de 100 puntos calibrada y solución tras ⛔ SPOILER |
| `assets/` | Recursos de Gemini: `M18-IMG-01.png`, `M18-IMG-02.png`, `M18-IMG-03.png`, `M18-VID-01.mp4` |

## Objetivos
1. Calcular costes de embeber y servir (API vs GPU) con supuestos explícitos y fechados.
2. Medir batching/padding y razonar p50/p99 con colas y fan-out.
3. Implementar caché versionada y medir su hit rate.
4. Implementar y medir la migración de embedder (re-embedding vs adaptador lineal).
5. Operar una vector DB ligera con filtros y versiones; combinarla con BM25.
6. Cuantificar privacidad (inversión), detectar drift y elegir entre A/B e interleaving.

## Piezas reutilizadas (no reescritas)
Corpus, métricas y BM25 canónicos (`_tools/builders/poliglota_utils.py`, módulo 00) · embedders con fallback (`_a5_common.py`, módulo 12) · `bootstrap_ci`/`paired_bootstrap` (`poliglota_eval.py`, módulo 15). El servicio del proyecto (`_tools/builders/_a7_common.py`) se reutiliza en el capstone (módulo 20).

## Datos y modelos
Corpus Políglota (`carga_corpus`, cadena oficial → espejo → sintético). Embedders v1/v2 = `multilingual-e5-small`/`multilingual-e5-base` con hub; sin hub, dos fallbacks TF-IDF+SVD distintos (48 d y 128 d).

## Estado de pruebas (entorno de autoría, oct-2026)
Lección y proyecto ejecutados completos con `nbclient` en CPU (≈ 1 min cada uno) con el corpus **sintético** + stdlib y los **fallbacks** (Hugging Face bloqueado por el proxy). **Sí se ejecutaron:** FAISS, Qdrant en modo local (`qdrant-client`), FastAPI + `TestClient`, el encoder PyTorch de las mediciones de batching. **No se pudo probar:** modelos reales del hub, TEI/vLLM (sin Docker ni hub; el cliente TEI solo corre si defines `TEI_URL`), pgvector (sin Postgres; solo SQL de referencia), throughput en GPU. Precios de API verificados en fuentes públicas (oct-2026); el precio y el throughput de GPU son **supuestos** marcados como tales.

## Lecturas
Dean & Barroso 2013 (*The Tail at Scale*) · Shen et al. 2020 (BCT, arXiv:2003.11942) · Song & Raghunathan 2020 (arXiv:2004.00053) · Morris et al. 2023 (vec2text, arXiv:2310.06816) · Chapelle et al. 2012 (interleaving, ACM TOIS) · Kohavi, Tang, Xu 2020 · Douze et al. 2024 (FAISS, arXiv:2401.08281) · documentación de TEI, vLLM, Qdrant y pgvector.

## Enlaces
Anterior: [17 · Interpretabilidad y geometría](../17_interpretabilidad_geometria/) · Siguiente: [19 · Playbook de élite](../19_playbook_elite/)

*Notebooks generados con `python tokenization-embeddings-course/_tools/builders/build_18.py` (desde la raíz del repo).*
"""
