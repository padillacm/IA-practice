"""Proyecto 20 · Capstone: Políglota completo (plantilla con TODOs + solución tras SPOILER) y README del módulo 20."""
import _a7_common as C
from _a7_common import hint
from _a7_l20 import CODE_CAPSTONE_TOOLS

# Valores medidos por la solución de referencia (FAST_DEV_RUN=True, corpus sintético + stdlib, fallbacks, semilla 42).
REF = {"dev_config": 0.914, "test": 0.887, "test_bm25": 0.842}

ACEPTACION_SRC = r'''
ACEPTACION = {
    "calidad_vs_bm25":   "nDCG@10 en test ≥ BM25 del módulo 00 y límite inferior del IC95 de la diferencia pareada > −0.03",
    "peor_slice":        "ningún idioma más de 0.05 por debajo de BM25 en test",
    "recall_ann":        "neighbor recall@10 del índice elegido ≥ 0.95 frente a fuerza bruta",
    "latencia_p99_ms":   "p99 del servicio ≤ 50 ms (CPU, batch=1)",
    "ram_10M_gb":        "RAM del índice para 10 M de chunks ≤ 16 GB por réplica",
    "coste_reembed_usd": "re-embedding de 10 M chunks × 400 tokens ≤ 500 $ (API a 0.02 $/1M, oct-2026)",
    "hit_rate":          "hit rate de la caché con tráfico Zipf ≥ 0.70",
}
'''

GIVEN_SRC = r'''
ANALIZADORES = {"palabras": tokenize_simple, "palabras+ident": tok_ident}
def trafico_zipf(n, universo, s=1.1, p_variante=0.35, seed=SEED):
    """(Dado) tráfico Zipf con variantes superficiales (módulo 18)."""
    rng = np.random.default_rng(seed); p = 1.0 / np.arange(1, len(universo) + 1) ** s; p /= p.sum(); out = []
    for i in rng.choice(len(universo), size=n, p=p):
        t = universo[i]
        out.append(rng.choice([t.upper(), "  " + t, t + " "]) if rng.random() < p_variante else t)
    return out
UNIVERSO = [q_texts[i % len(q_texts)] + ("" if i < len(q_texts) else f" {i // len(q_texts)}") for i in range(3000)]

def vectores_de(config):
    """(Dado) Vectores de docs y queries según config: modelo, dim (primeras d + renormalizar) y precisión."""
    D, Q = EMB[config["modelo"]]["D"][:, :config["dim"]], EMB[config["modelo"]]["Q"][:, :config["dim"]]
    D, Q = l2n(D), l2n(Q)
    return (int8_ida_vuelta(D) if config["precision"] == "int8" else D), Q

def scores_de(config):
    """(Dado) Matriz de scores (queries x docs) del sistema descrito por config, SIN índice ANN (fuerza bruta)."""
    D, Q = vectores_de(config); f = ANALIZADORES[config["analizador"]]
    bm = BM25().fit([f(t) for t in doc_texts], doc_ids); Sl = np.array([bm.scores(f(q)) for q in q_texts]); Sd = Q @ D.T
    if config["fusion"] == "rrf":
        return rrf_mat(Sd, Sl)
    if config["fusion"] == "lineal":
        return lineal_lista(Sd, Sl, config["alfa"])
    return Sd if config["fusion"] == "denso" else Sl
RES = {}
'''

