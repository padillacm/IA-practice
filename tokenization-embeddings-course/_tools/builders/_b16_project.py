"""Proyecto 16 · Políglota Visual: buscar en «capturas» de la documentación con late interaction (MaxSim)."""
from _a6_common import SYNTH_DATA_SRC, CORPUS_SRC, REAL_SRC
from _a6_src15 import METRICS_SRC, STATS_SRC, RETRIEVERS_SRC
from _a6_src16 import SHAPES_SRC, PAGES_SRC

# Medido por la solución de referencia (FAST_DEV_RUN=True, corpus sintético, semilla 42) -> calibra la rúbrica
REF = {"ocr_bm25_0": 0.421, "ocr_lsi_0": 0.898, "maxsim_0": 0.761, "mean_0": 0.761, "maxsim_03": 0.526, "ocr_lsi_03": 0.898}

DATA_SRC = r'''
corpus = carga_corpus(fast_dev=FAST_DEV_RUN)
docs = [d for d in corpus["docs"] if d["lang"] != "code"]            # las "capturas" son de documentación en ES/EN
ids, txt = [d["id"] for d in docs], [d["text"] for d in docs]; N = len(docs)
queries = [q for q in corpus["queries"] if q["lang"] != "code"]; qrels = {q["qid"]: corpus["qrels"][q["qid"]] for q in queries}
print(corpus["source"], N, "documentos-página ·", len(queries), "queries")

# "Profesor" de texto: LSI-48 (embedder de texto). Sus vectores de TÉRMINO serán el espacio de los tokens de la query.
lsi = LSI(48, SEED).fit(txt, ids); bm25_full = BM25(tok_simple).fit(txt, ids)
comp = lsi.svd.components_.T; comp = comp / (np.linalg.norm(comp, axis=1, keepdims=True) + 1e-9)
vec_termino = {}
for t, j in lsi.tf.vocabulary_.items(): vec_termino.setdefault(plano(t), comp[j])      # término (sin tildes) -> vector 48-d

# Términos clave de cada documento (top TF-IDF) -> lo que se "imprime" en su captura
Xtf = lsi.tf.transform(txt); inv = {j: t for t, j in lsi.tf.vocabulary_.items()}; dfreq = np.asarray((Xtf > 0).sum(0)).ravel()
def terminos_clave(i, k=8):
    fila = Xtf[i].toarray().ravel(); out = []
    for j in np.argsort(-fila):
        t = plano(inv[j])
        if fila[j] == 0: break
        if re.fullmatch(r"[a-z]{3,12}", t) and 3 <= dfreq[j] <= 0.2 * N and t not in out: out.append(t)
        if len(out) >= k: break
    return out
CLAVE = [terminos_clave(i) for i in range(N)]
VOC = sorted({t for k in CLAVE for t in k})[:250]; w2c = {w: i + 1 for i, w in enumerate(VOC)}      # clase 0 = celda vacía
CLAVE = [[w for w in k if w in w2c] for k in CLAVE]
print(f"vocabulario renderizable: {len(VOC)} términos · {np.mean([len(k) for k in CLAVE]):.1f} términos clave por página")
''' .strip("\n")

RENDER_SRC = r'''
rr = np.random.default_rng(7)
def render_doc(i, ruido=0.0):
    """Captura sintética del documento i: sus términos clave impresos en celdas aleatorias de una rejilla 3x4."""
    g = np.zeros(12, int); g[rr.choice(12, len(CLAVE[i]), replace=False)] = [w2c[w] for w in CLAVE[i]]
    return pagina_a_imagen([celda_vacia() if c == 0 else celda_palabra(VOC[c - 1], rr) for c in g], ruido, rr)

def parches_corpus(ruido: float) -> np.ndarray:
    return np.stack([parchea(render_doc(i, ruido)) for i in range(N)])          # (N, 12, 16, 96)
'''.strip("\n")

TOKENS_SRC = r'''
def consulta_a_tokens(q: str):
    """Texto de la query -> matriz (n_tokens, 48) con los vectores de término del profesor LSI (sin tildes; descarta OOV). None si vacía."""
    ws = [plano(w) for w in re.findall(r"\w+", q.lower())]; vs = [vec_termino[w] for w in ws if w in vec_termino]
    return np.stack(vs).astype(np.float32) if vs else None
'''.strip("\n")


