"""Lección 16 · parte 2: ColPali en miniatura, unificados, audio/video, decisión, cierre."""
from _a6_src16 import PAGES_SRC


def part2(nb):
    nb.md("""
    ## 6. Retrieval visual de documentos: de OCR + texto a ColPali

    **El problema.** Una documentación técnica real contiene PDFs con tablas, diagramas, capturas de pantalla y gráficos. El pipeline clásico es: *parsear/OCR → trocear → embeber texto → indexar*. Cada paso pierde información (layout, tablas, figuras) y es caro de mantener.

    **Tres familias** (Faysse et al., 2024; Ma et al., 2024):
    | Enfoque | Qué indexa por página | Pros | Contras |
    |---|---|---|---|
    | OCR + texto + embedder de texto | texto extraído (a veces + captions de figuras) | barato de almacenar, maduro | falla con layout/figuras; calidad = calidad del OCR |
    | **DSE** (*Document Screenshot Embedding*): una captura → **un vector** | 1 vector por página | índice pequeño | un vector comprime todo |
    | **ColPali / ColQwen**: la página como imagen → un VLM → **un vector por patch** + late interaction | ≈ 1 000 vectores de 128-d | recupera detalles locales, sin OCR | almacenamiento y cómputo de MaxSim |

    **ColPali** (Faysse et al., ICLR 2025) usa PaliGemma-3B (SigLIP-So400m + Gemma-2B): 1 024 patches de la imagen + 6 tokens de texto, proyectados a $D=128$; entrena con una pérdida contrastiva *late interaction* sobre 118 695 pares query–página. En **ViDoRe** obtiene 81.3 de nDCG@5 medio frente a 67.0 del mejor pipeline de texto del paper (Unstructured + captioning + BGE-M3), e indexa una página en 0.39 s frente a 7.22 s del pipeline completo (GPU L4; Tablas 2 y 5 del paper). ⚠️ Son los números **de su paper (2024)**: el campo se movió (ViDoRe V2 y V3, ColQwen, Jina v4…).

    ### 6.1 MaxSim sobre patches
    Con la query tokenizada en vectores $q_1..q_m$ y la página en patches $p_1..p_n$ (ambos en $\\mathbb R^D$, normalizados):
    $$\\mathrm{score}(q,\\text{página})=\\sum_{i=1}^{m}\\max_{1\\le j\\le n}\\ \\langle q_i,\\,p_j\\rangle$$
    Cada palabra de la query **elige el patch que mejor la «ve»**; sumamos esas coincidencias. Un vector medio de la página tendría que contener *todo* a la vez.
    """)
    nb.gemini(
        "video", "M16-VID-01", "ColPali: de la página a los patches y MaxSim",
        "Animación del recorrido: página → rejilla de patches → un vector por patch; query → un vector por token; cada token toma el máximo sobre los patches; se suman los máximos.",
        """
        Animación técnica limpia, 16:9, fondo blanco, paleta sobria (azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280), tipografía sans-serif, ritmo calmado, sin voz en off, sin música. Textos en español, términos técnicos en inglés.
        Escenas:
        0–5 s: aparece una página de documento esquemática (rectángulo blanco con borde gris; un título como barra gris, dos párrafos como líneas grises, un gráfico de barras azules y una pequeña tabla). Título en pantalla: «Una página = una imagen».
        5–11 s: sobre la página se dibuja una rejilla de 4×3 celdas y cada celda se resalta brevemente de izquierda a derecha, de arriba abajo; a la derecha aparece una columna de 12 vectores pequeños (barras verticales de colores) con la etiqueta «1 vector por patch (128-d)».
        11–16 s: abajo a la izquierda aparece la consulta «latencia del índice HNSW»; se parte en tres tokens, «latencia», «índice», «HNSW», y cada uno genera un vector naranja con la etiqueta «1 vector por token».
        16–25 s: para el token «índice» se dibujan 12 líneas finas grises hacia los 12 vectores de patch y la de mayor similitud se engrosa en verde con el texto «max»; se repite para «latencia» y «HNSW», cada uno con su línea verde hacia un patch distinto (el gráfico de barras, la tabla y el párrafo).
        25–30 s: los tres valores máximos se suman en una caja verde: «score = max₁ + max₂ + max₃» y aparece el texto «MaxSim (late interaction)».
        Evita: voz en off, música, texto ilegible, números inventados, efectos 3D, transiciones bruscas, imágenes realistas.
        """,
        "Una página se divide en patches con un vector cada uno; cada token de la consulta toma su máxima similitud sobre los patches y se suman.",
        """
        página -> [p1 p2 ... p12]   (un vector por patch)
        query  -> [q1 q2 q3]        (un vector por token)
        score = max_j<q1,pj> + max_j<q2,pj> + max_j<q3,pj>
        """,
        duration="30 s",
    )
    nb.md("""
    > 👀 **Qué debes observar.** Cada token de la query «apunta» a un **patch distinto** (el gráfico, la tabla, el párrafo): por eso MaxSim distingue páginas que contienen *todos* los conceptos de las que solo tienen la media de ellos. El mapa de calor que construiremos en 6.2 es esta misma operación.
    """)
    nb.md("""
    ### 6.2 ColPali en miniatura (entrenable en CPU)
    Construimos páginas de 12 celdas (3×4); cada celda contiene **una palabra renderizada** (fuente real, con desplazamiento aleatorio), un **icono** (forma de color: contenido *no textual*) o está vacía. Entrenamos un codificador de patch (CNN) contra una tabla de embeddings de «tokens» (palabras e iconos) con ruido de píxel. Es el equivalente funcional del VLM de ColPali: *patch de imagen → vector en el mismo espacio que los tokens de la query*.
    """)
    nb.code(PAGES_SRC)
    nb.code(r'''
    PALABRAS = ("cache index token query model vector graph latency memory thread lock tests branch merge cloud shard route kernel buffer socket "
                "digest cursor schema trace metric batch queue stack hash layer loss epoch gamma delta cosine matrix tensor decode patch retry pool").split()[:40]
    NW = len(PALABRAS); V = 1 + NW + 16            # clase 0 = celda vacía · 1..NW palabras · NW+1.. iconos (los 16 conceptos forma×color)
    nombre_clase = ["<vacía>"] + PALABRAS + [f"icono:{c}-{f}" for f, c in CONCEPTOS]

    def muestra_celdas(n, rng, ruido_max=.3):
        ys = rng.integers(0, V, n); xs = []
        for y in ys:
            c = celda_vacia() if y == 0 else celda_palabra(PALABRAS[y - 1], rng) if y <= NW else celda_icono(y - NW - 1, rng)
            xs.append(c + rng.normal(0, float(rng.uniform(0, ruido_max)), c.shape).astype(np.float32))
        return torch.tensor(np.stack(xs)), torch.tensor(ys)

    def entrena_red_patch(pasos=700, D=32, seed=0):
        torch.manual_seed(seed); rng = np.random.default_rng(seed); red = RedPatch(D)
        emb = nn.Parameter(torch.randn(V, D) * .1); logt = nn.Parameter(torch.tensor(math.log(10.)))
        opt = torch.optim.Adam(list(red.parameters()) + [emb, logt], lr=3e-3); hist = []
        for _ in range(pasos):
            x, y = muestra_celdas(128, rng); loss = F.cross_entropy(logt.exp() * red(x) @ F.normalize(emb, dim=-1).T, y)
            opt.zero_grad(); loss.backward(); opt.step(); hist.append(loss.item())
        return red.eval(), F.normalize(emb, dim=-1).detach().numpy(), hist

    t0 = time.time(); RED, EMB, hist_patch = entrena_red_patch(700 if FAST_DEV_RUN else 2000)
    print(f"codificador de patch entrenado en {time.time()-t0:.0f}s · pérdida final {np.mean(hist_patch[-20:]):.3f}")
    ''')
    nb.code(r'''
    rng_p = np.random.default_rng(11); N_PAG = 200 if FAST_DEV_RUN else 600
    def genera_paginas(n):
        G = []
        for _ in range(n):
            nw, ni = int(rng_p.integers(4, 7)), int(rng_p.integers(1, 3))
            cont = np.concatenate([rng_p.choice(NW, nw, replace=False) + 1, rng_p.choice(16, ni, replace=False) + NW + 1])
            g = np.zeros(12, int); g[rng_p.choice(12, len(cont), replace=False)] = cont; G.append(g)
        return np.stack(G)
    GRID = genera_paginas(N_PAG)
    def render(g, rng, ruido):
        return pagina_a_imagen([celda_vacia() if c == 0 else celda_palabra(PALABRAS[c - 1], rng) if c <= NW else celda_icono(c - NW - 1, rng) for c in g], ruido, rng)
    fig, ax = plt.subplots(1, 3, figsize=(13, 2.6))
    for a, ruido in zip(ax, (0.0, 0.3, 0.45)):
        a.imshow(render(GRID[0], np.random.default_rng(0), ruido), cmap="gray", vmin=0, vmax=1); a.set_title(f"página 0 · ruido de píxel σ={ruido}", fontsize=9); a.axis("off")
    plt.tight_layout(); plt.show()
    print("contenido de la página 0:", [nombre_clase[c] for c in GRID[0] if c])
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** Con σ=0.45 el texto sigue siendo legible para una persona pero ya es difícil para un modelo pequeño. Los **iconos** no tienen ninguna palabra: un OCR no puede «leerlos»; un codificador visual sí puede alinearlos con tokens de la query (p. ej. «icono:red-circle»).
    """)
    nb.code(r'''
    TPL, LAB = ocr_plantillas(PALABRAS)            # OCR clásico por plantillas con desplazamientos
    rq = np.random.default_rng(13)
    def ndcg10(order, rel):
        rs = set(rel); dcg = sum(1 / math.log2(i + 2) for i, d in enumerate(order[:10]) if d in rs); idcg = sum(1 / math.log2(i + 2) for i in range(min(10, len(rs)))); return dcg / idcg
    def consultas(tipo, n):
        out = []
        for _ in range(n):
            g = GRID[rq.integers(0, N_PAG)]; w, ic = g[(g > 0) & (g <= NW)], g[g > NW]
            out.append(rq.choice(w, 2, replace=False) if tipo == "2 palabras" else np.array([rq.choice(w), rq.choice(ic)]) if tipo == "1 palabra + 1 icono" else (rq.choice(ic, 2, replace=False) if len(ic) > 1 else np.array([ic[0]])))
        return out
    TIPOS = ["2 palabras", "1 palabra + 1 icono", "2 iconos"]; N_Q = 80 if FAST_DEV_RUN else 200
    def evalua(ruido):
        rr = np.random.default_rng(20); P = np.stack([parchea(render(g, rr, ruido)) for g in GRID])
        with torch.no_grad(): PE = RED(torch.tensor(P.reshape(-1, CH, CW))).reshape(N_PAG, 12, -1).numpy()
        ocr = np.stack([ocr_pagina(P[i], TPL, LAB) for i in range(N_PAG)]); sets = [set(o) for o in ocr]; res = {}
        for tipo in TIPOS:
            r = {"MaxSim (multi-vector)": [], "vector medio (1 por página)": [], "OCR + coincidencia de palabras": []}
            for q in consultas(tipo, N_Q):
                rel = [j for j in range(N_PAG) if all(w in GRID[j] for w in q)]; qe = EMB[q]
                for k, s in (("MaxSim (multi-vector)", maxsim(qe, PE)), ("vector medio (1 por página)", PE.mean(1) @ qe.mean(0)), ("OCR + coincidencia de palabras", np.array([sum(float(w in st) for w in q) for st in sets]))):
                    r[k].append(ndcg10(np.lexsort((np.arange(N_PAG), -s)), rel))
            res[tipo] = {k: float(np.mean(v)) for k, v in r.items()}
        return res, PE
    t0 = time.time(); RUIDOS = (0.0, 0.3, 0.45); RES_PAG = {}
    for rz in RUIDOS: RES_PAG[rz] = evalua(rz)[0]
    print(f"({time.time()-t0:.0f}s)"); pd.DataFrame({f"σ={rz} · {t}": v for rz in RUIDOS for t, v in RES_PAG[rz].items()}).T.round(2)
    ''')
    nb.code(r'''
    sist = ["MaxSim (multi-vector)", "vector medio (1 por página)", "OCR + coincidencia de palabras"]; cols = [AZUL, GRIS, NARANJA]
    fig, ax = plt.subplots(1, 3, figsize=(14, 3.6), sharey=True)
    for a, rz in zip(ax, RUIDOS):
        for i, (s, c) in enumerate(zip(sist, cols)): a.bar(np.arange(3) + (i - 1) * .27, [RES_PAG[rz][t][s] for t in TIPOS], .27, color=c, label=s)
        a.set_xticks(range(3)); a.set_xticklabels(TIPOS, fontsize=8); a.set_title(f"ruido de píxel σ = {rz}")
    ax[0].set_ylabel("nDCG@10"); ax[0].legend(frameon=False, fontsize=7); plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** (1) El **vector medio** falla siempre: promediar patches *diluye* cada palabra entre las demás (el cuello de botella de un único vector por página). (2) Con texto limpio, **OCR + palabras es perfecto** (nDCG≈1) en consultas de palabras: no hay razón para pagar un modelo visual si el texto es legible y tu pregunta es léxica. (3) En consultas que incluyen **iconos**, el OCR cae porque no hay texto que leer, y MaxSim sigue funcionando (imperfecto: el codificador es diminuto). (4) Con mucho ruido, **el OCR «filtro adaptado» aguanta mejor que el codificador pequeño** en palabras: un OCR clásico bien afinado es un baseline duro.
    > Conclusión honesta: el embedding visual **no sustituye** al OCR en texto limpio; gana donde el contenido relevante **no es texto** o donde OCR/parseo es frágil.
    """)
    nb.code(r'''
    # Mapa de calor token-de-query × patch: la "explicabilidad" de ColPali. Usamos una consulta con dos palabras de la página 0.
    rr = np.random.default_rng(0); pag = render(GRID[0], rr, 0.1); P0 = parchea(pag)
    with torch.no_grad(): pe = RED(torch.tensor(P0)).numpy()
    ws = [c for c in GRID[0] if 0 < c <= NW][:2]; qe = EMB[ws]; sim = qe @ pe.T          # (2, 12)
    fig, ax = plt.subplots(1, 3, figsize=(14, 2.8), gridspec_kw={"width_ratios": [2.2, 1, 1]}); ax[0].imshow(pag, cmap="gray", vmin=0, vmax=1); ax[0].set_title("página (σ=0.1)", fontsize=9); ax[0].axis("off")
    for a, w, s in zip(ax[1:], ws, sim):
        a.imshow(s.reshape(FILAS, COLS), cmap="viridis", vmin=-.2, vmax=1); a.set_title(f"similitud del token «{PALABRAS[w-1]}»", fontsize=9); a.set_xticks([]); a.set_yticks([])
        j = int(s.argmax()); a.add_patch(plt.Rectangle((j % COLS - .5, j // COLS - .5), 1, 1, fill=False, ec=ROJO, lw=2))
    plt.tight_layout(); plt.show()
    print("score MaxSim de la página 0 para esa query:", round(float(maxsim(qe, pe[None])[0]), 3), "· máximo posible =", len(ws))
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** Cada token ilumina **exactamente la celda** donde está su palabra (recuadro rojo) y el resto queda cerca de 0. Esos mapas son los que usan ColPali/ViDoRe para mostrar *qué región de la página* justificó el resultado: mejor depuración que un score opaco.
    """)
    nb.md("""
    ### 6.3 Coste: ¿cuánto pesa un índice multi-vector?
    ColPali guarda ≈ 1 030 vectores de 128 dimensiones por página: en `float16`, $1030\\times128\\times2\\ \\text{B}=263\\,680\\ \\text{B}\\approx257.5\\ \\text{KiB}$ (el paper reporta ≈ 257.5 KB por página). Un único vector de 1024-d en `float16` son 2 KiB. **Calcula tú el coste para tu colección.**
    """)
    nb.code(r'''
    def bytes_pagina(n_vec, dim, bytes_por_valor): return n_vec * dim * bytes_por_valor
    esquemas = {"ColPali (1030×128, fp16)": bytes_pagina(1030, 128, 2), "ColPali binarizado (1030×128 bits)": 1030 * 128 / 8, "token pooling ÷4 (≈258×128, fp16)": bytes_pagina(258, 128, 2),
                "1 vector 1024-d fp16 (DSE / denso)": bytes_pagina(1, 1024, 2), "1 vector 1024-d binario": 1024 / 8, "texto OCR + embedding 1024-d fp16 (≈ 3 KB de texto)": 3000 + bytes_pagina(1, 1024, 2)}
    paginas = [10**4, 10**6, 10**8]
    df = pd.DataFrame({n: [b * p / 1e9 for p in paginas] for n, b in esquemas.items()}, index=[f"{p:,} páginas" for p in paginas]).T.round(2); display(df.rename(columns=lambda c: c + " (GB)"))
    fig, ax = plt.subplots(figsize=(8.5, 3.6)); ax.barh(list(esquemas), [b / 1024 for b in esquemas.values()], color=[AZUL, AZUL, AZUL, GRIS, GRIS, NARANJA]); ax.set_xscale("log")
    ax.set_xlabel("KiB por página (escala log)"); ax.set_title("El multi-vector cuesta ~100× más almacenamiento por página"); ax.invert_yaxis(); plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** Para 1 M de páginas, ColPali en `fp16` ocupa **≈ 264 GB** frente a ≈ 2 GB de un vector denso: el multi-vector se paga en RAM/SSD y en cómputo de MaxSim. Las palancas son: **binarizar**, *token pooling* (agrupar patches), reducir $D$, **pre-filtrar** con un vector por página y reordenar con MaxSim, o **codificaciones de dimensión fija** como MUVERA (Dhulipala et al., 2024: convierten multi-vector en un vector único para usar ANN). 🟡 Los factores de las filas «binarizado» y «pooling» son aritmética sobre el esquema; la **pérdida de calidad** hay que medirla (módulo 14 y 15).
    """)
    nb.md("""
    ### 6.4 Con modelos reales: ColPali / ColQwen y ViDoRe **(opcional, no probada en CPU)**
    En Colab con GPU (L4 recomendada, bf16) puedes usar el paquete `colpali-engine`. La API siguiente es la del README del paquete (PyPI): consulta la versión instalada porque los nombres de checkpoints y métodos evolucionan. **Esta celda no se pudo ejecutar en el entorno de desarrollo (sin acceso a Hugging Face ni GPU).**
    """)
    nb.code(r'''
    RUN_COLPALI = False      # True en Colab con GPU. pip install -q colpali-engine
    if RUN_COLPALI:
        from colpali_engine.models import ColPali, ColPaliProcessor
        from PIL import Image
        nombre = "vidore/colpali-v1.3"                       # alternativas más recientes: familia ColQwen2/2.5 (mismo patrón de API)
        modelo = ColPali.from_pretrained(nombre, torch_dtype=torch.bfloat16, device_map=device).eval(); proc = ColPaliProcessor.from_pretrained(nombre)
        paginas_img = [Image.fromarray((render(GRID[i], np.random.default_rng(i), 0.0) * 255).astype("uint8")).convert("RGB").resize((448, 448)) for i in range(4)]
        consultas_txt = ["cache index", "token query"]
        with torch.no_grad():
            emb_pag = modelo(**proc.process_images(paginas_img).to(modelo.device)); emb_q = modelo(**proc.process_queries(consultas_txt).to(modelo.device))
        print(proc.score_multi_vector(emb_q, emb_pag))       # (n_queries, n_páginas)
    else:
        print("RUN_COLPALI=False: celda omitida. En Hugging Face Transformers también existe ColPaliForRetrieval (checkpoint «vidore/colpali-v1.3-hf»).")
    ''')
    nb.md("""
    **Benchmarks.** *ViDoRe* (Faysse et al., 2024) evalúa retrieval a nivel de página con nDCG@5; **ViDoRe V2** (Macé et al., 2025) sube el listón; **ViDoRe V3** (arXiv ene-2026, ACL 2026) cubre 10 datasets profesionales, ≈ 26 000 páginas y 3 099 queries en 6 idiomas, con anotación humana; concluye que los retrievers visuales superan a los de solo texto y que late interaction y reranking de texto ayudan, pero que **siguen fallando con elementos no textuales, preguntas abiertas y grounding fino** (a oct-2026; fuente: su paper). MIEB (Xiao et al., 2025) es el benchmark masivo de embeddings de imagen.
    """)

    # ───────── 7. Unificados ─────────
    nb.md("""
    ## 7. Embeddings unificados multimodales
    La tendencia 2025–2026 es **un solo modelo y un solo espacio** para texto, imágenes, video, audio y documentos, en lugar de una torre por modalidad.

    | Modelo | Qué ofrece (fuente) | Madurez |
    |---|---|---|
    | **Gemini Embedding 2** (Google) | Primer modelo de embeddings nativamente multimodal de Google: texto, imágenes, video, audio y PDFs en un único espacio; >100 idiomas; Matryoshka (dim. por defecto 3 072). Lanzado en *preview* el **10-mar-2026** y GA el **22-abr-2026**. Según la cobertura de prensa que pude consultar (no pude abrir blog.google/ai.google.dev desde mi entorno), límites por petición de ≈ 8 192 tokens de texto, 6 imágenes, video hasta 120 s, audio hasta 80 s y PDFs de hasta 6 páginas, y **espacio incompatible con `gemini-embedding-001`** (hay que re-embeber). **Verifica límites y precios en la documentación oficial.** | 🟡 |
    | **jina-embeddings-v4** (Jina AI) | Texto + imágenes (incluidos documentos visuales); produce **vectores densos y multi-vector (late interaction)** (Günther et al., 2025) | 🟡 |
    | **VLM2Vec / MMEB** | Convierte VLMs en embedders multimodales con un benchmark de 36 tareas (Jiang et al., 2024) | 🟡 / 🔴 |
    | **ImageBind** (Meta) | Un espacio de 6 modalidades con *imágenes como pivote* (Girdhar et al., CVPR 2023) | 🟡 |
    | **CLAP** | Audio ↔ texto con contraste (Elizalde et al., 2022) | 🟡 |

    > 📅 Las capacidades de modelos propietarios cambian: la tabla anterior es **a oct-2026** y sujeta a la fecha de cada fuente. El paper de *Gemini Embedding* (Lee et al., 2025, arXiv 2503.07891) describe el modelo de **texto**; la versión multimodal «2» se documenta en anuncios y documentación de Google.
    """)
    nb.md("**(opcional, protegida)** Llamada a la API de Gemini para embeber un texto y una imagen y medir su similitud. Solo se ejecuta si defines `GEMINI_API_KEY`; el id del modelo lo lees de `GEMINI_EMBED_MODEL` (por defecto `gemini-embedding-2`; en *preview* se llamó `gemini-embedding-2-preview`). Sigue el patrón del SDK `google-genai`; **verifica nombres de parámetros en la documentación vigente**.")
    nb.code(r'''
    if os.environ.get("GEMINI_API_KEY"):
        from google import genai
        from google.genai import types
        import io
        from PIL import Image
        cliente = genai.Client(api_key=os.environ["GEMINI_API_KEY"]); modelo_id = os.environ.get("GEMINI_EMBED_MODEL", "gemini-embedding-2")
        buf = io.BytesIO(); Image.fromarray((Xte[0] * 255).astype("uint8")).resize((224, 224)).save(buf, format="PNG")
        r_txt = cliente.models.embed_content(model=modelo_id, contents=[" ".join(Tte[0])], config=types.EmbedContentConfig(output_dimensionality=768))
        r_img = cliente.models.embed_content(model=modelo_id, contents=[types.Part.from_bytes(data=buf.getvalue(), mime_type="image/png")], config=types.EmbedContentConfig(output_dimensionality=768))
        a, b = (np.array(r.embeddings[0].values) for r in (r_txt, r_img)); a, b = a / np.linalg.norm(a), b / np.linalg.norm(b)   # normalizar al truncar (Matryoshka)
        print("coseno texto↔imagen:", float(a @ b))
    else:
        print("Sin GEMINI_API_KEY: celda omitida (opcional).")
    ''')

    # ───────── 8. Audio y video ─────────
    nb.md("""
    ## 8. Audio y video en espacios de embedding
    - **Audio**: CLAP (audio ↔ texto) e ImageBind; para voz, la ruta habitual sigue siendo **ASR (p. ej. Whisper) → texto → embedder**, que conserva la exactitud léxica. Los embeddings de audio nativos (Gemini Embedding 2 declara audio sin transcripción) ganan cuando importa el sonido no verbal (música, eventos) o se quiere evitar el coste/latencia de ASR. 🟡
    - **Video**: se suele **muestrear fotogramas** (p. ej. 1–2 fps), embeberlos y combinarlos. Lo que se pierde al combinar es el **orden temporal**. Lo medimos.
    """)
    nb.code(r'''
    def video(forma, color, direccion, rng, n_frames=8):
        """Una figura que cruza el cuadro de izquierda a derecha (direccion=+1) o al revés (-1)."""
        xs = np.linspace(8, 24, n_frames)[::direccion]; cy = int(rng.integers(14, 19))
        return np.stack([dibuja(forma, color, rng, centro=(int(x), cy)) for x in xs])
    rng_v = np.random.default_rng(5); I_ = MODELOS["InfoNCE τ aprendida"]["I"]; Vs, Dir, Col = [], [], []
    for _ in range(160):
        d = int(rng_v.choice([1, -1])); k = int(rng_v.integers(0, 16)); f, c = CONCEPTOS[k]
        Vs.append(video(f, c, d, rng_v)); Dir.append(d); Col.append(k)
    with torch.no_grad(): FE = np.stack([I_(torch.tensor(v)).numpy() for v in Vs])      # (160, 8, D)
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score
    medio = FE.mean(1); secuencia = FE.reshape(len(FE), -1); Dir = np.array(Dir)
    acc = {"vector medio de los frames": cross_val_score(LogisticRegression(max_iter=2000), medio, Dir, cv=5).mean(),
           "frames concatenados (conserva el orden)": cross_val_score(LogisticRegression(max_iter=2000), secuencia, Dir, cv=5).mean()}
    acc_col = cross_val_score(LogisticRegression(max_iter=2000), medio, np.array(Col), cv=5).mean()
    ax = pd.Series(acc).plot(kind="bar", color=[ROJO, VERDE], figsize=(6, 3.2), rot=10); ax.axhline(.5, color=GRIS, ls="--"); ax.set_ylim(0, 1.05); ax.set_ylabel("precisión al predecir la dirección")
    ax.set_title("Promediar frames borra el orden temporal"); plt.tight_layout(); plt.show(); print(f"(el mismo vector medio SÍ identifica el concepto forma×color: precisión {acc_col:.2f})")
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** El vector medio de frames identifica **qué** aparece (forma y color) pero **no hacia dónde se mueve**: la dirección queda al azar (≈ 0.5) porque la media es invariante al orden. Conservar el orden (concatenar, atención temporal, modelos de video nativos) lo resuelve en el juguete.
    > Implicación práctica: un embedding de video basado en frames sirve para «encontrar el clip donde sale X», no para «el clip donde alguien *entra* en vez de *salir*».
    """)

    # ───────── 9. Decisión ─────────
    nb.md("""
    ## 9. ¿OCR + texto o embedding visual? Árbol de decisión
    """)
    nb.gemini(
        "imagen", "M16-IMG-03", "Árbol de decisión: OCR + texto vs embedding visual",
        "Guía de decisión para elegir el pipeline de documentos de Políglota según el tipo de contenido, la calidad del OCR y las restricciones de coste.",
        """
        Diagrama de flujo técnico limpio, fondo blanco, paleta sobria (azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280), tipografía sans-serif legible, flechas claras, sin ilustraciones decorativas. 16:9.
        Árbol de decisión de arriba abajo con rombos (preguntas) y rectángulos redondeados (resultados). Textos literales:
        Rombo 1: «¿El contenido relevante es texto limpio y seleccionable?» → Sí: rectángulo verde «Parseo + texto + embedder de texto (+ BM25 híbrido)». → No: siguiente.
        Rombo 2: «¿Hay tablas, gráficos, capturas o diagramas que responden preguntas?» → No: rectángulo azul «OCR de calidad + texto». → Sí: siguiente.
        Rombo 3: «¿Presupuesto de almacenamiento multi-vector (≈ 258 KiB/página)?» → Sí: rectángulo naranja «ColPali / ColQwen (multi-vector) + MaxSim». → No: rectángulo naranja «Un vector por página (DSE) o pooling/binarización + reranking».
        A la derecha, un recuadro gris: «Siempre: evaluar con IC por tipo de consulta (módulo 15). Considerar híbrido: texto + visual con fusión RRF».
        Título superior: «¿OCR + texto o embedding visual?».
        Evita: texto ilegible o inventado, ilustraciones decorativas, más de tres rombos, flechas que se crucen.
        """,
        "Árbol de decisión con tres preguntas que lleva a parseo+texto, OCR de calidad, ColPali multi-vector o un vector por página.",
        """
        texto limpio? --sí--> parseo + texto + embedder (+BM25)
           no -> ¿hay tablas/figuras que responden? --no--> OCR de calidad + texto
                    sí -> ¿presupuesto multi-vector? --sí--> ColPali/ColQwen + MaxSim ; no -> 1 vector/página o pooling + rerank
        """,
    )
    nb.md("""
    > 👀 **Qué debes observar.** La primera pregunta evita pagar por visión cuando no hace falta (nuestro experimento: OCR perfecto en texto limpio). La tercera es de **coste**: el multi-vector no es gratis (§6.3). La mejor práctica actual es **híbrida**: índice de texto + índice visual y fusión por rangos.
    > Idea para Políglota: la documentación técnica tiene muchos diagramas de arquitectura y capturas de consola: ahí el índice visual aporta; en README y referencias API, no.
    """)
    nb.md("""
    ## 🗺️ Mapa de madurez (estado a oct-2026)
    Ya has entrenado un CLIP en miniatura, medido el modality gap y construido un ColPali de juguete; la tabla sitúa esas técnicas y las más nuevas (embeddings unificados, audio y video) por madurez antes de ver cómo se usan en producción.


    | Técnica | Madurez | Quién / dónde | Fuente |
    |---|---|---|---|
    | CLIP (contraste imagen-texto con InfoNCE) | 🟢 sólido | Base de casi todo el ecosistema texto-imagen | Radford et al. 2021 |
    | SigLIP (pérdida sigmoide) y SigLIP 2 (multilingüe, captioning + auto-distilación + datos curados) | 🟢 sólido / 🟡 SigLIP 2 en adopción | Google; codificadores de visión de PaliGemma | Zhai et al. 2023; Tschannen et al. 2025 |
    | Modality gap: existencia y medición | 🟢 sólido (fenómeno); 🟡 cuánto importa en producto | Investigación; práctica de índices mixtos | Liang et al. 2022 |
    | Retrieval visual de documentos con multi-vector (ColPali / ColQwen) | 🟡 emergente (resultados fuertes en ViDoRe; coste de almacenamiento) | ILLUIN y comunidad; también Jina v4 (dense + multi-vector) | Faysse et al. 2024; Günther et al. 2025 |
    | Un único vector por captura de pantalla (DSE) | 🟡 emergente | Investigación (Waterloo) | Ma et al. 2024 |
    | Embeddings unificados multimodales (texto, imagen, video, audio, PDF en un espacio) | 🟡 emergente: Gemini Embedding 2 (preview 10-mar-2026, GA 22-abr-2026 según el blog de Google) | Google; también Jina v4, VLM2Vec en investigación | ver §6 |
    | Espacios de audio/video (CLAP, ImageBind) | 🟡 / 🔴 | Investigación | Elizalde 2022; Girdhar 2023 |
    | Embeddings de video con orden temporal fino | 🔴 experimental | — | (§8) |
    """)
    nb.md("""
    ## 🏭 En producción
    - **Un índice por modalidad, fusión por rangos.** Mezclar vectores de texto e imagen en un solo ANN sin calibrar sufre el *modality gap* (§5). Lo habitual es consultar índices separados y fusionar con RRF (módulo 13), o usar un modelo unificado entrenado para ello.
    - **Documentos visuales:** los proveedores de embeddings (Google con Gemini Embedding 2, Jina con v4, Cohere, Voyage…) ofrecen API multimodal; los equipos que quieren control usan ColPali/ColQwen con *late interaction* y aceleran con pre-filtro + reordenado. Los costes dominantes son **almacenamiento** y **latencia de MaxSim**, no la calidad.
    - **Re-embedding:** cambiar de modelo multimodal exige re-procesar **imágenes/PDFs** (más caro que texto). Guarda las páginas renderizadas y versiona el modelo (módulo 18).
    - **Privacidad:** capturas de pantalla contienen datos sensibles (tokens, correos): decide qué se envía a APIs externas.
    - **Evaluación:** construye un golden set de *queries visuales* (preguntas sobre tablas/figuras) con anotación humana y mide por tipo de consulta con IC (módulo 15).
    """)
    nb.md("""
    ## 🧠 Secretos de la élite
    1. **El gap casi nunca importa para ranking dentro de una modalidad, y siempre importa al mezclar.** Medido aquí: con τ=0.01 (gap ≈ 1) el 100 % de las queries tiene un texto equivocado por delante de la imagen correcta en un índice mixto, y restar el centroide por modalidad **no** lo arregla (§5); con gap ≤ 0.35 no hubo intrusos.
    2. **La temperatura es un hiperparámetro de geometría, no solo de optimización**: $\\tau$ baja ⇒ gap alto (Liang et al.; nuestro barrido). Al comparar dos modelos, compara también su $\\tau$ aprendida.
    3. **Los falsos negativos en el batch** (varias imágenes del mismo concepto) ponen un suelo a la pérdida contrastiva: con pocos conceptos y batches grandes, la pérdida no baja de $\\ln(N/\\text{conceptos})$ aunque el modelo sea perfecto.
    4. **El coste real del multi-vector es el almacenamiento**: ≈ 257.5 KB/página en ColPali (fp16) ⇒ ≈ 257 GB por millón de páginas; decide pooling/binarización/pre-filtro *antes* de indexar.
    5. **Un OCR clásico bien afinado es un baseline duro** en texto limpio (§6.2). Compara siempre contra «OCR + BM25 + embedder de texto» por tipo de consulta antes de adoptar visión.
    6. **La precisión de retrieval no mide composición, y el pooling medio la destruye**: un vector medio de frames, patches o palabras es invariante al orden (sirve para «qué hay», no para «dónde/cuándo/a quién»), y los VLM contrastivos reales se comportan casi como bolsas de palabras en ARO (Yuksekgonul et al., ICLR 2023) porque sus negativos de lote casi nunca difieren solo en el orden. Remedio: negativos duros composicionales al entrenar y un slice composicional en el golden set (§3b).
    7. **Verifica límites por petición y compatibilidad de espacio al migrar a un embedder multimodal propietario**: p. ej., la prensa reporta que Gemini Embedding 2 no comparte espacio con `gemini-embedding-001` (hay que re-embeber).
    8. **Benchmarks de documentos (ViDoRe V3) muestran que los retrievers visuales ganan a los de texto, pero siguen flojos con elementos no textuales y grounding fino** (a oct-2026): no vendas «OCR-free resuelve todo».
    """)
    nb.md("""
    ## ⚠️ Errores comunes
    - Comparar similitudes **entre modalidades** (texto↔texto vs texto↔imagen) como si estuvieran en la misma escala.
    - Olvidar **normalizar** al truncar dimensiones (Matryoshka) en APIs multimodales.
    - Evaluar retrieval visual solo con queries *léxicas* (que un OCR resuelve) y concluir que «la visión no aporta» — o con queries visuales y concluir que «OCR no sirve».
    - Usar fuentes/renderizados de entrenamiento distintos a producción (resolución, DPI, idioma) sin medir.
    - Indexar páginas a baja resolución para ahorrar y perder texto pequeño.
    - Tratar el espacio de un modelo propietario como estable: **versiona** modelo y dimensión.
    - Promediar frames y esperar sensibilidad temporal.
    """)
    nb.md("""
    ## 📝 Autoevaluación
    <details><summary><b>1. (Cálculo)</b> Una colección de 2 millones de páginas con ColPali (1 030 vectores × 128 d, fp16). ¿Cuánto ocupa? ¿Y binarizada a 1 bit por dimensión?</summary>

    $1030\\times128\\times2=263\\,680$ B/página ⇒ $2\\times10^6\\times263\\,680\\approx527$ GB. Binarizada: $1030\\times128/8=16\\,480$ B ⇒ ≈ 33 GB (16× menos), a costa de calidad que debes medir.
    </details>

    <details><summary><b>2. (Cálculo)</b> Query de 3 tokens, página de 4 patches; similitudes (filas = tokens): [[.9,.1,.0,.2],[.1,.8,.3,.0],[.0,.2,.7,.1]]. ¿Score MaxSim? ¿Y con el vector medio si los vectores fueran ortonormales?</summary>

    Máximos por fila: .9 + .8 + .7 = **2.4**. Con el vector medio (promedio de patches y de tokens) cada token solo contribuye con ≈ 1/4 de su coincidencia: la señal se diluye (por eso el vector medio falló en nuestro experimento).
    </details>

    <details><summary><b>3. (Diagnóstico)</b> Tu índice mixto (imágenes + textos) devuelve casi solo textos para una query de texto. ¿Causa y arreglos?</summary>

    Modality gap: los textos están más cerca entre sí que de las imágenes. Arreglos: índices separados + RRF; un modelo entrenado para un espacio unificado; centrar cada modalidad (restar su centroide y renormalizar) ayuda a veces, pero en nuestro experimento extremo no bastó. Mide con un golden set mixto.
    </details>

    <details><summary><b>4. (Diagnóstico)</b> ColPali brilla en ViDoRe pero en tus PDFs financieros (tablas pequeñas, texto denso) un pipeline OCR+texto le gana. Hipótesis.</summary>

    Resolución de entrada insuficiente para texto pequeño; dominio distinto al de entrenamiento; las queries son léxicas (identificadores, cifras exactas) donde BM25/OCR son mejores; ViDoRe no representa tu distribución. Evalúa por tipo de consulta e híbrido.
    </details>

    <details><summary><b>5. (Transferencia)</b> Quieres buscar clips de video de demos de producto en Políglota. ¿Qué pipeline propones y qué no cubrirá?</summary>

    Muestreo de frames (+ ASR de la voz → texto) y embedder multimodal; fusión de índices de texto (transcripción) y visual. No cubrirá bien el **orden/dirección temporal** ni acciones finas: añade metadatos o un modelo de video nativo.
    </details>

    <details><summary><b>6. (Transferencia)</b> ¿Cómo repetirías el experimento de modality gap con CLIP real y qué medirías?</summary>

    Embeder N pares imagen–caption de COCO con `get_image_features/get_text_features`, normalizar, medir ‖centroide_img − centroide_txt‖, el coseno medio intra-modalidad y la «tasa de intrusos» en un índice mixto antes/después de centrar. Comparar CLIP vs SigLIP/SigLIP 2.
    </details>
    """)
    nb.md("""
    ## 📚 Referencias
    - Radford et al. (2021). *Learning Transferable Visual Models From Natural Language Supervision* (CLIP). ICML 2021. <https://arxiv.org/abs/2103.00020>
    - Yuksekgonul, Bianchi, Kalluri, Jurafsky, Zou (2023). *When and Why Vision-Language Models Behave like Bags-Of-Words, and What to Do About It?* ICLR 2023. <https://arxiv.org/abs/2210.01936>
    - Zhai, Mustafa, Kolesnikov, Beyer (2023). *Sigmoid Loss for Language Image Pre-Training* (SigLIP). ICCV 2023. <https://arxiv.org/abs/2303.15343>
    - Tschannen et al. (2025). *SigLIP 2: Multilingual Vision-Language Encoders with Improved Semantic Understanding, Localization, and Dense Features*. Preprint. <https://arxiv.org/abs/2502.14786>
    - Liang, Zhang, Kwon, Yeung, Zou (2022). *Mind the Gap: Understanding the Modality Gap in Multi-modal Contrastive Representation Learning*. NeurIPS 2022. <https://arxiv.org/abs/2203.02053>
    - Faysse et al. (2024). *ColPali: Efficient Document Retrieval with Vision Language Models*. ICLR 2025. <https://arxiv.org/abs/2407.01449>
    - Ma, Lin, Li, Chen, Lin (2024). *Unifying Multimodal Retrieval via Document Screenshot Embedding*. EMNLP 2024. <https://arxiv.org/abs/2406.11251>
    - Macé, Loison, Faysse (2025). *ViDoRe Benchmark V2: Raising the Bar for Visual Retrieval*. Preprint. <https://arxiv.org/abs/2505.17166>
    - Loison, Macé, Edy et al. (2026). *ViDoRe V3: A Comprehensive Evaluation of Retrieval Augmented Generation in Complex Real-World Scenarios*. Preprint. <https://arxiv.org/abs/2601.08620>
    - Günther et al. (2025). *jina-embeddings-v4: Universal Embeddings for Multimodal Multilingual Retrieval*. Preprint. <https://arxiv.org/abs/2506.18902>
    - Jiang et al. (2024). *VLM2Vec: Training Vision-Language Models for Massive Multimodal Embedding Tasks*. Informe técnico. <https://arxiv.org/abs/2410.05160>
    - Girdhar et al. (2023). *ImageBind: One Embedding Space To Bind Them All*. CVPR 2023. <https://arxiv.org/abs/2305.05665>
    - Elizalde et al. (2022). *CLAP: Learning Audio Concepts From Natural Language Supervision*. ICASSP 2023. <https://arxiv.org/abs/2206.04769>
    - Xiao et al. (2025). *MIEB: Massive Image Embedding Benchmark*. Preprint. <https://arxiv.org/abs/2504.10471>
    - Lee et al. (2025). *Gemini Embedding: Generalizable Embeddings from Gemini*. <https://arxiv.org/abs/2503.07891>
    - Khattab & Zaharia (2020). *ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT*. SIGIR 2020. <https://arxiv.org/abs/2004.12832> · Dhulipala et al. (2024). *MUVERA: Multi-Vector Retrieval via Fixed Dimensional Encodings*. NeurIPS 2024. <https://arxiv.org/abs/2405.19504>
    - Anuncio de disponibilidad general de Gemini Embedding 2 (Google, abr-2026): <https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-embedding-2-generally-available/> *(fecha de GA del propio blog; los límites por petición, contrastados con prensa: confírmalos en la documentación oficial)*.
    - Paquete `colpali-engine` (PyPI) <https://pypi.org/project/colpali-engine/>.
    - Material del curso: módulos 08 (tokens multimodales), 11, 13, 14, 15 (`poliglota_eval.py`), 18.
    """)