RUBRICA_SRC = r'''
CLAVES_CONFIG = {"analizador", "modelo", "dim", "precision", "fusion", "alfa", "ef_search"}

def _requiere(*claves):
    falta = [k for k in claves if k not in RES]
    if falta:
        raise NotImplementedError(f"completa antes los TODOs que producen {falta}")

def test_tokenizer():
    df = informe_tokenizer(4000); RES["tok"] = df
    assert set(df["lang"]) == {"es", "en", "code"} and {"fertilidad", "bytes_por_token"} <= set(df.columns)
    f = dict(zip(df["lang"], df["fertilidad"]))
    assert f["code"] > f["es"], "el código debería pagar más tokens por palabra que el español"
    return f"✅ tokenizer · fertilidad {', '.join(f'{k}={v:.2f}' for k, v in f.items())}"

def test_config():
    cfg = elige_configuracion(); RES["config"] = cfg
    assert CLAVES_CONFIG <= set(cfg), f"faltan claves: {CLAVES_CONFIG - set(cfg)}"
    assert cfg["analizador"] in ANALIZADORES and cfg["modelo"] in EMB and cfg["precision"] in ("float32", "int8")
    assert cfg["fusion"] in ("rrf", "lineal", "denso", "bm25") and 1 <= cfg["dim"] <= EMB[cfg["modelo"]]["D"].shape[1]
    dev = pq_S(scores_de(cfg))[I_DEV].mean(); RES["dev_config"] = dev
    assert dev >= REF["dev_config"] - 0.03, f"nDCG@10 en dev de tu configuración {dev:.3f} < {REF['dev_config'] - 0.03:.3f}"
    return f"✅ configuración · dev nDCG@10 = {dev:.3f} · {cfg}"

def test_indice():
    _requiere("config")
    r = verifica_indice(RES["config"]); RES.update(recall_ann=r["recall"], ram_10M_gb=r["ram_10M_gb"])
    assert r["recall"] >= 0.95, f"recall@10 {r['recall']:.3f} < 0.95: sube efSearch"
    return f"✅ índice · recall@10={r['recall']:.3f} · RAM 10 M={r['ram_10M_gb']:.1f} GB"

def test_servicio():
    _requiere("config")
    svc, m = monta_servicio(RES["config"]); RES["svc"] = svc; RES.update(m)
    assert m["p99_frio"] <= 50, f"p99 {m['p99_frio']:.1f} ms > 50 ms"
    assert m["hit_rate"] >= 0.70, f"hit rate {m['hit_rate']:.2f} < 0.70"
    assert svc.alias.get("prod") in svc.versiones and str(RES["config"]["dim"]) in svc.alias["prod"], "la versión servida debe incluir dim"
    return f"✅ servicio · p99 frío={m['p99_frio']:.1f} ms · hit rate={m['hit_rate']:.2f} · versión={svc.alias['prod']}"

def test_evaluacion():
    _requiere("config", "svc")
    e = evalua_test(RES["svc"]); RES["eval"] = e
    assert {"final", "bm25", "delta_bm25", "slices"} <= set(e)
    assert e["final"] >= REF["test"] - 0.03, f"nDCG@10 en test {e['final']:.3f} < {REF['test'] - 0.03:.3f}"
    return f"✅ evaluación · test nDCG@10={e['final']:.3f} (BM25 {e['bm25']:.3f}) · Δ IC95=[{e['delta_bm25']['ci_low']:+.3f},{e['delta_bm25']['ci_high']:+.3f}]"

def test_informe():
    _requiere("config", "eval", "tok", "recall_ann", "p99_frio", "dev_config")
    md = genera_informe(); RES["informe"] = md
    for h in ("Decisiones", "test ciego", "Costes", "Criterios de aceptación", "Limitaciones"):
        assert h.lower() in md.lower(), f"falta la sección «{h}»"
    assert md.count("✅") + md.count("❌") >= len(ACEPTACION), "la tabla de aceptación debe tener una fila por criterio"
    assert os.path.exists("poliglota_informe.md") and os.path.exists("poliglota_config.json")
    return f"✅ informe · {md.count('✅')} criterios cumplidos de {len(ACEPTACION)}"

def rubrica_final():
    filas = [("1 tokenizer", 10, test_tokenizer), ("2 decisiones en dev", 25, test_config), ("3 índice", 10, test_indice),
             ("4 servicio", 15, test_servicio), ("5 evaluación test", 20, test_evaluacion), ("6 informe", 15, test_informe)]
    total = 0
    for nombre, pts, f in filas:
        ok = corre(f); total += pts if ok else 0
        print(f"   {'✅' if ok else '⬜'} {nombre:22s} {pts:3d} pts")
    print(f"\nPuntuación automática: {total}/95 (+5 de la reflexión, la revisa una persona). Aprobado: ≥ 75.")
    if corpus["source"] != "synthetic":
        print("ℹ️ Datos reales: los umbrales de calidad están calibrados con el corpus sintético; compara con criterio.")
    return total
'''


