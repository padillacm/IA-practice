"""Lección 16 · parte 1: cabecera, CLIP/SigLIP en miniatura, modality gap."""
from _a6_src16 import SHAPES_SRC, CLIP_SRC, PAGES_SRC


def part1(nb):
    nb.md(f"""
    {nb.badge()}

    # Módulo 16 · Embeddings multimodales

    | | |
    |---|---|
    | **Nivel** | 🟠 Avanzado |
    | **Duración** | ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) |
    | **GPU** | L4 recomendada **solo** para las celdas opcionales con modelos reales (ColPali, CLIP/SigLIP); T4 vale con modelos pequeños. Todo lo demás corre en CPU con `FAST_DEV_RUN=True` (≈ 0 unidades de Colab; ≈ 5–8 min de CPU) |
    | **Prerrequisitos** | 08 (tokens multimodales: patches ViT), 11 (InfoNCE), 13 (late interaction / MaxSim), 15 (evaluación) |
    | **Hilo conductor** | Políglota Labs quiere que el buscador encuentre también **PDFs, capturas y diagramas** de la documentación |

    > 🧭 **Ruta núcleo vs ampliación.** Núcleo (≈ 3 h, lo que usa el proyecto): secciones 1–6 (CLIP, SigLIP, modality gap, retrieval visual de documentos y ColPali en miniatura). Ampliación (≈ 2 h): 7–9 (embeddings unificados, audio y video, árbol de decisión OCR vs visual).
    > Las celdas con modelos reales están marcadas **(opcional, no probada en CPU)** y protegidas con flags.
    """)
    nb.md("""
    ## 🎯 Objetivos de aprendizaje
    1. **Implementar** desde cero un modelo de dos torres con pérdida InfoNCE simétrica (CLIP) y con pérdida sigmoide (SigLIP) y **comparar** su comportamiento.
    2. **Medir** el *modality gap* (distancia entre centroides), su dependencia de la temperatura y sus efectos en un índice de modalidades mezcladas; **aplicar** una corrección simple.
    3. **Explicar y programar** MaxSim (late interaction) sobre *patch embeddings* de una página, y **diagnosticar** por qué un único vector medio falla.
    4. **Comparar** un pipeline OCR + texto con un embedding visual según el tipo de consulta y el nivel de ruido, y **estimar** el coste de almacenamiento multi-vector.
    5. **Situar** los embeddings unificados (Gemini Embedding 2, Jina v4, VLM2Vec) con sus capacidades **verificadas y fechadas**.
    6. **Razonar** sobre audio y video en espacios de embedding y sobre qué se pierde al promediar frames.
    7. **Decidir** cuándo usar OCR+texto, embedding visual o ambos.
    """)
    nb.md("""
    ## 🔁 Conexión con módulos anteriores
    <details><summary><b>1.</b> (Módulo 08) Una imagen entra a un ViT como patches. Si la página tiene 448×448 px y los patches son de 14×14, ¿cuántos patches hay?</summary>

    $(448/14)^2 = 32^2 = 1024$ patches. Es justo el orden de magnitud que usa ColPali (1024 patches por página con el codificador de visión de PaliGemma): **cada patch pasa a ser un vector**.
    </details>

    <details><summary><b>2.</b> (Módulo 11) Escribe la InfoNCE para un batch de $N$ pares y di qué son los negativos.</summary>

    $\\mathcal L=-\\frac1N\\sum_i\\log\\frac{e^{s_{ii}/\\tau}}{\\sum_j e^{s_{ij}/\\tau}}$: los negativos son los otros $N-1$ elementos del batch (*in-batch negatives*). En CLIP se aplica en ambas direcciones (imagen→texto y texto→imagen).
    </details>

    <details><summary><b>3.</b> (Módulo 13) ¿Qué calcula MaxSim de ColBERT?</summary>

    Para cada token de la query toma la **máxima** similitud con cualquier token del documento y suma: $\\sum_i\\max_j\\langle q_i,d_j\\rangle$. Aquí los «tokens del documento» serán los patches de la página.
    </details>

    <details><summary><b>4.</b> (Módulo 15) ¿Cómo comparas dos sistemas de retrieval con pocas queries?</summary>

    Métricas por query + bootstrap/test pareado con IC (nunca dos medias sueltas). Lo usaremos en el proyecto con `poliglota_eval.py`.
    </details>

    <details><summary><b>5.</b> (Módulo 01, Diagnóstico) El OCR de un PDF devuelve «conﬁguración» con la ligadura «ﬁ» (U+FB01). ¿Qué le pasa a BM25 con la query «configuración» y qué normalización lo arregla?</summary>

    No hay coincidencia: «ﬁ» es un solo code point distinto de «f» + «i», así que el término del documento es otro. **NFKC** descompone la ligadura de compatibilidad (módulo 01). Es una de las razones por las que la ruta «OCR + texto» (sección 6) necesita el mismo normalizador en indexación y consulta, y una ventaja de la ruta visual, que no pasa por el texto.
    </details>
    """)

    nb.md("""
    ## 1. Intuición: dos torres, un espacio

    Un **embedding multimodal** coloca contenidos de distinto tipo (una foto y su descripción) **cerca** en el mismo espacio vectorial, de modo que se pueda buscar «foto de un círculo rojo» y obtener la imagen. Es la misma idea que el *two-tower* de recomendación (usuario ↔ ítem) que viste en `recsys-course`: dos codificadores, un producto escalar, y entrenamiento con negativos del batch.

    ```
    imagen ──► [torre de imagen] ──► z_i ─┐
                                          ├─ coseno ──► InfoNCE (diagonal = pares correctos)
    texto  ──► [torre de texto ] ──► z_t ─┘
    ```
    Para poder **medir** todo en CPU y en minutos construiremos un CLIP en miniatura con figuras de colores y captions en **español e inglés** (la imagen hace de «pivote» entre los dos idiomas). Después subiremos de escala con modelos reales (celdas opcionales).
    """)
    nb.gemini(
        "imagen", "M16-IMG-1", "CLIP y SigLIP: dos torres y la matriz de similitudes",
        "Arquitectura de dos torres (imagen y texto), la matriz N×N de similitudes y la diferencia entre InfoNCE (softmax por fila y columna) y SigLIP (sigmoide por celda).",
        """
        Diagrama técnico limpio, fondo blanco, paleta sobria (azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280), tipografía sans-serif legible, flechas claras, sin ilustraciones decorativas. 16:9.
        Composición con tres zonas de izquierda a derecha.
        Zona izquierda: dos columnas verticales de bloques. Arriba una caja azul «Torre de imagen (ViT / CNN)» con una miniatura abstracta de un círculo rojo a su izquierda; abajo una caja naranja «Torre de texto (Transformer)» con el texto «un círculo rojo» a su izquierda. De cada torre sale una flecha hacia un vector etiquetado «z_i» (azul) y «z_t» (naranja), ambos con la etiqueta «L2-normalizado».
        Zona central: una cuadrícula 4×4 con filas etiquetadas «imagen 1…4» y columnas «texto 1…4»; la diagonal en verde con «s_ii (par correcto)» y el resto en gris claro con «s_ij (negativos)». Título: «Matriz de similitudes N×N».
        Zona derecha: dos recuadros apilados. Recuadro superior (azul) «CLIP · InfoNCE»: texto «softmax sobre cada fila y cada columna» y la fórmula «L = −log( exp(s_ii/τ) / Σ_j exp(s_ij/τ) )». Recuadro inferior (verde) «SigLIP · sigmoide»: texto «cada celda es una clasificación binaria independiente (+1 diagonal, −1 fuera)» y la fórmula «L = −Σ_ij log σ( z_ij · (t·s_ij + b) )».
        Título superior: «Dos torres, un espacio de embeddings».
        Evita: texto ilegible o inventado, fotografías realistas, sombras 3D, elementos decorativos, flechas ambiguas.
        """,
        "Dos torres (imagen y texto) producen vectores normalizados cuya matriz de similitudes se entrena con InfoNCE (softmax) o con la pérdida sigmoide de SigLIP.",
        """
        imagen -> [torre imagen] -> z_i --\\
                                          >-- S = z_i z_t^T (N x N) -- CLIP: softmax fila/col ; SigLIP: sigmoide por celda
        texto  -> [torre texto ] -> z_t --/       diagonal = pares correctos
        """,
    )
    nb.md("""
    > 👀 **Qué debes observar.** En CLIP los negativos compiten entre sí (softmax): el valor de cada celda depende del resto del batch. En SigLIP cada celda es independiente (sigmoide), por lo que **no hace falta normalizar sobre todo el batch** y se simplifica el entrenamiento distribuido (Zhai et al., 2023).
    """)

    nb.md("## 2. Entorno y datos de juguete")
    nb.code("!pip install -q numpy scikit-learn matplotlib pandas torch pillow transformers datasets")
    nb.code(r'''
    import os, math, random, time, warnings
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
    nb.code(SHAPES_SRC)
    nb.code(r'''
    Xtr, Ttr, Ytr, Ltr = make_dataset(80, seed=1); Xte, Tte, Yte, Lte = make_dataset(20, seed=2)
    vocab = sorted({w for t in Ttr + Tte for w in t}); w2i = {w: i + 1 for i, w in enumerate(vocab)}
    print(f"{len(Xtr)} imágenes de entrenamiento · {len(Xte)} de test · vocabulario de captions: {len(vocab)} palabras (ES+EN)")
    fig, ax = plt.subplots(2, 6, figsize=(12, 4.4))
    for a, k in zip(ax.ravel(), np.random.default_rng(0).choice(len(Xte), 12, replace=False)):
        a.imshow(Xte[k]); a.set_title(" ".join(Tte[k])[:26], fontsize=8); a.axis("off")
    fig.suptitle("Dataset de juguete: 16 conceptos (forma × color), captions en ES o EN", y=1.02); plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** Cada imagen tiene una sola caption, **en español o en inglés al azar**. El modelo nunca ve «un círculo rojo» y «a red circle» juntos: solo se conectarán a través de la **imagen** que ambos describen (pivote visual).
    > Con 16 conceptos y batches de 128 habrá muchos *falsos negativos* en el batch (otra imagen del mismo concepto): el suelo teórico de la pérdida no es 0 (≈ $\\ln(128/16)\\approx2.1$).
    """)
    nb.md("""
    ## 3. CLIP en miniatura desde cero
    **Pérdida (InfoNCE simétrica).** Con $z_i,z_t$ normalizados y escala $1/\\tau$:
    $$\\mathcal L=\\tfrac12\\Big[\\mathrm{CE}\\big(\\tfrac{1}{\\tau}Z_iZ_t^\\top,\\ \\mathrm{diag}\\big)+\\mathrm{CE}\\big(\\tfrac{1}{\\tau}Z_tZ_i^\\top,\\ \\mathrm{diag}\\big)\\Big]$$
    $\\tau$ es la **temperatura**: pequeña ⇒ distribución muy picuda (castiga mucho al negativo más cercano); grande ⇒ casi uniforme. En CLIP se **aprende** (inicializada en 0.07).

    **SigLIP.** Sustituye el softmax por una sigmoide por par, con escala $t$ y sesgo $b$ aprendibles (el paper inicializa $t'=\\log 10$, $b=-10$):
    $$\\mathcal L=-\\frac1N\\sum_{i}\\sum_{j}\\log\\sigma\\big(y_{ij}\\,(t\\,z_i\\!\\cdot\\! z_j+b)\\big),\\quad y_{ij}=\\begin{cases}+1&i=j\\\\-1&i\\ne j\\end{cases}$$
    El sesgo $b\\approx-10$ compensa que hay $N^2-N$ negativos frente a $N$ positivos desde el primer paso.
    """)
    nb.code(CLIP_SRC)
    nb.code(r'''
    CONFIGS = [("infonce", None, "InfoNCE τ aprendida"), ("infonce", 0.01, "InfoNCE τ=0.01"), ("infonce", 0.05, "InfoNCE τ=0.05"),
               ("infonce", 0.2, "InfoNCE τ=0.2"), ("infonce", 1.0, "InfoNCE τ=1.0"), ("sigmoid", None, "SigLIP (sigmoide)")]
    EPOCHS = 60 if FAST_DEV_RUN else 120
    MODELOS, t0 = {}, time.time()
    for tipo, tau, nombre in CONFIGS:
        I, Tx, hist = entrena_clip(Xtr, Ttr, w2i, tipo=tipo, tau=tau, epochs=EPOCHS)
        zi, zt = embebe(I, Tx, Xte, Tte, w2i); MODELOS[nombre] = dict(I=I, Tx=Tx, hist=hist, zi=zi, zt=zt, **metricas_clip(zi, zt, Yte))
        print(f"{nombre:22s} acc i→t={MODELOS[nombre]['acc_i2t']:.2f}  acc t→i={MODELOS[nombre]['acc_t2i']:.2f}  gap={MODELOS[nombre]['gap']:.3f}  ({time.time()-t0:.0f}s)")
    ''')
    nb.code(r'''
    fig, ax = plt.subplots(1, 3, figsize=(14, 3.8)); nombres = list(MODELOS)
    for n in nombres: ax[0].plot(MODELOS[n]["hist"], label=n)
    ax[0].set_xlabel("época"); ax[0].set_ylabel("pérdida (último batch)"); ax[0].set_title("Curvas de entrenamiento"); ax[0].legend(frameon=False, fontsize=7)
    ax[1].bar(range(len(nombres)), [MODELOS[n]["acc_i2t"] for n in nombres], color=[AZUL] * 5 + [VERDE]); ax[1].set_xticks(range(len(nombres))); ax[1].set_xticklabels(nombres, rotation=30, ha="right", fontsize=7)
    ax[1].set_ylabel("precisión imagen → concepto"); ax[1].set_title("Calidad del retrieval cruzado")
    ax[2].bar(range(len(nombres)), [MODELOS[n]["gap"] for n in nombres], color=[NARANJA] * 5 + [VERDE]); ax[2].set_xticks(range(len(nombres))); ax[2].set_xticklabels(nombres, rotation=30, ha="right", fontsize=7)
    ax[2].set_ylabel("modality gap (distancia entre centroides)"); ax[2].set_title("Modality gap por configuración")
    plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** (1) La calidad se degrada si $\\tau$ es demasiado grande (1.0): la señal contrastiva se diluye. (2) El **gap cae de forma monótona al subir $\\tau$**, y solo ahí podría «cerrarse» a costa de calidad: no es gratis. (3) SigLIP aprende también, con un gap intermedio.
    > Los números exactos dependen de semilla y épocas; lo robusto es la **tendencia**. Nota: en la sección siguiente se compara contra el gap del modelo *sin entrenar*.
    """)
    nb.md("""
    ## 4. SigLIP 2 y el panorama de modelos reales
    **SigLIP 2** (Tschannen et al., 2025) mantiene el objetivo image-text de SigLIP y añade pretraining con *captioning*, pérdidas auto-supervisadas (auto-distilación y *masked prediction*), curación de datos online, una mezcla multilingüe menos sesgada y variantes con distintas resoluciones y relación de aspecto nativa.
    En producción conviene probar **ambos**: SigLIP/SigLIP 2 suelen ser mejores en zero-shot que CLIP del mismo tamaño en los benchmarks de sus papers, pero la ganancia en *tu* dominio se mide, no se supone (módulo 15).

    **(opcional, no probada en CPU)** Con red y GPU puedes repetir la medición del gap con modelos reales sobre nuestras figuras: pon `USE_REAL_MODELS = True`.
    """)
    nb.code(r'''
    USE_REAL_MODELS = False     # True en Colab con GPU/red (descarga ~0.6-1.5 GB). Probado solo en CPU con el juguete; esta celda NO se ejecutó en el entorno de desarrollo.
    if USE_REAL_MODELS:
        from transformers import AutoModel, AutoProcessor
        from PIL import Image
        for nombre in ("openai/clip-vit-base-patch32", "google/siglip-base-patch16-224"):
            try:
                m = AutoModel.from_pretrained(nombre).to(device).eval(); pr = AutoProcessor.from_pretrained(nombre)
                imgs = [Image.fromarray((x * 255).astype("uint8")).resize((224, 224)) for x in Xte[:64]]; txt = [" ".join(t) for t in Tte[:64]]
                with torch.no_grad():
                    ei = m.get_image_features(**pr(images=imgs, return_tensors="pt").to(device)); et = m.get_text_features(**pr(text=txt, padding="max_length", return_tensors="pt").to(device))
                ei, et = torch.nn.functional.normalize(ei, dim=-1).cpu(), torch.nn.functional.normalize(et, dim=-1).cpu()
                print(nombre, "modality gap =", round(modality_gap(ei, et), 3))
            except Exception as e:
                print(nombre, "no disponible:", type(e).__name__, str(e)[:80])
    else:
        print("USE_REAL_MODELS=False: celda omitida.")
    ''')

    # ───────── 5. Modality gap ─────────
    nb.md("""
    ## 5. El modality gap, medido
    **Liang et al. (NeurIPS 2022)** observaron que en CLIP y otros modelos multimodales las imágenes y los textos ocupan **regiones separadas** de la hiperesfera (a «un brazo de distancia»). Dos causas:
    1. **Efecto cono** *(inicialización)*: las representaciones de una red profunda ocupan un cono estrecho; con dos redes distintas, **dos conos distintos** desde el paso 0.
    2. **Aprendizaje contrastivo**: con temperatura baja la optimización *conserva* esa separación; la temperatura modifica su tamaño.

    **Cómo se mide:** $\\text{gap}=\\lVert\\bar z_i-\\bar z_t\\rVert_2$ con $\\bar z$ el centroide de cada modalidad (embeddings normalizados). Medimos primero el modelo **sin entrenar** y comparamos.

    ✍️ **Ejemplo a mano (2D).** Imágenes $(1, 0)$ y $(0.8, 0.6)$, centroide $(0.9, 0.3)$; textos $(0, 1)$ y $(0.6, 0.8)$, centroide $(0.3, 0.9)$. gap $= \\lVert(0.6, -0.6)\\rVert = 0.85$. En un índice mixto, la query de texto $(0, 1)$ da coseno 0.8 con el texto $(0.6, 0.8)$ y solo 0.6 con la imagen $(0.8, 0.6)$, aunque describan lo mismo: **los documentos de la misma modalidad que la query ganan por geometría**, no por relevancia. Restar a cada vector el centroide de su modalidad (y renormalizar) es la corrección simple que probaremos; es el mismo centrado por grupo que el centrado por idioma del módulo 10.
    """)
    nb.code(r'''
    torch.manual_seed(0); I0, T0 = TorreImagen(), TorreTexto(len(w2i)); zi0, zt0 = embebe(I0, T0, Xte, Tte, w2i)
    coseno_intra = lambda z: float((z @ z.T).mean())
    filas = [{"modelo": "sin entrenar", "gap": modality_gap(zi0, zt0), "coseno medio intra-imagen": coseno_intra(zi0), "coseno medio intra-texto": coseno_intra(zt0)}]
    for n in ("InfoNCE τ=0.01", "InfoNCE τ aprendida", "InfoNCE τ=0.2"):
        filas.append({"modelo": n, "gap": MODELOS[n]["gap"], "coseno medio intra-imagen": coseno_intra(MODELOS[n]["zi"]), "coseno medio intra-texto": coseno_intra(MODELOS[n]["zt"])})
    pd.DataFrame(filas).set_index("modelo").round(3)
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** Sin entrenar, las imágenes están **casi todas en el mismo punto** (coseno medio intra-imagen ≈ 1: efecto cono extremo) y a distancia grande de los textos. El entrenamiento reparte cada modalidad por la esfera (coseno intra baja) pero **el gap no desaparece** salvo con temperaturas altas.
    """)
    nb.code(r'''
    def pca2(Z, ref):
        c = ref.mean(0); _, _, Vt = np.linalg.svd((ref - c).numpy(), full_matrices=False); return (Z - c).numpy() @ Vt[:2].T
    escenas = [("sin entrenar", zi0, zt0), ("InfoNCE τ=0.01", MODELOS["InfoNCE τ=0.01"]["zi"], MODELOS["InfoNCE τ=0.01"]["zt"]), ("InfoNCE τ=0.2", MODELOS["InfoNCE τ=0.2"]["zi"], MODELOS["InfoNCE τ=0.2"]["zt"])]
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.8))
    for a, (n, zi, zt) in zip(ax, escenas):
        ref = torch.cat([zi, zt]); pi, pt = pca2(zi, ref), pca2(zt, ref)
        a.scatter(*pi.T, s=8, color=AZUL, alpha=.6, label="imágenes"); a.scatter(*pt.T, s=8, color=NARANJA, alpha=.6, label="textos")
        a.set_title(f"{n} · gap={modality_gap(zi, zt):.2f}", fontsize=10); a.set_xlabel("PC1"); a.set_ylabel("PC2"); a.legend(frameon=False, fontsize=8)
    plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** En el primer panel hay **dos nubes totalmente separadas** (los dos conos). Con $\\tau=0.01$ siguen separadas (gap grande); con $\\tau=0.2$ se solapan. Es la figura clásica de Liang et al. reproducida con tu propio modelo.
    """)
    nb.gemini(
        "imagen", "M16-IMG-2", "El modality gap y el efecto cono",
        "Dos conos estrechos en la hiperesfera (imágenes y textos) separados por el vector del gap; consecuencia: en un índice mixto un texto tiene más cerca otros textos que su imagen correcta.",
        """
        Diagrama técnico limpio, fondo blanco, paleta sobria (azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280), tipografía sans-serif legible, flechas claras, sin ilustraciones decorativas. 16:9.
        Composición con dos paneles.
        Panel izquierdo, título «Efecto cono: dos redes, dos conos»: una esfera dibujada como círculo gris con dos zonas en forma de cono estrecho: una azul etiquetada «imágenes» (arriba a la izquierda) y una naranja etiquetada «textos» (abajo a la derecha). Entre los centroides (puntos grandes) una flecha negra etiquetada «vector del gap  Δ = z̄_img − z̄_txt» y la medida «gap = ‖Δ‖».
        Panel derecho, título «Consecuencia en un índice mixto»: la misma disposición, con una consulta de texto «un círculo rojo» (estrella naranja) dentro del cono naranja; tres puntos naranjas vecinos (otros textos) a distancia corta etiquetados «textos más cercanos», y un punto azul (la imagen correcta) a distancia mayor etiquetado «su imagen (más lejos)». Debajo, el texto: «Con gap grande, el top-k mezcla poco las modalidades».
        Abajo un recuadro verde: «Mitigación simple: restar el centroide de cada modalidad y renormalizar».
        Evita: texto ilegible o inventado, ilustraciones decorativas, sombras 3D, más de dos conos, flechas ambiguas.
        """,
        "Dos conos en la hiperesfera (imágenes y textos) separados por el vector del gap y su efecto en un índice mixto.",
        """
         (imágenes)  ●─────── Δ (gap) ───────►  ●  (textos)
         una consulta de texto ★ tiene más cerca otros textos que su imagen correcta
         mitigación: restar el centroide de cada modalidad y renormalizar
        """,
    )
    nb.md("""
    > 👀 **Qué debes observar.** El gap **no importa** si solo comparas texto→imágenes (ranking dentro de una modalidad). Importa cuando **mezclas modalidades en el mismo índice** o comparas puntuaciones entre modalidades: el vecino más cercano de un texto tiende a ser otro texto. Lo medimos a continuación con la «tasa de intrusos».
    """)
    nb.code(r'''
    def centra(z, mu): return torch.nn.functional.normalize(z - mu, dim=-1)

    def tasa_intruso(zi, zt, zq, Y, Yq):
        """Índice MIXTO (imágenes + captions de test). Para cada caption-query NUEVA: ¿hay un texto de OTRO concepto más cercano
        que la mejor imagen del concepto correcto? Devuelve (tasa de 'intrusos', margen medio imagen-correcta menos intruso)."""
        Y, Yq = torch.as_tensor(Y), torch.as_tensor(Yq); si, st = zq @ zi.T, zq @ zt.T
        mejor_img = torch.where(Y[None, :] == Yq[:, None], si, torch.full_like(si, -9)).max(1).values
        mejor_txt_mal = torch.where(Y[None, :] != Yq[:, None], st, torch.full_like(st, -9)).max(1).values
        return float((mejor_txt_mal > mejor_img).float().mean()), float((mejor_img - mejor_txt_mal).mean())

    Xq, Tq_, Yq, Lq = make_dataset(10, seed=3)
    filas = []
    for n in ("InfoNCE τ=0.01", "InfoNCE τ aprendida", "InfoNCE τ=0.2", "SigLIP (sigmoide)"):
        M = MODELOS[n]; _, zq = embebe(M["I"], M["Tx"], Xq[:1], Tq_, w2i)
        r0, m0 = tasa_intruso(M["zi"], M["zt"], zq, Yte, Yq); mi, mt = M["zi"].mean(0), M["zt"].mean(0)
        r1, m1 = tasa_intruso(centra(M["zi"], mi), centra(M["zt"], mt), centra(zq, mt), Yte, Yq)
        filas.append({"modelo": n, "gap": M["gap"], "intrusos (original)": r0, "intrusos (centrado)": r1, "margen original": m0, "margen centrado": m1})
    sesgo = pd.DataFrame(filas).set_index("modelo"); display(sesgo.round(3))
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.4)); x = np.arange(len(sesgo)); w = .38
    ax[0].bar(x - w/2, sesgo["intrusos (original)"], w, color=ROJO, label="original"); ax[0].bar(x + w/2, sesgo["intrusos (centrado)"], w, color=VERDE, label="centrado por modalidad")
    ax[0].set_xticks(x); ax[0].set_xticklabels(sesgo.index, rotation=15, fontsize=8); ax[0].set_ylabel("tasa de 'intrusos' (texto equivocado > imagen correcta)"); ax[0].legend(frameon=False, fontsize=8); ax[0].set_title("Índice mixto: texto equivocado que supera a la imagen correcta")
    ax[1].scatter(sesgo["gap"], sesgo["intrusos (original)"], s=70, color=AZUL); [ax[1].annotate(n, (g, r), fontsize=7, xytext=(4, 4), textcoords="offset points") for n, g, r in zip(sesgo.index, sesgo["gap"], sesgo["intrusos (original)"])]
    ax[1].set_xlabel("modality gap"); ax[1].set_ylabel("tasa de intrusos"); ax[1].set_title("Más gap, más intrusos")
    plt.tight_layout(); plt.show()
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** Con un gap pequeño o moderado (≤ 0.35 aquí) **no hay intrusos**: el texto correcto→imagen correcta sigue ganando a cualquier texto equivocado. Con $\\tau=0.01$ (gap ≈ 1) **el 100 % de las queries tiene un texto equivocado por delante de la imagen correcta**: el índice mixto es inservible aunque el retrieval texto→imagen *por separado* funcione.
    > Y ojo: **restar el centroide de cada modalidad no lo arregla** en el caso extremo (las imágenes siguen en un cono estrecho: coseno intra-imagen 0.62). La corrección por media es un parche, no un cambio de geometría; en la práctica se opta por índices separados con fusión por rangos (módulo 13) o por un modelo entrenado para un espacio unificado.
    """)
    nb.code(r'''
    # El pivote visual: ES ↔ EN sin pares ES-EN directos. Para cada caption ES de test, ¿su vecino EN más cercano es del mismo concepto?
    M = MODELOS["InfoNCE τ aprendida"]; zt = M["zt"]; Yt = torch.as_tensor(Yte); es = torch.tensor([l == "es" for l in Lte]); en = ~es
    S = zt[es] @ zt[en].T; acierto = float((Yt[en][S.argmax(1)] == Yt[es]).float().mean())
    print(f"caption ES → caption EN del mismo concepto (top-1): {acierto:.2f}  (azar = {1/16:.2f}) · entrenamiento SIN pares ES-EN directos")
    ''')
    nb.md("""
    > 👀 **Qué debes observar.** El alineamiento cross-lingüe aparece **gratis**: las dos lenguas se conectan por la imagen. Es la intuición de por qué CLIP multilingüe (y SigLIP 2) pueden dar buena búsqueda texto→imagen en idiomas con pocas parejas texto-texto. 🟡 En modelos reales la calidad por idioma es muy desigual: evalúala con tus queries en español.
    """)
