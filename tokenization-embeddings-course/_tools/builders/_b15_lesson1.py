"""Lección 15 · parte 1: cabecera, intuición, setup, métricas."""
from _a6_common import SYNTH_DATA_SRC, CORPUS_SRC, REAL_SRC
from _a6_src15 import METRICS_SRC, STATS_SRC, RETRIEVERS_SRC


def part1(nb):
    nb.md(f"""
    {nb.badge()}

    # Módulo 15 · Evaluación de embeddings y retrieval
    **Tokenización y Embeddings: de BPE a los modelos modernos**

    | | |
    |---|---|
    | **Nivel** | 🟠 Avanzado |
    | **Duración estimada** | ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) |
    | **GPU recomendada** | No necesaria (CPU; ≈ 0 unidades de Colab). Una celda opcional usa un embedder real si hay red |
    | **Prerrequisitos** | 00 (BM25 + mini golden set), 10 (similitud y pooling), 12 (embedders y MTEB), 13 (híbrido, RRF), 14 (recall en ANN) |
    | **Hilo conductor** | Políglota Labs necesita saber **si el nuevo embedder es mejor de verdad** antes de migrar el índice |

    > 🧭 **Ruta núcleo vs ampliación.** Núcleo (≈ 3 h, lo que usa el proyecto): secciones 1–6 (métricas, benchmarks, bootstrap y tests, golden sets) y 11 (análisis de errores: TODO 5 del proyecto).
    > Ampliación (≈ 2 h): secciones 7–10 (LLM-as-judge, límite teórico de la dimensión, contaminación, drift).
    > Si vas justo de tiempo, haz el núcleo y salta a la autoevaluación.
    """)

    nb.md("""
    ## 🎯 Objetivos de aprendizaje
    Al terminar podrás:
    1. **Implementar** nDCG@k, Recall@k y MRR@k (con relevancias graduadas, empates, duplicados y queries sin relevantes) y **verificarlas** con tests y contra `ranx`.
    2. **Calcular a mano** un nDCG y **explicar** por qué cada métrica premia cosas distintas (posición vs cobertura vs primer acierto).
    3. **Construir** un golden set propio (muestreo estratificado, protocolo de anotación, acuerdo entre anotadores κ) y **estimar** cuántas queries necesitas.
    4. **Cuantificar la incertidumbre** con bootstrap (IC al 95 %), comparar sistemas con tests pareados y corregir comparaciones múltiples (Holm).
    5. **Diseñar** un protocolo de *LLM-as-judge* para relevancia y **detectar sus sesgos** (inflado por solapamiento léxico, sesgo de posición/longitud).
    6. **Explicar y reproducir** el límite teórico de los embeddings de dimensión fija (Weller et al., LIMIT) con un experimento de embeddings libres.
    7. **Detectar** contaminación y sobreajuste al leaderboard, y **monitorizar** drift con un set canario.
    8. **Hacer análisis de errores** por *slices* y convertir los fallos en acciones (tokenización, híbrido, datos).
    """)

    nb.md("""
    ## 🔁 Conexión con módulos anteriores
    Antes de empezar, intenta responder sin mirar (recuperación activa):

    <details><summary><b>1.</b> (Módulo 00) En el baseline BM25 de Políglota, ¿por qué reportamos nDCG@10 y no solo «accuracy»?</summary>

    Porque la tarea es *ranking*: importa **en qué posición** aparece lo relevante, no solo si aparece. La accuracy ni siquiera está definida para una lista ordenada con varios relevantes.
    </details>

    <details><summary><b>2.</b> (Módulo 10) Con vectores L2-normalizados, ¿qué relación hay entre coseno, producto escalar y distancia L2? ¿Por qué importa al evaluar?</summary>

    Coseno = producto escalar; y $\\lVert a-b\\rVert^2 = 2-2\\cos(a,b)$. Los tres **ordenan igual**, así que dan el mismo ranking y las mismas métricas. Si olvidas normalizar, el producto escalar favorece a los vectores de mayor norma y el ranking cambia: una causa clásica de «el embedder nuevo es peor» que es solo un bug de evaluación.
    </details>

    <details><summary><b>3.</b> (Módulo 13) ¿Qué hace Reciprocal Rank Fusion y por qué no necesita calibrar escalas?</summary>

    Suma $1/(k+\\text{rango})$ sobre las listas de cada retriever. Solo usa **rangos**, por lo que ignora que BM25 devuelve scores en $[0,\\infty)$ y el coseno en $[-1,1]$.
    </details>

    <details><summary><b>4.</b> (Módulo 14) El «recall@10» de un índice ANN (HNSW vs fuerza bruta) y el «Recall@10» de relevancia de este módulo, ¿son la misma cosa?</summary>

    **No.** El recall del ANN mide fidelidad al vecino exacto *del mismo embedder*; el de este módulo mide cuántos documentos **relevantes según humanos** recuperas. Un ANN con recall 1.0 sobre un embedder malo sigue siendo malo. Son dos capas de error que se componen.
    </details>

    <details><summary><b>5.</b> (Módulos 04 y 01, Diagnóstico) Un embedder nuevo sube el nDCG@10 global, pero las queries en español empeoran. Antes de culpar al modelo, ¿qué dos causas del bloque A comprobarías?</summary>

    (a) **Truncado por prima de tokens** (04): si el nuevo modelo tiene peor fertilidad en español, los documentos ES se cortan antes en `max_seq_length` y pierden contenido; (b) **normalización asimétrica** (01): texto ES con acentos en NFD en el índice y NFC en las queries (o al revés). Ambas se ven solo **por slice** de idioma, que es lo que construye la sección 11; el número global las esconde.
    </details>
    """)


    # ───────────────────────── 1. Intuición ─────────────────────────
    nb.md("""
    ## 1. Intuición: evaluar es la parte difícil

    Entrenar un embedder es *relativamente* fácil; saber si es **mejor** que el anterior es lo difícil. Tres cosas hacen que una mejora aparente sea falsa:

    1. **La métrica mide otra cosa** que tu producto (p. ej. optimizas Recall@100 y al usuario solo le importa el top-3).
    2. **El set de queries es pequeño o sesgado**, y la diferencia es ruido (¡o los qrels son incompletos y castigan al sistema nuevo!).
    3. **El benchmark está contaminado o sobreajustado**: el modelo vio las preguntas durante el entrenamiento.

    **Analogía con recsys.** Si hiciste el curso `recsys-course`, esto es el mismo problema: allí construiste `cinematch_eval.py` y viste que
    las *sampled metrics* pueden **invertir** el ranking de modelos y que sin intervalos de confianza no sabes si 0.01 de nDCG es algo. Aquí heredamos esas lecciones
    (ver [`recsys-course/02_evaluation`](../../recsys-course/02_evaluation/README.md)) y las adaptamos al retrieval de texto: **no repetimos** la derivación de nDCG/AP/AUC
    ni el catálogo beyond-accuracy; nos centramos en lo específico de embeddings (qrels dispersos, benchmarks de texto, LLM-as-judge, límites de dimensión, contaminación).

    **Analogía con compresión/ML clásico.** El golden set es tu *test set*; reutilizarlo para elegir modelos lo convierte en *validation set* sin que te des cuenta (el equivalente a hacer *p-hacking*). Un solo número sin barra de error es como reportar un bitrate sin decir cuántos archivos mediste.
    """)

    nb.gemini(
        "imagen", "M15-IMG-01", "Pipeline de evaluación de retrieval y dónde se rompe",
        "Vista general del módulo: golden set (queries + qrels) → run del sistema → métricas por query → agregación con IC y tests; con los 5 puntos de fallo marcados.",
        """
        Diagrama técnico limpio, fondo blanco, paleta sobria (azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280), tipografía sans-serif legible, flechas claras, sin ilustraciones decorativas. 16:9.

        Composición de izquierda a derecha en 4 bloques conectados por flechas grises gruesas:
        1) Bloque azul «GOLDEN SET» con dos cajas internas: «Queries (qid, texto, idioma)» y «Qrels: qid → {doc_id: relevancia}».
        2) Bloque verde «SISTEMA A EVALUAR» con una caja «Embedder + índice (BM25 / denso / híbrido)» que produce «RUN: qid → lista ordenada de doc_id».
        3) Bloque azul «MÉTRICA POR QUERY» con tres cajas pequeñas apiladas: «nDCG@10», «Recall@k», «MRR@10» y debajo un vector de números «[0.82, 0.00, 1.00, 0.45, …]».
        4) Bloque naranja «AGREGACIÓN CON INCERTIDUMBRE» con: «Media + IC 95 % (bootstrap sobre queries)» y «Test pareado A vs B + corrección de Holm».
        Debajo de cada bloque, un pequeño círculo naranja numerado con una advertencia en texto corto:
        ① bajo el bloque 1: «Qrels incompletos (pooling sesgado)».
        ② bajo el bloque 1: «Contaminación: el modelo vio el test».
        ③ bajo el bloque 2: «Empates y duplicados en el ranking».
        ④ bajo el bloque 3: «Queries sin relevantes».
        ⑤ bajo el bloque 4: «Diferencia dentro del ruido».
        Título superior: «Cómo se evalúa un buscador semántico». Texto inferior pequeño en gris: «Cada flecha es una fuente de error».
        Evita: texto ilegible o inventado, ilustraciones decorativas, sombras 3D, más de 4 bloques principales, flechas ambiguas que se crucen.
        """,
        "Diagrama de cuatro bloques: golden set, sistema, métrica por query y agregación con IC; cinco advertencias numeradas de dónde falla la evaluación.",
        """
        [GOLDEN SET]──►[SISTEMA]──►[MÉTRICA/QUERY]──►[AGREGACIÓN + IC + TESTS]
         ① qrels incompletos   ③ empates/duplicados  ④ queries sin relevantes  ⑤ diferencia ≈ ruido
         ② contaminación
        """,
    )
    nb.md("""
    > 👀 **Qué debes observar.** La evaluación no es «un número»: es una *cadena* con cinco puntos donde puedes equivocarte sin que salte ningún error.
    > A lo largo del módulo cada sección ataca uno: ①② en las secciones 6 y 10, ③④ en la 3, ⑤ en la 5.
    """)

    # ───────────────────────── 2. Setup ─────────────────────────
    nb.md("## 2. Entorno, corpus Políglota y sistemas de referencia")
    nb.code("""
    !pip install -q numpy scipy scikit-learn matplotlib pandas torch ranx datasets sentence-transformers
    """)
    nb.code(r'''
    import os, re, math, random, time, warnings
    import numpy as np, pandas as pd
    import matplotlib.pyplot as plt
    warnings.filterwarnings("ignore")

    SEED = 42
    FAST_DEV_RUN = True          # True: tamaños diminutos (CPU, minutos). False: corpus más grande
    random.seed(SEED); np.random.seed(SEED)
    try:
        import torch
        torch.manual_seed(SEED)
        if FAST_DEV_RUN: torch.set_num_threads(1)
        device = "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        torch, device = None, "cpu"

    AZUL, NARANJA, VERDE, GRIS, ROJO = "#1F6FEB", "#F28E2B", "#2CA02C", "#6B7280", "#D62728"
    plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.alpha": .25, "axes.titlesize": 11, "axes.labelsize": 10})
    print(f"device={device} · FAST_DEV_RUN={FAST_DEV_RUN} · semilla={SEED}")
    ''')
    nb.md("""
    ### Utilidades del corpus Políglota (`carga_corpus`)
    Contrato común del curso: `carga_corpus(fast_dev) -> {"docs", "queries", "qrels", "source"}`. Este notebook es autocontenido, así que incluye su copia
    (cadena **oficial → espejo → sintético**). ⚠️ *Diferencia respecto al módulo 00:* aquí el sintético tiene **huecos léxicos a propósito** (las queries usan sinónimos raros), porque
    un benchmark en el que BM25 saca 0.98 no sirve para comparar sistemas.
    """)
    nb.code(SYNTH_DATA_SRC)
    nb.code(CORPUS_SRC)
    nb.code(REAL_SRC)
    nb.code(r'''
    corpus = carga_corpus(fast_dev=FAST_DEV_RUN)
    docs, queries, qrels = corpus["docs"], corpus["queries"], corpus["qrels"]
    doc_ids, doc_texts = [d["id"] for d in docs], [d["text"] for d in docs]
    q_lang = {q["qid"]: q["lang"] for q in queries}
    print("fuente:", corpus["source"], "| docs:", len(docs), "| queries:", len(queries))
    print(pd.DataFrame(docs).lang.value_counts().to_dict(), "docs por idioma;", pd.Series(q_lang).value_counts().to_dict(), "queries por idioma")
    print("relevantes por query (media):", np.mean([len(v) for v in qrels.values()]).round(2))
    for q in queries[:3]: print(" ", q["qid"], "→", q["text"])
    ''')
    nb.md("""
    ## 3. Métricas: qué miden y cómo implementarlas sin errores

    ### 3.1 Definiciones (con cada símbolo)
    Para una query $q$, un ranking $\\pi = (d_1, d_2, \\dots)$ y relevancias $\\text{rel}(d)\\ge 0$ (0 = no relevante o no juzgado):

    $$\\text{DCG@}k=\\sum_{i=1}^{k}\\frac{g(\\text{rel}(d_i))}{\\log_2(i+1)},\\qquad \\text{nDCG@}k=\\frac{\\text{DCG@}k}{\\text{IDCG@}k}$$

    - $g(r)=r$ (ganancia lineal, **la de `trec_eval`/BEIR/MTEB**) o $g(r)=2^r-1$ (Burges; premia mucho más lo muy relevante).
    - $\\text{IDCG@}k$ es el DCG del **mejor ranking posible** con los documentos juzgados (se ordenan las relevancias de mayor a menor y se toman $k$).
    - El descuento $1/\\log_2(i+1)$ vale $1$ en la posición 1, $0.63$ en la 2, $0.5$ en la 3… y $0.29$ en la 10.

    $$\\text{Recall@}k=\\frac{|\\{d\\in\\pi_{1..k}:\\text{rel}(d)>0\\}|}{|\\{d:\\text{rel}(d)>0\\}|},\\qquad \\text{MRR@}k=\\frac{1}{\\text{rango del 1.º relevante}}\\ (\\text{0 si no está en el top-}k)$$

    - **nDCG** premia *posición* y admite relevancia graduada → métrica principal de BEIR/MTEB-retrieval.
    - **Recall@k** premia *cobertura*: crítico si hay un reranker después (pipeline de dos etapas: Recall@100 del primero acota lo que el segundo puede lograr).
    - **MRR** solo mira el *primer acierto*: útil para QA con una respuesta, ciego a todo lo demás.

    ### 3.2 Ejemplo resuelto a mano
    Ranking `[d3, d1, d9, d2, d7]`, relevancias `{d1: 3, d2: 2, d5: 1}` ($d_5$ no aparece en el ranking). Con $k=5$:

    - $\\text{DCG}=\\frac{3}{\\log_2 3}+\\frac{2}{\\log_2 5}$ (d1 en posición 2, d2 en la 4) $=1.893+0.861=2.754$
    - $\\text{IDCG}=\\frac{3}{\\log_2 2}+\\frac{2}{\\log_2 3}+\\frac{1}{\\log_2 4}=3+1.262+0.5=4.762$
    - $\\text{nDCG@5}=0.578$ · $\\text{Recall@5}=2/3$ · $\\text{MRR}=1/2$
    """)
    nb.md("### 3.3 Implementación (versión canónica del curso)\nLas convenciones son las de `trec_eval`/`ranx`; las decisiones sutiles están en los docstrings y las verificamos con tests justo después.")
    nb.code(METRICS_SRC)
    nb.code(r'''
    ranked = ["d3", "d1", "d9", "d2", "d7"]; rels = {"d1": 3, "d2": 2, "d5": 1}
    dcg_mano  = 3 / math.log2(3) + 2 / math.log2(5)
    idcg_mano = 3 / math.log2(2) + 2 / math.log2(3) + 1 / math.log2(4)
    print(f"a mano:  DCG={dcg_mano:.3f}  IDCG={idcg_mano:.3f}  nDCG@5={dcg_mano/idcg_mano:.3f}")
    print(f"código:  nDCG@5={ndcg_at_k(ranked, rels, 5):.3f}  Recall@5={recall_at_k(ranked, rels, 5):.3f}  MRR@5={mrr_at_k(ranked, rels, 5):.3f}")
    ''')
    nb.md("""
    ### 3.4 Tests: los bordes donde fallan las implementaciones caseras
    Cada línea es un bug real que he visto en repos de evaluación: duplicados que puntúan dos veces, `argsort` inestable con empates, divisiones por cero cuando una query no tiene relevantes, `k` mayor que la lista…
    """)
    nb.code(r'''
    def test_metricas():
        close = lambda a, b: abs(a - b) < 1e-9
        # 1) cálculo a mano
        assert close(ndcg_at_k(ranked, rels, 5), dcg_mano / idcg_mano)
        # 2) ranking ideal => nDCG = 1; ranking peor => estrictamente menor
        ideal = ["d1", "d2", "d5", "x"]; assert close(ndcg_at_k(ideal, rels, 10), 1.0)
        assert ndcg_at_k(["x", "d1", "d2", "d5"], rels, 10) < 1.0
        # 3) queries sin relevantes: 0.0 y sin excepción (el agregador decide si las excluye)
        assert ndcg_at_k(ranked, {}, 10) == recall_at_k(ranked, {}, 10) == mrr_at_k(ranked, {}, 10) == 0.0
        # 4) duplicados: un doc repetido NO puntúa dos veces
        assert close(ndcg_at_k(["d1", "d1", "d1"], {"d1": 1, "d2": 1}, 10), ndcg_at_k(["d1"], {"d1": 1, "d2": 1}, 10))
        assert recall_at_k(["d1", "d1"], {"d1": 1, "d2": 1}, 10) == 0.5
        # 5) k mayor que la lista, y k=1
        assert close(recall_at_k(["d1"], {"d1": 1}, 100), 1.0) and mrr_at_k(["x", "d1"], {"d1": 1}, 1) == 0.0
        # 6) relevancia graduada importa: invertir [3,2] cambia el nDCG; ganancia exponencial amplifica la diferencia
        a, b = ["d1", "d2"], ["d2", "d1"]
        assert ndcg_at_k(a, rels, 2) > ndcg_at_k(b, rels, 2)
        assert (ndcg_at_k(a, rels, 2, exp_gain=True) - ndcg_at_k(b, rels, 2, exp_gain=True)) > (ndcg_at_k(a, rels, 2) - ndcg_at_k(b, rels, 2))
        # 7) Recall@k es monótona en k; precision divide por k siempre
        assert all(recall_at_k(ranked, rels, k) <= recall_at_k(ranked, rels, k + 1) for k in range(1, 6))
        assert precision_at_k(["d1"], {"d1": 1}, 10) == 0.1
        # 8) empates: orden determinista = orden del corpus (no depende del algoritmo de argsort)
        ids = ["a", "b", "c", "d"]; sc = np.array([1.0, 2.0, 2.0, 2.0])
        assert rank_from_scores(sc, ids) == ["b", "c", "d", "a"] == rank_from_scores(sc.copy(), ids)
        # 9) un doc relevante con relevancia 0 explícita NO cuenta como relevante
        assert recall_at_k(["d1"], {"d1": 0, "d2": 1}, 5) == 0.0
        return "✅ 9 grupos de tests OK"
    print(test_metricas())
    ''')
    nb.md("""
    > ⚠️ **Cuidado con los empates.** Con modelos cuantizados o scores enteros (BM25 con documentos idénticos, embeddings binarios con distancia de Hamming) los empates abundan.
    > Si ordenas con `np.argsort` sin `kind="stable"`, **dos implementaciones (o el mismo código con otro orden de entrada o versión de NumPy) pueden dar métricas distintas**. Fijar el desempate (aquí: orden del corpus) es parte del protocolo.
    """)