def project(nb):
    nb.md(nb.badge() + f"""

# Proyecto 20 · Capstone: Políglota completo

| | |
|---|---|
| **Nivel** | 🔴 Experto |
| **Duración estimada** | ≈ 3.5 h |
| **GPU recomendada** | No necesaria en `FAST_DEV_RUN` (≈ 1 min de CPU); T4/L4 con modelos reales y `FAST_DEV_RUN=False` |
| **Prerrequisitos** | Todo el curso; la lección 20 es la solución de referencia del procedimiento |
| **Entrega** | `poliglota_informe.md` + `poliglota_config.json` + este notebook ejecutado |

## 🏢 Contexto de negocio
Es el día de la revisión de lanzamiento de **Políglota v1.0**. La CTO ya fijó los **criterios de aceptación** (celda dada). Tú decides cada componente con datos de *dev*, montas el servicio, lo evalúas **una vez** en el test ciego y entregas el informe técnico que se leerá en la reunión. La pregunta no es «¿cuánto da?», sino **«¿podemos lanzar, con qué riesgos y qué medimos después?»**.

## 📦 Datos
Corpus Políglota canónico (`carga_corpus`, módulo 00: Wikipedia ES/EN + CodeSearchNet; sin red, **sintético** + stdlib con aviso). Split **dev / test ciego** estratificado por idioma (dado). Embedders v1/v2 (e5 o fallbacks, módulo 18). Opcional: el retriever visual del proyecto 16 como tercer componente.

## 🎯 Entregables y rúbrica final (100 puntos)
| # | Entregable | Criterio objetivo (calibrado con la solución de referencia) | Pts |
|---|---|---|---|
| 1 | Informe del tokenizer (BPE byte-level, HF `tokenizers`) | fertilidad y bytes/token por idioma; el código paga más que el español | 10 |
| 2 | `elige_configuracion()` decidida **solo con dev** | config válida; nDCG@10 en dev ≥ {REF['dev_config'] - 0.03:.3f} (ref. {REF['dev_config']:.3f}) | 25 |
| 3 | Índice verificado | neighbor recall@10 ≥ 0.95 con N = 20 000 y proyección de RAM a 10 M | 10 |
| 4 | Servicio montado con la config | p99 frío ≤ 50 ms (CPU, batch=1); hit rate Zipf ≥ 0.70; versión servida con `dim` | 15 |
| 5 | Evaluación en test ciego (una vez) | nDCG@10 del servicio ≥ {REF['test'] - 0.03:.3f} (ref. {REF['test']:.3f}; BM25 {REF['test_bm25']:.3f}); IC pareado vs BM25 y slices | 20 |
| 6 | Informe técnico generado | secciones obligatorias + tabla de los 7 criterios + archivos guardados | 15 |
| 7 | Reflexión | 3 respuestas al final | 5 |

**Aprobado: ≥ 75/100.** Reglas de juego: (a) nada de lo que elijas puede mirar `I_TEST` (la rúbrica revisa el código de la solución, tú revisa el tuyo); (b) el número final sale **del servicio**, no de una matriz de scores.
""")
    nb.md("## 0. Preparación (celdas dadas)")
    nb.code(C.CODE_PIP.replace("pandas", "pandas tokenizers"))
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
    nb.code(C.CODE_CACHE)
    nb.code(C.CODE_SERVICE)
    nb.code(CODE_CAPSTONE_TOOLS)
    nb.code(C.CODE_CORRE + f"\nREF = {REF!r}\n")
    nb.code(ACEPTACION_SRC)
    nb.code(GIVEN_SRC)
    nb.code(RUBRICA_SRC)

    nb.md("## 1. Tokenizer: informe de coste por idioma (TODO 1)\nEntrena un BPE byte-level con `entrena_bpe(doc_texts, V)` y devuelve un `DataFrame` con columnas `lang`, `fertilidad` (tokens/palabra) y `bytes_por_token` para `es`, `en` y `code`.")
    nb.md(hint("Agrupa los documentos por `d['lang']`, codifica cada texto con `tk.encode(t).ids` y suma tokens, palabras (`t.split()`) y bytes (`t.encode()`).",
               "`n_tok = sum(len(tk.encode(t).ids) for t in tx)`; `fertilidad = n_tok / sum(len(t.split()) for t in tx)`; `bytes_por_token = sum(len(t.encode()) for t in tx) / n_tok`."))
    nb.code(r'''
def informe_tokenizer(V: int = 4000) -> pd.DataFrame:
    # TODO 1
    raise NotImplementedError("TODO 1: informe_tokenizer")

corre(test_tokenizer)
''')
    nb.md("## 2. Decisiones en dev (TODO 2)\nDevuelve la configuración completa decidida **solo con `I_DEV`**: `analizador` ∈ `ANALIZADORES`, `modelo` ∈ {`v1`,`v2`}, `dim`, `precision`, `fusion` ∈ {`rrf`,`lineal`,`denso`,`bm25`}, `alfa` y `ef_search`. Usa (o mejora, justificándolo) las reglas de la lección: modelo por test pareado, menor `dim` a ≤ 0.01 de la completa, int8 si pierde ≤ 0.01, lineal solo si su CV gana a RRF con IC.")
    nb.md(hint("`scores_de(config)` te da la matriz de scores de cualquier configuración: evalúala con `pq_S(S)[I_DEV]`. Decide por etapas (analizador → modelo → dim → precisión → fusión) en vez de una rejilla enorme (¿recuerdas el *winner's curse*?).",
               "Analizador: `max(ANALIZADORES, key=lambda a: pq_S(scores_de({**cfg, 'analizador': a, 'fusion': 'bm25'}))[I_DEV].mean())`. Fusión lineal con CV: la celda §4 de la lección (`PQa`, `np.array_split`, `paired_bootstrap(lin_cv, pq_rrf)`). `ef_search`: empieza en 128 y verifícalo en el TODO 3."))
    nb.code(r'''
def elige_configuracion() -> dict:
    # TODO 2: SOLO I_DEV. Devuelve dict(analizador, modelo, dim, precision, fusion, alfa, ef_search)
    raise NotImplementedError("TODO 2: elige_configuracion")

corre(test_config)
''')
    nb.md("## 3. Índice: recall y memoria (TODO 3)\nAmplía los vectores de documentos de tu config con copias ruidosas hasta N = 20 000 (como en la lección §5), mide el neighbor recall@10 de HNSW (M = 32, `efSearch = config['ef_search']`) contra Flat con las queries de dev, y proyecta la RAM a 10 M de chunks (bytes por vector + 256 B de grafo).")
    nb.md(hint("Usa `vectores_de(config)`; ruido gaussiano de escala `0.35/sqrt(dim)` y renormaliza.",
               "`flat = faiss.IndexFlatIP(d); flat.add(X); gt = flat.search(Qd, 10)[1]`; `hnsw = faiss.IndexHNSWFlat(d, 32, faiss.METRIC_INNER_PRODUCT)`; `hnsw.search(Qd, 10, params=faiss.SearchParametersHNSW(efSearch=ef))[1]`; RAM = `1e7 * (bpv + 256) / 1e9`."))
    nb.code(r'''
def verifica_indice(config: dict, N: int = 20_000) -> dict:
    """Devuelve {"recall": float, "ram_10M_gb": float}."""
    # TODO 3
    raise NotImplementedError("TODO 3: verifica_indice")

corre(test_indice)
''')
    nb.md("## 4. Servicio (TODO 4)\nMonta `ServicioPoliglota` con tu config (BM25 con **el mismo analizador** que pasas como `tokenizador`, `EmbedderRecortado`, vectores de `vectores_de`, `indice='hnsw'`, tu `ef_search` y tu fusión), con alias `prod` → una versión cuyo nombre incluya modelo, `dim` y precisión. Mide p50/p99 en frío (todas las queries una vez) y el hit rate con `trafico_zipf(5000, UNIVERSO)` en un servicio nuevo.")
    nb.md(hint("La lección §6 hace exactamente esto. Recuerda: la fusión del servicio se pasa en el constructor (`fusion='rrf'|'lineal'`, `alfa`). Si tu config elige `denso` o `bm25`, usa `modo=` al buscar.",
               "`svc = ServicioPoliglota(docs, bm, cache_cap=1024, tokenizador=f, fusion=..., alfa=...)`; `svc.registrar_version(v, EmbedderRecortado(VERS[m], dim), D, indice='hnsw', ef_search=ef)`; `svc.alias['prod'] = v`."))
    nb.code(r'''
def monta_servicio(config: dict):
    """Devuelve (servicio, {"p50_frio", "p99_frio", "hit_rate"}). El servicio devuelto es el que se evalúa en test."""
    # TODO 4
    raise NotImplementedError("TODO 4: monta_servicio")

corre(test_servicio)
''')
    nb.md("## 5. Evaluación en test ciego, una sola vez (TODO 5)\nSirve las queries de **test** por el servicio y compáralas con BM25 del módulo 00 (`S_BM25`): nDCG@10 medio, `paired_bootstrap` y nDCG por idioma de ambos.")
    nb.md(hint("Construye un `run` solo para las queries de `I_TEST` llamando a `svc.buscar(q_texts[i], k=10, modo=...)` y evalúalo con `ndcg_at_k` contra `qrels`.",
               "`pq_f = np.array([ndcg_at_k([d for d, _ in svc.buscar(q_texts[i], k=10, modo=modo)], qrels[qids[i]], 10) for i in I_TEST])`; `pq_b = pq_S(S_BM25)[I_TEST]`; `slices = {l: (pq_f[q_lang[I_TEST]==l].mean(), pq_b[q_lang[I_TEST]==l].mean()) for l in ('es','en','code')}`."))
    nb.code(r'''
def evalua_test(svc) -> dict:
    """Devuelve {"final", "bm25", "delta_bm25" (paired_bootstrap), "slices": {lang: (final, bm25)}}."""
    # TODO 5
    raise NotImplementedError("TODO 5: evalua_test")

corre(test_evaluacion)
''')
    nb.md("## 6. Informe técnico (TODO 6)\nGenera el Markdown **desde `RES`** (nada de números a mano) con las secciones: *Decisiones*, *Resultados en test ciego*, *Costes y latencia*, *Criterios de aceptación* (tabla con ✅/❌ por cada criterio de `ACEPTACION`) y *Limitaciones*. Guárdalo en `poliglota_informe.md` y la config en `poliglota_config.json`.")
    nb.md(hint("Calcula primero un `dict` `checks` criterio → bool con los mismos umbrales del texto de `ACEPTACION`, luego formatea la tabla con un `join`.",
               "Coste: `1e7 * 400 / 1e6 * 0.02`; `checks['calidad_vs_bm25'] = e['final'] >= e['bm25'] and e['delta_bm25']['ci_low'] > -0.03`; `open('poliglota_informe.md','w').write(md)`; `json.dump(RES['config'], open('poliglota_config.json','w'))`."))
    nb.code(r'''
def genera_informe() -> str:
    # TODO 6
    raise NotImplementedError("TODO 6: genera_informe")

corre(test_informe)
''')
    nb.code("puntos = rubrica_final()")

    # ── SPOILER
    nb.md("---\n## ⛔ SPOILER — intenta resolverlo primero\nSolución de referencia: el procedimiento de la lección 20 empaquetado en funciones. Ejecutarla redefine tus funciones y vuelve a pasar la rúbrica final.")
    nb.code(r'''
def informe_tokenizer(V: int = 4000) -> pd.DataFrame:
    tk = entrena_bpe(doc_texts, V); filas = []
    for l in ("es", "en", "code"):
        tx = [d["text"] for d in docs if d["lang"] == l]; n_tok = sum(len(tk.encode(t).ids) for t in tx)
        filas.append({"lang": l, "fertilidad": n_tok / sum(len(t.split()) for t in tx), "bytes_por_token": sum(len(t.encode()) for t in tx) / n_tok})
    return pd.DataFrame(filas)

def elige_configuracion() -> dict:
    dv = lambda cfg: pq_S(scores_de(cfg))[I_DEV]
    cfg = dict(analizador="palabras", modelo="v2", dim=EMB["v2"]["D"].shape[1], precision="float32", fusion="bm25", alfa=0.5, ef_search=128)
    cfg["analizador"] = max(ANALIZADORES, key=lambda a: dv({**cfg, "analizador": a}).mean())
    r = paired_bootstrap(dv({**cfg, "fusion": "denso", "modelo": "v2", "dim": EMB["v2"]["D"].shape[1]}),
                         dv({**cfg, "fusion": "denso", "modelo": "v1", "dim": EMB["v1"]["D"].shape[1]}))
    cfg["modelo"] = "v2" if r["ci_low"] > 0 else "v1"
    full = EMB[cfg["modelo"]]["D"].shape[1]
    dims = [d for d in (16, 32, 48, 64, 96, 128, 256, 384, 512, 768, 1024) if d <= full]
    nd_d = {d: dv({**cfg, "fusion": "denso", "dim": d}).mean() for d in dims}
    cfg["dim"] = min(d for d in dims if nd_d[d] >= nd_d[full] - 0.01)
    cfg["precision"] = "int8" if dv({**cfg, "fusion": "denso", "precision": "int8"}).mean() >= nd_d[cfg["dim"]] - 0.01 else "float32"
    alfas = np.linspace(0, 1, 21); PQa = np.array([dv({**cfg, "fusion": "lineal", "alfa": a}) for a in alfas])
    lin_cv = np.zeros(len(I_DEV))
    for f in np.array_split(np.random.default_rng(SEED).permutation(len(I_DEV)), 5):
        tr = np.setdiff1d(np.arange(len(I_DEV)), f); lin_cv[f] = PQa[PQa[:, tr].mean(1).argmax(), f]
    r = paired_bootstrap(lin_cv, dv({**cfg, "fusion": "rrf"}))
    cfg["fusion"] = "lineal" if r["ci_low"] > 0 else "rrf"; cfg["alfa"] = float(alfas[PQa.mean(1).argmax()])
    return cfg

def verifica_indice(config: dict, N: int = 20_000) -> dict:
    D, Q = vectores_de(config); d = D.shape[1]; rng = np.random.default_rng(SEED)
    base = D[rng.integers(0, len(D), N)]; X = l2n(base + 0.35 * rng.normal(size=base.shape).astype(np.float32) / np.sqrt(d))
    Qd = Q[I_DEV]; flat = faiss.IndexFlatIP(d); flat.add(X); gt = flat.search(Qd, 10)[1]
    h = faiss.IndexHNSWFlat(d, 32, faiss.METRIC_INNER_PRODUCT); h.hnsw.efConstruction = 80; h.add(X)
    got = h.search(Qd, 10, params=faiss.SearchParametersHNSW(efSearch=config["ef_search"]))[1]
    bpv = d * (1 if config["precision"] == "int8" else 4)
    return {"recall": float(np.mean([len(set(a) & set(b)) / 10 for a, b in zip(gt, got)])), "ram_10M_gb": 1e7 * (bpv + 256) / 1e9}

def _servicio(config):
    f = ANALIZADORES[config["analizador"]]; bm = BM25().fit([f(t) for t in doc_texts], doc_ids)
    fus = config["fusion"] if config["fusion"] in ("rrf", "lineal") else "rrf"
    s = ServicioPoliglota(docs, bm, cache_cap=1024, tokenizador=f, fusion=fus, alfa=config["alfa"])
    D, _ = vectores_de(config); v = f"{config['modelo']}-d{config['dim']}-{config['precision']}"
    s.registrar_version(v, EmbedderRecortado(VERS[config["modelo"]], config["dim"]), D, indice="hnsw", ef_search=config["ef_search"])
    s.alias["prod"] = v
    return s

MODO = lambda config: "hibrido" if config["fusion"] in ("rrf", "lineal") else config["fusion"]

def monta_servicio(config: dict):
    s = _servicio(config)
    for t in q_texts: s.buscar(t, k=10, modo=MODO(config))
    lat = np.array(s.lat_ms)
    z = _servicio(config)
    for t in trafico_zipf(5000, UNIVERSO): z.buscar(t, k=10, modo=MODO(config))
    s.cache = LRUCache(1024); s.lat_ms = []           # el servicio a evaluar arranca limpio
    return s, {"p50_frio": float(np.percentile(lat, 50)), "p99_frio": float(np.percentile(lat, 99)), "hit_rate": z.cache.hit_rate}

def evalua_test(svc) -> dict:
    modo = MODO(RES["config"])
    pq_f = np.array([ndcg_at_k([d for d, _ in svc.buscar(q_texts[i], k=10, modo=modo)], qrels[qids[i]], 10) for i in I_TEST])
    pq_b = pq_S(S_BM25)[I_TEST]; lt = q_lang[I_TEST]
    return {"final": float(pq_f.mean()), "bm25": float(pq_b.mean()), "delta_bm25": paired_bootstrap(pq_f, pq_b),
            "slices": {l: (float(pq_f[lt == l].mean()), float(pq_b[lt == l].mean())) for l in ("es", "en", "code")}, "pq": pq_f, "pq_bm25": pq_b}

def genera_informe() -> str:
    c, e = RES["config"], RES["eval"]; coste = 1e7 * 400 / 1e6 * 0.02
    checks = {"calidad_vs_bm25": e["final"] >= e["bm25"] and e["delta_bm25"]["ci_low"] > -0.03,
              "peor_slice": all(f >= b - 0.05 for f, b in e["slices"].values()), "recall_ann": RES["recall_ann"] >= 0.95,
              "latencia_p99_ms": RES["p99_frio"] <= 50, "ram_10M_gb": RES["ram_10M_gb"] <= 16, "coste_reembed_usd": coste <= 500,
              "hit_rate": RES["hit_rate"] >= 0.70}
    filas = "\n".join(f"| {k} | {ACEPTACION[k]} | {'✅' if ok else '❌'} |" for k, ok in checks.items())
    tok = RES["tok"].set_index("lang")
    md = f"""# Políglota v1.0 · Informe técnico (proyecto)
Fuente: {corpus['source']} · dev {len(I_DEV)} / test ciego {len(I_TEST)} queries · semilla {SEED}

## Decisiones (solo dev)
`{json.dumps(c, ensure_ascii=False)}` · nDCG@10 en dev de la configuración: {RES['dev_config']:.3f}.
Fertilidad BPE 4k: es {tok.loc['es', 'fertilidad']:.2f} · en {tok.loc['en', 'fertilidad']:.2f} · code {tok.loc['code', 'fertilidad']:.2f} tokens/palabra.

## Resultados en test ciego
Servicio {e['final']:.3f} vs BM25 {e['bm25']:.3f} · Δ = {e['delta_bm25']['diff']:+.3f} (IC95 [{e['delta_bm25']['ci_low']:+.3f}, {e['delta_bm25']['ci_high']:+.3f}]) ·
por idioma (servicio/BM25): {', '.join(f'{l} {f:.3f}/{b:.3f}' for l, (f, b) in e['slices'].items())}.

## Costes y latencia
Re-embedding 10 M × 400 tokens: {coste:.0f} $ (API 0.02 $/1M, oct-2026) · RAM índice 10 M: {RES['ram_10M_gb']:.1f} GB · p50/p99 frío {RES['p50_frio']:.1f}/{RES['p99_frio']:.1f} ms (CPU) · hit rate {RES['hit_rate']:.2f} · recall ANN {RES['recall_ann']:.3f}.

## Criterios de aceptación
| Criterio | Umbral | OK |
|---|---|---|
{filas}

## Limitaciones
* {len(I_TEST)} queries de test: IC anchos; ampliar el golden set por slice con tráfico real.
* {'Corpus sintético y embedders fallback: repetir con datos y modelos reales.' if corpus['source'] == 'synthetic' else 'Validar online con interleaving antes del A/B.'}
* Latencia medida en CPU sin red: re-medir en el despliegue real.
"""
    open("poliglota_informe.md", "w", encoding="utf-8").write(md)
    json.dump({k: (v.item() if hasattr(v, "item") else v) for k, v in c.items()}, open("poliglota_config.json", "w"), ensure_ascii=False, indent=1)
    return md
''')
    nb.code(r'''
puntos = rubrica_final()
from IPython.display import Markdown, display
display(Markdown(RES["informe"]))
''')
    nb.code(r'''
# Figura final: nDCG@10 por idioma en test (servicio vs BM25) con IC95 global
e = RES["eval"]; fig, ax = plt.subplots(figsize=(8, 3.8)); x = np.arange(4); w = .38
for j, (nombre, pq, c) in enumerate((("BM25 (módulo 00)", e["pq_bm25"], GRIS), ("Políglota v1.0", e["pq"], AZUL))):
    lt = q_lang[I_TEST]; vals = [pq.mean()] + [pq[lt == l].mean() for l in ("es", "en", "code")]; ci = bootstrap_ci(pq)
    ax.bar(x + (j - .5) * w, vals, w, color=c, label=nombre)
    ax.errorbar(x[0] + (j - .5) * w, vals[0], yerr=[[vals[0] - ci[1]], [ci[2] - vals[0]]], color="k", capsize=3)
ax.set_xticks(x); ax.set_xticklabels(["global (IC95)", "es", "en", "code"]); ax.set_ylabel("nDCG@10 (test ciego)"); ax.set_ylim(0, 1.05)
ax.set_title("Políglota v1.0 en test ciego"); ax.legend(); plt.tight_layout(); plt.show()
''')
    nb.md(r"""> 👀 **Qué debes observar:** el global con su IC y, sobre todo, el slice que más se mueve. Si el IC global incluye el 0, el informe debe decir «no peor que BM25, mejora no demostrada»: es una conclusión válida para lanzar una beta con interleaving, no para anunciar una mejora.

## 🚀 Retos extra
1. **Modelos reales**: con `FAST_DEV_RUN=False` en una T4, repite con `multilingual-e5-small/base` (o tu embedder del módulo 11) y compara las decisiones con las del fallback. ¿Cambia la fusión elegida?
2. **Reranker** (módulo 13): añade un cross-encoder sobre el top-20 y extiende `ACEPTACION` con su latencia.
3. **Multimodal** (módulo 16): añade el retriever visual del proyecto 16 como tercera lista en la RRF y un slice «capturas» al informe.
4. **Migración** (módulo 18): publica `v2-d…` junto a la versión actual, ajusta un adaptador y escribe en el informe el plan blue/green con costes.
5. **Interleaving** (módulo 18): simula clics con los qrels de test y compara tu servicio con BM25 por potencia.
6. **Robustez** (módulos 01 y 05): pasa las queries de test por el fuzzer del proyecto 05 (ZWSP, NFD, homoglifos, mayúsculas) y comprueba la invariante «mismo top-10 que la query limpia». Añade a `ACEPTACION` un criterio de estabilidad (p. ej. ≥ 95 % de queries con el mismo top-10).
7. **Privacidad** (módulos 17 y 18): añade a *Limitaciones* el riesgo de inversión de embeddings y las medidas del módulo 18 (control de acceso al índice, borrado propagado, sin texto de queries en logs).

## 🤔 Reflexión (5 pts)
1. ¿Qué decisión de tu configuración es la **más frágil** (la que más podría cambiar con datos reales) y qué medirías primero en la beta?
2. Si un criterio sale ❌, ¿lanzarías igualmente? Argumenta con el impacto y con el plan de mitigación.
3. ¿Qué parte del curso cambió más tu forma de **evaluar** un sistema de retrieval, y qué harías distinto en tu trabajo actual?
""")


