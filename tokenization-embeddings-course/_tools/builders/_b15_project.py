"""Proyecto 15 · Banco de evaluación de Políglota (plantilla con TODOs + solución tras SPOILER)."""
from _a6_common import SYNTH_DATA_SRC, CORPUS_SRC, REAL_SRC
from _a6_src15 import METRICS_SRC, STATS_SRC, RETRIEVERS_SRC

# Valores medidos por la solución de referencia (FAST_DEV_RUN=True, corpus sintético, semilla 42) -> calibran la rúbrica.
REF = {
    "bm25": 0.531, "lsi": 0.589, "rrf": 0.519,
    "ci_ancho_bm25": 0.178, "diff_lsi_bm25": 0.058, "code_bm25": 0.094, "code_tokfix": 0.253,
}

GIVEN_PRE = r'''
import math
def _dedup(ranked_ids):
    seen, out = set(), []
    for d in ranked_ids:
        if d not in seen:
            seen.add(d); out.append(d)
    return out

def rank_from_scores(scores, doc_ids, k=None):
    """(Dado) Orden por score desc; empates -> orden del corpus. Determinista."""
    scores = np.asarray(scores, dtype=float)
    order = np.lexsort((np.arange(len(scores)), -scores))
    return [doc_ids[i] for i in (order[:k] if k else order)]
'''.strip("\n")

EVALPQ = r'''
def evaluate_per_query(run: dict, qrels: dict, k: int = 10, metrics=("ndcg", "recall", "mrr")) -> dict:
    """(Dado) Devuelve {"qids": [...], metric: np.ndarray}. Excluye queries sin relevantes; query sin ranking = 0."""
    fns = {"ndcg": ndcg_at_k, "recall": recall_at_k, "mrr": mrr_at_k}
    qids = [q for q, rels in qrels.items() if any(r > 0 for r in rels.values())]
    out = {"qids": qids}
    for m in metrics:
        out[m] = np.array([fns[m](run.get(q, []), qrels[q], k) for q in qids])
    return out
'''.strip("\n")


def hint(n1: str, n2: str) -> str:
    return f"""
    <details><summary>🪜 Pista 1 (la idea)</summary>

    {n1}
    </details>

    <details><summary>🪜 Pista 2 (casi la API)</summary>

    {n2}
    </details>
    """


