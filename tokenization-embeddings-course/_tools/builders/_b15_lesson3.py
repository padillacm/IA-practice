"""Lección 15 · parte 3: LLM-as-judge, límites de dimensión (LIMIT), contaminación, drift, errores, cierre."""


def part3(nb):
    # ───────────────────────── 7. LLM-as-judge ─────────────────────────
    nb.md("""
    ## 7. LLM-as-judge para relevancia (y por qué hay que desconfiar con método)

    Anotar a mano 10 000 pares query–documento cuesta semanas. La tentación: pedir a un LLM que etiquete relevancia. La literatura está **dividida** (🟡 debatido):

    - **A favor**: Thomas, Spielman, Craswell y Mitra (2023) muestran que prompts afinados contra preferencias de usuarios reales producen etiquetas «tan precisas como las de anotadores humanos» y mucho más baratas.
    - **En contra**: Soboroff (2024, *Don't Use LLMs to Make Relevance Judgments*) y Clarke & Dietz (2024) argumentan que, para evaluación tipo TREC, hay riesgos de circularidad (los sistemas que usan LLMs salen favorecidos) y que las métricas basadas en LLM se pueden manipular. Faggioli et al. (2023) proponen un espectro de colaboración humano–máquina.
    - **Vulnerabilidad medida**: Alaofi et al. (SIGIR-AP 2024) insertaron las palabras de la query en pasajes irrelevantes y comprobaron que muchos LLMs los etiquetan como relevantes; sus etiquetas «no relevante» son más fiables que las «relevante».
    - **Sesgos generales de LLM-judge** (Zheng et al., NeurIPS 2023): de posición, de verbosidad y de auto-preferencia.

    **Protocolo razonable hoy:** el LLM como *triaje* (priorizar qué anotar, detectar qrels dudosos), humanos para el set de decisión, y calibración continua: mide κ del LLM vs humanos en una muestra y **actualízala cuando cambies de modelo o de prompt**.

    ### 7.1 Simulación del mecanismo del sesgo (no es una medición de ningún LLM real)
    Modelamos un juez con sensibilidad `tpr` y falsos positivos que **crecen con el solapamiento léxico** con la query (el fallo documentado por Alaofi et al.). Lo aplicamos al *pool* de los tres sistemas y recalculamos las métricas.
    """)
    nb.code(r'''
    def juez_simulado(q_text, d_text, es_rel, sesgo, rng, tpr=0.9, fpr=0.05):
        """Juez con ruido: P(relevante|rel)=tpr; P(relevante|no rel)=fpr + sesgo * (fracción de términos de la query en el doc)."""
        qt, dt = set(tok_simple(q_text)), set(tok_simple(d_text))
        solap = len(qt & dt) / max(1, len(qt))
        return rng.random() < (tpr if es_rel else min(1.0, fpr + sesgo * solap))

    doc_text = dict(zip(doc_ids, doc_texts)); q_text = {q["qid"]: q["text"] for q in queries}
    pool = {q: sorted({d for run in RUNS.values() for d in run[q][:10]}) for q in qrels}
    def qrels_juez(sesgo, seed=SEED):
        rng = np.random.default_rng(seed); out, tp, fp, fn, tn = {}, 0, 0, 0, 0
        for q, cand in pool.items():
            out[q] = {}
            for d in cand:
                es = qrels[q].get(d, 0) > 0; lab = juez_simulado(q_text[q], doc_text[d], es, sesgo, rng)
                if lab: out[q][d] = 1
                tp += lab and es; fp += lab and not es; fn += (not lab) and es; tn += (not lab) and not es
        n = tp + fp + fn + tn; po = (tp + tn) / n; pe = ((tp + fp) * (tp + fn) + (fn + tn) * (fp + tn)) / n**2
        return out, (po - pe) / (1 - pe)
    filas = []
    for sesgo in (0.0, 0.4, 0.8):
        qj, kappa = qrels_juez(sesgo)
        for n in ("BM25", "LSI-48", "RRF(BM25+LSI)"):
            filas.append({"sesgo": sesgo, "sistema": n, "nDCG@10 (juez)": evaluate(RUNS[n], qj, 10)["ndcg@10"], "κ juez vs verdad": kappa})
    jdf = pd.DataFrame(filas); verdad_nd = {n: evaluate(RUNS[n], qrels, 10)["ndcg@10"] for n in RUNS if n in ("BM25", "LSI-48", "RRF(BM25+LSI)")}
    fig, ax = plt.subplots(figsize=(8, 3.6)); w = .2; sist = list(verdad_nd)
    ax.bar(np.arange(3) - 1.5*w, [verdad_nd[s] for s in sist], w, color=GRIS, label="verdad (humanos)")
    for i, (sesgo, c) in enumerate(zip((0.0, 0.4, 0.8), (VERDE, NARANJA, ROJO))):
        sub = jdf[jdf.sesgo == sesgo].set_index("sistema").loc[sist]
        ax.bar(np.arange(3) + (i - 0.5) * w, sub["nDCG@10 (juez)"], w, color=c, label=f"juez sesgo={sesgo} (κ={sub['κ juez vs verdad'].iloc[0]:.2f})")
    ax.set_xticks(range(3)); ax.set_xticklabels(sist); ax.set_ylabel("nDCG@10"); ax.set_ylim(0, .95); ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper center"); ax.set_title("Un juez sesgado hacia el solapamiento léxico cambia la tabla de resultados")
    plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** (1) Incluso con sesgo 0 los valores **absolutos suben** respecto a la verdad: el juez solo etiqueta el *pool* (top-10 de los tres sistemas), los relevantes fuera del pool desaparecen del IDCG, y eso infla el nDCG (el mismo mecanismo que en 6.2). (2) Al subir el sesgo léxico, los documentos *irrelevantes pero con palabras de la query* se etiquetan como relevantes: las **diferencias entre sistemas se comprimen y se reordenan** (BM25 recupera terreno) y κ cae de 0.8 a ≈ 0.4. Un juez «razonable en promedio» puede sesgar la comparación justo en la dirección que te interesa evaluar (léxico vs semántico).
    """)
    nb.md("""
    ### 7.2 Plantilla de prompt y celda opcional con API
    Buenas prácticas verificables en la literatura de LLM-judge: rúbrica con grados definidos, pedir la etiqueta **después** de un razonamiento corto (o solo etiqueta con `temperature=0` si priorizas coste), barajar el orden cuando compares pares, y medir κ contra humanos.
    La celda está **protegida**: solo llama a la API si defines `ANTHROPIC_API_KEY` y `JUDGE_MODEL` (el identificador del modelo lo eliges tú; no lo fijamos porque cambia con el tiempo).
    """)
    nb.code(r'''
    PROMPT_JUEZ = """Eres un evaluador de relevancia para un buscador de documentación técnica.
    Consulta: {query}
    Documento: {doc}

    Grados: 0 = irrelevante (aunque comparta palabras con la consulta); 1 = tangencial; 2 = responde parcialmente; 3 = responde completamente.
    Considera el SIGNIFICADO, no la coincidencia de palabras. Responde SOLO con un dígito 0-3."""

    JUDGE_MODEL = os.environ.get("JUDGE_MODEL")
    if os.environ.get("ANTHROPIC_API_KEY") and JUDGE_MODEL:
        import anthropic
        client = anthropic.Anthropic()
        def juez_llm(query: str, doc: str) -> int:
            msg = client.messages.create(model=JUDGE_MODEL, max_tokens=5, temperature=0,
                                         messages=[{"role": "user", "content": PROMPT_JUEZ.format(query=query, doc=doc[:1500])}])
            m = re.search(r"[0-3]", msg.content[0].text)
            return int(m.group()) if m else 0
        muestra = [(q, d) for q in list(pool)[:5] for d in pool[q][:4]]
        humano = [int(qrels[q].get(d, 0) > 0) for q, d in muestra]; llm = [int(juez_llm(q_text[q], doc_text[d]) >= 2) for q, d in muestra]
        print(f"κ(LLM, verdad) en {len(muestra)} pares = {cohen_kappa(humano, llm):.2f}")
    else:
        print("Sin ANTHROPIC_API_KEY/JUDGE_MODEL: celda omitida (opcional). Prompt de ejemplo:\n" + PROMPT_JUEZ.format(query="cómo configurar ttl", doc="…")[:250])
    ''')

    # ───────────────────────── 8. Límite de dimensión ─────────────────────────
    nb.md("""
    ## 8. Límites teóricos de los embeddings de dimensión fija (LIMIT)

    Un buscador *denso* representa cada documento con un vector de dimensión $d$ y cada query con otro; el top-$k$ de una query es el conjunto de los $k$ documentos con mayor producto punto.
    **Pregunta:** ¿cuántos *subconjuntos distintos* de $k$ documentos puede devolver un conjunto de $n$ documentos al variar la query? Si el producto necesita devolver **cualquier** par posible (k = 2) y hay $\\binom{n}{2}$ pares, la dimensión no puede ser arbitrariamente pequeña.

    **Resultado (Weller, Boratko, Naim, Lee; arXiv ago-2025, ICLR 2026).** Con documentos como vectores unitarios y una query que realiza un subconjunto $S$ con margen $\\ge 2\\gamma$ sobre el resto, un argumento de empaquetamiento de esferas da:

    $$\\binom{n}{k}\\le\\left(1+\\tfrac{1}{\\gamma}\\right)^{d}\\ \\Longrightarrow\\ d\\ \\ge\\ \\frac{\\log\\binom{n}{k}}{\\log(1+1/\\gamma)}$$

    Es una **cota inferior optimista** (ignora que el modelo se entrena con gradiente y que su texto restringe los vectores). Los autores muestran además, optimizando **embeddings libres** (sin pasar por ningún encoder) directamente sobre las qrels de test, que el *tamaño crítico* de corpus $n$ que aún se resuelve crece de forma polinómica con $d$,
    y construyen **LIMIT**, un dataset realista y trivialmente simple («¿a quién le gusta X?») donde los embedders de SOTA fallan. Verificaremos la cota y reproduciremos el experimento de embeddings libres en miniatura.
    """)
    nb.code(r'''
    from math import lgamma, log, ceil
    def d_minimo(n: int, k: int, gamma: float = 0.1) -> int:
        """Cota inferior de dimensión: log C(n,k) / log(1+1/γ)  (usa lgamma: C(n,k) enorme)."""
        logC = lgamma(n + 1) - lgamma(k + 1) - lgamma(n - k + 1)
        return ceil(logC / log(1 + 1 / gamma))
    filas = [{"n (docs)": f"{n:,}", "k": k, "d ≥ (γ=0.1)": d_minimo(n, k)} for n in (10**4, 10**6, 10**9) for k in (2, 10, 100)]
    pd.DataFrame(filas)
    ''')
    nb.md("""
    > 🔬 **Comprobación contra el paper.** Para $n=10^6$: $k=2$ da $d\\ge 12$ y $k=100$ da $d\\ge 425$ (con $\\gamma=0.1$): son los valores de la Tabla 1 de Weller et al. que reproduce la celda.
    > La cota crece solo **logarítmicamente** con $n$ pero **casi linealmente con $k$**: pedir top-100 *exacto* para todas las combinaciones es mucho más exigente que top-2.
    """)
    nb.md("### 8.1 Experimento de embeddings libres (miniatura del de los autores)\nOptimizamos directamente vectores de documentos y de queries (sin encoder) para que **cada par** de documentos sea el top-2 de alguna query. Buscamos el mayor $n$ que se logra para cada $d$.")
    nb.code(r'''
    import torch.nn.functional as F
    def realizable(n: int, d: int, steps: int = 600, lr: float = 0.05, seed: int = 0, gamma: float = 0.01) -> bool:
        """¿Existen vectores unitarios tales que, para TODO par (i,j), una query tiene a i,j como top-2? (optimiza margen)."""
        g = torch.Generator().manual_seed(seed)
        pairs = torch.combinations(torch.arange(n), 2); m = len(pairs); rows = torch.arange(m)
        D = torch.randn(n, d, generator=g).requires_grad_(); Q = torch.randn(m, d, generator=g).requires_grad_()
        opt = torch.optim.Adam([D, Q], lr=lr)
        mask = torch.ones(m, n, dtype=torch.bool); mask[rows, pairs[:, 0]] = False; mask[rows, pairs[:, 1]] = False
        for _ in range(steps):
            S = F.normalize(Q, dim=1) @ F.normalize(D, dim=1).T
            margin = S.gather(1, pairs).min(1).values - S.masked_fill(~mask, -2).max(1).values
            if bool((margin > 0).all()): return True
            loss = F.relu(gamma - margin).mean(); opt.zero_grad(); loss.backward(); opt.step()
        return False

    dims = [2, 3, 4, 5, 6, 8] if FAST_DEV_RUN else [2, 3, 4, 5, 6, 8, 10, 12]
    crit, t0 = {}, time.time()
    for d in dims:
        best = 0
        for n in range(3, 80):
            if any(realizable(n, d, seed=s) for s in range(2)): best = n
            elif n > best + 3: break
        crit[d] = best
    print(f"n crítico por dimensión: {crit}   ({time.time()-t0:.0f}s)")
    ''')
    nb.code(r'''
    dd = np.array(list(crit)); nn = np.array(list(crit.values()))
    cubic_paper = lambda d: -10.5322 + 4.0309 * d + 0.0520 * d**2 + 0.0037 * d**3      # ajuste reportado por Weller et al. (v2)
    fig, ax = plt.subplots(1, 2, figsize=(12, 3.8))
    ax[0].plot(dd, nn, "o-", color=AZUL, label="este notebook (embeddings libres, 2 semillas)")
    ax[0].plot(dd, cubic_paper(dd), "--", color=NARANJA, label="ajuste cúbico del paper (v2)")
    ax[0].set_xlabel("dimensión d"); ax[0].set_ylabel("n crítico (todos los pares son top-2)"); ax[0].legend(frameon=False); ax[0].set_title("El corpus que cabe crece polinómicamente con d")
    N_TOT = crit[dims[-1]]
    pares_tot = N_TOT * (N_TOT - 1) // 2
    ax[1].bar(["pares posibles\n(n=%d)" % N_TOT, "pares que un\nvector 2-D puede devolver"], [pares_tot, N_TOT], color=[GRIS, ROJO])
    ax[1].set_title("En d=2 solo caben ~n pares adyacentes de C(n,2)"); plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** (1) El $n$ crítico **crece rápido pero no exponencialmente** con $d$, y nuestras curvas, aun con pocas semillas y pasos, siguen la tendencia del ajuste del paper (no esperes coincidencia exacta: depende de optimizador y pasos).
    > (2) En $d=2$ los documentos son puntos de una circunferencia y una query solo puede devolver pares **adyacentes**: de $\\binom{n}{2}$ pares posibles, ~$n$ son alcanzables.
    > (3) Esto es el **mejor caso** (vectores libres con acceso a las qrels). Un embedder real, que genera los vectores desde texto, lo tiene peor.
    """)
    nb.gemini(
        "imagen", "M15-IMG-2", "Por qué dimensión pequeña no puede devolver todos los pares",
        "Intuición geométrica del límite: 5 documentos como puntos en una circunferencia (d=2); cada query es una dirección y solo devuelve pares adyacentes; 5 de 10 pares son alcanzables.",
        """
        Diagrama técnico limpio, fondo blanco, paleta sobria (azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280), tipografía sans-serif legible, flechas claras, sin ilustraciones decorativas. 16:9.
        Composición con dos paneles lado a lado.
        Panel izquierdo, título «d = 2: 5 documentos en una circunferencia»: una circunferencia gris fina centrada; sobre ella 5 puntos azules etiquetados A, B, C, D, E a ángulos 90°, 18°, −54°, −126°, 162° (pentágono regular). Desde el centro, una flecha naranja larga etiquetada «query u» apunta entre A y B; los puntos A y B quedan resaltados en verde con el texto «top-2 = {A, B}».
        Panel derecho, título «Pares posibles vs. pares alcanzables»: una cuadrícula 5×5 triangular con los 10 pares AB, AC, AD, AE, BC, BD, BE, CD, CE, DE; los 5 pares adyacentes (AB, BC, CD, DE, EA) en verde con una marca ✓ y los otros 5 (AC, AD, BD, BE, CE) en gris tachados con una cruz.
        Debajo, una línea de texto: «Con d = 2 solo 5 de 10 pares son top-2 de alguna query. Más dimensiones → más pares alcanzables».
        Evita: texto ilegible o inventado, más de 5 puntos, sombras 3D, ilustraciones decorativas, flechas ambiguas.
        """,
        "Pentágono de cinco documentos sobre una circunferencia y una cuadrícula que muestra que solo cinco de los diez pares son el top-2 de alguna query.",
        """
              A
          E       B        query u apunta entre A y B  -> top-2 = {A,B}
            D   C          pares alcanzables: AB BC CD DE EA (5 de 10)
        """,
    )
    nb.md("""
    > 👀 **Qué debes observar:** con 5 documentos en un círculo ($d = 2$), una query es una dirección y su top-2 son siempre dos vecinos **adyacentes**: solo 5 de los $\\binom{5}{2} = 10$ pares son alcanzables, por mucho que entrenes. Ese es el límite de LIMIT en miniatura: no es un fallo de entrenamiento sino de **geometría**. BM25 no lo sufre porque cada término es su propia dimensión (el vocabulario hace de $d$ enorme), y lo comprobarás en la celda siguiente.
    """)
    nb.md("""
    ### 8.2 LIMIT en miniatura: BM25 contra un «embedding» de dimensión baja
    Réplica de la construcción del paper: $n$ personas, un atributo único por **cada par** de personas («le gusta *kobelu*» solo a las personas $i$ y $j$); la query «¿a quién le gusta *kobelu*?» tiene exactamente 2 relevantes.
    Evaluamos BM25 (espacio de dimensión ≈ tamaño del vocabulario) y LSI con dimensión $d$ creciente.
    """)
    nb.code(r'''
    def genera_limit(n_personas: int = 24, seed: int = SEED):
        rng = random.Random(seed); syl = ["ka", "ko", "mi", "su", "ta", "ne", "lo", "ri", "pa", "ve", "zu", "do"]
        nombres, usados = [], set()
        def palabra():
            while True:
                w = "".join(rng.choice(syl) for _ in range(3))
                if w not in usados: usados.add(w); return w
        gustos = {i: [] for i in range(n_personas)}; qs, qr = [], {}
        for i in range(n_personas):
            for j in range(i + 1, n_personas):
                a = palabra(); gustos[i].append(a); gustos[j].append(a)
                qid = f"lq{i}-{j}"; qs.append({"qid": qid, "lang": "en", "text": f"who likes {a}"}); qr[qid] = {f"p{i}": 1, f"p{j}": 1}
        ds = [{"id": f"p{i}", "lang": "en", "text": f"person {i} likes " + " ".join(rng.sample(gustos[i], len(gustos[i])))} for i in range(n_personas)]
        return ds, qs, qr

    L_docs, L_qs, L_qr = genera_limit(24 if FAST_DEV_RUN else 40)
    L_ids, L_txt = [d["id"] for d in L_docs], [d["text"] for d in L_docs]
    print(f"{len(L_docs)} docs, {len(L_qs)} queries (= todos los C(n,2) pares), {len(L_qr[L_qs[0]['qid']])} relevantes por query")
    bm = BM25(tok_simple).fit(L_txt, L_ids); r_bm = build_run(bm.scores, L_qs, L_ids, 10)
    res_limit = {"BM25": float(np.mean([recall_at_k(r_bm[q["qid"]], L_qr[q["qid"]], 2) for q in L_qs]))}
    curva = {}
    for d in (2, 3, 4, 6, 8, 12, 16, len(L_docs) - 1):
        m = LSI(dim=d, seed=SEED).fit(L_txt, L_ids); rr_ = build_run(m.scores, L_qs, L_ids, 10)
        curva[d] = float(np.mean([recall_at_k(rr_[q["qid"]], L_qr[q["qid"]], 2) for q in L_qs]))
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.plot(list(curva), list(curva.values()), "o-", color=AZUL, label="LSI (denso) con dimensión d")
    ax.axhline(res_limit["BM25"], color=NARANJA, ls="--", label=f"BM25 (≈ dimensión del vocabulario): {res_limit['BM25']:.2f}")
    ax.set_xscale("log", base=2); ax.set_xlabel("dimensión d (escala log)"); ax.set_ylabel("Recall@2"); ax.legend(frameon=False); ax.set_title("LIMIT en miniatura: la dimensión limita al denso, no al léxico")
    plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** Con $d$ pequeña el Recall@2 del denso es bajo y sube con $d$; BM25 resuelve casi todo porque vive en un espacio de dimensión ≈ tamaño del vocabulario.
    > **Cuidado con la conclusión:** este juguete *exagera* (las queries no tienen semántica: son tokens únicos). El paper muestra en el LIMIT real (50 K documentos, 1 000 queries, k = 2) que BM25 llega a 85.7 de Recall@2 (93.6 de Recall@100) mientras que, p. ej., Gemini Embed (3072-d) llega a 1.6 de Recall@2 y 10.0 de Recall@100 (Tabla 5 del paper, v2, a oct-2026), y que un multi-vector (GTE-ModernColBERT) queda en medio (23.1 de Recall@2).
    > Lectura madura: **la dimensión importa cuando la consulta pide combinaciones arbitrarias** (instrucciones, razonamiento, filtros implícitos). Para búsqueda temática típica, los embeddings siguen funcionando; por eso el híbrido (módulo 13) y el reranking son la respuesta práctica.
    """)

    # ───────────────────────── 9. Contaminación ─────────────────────────
    nb.md("""
    ## 9. Contaminación y sobreajuste al leaderboard

    **Contaminación** = el modelo vio datos de evaluación durante el entrenamiento (directa: las queries/documentos de test; indirecta: paráfrasis o el mismo corpus de Wikipedia en varios benchmarks).
    **Sobreajuste al leaderboard** = aunque no haya fuga, elegir el modelo/hiperparámetros por la puntuación en un test público fijo lo convierte en *validation set*.

    Lo que se sabe (y lo que no):
    - Los autores de **E5-Mistral** reportan haber buscado coincidencias exactas entre su entrenamiento y los test de MTEB: encontraron muy pocas (p. ej. 4 preguntas de DBpedia también en TriviaQA) y juzgaron su efecto insignificante; también señalan que varios datasets de retrieval comparten el mismo corpus de Wikipedia. Es una auditoría **de un modelo**, no del leaderboard.
    - Es habitual entrenar con los *train splits* de los datasets de MTEB. No es trampa, pero hace que «zero-shot» deje de serlo; la leaderboard de MTEB muestra un porcentaje «zero-shot» por modelo (fracción de tareas cuyo train split no se usó), que conviene mirar.
    - **RTEB** (beta, oct-2025) responde con datasets privados: su paper reporta 48 datasets (28 privados) y una correlación débil de rankings con BEIR/MTEB (ρ = 0.38). 🟡 Es evidencia de que los rankings públicos y privados difieren, no una prueba de cuánto hay de contaminación.

    ### 9.1 Experimento: qué aspecto tiene una fuga y cómo detectarla
    Simulamos la fuga más simple: «expandir» los documentos con las **queries públicas** (como si el entrenamiento las hubiera visto). Medimos el salto en las queries públicas vs las privadas, y un detector de solapamiento de n-gramas.
    """)
    nb.code(r'''
    rng = random.Random(SEED); qs_all = [q["qid"] for q in queries]; rng.shuffle(qs_all)
    publicas, privadas = set(qs_all[: len(qs_all) // 2]), set(qs_all[len(qs_all) // 2:])
    expand = dict(doc_text)
    for q in publicas:
        for d in qrels[q]: expand[d] = expand[d] + " " + q_text[q]          # fuga: el "entrenamiento" vio la query
    def nd_sub(model, subset): 
        run = build_run(model.scores, [q for q in queries if q["qid"] in subset], doc_ids, 10)
        return float(np.mean([ndcg_at_k(run[q], qrels[q], 10) for q in subset]))
    limpio = BM25(tok_simple).fit(doc_texts, doc_ids); sucio = BM25(tok_simple).fit([expand[d] for d in doc_ids], doc_ids)
    def ngramas(texto, n): t = tok_simple(texto); return {tuple(t[i:i + n]) for i in range(len(t) - n + 1)}
    def frac_contaminada(train_texts, test_texts, n=3):
        tr = set().union(*[ngramas(t, n) for t in train_texts]); return np.mean([bool(ngramas(t, n) & tr) for t in test_texts])
    res_c = {"limpio": (nd_sub(limpio, publicas), nd_sub(limpio, privadas)), "contaminado": (nd_sub(sucio, publicas), nd_sub(sucio, privadas))}
    det = {"ref. limpia": frac_contaminada(doc_texts, [q_text[q] for q in publicas]), "tras la fuga": frac_contaminada([expand[d] for d in doc_ids], [q_text[q] for q in publicas])}
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.5)); x = np.arange(2); w = .35
    ax[0].bar(x - w/2, res_c["limpio"], w, color=AZUL, label="modelo limpio"); ax[0].bar(x + w/2, res_c["contaminado"], w, color=ROJO, label="modelo contaminado")
    ax[0].set_xticks(x); ax[0].set_xticklabels(["queries PÚBLICAS\n(vistas en la fuga)", "queries PRIVADAS"]); ax[0].set_ylabel("nDCG@10"); ax[0].legend(frameon=False); ax[0].set_title("La fuga infla solo lo público")
    ax[1].bar(list(det), list(det.values()), color=[VERDE, ROJO]); ax[1].set_ylabel("fracción de queries con un 3-grama en el train"); ax[1].set_title("Detector de solapamiento de n-gramas")
    plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** El modelo contaminado «mejora» muchísimo en lo público y **nada** en lo privado (aquí incluso empeora: el texto añadido es ruido para las demás queries): la brecha público–privado es la huella de la fuga. El detector de n-gramas la señala (con n=3 por la brevedad de nuestras queries; en documentos largos se usan n≈13).
    > Qué hacer: (1) mantén un **set privado** propio y no lo uses para decidir; (2) reporta la brecha público–privado; (3) con modelos de terceros, desconfía de saltos grandes en un benchmark público sin mejora en el privado; (4) fecha las cifras.
    """)

    # ───────────────────────── 10. Drift ─────────────────────────
    nb.md("""
    ## 10. Drift: tu evaluación también caduca
    Hay tres drifts distintos: **de queries** (los usuarios empiezan a preguntar otra cosa), **de corpus** (llegan documentos nuevos con vocabulario nuevo) y **de modelo** (cambias de versión del embedder o del tokenizer).
    El golden set congelado es un *termómetro de laboratorio*: no ve que el tráfico real cambió. Soluciones: ponderar por tráfico, un **set canario** pequeño ejecutado en cada despliegue, y monitorizar la distribución de entradas (p. ej. PSI).
    """)
    nb.code(r'''
    def psi(p, q, eps=1e-6):
        """Population Stability Index entre dos distribuciones discretas. Regla práctica: <0.1 estable, 0.1–0.25 vigilar, >0.25 drift."""
        p, q = np.clip(np.asarray(p, float), eps, None), np.clip(np.asarray(q, float), eps, None); p, q = p / p.sum(), q / q.sum()
        return float(np.sum((p - q) * np.log(p / q)))

    langs = ["es", "en", "code"]; nd_q = dict(zip(per["BM25"]["qids"], per["BM25"]["ndcg"]))
    por_lang = {l: np.array([nd_q[q] for q in nd_q if q_lang[q] == l]) for l in langs}
    rng = np.random.default_rng(SEED); semanas = np.arange(12); base_mix = np.array([.45, .45, .10])
    golden_fijo = evaluate(RUNS["BM25"], qrels, 10)["ndcg@10"]
    filas = []
    for s in semanas:
        code_share = .10 + .30 * s / 11                       # el tráfico migra hacia consultas de código
        mix = np.array([(1 - code_share) / 2, (1 - code_share) / 2, code_share])
        muestra = [rng.choice(por_lang[l], int(round(300 * m))) for l, m in zip(langs, mix)]
        filas.append({"semana": s, "nDCG tráfico real": np.concatenate(muestra).mean(), "nDCG golden fijo": golden_fijo, "PSI mezcla": psi(base_mix, mix)})
    dr = pd.DataFrame(filas)
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.5))
    ax[0].plot(dr.semana, dr["nDCG golden fijo"], "--", color=GRIS, label="golden set fijo (no se entera)"); ax[0].plot(dr.semana, dr["nDCG tráfico real"], "o-", color=ROJO, label="ponderado por tráfico real")
    ax[0].set_xlabel("semana"); ax[0].set_ylabel("nDCG@10 de BM25"); ax[0].legend(frameon=False); ax[0].set_title("La calidad percibida cae aunque el 'benchmark' no cambie")
    ax[1].plot(dr.semana, dr["PSI mezcla"], "o-", color=AZUL); ax[1].axhline(.1, color=NARANJA, ls="--", label="vigilar (0.1)"); ax[1].axhline(.25, color=ROJO, ls="--", label="drift (0.25)")
    ax[1].set_xlabel("semana"); ax[1].set_ylabel("PSI de la mezcla de idiomas"); ax[1].legend(frameon=False); ax[1].set_title("El PSI da la alarma antes de que se queje nadie")
    plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** Cuando el tráfico migra hacia las consultas donde el sistema es peor (aquí, código con tokens `snake_case`), la métrica **ponderada por tráfico** cae mientras el golden fijo permanece plano.
    > El PSI cruza los umbrales de vigilancia/drift semanas antes de que la caída sea evidente en las quejas. Lo desarrollamos en producción en el módulo 18 (monitoreo, A/B).
    """)

    # ───────────────────────── 11. Análisis de errores ─────────────────────────
    nb.md("""
    ## 11. Análisis de errores: de «0.52» a «qué arreglar»
    Una media esconde *dónde* falla el sistema. Receta: (1) **slices** (idioma, longitud, solapamiento léxico con el relevante, tipo de intención); (2) ordenar queries por pérdida; (3) leer 20 fallos y **etiquetar la causa**; (4) cuantificar cada causa y priorizar.
    """)
    nb.code(r'''
    filas = [{"qid": q, "lang": q_lang[q], **{n: per[n]["ndcg"][i] for n in RUNS}} for i, q in enumerate(per["BM25"]["qids"])]
    ea = pd.DataFrame(filas)
    tab = ea.groupby("lang")[list(RUNS)].mean().round(3)
    fig, ax = plt.subplots(figsize=(6.5, 2.8)); im = ax.imshow(tab.values, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(tab.shape[1])); ax.set_xticklabels(tab.columns, fontsize=8); ax.set_yticks(range(tab.shape[0])); ax.set_yticklabels(tab.index)
    for i in range(tab.shape[0]):
        for j in range(tab.shape[1]): ax.text(j, i, f"{tab.values[i, j]:.2f}", ha="center", va="center", fontsize=9)
    ax.set_title("nDCG@10 por idioma de la query y sistema"); ax.grid(False); plt.colorbar(im, ax=ax, shrink=.8); plt.tight_layout(); plt.show()
    print("Peores queries para BM25:"); print(ea.sort_values("BM25").head(5)[["qid", "lang", "BM25", "LSI-48"]].to_string(index=False))
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** El promedio global oculta que las consultas de **código** son el punto débil de BM25 (fila `code`), y que el denso las rescata parcialmente. Una media de 0.5 «mezcla» un 0.8 con un 0.1.
    > Antes de comprar un modelo más grande, mira *por qué* falla la fila roja.
    """)
    nb.code(r'''
    # Diagnóstico de causa: ¿las queries de código fallan porque snake_case NO se parte? (tokenización con criterio de dominio)
    bm25_codigo = BM25(tok_code).fit(doc_texts, doc_ids)
    run_tc = build_run(bm25_codigo.scores, queries, doc_ids, 100); per_tc = evaluate_per_query(run_tc, qrels, 10)
    mask = np.array([q_lang[q] == "code" for q in per_tc["qids"]])
    print(f"BM25 tokenización simple  | code: {per['BM25']['ndcg'][mask].mean():.3f}  todo: {per['BM25']['ndcg'].mean():.3f}")
    print(f"BM25 parte snake_case     | code: {per_tc['ndcg'][mask].mean():.3f}  todo: {per_tc['ndcg'].mean():.3f}")
    d_tc = paired_bootstrap(per_tc["ndcg"][mask], per["BM25"]["ndcg"][mask])
    print(f"Δ en code = {d_tc['diff']:+.3f}  IC95 [{d_tc['ci_low']:+.3f}, {d_tc['ci_high']:+.3f}]  p={d_tc['p_value']:.4f}")
    ''')
    nb.md("""
    > 🔁 **Conexión con tokenización (módulos 01–05).** El fallo de BM25 en código **no es de «semántica»**: es de *tokenización* (`set_ttl` es un único token léxico que nunca coincide con «ttl»).
    > Un buen análisis de errores te devuelve al módulo correcto. Si la causa fuera morfología del español, la acción sería lematizar o usar subwords; si fuera vocabulario, un embedder multilingüe.
    """)
    nb.code(r'''
    # Slice por "dificultad léxica": fracción de términos de la query presentes en algún doc relevante
    def solape(q):
        qt = set(tok_simple(q_text[q])); rel_tokens = set().union(*[set(tok_simple(doc_text[d])) for d in qrels[q]])
        return len(qt & rel_tokens) / max(1, len(qt))
    ea["solape"] = [solape(q) for q in ea.qid]; ea["bin"] = pd.cut(ea.solape, [-.01, .34, .67, 1.0], labels=["bajo", "medio", "alto"])
    g = ea.groupby("bin", observed=True)[["BM25", "LSI-48", "RRF(BM25+LSI)"]].mean()
    ax = g.plot(kind="bar", color=[AZUL, NARANJA, VERDE], figsize=(7, 3.4), rot=0); ax.set_xlabel("solape léxico query–relevantes"); ax.set_ylabel("nDCG@10")
    ax.set_title("El denso gana donde el léxico no ve (solape bajo)"); ax.legend(frameon=False, fontsize=8); plt.tight_layout(); plt.show()
    print(ea.groupby("bin", observed=True).size().rename("nº queries").to_dict())
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** Cuanto menor es el solapamiento léxico, más cae BM25 y más aporta un componente semántico: la justificación empírica del retrieval híbrido (módulo 13) sale del **análisis por slices**, no de la media.
    > Ojo con el tamaño de cada slice: con pocas queries por bin, **calcula IC también por slice** antes de actuar.
    """)

    nb.md("""
    ## 🗺️ Mapa de madurez (estado a oct-2026)
    Ya has implementado las métricas, la estadística, el golden set, el juez LLM, LIMIT, la contaminación, el drift y el análisis de errores; la tabla separa lo consolidado de lo que sigue en debate (🟡) antes de ver cómo lo hacen los equipos en producción.


    | Técnica / práctica | Madurez | Quién / dónde se usa | Fuente |
    |---|---|---|---|
    | nDCG@10, Recall@k, MRR@10 con qrels fijos | 🟢 sólido | BEIR, MTEB (retrieval usa nDCG@10 como métrica principal), TREC | Thakur et al. 2021; Muennighoff et al. 2022 |
    | Benchmarks públicos multi-dominio (BEIR, MTEB/MMTEB, MIRACL) | 🟢 sólido (con límites de contaminación) | Estándar de facto para comparar embedders | Thakur 2021; Enevoldsen 2025; Zhang 2022 |
    | Bootstrap / tests pareados sobre queries | 🟢 sólido en IR clásico, 🟡 poco adoptado en papers de embeddings | Comunidad TREC/SIGIR | Smucker et al. 2007; Urbano et al. 2019 |
    | Golden sets propios + anotación con acuerdo κ | 🟢 sólido | Equipos de búsqueda en producción | práctica de la industria |
    | LLM-as-judge para relevancia | 🟡 emergente y **debatido** | Investigación (Bing/TREC) y equipos de evaluación | Thomas et al. 2023; Soboroff 2024; Clarke & Dietz 2024 |
    | Benchmarks con parte privada contra overfitting (RTEB) | 🟡 emergente (beta lanzada oct-2025) | Hugging Face / comunidad MTEB | RTEB (HF blog, 2025) |
    | Límite teórico de la dimensión del embedding (LIMIT) | 🟡 emergente (resultado teórico sólido; relevancia práctica en discusión) | Investigación (Google DeepMind / JHU) | Weller et al., ICLR 2026 |
    | Monitorización de drift con set canario | 🟢 sólido como práctica; 🟡 como tooling específico de embeddings | Producción | módulo 18 |
    """)
    # ───────────────────────── Cierre ─────────────────────────
    nb.md("""
    ## 12. 🏭 En producción
    - **Evaluación continua, no puntual.** Equipos de búsqueda en producción mantienen (i) un golden set versionado, (ii) un set **canario** pequeño que corre en cada cambio de modelo/índice/tokenizer, y (iii) métricas online (clics, reformulaciones, abandono) que se contrastan periódicamente con las offline. Si offline y online se desacoplan, tu golden set está obsoleto.
    - **MTEB/MMTEB como filtro, tu golden set como decisión.** Los leaderboards sirven para preseleccionar 3–5 modelos; la decisión se toma en datos propios. Los proveedores de embeddings (OpenAI, Google, Cohere, Voyage, Jina…) publican resultados en benchmarks públicos; trátalos como *marketing técnico* hasta reproducirlos en tu dominio.
    - **Anotación asistida por LLM** (triaje, sugerencias) con humanos en el bucle para el set de decisión, medido con κ y re-calibrado al cambiar de modelo-juez.
    - **Costes de re-embedding.** Evaluar un modelo nuevo implica re-indexar el corpus entero; presupuesta ese coste *antes* (módulo 18) y evalúa primero en una muestra con el mismo muestreo de documentos relevantes + negativos duros.
    - **Informe estándar:** métrica principal con IC, diferencia pareada vs baseline con IC y p corregido, tabla por slices, brecha público–privado y la versión exacta de dataset, modelo, tokenizer y semilla.
    """)
    nb.md("""
    ## 13. 🧠 Secretos de la élite
    1. **Siempre diferencia pareada con IC, nunca dos IC separados.** Las queries comparten dificultad; el test pareado detecta mejoras que los IC por sistema esconden (experimento 5.3).
    2. **Un golden set de 100 queries solo distingue diferencias grandes.** La semi-anchura del IC cae como $1/\\sqrt n$; calcula el $n$ necesario con *tu* $\\sigma$ (sección 5.3) antes de prometer «+1 punto».
    3. **Los empates y duplicados son una fuente silenciosa de varianza.** Fija el desempate (orden del corpus) y deduplica el ranking; es el primer sitio donde busco diferencias entre dos implementaciones de la «misma» métrica.
    4. **Qrels incompletos castigan a lo nuevo.** BEIR reconoce sesgo léxico en varios datasets (Thakur et al., sección 6); al evaluar un sistema distinto de los que generaron los qrels, añade su top-k al pool o corrige con juicios nuevos (en TREC-COVID, anotar juicios faltantes subió a los modelos densos).
    5. **Mide la brecha público–privado.** Si tu modelo sube 3 puntos en el benchmark público y 0 en tu set privado, has aprendido el benchmark. Por eso existe RTEB.
    6. **LLM-as-judge sesgado hacia el léxico favorece a BM25.** Alaofi et al. muestran que meter palabras de la query en texto irrelevante engaña a muchos LLMs; valida el juez con casos adversariales antes de confiar en él.
    7. **La dimensión es un presupuesto, no un parámetro libre.** Si tu producto pide combinaciones arbitrarias (instrucciones, filtros implícitos), LIMIT te dice que un vector único tiene un techo; multi-vector, híbrido y reranking existen por eso.
    8. **El análisis de errores por slices decide la hoja de ruta.** En nuestro corpus la «mejora de embedder» que parecía necesaria era un arreglo de tokenización de código (sección 11).
    """)
    nb.md("""
    ## 14. ⚠️ Errores comunes
    - **Evaluar sobre queries que usaste para elegir hiperparámetros** (no reservar test ciego).
    - **Promediar sin mirar la varianza**: 0.52 vs 0.50 con σ=0.35 y 70 queries es ruido.
    - **Comparar sistemas con k, métrica o corpus distintos** (p. ej. comparar tu nDCG@10 con el de un paper que usó otro split o qrels).
    - **Dividir por el número de relevantes devueltos en vez de por el total** (Recall inflado) o **no normalizar embeddings** al comparar coseno vs producto punto.
    - **Descartar silenciosamente las queries sin resultados** (el sistema que no responde sale ganando).
    - **Usar el mismo LLM como generador de queries, juez y sistema** (circularidad).
    - **Citar cifras de leaderboards sin fecha ni versión** del benchmark.
    - **Confiar en nDCG@10 si el producto muestra 3 resultados** (usa la métrica que corresponde a la UI, p. ej. nDCG@3 / MRR).
    """)
    nb.md("""
    ## 15. ✅ Autoevaluación
    Intenta responder antes de abrir cada respuesta.

    <details><summary><b>1. (Cálculo)</b> Ranking <code>[a, b, c, d]</code>, relevancias <code>{b: 2, d: 1, e: 3}</code>. Calcula nDCG@4 (ganancia lineal).</summary>

    DCG = $2/\\log_2 3 + 1/\\log_2 5 = 1.262 + 0.431 = 1.693$. IDCG (mejor orden: $e{=}3, b{=}2, d{=}1$) $= 3/1 + 2/\\log_2 3 + 1/\\log_2 4 = 3 + 1.262 + 0.5 = 4.762$. nDCG@4 $= 0.356$. Observa que *e* no aparece en el ranking pero sí cuenta en el IDCG: el recall perdido penaliza.
    </details>

    <details><summary><b>2. (Cálculo)</b> Tu σ entre queries es 0.30. ¿Cuántas queries necesitas para un IC95 % de semi-anchura ±0.02 sobre una media?</summary>

    $n\\approx(1.96\\cdot\\sigma/h)^2=(1.96\\cdot0.30/0.02)^2\\approx 864$ queries. Si comparas dos sistemas de forma *pareada*, lo relevante es la σ de la diferencia (normalmente menor), así que necesitas menos.
    </details>

    <details><summary><b>3. (Diagnóstico)</b> El embedder nuevo sube +0.02 nDCG@10 sobre 60 queries y el IC95 % pareado es [−0.03, +0.07]. ¿Despliegas?</summary>

    No hay evidencia de mejora: el IC incluye 0. Opciones: ampliar el golden set (necesitas ~4× queries para duplicar la precisión), mirar slices donde se espera la ganancia, o decidir con otros criterios (coste, latencia). Declarar «mejora» sería *p-hacking* por falta de potencia.
    </details>

    <details><summary><b>4. (Diagnóstico)</b> Tu nuevo modelo denso supera a BM25 en tu leaderboard pero los usuarios no lo notan. Da tres hipótesis y cómo las comprobarías.</summary>

    (a) Qrels sesgados o incompletos → añade el pool del nuevo sistema y re-anota una muestra. (b) El golden set no representa el tráfico (drift de queries) → reponderar por tráfico / PSI. (c) Contaminación o sobreajuste al set → brecha público–privado. (d) La UI solo muestra 3 resultados y optimizaste nDCG@10 → mide nDCG@3/MRR.
    </details>

    <details><summary><b>5. (Transferencia)</b> Tienes que evaluar un buscador de contratos en español con 0 anotaciones. Diseña el plan en 5 pasos.</summary>

    (1) Muestra de queries de logs/expertos estratificada por tipo de cláusula; (2) pooling de top-20 de BM25 + 2 embedders; (3) anotación humana con guía de 4 grados sobre 300 queries y doble anotación del 15 % (κ ≥ 0.7); (4) LLM-judge solo para triaje, validado contra humanos; (5) congelar v1.0 con test ciego, métrica nDCG@10 con IC bootstrap, test pareado entre candidatos con Holm, canario semanal para drift.
    </details>

    <details><summary><b>6. (Transferencia)</b> ¿Por qué LIMIT no implica que «los embeddings no sirven»? ¿Qué cambia en tu arquitectura?</summary>

    La cota habla de realizar *todas* las combinaciones posibles de top-$k$ y de un margen dado; las consultas temáticas reales ocupan una fracción minúscula de ese espacio y los embeddings funcionan bien ahí. Pero si el producto admite instrucciones o combinaciones arbitrarias (lógica, filtros), el vector único tiene un techo: usa híbrido (BM25 + denso), multi-vector o reranker, y filtra por metadatos antes del ANN.
    </details>

    <details><summary><b>7. (Diagnóstico)</b> El Recall@10 de BM25 en tu set es 0.81 y el de tu HNSW sobre el mismo embedder es 0.78. ¿Qué evalúa cada número?</summary>

    Ambos son recall de **relevancia** sobre tus qrels. El «recall del ANN» frente a fuerza bruta (módulo 14) es otra cosa: mide cuánto del top-10 exacto recupera el índice aproximado. Pérdida total = error del embedder (qrels) más error del índice (ANN).
    </details>
    """)
    nb.md("""
    ## 16. 📚 Referencias
    **Evaluación y benchmarks**
    - Thakur, Reimers, Rücklé, Srivastava, Gurevych (2021). *BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models*. NeurIPS Datasets & Benchmarks. <https://arxiv.org/abs/2104.08663>
    - Zhang et al. (2022). *Making a MIRACL: Multilingual Information Retrieval Across a Continuum of Languages*. <https://arxiv.org/abs/2210.09984>
    - Muennighoff, Tazi, Magne, Reimers (2022). *MTEB: Massive Text Embedding Benchmark*. <https://arxiv.org/abs/2210.07316>
    - Enevoldsen et al. (2025). *MMTEB: Massive Multilingual Text Embedding Benchmark*. ICLR. <https://arxiv.org/abs/2502.13595>
    - RTEB (2025). *Introducing RTEB: A New Standard for Retrieval Evaluation* (Hugging Face blog) <https://huggingface.co/blog/rteb> y *RTEB: An Overfitting-Resistant Benchmark for Embedding Model Evaluation* (NeurIPS 2026 poster) <https://neurips.cc/virtual/2026/poster/139103>
    - Wadden et al. (2020). *Fact or Fiction: Verifying Scientific Claims* (SciFact). EMNLP. <https://arxiv.org/abs/2004.14974>
    - Wang, Wang, Li (2013). *A Theoretical Analysis of NDCG Type Ranking Measures*. COLT. <https://arxiv.org/abs/1304.6480>
    - Bassani (2022). *ranx: A Blazing-Fast Python Library for Ranking Evaluation and Comparison*. ECIR. <https://github.com/AmenRa/ranx>
    - Craswell, Mitra, Yilmaz, Campos, Lin (2021). *MS MARCO: Benchmarking Ranking Models in the Large-Data Regime*. <https://arxiv.org/abs/2105.04021>
    - Arabzadeh, Vtyurina, Yan, Clarke (2021). *Shallow pooling for sparse labels*. <https://arxiv.org/abs/2109.00062>
    - Krichene & Rendle (2020). *On Sampled Metrics for Item Recommendation*. KDD. <https://research.google/pubs/on-sampled-metrics-for-item-recommendation/> (ver `recsys-course/02_evaluation`)

    **Estadística en IR**
    - Smucker, Allan, Carterette (2007). *A Comparison of Statistical Significance Tests for Information Retrieval Evaluation*. CIKM. DOI 10.1145/1321440.1321528
    - Sakai (2006). *Evaluating Evaluation Metrics based on the Bootstrap*. SIGIR. DOI 10.1145/1148170.1148261
    - Urbano, Lima, Hanjalic (2019). *Statistical Significance Testing in Information Retrieval: An Empirical Analysis of Type I, Type II and Type III Errors*. SIGIR. <https://arxiv.org/abs/1905.11096>

    **LLM-as-judge**
    - Thomas, Spielman, Craswell, Mitra (2023). *Large language models can accurately predict searcher preferences*. <https://arxiv.org/abs/2309.10621>
    - Faggioli et al. (2023). *Perspectives on Large Language Models for Relevance Judgment*. <https://arxiv.org/abs/2304.09161>
    - Soboroff (2024). *Don't Use LLMs to Make Relevance Judgments*. <https://arxiv.org/abs/2409.15133>
    - Clarke & Dietz (2024). *LLM-based relevance assessment still can't replace human relevance assessment*. <https://arxiv.org/abs/2412.17156>
    - Alaofi, Thomas, Scholer, Sanderson (2024). *LLMs can be Fooled into Labelling a Document as Relevant*. SIGIR-AP. <https://arxiv.org/abs/2501.17969>
    - Zheng et al. (2023). *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*. NeurIPS D&B. <https://arxiv.org/abs/2306.05685>

    **Límites de los embeddings y contaminación**
    - Weller, Boratko, Naim, Lee (2025; v2 mar-2026, ICLR 2026). *On the Theoretical Limitations of Embedding-Based Retrieval*. <https://arxiv.org/abs/2508.21038>
    - Reimers & Gurevych (2021). *The Curse of Dense Low-Dimensional Information Retrieval for Large Index Sizes*. ACL. <https://arxiv.org/abs/2012.14210>
    - Wang et al. (2024). *Improving Text Embeddings with Large Language Models* (E5-Mistral; sección de análisis de contaminación). <https://arxiv.org/abs/2401.00368>

    **Material del curso**: [`recsys-course/02_evaluation`](../../recsys-course/02_evaluation/README.md) · módulos 00, 10, 12, 13, 14 y 18.
    """)