README = r"""# Módulo 20 · Capstone: Políglota completo

**Nivel:** 🔴 Experto · **Duración:** ≈ 6 h (lección ≈ 2.5 h + proyecto ≈ 3.5 h) · **Cómputo:** CPU en `FAST_DEV_RUN` (≈ 1 min cada notebook); T4/L4 con modelos reales

| Archivo | Contenido |
|---|---|
| [`20_capstone.ipynb`](20_capstone.ipynb) | Lección = **solución de referencia del sistema completo**: criterios de aceptación fijados antes · split dev / test ciego estratificado · tokenizer BPE byte-level (HF `tokenizers`) con fertilidad y bytes/token por idioma y prueba como analizador de BM25 · elección del analizador léxico (palabras + identificadores) · embedder (test pareado v1/v2, dimensión recortada, int8) · fusión RRF vs lineal con CV y la misma normalización que el servicio · índice HNSW vs Flat (recall/latencia con N = 20 000, RAM a 10 M) · `ServicioPoliglota` del módulo 18 con la config elegida (latencia fría/caliente, hit rate Zipf) · evaluación única en test ciego vs BM25 del módulo 00 con IC pareado y slices · **informe técnico generado** (`poliglota_informe.md`, `poliglota_config.json`) con la tabla de criterios · extensión multimodal opcional |
| [`20_proyecto_capstone.ipynb`](20_proyecto_capstone.ipynb) | Proyecto final: 6 TODOs (informe del tokenizer, decisiones solo en dev, verificación del índice, servicio, evaluación en test, informe), pistas 🪜, **rúbrica final de 100 puntos** calibrada con la solución y solución tras ⛔ SPOILER |
| `assets/` | Recursos de Gemini: `M20-IMG-01.png`, `M20-IMG-02.png`, `M20-VID-01.mp4` |

## Objetivos
1. Fijar criterios de aceptación medibles antes de construir.
2. Integrar tokenizer, analizador, embedder, fusión, índice y servicio.
3. Decidir cada componente en dev con reglas explícitas; evaluar una vez en test ciego.
4. Proyectar memoria, coste y latencia a 10 M de chunks.
5. Generar un informe técnico de decisiones desde las métricas.

## Piezas integradas (todas reutilizadas)
`carga_corpus`, métricas y BM25 (módulo 00) · BPE con HF `tokenizers` (02–03) · fertilidad y paridad (04) · embedders con fallback (12) · RRF y combinación lineal (13) · FAISS HNSW/Flat (14) · `bootstrap_ci`/`paired_bootstrap` (15) · ColPali/visual opcional (16) · `ServicioPoliglota`, caché versionada, alias (18) · árboles de decisión y trampas de evaluación (19).

## Estado de pruebas (entorno de autoría, oct-2026)
Lección (≈ 30 s) y proyecto ejecutados completos con `nbclient` en CPU con el corpus **sintético** + stdlib y los **fallbacks** TF-IDF+SVD (Hugging Face bloqueado). Con esa ejecución la regla elige v1 (la diferencia v2−v1 en dev no excluye el 0), d = 48, int8, fusión lineal y HNSW con efSearch = 128, y se cumplen los 7 criterios. **No se pudo probar:** modelos reales del hub, datos reales de Wikipedia/CodeSearchNet, GPU, la extensión multimodal con modelos reales.

## Enlaces
Anterior: [19 · Playbook de élite](../19_playbook_elite/) · Material de cierre: [`extras/GUIA_ENTREVISTAS.md`](../extras/GUIA_ENTREVISTAS.md) · [`extras/LECTURA_PAPERS.md`](../extras/LECTURA_PAPERS.md)

*Notebooks generados con `python tokenization-embeddings-course/_tools/builders/build_20.py` (desde la raíz del repo).*
"""
