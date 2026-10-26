"""Lección 17 · parte 1: cabecera, probing, representación lineal, dimensiones dominantes."""
from _a6_common import SYNTH_DATA_SRC, CORPUS_SRC
from _a6_src15 import RETRIEVERS_SRC
from _a6_src17 import SAE_SRC, PROBE_SRC


def part1(nb):
    nb.md(f"""
    {nb.badge()}

    # Módulo 17 · Interpretabilidad y geometría de los embeddings

    | | |
    |---|---|
    | **Nivel** | 🔴 Experto |
    | **Duración** | ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) |
    | **GPU** | No necesaria con `FAST_DEV_RUN=True` (CPU, ≈ 3–4 min). T4/L4 solo si activas el embedder real opcional |
    | **Prerrequisitos** | 09–10 (geometría, anisotropía, pooling), 11 (contrastivo), 12 (embedders), 15 (evaluación) |
    | **Hilo conductor** | ¿Qué *sabe* el vector que Políglota guarda por cada documento? ¿Qué filtra? |

    > 🔴 **Honestidad de madurez.** Este módulo mezcla técnicas **sólidas** (probing, direcciones lineales, anisotropía), **emergentes** (sparse autoencoders sobre embeddings) y **experimentales** (interpretación causal fiable, steering en producción). Marcamos cada una; lo que medimos con nuestros experimentos de juguete **no** es evidencia sobre modelos reales.
    > 🧭 **Ruta núcleo vs ampliación.** Núcleo (≈ 3 h, lo que usa el proyecto): secciones 1–4 (probing, dirección lineal y steering), 6–7 (superposición y SAE TopK) y 9 (vec2text: el TODO 5 audita la inversión). Ampliación (≈ 2 h): 5 (dimensiones dominantes) y 8 (qué codifica un embedding: longitud y orden).
    """)
    nb.md("""
    ## 🎯 Objetivos de aprendizaje
    1. **Diseñar e interpretar** sondas (*probes*) lineales y no lineales con **control tasks** y selectividad (Hewitt & Liang).
    2. **Formular** la hipótesis de representación lineal y **comprobarla**: dirección de un concepto por diferencia de medias, steering de una consulta y borrado lineal de un concepto.
    3. **Diagnosticar** dimensiones dominantes y anisotropía y **corregirlas** (estandarizar / *all-but-the-top*).
    4. **Implementar desde cero** un *sparse autoencoder* **TopK** (con AuxK) en PyTorch y un SAE ReLU+L1, y **compararlos** recuperando características *plantadas* con verdad conocida.
    5. **Aplicar** un SAE a embeddings de documentos de Políglota y **evaluar** si sus *features* son interpretables (pureza vs k-means/PCA) y estables entre semillas.
    6. **Usar** una *feature* para **steering** del retrieval y **explicar** sus límites.
    7. **Medir** qué información de un documento se puede **reconstruir** desde su embedding (inversión) y su coste de privacidad.
    """)
    nb.md("""
    ## 🔁 Conexión con módulos anteriores
    <details><summary><b>1.</b> (Módulo 10) ¿Qué es la anisotropía de los embeddings contextuales y cómo se corrige?</summary>

    Los vectores ocupan un cono estrecho (coseno medio alto entre textos no relacionados). Se corrige centrando, **whitening**, quitando componentes principales dominantes (*all-but-the-top*, Mu et al. 2018) o estandarizando dimensiones. En §5 medimos el efecto de una sola dimensión dominante.
    </details>

    <details><summary><b>2.</b> (Módulo 11) ¿Qué miden alineación y uniformidad?</summary>

    Alineación: cercanía de pares positivos. Uniformidad: dispersión de los embeddings en la esfera. Un embedding anisotrópico tiene mala uniformidad: «menos capacidad» efectiva.
    </details>

    <details><summary><b>3.</b> (Módulo 12) ¿Qué es Matryoshka y qué sugiere sobre dónde está la información en un embedding?</summary>

    El entrenamiento Matryoshka fuerza que **los primeros $m$ componentes** sirvan por sí solos: la información está *ordenada por importancia* en las dimensiones, lo cual no es el caso en un embedding «normal», donde está **distribuida** y rotada arbitrariamente.
    </details>

    <details><summary><b>4.</b> (Módulo 15) Antes de afirmar «el SAE A es mejor que B», ¿qué necesitas?</summary>

    Misma métrica por query/feature, IC bootstrap, varias semillas y un test pareado; aquí veremos que **la semilla cambia qué features aparecen**.
    </details>

    <details><summary><b>5.</b> (Módulos 01 y 04, Diagnóstico) Un probe lineal predice el idioma (ES/EN/código) desde el embedding con un 99 % de acierto. ¿Demuestra que el modelo «entiende» el idioma?</summary>

    No necesariamente: el idioma es casi trivial de leer en la **forma superficial** (acentos y «ñ» con bytes UTF-8 de 2 bytes, módulo 01; tokens distintos y fertilidad distinta, módulo 04; símbolos del código). Un probe alto solo dice que la información es linealmente accesible. Por eso la sección 3 mide la **selectividad** frente a una *control task* (Hewitt & Liang) antes de interpretar.
    </details>
    """)

    nb.md("""
    ## 1. Intuición: abrir el vector
    Un embedding de 768 números es una caja negra: sabemos que «cerca = similar», pero no **qué eje significa qué**. La interpretabilidad pregunta tres cosas, de menor a mayor exigencia:
    1. **¿Qué información contiene?** (probing: ¿se puede *leer* X desde el vector?)
    2. **¿Cómo está organizada?** (geometría: direcciones, dimensiones dominantes, subespacios)
    3. **¿Qué usa el sistema?** (causalidad: si muevo el vector en esa dirección, ¿cambia el comportamiento?)

    **Analogías con lo que ya sabes.** (a) En *recsys*, los factores latentes de una factorización de matrices rara vez son interpretables por sí solos: hay que *rotarlos* o inspeccionar sus ítems extremos; un SAE es el análogo moderno (diccionario disperso en lugar de bases densas). (b) En *compresión*, un diccionario sobrecompleto con codificación dispersa es *sparse coding*: más átomos que dimensiones, pero pocos activos por muestra.
    """)
    nb.gemini(
        "imagen", "M17-IMG-3", "Capas de información dentro de un embedding de texto",
        "Mapa de qué codifica un embedding de documento (léxico, tema, idioma, estilo, longitud) y qué puede extraer un atacante o un probe.",
        """
        Diagrama técnico limpio, fondo blanco, paleta sobria (azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280), tipografía sans-serif legible, flechas claras, sin ilustraciones decorativas. 16:9.
        Composición: a la izquierda un documento (rectángulo blanco con borde gris y tres líneas de texto: «La caché expira tras un TTL…») con una flecha azul etiquetada «Embedder de texto» hacia un vector central dibujado como una fila larga de 12 celdas de colores (etiqueta «z ∈ R^768»).
        A la derecha del vector, cinco flechas verdes que salen hacia cinco cajas apiladas, con estos textos literales:
        «Tema (sonda lineal: muy legible)»,
        «Idioma (sonda lineal: casi perfecta)»,
        «Palabras concretas (parcial: inversión con vec2text)»,
        «Longitud y estilo (parcial)»,
        «Orden de las palabras (depende del modelo)».
        Debajo del vector, una flecha naranja hacia atrás hacia el documento con la etiqueta «Inversión: reconstruir el texto desde z» y un candado gris con el texto «privacidad (módulo 18)».
        Título superior: «¿Qué hay dentro de un embedding?». Pie en gris: «Probing mide lo que se puede leer, no lo que el sistema usa».
        Evita: texto ilegible o inventado, ilustraciones decorativas, sombras 3D, más de cinco cajas a la derecha, flechas ambiguas.
        """,
        "Un documento pasa por un embedder y el vector resultante permite leer tema, idioma, palabras, longitud y orden, con una flecha de inversión hacia el texto original.",
        """
        documento -> [embedder] -> z (768-d) --+--> tema (muy legible)
                                               +--> idioma (casi perfecto)
                                               +--> palabras (parcial; inversión)
                                               +--> longitud/estilo (parcial)
                                               +--> orden de palabras (depende)
                          z -- inversión --> texto   (privacidad, módulo 18)
        """,
    )
    nb.md("""
    > 👀 **Qué debes observar.** Un embedding **no es una caja opaca para un probe ni para un atacante**: tema e idioma se leen casi gratis, y las palabras concretas se pueden recuperar parcialmente. Lo que *no* sabemos todavía es qué parte de esa información **usa** el retrieval: eso exige experimentos causales (§4 y §8).
    """)

    nb.md("## 2. Entorno y embeddings de Políglota con etiquetas")
    nb.code("!pip install -q numpy scipy scikit-learn matplotlib pandas torch sentence-transformers")
    nb.code(r'''
    import os, re, math, random, time, warnings
    import numpy as np, pandas as pd
    import matplotlib.pyplot as plt
    warnings.filterwarnings("ignore")
    SEED = 42; FAST_DEV_RUN = True
    random.seed(SEED); np.random.seed(SEED)
    import torch
    torch.manual_seed(SEED)
    if FAST_DEV_RUN: torch.set_num_threads(1)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    AZUL, NARANJA, VERDE, GRIS, ROJO = "#1F6FEB", "#F28E2B", "#2CA02C", "#6B7280", "#D62728"
    plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": .25})
    print(f"device={device} · FAST_DEV_RUN={FAST_DEV_RUN} · semilla={SEED}")
    ''')
    nb.md("""
    Para **medir** interpretabilidad necesitamos una *verdad terreno*: usamos el generador sintético de Políglota, que etiqueta cada documento con **idioma, tema (12) y faceta (36)** (contrato común: mismo esquema que `carga_corpus`; aquí no usamos la cadena real porque necesitamos esas etiquetas; en el proyecto sí aplicarás el SAE a `carga_corpus`).
    El «embedder» por defecto es **LSI-64** (TF-IDF + SVD): un embedding denso real, entrenado en el corpus y reproducible en CPU. Con red y GPU puedes sustituirlo por un embedder real (`USE_ST=True`): *esa opción no se pudo probar en el entorno de desarrollo*.
    """)
    nb.code(SYNTH_DATA_SRC); nb.code(CORPUS_SRC); nb.code(RETRIEVERS_SRC)
    nb.code(r'''
    corp = genera_sintetico(n_temas=12, docs_por_faceta=40 if FAST_DEV_RUN else 80, seed=SEED)
    docs = [d for d in corp["docs"] if d["lang"] != "code"]; txt = [d["text"] for d in docs]; ids = [d["id"] for d in docs]
    lang = np.array([d["lang"] for d in docs]); facet = np.array([d["id"].split("-", 1)[1].rsplit("-", 1)[0] for d in docs]); topic = np.array([f.split(".")[0] for f in facet])
    uniq = lambda a: np.unique(a, return_inverse=True)[1]; lang_id, top_id, fac_id = uniq(lang), uniq(topic), uniq(facet)

    USE_ST = False       # True: embedder real (sentence-transformers multilingüe). NO probado en el entorno de desarrollo (sin HF).
    def embebe_docs(textos, dim=64):
        if USE_ST:
            try:
                from sentence_transformers import SentenceTransformer
                return SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2", device=device).encode(textos, normalize_embeddings=True, show_progress_bar=False).astype(np.float32), None
            except Exception as e: print("ST no disponible:", type(e).__name__)
        m = LSI(dim, SEED).fit(textos, ids); return m.Z.astype(np.float32), m

    E, lsi = embebe_docs(txt, 64); En = E / np.linalg.norm(E, axis=1, keepdims=True)
    print(f"{len(docs)} documentos · {len(set(facet))} facetas · {len(set(topic))} temas · embeddings {E.shape}")
    ''')

    # ───────── 3. Probing ─────────
    nb.md("""
    ## 3. Probing: ¿se puede *leer* X desde el vector?
    Una **sonda** es un clasificador supervisado entrenado sobre embeddings **congelados** para predecir una propiedad $y$ (idioma, tema, categoría gramatical…). Si la sonda acierta, la información está *presente* (y accesible para esa familia de sondas).
    **Hewitt & Manning (NAACL 2019)** llevaron la idea más lejos con la **sonda estructural**: buscan una transformación lineal $B$ tal que la **distancia L2 al cuadrado** $\\lVert B(h_i-h_j)\\rVert^2$ aproxime la distancia en el árbol sintáctico entre las palabras $i,j$ (y $\\lVert Bh_i\\rVert^2$ la profundidad); en ELMo y BERT existen esas transformaciones y en los baselines no: **el árbol sintáctico está incrustado en la geometría**.

    **El problema:** una sonda muy expresiva puede *aprender la tarea por sí sola* aunque el embedding no la codifique. **Hewitt & Liang (EMNLP 2019)** proponen **control tasks**: asignar etiquetas **aleatorias por tipo** (aquí, por faceta). Una sonda que memoriza tipos saca buena nota en la tarea de control; una sonda *selectiva* saca nota alta en la tarea real y baja en el control:
    $$\\text{selectividad}=\\text{acc}_{\\text{tarea real}}-\\text{acc}_{\\text{control}}$$
    Belinkov (2022) resume las limitaciones: probar que *se puede leer* no prueba que el modelo *lo use*.
    """)
    nb.code(PROBE_SRC)
    nb.code(r'''
    E24, _ = embebe_docs(txt, 24)                         # embedding compacto: si es muy grande, hasta el control es separable
    ctrl = tarea_control(list(facet), 12)                 # etiqueta aleatoria (12 clases) fija por faceta
    filas = []
    for tarea, y in (("idioma (2)", lang_id), ("tema (12)", top_id), ("CONTROL (12, aleatorio por faceta)", ctrl)):
        filas.append({"tarea": tarea, "sonda lineal": sonda(E24, y, "lineal"), "sonda MLP-256": sonda(E24, y, "mlp")})
    pt = pd.DataFrame(filas).set_index("tarea")
    sel = pd.Series({"selectividad lineal": pt.loc["tema (12)", "sonda lineal"] - pt.loc["CONTROL (12, aleatorio por faceta)", "sonda lineal"],
                     "selectividad MLP": pt.loc["tema (12)", "sonda MLP-256"] - pt.loc["CONTROL (12, aleatorio por faceta)", "sonda MLP-256"]})
    display(pt.round(3))
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.6)); pt.plot(kind="bar", ax=ax[0], color=[AZUL, NARANJA], rot=12); ax[0].set_ylabel("precisión en test"); ax[0].set_title("Sondas sobre LSI-24"); ax[0].legend(frameon=False, fontsize=8)
    ax[1].bar(sel.index, sel.values, color=[VERDE, ROJO]); ax[1].set_title("Selectividad (tema − control)"); ax[1].set_ylabel("selectividad"); plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** Idioma y tema se leen casi perfectamente. Pero la sonda **MLP** también «lee» la tarea de control (≈ 0.95): memoriza, así que su selectividad es mínima; la sonda **lineal** **no** puede (≈ 0.55) y su selectividad es alta. Conclusión metodológica (Hewitt & Liang): **prefiere sondas simples y reporta siempre la tarea de control**; si no, el «ha aprendido sintaxis» puede ser «la sonda aprendió sintaxis».
    > Si subes la dimensión a 64+, hasta el control se vuelve linealmente separable (el embedding es tan grande que *cualquier* etiquetado por clúster es lineal): la selectividad también depende de la **capacidad** del espacio.
    """)

    # ───────── 4. Representación lineal ─────────
    nb.md("""
    ## 4. La hipótesis de representación lineal: direcciones, steering y borrado
    **Hipótesis (Park, Choe, Veitch; ICML 2024):** los conceptos se codifican como **direcciones** del espacio de representación. Formalizan «concepto lineal» mediante pares contrafactuales y relacionan la hipótesis con (i) *probing lineal* y (ii) *steering* (mover la representación en esa dirección); argumentan que la geometría correcta para medir similitud entre direcciones requiere un **producto interno causal**, no el coseno ingenuo.
    **Receta mínima:** dirección de un concepto por **diferencia de medias**: $v_{A\\to B}=\\bar z_B-\\bar z_A$. **Steering:** $q'=\\mathrm{norm}(q+\\alpha v_{A\\to B})$.

    ✍️ **Ejemplo a mano (2D).** Documentos de «cache»: $(1, 0.2)$ y $(0.8, 0.6)$, media $(0.9, 0.4)$; de «git»: $(0.2, 1)$ y $(0.6, 0.8)$, media $(0.4, 0.9)$. Dirección $v_{\\text{cache}\\to\\text{git}} = (-0.5, 0.5)$. La query $q = (1, 0.2)$ con $\\alpha = 1$ pasa a $(0.5, 0.7)$ → normalizada $(0.58, 0.81)$: su vecino más cercano ya es un documento de «git» (coseno ≈ 1.00 con $(0.6, 0.8)$ frente a 0.95 con $(0.8, 0.6)$, el «cache» más cercano). Es la aritmética de vectores de word2vec (rey − hombre + mujer) aplicada a una consulta, y el «*boost* por categoría» de un recomendador hecho en el espacio de embeddings.
    """)
    nb.code(r'''
    topics = sorted(set(topic)); mu = {t: En[(topic == t) & (lang == "es")].mean(0) for t in topics}
    v_cache_git = mu["git"] - mu["cache"]
    qs = np.where((topic == "cache") & (lang == "es"))[0][:100]; alphas = [0, .25, .5, .75, 1, 1.25, 1.5, 2, 3]
    curva = {"cache": [], "git": [], "otros": []}
    for a in alphas:
        q = En[qs] + a * v_cache_git; q /= np.linalg.norm(q, axis=1, keepdims=True)
        sc = q @ En.T; sc[np.arange(len(qs)), qs] = -9; top = np.argsort(-sc, axis=1)[:, :10]
        fc, fg = float((topic[top] == "cache").mean()), float((topic[top] == "git").mean()); curva["cache"].append(fc); curva["git"].append(fg); curva["otros"].append(1 - fc - fg)
    fig, ax = plt.subplots(figsize=(7, 3.6))
    for k, c in (("cache", AZUL), ("git", NARANJA), ("otros", GRIS)): ax.plot(alphas, curva[k], "o-", color=c, label=f"% de resultados de «{k}»")
    ax.set_xlabel("intensidad del steering α  (q' = q + α·v_{cache→git})"); ax.set_ylabel("fracción del top-10"); ax.legend(frameon=False); ax.set_title("Mover la consulta en la dirección «git − cache» cambia los resultados"); plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** La transición es **suave y casi monótona**: con α≈0.5 todavía domina «cache», hacia α≈1 hay mezcla y con α ≥ 1.5 todo el top-10 es «git». Una dirección calculada con *medias* (sin entrenamiento) basta para controlar el tema del retrieval en este juguete.
    > 🟡 En embedders reales funciona de forma menos limpia (conceptos entrelazados, direcciones que cambian de capa a capa, normas); además *AxBench* (Wu et al., 2025) encontró que, para steering de LLMs, **líneas base simples** (prompting, diferencia de medias) **superan a los SAE**. Por eso conviene comparar siempre contra la diferencia de medias antes de afirmar que una *feature* aprendida «controla» algo.
    """)
    nb.gemini(
        "video", "M17-VID-1", "Steering: sumar un vector de concepto desplaza la consulta y sus resultados",
        "Animación en 2D de una consulta que se desplaza por el vector «git − cache» y pasa del clúster de documentos de caché al de git, con el top-3 cambiando.",
        """
        Animación técnica limpia, 16:9, fondo blanco, paleta sobria (azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280), tipografía sans-serif, ritmo calmado, sin voz en off, sin música. Textos en español.
        Escenas:
        0–6 s: un plano 2D sin ejes numéricos con dos nubes de puntos: una azul etiquetada «documentos de caché» (izquierda) y una naranja etiquetada «documentos de git» (derecha), y una estrella negra «consulta q» dentro de la nube azul. Un panel a la derecha lista «Top-3: cache, cache, cache» con barras azules.
        6–12 s: aparecen los centroides de cada nube como puntos grandes y una flecha gris gruesa del centroide azul al naranja con la etiqueta «v = media(git) − media(cache)».
        12–22 s: la estrella se desplaza gradualmente a lo largo de una flecha verde paralela a v; sobre ella un contador «α = 0 → 0.5 → 1 → 1.5». Los tres vecinos más cercanos se resaltan con líneas finas y el panel de la derecha cambia: «cache, cache, git» (α = 1), luego «git, git, git» (α = 1.5), con barras que pasan de azul a naranja.
        22–28 s: la estrella queda dentro de la nube naranja; texto final «Una dirección de concepto controla el retrieval (¡mídelo y compáralo con baselines!)».
        Evita: voz en off, música, texto ilegible, números inventados, efectos 3D, transiciones bruscas.
        """,
        "Una consulta se desplaza por la dirección que va de la nube de caché a la de git y su top-3 cambia de caché a git.",
        """
        [nube cache]  q ★ ------ α·v ------> ★ [nube git]
        top-3: cache cache cache  ->  cache cache git  ->  git git git
        """,
        duration="28 s",
    )
    nb.code(r'''
    # Borrado lineal de un concepto (idioma) con la dirección de diferencia de medias: la versión más simple de LEACE (Belrose et al. 2023)
    u = En[lang == "en"].mean(0) - En[lang == "es"].mean(0); u /= np.linalg.norm(u)
    Ep = En - np.outer(En @ u, u); Epn = Ep / np.linalg.norm(Ep, axis=1, keepdims=True); y_en = (lang == "en").astype(int)
    acc_antes, acc_despues = sonda(En, y_en), sonda(Ep, y_en)
    def stats_retrieval(M):
        qi = np.where(lang == "es")[0][:200]; sc = M[qi] @ M.T; sc[np.arange(len(qi)), qi] = -9; top = np.argsort(-sc, axis=1)[:, :10]
        return float((lang[top] == "es").mean()), float((facet[top] == facet[qi][:, None]).mean())
    mis_l0, mis_f0 = stats_retrieval(En); mis_l1, mis_f1 = stats_retrieval(Epn)
    fig, ax = plt.subplots(1, 2, figsize=(10.5, 3.4))
    ax[0].bar(["antes", "tras borrar la dirección"], [acc_antes, acc_despues], color=[AZUL, VERDE]); ax[0].axhline(.5, color=GRIS, ls="--"); ax[0].set_ylim(0, 1.05); ax[0].set_title("Sonda lineal de IDIOMA"); ax[0].set_ylabel("precisión")
    w = .38; ax[1].bar(np.arange(2) - w/2, [mis_l0, mis_f0], w, color=AZUL, label="antes"); ax[1].bar(np.arange(2) + w/2, [mis_l1, mis_f1], w, color=VERDE, label="tras borrar")
    ax[1].set_xticks(range(2)); ax[1].set_xticklabels(["top-10 en el mismo idioma", "top-10 de la misma faceta"]); ax[1].legend(frameon=False); ax[1].set_ylim(0, 1.05); ax[1].set_title("Efecto en el retrieval (consultas ES)")
    plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** Tras proyectar fuera una sola dirección, la sonda lineal de idioma cae al **azar** (≈ 0.5): la información ya no es *linealmente* legible. Pero el **retrieval no cambia**: sigue devolviendo documentos del mismo idioma. Lección de interpretabilidad: **borrar lo que un probe lee no cambia necesariamente lo que el sistema hace** (la información de idioma está también en *qué palabras* aparecen, redundante en muchas dimensiones). Para borrado óptimo se usa **LEACE** (Belrose et al., 2023, borrado lineal en forma cerrada); sigue habiendo información no lineal.
    """)

    # ───────── 5. Dimensiones dominantes ─────────
    nb.md("""
    ## 5. Dimensiones dominantes, outliers y anisotropía
    **Timkey & van Schijndel (EMNLP 2021):** en BERT y GPT-2, las similitudes (coseno, euclídea) están dominadas por **1–3 «rogue dimensions»** de varianza enorme, que además no coinciden con las que importan para el comportamiento; estandarizar las dimensiones revela la calidad real de la representación. **Kovaleva et al. (2021)** encuentran *outlier dimensions* (escalas y sesgos de LayerNorm de gran magnitud) y muestran que desactivarlas degrada mucho el modelo: **son «importantes» para el modelo pero distorsionan la similitud**. Ethayarajh (2019) documenta la anisotropía de las representaciones contextuales.
    Nuestro LSI **no tiene** esas dimensiones (no es un transformer); **simulamos** una (inyectamos una dimensión con desviación ≈ 100× la típica) para ver el mecanismo; con un embedder real, `diagnostico_dimensiones(E)` te dirá si las tienes.
    """)
    nb.code(r'''
    def con_dim_rogue(E, escala=100.0, seed=0):
        r = np.random.default_rng(seed); out = E.copy(); out[:, 3] = E[:, 3] * 1.0 + escala * E.std() * (1.0 + 0.3 * r.standard_normal(len(E))); return out
    E_rogue = con_dim_rogue(E)
    def prec_facet(M, n_q=300):
        M = M / np.linalg.norm(M, axis=1, keepdims=True); qi = np.random.default_rng(1).choice(len(M), n_q, replace=False); sc = M[qi] @ M.T; sc[np.arange(n_q), qi] = -9
        return float((facet[np.argsort(-sc, axis=1)[:, :10]] == facet[qi][:, None]).mean())
    Z_std = (E_rogue - E_rogue.mean(0)) / (E_rogue.std(0) + 1e-12)
    res = {"LSI limpio": diagnostico_dimensiones(E), "con dimensión rogue (simulada)": diagnostico_dimensiones(E_rogue)}
    res["LSI limpio"]["precisión@10 de faceta"] = prec_facet(E); res["con dimensión rogue (simulada)"]["precisión@10 de faceta"] = prec_facet(E_rogue)
    def falsos_umbral(M, u=0.5):
        M = M / np.linalg.norm(M, axis=1, keepdims=True); a, b = np.random.default_rng(3).integers(0, len(M), (2, 20000)); m = (a != b) & (facet[a] != facet[b]); return float((np.sum(M[a] * M[b], 1)[m] > u).mean())
    res["LSI limpio"]["pares NO relacionados con coseno > 0.5"] = falsos_umbral(E); res["con dimensión rogue (simulada)"]["pares NO relacionados con coseno > 0.5"] = falsos_umbral(E_rogue)
    d_rogue = pd.DataFrame(res).T; d_rogue["tras estandarizar: precisión@10"] = [prec_facet((E - E.mean(0)) / (E.std(0) + 1e-12)), prec_facet(Z_std)]; display(d_rogue.round(3))
    fig, ax = plt.subplots(1, 3, figsize=(14, 3.5)); v = np.sort(E_rogue.var(0))[::-1]; ax[0].bar(range(len(v)), v, color=AZUL); ax[0].set_title("Varianza por dimensión (con rogue)"); ax[0].set_xlabel("dimensiones ordenadas"); ax[0].set_ylabel("varianza")
    ax[1].bar(["limpio", "rogue", "rogue\nestandarizado"], [d_rogue.loc["LSI limpio", "coseno_medio"], d_rogue.loc["con dimensión rogue (simulada)", "coseno_medio"], d_rogue.loc["con dimensión rogue (simulada)", "coseno_medio_estandarizado"]], color=[VERDE, ROJO, AZUL]); ax[1].set_title("Coseno medio entre textos al azar"); ax[1].set_ylabel("coseno medio")
    ax[2].bar(["limpio", "rogue"], [d_rogue.loc["LSI limpio", "pares NO relacionados con coseno > 0.5"], d_rogue.loc["con dimensión rogue (simulada)", "pares NO relacionados con coseno > 0.5"]], color=[VERDE, ROJO]); ax[2].set_title("Pares no relacionados que pasan un umbral de coseno 0.5"); ax[2].set_ylim(0, 1.05)
    plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** Con **una sola** dimensión dominante: (1) concentra ≈ 94 % de la varianza; (2) el **coseno medio entre textos al azar se dispara** (≈ 1: anisotropía extrema); (3) **casi todos los pares no relacionados superan un umbral de coseno 0.5**: cualquier regla del tipo «considerar duplicado/relevante si coseno > u», filtros de similitud, *clustering* o diversificación (MMR) **se rompe**; (4) sin embargo la **precisión@10 del ranking apenas cambia** en este juguete (ver columna `precisión@10 de faceta`): el ranking depende de diferencias *relativas*, no del nivel absoluto del coseno. **Estandarizar** cada dimensión devuelve el coseno medio a ≈ 0. Es el diagnóstico y remedio de Timkey & van Schijndel (ellos reportan efectos en medidas de similitud y en la calidad aparente de la representación).
    > Nota de honestidad: la dimensión es **simulada** (no es una medición de ningún modelo real). Ejecuta `diagnostico_dimensiones` sobre tu embedder real: si `var_top1` es grande o el coseno medio entre textos no relacionados es alto, aplica *whitening* o estandarización (con un sistema de producción, **valida el efecto en nDCG**, módulo 15).
    """)
    nb.md("""
    ### 5b. 🧪 Hubness: el documento que aparece en todas las búsquedas
    Otra patología geométrica con consecuencias directas en retrieval: en alta dimensión, unos pocos puntos (**hubs**) aparecen entre los $k$ vecinos más cercanos de muchísimos otros, y muchos puntos (**anti-hubs**) no aparecen en ninguno (Radovanović, Nanopoulos & Ivanović, JMLR 2010, *Hubs in Space*: la asimetría de la distribución de la *k-ocurrencia* $N_k$ crece con la dimensión intrínseca). En un buscador, un hub es «el documento que sale para todo» y un anti-hub, un documento que nadie encuentra. Remedios clásicos: **centrar** (restar la media: la misma anisotropía de §5 empeora la hubness) y **CSLS** (Conneau et al., ICLR 2018), que penaliza a cada documento por su similitud media con sus $k$ vecinos: $\\mathrm{CSLS}(q,d)=2\\cos(q,d)-r(q)-r(d)$; para ordenar los documentos de una query fija solo importa $-r(d)$.
    Primero el mecanismo con datos controlados (gaussianas con una dirección común, como un embedding anisótropo, a varias dimensiones) y después la medición en nuestros embeddings LSI. $N_{10}$ se mide con los documentos como queries, lo estándar en esta literatura.
    """)
    nb.code(r'''
    from scipy.stats import skew
    def k_ocurrencia(M, k=10, csls=False):
        """N_k de cada punto (en cuántas listas top-k de los demás aparece) y las listas; coseno, sin el propio punto."""
        M = M / np.linalg.norm(M, axis=1, keepdims=True); S = M @ M.T; np.fill_diagonal(S, -9)
        if csls:
            r = np.sort(S, axis=1)[:, -k:].mean(1); S = S - r[None, :]          # penaliza documentos «populares»
        top = np.argpartition(-S, k, axis=1)[:, :k]
        return np.bincount(top.ravel(), minlength=len(M)), top
    def resumen_hub(Nk):
        return {"asimetría N10": skew(Nk), "máx N10": int(Nk.max()), "% anti-hubs (N10 = 0)": 100 * (Nk == 0).mean()}
    rng_h = np.random.default_rng(SEED); filas_h, Nk_d100 = [], {}
    for d in (20, 100, 500):
        G = rng_h.standard_normal((2000, d)) + 1.0                                  # nube con una dirección común (anisótropa)
        for nombre, M, cs in (("coseno crudo", G, False), ("centrado", G - G.mean(0), False), ("CSLS", G, True)):
            Nk, _ = k_ocurrencia(M, csls=cs); filas_h.append({"d": d, "variante": nombre, **resumen_hub(Nk)})
            if d == 100: Nk_d100[nombre] = Nk
    d_hub = pd.DataFrame(filas_h).set_index(["d", "variante"]); display(d_hub.round(2))
    Nk_lsi, top_lsi = k_ocurrencia(E)
    print("Políglota, LSI-64:", {k: round(float(v), 2) for k, v in resumen_hub(Nk_lsi).items()}, f"· precisión@10 de faceta = {(facet[top_lsi] == facet[:, None]).mean():.3f}")
    fig, ax = plt.subplots(figsize=(8, 3.6))
    for (nombre, Nk), c in zip(Nk_d100.items(), [ROJO, VERDE, NARANJA]):
        ax.hist(Nk, bins=np.arange(0, Nk_d100["coseno crudo"].max() + 5, 4), histtype="step", lw=2, color=c, label=f"d = 100 · {nombre}")
    ax.hist(Nk_lsi, bins=np.arange(0, Nk_d100["coseno crudo"].max() + 5, 4), histtype="step", lw=2, ls="--", color=AZUL, label="Políglota LSI-64")
    ax.set_yscale("log"); ax.set_xlabel("$N_{10}$: en cuántas listas top-10 aparece cada punto"); ax.set_ylabel("nº de puntos (log)")
    ax.set_title("Distribución de la k-ocurrencia (hubness)"); ax.legend(fontsize=8); plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** La media de $N_{10}$ es siempre 10 (cada lista tiene 10 huecos); lo que cambia es la **cola**. Con una dirección común, la asimetría crece con la dimensión (en la ejecución de referencia ≈ 1.5 a d = 20 y ≈ 4.7–5.5 a d = 100–500, con un punto que aparece en 250–317 de las 2000 listas y un 13–19 % de anti-hubs); **centrar** la elimina casi por completo (asimetría 0.1–0.4) y **CSLS** la reduce sin tocar los vectores. En Políglota con LSI la hubness es baja (asimetría ≈ 0.4, sin anti-hubs relevantes): LSI sale casi centrado y los documentos forman clusters compactos por faceta. Un embedder Transformer real es anisótropo (§5), así que **mídelo**: en producción es una señal sin etiquetas barata (la concentración del top-1 sobre el tráfico, módulo 18 §9, y la lista de documentos que nunca aparecen en ningún top-k) antes de que un usuario se queje de que «siempre sale el mismo».
    """)