def build(nb):
    nb.md(f"""
    {nb.badge()}

    # Proyecto 15 · Banco de evaluación de Políglota

    | | |
    |---|---|
    | **Nivel** | 🟠 Avanzado |
    | **Duración estimada** | ≈ 2 h |
    | **GPU recomendada** | No necesaria (CPU, `FAST_DEV_RUN = True`) |
    | **Prerrequisitos** | Lección 15 (métricas, bootstrap, tests pareados, análisis de errores) |
    | **Conecta con** | Módulo 13 (híbrido: el RRF que evaluarás) · Módulo 14 (el índice que evaluarás después) · Módulo 18 (monitorización y A/B) |

    ## 🏢 Contexto de negocio
    Eres ML engineer en **Políglota Labs**. La CTO pregunta: *«El prototipo híbrido (BM25 + denso con RRF), ¿es mejor que BM25 solo? ¿Y mejor que el denso solo? No quiero decidirlo con un solo número.»*
    El equipo ha dejado de confiar en las evaluaciones ad hoc de notebooks sueltos. Tu entregable es un **banco de evaluación reutilizable** (`poliglota_eval`) y un **informe** con intervalos de confianza y análisis de errores que sirva para decidir.

    ## 📦 Dataset
    Corpus Políglota (`carga_corpus`: Wikipedia ES/EN + CodeSearchNet vía Hugging Face; si no hay red, **corpus sintético** con el mismo esquema y huecos léxicos a propósito).
    Las rúbricas numéricas están **calibradas con el corpus sintético y `FAST_DEV_RUN=True`** (semilla 42, determinista). Con datos reales el notebook imprime tus valores y solo exige los chequeos estructurales.

    ## 🎯 Entregables y criterios de evaluación
    | # | Entregable | Criterio objetivo |
    |---|---|---|
    | 1 | `dcg/ndcg/recall/mrr` correctos | Pasan los 9 grupos de tests (empates, duplicados, graduadas, sin relevantes…) |
    | 2 | Golden set con split dev / **test ciego** estratificado y κ | dev ∩ test = ∅; mismas proporciones por idioma (±1 query); κ calculado |
    | 3 | 3 sistemas evaluados (BM25, LSI, RRF) | nDCG@10 de cada uno ≈ valor de referencia (± 0.01) |
    | 4 | Estadística correcta | IC bootstrap con ancho dentro de rango; test pareado + Holm; decisión explícita |
    | 5 | Análisis de errores | slice por idioma con la fila `code` identificada como peor; hipótesis de tokenización contrastada con IC |
    | 6 | Informe (3 decisiones) | Respuesta a la CTO que cite IC y diferencia pareada |
    """)

    nb.md("## 0. Preparación (celdas dadas)")
    nb.code("!pip install -q numpy scipy scikit-learn matplotlib pandas datasets ranx")
    nb.code(r'''
    import os, re, math, random, time, warnings
    import numpy as np, pandas as pd
    import matplotlib.pyplot as plt
    warnings.filterwarnings("ignore")
    SEED, FAST_DEV_RUN = 42, True
    random.seed(SEED); np.random.seed(SEED)
    AZUL, NARANJA, VERDE, GRIS, ROJO = "#1F6FEB", "#F28E2B", "#2CA02C", "#6B7280", "#D62728"
    plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": .25})
    ''')
    nb.code(SYNTH_DATA_SRC)
    nb.code(CORPUS_SRC)
    nb.code(REAL_SRC)
    nb.code(r'''
    corpus = carga_corpus(fast_dev=FAST_DEV_RUN)
    docs, queries, qrels = corpus["docs"], corpus["queries"], corpus["qrels"]
    doc_ids, doc_texts = [d["id"] for d in docs], [d["text"] for d in docs]
    q_lang = {q["qid"]: q["lang"] for q in queries}; q_text = {q["qid"]: q["text"] for q in queries}
    print(corpus["source"], len(docs), "docs", len(queries), "queries")
    ''')
    nb.md("## 1. Métricas canónicas (TODO 1)\nImplementa las cuatro funciones. Reglas: ganancia lineal; descuento $1/\\log_2(i+1)$; **dedup** del ranking; relevante ⇔ `rel > 0`; sin relevantes → `0.0`; `recall` divide por **todos** los relevantes juzgados; `mrr@k` es 0 si el primer relevante está más allá de $k$.\n" + "(`_dedup` y `rank_from_scores` te los damos.)")
    nb.code(GIVEN_PRE)
    nb.md(hint(
        "Para nDCG necesitas DCG del ranking (tras `_dedup` y cortar a `k`) y DCG ideal (relevancias positivas ordenadas de mayor a menor, cortadas a `k`). Una función auxiliar interna `_dcg(lista_de_ganancias)` evita repetir código.",
        "`ideal = sorted((r for r in rels.values() if r > 0), reverse=True)[:k]`; `dcg = sum(rels.get(d,0)/math.log2(i+2) for i,d in enumerate(_dedup(ranked)[:k]))` (posición 0 → `log2(2)=1`). Recall: `len(set(relevantes) & set(_dedup(ranked)[:k])) / len(relevantes)`."))
    nb.code(r'''
    def dcg_at_k(ranked_ids, rels: dict, k: int = 10) -> float:
        """DCG@k con ganancia lineal. rels: doc_id -> relevancia (>0 relevante)."""
        # TODO 1a: suma de rel / log2(posición + 1) sobre el top-k SIN duplicados (solo docs con rel > 0)
        raise NotImplementedError("TODO 1a: dcg_at_k")

    def ndcg_at_k(ranked_ids, rels: dict, k: int = 10) -> float:
        """nDCG@k = DCG / IDCG. Sin relevantes -> 0.0."""
        # TODO 1b: IDCG con las mejores relevancias; cuidado con IDCG == 0
        raise NotImplementedError("TODO 1b: ndcg_at_k")

    def recall_at_k(ranked_ids, rels: dict, k: int = 10) -> float:
        """|relevantes en top-k| / |relevantes|. Sin relevantes -> 0.0."""
        # TODO 1c
        raise NotImplementedError("TODO 1c: recall_at_k")

    def mrr_at_k(ranked_ids, rels: dict, k: int = 10) -> float:
        """1/rango del primer relevante en el top-k; 0 si no hay."""
        # TODO 1d
        raise NotImplementedError("TODO 1d: mrr_at_k")
    ''')
    nb.code(r'''
    def test_metricas():
        close = lambda a, b: abs(a - b) < 1e-9
        ranked = ["d3", "d1", "d9", "d2", "d7"]; rels = {"d1": 3, "d2": 2, "d5": 1}
        dcg = 3 / math.log2(3) + 2 / math.log2(5); idcg = 3 + 2 / math.log2(3) + 1 / math.log2(4)
        assert close(ndcg_at_k(ranked, rels, 5), dcg / idcg), "nDCG a mano (ejemplo de la lección)"
        assert close(ndcg_at_k(["d1", "d2", "d5", "x"], rels, 10), 1.0), "ranking ideal => 1"
        assert ndcg_at_k(["x", "d1", "d2", "d5"], rels, 10) < 1.0
        assert ndcg_at_k(ranked, {}, 10) == recall_at_k(ranked, {}, 10) == mrr_at_k(ranked, {}, 10) == 0.0, "sin relevantes -> 0.0"
        assert close(ndcg_at_k(["d1", "d1", "d1"], {"d1": 1, "d2": 1}, 10), ndcg_at_k(["d1"], {"d1": 1, "d2": 1}, 10)), "duplicados"
        assert recall_at_k(["d1", "d1"], {"d1": 1, "d2": 1}, 10) == 0.5, "duplicados en recall"
        assert close(recall_at_k(["d1"], {"d1": 1}, 100), 1.0) and mrr_at_k(["x", "d1"], {"d1": 1}, 1) == 0.0, "k grande / k=1"
        assert ndcg_at_k(["d1", "d2"], rels, 2) > ndcg_at_k(["d2", "d1"], rels, 2), "relevancia graduada"
        assert all(recall_at_k(ranked, rels, k) <= recall_at_k(ranked, rels, k + 1) for k in range(1, 6)), "recall monótona"
        assert recall_at_k(["d1"], {"d1": 0, "d2": 1}, 5) == 0.0, "rel=0 no es relevante"
        assert close(mrr_at_k(["x", "y", "d2"], rels, 10), 1 / 3)
        ids = ["a", "b", "c", "d"]; sc = np.array([1., 2., 2., 2.]); assert rank_from_scores(sc, ids) == ["b", "c", "d", "a"]
        return "✅ test_metricas OK"

    def corre(f):
        """Ejecuta un chequeo sin romper 'ejecutar todo' si el TODO está pendiente."""
        try: print(f())
        except NotImplementedError as e: print(f"⏳ pendiente: {e}")
        except AssertionError as e: print(f"❌ falló: {e}")
        except Exception as e: print(f"❌ {type(e).__name__}: {e}")
    corre(test_metricas)
    ''')
    nb.code(EVALPQ)

    nb.md("## 2. Golden set: split estratificado y acuerdo entre anotadores (TODO 2)\nReserva el **30 % de las queries como test ciego**, estratificado por idioma (cada idioma contribuye `round(30 % del grupo)` queries al test; usa `random.Random(seed)`, ordena los idiomas alfabéticamente y baraja cada grupo antes de cortar). Implementa también κ de Cohen.")
    nb.md(hint(
        "Agrupa por `q['lang']`, baraja cada grupo con un `random.Random(seed)` y corta en `int(round(len(grupo) * frac_test))`. κ = (p_o − p_e)/(1 − p_e) con p_e = Σ_l P(a=l)·P(b=l).",
        "`for lang in sorted({q['lang'] for q in queries}): grp=[q for q in queries if q['lang']==lang]; rng.shuffle(grp); cut=int(round(len(grp)*frac_test)); test+=grp[:cut]; dev+=grp[cut:]`. Para κ: `labs=np.unique(np.concatenate([a,b]))`."))
    nb.code(r'''
    def split_estratificado(queries, frac_test: float = 0.3, seed: int = SEED):
        """Devuelve (dev, test). Estratificado por idioma. Determinista."""
        # TODO 2a
        raise NotImplementedError("TODO 2a: split_estratificado")

    def cohen_kappa(a, b) -> float:
        """κ de Cohen entre dos anotadores (listas de etiquetas)."""
        # TODO 2b
        raise NotImplementedError("TODO 2b: cohen_kappa")

    def test_golden():
        dev, test = split_estratificado(queries)
        assert not ({q["qid"] for q in dev} & {q["qid"] for q in test}), "dev y test se solapan"
        assert len(dev) + len(test) == len(queries)
        for lang in {q["lang"] for q in queries}:
            n, nt = sum(q["lang"] == lang for q in queries), sum(q["lang"] == lang for q in test)
            assert abs(nt - round(0.3 * n)) <= 1, f"proporción de test en {lang}: {nt}/{n}"
        assert [q["qid"] for q in split_estratificado(queries)[1]] == [q["qid"] for q in test], "debe ser determinista"
        assert abs(cohen_kappa([1, 1, 0, 0], [1, 1, 0, 0]) - 1) < 1e-12 and abs(cohen_kappa([1, 0, 1, 0], [0, 1, 0, 1]) + 1) < 1e-12
        a, b = [1] * 50 + [0] * 50, [1] * 45 + [0] * 5 + [1] * 5 + [0] * 45   # acuerdo 90 %, p_e = 0.5 -> κ = 0.8
        assert abs(cohen_kappa(a, b) - 0.8) < 1e-9, "κ de Cohen"
        return "✅ test_golden OK"
    corre(test_golden)
    ''')

    nb.md("## 3. Sistemas a evaluar (dados) + fusión RRF (TODO 3)\nBM25 y LSI (TF-IDF + SVD) te los damos. Implementa la **fusión RRF** (módulo 13): $\\sum_r 1/(k+\\text{rango}_r)$ con $k=60$, rangos desde 1, empates por orden del corpus.")
    nb.code(RETRIEVERS_SRC.replace("def rrf_scores(score_lists, k: int = 60) -> np.ndarray:", "def _rrf_dado(score_lists, k: int = 60) -> np.ndarray:"))
    nb.md(hint("Para cada lista de scores obtén el orden (desc., desempate por posición) y suma `1/(k + rango)` en la posición de cada documento.",
               "`order = np.lexsort((np.arange(len(s)), -np.asarray(s)))`; `out[order] += 1.0 / (k + np.arange(len(s)) + 1)`."))
    nb.code(r'''
    def rrf_scores(score_lists, k: int = 60) -> np.ndarray:
        """Reciprocal Rank Fusion de varias listas de scores alineadas con doc_ids."""
        # TODO 3
        raise NotImplementedError("TODO 3: rrf_scores")

    def test_rrf():
        s1, s2 = np.array([3., 2., 1.]), np.array([1., 3., 2.])
        esperado = np.array([1/61 + 1/63, 1/62 + 1/61, 1/63 + 1/62])
        assert np.allclose(rrf_scores([s1, s2]), esperado), "RRF con k=60"
        return "✅ test_rrf OK"
    corre(test_rrf)
    ''')
    nb.code(r'''
    bm25 = BM25(tok_simple).fit(doc_texts, doc_ids); lsi = LSI(dim=48, seed=SEED).fit(doc_texts, doc_ids)
    def construye_runs():
        sis = {"BM25": bm25.scores, "LSI-48": lsi.scores, "RRF": lambda q: rrf_scores([bm25.scores(q), lsi.scores(q)])}
        return {n: build_run(f, queries, doc_ids, topn=100) for n, f in sis.items()}
    try:
        RUNS = construye_runs(); PER = {n: evaluate_per_query(r, qrels, 10) for n, r in RUNS.items()}
        print({n: round(float(p["ndcg"].mean()), 3) for n, p in PER.items()})
    except NotImplementedError as e:
        RUNS = PER = None; print("⏳ pendiente:", e)
    ''')

    nb.md("## 4. Estadística (TODO 4)\nLa unidad de remuestreo es la **query**. Implementa: IC percentil por bootstrap, test **pareado** por bootstrap (IC de la diferencia + p-valor por *shift*) y corrección de Holm.")
    nb.md(hint("Bootstrap: genera índices con `rng.integers(0, n, size=(B, n))`, calcula la media de cada remuestreo y toma los cuantiles. Pareado: trabaja con `d = a - b`; para el p-valor centra `d` (resta su media), remuestrea y cuenta cuántos |medias| superan |media observada|. Holm: ordena p ascendente; ajustado_i = max(ajustado_{i-1}, (m−i)·p_i) acotado a 1.",
               "`idx = np.random.default_rng(seed).integers(0, len(v), (n_boot, len(v)))`; `means = v[idx].mean(1)`; p = `(np.sum(np.abs(null) >= abs(d.mean())) + 1) / (n_boot + 1)`; en Holm `running = max(running, min(1, (m - i) * p))` con `i` desde 0."))
    nb.code(r'''
    def bootstrap_ci(values, n_boot: int = 2000, alpha: float = 0.05, seed: int = 42):
        """(media, bajo, alto) con IC percentil remuestreando QUERIES."""
        # TODO 4a
        raise NotImplementedError("TODO 4a: bootstrap_ci")

    def paired_bootstrap(a, b, n_boot: int = 10000, alpha: float = 0.05, seed: int = 42) -> dict:
        """{'diff','ci_low','ci_high','p_value'} para a - b sobre las MISMAS queries (p bilateral por shift)."""
        # TODO 4b
        raise NotImplementedError("TODO 4b: paired_bootstrap")

    def holm(pvalues: dict, alpha: float = 0.05) -> dict:
        """{nombre: (p_ajustado, rechaza_H0)} con Holm-Bonferroni."""
        # TODO 4c
        raise NotImplementedError("TODO 4c: holm")

    def test_stats():
        v = np.array([0., .2, .4, .6, .8, 1.0] * 10)
        m, lo, hi = bootstrap_ci(v); assert lo < m < hi and abs(m - v.mean()) < 1e-12 and 0.05 < hi - lo < 0.3, "IC percentil"
        assert bootstrap_ci(np.ones(30)) == (1.0, 1.0, 1.0), "varianza 0 -> IC de ancho 0"
        r = paired_bootstrap(v, v); assert r["diff"] == 0 and r["p_value"] > 0.9, "A vs A no es significativo"
        r = paired_bootstrap(v + .1, v); assert abs(r["diff"] - .1) < 1e-12 and r["p_value"] < 0.01 and r["ci_low"] > 0.09, "diferencia constante"
        h = holm({"a": .01, "b": .04, "c": .03}); assert abs(h["a"][0] - .03) < 1e-12 and abs(h["c"][0] - .06) < 1e-12 and abs(h["b"][0] - .06) < 1e-12
        assert [h[k][1] for k in "abc"] == [True, False, False], "Holm: solo 'a' sobrevive"
        return "✅ test_stats OK"
    corre(test_stats)
    ''')
    nb.code(r'''
    RES = {}
    try:
        RES["ndcg10"] = {n: bootstrap_ci(p["ndcg"]) for n, p in PER.items()}
        pares = [("LSI-48", "BM25"), ("RRF", "BM25"), ("RRF", "LSI-48")]
        tests = {f"{a} vs {b}": paired_bootstrap(PER[a]["ndcg"], PER[b]["ndcg"]) for a, b in pares}
        adj = holm({k: v["p_value"] for k, v in tests.items()})
        RES["tests"], RES["holm"] = tests, adj
        for k, v in tests.items(): print(f"{k:16s} Δ={v['diff']:+.3f} IC95[{v['ci_low']:+.3f},{v['ci_high']:+.3f}] p={v['p_value']:.4f} p_Holm={adj[k][0]:.4f} {'✅ sig.' if adj[k][1] else '— no sig.'}")
        print({n: tuple(round(x, 3) for x in v) for n, v in RES["ndcg10"].items()})
    except (NotImplementedError, TypeError, NameError, AttributeError, KeyError) as e:
        print("⏳ pendiente (completa TODOs 1–4):", type(e).__name__)
    ''')

    nb.md("## 5. Golden set versionado y reparto (usa tu TODO 2)")
    nb.code(r'''
    try:
        dev_q, test_q = split_estratificado(queries)
        RES["n_dev"], RES["n_test"] = len(dev_q), len(test_q)
        rng = np.random.default_rng(SEED); verdad = rng.integers(0, 2, 300)
        a1 = np.where(rng.random(300) < .90, verdad, 1 - verdad); a2 = np.where(rng.random(300) < .90, verdad, 1 - verdad)
        RES["kappa"] = cohen_kappa(a1, a2); print(f"dev={len(dev_q)} test={len(test_q)} κ(dos anotadores 90 %)={RES['kappa']:.2f}")
    except NotImplementedError as e:
        print("⏳ pendiente:", e)
    ''')

    nb.md("""
    ## 6. Análisis de errores (TODO 5)
    1. Construye una tabla **nDCG@10 por idioma × sistema** y localiza el slice más débil.
    2. Lee las 5 peores queries de BM25 y formula una **hipótesis de causa**.
    3. Contrasta la hipótesis: ¿mejora BM25 con `tok_code` (parte `snake_case`) en el slice de código? Cuantifícalo con un **IC pareado** y deja el resultado en `RES`.
    """)
    nb.md(hint("Primero un DataFrame con una fila por query (`qid`, `lang`, una columna por sistema) y `groupby('lang').mean()`. La hipótesis sale de mirar `q_text` y los documentos relevantes de las peores queries: ¿qué palabra de la query *no* aparece como token en el documento?",
               "`bm25_tc = BM25(tok_code).fit(doc_texts, doc_ids)`; `run_tc = build_run(bm25_tc.scores, queries, doc_ids, 100)`; `per_tc = evaluate_per_query(run_tc, qrels, 10)`; máscara `mask = np.array([q_lang[q]=='code' for q in PER['BM25']['qids']])` y `paired_bootstrap(per_tc['ndcg'][mask], PER['BM25']['ndcg'][mask])`."))
    nb.code(r'''
    def slice_table(per, qids, q_lang, sistemas):
        """DataFrame idioma × sistema con el nDCG@10 medio. `per[sistema]['ndcg']` está alineado con `qids`."""
        # TODO 5a
        raise NotImplementedError("TODO 5a: slice_table")

    def hipotesis_tokenizacion():
        """Devuelve dict con 'code_bm25', 'code_tokfix' (nDCG@10 medio en queries de código) y 'delta' (paired_bootstrap)."""
        # TODO 5b: BM25 con tok_code vs BM25 con tok_simple SOLO en queries de código
        raise NotImplementedError("TODO 5b: hipotesis_tokenizacion")

    try:
        qids = PER["BM25"]["qids"]; tab = slice_table(PER, qids, q_lang, list(PER)); display(tab.round(3))
        RES["slice_peor"] = tab.min(axis=1).idxmin(); h = hipotesis_tokenizacion(); RES["hipotesis"] = h
        print(f"slice más débil: {RES['slice_peor']} · tokenización code: {h['code_bm25']:.3f} → {h['code_tokfix']:.3f}  Δ={h['delta']['diff']:+.3f} IC95[{h['delta']['ci_low']:+.3f}, {h['delta']['ci_high']:+.3f}]")
    except (NotImplementedError, TypeError, NameError, AttributeError, KeyError) as e:
        print("⏳ pendiente (TODOs 1–5):", type(e).__name__)
    ''')

    nb.md("""
    ## 7. Rúbrica (autoevaluación)
    Ejecuta la celda: marca ✅ / ❌ / ⏳ (pendiente). Los umbrales numéricos están **calibrados con la solución de referencia** (FAST_DEV_RUN=True, corpus sintético, semilla 42) con un margen explícito; con datos reales solo se exigen los chequeos estructurales.
    """)
    nb.code(f'''
    REF = {REF!r}   # medidos por la solución de referencia
    ''' + r'''
    def rubrica(res: dict, strict_numbers: bool = None):
        sint = corpus["source"] == "synthetic" and FAST_DEV_RUN
        strict_numbers = sint if strict_numbers is None else strict_numbers
        out = []
        def chk(nombre, cond_fn):
            try: ok = cond_fn(); out.append((nombre, "✅" if ok else "❌"))
            except Exception: out.append((nombre, "⏳"))
        chk("1. test_metricas", lambda: test_metricas().startswith("✅"))
        chk("2. test_golden", lambda: test_golden().startswith("✅"))
        chk("3. test_rrf", lambda: test_rrf().startswith("✅"))
        chk("4. test_stats", lambda: test_stats().startswith("✅"))
        chk("5. split: nº dev + test = nº queries", lambda: res["n_dev"] + res["n_test"] == len(queries))
        chk("6. κ de dos anotadores ∈ [0.55, 0.75]", lambda: 0.55 <= res["kappa"] <= 0.75)
        if strict_numbers:
            for k, nom in (("BM25", "bm25"), ("LSI-48", "lsi"), ("RRF", "rrf")):
                chk(f"7. nDCG@10 {k} = {REF[nom]} ± 0.01", lambda k=k, nom=nom: abs(res["ndcg10"][k][0] - REF[nom]) <= 0.01)
            chk(f"8. ancho IC95 de BM25 ∈ [{REF['ci_ancho_bm25']-0.04:.2f}, {REF['ci_ancho_bm25']+0.04:.2f}]", lambda: abs((res["ndcg10"]["BM25"][2] - res["ndcg10"]["BM25"][1]) - REF["ci_ancho_bm25"]) <= 0.04)
            chk(f"9. Δ(LSI−BM25) = {REF['diff_lsi_bm25']} ± 0.015", lambda: abs(res["tests"]["LSI-48 vs BM25"]["diff"] - REF["diff_lsi_bm25"]) <= 0.015)
            chk("10. Holm: LSI−BM25 NO significativo tras corrección", lambda: res["holm"]["LSI-48 vs BM25"][1] is False)
            chk("11. slice más débil = code", lambda: res["slice_peor"] == "code")
            chk(f"12. tokenización: nDCG code {REF['code_bm25']} → {REF['code_tokfix']} (± 0.03) con IC95 > 0", lambda: abs(res["hipotesis"]["code_tokfix"] - REF["code_tokfix"]) <= 0.03 and res["hipotesis"]["delta"]["ci_low"] > 0)
        else:
            print("ℹ️ Datos reales o FAST_DEV_RUN=False: se omiten umbrales numéricos (compara con tus propios valores).")
        for nombre, estado in out: print(estado, nombre)
        print(f"\n{sum(e == '✅' for _, e in out)}/{len(out)} criterios cumplidos")
    rubrica(RES)
    ''')

    nb.md("""
    ## 8. Informe para la CTO (escribe aquí — 3 decisiones)
    Rellena en este bloque (markdown) tus respuestas; deben **citar IC y la diferencia pareada**:

    1. **¿Híbrido vs BM25 vs denso?** (…)
    2. **¿Qué acción de mayor impacto sugieren los errores?** (…)
    3. **¿Cuántas queries más necesitas para decidir con confianza y qué harías con el test ciego?** (…)
    """)

    # ─────────────────────────── SOLUCIÓN ───────────────────────────
    nb.md("""
    # ⛔ SPOILER — intenta resolverlo primero

    Debajo está la **solución de referencia completa y ejecutable**. Si te atascas en un TODO, abre antes las pistas 🪜 de ese paso. Al ejecutarla se redefinen las funciones de arriba y se recalcula `RES`.
    """)
    nb.md("### Solución 1 · Métricas")
    nb.code(METRICS_SRC.split("METRICS = {")[0].rstrip() + "\n")
    nb.code(r'''
    corre(test_metricas)
    ''')
    nb.md("### Solución 2 · Golden set y κ")
    nb.code(r'''
    def split_estratificado(queries, frac_test: float = 0.3, seed: int = SEED):
        rng = random.Random(seed); dev, test = [], []
        for lang in sorted({q["lang"] for q in queries}):
            grp = [q for q in queries if q["lang"] == lang]; rng.shuffle(grp)
            cut = int(round(len(grp) * frac_test)); test += grp[:cut]; dev += grp[cut:]
        return dev, test

    def cohen_kappa(a, b) -> float:
        a, b = np.asarray(a), np.asarray(b); labs = np.unique(np.concatenate([a, b]))
        po = np.mean(a == b); pe = sum(np.mean(a == l) * np.mean(b == l) for l in labs)
        return float((po - pe) / (1 - pe)) if pe < 1 else 1.0
    corre(test_golden)
    ''')
    nb.md("### Solución 3 · RRF")
    nb.code(r'''
    def rrf_scores(score_lists, k: int = 60) -> np.ndarray:
        out = np.zeros(len(score_lists[0]))
        for s in score_lists:
            order = np.lexsort((np.arange(len(s)), -np.asarray(s)))
            out[order] += 1.0 / (k + np.arange(len(s)) + 1)
        return out
    corre(test_rrf)
    RUNS = construye_runs(); PER = {n: evaluate_per_query(r, qrels, 10) for n, r in RUNS.items()}
    print({n: round(float(p["ndcg"].mean()), 3) for n, p in PER.items()})
    ''')
    nb.md("### Solución 4 · Estadística")
    nb.code(STATS_SRC + "\ncorre(test_stats)\n")
    nb.md("### Solución 5 · Slices e hipótesis de tokenización")
    nb.code(r'''
    def slice_table(per, qids, q_lang, sistemas):
        df = pd.DataFrame({"lang": [q_lang[q] for q in qids], **{s: per[s]["ndcg"] for s in sistemas}})
        return df.groupby("lang")[sistemas].mean()

    def hipotesis_tokenizacion():
        run_tc = build_run(BM25(tok_code).fit(doc_texts, doc_ids).scores, queries, doc_ids, 100); per_tc = evaluate_per_query(run_tc, qrels, 10)
        mask = np.array([q_lang[q] == "code" for q in per_tc["qids"]])
        return {"code_bm25": float(PER["BM25"]["ndcg"][mask].mean()), "code_tokfix": float(per_tc["ndcg"][mask].mean()),
                "delta": paired_bootstrap(per_tc["ndcg"][mask], PER["BM25"]["ndcg"][mask])}
    ''')
    nb.md("### Solución 6 · Pipeline completo y rúbrica")
    nb.code(r'''
    RES = {}
    RES["ndcg10"] = {n: bootstrap_ci(p["ndcg"]) for n, p in PER.items()}
    tests = {f"{a} vs {b}": paired_bootstrap(PER[a]["ndcg"], PER[b]["ndcg"]) for a, b in [("LSI-48", "BM25"), ("RRF", "BM25"), ("RRF", "LSI-48")]}
    adj = holm({k: v["p_value"] for k, v in tests.items()}); RES["tests"], RES["holm"] = tests, adj
    for k, v in tests.items(): print(f"{k:16s} Δ={v['diff']:+.3f} IC95[{v['ci_low']:+.3f},{v['ci_high']:+.3f}] p={v['p_value']:.4f} p_Holm={adj[k][0]:.4f} {'✅ sig.' if adj[k][1] else '— no sig.'}")
    dev_q, test_q = split_estratificado(queries); RES["n_dev"], RES["n_test"] = len(dev_q), len(test_q)
    rng = np.random.default_rng(SEED); verdad = rng.integers(0, 2, 300)
    a1 = np.where(rng.random(300) < .90, verdad, 1 - verdad); a2 = np.where(rng.random(300) < .90, verdad, 1 - verdad); RES["kappa"] = cohen_kappa(a1, a2)
    tab = slice_table(PER, PER["BM25"]["qids"], q_lang, list(PER)); display(tab.round(3)); RES["slice_peor"] = tab.min(axis=1).idxmin()
    RES["hipotesis"] = hipotesis_tokenizacion(); print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in RES["hipotesis"].items() if k != "delta"}, RES["hipotesis"]["delta"])
    rubrica(RES)
    ''')
    nb.code(r'''
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.6))
    for i, (n, (m, lo, hi)) in enumerate(RES["ndcg10"].items()): ax[0].errorbar(m, i, xerr=[[m - lo], [hi - m]], fmt="o", color=AZUL, capsize=4)
    ax[0].set_yticks(range(3)); ax[0].set_yticklabels(list(RES["ndcg10"])); ax[0].set_xlabel("nDCG@10 (IC 95 % bootstrap)"); ax[0].set_title("Banco de evaluación: sistemas con incertidumbre")
    for i, (k, v) in enumerate(RES["tests"].items()): ax[1].errorbar(v["diff"], i, xerr=[[v["diff"] - v["ci_low"]], [v["ci_high"] - v["diff"]]], fmt="s", color=NARANJA if not RES["holm"][k][1] else VERDE, capsize=4)
    ax[1].axvline(0, color=GRIS, ls="--"); ax[1].set_yticks(range(3)); ax[1].set_yticklabels(list(RES["tests"])); ax[1].set_xlabel("Δ nDCG@10 pareada (verde = sig. tras Holm)"); ax[1].set_title("Diferencias pareadas con IC")
    plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** Los IC de las tres medias se solapan; la diferencia *pareada* LSI−BM25 tiene IC que apenas excluye 0 y **no sobrevive a Holm**, mientras que RRF es *significativamente peor* que LSI.
    > Decisión honesta con 72 queries: no hay evidencia de que el híbrido ingenuo (RRF) mejore a BM25; el mayor impacto no es cambiar de modelo, sino **arreglar la tokenización del código** (Δ ≈ +0.16 en ese slice, IC > 0).
    """)

    nb.md("""
    ## 🚀 Retos extra (nivel experto)
    1. **Verifica contra `ranx`** (`Qrels`, `Run`, `evaluate`) tus tres métricas con tolerancia 1e-9 y añade `exp_gain=True` (nDCG de Burges).
    2. **LLM-as-judge simulado**: reproduce la sección 7 de la lección sobre tu banco; encuentra el sesgo léxico a partir del cual **se invierte** el orden BM25 vs LSI.
    3. **LIMIT-mini**: genera el corpus «¿a quién le gusta X?» con 30 personas y mide Recall@2 de BM25 y de LSI con $d\\in\\{4,8,16,29\\}$. ¿Cuál es el mínimo $d$ para Recall@2 ≥ 0.9?
    4. **Detector de contaminación**: añade al banco una función `frac_contaminada(train, test, n)` y un test automático que falle si >5 % de las queries de test tienen n-gramas en los documentos.
    5. **Drift**: simula 12 semanas de tráfico con mezcla de idiomas cambiante y dispara alerta con PSI > 0.25; añade ponderación por tráfico al informe.
    6. **MIRACL-es / SciFact reales** (con red): corre BM25 y un embedder real y reporta IC pareado; compara con el leaderboard de MTEB **con fecha**.
    7. **Calidad del qrel**: estima qué fracción de «falsos negativos» (relevantes no juzgados) hay anotando a mano el top-5 de LSI en 20 queries.

    ## 🧠 Reflexión (conecta con producción y con Políglota)
    - Si el IC de la mejora incluye 0, ¿qué haces antes de gastar GPU en re-embedding? ¿Qué decisión se puede tomar con *coste* en vez de *calidad*?
    - ¿Cómo repartirías el test ciego entre idiomas si el tráfico real es 60 % ES, 30 % EN, 10 % código? (pista: ponderar vs estratificar).
    - Tu banco evalúa **calidad de ranking**. ¿Qué métricas necesitas añadir cuando introduzcas el índice ANN (módulo 14) y el servicio (módulo 18)?
    - ¿Qué parte de este banco reutilizarías para evaluar el **tokenizer** (módulos 02–04) más allá de la fertilidad?

    ➡️ **Siguiente:** módulo 16 (embeddings multimodales): extenderás Políglota para buscar en PDFs y capturas, y su evaluación reutilizará este banco.
    """)