def build(nb):
    nb.md(f"""
    {nb.badge()}

    # Proyecto 16 · Políglota Visual: buscar en capturas y PDFs

    | | |
    |---|---|
    | **Nivel** | 🟠 Avanzado |
    | **Duración** | ≈ 2 h |
    | **GPU** | No necesaria en `FAST_DEV_RUN=True` (CPU, ≈ 3–5 min). L4 recomendada para el reto con ColPali real |
    | **Requiere** | Lección 16 (MaxSim, patches, OCR vs visual) y módulo 15 (métricas e IC) |
    | **Conecta con** | Módulo 08 (patches) · 13 (MaxSim en ColBERT) · 15 (`poliglota_eval`) · 18 (servicio y coste) |

    ## 🏢 Contexto de negocio
    Eres ML engineer en **Políglota Labs**. Soporte reporta que muchas respuestas están en **capturas de pantalla y PDFs** de la documentación, que el buscador de texto no «ve». La CTO te pide un prototipo de **Políglota Visual** y una recomendación: *¿OCR + texto, un modelo visual con late interaction, o ambos? ¿Y cuánto cuesta almacenarlo?*

    ## 📦 Dataset
    Cada documento de Políglota (ES/EN) se convierte en una **captura sintética**: sus 8 términos clave (TF-IDF) impresos como palabras en una rejilla 3×4 (fuente real, desplazamientos aleatorios y **ruido de píxel**). Las queries y qrels son las de Políglota (`carga_corpus`; con datos reales, el vocabulario renderizable se limita a los 250 términos clave más frecuentes). Importante: las queries usan **sinónimos que no aparecen en la captura**, de modo que hace falta semántica.
    En Colab con GPU puedes sustituir las capturas por páginas reales de **ViDoRe** y el codificador por **ColPali/ColQwen** (reto extra).

    ## 🎯 Entregables y criterios
    | # | Entregable | Criterio objetivo |
    |---|---|---|
    | 1 | Pérdida de destilación visual→texto (TODO 1) | El codificador de patch alcanza ≥ 70 % de precisión de «lectura» de términos con σ=0 (medido: ≈ 80 % con 800 pasos) |
    | 2 | `maxsim_paginas` correcto (TODO 2) | Pasa el test numérico (2.4) y las formas |
    | 3 | `consulta_a_tokens` (TODO 3) | Pasa el test (tildes, OOV, vacía) |
    | 4 | Evaluación con IC de 5 sistemas a σ=0 y σ=0.3 | nDCG@10 de cada sistema ≈ valor de referencia (± margen indicado) |
    | 5 | Coste de almacenamiento (TODO 4) | Cifra correcta por 1 M de páginas para 4 esquemas |
    | 6 | Recomendación para la CTO | Cita IC, ruido y coste |
    """)
    nb.md("## 0. Preparación (celdas dadas)")
    nb.code("!pip install -q numpy scipy scikit-learn matplotlib pandas torch pillow datasets")
    nb.code(r'''
    import os, re, math, random, time, warnings
    import numpy as np, pandas as pd
    import matplotlib.pyplot as plt
    warnings.filterwarnings("ignore")
    SEED, FAST_DEV_RUN = 42, True
    random.seed(SEED); np.random.seed(SEED)
    import torch
    torch.manual_seed(SEED)
    if FAST_DEV_RUN: torch.set_num_threads(1)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    AZUL, NARANJA, VERDE, GRIS, ROJO = "#1F6FEB", "#F28E2B", "#2CA02C", "#6B7280", "#D62728"
    plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": .25})
    ''')
    nb.md("Utilidades del corpus Políglota (`carga_corpus`: oficial → espejo → sintético), copia autocontenida del contrato común.")
    nb.code(SYNTH_DATA_SRC); nb.code(CORPUS_SRC); nb.code(REAL_SRC)
    nb.md("Métricas y estadística del módulo 15 (`poliglota_eval.py`), retrievers de CPU, y la librería de páginas/patches/MaxSim de la lección 16.")
    nb.code(METRICS_SRC); nb.code(STATS_SRC); nb.code(RETRIEVERS_SRC)
    nb.code(SHAPES_SRC); nb.code(PAGES_SRC.replace("def maxsim(Q: np.ndarray, P: np.ndarray) -> np.ndarray:", "def _maxsim_dado(Q: np.ndarray, P: np.ndarray) -> np.ndarray:"))
    nb.code(DATA_SRC); nb.code(RENDER_SRC)
    nb.code(r'''
    fig, ax = plt.subplots(1, 3, figsize=(13, 2.5))
    for a, (i, rz) in zip(ax, ((0, 0.0), (0, 0.3), (60, 0.0))):
        a.imshow(render_doc(i, rz), cmap="gray", vmin=0, vmax=1); a.set_title(f"captura del doc {ids[i]} · σ={rz}", fontsize=9); a.axis("off")
    plt.tight_layout(); plt.show(); print("términos clave del doc 0:", CLAVE[0])
    ''')

    nb.md("""
    ## 1. Destilación visual → texto (TODO 1)
    El «profesor» de texto (LSI) da a cada término un vector 48-d. El **estudiante visual** (`RedPatch`) debe mapear la imagen de una palabra a *ese* vector, de modo que un token de query y un patch de la página queden en el mismo espacio (en ColPali lo consigue el VLM entrenado contrastivamente).
    Implementa `perdida_destilacion`: logits = similitud coseno entre el embedding del patch y las **filas fijas** de la tabla de objetivos (la fila 0 es el embedding de la celda vacía), dividida por una temperatura `tau` (0.05), y entropía cruzada con la clase correcta.
    """)
    nb.md(_hint("Es una clasificación sobre el vocabulario, pero con los *pesos* fijados a los vectores del profesor (normalizados) en lugar de aprendidos. `tau` pequeña afila el softmax.",
                "`logits = F.normalize(z, dim=-1) @ F.normalize(objetivos, dim=-1).T / tau`; `return F.cross_entropy(logits, y)`. Aquí `z` ya viene normalizado de `RedPatch`."))
    nb.code(r'''
    def perdida_destilacion(z: torch.Tensor, y: torch.Tensor, objetivos: torch.Tensor, tau: float = 0.05) -> torch.Tensor:
        """z: (B, D) embeddings de patch; y: (B,) clase (0 = vacía, k = término k); objetivos: (V+1, D) vectores del profesor."""
        # TODO 1: entropía cruzada sobre logits coseno / tau
        raise NotImplementedError("TODO 1: perdida_destilacion")

    def test_perdida():
        z = F.normalize(torch.eye(3)[:, :3] + 0.01, dim=-1); obj = torch.eye(3); y = torch.tensor([0, 1, 2])
        l_ok = perdida_destilacion(z, y, obj); l_mal = perdida_destilacion(z, torch.tensor([1, 2, 0]), obj)
        assert l_ok.ndim == 0 and l_ok < l_mal, "la clase correcta debe tener menos pérdida que una incorrecta"
        z.requires_grad_(True); perdida_destilacion(z, y, obj).backward(); assert z.grad is not None
        return "✅ test_perdida OK"
    def corre(f):
        try: print(f())
        except NotImplementedError as e: print(f"⏳ pendiente: {e}")
        except AssertionError as e: print(f"❌ falló: {e}")
        except Exception as e: print(f"❌ {type(e).__name__}: {e}")
    corre(test_perdida)
    ''')
    nb.code(r'''
    D = 48
    OBJ = torch.tensor(np.stack([np.zeros(D)] + [vec_termino.get(w, np.zeros(D)) for w in VOC]).astype(np.float32))     # fila 0 la aprende la red

    def muestra_celdas(n, rng, ruido_max=.25):
        ys = rng.integers(0, len(VOC) + 1, n); xs = []
        for y in ys:
            c = celda_vacia() if y == 0 else celda_palabra(VOC[y - 1], rng); xs.append(c + rng.normal(0, float(rng.uniform(0, ruido_max)), c.shape).astype(np.float32))
        return torch.tensor(np.stack(xs)), torch.tensor(ys)

    def entrena_estudiante(pasos=800, seed=0):
        """(Dado) Bucle de entrenamiento: usa TU perdida_destilacion."""
        torch.manual_seed(seed); rng = np.random.default_rng(seed); red = RedPatch(D); vacia = nn.Parameter(torch.randn(1, D) * .1)
        opt = torch.optim.Adam(list(red.parameters()) + [vacia], lr=3e-3); hist = []
        for _ in range(pasos):
            x, y = muestra_celdas(128, rng); obj = torch.cat([vacia, OBJ[1:]])
            loss = perdida_destilacion(red(x), y, obj); opt.zero_grad(); loss.backward(); opt.step(); hist.append(loss.item())
        return red.eval(), hist
    try:
        t0 = time.time(); RED, hist = entrena_estudiante(800 if FAST_DEV_RUN else 2500)
        x, y = muestra_celdas(600, np.random.default_rng(99), ruido_max=0.0)
        with torch.no_grad(): z = RED(x); acc_lectura = float(((F.normalize(z, dim=-1) @ F.normalize(OBJ, dim=-1).T)[:, 1:].argmax(1) + 1 == y)[y > 0].float().mean())
        print(f"entrenado en {time.time()-t0:.0f}s · pérdida final {np.mean(hist[-20:]):.3f} · precisión de lectura de palabras (σ=0): {acc_lectura:.3f}")
    except NotImplementedError as e:
        RED, acc_lectura = None, None; print("⏳ pendiente:", e)
    ''')

    nb.md("""
    ## 2. MaxSim y tokens de query (TODOs 2 y 3)
    $$\\mathrm{score}(q,\\text{página})=\\sum_i\\max_j\\langle q_i,p_j\\rangle$$
    Implementa **`maxsim_paginas(Q, P)`** vectorizado (`Q`: `(nq, D)`; `P`: `(n_págs, n_patches, D)` → `(n_págs,)`) y **`consulta_a_tokens`**: minúsculas, `\\w+`, sin tildes (`plano`), vector del profesor para cada término en `vec_termino` y descarte de los desconocidos (devuelve `None` si no queda ninguno).
    """)
    nb.md(_hint("Con `einsum` obtienes la matriz de similitudes `(n_págs, nq, n_patches)`; el máximo va sobre el último eje y la suma sobre tokens.",
                "`np.einsum('qd,npd->nqp', Q, P).max(axis=2).sum(axis=1)`. Para los tokens: `[plano(w) for w in re.findall(r'\\w+', q.lower())]` y `np.stack([vec_termino[w] for w in ws if w in vec_termino])`."))
    nb.code(r'''
    def maxsim_paginas(Q: np.ndarray, P: np.ndarray) -> np.ndarray:
        # TODO 2
        raise NotImplementedError("TODO 2: maxsim_paginas")

    def consulta_a_tokens(q: str):
        # TODO 3
        raise NotImplementedError("TODO 3: consulta_a_tokens")

    def test_maxsim_tokens():
        S = np.array([[.9, .1, .0, .2], [.1, .8, .3, .0], [.0, .2, .7, .1]])      # 3 tokens x 4 patches (ejemplo de la lección)
        Qv = np.eye(4)[:3]; P4 = np.zeros((2, 4, 4)); P4[0, :, :3] = S.T          # tokens = e1..e3; página 0 con esas similitudes, página 1 vacía
        s = maxsim_paginas(Qv, P4); assert s.shape == (2,) and abs(s[0] - 2.4) < 1e-9 and abs(s[1]) < 1e-12, "MaxSim del ejemplo = .9+.8+.7"
        t = consulta_a_tokens("Cómo configurar la CACHÉ de índice"); assert t is None or (t.ndim == 2 and t.shape[1] == 48)
        assert consulta_a_tokens("zzzz qqqq") is None, "palabras desconocidas -> None"
        a, b = consulta_a_tokens("caché"), consulta_a_tokens("cache"); assert a is not None and np.allclose(a, b), "las tildes se pliegan"
        return "✅ test_maxsim_tokens OK"
    corre(test_maxsim_tokens)
    ''')

    nb.md("""
    ## 3. Cinco sistemas, dos niveles de ruido (celdas dadas + tu evaluación)
    | Sistema | Qué hace |
    |---|---|
    | BM25 sobre el **texto completo** | referencia: lo que hay si tuvieras el texto original (no hay OCR) |
    | **OCR + BM25** | reconoce las palabras de la captura (OCR clásico por plantillas) y hace BM25: puramente léxico |
    | **OCR + LSI** | reconoce las palabras y las embebe con el LSI del corpus |
    | **MaxSim visual** | tu estudiante visual + tu MaxSim sobre los patches |
    | **Vector medio visual** | un solo vector por página (media de patches) |
    """)
    nb.code(r'''
    def construye_sistemas(ruido):
        P = parches_corpus(ruido)
        with torch.no_grad(): PE = RED(torch.tensor(P.reshape(-1, CH, CW))).reshape(N, 12, -1).numpy()
        TPL, LAB = ocr_plantillas(VOC); ocr = np.stack([ocr_pagina(P[i], TPL, LAB) for i in range(N)])
        ocr_txt = [" ".join(VOC[c - 1] for c in o if c > 0) for o in ocr]; bm_ocr = BM25(tok_simple).fit(ocr_txt, ids)
        Zo = lsi.svd.transform(lsi.tf.transform(ocr_txt)); Zo /= np.linalg.norm(Zo, axis=1, keepdims=True) + 1e-9
        def ocr_lsi(q):
            z = lsi.svd.transform(lsi.tf.transform([q]))[0]; return Zo @ (z / (np.linalg.norm(z) + 1e-9))
        def maxsim_vis(q):
            Q = consulta_a_tokens(q); return maxsim_paginas(Q, PE) if Q is not None else np.zeros(N)
        def media_vis(q):
            Q = consulta_a_tokens(q); return PE.mean(1) @ Q.mean(0) if Q is not None else np.zeros(N)
        return {"BM25 texto completo": bm25_full.scores, "OCR + BM25": bm_ocr.scores, "OCR + LSI": ocr_lsi, "MaxSim visual": maxsim_vis, "Vector medio visual": media_vis}

    def evalua_sistemas(ruido):
        sis = construye_sistemas(ruido); runs = {n: build_run(f, queries, ids, 100) for n, f in sis.items()}
        return {n: evaluate_per_query(r, qrels, 10) for n, r in runs.items()}
    ''')
    nb.md("""
    ### TODO 4 · Informe con IC y coste de almacenamiento
    Para cada nivel de ruido calcula **nDCG@10 con IC95 %** (`bootstrap_ci`) de los cinco sistemas, y un **test pareado** de *MaxSim visual* contra *OCR + BM25* (`paired_bootstrap`). Después implementa `gb_por_millon(n_vec, dim, bits)` y completa la tabla de coste para 1 M de páginas.
    """)
    nb.md(_hint("`PER = evalua_sistemas(0.0)` te da `PER[sistema]['ndcg']` (un valor por query). Recorre los sistemas con `bootstrap_ci`. Coste: bytes = n_vec · dim · bits / 8.",
                "`gb_por_millon = n_vec * dim * bits / 8 * 1e6 / 1e9` (GB decimales). ColPali: 1030 × 128 × 16 bits; un vector denso 1024-d fp16: 1 × 1024 × 16; binario: 1 × 1024 × 1."))
    nb.code(r'''
    def gb_por_millon(n_vec: int, dim: int, bits: int) -> float:
        """GB (10^9 bytes) para un millón de páginas."""
        # TODO 4a
        raise NotImplementedError("TODO 4a: gb_por_millon")

    def informe(ruido):
        """Devuelve {'ic': {sistema: (media, lo, hi)}, 'test': dict de paired_bootstrap MaxSim vs OCR+BM25, 'per': per-query}."""
        # TODO 4b: usa evalua_sistemas(ruido), bootstrap_ci y paired_bootstrap
        raise NotImplementedError("TODO 4b: informe")

    def test_coste():
        assert abs(gb_por_millon(1030, 128, 16) - 263.68) < 1e-6 and abs(gb_por_millon(1, 1024, 16) - 2.048) < 1e-9 and abs(gb_por_millon(1, 1024, 1) - 0.128) < 1e-9
        return "✅ test_coste OK"
    corre(test_coste)
    RES = {}
    try:
        for rz in (0.0, 0.3):
            RES[rz] = informe(rz)
            print(f"\n=== ruido σ={rz} ==="); [print(f"  {n:22s} nDCG@10 = {m:.3f}  IC95 [{lo:.3f}, {hi:.3f}]") for n, (m, lo, hi) in RES[rz]["ic"].items()]
            t = RES[rz]["test"]; print(f"  MaxSim − OCR+BM25: Δ={t['diff']:+.3f} IC95[{t['ci_low']:+.3f},{t['ci_high']:+.3f}] p={t['p_value']:.4f}")
        ESQ = {"ColPali-like (1030×128 fp16)": gb_por_millon(1030, 128, 16), "Nuestro juguete (12×48 fp32)": gb_por_millon(12, 48, 32), "1 vector 1024-d fp16": gb_por_millon(1, 1024, 16), "1 vector 1024-d binario": gb_por_millon(1, 1024, 1)}
        print({k: round(v, 3) for k, v in ESQ.items()}); RES["coste"] = ESQ
    except (NotImplementedError, TypeError, NameError, AttributeError, KeyError) as e:
        print("⏳ pendiente (completa TODOs 1–4):", type(e).__name__)
    ''')

    nb.md("""
    ## 4. Rúbrica (autoevaluación)
    Umbrales **calibrados con la solución de referencia** (FAST_DEV_RUN=True, corpus sintético, semilla 42) con el margen indicado: el entrenamiento del estudiante tiene varianza entre ejecuciones/hardware, de ahí márgenes de ± 0.05–0.07. Con datos reales solo se exigen chequeos estructurales.
    """)
    nb.code(f'''
    REF = {REF!r}
    ''' + r'''
    def rubrica(res, acc):
        sint = corpus["source"] == "synthetic" and FAST_DEV_RUN; out = []
        def chk(nombre, f):
            try: out.append((nombre, "✅" if f() else "❌"))
            except Exception: out.append((nombre, "⏳"))
        chk("1. test_perdida", lambda: test_perdida().startswith("✅"))
        chk("1b. precisión de lectura de palabras (σ=0) ≥ 0.70", lambda: acc >= 0.70)
        chk("2-3. test_maxsim_tokens", lambda: test_maxsim_tokens().startswith("✅"))
        chk("5. test_coste", lambda: test_coste().startswith("✅"))
        if sint:
            g = lambda rz, n: res[rz]["ic"][n][0]
            chk(f"4a. OCR + BM25 (σ=0) = {REF['ocr_bm25_0']} ± 0.04", lambda: abs(g(0.0, "OCR + BM25") - REF["ocr_bm25_0"]) <= .04)
            chk(f"4b. OCR + LSI (σ=0) = {REF['ocr_lsi_0']} ± 0.04", lambda: abs(g(0.0, "OCR + LSI") - REF["ocr_lsi_0"]) <= .04)
            chk(f"4c. MaxSim visual (σ=0) = {REF['maxsim_0']} ± 0.07", lambda: abs(g(0.0, "MaxSim visual") - REF["maxsim_0"]) <= .07)
            chk(f"4d. MaxSim visual (σ=0.3) = {REF['maxsim_03']} ± 0.08", lambda: abs(g(0.3, "MaxSim visual") - REF["maxsim_03"]) <= .08)
            chk("4e. MaxSim > OCR+BM25 con IC95 > 0 (σ=0) [la semántica gana al léxico]", lambda: res[0.0]["test"]["ci_low"] > 0)
            chk("4f. el ruido degrada el estudiante visual (σ=0.3 < σ=0) y NO al OCR", lambda: g(0.3, "MaxSim visual") < g(0.0, "MaxSim visual") - 0.1 and abs(g(0.3, "OCR + LSI") - g(0.0, "OCR + LSI")) < 0.03)
            chk("5b. coste ColPali-like ≈ 263.7 GB por 1 M de páginas", lambda: abs(res["coste"]["ColPali-like (1030×128 fp16)"] - 263.68) < 0.1)
        else: print("ℹ️ Datos reales o FAST_DEV_RUN=False: se omiten umbrales numéricos.")
        for n, e in out: print(e, n)
        print(f"\n{sum(e == '✅' for _, e in out)}/{len(out)} criterios cumplidos")
    rubrica(RES, acc_lectura)
    ''')
    nb.md("""
    ## 5. Recomendación para la CTO (escribe aquí)
    1. **¿OCR + texto, visual o ambos?** (cita IC y el efecto del ruido) …
    2. **¿Por qué «OCR + BM25» pierde aquí si el OCR es perfecto?** (pista: ¿qué palabras aparecen en la captura y cuáles en la query?) …
    3. **Coste:** ¿cuánto ocuparía el índice multi-vector de 1 M de páginas y qué palancas usarías? …
    """)

    # ───────────── SOLUCIÓN ─────────────
    nb.md("""
    # ⛔ SPOILER — intenta resolverlo primero
    Solución de referencia completa y ejecutable. Si te atascas en un TODO, abre antes las pistas 🪜 de ese paso. Al ejecutar se redefinen las funciones y se recalcula `RES`.
    """)
    nb.code(r'''
    def perdida_destilacion(z, y, objetivos, tau: float = 0.05):
        logits = F.normalize(z, dim=-1) @ F.normalize(objetivos, dim=-1).T / tau
        return F.cross_entropy(logits, y)
    corre(test_perdida)
    t0 = time.time(); RED, hist = entrena_estudiante(800 if FAST_DEV_RUN else 2500)
    x, y = muestra_celdas(600, np.random.default_rng(99), ruido_max=0.0)
    with torch.no_grad(): z = RED(x); acc_lectura = float(((F.normalize(z, dim=-1) @ F.normalize(OBJ, dim=-1).T)[:, 1:].argmax(1) + 1 == y)[y > 0].float().mean())
    print(f"entrenado en {time.time()-t0:.0f}s · precisión de lectura (σ=0): {acc_lectura:.3f}")
    ''')
    nb.code(TOKENS_SRC + "\n\n" + '''def maxsim_paginas(Q, P):
    return np.einsum("qd,npd->nqp", Q, P).max(axis=2).sum(axis=1)
corre(test_maxsim_tokens)''')
    nb.code(r'''
    def gb_por_millon(n_vec, dim, bits): return n_vec * dim * bits / 8 * 1e6 / 1e9

    def informe(ruido):
        per = evalua_sistemas(ruido)
        return {"ic": {n: bootstrap_ci(p["ndcg"]) for n, p in per.items()}, "per": per,
                "test": paired_bootstrap(per["MaxSim visual"]["ndcg"], per["OCR + BM25"]["ndcg"])}
    corre(test_coste)
    RES = {}
    for rz in (0.0, 0.3):
        RES[rz] = informe(rz)
        print(f"\n=== ruido σ={rz} ==="); [print(f"  {n:22s} nDCG@10 = {m:.3f}  IC95 [{lo:.3f}, {hi:.3f}]") for n, (m, lo, hi) in RES[rz]["ic"].items()]
        t = RES[rz]["test"]; print(f"  MaxSim − OCR+BM25: Δ={t['diff']:+.3f} IC95[{t['ci_low']:+.3f},{t['ci_high']:+.3f}] p={t['p_value']:.4f}")
    RES["coste"] = {"ColPali-like (1030×128 fp16)": gb_por_millon(1030, 128, 16), "Nuestro juguete (12×48 fp32)": gb_por_millon(12, 48, 32), "1 vector 1024-d fp16": gb_por_millon(1, 1024, 16), "1 vector 1024-d binario": gb_por_millon(1, 1024, 1)}
    print({k: round(v, 3) for k, v in RES["coste"].items()}); rubrica(RES, acc_lectura)
    ''')
    nb.code(r'''
    fig, ax = plt.subplots(1, 2, figsize=(12, 3.8)); sis = list(RES[0.0]["ic"]); cols = [GRIS, NARANJA, VERDE, AZUL, ROJO]
    for a, rz in zip(ax, (0.0, 0.3)):
        for i, (n, c) in enumerate(zip(sis, cols)):
            m, lo, hi = RES[rz]["ic"][n]; a.bar(i, m, color=c, yerr=[[m - lo], [hi - m]], capsize=3)
        a.set_xticks(range(len(sis))); a.set_xticklabels(sis, rotation=25, ha="right", fontsize=8); a.set_ylim(0, 1.05); a.set_title(f"nDCG@10 con IC95 % · σ={rz}")
    plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** (1) *OCR + BM25* queda muy por debajo aunque el OCR sea perfecto: **el cuello de botella no es leer, es el vocabulario** (las queries usan sinónimos que no están impresos). (2) *OCR + LSI* (texto semántico) es el mejor sistema, y con σ=0 el **estudiante visual se acerca a su profesor** pero no lo supera: destilar no crea información nueva. (3) Con ruido (σ=0.3) el estudiante visual se degrada mientras que el OCR por plantillas (filtro adaptado) no: un OCR clásico es un baseline duro cuando el texto es legible. (4) El **vector medio** compite bien aquí porque las queries son *temáticas* (bolsa de términos semánticos); en la lección, con queries *conjuntivas* («palabra A y palabra B en la misma página»), la media fallaba: la métrica depende del tipo de consulta.
    > Recomendación honesta para Políglota: OCR + embedder de texto como base; **añadir índice visual solo para páginas con contenido no textual** (diagramas/capturas) y medirlo por tipo de consulta.
    """)
    nb.md("""
    ## 🚀 Retos extra (nivel experto)
    1. **Binariza** los patches (signo) y calcula MaxSim con producto en {−1,+1}: ¿cuánto nDCG pierdes y cuánto ahorras (§ coste)?
    2. **Token pooling:** agrupa los 12 patches en 6 (media de pares adyacentes) y mide calidad vs almacenamiento.
    3. **Pre-filtro + reordenado:** usa el vector medio para quedarte con los 20 mejores y reordena con MaxSim; compara latencia (`time.perf_counter`) y nDCG.
    4. **Queries conjuntivas:** crea un slice de queries con 2 términos *clave* de la misma página y re-mide vector medio vs MaxSim con IC (conecta con la lección).
    5. **ColPali real (GPU, con red):** renderiza 200 páginas de documentación como PNG (por ejemplo con `matplotlib` o capturas de tu docs), indexa con `colpali-engine` y compara con OCR+BM25 usando `poliglota_eval`; o evalúa en un subconjunto de **ViDoRe** (`vidore/*`) con su paquete de benchmark.
    6. **Fusión híbrida:** RRF entre *OCR + LSI* y *MaxSim visual*: ¿mejora con IC pareado y Holm?
    7. **Embedder unificado:** si tienes `GEMINI_API_KEY`, embebe 50 capturas reales y compara con tu pipeline (verifica límites/versión del modelo en la documentación vigente).

    ## 🧠 Reflexión
    - ¿Qué tipos de página de la documentación de Políglota justificarían un índice multi-vector y cuáles no?
    - Si el almacenamiento es el problema, ¿prefieres binarizar, hacer pooling, o indexar solo páginas con figuras? ¿Cómo lo decidirías con datos?
    - ¿Qué cambia en la evaluación (módulo 15) cuando las queries son *visuales* («¿qué diagrama muestra el flujo de auth?») y los qrels dependen de regiones de la página?
    - ¿Qué riesgos de privacidad introducen las capturas de pantalla (módulo 18)?

    ➡️ **Siguiente:** módulo 17 (interpretabilidad y geometría): abrirás la «caja negra» del embedding de Políglota con *probing* y *sparse autoencoders*.
    """)


def _hint(a: str, b: str) -> str:
    return f"""
    <details><summary>🪜 Pista 1 (la idea)</summary>

    {a}
    </details>

    <details><summary>🪜 Pista 2 (casi la API)</summary>

    {b}
    </details>
    """
