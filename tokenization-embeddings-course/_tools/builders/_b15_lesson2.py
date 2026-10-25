"""Lección 15 · parte 2: sistemas, gráficos de métricas, ranx, benchmarks, golden sets."""
from _a6_src15 import STATS_SRC, RETRIEVERS_SRC


def part2(nb):
    nb.md("""
    ### 3.5 Tres sistemas para evaluar
    Necesitamos algo que evaluar. Sin descargas: **BM25** (léxico, implementación propia), **LSI-48** (TF-IDF + SVD: un «embedder» denso de CPU) y su fusión **RRF**.
    Si tienes red y `sentence-transformers`, la celda siguiente añade un embedder real (`multilingual-e5-small`) como cuarto sistema.
    """)
    nb.code(RETRIEVERS_SRC)
    nb.code(r'''
    bm25 = BM25(tok_simple).fit(doc_texts, doc_ids)
    lsi = LSI(dim=48, seed=SEED).fit(doc_texts, doc_ids)
    SISTEMAS = {
        "BM25": bm25.scores,
        "LSI-48": lsi.scores,
        "RRF(BM25+LSI)": lambda q: rrf_scores([bm25.scores(q), lsi.scores(q)]),
    }

    def try_sentence_transformer(name="intfloat/multilingual-e5-small"):
        """Opcional: embedder real. Devuelve scorer o None si no hay red/librería (nunca rompe el notebook)."""
        try:
            from sentence_transformers import SentenceTransformer
            m = SentenceTransformer(name, device=device)
            E = m.encode(["passage: " + t for t in doc_texts], normalize_embeddings=True, batch_size=64, show_progress_bar=False)
            return lambda q: E @ m.encode(["query: " + q], normalize_embeddings=True)[0]
        except Exception as e:
            print(f"ℹ️ Embedder real no disponible ({type(e).__name__}); seguimos con BM25/LSI/RRF.")
            return None

    if not FAST_DEV_RUN or os.environ.get("TRY_ST") == "1":
        st = try_sentence_transformer()
        if st: SISTEMAS["e5-small"] = st

    RUNS = {n: build_run(f, queries, doc_ids, topn=100) for n, f in SISTEMAS.items()}
    resumen = pd.DataFrame({n: evaluate(r, qrels, 10) for n, r in RUNS.items()}).T.round(3)
    resumen
    ''')
    nb.md("### 3.6 Verificación contra `ranx`\nNunca confíes en tu propia implementación de una métrica sin contrastarla con una referencia independiente. `ranx` (Bassani, ECIR 2022) es una librería ampliamente usada; debe coincidir al 1e-9.")
    nb.code(r'''
    try:
        from ranx import Qrels, Run, evaluate as ranx_evaluate
        q_ranx = Qrels({q: {d: int(r) for d, r in rels.items()} for q, rels in qrels.items()})
        for nombre, run in RUNS.items():
            # ranx necesita scores: damos scores decrecientes según la posición del ranking
            r_ranx = Run({q: {d: float(len(lst) - i) for i, d in enumerate(lst)} for q, lst in run.items()})
            ref = ranx_evaluate(q_ranx, r_ranx, ["ndcg@10", "recall@10", "mrr@10"])
            mio = evaluate(run, qrels, 10)
            dif = max(abs(ref["ndcg@10"] - mio["ndcg@10"]), abs(ref["recall@10"] - mio["recall@10"]), abs(ref["mrr@10"] - mio["mrr@10"]))
            print(f"{nombre:16s} máx|ranx - mío| = {dif:.2e}  {'✅' if dif < 1e-9 else '❌'}")
    except ImportError:
        print("ranx no instalado: `pip install ranx` para esta verificación (opcional).")
    ''')

    nb.md("### 3.7 Gráfico: cómo se ven las tres métricas sobre el mismo run")
    nb.code(r'''
    ks = [1, 2, 3, 5, 10, 20, 50, 100]
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.6), sharex=True)
    colores = [AZUL, NARANJA, VERDE, GRIS]
    for (nombre, run), c in zip(RUNS.items(), colores):
        for a, (m, fn) in zip(ax, (("nDCG@k", ndcg_at_k), ("Recall@k", recall_at_k), ("MRR@k", mrr_at_k))):
            v = [np.mean([fn(run[q], qrels[q], k) for q in qrels if any(qrels[q].values())]) for k in ks]
            a.plot(ks, v, marker="o", ms=3, color=c, label=nombre); a.set_title(m); a.set_xscale("log"); a.set_xlabel("k (escala log)")
    ax[0].set_ylabel("valor medio sobre queries"); ax[0].legend(frameon=False, fontsize=8)
    fig.suptitle("Las mismas rankings, tres métricas: saturan a ritmos distintos", y=1.03); plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** (1) **Recall@k** crece sin parar con $k$ y llega casi a 1 hacia $k=100$: es la métrica del *primer paso* de un pipeline.
    > (2) **MRR@k** casi no cambia después de $k\\approx 5$: solo mira el primer acierto. (3) **nDCG@k no es monótona** en $k$: puede bajar al principio (al aparecer relevantes de grado bajo detrás de uno muy bien colocado) y sube cuando entran más relevantes. (4) El *orden entre sistemas* puede cambiar según la métrica y el $k$ elegido:
    > por eso se fija el protocolo (nDCG@10) **antes** de ver los resultados.
    """)

    nb.code(r'''
    pos = np.arange(1, 11)
    ranking_a = ["x", "r2", "x", "r1", "x", "x", "r3", "x", "x", "x"]   # relevantes (grados 3,2,1) en posiciones 2,4,7
    ranking_b = ["r1", "r2", "r3", "x", "x", "x", "x", "x", "x", "x"]   # ranking ideal
    rr = {"r1": 3, "r2": 2, "r3": 1}
    fig, ax = plt.subplots(1, 2, figsize=(12, 3.8))
    ax[0].plot(pos, 1 / np.log2(pos + 1), "o-", color=AZUL, label="descuento nDCG  1/log₂(i+1)")
    ax[0].plot(pos, 1 / pos, "s--", color=NARANJA, label="descuento MRR/AP  1/i")
    ax[0].set_xlabel("posición i"); ax[0].set_ylabel("peso"); ax[0].set_title("El descuento de nDCG es más suave que 1/i"); ax[0].legend(frameon=False)
    w = .38
    for off, (nom, rk, c) in zip((-w/2, w/2), (("ranking A", ranking_a, ROJO), ("ranking ideal", ranking_b, VERDE))):
        contrib = [rr.get(d, 0) / math.log2(i + 2) for i, d in enumerate(rk)]
        ax[1].bar(pos + off, contrib, w, color=c, label=f"{nom}: nDCG@10={ndcg_at_k(rk, rr, 10):.2f}")
    ax[1].set_xlabel("posición"); ax[1].set_ylabel("contribución al DCG"); ax[1].set_title("Dónde se gana el DCG (ganancia 3, 2, 1)"); ax[1].legend(frameon=False)
    plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** A la izquierda, el descuento logarítmico castiga menos las posiciones bajas que $1/i$: nDCG es «más tolerante» que MRR/AP.
    > A la derecha, el ranking A pone el documento más relevante (ganancia 3) en la posición 4 en vez de la 1: pierde un tercio del DCG (nDCG 0.67) aunque *recupere los tres relevantes*.
    > Recall@10 sería **idéntico (1.0)** para ambos: Recall no ve el orden.
    """)

    # ───────────────────────── 4. Benchmarks ─────────────────────────
    nb.md("""
    ## 4. Benchmarks públicos: qué miden y qué no

    | Benchmark | Qué es | Detalles verificados | Cuidado |
    |---|---|---|---|
    | **BEIR** (Thakur et al., NeurIPS 2021) | 18 datasets heterogéneos de retrieval *zero-shot* (SciFact, FiQA, NFCorpus, TREC-COVID…) | **SciFact**: verificación de afirmaciones científicas, ≈ 5 K abstracts y 300 queries de test; **FiQA**: QA financiero (opiniones), ≈ 57 K documentos y 648 queries de test (BEIR, Tabla 1) | qrels dispersos: muchos relevantes **sin juzgar** (sección 6) |
    | **MIRACL** (Zhang et al., 2022) | Retrieval monolingüe en **18 idiomas** (incluye español) con juicios humanos | Wikipedia por idioma; evaluado con nDCG@10 | Solo monolingüe; sin cross-lingual |
    | **MTEB** (Muennighoff et al., 2022) | 8 tareas / 58 datasets / 112 idiomas; para retrieval, métrica principal nDCG@10 | Promedia tareas muy distintas | El promedio oculta qué tarea importa a *tu* producto |
    | **MMTEB** (Enevoldsen et al., ICLR 2025) | Extensión comunitaria: **> 500 tareas, 250+ idiomas** | Incluye retrieval, instrucciones, código… | Sigue siendo público → contaminable |
    | **RTEB** (HF + MTEB, beta oct-2025) | Retrieval con datasets **privados** para medir overfitting | 48 datasets, 28 privados; correlación de rankings con BEIR/MTEB débil (ρ = 0.38) según su paper | 🟡 Joven; los privados no son auditables por ti |

    > 📅 *Cifras a oct-2026, tomadas de los papers/blog citados en Referencias; los leaderboards cambian cada semana: no copies números de ahí sin fecha.*
    """)
    nb.code(r'''
    def carga_beir(nombre: str = "scifact", split: str = "test", max_docs: int = 5000, max_queries: int = 300):
        """BEIR vía Hugging Face (`BeIR/<nombre>` + `BeIR/<nombre>-qrels`). Devuelve el mismo contrato que carga_corpus o None.
        ⚠️ No pude probarlo en mi entorno de desarrollo (HF bloqueado): el esquema es el documentado en las model cards de BeIR."""
        try:
            from datasets import load_dataset
            corp = load_dataset(f"BeIR/{nombre}", "corpus", split="corpus")
            qs = load_dataset(f"BeIR/{nombre}", "queries", split="queries")
            qr = load_dataset(f"BeIR/{nombre}-qrels", split=split)
        except Exception as e:
            print(f"ℹ️ BEIR/{nombre} no disponible ({type(e).__name__}) -> usa el corpus Políglota de arriba.")
            return None
        rel: dict = {}
        for r in qr:
            if r["score"] > 0: rel.setdefault(str(r["query-id"]), {})[str(r["corpus-id"])] = int(r["score"])
        keep = list(rel)[:max_queries]
        need = {d for q in keep for d in rel[q]}
        docs_b = [{"id": str(r["_id"]), "lang": "en", "text": (r["title"] + ". " + r["text"]).strip()} for r in corp]
        docs_b = [d for d in docs_b if d["id"] in need] + [d for d in docs_b if d["id"] not in need][: max(0, max_docs - len(need))]
        qd = {str(r["_id"]): r["text"] for r in qs}
        return {"docs": docs_b, "queries": [{"qid": q, "lang": "en", "text": qd[q]} for q in keep if q in qd],
                "qrels": {q: rel[q] for q in keep}, "source": f"real:BeIR/{nombre}"}

    beir = carga_beir("scifact") if not FAST_DEV_RUN or os.environ.get("TRY_BEIR") == "1" else None
    if beir:
        b_ids = [d["id"] for d in beir["docs"]]; b_bm25 = BM25(tok_simple).fit([d["text"] for d in beir["docs"]], b_ids)
        b_run = build_run(b_bm25.scores, beir["queries"], b_ids)
        print("BM25 en", beir["source"], evaluate(b_run, beir["qrels"], 10))
    else:
        print("BEIR no cargado (FAST_DEV_RUN=True o sin red). Pon FAST_DEV_RUN=False en Colab para probarlo; "
              "referencia pública: BM25 en SciFact ≈ 0.665 nDCG@10 (BEIR, 2021).")
    ''')
    nb.md("""
    ### 4.1 Cómo se corre MTEB «de verdad» (celda opcional)
    La librería `mteb` evalúa un modelo en tareas con la métrica oficial. Su API **cambió entre v1 y v2**; verifica con tu versión (`pip show mteb`). La celda está protegida:
    no se ejecuta salvo que pongas `RUN_MTEB = True`.
    """)
    nb.code(r'''
    RUN_MTEB = False   # True en Colab con red: descarga el modelo y los datasets de SciFact/FiQA
    if RUN_MTEB:
        import mteb
        modelo = mteb.get_model("intfloat/multilingual-e5-small")
        tareas = mteb.get_tasks(tasks=["SciFact", "FiQA2018"])
        try:
            resultados = mteb.evaluate(modelo, tareas)                        # mteb >= 2.x
        except AttributeError:
            resultados = mteb.MTEB(tasks=tareas).run(modelo, output_folder="mteb_out")   # mteb 1.x
        print(resultados)
    else:
        print("RUN_MTEB=False: celda omitida (ejemplo de uso, no se ejecuta).")
    ''')
    nb.md("""
    ## 5. Incertidumbre: bootstrap, tests pareados y comparaciones múltiples

    Un nDCG medio de 0.52 vs 0.50 sobre 72 queries, ¿es una mejora? Depende de la **varianza entre queries**. La unidad de muestreo es la *query* (no el par query-documento): las queries son las observaciones independientes.

    ### 5.1 Bootstrap percentil para la media
    1. Tienes $n$ valores por query $x_1..x_n$ (p. ej. nDCG@10 de cada una).
    2. Repite $B$ veces: remuestrea $n$ valores **con reemplazo** y calcula su media $\\bar x^*_b$.
    3. El IC 95 % es el intervalo $[q_{2.5\\%},\\,q_{97.5\\%}]$ de las $\\bar x^*_b$.
    """)
    nb.gemini(
        "video", "M15-VID-1", "Bootstrap: remuestrear queries y construir el intervalo de confianza",
        "Animación del bootstrap percentil: 8 valores de nDCG por query, tres remuestreos con reemplazo, histograma de medias que se va llenando y el IC 95 % sombreado.",
        """
        Animación técnica limpia, 16:9, fondo blanco, paleta sobria (azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280), tipografía sans-serif, ritmo calmado, sin voz en off, sin música. Texto en pantalla en español.
        Datos exactos: 8 queries con nDCG@10 = [0.00, 0.31, 0.45, 0.50, 0.63, 0.72, 0.89, 1.00]; media = 0.5625.
        Escenas:
        0–5 s: título «Bootstrap sobre queries». Aparecen 8 barras verticales azules etiquetadas q1…q8 con alturas iguales a los valores anteriores y la línea horizontal gris de la media «media = 0.56».
        5–12 s: texto «Remuestreo 1 (con reemplazo)». De las 8 barras salen flechas naranjas que "caen" en 8 huecos nuevos; algunas barras se repiten (q4 dos veces) y otras no aparecen (q1). Se muestra la nueva media «0.61» y un punto naranja cae sobre un eje horizontal inferior (histograma vacío) en 0.61.
        12–18 s: repetir rápido otros dos remuestreos (medias 0.49 y 0.58) con puntos que caen sobre el histograma; el contador muestra «B = 3».
        18–25 s: el contador acelera «B = 100 … 1000 … 2000» y los puntos forman un histograma en forma de campana azul alrededor de 0.56.
        25–30 s: se sombrean los percentiles 2.5 % y 97.5 % en verde y aparece la etiqueta «IC 95 % = [0.37, 0.74]» sobre el histograma; texto final «la incertidumbre depende del número de queries».
        Evita: voz en off, música, texto ilegible, números distintos a los dados, efectos 3D, transiciones bruscas.
        """,
        "Animación en la que ocho valores de nDCG se remuestrean con reemplazo, las medias forman un histograma y se marca el intervalo de confianza al 95 %.",
        """
        q1..q8 = [0.00 0.31 0.45 0.50 0.63 0.72 0.89 1.00]  media 0.56
        remuestreo 1: [q4 q4 q6 q8 q2 q7 q8 q5] -> media 0.61  (punto en el histograma)
        ... B=2000 medias -> campana -> percentiles 2.5% y 97.5% = IC 95%
        """,
        duration="30 s",
    )
    nb.md("""
    > 👀 **Qué debes observar.** Algunas queries aparecen repetidas y otras desaparecen en cada remuestreo: eso simula «otro conjunto de queries posible».
    > El ancho del histograma de medias es la **incertidumbre por tener solo estas queries**. Con más queries la campana se estrecha como $\\sigma/\\sqrt n$.
    """)
    nb.code(STATS_SRC)
    nb.code(r'''
    per = {n: evaluate_per_query(r, qrels, 10) for n, r in RUNS.items()}
    qids_eval = per["BM25"]["qids"]
    filas = []
    for n in RUNS:
        m, lo, hi = bootstrap_ci(per[n]["ndcg"])
        filas.append({"sistema": n, "nDCG@10": m, "IC95_bajo": lo, "IC95_alto": hi, "ancho": hi - lo})
    tabla_ic = pd.DataFrame(filas).set_index("sistema").round(3)
    display(tabla_ic)

    fig, ax = plt.subplots(figsize=(7, 2.8))
    for i, (n, r) in enumerate(tabla_ic.iterrows()):
        ax.errorbar(r["nDCG@10"], i, xerr=[[r["nDCG@10"] - r["IC95_bajo"]], [r["IC95_alto"] - r["nDCG@10"]]], fmt="o", color=AZUL, capsize=4)
    ax.set_yticks(range(len(tabla_ic))); ax.set_yticklabels(tabla_ic.index); ax.set_xlabel("nDCG@10 (media e IC 95 % bootstrap)")
    ax.set_title("Los intervalos se solapan: ¿hay diferencia real?"); plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** Los IC de dos sistemas pueden **solaparse** y aun así uno ser significativamente mejor: ambos sistemas se evalúan sobre *las mismas queries*,
    > y las queries difíciles lo son para los dos. El IC de cada media ignora esa correlación; el **test pareado** (siguiente celda) la aprovecha y es mucho más potente.
    """)
    nb.md("""
    ### 5.2 Test pareado y corrección de Holm
    Para comparar A y B sobre las mismas queries se trabaja con las **diferencias por query** $d_i = a_i - b_i$. Dos tests no paramétricos equivalentes:

    - **Bootstrap pareado**: IC de $\\bar d$ remuestreando queries; p-valor desplazando las diferencias para que $H_0:\\bar d=0$ sea cierta.
    - **Aleatorización (sign-flip)**: bajo $H_0$ el signo de cada $d_i$ es intercambiable.

    Smucker, Allan y Carterette (CIKM 2007) compararon cinco tests sobre runs de TREC y encontraron que bootstrap, randomización y t-test **coinciden casi siempre**; el Wilcoxon y el de signos se desvían. Si comparas $m$ pares de sistemas, el riesgo de falso positivo se acumula: **Holm** controla la tasa de error familiar con más potencia que Bonferroni.
    """)
    nb.code(r'''
    pares = [("LSI-48", "BM25"), ("RRF(BM25+LSI)", "BM25"), ("RRF(BM25+LSI)", "LSI-48")]
    pb, pp, filas = {}, {}, []
    for a, b in pares:
        tb = paired_bootstrap(per[a]["ndcg"], per[b]["ndcg"]); pv = paired_permutation(per[a]["ndcg"], per[b]["ndcg"])
        pb[f"{a} vs {b}"] = tb["p_value"]
        filas.append({"comparación": f"{a} − {b}", "Δ nDCG@10": tb["diff"], "IC95_bajo": tb["ci_low"], "IC95_alto": tb["ci_high"], "p (bootstrap)": tb["p_value"], "p (permutación)": pv})
    ajustado = holm(pb)
    tabla_tests = pd.DataFrame(filas).set_index("comparación")
    tabla_tests["p Holm"] = [ajustado[k][0] for k in pb]; tabla_tests["¿significativo (α=.05)?"] = [ajustado[k][1] for k in pb]
    tabla_tests.round(4)
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** La primera fila (LSI−BM25) tiene un p *sin corregir* cercano a 0.03 (\"significativo\"), pero tras **Holm** (3 comparaciones) el p ajustado sube por encima de 0.05: con 72 queries y tres comparaciones **no puedes afirmarlo**.
    > Es lo que pasa en un paper cuando se prueban muchas variantes y solo se reporta la «ganadora». La tercera fila, en cambio, sí resiste la corrección. Con otro corpus los números cambiarán: lo importante es el procedimiento (IC pareado + Holm), no estos valores.
    """)
    nb.md("""
    ### 5.3 ¿Cuántas queries necesito? (experimento)
    El ancho del IC cae como $1/\\sqrt n$. Midamos la desviación estándar *real* entre queries de nuestro sistema y deduzcamos el tamaño de golden set necesario para una semi-anchura objetivo.
    """)
    nb.code(r'''
    x = per["BM25"]["ndcg"]; rng = np.random.default_rng(SEED)
    sizes = [n for n in (10, 20, 30, 45, 60, 80, len(x)) if n <= len(x)]
    anchos = []
    for n in sizes:
        w = [np.subtract(*np.quantile(x[rng.choice(len(x), n, replace=False)][rng.integers(0, n, (400, n))].mean(1), [.975, .025])) for _ in range(20)]
        anchos.append(np.mean(w))
    sd = x.std(ddof=1)
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    ax.plot(sizes, anchos, "o-", color=AZUL, label="ancho medio del IC95 % (bootstrap)")
    nn = np.linspace(min(sizes), max(sizes), 50); ax.plot(nn, 2 * 1.96 * sd / np.sqrt(nn), "--", color=NARANJA, label=r"teoría: $2\cdot1.96\,\sigma/\sqrt{n}$")
    ax.set_xlabel("nº de queries en el golden set"); ax.set_ylabel("ancho del IC (nDCG@10)"); ax.legend(frameon=False); ax.set_title("Más queries → intervalos más estrechos"); plt.tight_layout(); plt.show()
    print(f"σ entre queries = {sd:.3f}")
    for h in (0.05, 0.03, 0.02):
        print(f"  para semi-anchura ±{h:.2f} sobre UNA media: n ≈ {math.ceil((1.96 * sd / h) ** 2)} queries")
    d = per["LSI-48"]["ndcg"] - per["BM25"]["ndcg"]
    print(f"σ de la DIFERENCIA pareada LSI−BM25 = {d.std(ddof=1):.3f}  (pareada: {'menor' if d.std(ddof=1) < sd else 'similar/mayor'} que σ de una sola métrica)")
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** El IC medido sigue la curva teórica $\\propto 1/\\sqrt n$: **para reducir el ancho a la mitad necesitas 4× queries**. Las cifras impresas son *las de tu golden set*, no una regla universal:
    > los benchmarks reales (SciFact 300 queries, FiQA 648) tienen σ distinta. Si tu objetivo es detectar mejoras de ±0.01 nDCG, 100 queries no bastan: o amplías el golden set o aceptas decidir solo diferencias grandes.
    """)
    nb.code(r'''
    # ¿Qué tests mantienen el error tipo I bajo control? Experimento A/A: dos "sistemas" con la MISMA calidad esperada.
    rng = np.random.default_rng(SEED); n_q, reps, alpha = 50, 300, .05
    from scipy import stats
    base = per["BM25"]["ndcg"]; rech = {"bootstrap pareado": 0, "permutación pareada": 0, "t pareado": 0, "t NO pareado (error)": 0}
    pot = dict.fromkeys(rech, 0); delta = 0.04
    for _ in range(reps):
        x0 = rng.choice(base, n_q)                                  # dificultad de cada query (compartida)
        a = np.clip(x0 + rng.normal(0, .12, n_q), 0, 1); b = np.clip(x0 + rng.normal(0, .12, n_q), 0, 1)
        for tag, (u, v) in (("null", (a, b)), ("alt", (np.clip(a + delta, 0, 1), b))):
            ps = {"bootstrap pareado": paired_bootstrap(u, v, n_boot=400, seed=int(rng.integers(10**9)))["p_value"],
                  "permutación pareada": paired_permutation(u, v, n_perm=400, seed=int(rng.integers(10**9))),
                  "t pareado": stats.ttest_rel(u, v).pvalue, "t NO pareado (error)": stats.ttest_ind(u, v).pvalue}
            tgt = rech if tag == "null" else pot
            for k, p in ps.items(): tgt[k] += p < alpha
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.4))
    ax[0].bar(list(rech), [v / reps for v in rech.values()], color=[AZUL, AZUL, AZUL, ROJO]); ax[0].axhline(alpha, color=GRIS, ls="--"); ax[0].set_title("Falsos positivos (A = B): debería ser ≈ 0.05")
    ax[1].bar(list(pot), [v / reps for v in pot.values()], color=[VERDE, VERDE, VERDE, ROJO]); ax[1].set_title(f"Potencia con diferencia real Δ={delta}")
    for a_ in ax: a_.tick_params(axis="x", rotation=18); a_.set_ylim(0, 1)
    plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** Los tres tests pareados mantienen los falsos positivos cerca de 0.05 y tienen **potencia parecida**. Tratar las queries como muestras independientes
    > (t no pareado, barra roja) es *conservador* aquí (≈ 0 falsos positivos) pero **pierde casi toda la potencia**: desperdicia la información de que ambos sistemas ven las mismas queries.
    > Recomendación práctica: reporta siempre diferencia pareada con IC, no dos IC separados.
    """)

    # ───────────────────────── 6. Golden sets ─────────────────────────
    nb.md("""
    ## 6. Construir tu propio golden set
    Los benchmarks públicos responden «¿es buen embedder en general?». Tu producto necesita un set sobre **tus** documentos y **tus** usuarios. Receta mínima:

    1. **Fuente de queries**: logs reales anonimizados > queries escritas por expertos > queries sintéticas generadas por LLM a partir de documentos (útiles para empezar, sesgadas hacia el vocabulario del documento).
    2. **Muestreo estratificado** por idioma, longitud y tipo de intención; si no, domina lo frecuente. Reserva una parte (≥ 30 %) como **test ciego** que no se toca al iterar.
    3. **Pooling de candidatos**: junta el top-k de **varios sistemas distintos** (léxico + denso + híbrido); anotar solo lo que devuelve un sistema sesga los qrels a su favor (veremos el efecto en 6.2).
    4. **Guía de anotación** con grados (0 irrelevante, 1 tangencial, 2 responde parcialmente, 3 responde completamente) y ejemplos límite.
    5. **Doble anotación** de una muestra y medir acuerdo con **κ de Cohen**: $\\kappa=(p_o-p_e)/(1-p_e)$, donde $p_o$ es el acuerdo observado y $p_e$ el esperado por azar.
    6. **Versionar y congelar** (dataset card: fuente, fecha, criterios, κ); recalibrar cuando cambie el corpus o el tráfico.
    """)
    nb.gemini(
        "imagen", "M15-IMG-3", "Ciclo de vida de un golden set",
        "Ciclo en seis pasos: muestrear queries, hacer pooling de candidatos, anotar con guía, medir acuerdo κ, congelar versión y vigilar drift; con el test ciego aparte.",
        """
        Diagrama técnico limpio, fondo blanco, paleta sobria (azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280), tipografía sans-serif legible, flechas claras, sin ilustraciones decorativas. 16:9.
        Un ciclo circular de seis nodos redondeados conectados por flechas en sentido horario, con estos textos literales:
        1 (azul) «Muestrear queries (estratificado por idioma e intención)»,
        2 (azul) «Pooling: top-k de BM25 + denso + híbrido»,
        3 (naranja) «Anotar con guía (grados 0–3)»,
        4 (naranja) «Acuerdo entre anotadores: κ de Cohen»,
        5 (verde) «Congelar versión v1.0 + dataset card»,
        6 (verde) «Vigilar drift y recalibrar».
        En el centro del ciclo un rectángulo gris con el texto «TEST CIEGO (30 %): no se toca al iterar».
        Entre los nodos 4 y 3 una flecha curva de retorno con la etiqueta «κ < 0.6 → mejorar la guía».
        Título superior: «Ciclo de vida de un golden set».
        Evita: texto ilegible o inventado, ilustraciones de personas, elementos decorativos, más de seis nodos, flechas que se crucen.
        """,
        "Ciclo de seis pasos para construir y mantener un golden set, con un test ciego en el centro y un bucle de mejora de la guía de anotación.",
        """
        (1) muestrear → (2) pooling → (3) anotar → (4) κ de Cohen → (5) congelar v1.0 → (6) vigilar drift → (1)
                         [TEST CIEGO 30 %]       κ<0.6 → vuelve a (3)
        """,
    )
    nb.md("""
    > 👀 **Qué debes observar.** El paso 4 es un *bucle de calidad*: si dos humanos no se ponen de acuerdo (κ bajo), ningún embedder podrá «acertar» de forma consistente, y la métrica mide el ruido de la guía de anotación.
    > κ > 0.8 se considera acuerdo casi perfecto; entre 0.6 y 0.8, sustancial (escala de Landis y Koch, convención habitual).
    """)
    nb.md("""
    ### 6.1 Estratificar y repartir dev / test ciego
    """)
    nb.code(r'''
    def split_estratificado(queries, frac_test=0.3, seed=SEED):
        """Reparto dev/test ciego manteniendo la proporción por idioma (y por faceta temática si el id la lleva)."""
        rng = random.Random(seed); dev, test = [], []
        for lang in sorted({q["lang"] for q in queries}):
            grp = [q for q in queries if q["lang"] == lang]; rng.shuffle(grp)
            cut = int(round(len(grp) * frac_test)); test += grp[:cut]; dev += grp[cut:]
        return dev, test

    def cohen_kappa(a, b):
        a, b = np.asarray(a), np.asarray(b); labs = np.unique(np.concatenate([a, b]))
        po = np.mean(a == b); pe = sum(np.mean(a == l) * np.mean(b == l) for l in labs)
        return (po - pe) / (1 - pe) if pe < 1 else 1.0

    dev_q, test_q = split_estratificado(queries)
    print(f"dev={len(dev_q)} test_ciego={len(test_q)}", pd.Series([q['lang'] for q in test_q]).value_counts().to_dict())
    # Doble anotación simulada: dos anotadores con 90 % de acierto sobre pares (query, doc) reales del pool
    rng = np.random.default_rng(SEED); verdad = rng.integers(0, 2, 300)
    ann1 = np.where(rng.random(300) < .90, verdad, 1 - verdad); ann2 = np.where(rng.random(300) < .90, verdad, 1 - verdad)
    print(f"acuerdo observado={np.mean(ann1==ann2):.2f}  κ={cohen_kappa(ann1, ann2):.2f}  (anotadores 90 % fiables entre sí → κ ≈ 0.64)")
    ''')
    nb.md("""
    ### 6.2 El sesgo de pooling: los qrels incompletos castigan a lo nuevo
    Imagina que tus qrels se construyeron anotando **solo lo que devolvía BM25** (lo que tenías en 2019). Un embedder denso nuevo recupera documentos genuinamente relevantes que *nadie juzgó*; el evaluador los cuenta como no relevantes. Simulémoslo: conservamos solo los relevantes que BM25 trajo en su top-20.
    """)
    nb.code(r'''
    def qrels_pooled(qrels, run_ref, depth=20):
        out = {}
        for q, rels in qrels.items():
            top = set(run_ref[q][:depth]); keep = {d: r for d, r in rels.items() if d in top}
            out[q] = keep if keep else {}
        return out

    qr_bm25 = qrels_pooled(qrels, RUNS["BM25"], 20)
    comp = {}
    for n in ("BM25", "LSI-48", "RRF(BM25+LSI)"):
        comp[n] = (evaluate(RUNS[n], qrels, 10)["ndcg@10"], evaluate(RUNS[n], qr_bm25, 10)["ndcg@10"])
    perdidos = sum(len(v) for v in qrels.values()) - sum(len(v) for v in qr_bm25.values())
    fig, ax = plt.subplots(figsize=(7, 3.4)); x = np.arange(len(comp)); w = .36
    ax.bar(x - w/2, [v[0] for v in comp.values()], w, color=VERDE, label="qrels completos (verdad)")
    ax.bar(x + w/2, [v[1] for v in comp.values()], w, color=NARANJA, label="qrels agrupados solo desde BM25")
    ax.set_xticks(x); ax.set_xticklabels(comp); ax.set_ylabel("nDCG@10"); ax.legend(frameon=False); ax.set_title(f"Sesgo de pooling ({perdidos} relevantes sin juzgar)")
    plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** Con los qrels agrupados desde BM25, **todos los sistemas «suben»** (el IDCG se encoge al desaparecer relevantes) pero BM25 sube **más**: pasa de ser el segundo a parecer el mejor y el orden con LSI **se invierte**. El evaluador premia parecerse al sistema que sirvió para anotar.
    > Es exactamente el problema que Arabzadeh et al. (*Shallow pooling for sparse labels*, 2021) documentan en MS MARCO: los rankers neuronales modernos devuelven resultados que los jueces humanos prefieren a los «relevantes» etiquetados.
    > El propio paper de BEIR (sección 6) reconoce que varios de sus datasets sufren **sesgo léxico** (se anotaron candidatos de sistemas léxicos) y que en TREC-COVID anotar los juicios que faltaban subió a los modelos densos. **Regla:** al comparar un sistema nuevo, añade *su* top-k a la cola de anotación.
    """)
