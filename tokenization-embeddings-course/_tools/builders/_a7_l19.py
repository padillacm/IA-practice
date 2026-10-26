"""Lección 19 · Playbook de élite (autor A7). La llama build_19.py."""
import _a7_common as C
import _a5_common as A5


def lesson(nb):
    nb.md(nb.badge() + r'''

# Módulo 19 · Playbook de élite: decisiones, trampas y revisión

**Nivel:** 🔴 Experto · **Duración:** ≈ 4 h (lección ≈ 2.5 h + proyecto ≈ 1.5 h) · **GPU:** no necesaria (CPU, `FAST_DEV_RUN`) · **Cómputo estimado:** 0 unidades de Colab.

**Prerrequisitos:** todo el curso, en especial 04 (vocabularios), 12 (embedders), 13 (híbrido), 14 (ANN), 15 (evaluación) y 18 (producción).

> 🧭 **Ruta núcleo vs ampliación.** Núcleo (≈ 1.5 h, lo que usa el proyecto): §1 árboles de decisión · §2 trampas de evaluación · §4 costes a escala (la rúbrica A del proyecto usa sus fórmulas) · §6 checklist. Ampliación (≈ 1 h): §3 gap offline/online · §4b chunking · §5 galería de fallos · §7 cultura.

**Hilo conductor — Políglota.** Políglota Labs ha crecido: hay tres equipos, dos clientes enterprise y una entrevista de *staff engineer* la semana que viene. Las lecciones anteriores **enumeraban** buenas prácticas; aquí las convertimos en **código que decide, mide y revisa**: árboles de decisión ejecutables, trampas de evaluación reproducidas con números, una calculadora de costes a escala, una galería de fallos reales reproducidos y un *linter* de PRs. Este módulo produce además `extras/GUIA_ENTREVISTAS.md` y `extras/LECTURA_PAPERS.md`.

> **Estado del arte a octubre de 2026.** Las reglas de los árboles son **heurísticas razonadas** con su fuente o con una medición en este notebook; los umbrales concretos dependen de tu hardware y de tus datos: re-mídelos.
''')
    nb.md(r'''## 🎯 Objetivos de aprendizaje
1. **Codificar** árboles de decisión para tokenizer, embedder, índice e híbrido, y **justificar** sus umbrales con mediciones.
2. **Reproducir y cuantificar** cuatro trampas de evaluación: tuning en test, *winner's curse*, dependencia del golden set y sesgo de *pooling*.
3. **Explicar** el gap offline/online y **recalcular** la comparación de sistemas con la mezcla real de tráfico.
4. **Estimar** el coste total de un sistema de retrieval de 1 M a 1 B de documentos (embedding, memoria, réplicas) con supuestos explícitos.
5. **Diagnosticar** fallos reales documentados y reproducir versiones mínimas de los más comunes.
6. **Revisar** PRs de tokenización/embeddings con una checklist ejecutable.
''')
    nb.md(r'''## 🔁 Conexión con módulos anteriores
<details><summary><b>1 · (M14)</b> ¿Hasta qué tamaño basta la fuerza bruta?</summary>

Hasta donde su latencia cumpla el SLA con batch = 1: depende de $N \cdot d$ y del hardware. Lo **mediremos** en §1 en vez de citar un número.
</details>
<details><summary><b>2 · (M15)</b> ¿Por qué no se elige un hiperparámetro mirando el test?</summary>

Porque el máximo de muchas estimaciones ruidosas está sesgado hacia arriba: el número reportado es optimista. Lo cuantificamos en §2 con validación cruzada.
</details>
<details><summary><b>3 · (M18)</b> ¿Qué ventaja tiene interleaving sobre A/B y qué no mide?</summary>

Mucha más potencia por impresión (comparación pareada dentro de la misma impresión); no mide impacto en métricas de negocio de sesión, que siguen pidiendo A/B.
</details>
<details><summary><b>4 · (M05)</b> ¿Por qué aparecen tokens «glitch»?</summary>

Porque el tokenizer se entrenó con datos distintos de los del modelo: hay tokens que el modelo casi nunca vio y cuyos embeddings quedaron sin entrenar (Land & Bartolo 2024).
</details>
<details><summary><b>5 · (M00, diagnóstico)</b> Con 40 queries, A tiene nDCG@10 = 0.61 y B = 0.63; el IC bootstrap pareado de B − A es [−0.01, 0.05]. ¿Despliegas B diciendo que «es mejor»?</summary>

No: el IC incluye el 0, así que con esas 40 queries no sabes si B es mejor. Desde el módulo 00 el IC bootstrap por queries es la unidad de decisión; las cuatro trampas de §2 son formas de engañarse incluso **con** IC (elegir en test, elegir el mejor de muchos, golden set sesgado, pooling).
</details>
<details><summary><b>6 · (M01 + M02, transferencia)</b> Indexas con NFC y la app móvil envía las queries sin normalizar. ¿Qué ves en las métricas y qué ítem de la checklist de §6 lo caza?</summary>

Fallos de búsqueda en las queries con acentos o composición distinta (NFD en iOS/macOS es habitual): bytes distintos → tokens distintos (BPE byte-level del 02) → BM25 sin coincidencia y vectores algo distintos. Nada lanza excepción. Lo caza el ítem 2, **simetría** de normalización y tokenización entre indexación y consulta.
</details>
''')
    nb.md(r'''## 💡 Intuición: un playbook es código que decide, mide y revisa
Un piloto no memoriza el manual: sigue **checklists** y cada ítem existe porque algo falló alguna vez. Un playbook de retrieval es lo mismo, con una diferencia: muchas de sus reglas se pueden **ejecutar**. Este módulo tiene tres verbos y cada uno se convierte en código:

* **Decidir** (§1, §4): árboles que reciben requisitos (N, d, RAM, idiomas, latencia, privacidad) y devuelven una decisión **con sus razones** y sus umbrales medidos, igual que un sistema de reglas de recsys que puedes auditar.
* **Medir sin engañarte** (§2, §3): las trampas que inflan o desinflan un número, reproducidas con datos de Políglota para que veas su tamaño.
* **Revisar** (§5, §6): fallos reales y un *linter* de PRs que los detecta antes de producción.

Cómo se aprende aquí: **ejemplo resuelto** (los árboles aplicados a mano en §1) → **práctica guiada** (el calentamiento del proyecto: revisar la propuesta de un becario) → **práctica independiente** (tres casos de *system design* con rúbrica). Es la misma escalera que usan las entrevistas de *staff*.
''')
    nb.md("## 0. Preparación\nLas mismas piezas canónicas del curso (corpus, métricas, BM25, estadística pareada, embedders v1/v2 con fallback) y el mini golden set de **paráfrasis** ES↔EN↔código del módulo 13.")
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
    nb.code(A5.CODE_CORPUS_SEED)
    nb.code(A5.CODE_PARAFRASIS_LOADER)
    nb.code(r'''
D1, Q1, D2, Q2 = EMB["v1"]["D"], EMB["v1"]["Q"], EMB["v2"]["D"], EMB["v2"]["Q"]
nd = lambda S: evaluate(run_desde_scores(S), qrels)["ndcg"]
pq_de = lambda S: ndcg_por_query(run_desde_scores(S))
print({"BM25": round(nd(S_BM25), 3), "v1": round(nd(Q1 @ D1.T), 3), "v2": round(nd(Q2 @ D2.T), 3)})
''')

    # ─────────────── §1 Árboles de decisión ───────────────
    nb.md(r'''## 1. Árboles de decisión ejecutables
Un árbol de decisión en una diapositiva no se puede testear. Lo escribimos como **funciones** que devuelven la decisión **y sus razones**, para poder aplicarlas a escenarios, revisarlas en un PR y cambiar un umbral cuando una medición lo contradiga.

✍️ **Ejemplo resuelto a mano (el árbol del índice).** 10 M de vectores de $d = 768$; el grafo HNSW con $M = 32$ cuesta $2\cdot 32\cdot 4 = 256$ B por vector. Memoria: float32 $= 10^7\cdot 768\cdot 4$ B $= 30.7$ GB; int8 $= 7.7$ GB; grafo $= 2.56$ GB. Regla: usar como mucho el 70 % de la RAM.
* **Máquina de 64 GB** (presupuesto 44.8 GB): float32 + grafo = 33.3 GB → cabe → **HNSW float32**.
* **Máquina de 16 GB** (presupuesto 11.2 GB): float32 no cabe; int8 + grafo = 10.2 GB → **HNSW + int8**, con rescore en float32 desde disco (módulo 12).
* Antes de todo eso, la primera pregunta: ¿cabe la **fuerza bruta** en el SLA? Ese umbral no se cita: lo medimos en la celda siguiente.

Hazlo en papel y comprueba que la salida de `elige_indice` coincide con tus dos líneas.''')
    nb.gemini(
        "imagen", "M19-IMG-01", "Árbol de decisión del índice vectorial",
        "La versión visual del árbol `elige_indice`: de N, memoria, filtros y actualizaciones a Flat, HNSW, HNSW+int8, IVF-PQ o DiskANN.",
        """Diagrama de árbol de decisión técnico, fondo blanco, paleta: azul #1F6FEB (preguntas), verde #2CA02C (decisiones finales), naranja #F28E2B (advertencias), gris #6B7280 (flechas). Tipografía sans-serif legible. Flujo de arriba abajo.
Nodo raíz (rombo azul): "¿Fuerza bruta cumple el p99 con batch = 1? (mídelo)". Rama "sí" → hoja verde "Flat exacto (FAISS IndexFlatIP / numpy)". Rama "no" → rombo azul "¿Vectores float32 + grafo caben en RAM?".
"sí" → hoja verde "HNSW (M = 16–32, efSearch según recall)". "no" → rombo azul "¿Caben en RAM con int8?".
"sí" → hoja verde "HNSW + int8 (rescore con float en disco)". "no" → rombo azul "¿SSD rápido disponible?".
"sí" → hoja verde "DiskANN / Vamana (PQ en RAM, grafo en SSD)". "no" → hoja verde "IVF-PQ (+ refine)".
A la derecha, dos notas naranjas conectadas con línea discontinua a todo el árbol: "Filtros muy selectivos → pre-filtro o grafo con filtros (ACORN)" y "Muchas actualizaciones → evita reentrenar IVF; HNSW admite inserciones, compacta borrados".
Título arriba: "¿Qué índice vectorial?".
Evita: cifras de rendimiento, logotipos, iconos decorativos, texto pequeño.""",
        "Árbol de decisión de arriba abajo: fuerza bruta, HNSW, HNSW con int8, DiskANN o IVF-PQ según latencia, memoria y disco, con notas sobre filtros y actualizaciones.",
        """
¿Flat cumple p99? ─sí→ Flat
   └no→ ¿float32 cabe en RAM? ─sí→ HNSW
          └no→ ¿int8 cabe? ─sí→ HNSW+int8 (+rescore)
                 └no→ ¿SSD? ─sí→ DiskANN │ no→ IVF-PQ
Notas: filtros selectivos → pre-filtro/ACORN · updates → HNSW, compactar
""")
    nb.md("> 👀 **Qué debes observar:** la **primera** pregunta no es «¿qué índice es el mejor?» sino «¿necesito un índice?». El umbral de esa pregunta no se copia de un blog: lo medimos a continuación.")
    nb.code(r'''
import faiss
faiss.omp_set_num_threads(1)

def p99_ms(fn, Q, warm=5):
    for q in Q[:warm]: fn(q)
    t = []
    for q in Q:
        t0 = time.perf_counter(); fn(q); t.append((time.perf_counter() - t0) * 1e3)
    return float(np.percentile(t, 99))

rng = np.random.default_rng(SEED); d = 128
Ns = [1_000, 10_000, 50_000, 100_000] if FAST_DEV_RUN else [1_000, 10_000, 100_000, 500_000, 1_000_000]
Xall = rng.normal(size=(max(Ns), d)).astype("float32"); Xall /= np.linalg.norm(Xall, axis=1, keepdims=True)
Qs = rng.normal(size=(100, d)).astype("float32"); Qs /= np.linalg.norm(Qs, axis=1, keepdims=True)
filas = []
for N in Ns:
    X = Xall[:N]
    flat = faiss.IndexFlatIP(d); flat.add(X)
    hnsw = faiss.IndexHNSWFlat(d, 32, faiss.METRIC_INNER_PRODUCT); hnsw.hnsw.efConstruction = 80; hnsw.add(X); hnsw.hnsw.efSearch = 64
    gt = flat.search(Qs, 10)[1]; got = hnsw.search(Qs, 10)[1]
    rec = np.mean([len(set(a) & set(b)) / 10 for a, b in zip(gt, got)])
    filas.append({"N": N, "flat_p99_ms": p99_ms(lambda q: flat.search(q[None], 10), Qs),
                  "hnsw_p99_ms": p99_ms(lambda q: hnsw.search(q[None], 10), Qs), "hnsw_recall@10": rec})
df_idx = pd.DataFrame(filas)
SLA_MS = 5.0
fig, ax = plt.subplots(figsize=(7.5, 4))
ax.loglog(df_idx.N, df_idx.flat_p99_ms, "o-", color=NARANJA, label="Flat exacto (p99)"); ax.loglog(df_idx.N, df_idx.hnsw_p99_ms, "o-", color=AZUL, label="HNSW M=32 ef=64 (p99)")
ax.axhline(SLA_MS, color=ROJO, ls="--", label=f"SLA de búsqueda = {SLA_MS} ms")
ax.set_xlabel("N vectores (d=128, 1 hilo)"); ax.set_ylabel("p99 por query (ms)"); ax.set_title("¿Cuándo deja de bastar la fuerza bruta? (medido)")
ax.legend(fontsize=8); plt.tight_layout(); plt.show()
df_idx.round(3)
''')
    nb.md(r'''> 👀 **Qué debes observar:** la latencia de Flat crece lineal con $N$ y cruza el SLA en algún punto entre decenas y cientos de miles de vectores **en este hardware con un hilo**; HNSW apenas crece, a cambio de un recall < 1 que **cae con N** (columna `hnsw_recall@10`): con vectores gaussianos isótropos, el peor caso para ANN, es mucho más bajo que con embeddings reales (módulo 14), y se recupera subiendo `efSearch` a costa de latencia. Nunca elijas el índice sin mirar ambas columnas. Ese cruce es el umbral `N_FLAT_MAX` que usa el árbol: **recalcúlalo** con tu $d$, tu CPU/GPU y tu SLA.''')
    nb.code(r'''
N_FLAT_MAX = int(df_idx.loc[df_idx.flat_p99_ms <= SLA_MS, "N"].max()) if (df_idx.flat_p99_ms <= SLA_MS).any() else 1_000

def elige_indice(N, d, ram_gb, ssd=True, filtros_selectivos=False, muchas_actualizaciones=False, n_flat_max=N_FLAT_MAX):
    """Devuelve (decisión, razones). Memoria: float32 = 4·d B/vector, int8 = d B, grafo HNSW ≈ 2·M·4 B/vector (M=32)."""
    gb = lambda bytes_vec: N * bytes_vec / 1e9
    grafo = 2 * 32 * 4
    r = [f"N={N:,}, d={d}: float32={gb(4 * d):.1f} GB, int8={gb(d):.1f} GB, grafo≈{gb(grafo):.1f} GB, RAM={ram_gb} GB"]
    if N * d <= n_flat_max * 128:
        dec = "Flat exacto"; r.append(f"N·d ≤ umbral medido ({n_flat_max:,}×128): la fuerza bruta cumple el SLA y su recall es 1")
    elif gb(4 * d + grafo) <= 0.7 * ram_gb:
        dec = "HNSW (float32)"; r.append("cabe en RAM con margen del 30 %")
    elif gb(d + grafo) <= 0.7 * ram_gb:
        dec = "HNSW + int8 (rescore con float32 en disco)"; r.append("float32 no cabe; int8 sí (pérdida típica pequeña, módulo 12)")
    elif ssd:
        dec = "DiskANN / Vamana (PQ en RAM, grafo + vectores en SSD)"; r.append("no cabe en RAM: diseño para pocas lecturas aleatorias de SSD")
    else:
        dec = "IVF-PQ + refine"; r.append("sin SSD rápido: compresión agresiva en RAM")
    if filtros_selectivos:
        r.append("filtros selectivos: pre-filtro (si quedan pocos candidatos, fuerza bruta sobre ellos) o grafo con filtros (ACORN); nunca solo post-filtro")
    if muchas_actualizaciones:
        r.append("muchas actualizaciones: evita reentrenar centroides IVF a menudo; HNSW admite inserciones; planifica compactar borrados")
    return dec, r

for esc in [dict(N=50_000, d=384, ram_gb=16), dict(N=10_000_000, d=768, ram_gb=64), dict(N=10_000_000, d=768, ram_gb=16),
            dict(N=1_000_000_000, d=768, ram_gb=256, filtros_selectivos=True)]:
    dec, rz = elige_indice(**esc); print(f"▶ {dec}\n   " + "\n   ".join(rz))
''')
    nb.code(r'''
def elige_tokenizer(usa_modelo_preentrenado: bool, n_scripts: int = 1, mucho_codigo: bool = False, texto_ruidoso: bool = False):
    """Árbol de decisión del tokenizer (módulos 02–07)."""
    if usa_modelo_preentrenado:
        return "usa el tokenizer DEL MODELO", ["cambiarlo exige tokenizer transfer y reentrenar embeddings (módulo 07)",
                                               "mide fertilidad/paridad para presupuestar coste y contexto (módulo 04)"]
    r = ["byte-level o byte_fallback: ningún texto queda fuera del vocabulario (módulos 02–03)"]
    dec = "BPE byte-level"
    if n_scripts >= 3:
        dec = "BPE byte-level o Unigram con byte_fallback, vocabulario grande (≥ 100 k)"; r.append("muchos scripts: el vocabulario se reparte; mide la prima de tokens por idioma (04)")
    if mucho_codigo:
        r.append("código: pre-tokenización que preserve espacios/indentación y divida dígitos (regex tipo o200k, 02/04)")
    if texto_ruidoso:
        r.append("texto muy ruidoso o a nivel de carácter: evalúa byte-level/tokenizer-free (06–07), madurez 🔴")
    return dec, r

def elige_embedder(privacidad_on_prem: bool, multilingue: bool, pares_dominio: int, p99_ms_embed: float, presupuesto_gpu: bool):
    """Árbol de decisión del embedder (módulos 10–12). La validación final es SIEMPRE tu golden set + test pareado."""
    r = []
    if privacidad_on_prem or not presupuesto_gpu is False and p99_ms_embed < 20:
        base = "open weights autohospedado"; r.append("privacidad/latencia: el texto no sale y no hay viaje de red a una API")
    else:
        base = "API comercial o open weights"; r.append("sin restricción de residencia: compara coste total (módulo 18)")
    if multilingue:
        r.append("multilingüe: familias e5 multilingüe, BGE-M3, Qwen3-Embedding, EmbeddingGemma, Gemini Embedding (módulo 12; verifica versiones)")
    if pares_dominio >= 1000:
        r.append(f"{pares_dominio:,} pares de dominio: fine-tuning contrastivo con negativos duros filtrados (módulo 11)")
    if p99_ms_embed < 20:
        r.append("p99 de embedding < 20 ms: modelo pequeño (≤ ~300 M) o destilado; Matryoshka para bajar d")
    r.append("decide con TU golden set (estratificado por idioma) y test pareado, no con la media de MTEB (módulo 15)")
    return base, r

def elige_hibrido(identificadores_exactos: bool, parafrasis_multilingue: bool, presupuesto_ms: float, ms_reranker_por_doc: float = 2.0):
    """Árbol de decisión de la arquitectura de retrieval (módulo 13)."""
    r, etapas = [], []
    if identificadores_exactos:
        etapas.append("BM25"); r.append("identificadores, códigos de error, nombres de función: el léxico gana (módulo 13)")
    if parafrasis_multilingue or not etapas:
        etapas.append("denso"); r.append("paráfrasis y cruce ES↔EN: el denso gana")
    dec = " + ".join(etapas) + (" con RRF" if len(etapas) > 1 else "")
    K = int(max(0, presupuesto_ms - 30) // ms_reranker_por_doc)   # 30 ms reservados a primera etapa + red (supuesto)
    if K >= 20:
        dec += f" → reranker cross-encoder sobre top-{min(K, 100)}"; r.append(f"presupuesto: {presupuesto_ms} ms ⇒ K≈{K} docs a {ms_reranker_por_doc} ms/doc (supuesto)")
    return dec, r

for f, kw in [(elige_tokenizer, dict(usa_modelo_preentrenado=False, n_scripts=3, mucho_codigo=True)),
              (elige_embedder, dict(privacidad_on_prem=True, multilingue=True, pares_dominio=5000, p99_ms_embed=15, presupuesto_gpu=True)),
              (elige_hibrido, dict(identificadores_exactos=True, parafrasis_multilingue=True, presupuesto_ms=150))]:
    dec, rz = f(**kw); print(f"{f.__name__}: ▶ {dec}\n   - " + "\n   - ".join(rz))
''')
    nb.md(r'''> ⚠️ Mira con lupa `elige_embedder`: la condición `privacidad_on_prem or not presupuesto_gpu is False and p99_ms_embed < 20` tiene un **bug de precedencia** a propósito (`not presupuesto_gpu is False` se lee `not (presupuesto_gpu is False)`). La checklist de §6 existe para cazar exactamente esto: las reglas de decisión también son código y también se revisan y se testean. Ejercicio: escribe un test que lo detecte y arréglalo (el proyecto usa una versión corregida).''')

    # ─────────────── §2 Trampas de evaluación ───────────────
    nb.md(r'''## 2. Trampas de evaluación, reproducidas y medidas
Cuatro trampas que hacen que un número «mejore» sin que el sistema mejore. Para cada una: el valor **reportado** con la práctica incorrecta y el valor **honesto**.''')
    nb.gemini(
        "imagen", "M19-IMG-03", "Cuatro trampas de evaluación en retrieval",
        "Mapa visual de las cuatro trampas que se reproducen en la sección: tuning en test, winner's curse, dependencia del golden set y sesgo de pooling, con la dirección del sesgo y su remedio.",
        """Infografía técnica en cuadrícula 2x2, fondo blanco, paleta: naranja #F28E2B (práctica incorrecta), azul #1F6FEB (práctica correcta), gris #6B7280 (texto secundario), verde #2CA02C (remedio). Sans-serif legible, sin decoración.
Cuadrante 1, título "T1 · Ajustar en el test": a la izquierda una rejilla de 21 puntos con uno resaltado en naranja y la etiqueta "α elegido mirando el test"; a la derecha cinco bloques apilados (pliegues) con uno en azul y la etiqueta "validación cruzada". Flecha hacia arriba naranja "sesgo: optimista". Remedio verde: "CV o test ciego".
Cuadrante 2, título "T2 · Winner's curse": nube de 20 puntos grises en un plano "dev" (eje x) vs "test" (eje y), uno rojo arriba a la derecha en x y en el centro en y. Flecha naranja "sesgo: optimista". Remedio: "IC pareado + Holm".
Cuadrante 3, título "T3 · Depende del golden set": dos pequeñas tablas lado a lado, "ítem conocido (títulos)" y "paráfrasis", con dos barras cada una "BM25" y "denso" cuyo orden se invierte entre tablas. Remedio: "reportar por golden set y por slice".
Cuadrante 4, título "T4 · Sesgo de pooling": un embudo "top-10 de BM25 → juicios", y un sistema nuevo con documentos marcados "relevante sin juzgar = 0". Flecha naranja hacia abajo "sesgo: penaliza al sistema nuevo". Remedio: "juzgar el top-k del sistema nuevo".
Evita: cifras inventadas, logotipos, iconos decorativos, texto pequeño.""",
        "Cuadrícula 2x2 con las cuatro trampas (tuning en test, winner's curse, golden set, pooling), la dirección de su sesgo y su remedio.",
        """
T1 tuning en test   → optimista  → CV / test ciego
T2 winner's curse   → optimista  → IC pareado + Holm
T3 golden set       → cambia el orden → reportar por golden set y slice
T4 pooling          → penaliza al nuevo → juzgar su top-k
""")
    nb.md(r'''> 👀 **Qué debes observar:** dos trampas inflan el número del sistema que más tuneaste, una cambia el veredicto según el golden set y otra castiga al sistema nuevo. Saber la **dirección** del sesgo te dice qué sistema está favorecido antes de mirar ningún número.

### T1 · Ajustar en el test
Elegimos el peso $\alpha$ de la fusión lineal $\alpha \cdot \text{denso} + (1-\alpha)\cdot\text{BM25}$ (scores min-max por query) en una rejilla de 21 valores. Práctica incorrecta: elegir $\alpha$ con **todas** las queries y reportar ese nDCG. Práctica correcta: **validación cruzada** de 5 pliegues (elegir en 4, medir en 1).''')
    nb.code(r'''
def minmax(S):
    lo, hi = S.min(1, keepdims=True), S.max(1, keepdims=True)
    return (S - lo) / np.maximum(hi - lo, 1e-9)

SD, SB = minmax(Q2 @ D2.T), minmax(S_BM25)
alfas = np.linspace(0, 1, 21)
PQ_A = np.array([pq_de(a * SD + (1 - a) * SB) for a in alfas])        # (alfas, queries)
reportado = PQ_A.mean(1).max()
rng = np.random.default_rng(SEED); pliegues = np.array_split(rng.permutation(len(qids)), 5)
honesto = np.zeros(len(qids))
for f in pliegues:
    tr = np.setdiff1d(np.arange(len(qids)), f)
    a_best = PQ_A[:, tr].mean(1).argmax()
    honesto[f] = PQ_A[a_best, f]
T1 = {"reportado (α elegido en test)": reportado, "honesto (CV 5 pliegues)": honesto.mean()}
print({k: round(v, 3) for k, v in T1.items()}, "· α* en test =", alfas[PQ_A.mean(1).argmax()])
''')
    nb.md(r'''### T2 · *Winner's curse*: elegir el mejor de muchos
Generamos 20 configuraciones **casi equivalentes** (v2 restringido a 64 dimensiones aleatorias de 128: como 20 semillas o 20 combinaciones de hiperparámetros) y elegimos la mejor en un *dev* de 55 queries. ¿Cuánto rinde en el *test* (las otras 55)?

✍️ **Cuánto optimismo esperar, a mano.** Si las 20 configuraciones valen lo mismo y la medición en dev tiene un ruido de desviación típica $\sigma$, la ganadora está por encima de la media, en esperanza, ≈ $1.87\,\sigma$ (el máximo esperado de 20 normales estándar; con 40, ≈ $2.16\,\sigma$). Con $\sigma = 0.015$ de nDCG eso son ≈ **+0.03 de ventaja que no existe**. Es la regresión a la media de los *rankings* de recsys: el ítem con mejor CTR tras pocas impresiones suele ser el que tuvo suerte.''')
    nb.code(r'''
rng = np.random.default_rng(SEED); perm = rng.permutation(len(qids)); dev, te = perm[:55], perm[55:]
cfg = []
for c in range(20):
    keep = rng.choice(D2.shape[1], D2.shape[1] // 2, replace=False)
    pq = pq_de(l2n(Q2[:, keep]) @ l2n(D2[:, keep]).T)
    cfg.append((pq[dev].mean(), pq[te].mean()))
cfg = np.array(cfg); b = cfg[:, 0].argmax()
T2 = {"reportado (mejor en dev)": cfg[b, 0], "honesto (ese mismo en test)": cfg[b, 1], "media de las 20 en test": cfg[:, 1].mean()}
fig, ax = plt.subplots(figsize=(6.5, 4))
ax.scatter(cfg[:, 0], cfg[:, 1], color=GRIS, label="20 configuraciones"); ax.scatter(cfg[b, 0], cfg[b, 1], color=ROJO, s=90, label="la «ganadora» en dev")
lim = [cfg.min() - .02, cfg.max() + .02]; ax.plot(lim, lim, ls=":", color=GRIS, label="dev = test")
ax.set_xlabel("nDCG@10 en dev (55 queries)"); ax.set_ylabel("nDCG@10 en test (55 queries)"); ax.set_title("Winner's curse: la mejor en dev regresa a la media")
ax.legend(fontsize=8); plt.tight_layout(); plt.show()
print({k: round(v, 3) for k, v in T2.items()}, f"· correlación dev-test = {np.corrcoef(cfg[:, 0], cfg[:, 1])[0, 1]:.2f}")
''')
    nb.md(r'''> 👀 **Qué debes observar:** la «ganadora» en dev pierde en test buena parte de su ventaja sobre la media (**regresión a la media**): una parte de la diferencia entre configuraciones es real y otra es **ruido de muestreo de queries**. Cuanto menor la correlación dev-test, mayor el optimismo del número de dev. Con 55 queries, diferencias de ±0.02–0.05 son indistinguibles del azar (el IC del módulo 15 lo habría dicho). Remedio: test ciego que no se toca hasta el final, IC pareados y corrección por comparaciones múltiples (Holm).

### T3 · La conclusión depende del golden set
El golden set canónico del módulo 00 es de «ítem conocido» (la query es el **título** del artículo, la primera frase del docstring), que favorece a los métodos léxicos. El mini golden set de paráfrasis del módulo 13 pregunta con **otras palabras**. Mismo par de sistemas, dos golden sets:''')
    nb.code(r'''
P = corpus_parafrasis(); p_ids = [d["id"] for d in P["docs"]]; p_txt = [d["text"] for d in P["docs"]]; p_q = [q["text"] for q in P["queries"]]
bmP = BM25().fit([tokenize_simple(t) for t in p_txt], p_ids)
SBP = np.array([bmP.scores(tokenize_simple(q)) for q in p_q])
SDP = VERS["v2"].encode_queries(p_q) @ VERS["v2"].encode_docs(p_txt).T
run_p = lambda S: {q["qid"]: rank_from_scores(S[i], p_ids, 10) for i, q in enumerate(P["queries"])}
T3 = {"canónico · BM25": nd(S_BM25), "canónico · denso v2": nd(Q2 @ D2.T),
      "paráfrasis · BM25": evaluate(run_p(SBP), P["qrels"])["ndcg"], "paráfrasis · denso v2": evaluate(run_p(SDP), P["qrels"])["ndcg"]}
print({k: round(v, 3) for k, v in T3.items()})
print(f"Δ(denso − BM25): canónico {T3['canónico · denso v2'] - T3['canónico · BM25']:+.3f} · paráfrasis {T3['paráfrasis · denso v2'] - T3['paráfrasis · BM25']:+.3f}")
''')
    nb.md(r'''> 👀 **Qué debes observar:** el mismo par de sistemas cambia de tamaño (y puede cambiar de signo) la diferencia según el golden set; en paráfrasis ambos caen mucho porque las queries casi no comparten palabras. ⚠️ Con el *fallback* TF-IDF+SVD el «denso» también es léxico (n-gramas de caracteres), así que **no** gana en paráfrasis; con un embedder neuronal multilingüe real, el resultado esperable (módulo 13) es que el denso gane con claridad en paráfrasis. La lección es la misma: **reporta por golden set y por slice**, nunca un único número.

### T4 · Sesgo de *pooling*: juzgar solo lo que vio el sistema viejo
En la práctica los qrels se construyen juzgando los top-$k$ de los sistemas existentes (*pooling*). Un sistema nuevo que encuentra documentos relevantes **no juzgados** recibe 0 por ellos. Simulamos que solo se juzgó el top-10 de BM25:''')
    nb.code(r'''
run_bm = run_desde_scores(S_BM25)
qrels_pool = {q: {d: r for d, r in rels.items() if d in set(run_bm[q])} for q, rels in qrels.items()}
def nd_pool(S):
    run = run_desde_scores(S)
    return float(np.mean([ndcg_at_k(run[q], qrels_pool[q], 10) if any(qrels_pool[q].values()) else 0.0 for q in qids]))
T4 = {}
for nombre, S in (("BM25", S_BM25), ("v1", Q1 @ D1.T), ("v2", Q2 @ D2.T)):
    T4[nombre] = (nd(S), nd_pool(S))
print({k: (round(a, 3), round(b, 3)) for k, (a, b) in T4.items()}, "← (qrels completos, qrels del pool de BM25)")
fig, ax = plt.subplots(figsize=(10, 4))
etiquetas = ["T1 tuning en test", "T2 winner's curse", "T4 pooling (v2)"]
rep = [T1["reportado (α elegido en test)"], T2["reportado (mejor en dev)"], T4["v2"][1]]
hon = [T1["honesto (CV 5 pliegues)"], T2["honesto (ese mismo en test)"], T4["v2"][0]]
x = np.arange(3); ax.bar(x - .2, rep, .4, color=NARANJA, label="práctica incorrecta"); ax.bar(x + .2, hon, .4, color=AZUL, label="práctica correcta")
ax.set_xticks(x); ax.set_xticklabels(etiquetas); ax.set_ylabel("nDCG@10"); ax.set_ylim(min(rep + hon) - .1, max(rep + hon) + .05)
ax.set_title("Trampas de evaluación: número reportado vs número honesto"); ax.legend(); plt.tight_layout(); plt.show()
''')
    nb.md(r'''> 👀 **Qué debes observar:** T1 y T2 **inflan** el número (optimismo por selección); T4 **desinfla** al sistema nuevo (BM25 no cambia porque el pool es suyo, v1/v2 pierden). Las tres sesgan la decisión en direcciones previsibles: hacia el sistema que más tuneaste y hacia el sistema que construyó los juicios. Remedios: CV o test ciego (T1, T2), pools con varios sistemas + juicio de los no juzgados del sistema nuevo (T4; LLM-as-judge validado contra humanos, módulo 15).''')

    # ─────────────── §3 Gap offline/online ───────────────
    nb.md(r'''## 3. El gap offline/online
Tres fuentes clásicas de discrepancia entre el nDCG del golden set y lo que vive el usuario:
1. **Mezcla de tráfico**: el golden set pondera los idiomas/slices distinto que el tráfico real.
2. **Interfaz**: el usuario ve 3–5 resultados (móvil, panel de RAG con contexto limitado), no 10; y hay sesgo de posición.
3. **Lo que el golden set no tiene**: queries sin respuesta en el corpus, queries ambiguas, latencia (un sistema mejor pero más lento puede perder usuarios).

🧪 (1) Recalculamos la comparación BM25 vs denso v2 ponderando cada slice por una mezcla de tráfico que varía de 0 % a 80 % de queries de código.''')
    nb.gemini(
        "imagen", "M19-IMG-02", "Del nDCG offline a la métrica online",
        "Embudo que muestra por qué una mejora offline se encoge o se invierte online: mezcla de tráfico, interfaz y sesgo de posición, queries sin respuesta, latencia.",
        """Infografía técnica en forma de embudo horizontal (izquierda → derecha), fondo blanco, paleta: azul #1F6FEB (métricas), naranja #F28E2B (pérdidas), verde #2CA02C (métrica final), gris #6B7280 (texto secundario). Sans-serif legible.
A la izquierda, una caja azul ancha: "nDCG@10 offline (golden set)". El embudo se estrecha en cuatro tramos, cada uno con una etiqueta naranja encima:
tramo 1: "Mezcla de tráfico ≠ mezcla del golden set (reponderar por slice)";
tramo 2: "Interfaz: el usuario ve 3–5 resultados + sesgo de posición";
tramo 3: "Queries sin respuesta o ambiguas que el golden set no contiene";
tramo 4: "Latencia y abandono".
A la derecha, una caja verde estrecha: "Métrica online (éxito de sesión, interleaving, A/B)".
Debajo, en gris, una flecha de vuelta de derecha a izquierda con el texto: "muestrear tráfico real → ampliar el golden set".
Evita: números inventados, logotipos, iconos de personas, texto pequeño.""",
        "Embudo de izquierda a derecha desde el nDCG offline hasta la métrica online, con cuatro pérdidas etiquetadas y una flecha de realimentación al golden set.",
        """
nDCG@10 offline ▶ [mezcla de tráfico] ▶ [interfaz top-3/5 + sesgo posición] ▶ [queries sin respuesta] ▶ [latencia] ▶ métrica online
           ◀──────────── muestrear tráfico real y ampliar el golden set ◀────────────
""")
    nb.md("> 👀 **Qué debes observar:** cada tramo del embudo es una corrección que puedes **medir o simular** antes de lanzar (las celdas de abajo hacen la 1 y la 2); la flecha de vuelta es lo que cierra el gap a largo plazo.")
    nb.code(r'''
pq_bm, pq_v2 = pq_de(S_BM25), pq_de(Q2 @ D2.T)
slices = ["es", "en", "code"]
m = {n: np.array([pq[q_lang == l].mean() for l in slices]) for n, pq in (("BM25", pq_bm), ("denso v2", pq_v2))}
frac_code = np.linspace(0, 0.8, 17)
delta = []
for fc in frac_code:
    w = np.array([(1 - fc) * 0.7, (1 - fc) * 0.3, fc])          # el resto del tráfico: 70 % español, 30 % inglés (supuesto)
    delta.append(w @ m["denso v2"] - w @ m["BM25"])
w_golden = np.array([np.mean(q_lang == l) for l in slices])
fig, ax = plt.subplots(figsize=(7.5, 4))
ax.plot(frac_code * 100, delta, "o-", color=AZUL); ax.axhline(0, color=GRIS)
ax.axvline(w_golden[2] * 100, color=NARANJA, ls="--", label=f"mezcla del golden set ({w_golden[2]*100:.0f} % código)")
ax.set_xlabel("% de queries de código en el tráfico real"); ax.set_ylabel("Δ nDCG@10 (denso v2 − BM25) ponderado")
ax.set_title("La comparación depende de la mezcla de tráfico"); ax.legend(fontsize=8); plt.tight_layout(); plt.show()
pd.DataFrame(m, index=slices).round(3)
''')
    nb.md(r'''> 👀 **Qué debes observar:** con pesos del golden set ambos sistemas empatan; con más tráfico en español gana BM25 y con más código gana el denso. Si no sabes la mezcla real, **no sabes cuál es mejor**. En producción: pondera cada slice por su frecuencia en logs (muestreo estratificado del tráfico) y reporta también el peor slice.

🧪 (2) Interfaz: el usuario de Políglota ve 3 resultados. ¿Coincide el orden de sistemas por nDCG@10 con el orden por nDCG@3 y por la probabilidad de éxito con el modelo de clic del módulo 18?''')
    nb.code(r'''
P_EXAM = np.array([0.95, 0.7, 0.5, 0.35, 0.25, 0.18, 0.13, 0.1, 0.08, 0.06])
def exito_esperado(S, top=3, p_rel=0.8, p_norel=0.05):
    """P(al menos un clic) en el top visible con el modelo de clic con sesgo de posición."""
    run = run_desde_scores(S)
    R = np.array([[1.0 if qrels[q].get(dd, 0) > 0 else 0.0 for dd in run[q][:top]] for q in qids])
    p_click = P_EXAM[:top] * np.where(R > 0, p_rel, p_norel)
    return float(np.mean(1 - np.prod(1 - p_click, axis=1)))

lo_c, esc_c = np.quantile(D2, 0.001, 0), (np.quantile(D2, 0.999, 0) - np.quantile(D2, 0.001, 0)) / 255
D2_i8 = (np.clip(np.round((D2 - lo_c) / esc_c) - 128, -128, 127) + 128) * esc_c + lo_c
sist = {"BM25": S_BM25, "v1": Q1 @ D1.T, "v2": Q2 @ D2.T, "v2 int8": Q2 @ D2_i8.T, "RRF(v2,BM25)": None, "lineal α=.5": 0.5 * SD + 0.5 * SB}
rk = lambda S: np.argsort(np.argsort(-S, 1, kind="stable"), 1, kind="stable")
sist["RRF(v2,BM25)"] = 1 / (61 + rk(Q2 @ D2.T)) + 1 / (61 + rk(S_BM25))
filas = [{"sistema": n, "nDCG@10": evaluate(run_desde_scores(S), qrels, 10)["ndcg"], "nDCG@3": evaluate(run_desde_scores(S, 3), qrels, 3)["ndcg"],
          "éxito top-3 (simulado)": exito_esperado(S)} for n, S in sist.items()]
df_gap = pd.DataFrame(filas).sort_values("nDCG@10", ascending=False)
fig, ax = plt.subplots(figsize=(7, 4))
ax.scatter(df_gap["nDCG@10"], df_gap["éxito top-3 (simulado)"], color=AZUL, s=60)
for _, r in df_gap.iterrows():
    ax.annotate(r.sistema, (r["nDCG@10"], r["éxito top-3 (simulado)"]), xytext=(4, 4), textcoords="offset points", fontsize=8)
ax.set_xlabel("nDCG@10 offline"); ax.set_ylabel("P(éxito) con 3 resultados visibles"); ax.set_title("Offline vs online (modelo de clic)")
plt.tight_layout(); plt.show()
df_gap.round(3)
''')
    nb.md(r'''> 👀 **Qué debes observar:** la relación es monótona a grandes rasgos pero **no** preserva el orden fino: sistemas con nDCG@10 casi iguales pueden ordenarse distinto por nDCG@3 y por éxito en top-3, y diferencias offline de 0.01–0.02 desaparecen en la métrica online. Optimiza la métrica que se parece a la interfaz (aquí, @3) y confirma online (interleaving, módulo 18). El modelo de clic es de **juguete**: sus parámetros son supuestos.''')

    # ─────────────── §4 Costes a escala ───────────────
    nb.md(r'''## 4. Costes a escala: de 1 M a 1 B de documentos
Una calculadora con **supuestos explícitos** (cámbialos): embedding inicial por API (0.02 $/1M tokens, oct-2026), 400 tokens por chunk, $d = 768$, RAM a 3 $/GB-mes (**supuesto** ilustrativo para instancias con mucha memoria; mira tu proveedor), 1 réplica cada 500 QPS (**supuesto**) y 2 réplicas mínimo por disponibilidad. Comparamos float32, int8 y binario + rescore (float32 en SSD a 0.1 $/GB-mes, **supuesto**).''')
    nb.code(r'''
SUP = dict(precio_tok=0.02, tok_chunk=400, d=768, usd_gb_ram_mes=3.0, usd_gb_ssd_mes=0.10, qps_por_replica=500, replicas_min=2, grafo_b=256)

def costo_sistema(N, precision, qps, sup=SUP):
    """Coste inicial (embedding) y mensual (RAM + SSD de todas las réplicas). Devuelve dict en USD."""
    bpv = {"float32": 4 * sup["d"], "int8": sup["d"], "binario+rescore": sup["d"] / 8}[precision]
    ram_gb = N * (bpv + sup["grafo_b"]) / 1e9
    ssd_gb = N * 4 * sup["d"] / 1e9 if precision != "float32" else 0.0
    rep = max(sup["replicas_min"], math.ceil(qps / sup["qps_por_replica"]))
    return {"embedding_inicial": N * sup["tok_chunk"] / 1e6 * sup["precio_tok"], "ram_mes": rep * ram_gb * sup["usd_gb_ram_mes"],
            "ssd_mes": rep * ssd_gb * sup["usd_gb_ssd_mes"], "ram_gb_por_replica": ram_gb, "replicas": rep}

Ns_c = [1e6, 1e7, 1e8, 1e9]; precs = ["float32", "int8", "binario+rescore"]
tab = pd.DataFrame([{"N": int(N), "precisión": p, **costo_sistema(N, p, qps=1000)} for N in Ns_c for p in precs])
fig, ax = plt.subplots(figsize=(9, 4.2))
x = np.arange(len(Ns_c)); w = 0.27
for j, (p, c) in enumerate(zip(precs, [GRIS, AZUL, VERDE])):
    t = tab[tab["precisión"] == p]
    ax.bar(x + (j - 1) * w, t.ram_mes + t.ssd_mes, w, color=c, label=f"{p} · infra mensual")
    ax.scatter(x + (j - 1) * w, t.embedding_inicial, color=NARANJA, marker="D", zorder=3, label="embedding inicial (una vez)" if j == 0 else None)
ax.set_yscale("log"); ax.set_xticks(x); ax.set_xticklabels(["1 M", "10 M", "100 M", "1 B"]); ax.set_xlabel("documentos (chunks)")
ax.set_ylabel("USD (log)"); ax.set_title("Coste a escala (1 000 QPS, d=768, supuestos de SUP)"); ax.legend(fontsize=8); plt.tight_layout(); plt.show()
tab.round(1)
''')
    nb.md(r'''> 👀 **Qué debes observar:** el embedding inicial es un pago único que crece lineal con $N$; la **memoria se paga cada mes y por réplica**, y a partir de ~100 M de chunks domina con holgura: ahí la cuantización deja de ser una optimización y pasa a ser la arquitectura. Fíjate también en `ram_gb_por_replica`: con 1 B de vectores float32 ninguna máquina normal lo aloja → sharding (y la cola de §3 del módulo 18) o DiskANN. Todos los precios de infraestructura de esta celda son **supuestos**.''')

    # ─────────────── §4b Chunking (revisión élite) ───────────────
    nb.md(r'''## 4b. Chunking: la decisión que fija $N$ (y que casi nadie mide)
En la calculadora anterior $N$ es «número de chunks», no de documentos: el tamaño de chunk multiplica la memoria, el coste de embedding (por los tokens repetidos si hay solapamiento) y la latencia del ANN, y a la vez cambia la calidad. Tres hechos que un equipo de retrieval sabe:
* **Truncado vs troceado.** Un embedder tiene un `max_seq_length`; lo que pasa de ahí se tira sin aviso (F1 del §5). Trocear evita perder texto, pero cada chunk pierde el contexto del documento (de ahí *late chunking*, módulo 13 §9, y *Contextual Retrieval*, módulo 20 🏭).
* **Agregación al documento.** Si el usuario quiere documentos, el score del documento se agrega desde sus chunks: el máximo (**MaxP**) o solo el primer chunk (**FirstP**); Dai & Callan (2019) lo compararon con BERT como reranker: en Robust04 MaxP superó a FirstP (nDCG@20 0.469 frente a 0.444 con títulos), pero en ClueWeb09-B con descripciones ganó FirstP (0.272 frente a 0.262); la mejor agregación depende de dónde está la información en tus documentos. Detalle útil: añadían el **título** al principio de cada pasaje para devolverle contexto.
* **Chunks cortos = más vectores y más casi duplicados** en el top-k (el mismo documento ocupa varias posiciones): hay que deduplicar por documento antes de evaluar o de pasarlos al LLM.

🧪 Troceamos el corpus de Políglota en ventanas de $w$ palabras (sin solapamiento, y $w$ = 32 con 50 % de solapamiento), embebemos cada chunk con v2 y con BM25 sobre chunks, agregamos a documento con MaxP y FirstP y medimos nDCG@10 a nivel de documento frente al documento entero.''')
    nb.code(r'''
def trocea(texto, w, solape=0):
    p = texto.split(); paso = max(w - solape, 1)
    return [" ".join(p[i:i + w]) for i in range(0, max(len(p) - solape, 1), paso)] or [texto]

def agrega(Sc, dueno, primero):
    """Score de documento = máximo de sus chunks (MaxP) o el de su primer chunk (FirstP)."""
    S = np.full((Sc.shape[0], len(doc_ids)), -1e9)
    vistos = set()
    for j, d in enumerate(dueno):
        if primero and d in vistos:
            continue
        vistos.add(d); S[:, d] = np.maximum(S[:, d], Sc[:, j])
    return S

filas_ch = [{"w": "doc entero", "vectores/doc": 1.0, "denso MaxP": nd(Q2 @ D2.T), "denso FirstP": nd(Q2 @ D2.T), "BM25 MaxP": nd(S_BM25)}]
for w, sol in ((16, 0), (32, 0), (32, 16), (64, 0), (128, 0)):
    ch, dueno = [], []
    for i, t in enumerate(doc_texts):
        for c in trocea(t, w, sol):
            ch.append(c); dueno.append(i)
    Sd = Q2 @ l2n(VERS["v2"].encode_docs(ch)).T
    bm_c = BM25().fit([tokenize_simple(c) for c in ch], [f"c{j}" for j in range(len(ch))])
    Sb = np.array([bm_c.scores(tokenize_simple(q)) for q in q_texts])
    filas_ch.append({"w": f"{w}" + (f" (solape {sol})" if sol else ""), "vectores/doc": len(ch) / len(doc_texts),
                     "denso MaxP": nd(agrega(Sd, dueno, False)), "denso FirstP": nd(agrega(Sd, dueno, True)),
                     "BM25 MaxP": nd(agrega(Sb, dueno, False))})
df_ch = pd.DataFrame(filas_ch)
fig, ax = plt.subplots(figsize=(9, 4)); x = np.arange(len(df_ch))
for j, (col, c) in enumerate((("denso MaxP", AZUL), ("denso FirstP", GRIS), ("BM25 MaxP", NARANJA))):
    ax.bar(x + (j - 1) * .27, df_ch[col], .27, color=c, label=col)
ax.set_xticks(x); ax.set_xticklabels([f"{a}\n×{v:.1f} vect." for a, v in zip(df_ch.w, df_ch["vectores/doc"])], fontsize=8)
ax.set_xlabel("tamaño de chunk w (palabras) · vectores por documento"); ax.set_ylabel("nDCG@10 (documento)")
ax.set_title("Chunking: calidad frente a tamaño del índice"); ax.set_ylim(0, 1.05); ax.legend(fontsize=8); plt.tight_layout(); plt.show()
df_ch.round(3)
''')
    nb.md(r'''> 👀 **Qué debes observar** (cifras de la ejecución de referencia, respaldo SVD + corpus sintético): (1) los chunks **muy cortos** hunden al denso (w = 16: 0.742 frente a 0.861 del documento entero) y multiplican el índice por ≈ 7: un trozo de 16 palabras ya no contiene el tema. (2) **No hay agregación universal**: con w = 16 MaxP gana a FirstP (0.742 frente a 0.695), pero con w = 64 gana FirstP (0.881 frente a 0.863), porque estos documentos definen su tema en la primera frase (como un artículo de Wikipedia); es el mismo resultado mixto que Dai & Callan encontraron entre Robust04 y ClueWeb09. (3) BM25 sobre chunks medianos supera al documento entero (0.874 frente a 0.861 con w = 64): la normalización por longitud trata mejor trozos homogéneos. (4) El **solapamiento** (w = 32, solape 16) no mejora aquí y multiplica el índice por 1.6 frente a sin solape. Con un encoder real y documentación de miles de palabras los números cambian; la regla de playbook no es un tamaño: es **medir el chunking como cualquier otra decisión** (en dev, con nDCG al nivel de lo que consume el usuario y la memoria al lado) y deduplicar por documento.''')

    # ─────────────── §5 Fallos reales ───────────────
    nb.md(r'''## 5. Fallos reales documentados (y su reproducción mínima)
| Fallo | Qué pasó | Fuente | Módulo |
|---|---|---|---|
| Tokens «glitch» (SolidGoldMagikarp) | tokens del vocabulario casi ausentes del entrenamiento del modelo producen comportamiento anómalo | Rumbelow & Watkins 2023 (LessWrong); Land & Bartolo 2024 (arXiv:2405.05417) | 05 |
| Aritmética sensible a la tokenización de números | la dirección de troceo de dígitos (L2R vs R2L) cambia la exactitud | Singh & Strouse 2024 (arXiv:2402.14903) | 04–05 |
| Prima de tokens por idioma | el mismo contenido cuesta varias veces más tokens en algunos idiomas | Petrov et al. 2023 (arXiv:2305.15425); Ahia et al. 2023 (arXiv:2305.13707) | 04 |
| Trojan Source / caracteres invisibles | Unicode bidi e invisibles hacen que lo que ves no sea lo que se procesa | Boucher & Anderson 2021 (arXiv:2111.00169) | 01, 05 |
| Retrievers densos frágiles fuera de dominio | en BEIR, BM25 supera a muchos densos zero-shot | Thakur et al. 2021 (arXiv:2104.08663) | 00, 15 |
| Límite de dimensión | hay conjuntos top-k que un embedding de dimensión fija no puede representar | Weller et al. 2025 (arXiv:2508.21038) | 15 |
| Inversión de embeddings | los vectores permiten reconstruir el texto | Morris et al. 2023 (arXiv:2310.06816) | 17–18 |
| Contexto largo en RAG | los LLMs usan peor la información en mitad del contexto | Liu et al. 2023 (arXiv:2307.03172) | 13, 20 |

Los fallos de **ingeniería** más frecuentes no salen en papers porque son silenciosos. Reproducimos cuatro con el corpus de Políglota (todos dan resultados «razonables», ninguno lanza una excepción):''')
    nb.code(r'''
rng = np.random.default_rng(SEED)
sano = {"denso v2": nd(Q2 @ D2.T), "BM25": nd(S_BM25)}
rotos = {}
# F1 · Truncado silencioso al indexar (max_seq_length corto; aquí 200 caracteres)
rotos["F1 truncado al indexar"] = ("denso v2", nd(Q2 @ VERS["v2"].encode_docs([t[:200] for t in doc_texts]).T))
# F2 · Producto punto con vectores NO normalizados cuya norma crece con la longitud del documento
L = np.array([len(t) for t in doc_texts], float)
rotos["F2 dot sin normalizar"] = ("denso v2", nd(Q2 @ (D2 * np.sqrt(L / L.mean())[:, None]).T))
# F3 · Tokenización distinta al indexar (quita tildes) y al consultar (las conserva)
bm_fold = BM25().fit([tokenize_simple(t, accents="fold") for t in doc_texts], doc_ids)
rotos["F3 tildes: índice≠query"] = ("BM25", nd(np.array([bm_fold.scores(tokenize_simple(q)) for q in q_texts])))
# F4 · Caché sin versión tras reentrenar (rotación ortogonal = mismo modelo, otro espacio; módulo 18)
Rm, _ = np.linalg.qr(rng.normal(size=(D2.shape[1],) * 2))
rotos["F4 caché sin versión"] = ("denso v2", nd(Q2 @ (D2 @ Rm).T))
fig, ax = plt.subplots(figsize=(9, 4))
nombres = list(rotos); x = np.arange(len(nombres))
ax.bar(x - .2, [sano[rotos[n][0]] for n in nombres], .4, color=AZUL, label="sano")
ax.bar(x + .2, [rotos[n][1] for n in nombres], .4, color=ROJO, label="con el fallo")
ax.set_xticks(x); ax.set_xticklabels(nombres, fontsize=8); ax.set_ylabel("nDCG@10"); ax.set_title("Galería de fallos silenciosos (corpus Políglota)")
ax.legend(); plt.tight_layout(); plt.show()
print({n: f"{sano[s]:.3f} → {v:.3f}" for n, (s, v) in rotos.items()})
''')
    nb.md(r'''> 👀 **Qué debes observar:** F1–F3 cuestan unos pocos puntos de nDCG: lo bastante para perder un A/B, demasiado poco para que alguien abra un incidente. F4 hunde la calidad a cero, pero solo para las queries servidas desde caché (en producción: las más populares). Ninguno lanza excepciones; todos se detectan con **tests de contrato** (misma normalización/tokenización en ambos lados, norma de los vectores ≈ 1, versión en la clave) y con un golden set ejecutado en CI.''')

    # ─────────────── §6 Checklist ───────────────
    nb.md(r'''## 6. Checklist de revisión de PRs (ejecutable)
La checklist humana (para la descripción del PR):
1. **Contrato de versión**: ¿cambia modelo, checkpoint, servidor, normalización, truncado, prefijos o chunking? → es una **migración** (módulo 18), no un PR normal.
2. **Simetría**: misma normalización Unicode y tokenización en indexación y consulta; prefijos `query:`/`passage:` correctos.
3. **Vectores**: normalizados si la métrica es coseno/producto; dimensión y dtype comprobados al cargar.
4. **Evaluación**: golden set con test ciego, IC pareado vs producción, slices por idioma; hiperparámetros elegidos fuera del test.
5. **Coste y latencia**: tokens/s medidos, p99 con batch = 1, memoria proyectada a N de producción.
6. **Privacidad**: ¿se envía texto a terceros? ¿los vectores nuevos heredan la clasificación? ¿el borrado se propaga?
7. **Rollback**: alias o flag para volver atrás en minutos.

Y su versión ejecutable: un *linter* sobre la configuración que acompaña al PR.''')
    nb.code(r'''
REGLAS = [
    ("ALTA", "versión fuera de la clave de caché", lambda c: not c.get("version_en_clave_cache", False)),
    ("ALTA", "normalización Unicode distinta en índice y query", lambda c: c.get("norm_indice") != c.get("norm_query")),
    ("ALTA", "hiperparámetros elegidos en el test", lambda c: c.get("tuning_split") == "test"),
    ("ALTA", "cambio de modelo sin plan de migración (alias/rollback)", lambda c: c.get("cambia_modelo") and not c.get("plan_rollback")),
    ("MEDIA", "vectores sin normalizar con métrica coseno/IP", lambda c: c.get("metrica") in ("cos", "ip") and not c.get("normaliza", False)),
    ("MEDIA", "max_seq_length < percentil 95 de longitud de los chunks", lambda c: c.get("max_seq_len", 1e9) < c.get("p95_tokens_chunk", 0)),
    ("MEDIA", "sin IC pareado contra producción", lambda c: not c.get("ic_pareado", False)),
    ("MEDIA", "sin desglose por idioma/slice", lambda c: not c.get("slices", False)),
    ("BAJA", "prefijos query/passage ausentes en un modelo que los requiere", lambda c: c.get("modelo_requiere_prefijos") and not c.get("usa_prefijos")),
    ("BAJA", "texto enviado a API externa sin revisión de residencia", lambda c: c.get("api_externa") and not c.get("revision_privacidad")),
]

def revisa_pr(config: dict) -> pd.DataFrame:
    hall = [{"severidad": s, "hallazgo": m} for s, m, regla in REGLAS if regla(config)]
    return pd.DataFrame(hall) if hall else pd.DataFrame([{"severidad": "—", "hallazgo": "sin hallazgos ✅"}])

PR_123 = dict(cambia_modelo=True, plan_rollback=False, version_en_clave_cache=False, norm_indice="NFC", norm_query="ninguna",
              tuning_split="test", metrica="ip", normaliza=True, max_seq_len=128, p95_tokens_chunk=310, ic_pareado=False, slices=True,
              modelo_requiere_prefijos=True, usa_prefijos=True, api_externa=False)
PR_124 = dict(cambia_modelo=True, plan_rollback=True, version_en_clave_cache=True, norm_indice="NFC", norm_query="NFC", tuning_split="dev",
              metrica="cos", normaliza=True, max_seq_len=512, p95_tokens_chunk=310, ic_pareado=True, slices=True,
              modelo_requiere_prefijos=True, usa_prefijos=True, api_externa=True, revision_privacidad=True)
print("PR #123"); display(revisa_pr(PR_123)); print("PR #124"); display(revisa_pr(PR_124))
''')

    # ─────────────── §7 Cultura ───────────────
    nb.md(r'''## 7. Cultura de laboratorios y equipos top (lo que se repite)
Sin atribuir prácticas internas que no están publicadas, lo que sí se lee en sus papers, informes técnicos y blogs de ingeniería:
* **La evaluación se escribe antes que el modelo**: golden set, slices y criterio de aceptación fijados de antemano (los informes de MTEB/MMTEB, BEIR y los *technical reports* de embedders publican por tarea e idioma, no un único número).
* **Baselines fuertes y honestos**: BM25 bien configurado, el modelo de producción actual, y la versión «sin el truco». Una mejora sin baseline fuerte no es una mejora.
* **Ablaciones de una variable** y semillas múltiples con IC: si el efecto es menor que la varianza entre semillas, no hay efecto.
* **Mirar los datos**: leer 50 errores antes de cambiar la arquitectura (el análisis por slices del módulo 15 es la versión sistemática).
* **Documentos de diseño y post-mortems sin culpables**: las decisiones (§1) se escriben con sus alternativas y se revisan cuando una medición las contradice.
* **Etiquetar la madurez**: separar lo sólido de lo prometedor (🟢/🟡/🔴) es parte del rigor, no una opinión.

Ninguna de estas prácticas es un consejo suelto: cada una ya la **ejecutaste** en este notebook. Evaluación antes que el modelo → criterios de aceptación del capstone (módulo 20, §1); baselines fuertes → BM25 en T3 y en `elige_hibrido`; ablaciones con IC → T1–T2; mirar los datos → F1–F4 de §5; documentos de diseño → los tres casos del proyecto. Úsala como índice para repasar, no como lista para memorizar.
''')
    nb.md(r'''## 🗺️ Mapa de madurez (a oct-2026) de las decisiones de este playbook
Has aplicado ya cada decisión con números; la tabla dice cuáles de esas reglas descansan en evidencia consolidada y cuáles son apuestas razonables que conviene volver a medir.

🟢 sólido · 🟡 emergente · 🔴 experimental.

| Decisión / técnica | Madurez | Quién la usa (respaldado) | Fuente |
|---|---|---|---|
| BM25 como baseline obligatorio | 🟢 | BEIR lo mostró fuerte fuera de dominio | Thakur et al. 2021 |
| Fusión híbrida (RRF / lineal) | 🟢 | Elasticsearch/OpenSearch, Qdrant, Weaviate, Vespa | Cormack et al. 2009; Bruch et al. 2022 |
| Reranker cross-encoder en 2ª etapa | 🟢 | práctica estándar en búsqueda y RAG | Nogueira & Cho 2019 |
| Bi-encoder multilingüe abierto + fine-tuning de dominio | 🟢 | e5, BGE-M3, Qwen3-Embedding, EmbeddingGemma | módulos 11–12 |
| HNSW en RAM / IVF-PQ / DiskANN en SSD | 🟢 | FAISS, Lucene, pgvector, Qdrant, DiskANN | módulo 14 |
| Cuantización binaria + rescoring | 🟡 | sentence-transformers, varias vector DBs | Shakir et al. 2024 |
| Late interaction (ColBERT/PLAID/MUVERA) | 🟡 | ColBERTv2, PLAID; MUVERA (Google Research) | módulo 13 |
| LLM-as-judge para qrels | 🟡 | útil con validación humana; sesgos conocidos | Thomas et al. 2023; Soboroff 2024 |
| Tokenizer-free (BLT, H-Net) para retrieval | 🔴 | investigación | módulos 06–07 |
| Límites de dimensión (LIMIT) como criterio de diseño | 🟡 | — | Weller et al. 2025 |
''')
    nb.md(r'''## 🏭 En producción
* **Fusión híbrida** como opción de primera clase: RRF disponible en Elasticsearch/OpenSearch y en vector DBs como Qdrant y Weaviate (documentación oficial); Bruch et al. (2022) analizan cuándo la combinación convexa supera a RRF.
* **Reranking en dos etapas**: el patrón retrieve → rerank (Nogueira & Cho 2019) sigue siendo la forma estándar de gastar cómputo donde importa; el presupuesto de latencia fija K (§1, `elige_hibrido`).
* **Evaluación con humanos + LLM**: los juicios con LLM aceleran el pooling, pero su validez depende de calibrarlos con humanos (Thomas et al. 2023 frente a Soboroff 2024).
* **Interleaving online** para cribar y A/B para confirmar (Chapelle et al. 2012; Kohavi et al. 2020).
* **Costes**: la memoria por réplica domina a gran escala; la cuantización (int8/binaria + rescoring) y Matryoshka son las palancas principales (módulos 12 y 18).
''')
    nb.md(r'''## 🧠 Secretos de la élite
1. **Un umbral sin medición es una opinión**: `N_FLAT_MAX` sale de §1 en *tu* hardware; los árboles de decisión se versionan y se testean como código.
2. **El optimismo por selección es proporcional a cuántas cosas probaste**: reporta cuántas configuraciones evaluaste y usa test ciego (T1, T2).
3. **Los qrels tienen dueño**: si los construyó el sistema viejo, el nuevo parte con desventaja (T4); juzga los documentos nuevos del top-k antes de concluir.
4. **Pondera por tráfico, reporta el peor slice**: la media del golden set no es tu producto (§3).
5. **Los fallos caros son silenciosos**: tests de contrato (normalización, tokenización, norma, versión) en CI, no solo métricas (§5).
6. **A gran escala la arquitectura la decide la memoria por réplica**, no la calidad del embedder (§4).
7. **Sospecha de mejoras < IC**: si la diferencia pareada no excluye el 0, la respuesta correcta a «¿cuál es mejor?» es «no lo sabemos todavía».
8. **El tamaño de chunk es un hiperparámetro con factura**: fija $N$ (memoria, coste, latencia) y la calidad a la vez, y la agregación (MaxP/FirstP) depende de dónde está la información en tus documentos (§4b). Se elige en dev como la fusión o la dimensión, nunca por la cifra «512 tokens con 10 % de solape» de un tutorial.
''')
    nb.md(r'''## ⚠️ Errores comunes
* Elegir arquitectura por popularidad («todos usan HNSW») en vez de por N, memoria, filtros y actualizaciones.
* Comparar sistemas con golden sets distintos, o con un golden set construido a partir de uno de ellos.
* Reportar el mejor de N experimentos sin decir N.
* Optimizar nDCG@10 cuando la interfaz muestra 3 resultados.
* Calcular el coste de embedding y olvidar la memoria mensual por réplica.
* Revisar PRs de embeddings como si fueran PRs de código normal (sin contrato de versión ni evaluación pareada).
''')
    nb.md(r'''## 📝 Autoevaluación
<details><summary><b>1 · (Cálculo)</b> 200 M de chunks, d = 1024. ¿RAM por réplica para float32, int8 y binario (sin grafo)? ¿Cuál eliges con 128 GB por máquina?</summary>

float32: $2\cdot10^8 \cdot 4096$ B = **819 GB**; int8: **205 GB**; binario: **25.6 GB**. Con 128 GB solo cabe binario (+ grafo) en una réplica: binario en RAM + rescore con int8/float en SSD, o DiskANN; Matryoshka a 512 d reduce todo a la mitad.
</details>
<details><summary><b>2 · (Diagnóstico)</b> Tu nuevo embedder gana +0.04 nDCG@10 en dev tras probar 40 configuraciones, y +0.005 en el test ciego. ¿Qué pasó?</summary>

*Winner's curse* (T2): la ganancia en dev era sobre todo ruido de selección entre 40 configuraciones. El número válido es el del test ciego, con su IC pareado; probablemente no excluye el 0.
</details>
<details><summary><b>3 · (Diagnóstico)</b> Los juicios de relevancia vienen del top-10 de BM25 de hace un año. El nuevo denso «pierde» 0.03. ¿Qué haces antes de descartarlo?</summary>

Sospechar sesgo de pooling (T4): juzgar (humanos o LLM validado) los documentos del top-10 del denso que no tienen juicio, y recalcular. Comparar también solo sobre queries cuyo pool incluye ambos sistemas.
</details>
<details><summary><b>4 · (Transferencia)</b> Un cliente tiene 30 k documentos, 5 QPS y exige on-prem. Aplica los árboles.</summary>

Índice: Flat exacto (N muy por debajo de `N_FLAT_MAX`, recall 1, sin mantenimiento). Embedder: open weights autohospedado, multilingüe y pequeño; fine-tuning solo si hay ≥ 1 k pares. Híbrido: BM25 + denso con RRF; reranker si el presupuesto lo permite. Lo caro aquí no es la infraestructura sino el golden set.
</details>
<details><summary><b>5 · (Transferencia)</b> ¿Qué regla añadirías al linter de PRs para el fallo F1 (truncado)? ¿Y para F2?</summary>

F1: `max_seq_len ≥ p95 de longitud de chunk en tokens del tokenizer del modelo` (ya está como MEDIA). F2: test de contrato que compruebe $\lVert v\rVert \approx 1$ en una muestra del índice si la métrica es IP/coseno, y que la norma no correlacione con la longitud.
</details>
<details><summary><b>6 · (Diagnóstico)</b> En T1, ¿por qué el número «honesto» de la CV no es el rendimiento del α final?</summary>

La CV estima el rendimiento esperado del **procedimiento** «elegir α en datos de entrenamiento»; el α final (elegido con todo) puede ser distinto en cada pliegue. Para reportar el α final hace falta un test que no se usó para elegirlo.
</details>
''')
    nb.md(r'''## 📚 Referencias
* Thakur, N. et al. (2021). *BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models*. NeurIPS 2021 (Datasets & Benchmarks). https://arxiv.org/abs/2104.08663
* Cormack, G., Clarke, C., Büttcher, S. (2009). *Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods*. SIGIR 2009.
* Bruch, S., Gai, S., Ingber, A. (2022). *An Analysis of Fusion Functions for Hybrid Retrieval*. ACM TOIS 42(1), 2023. https://arxiv.org/abs/2210.11934
* Dai, Z., Callan, J. (2019). *Deeper Text Understanding for IR with Contextual Neural Language Modeling*. SIGIR 2019. https://arxiv.org/abs/1905.09217
* Nogueira, R. & Cho, K. (2019). *Passage Re-ranking with BERT*. Preprint. https://arxiv.org/abs/1901.04085
* Weller, O., Boratko, M., Naim, I., Lee, J. (2025). *On the Theoretical Limitations of Embedding-Based Retrieval*. ICLR 2026. https://arxiv.org/abs/2508.21038
* Thomas, P. et al. (2023). *Large language models can accurately predict searcher preferences*. SIGIR 2024. https://arxiv.org/abs/2309.10621 · Soboroff, I. (2024). *Don't Use LLMs to Make Relevance Judgments*. Information Retrieval Research 1(1) (2025). https://arxiv.org/abs/2409.15133
* Smucker, M., Allan, J., Carterette, B. (2007). *A Comparison of Statistical Significance Tests for Information Retrieval Evaluation*. CIKM 2007.
* Land, S. & Bartolo, M. (2024). *Fishing for Magikarp: Automatically Detecting Under-trained Tokens in Large Language Models*. EMNLP 2024. https://arxiv.org/abs/2405.05417
* Singh, A. & Strouse, D. J. (2024). *Tokenization counts: the impact of tokenization on arithmetic in frontier LLMs*. Preprint. https://arxiv.org/abs/2402.14903
* Petrov, A. et al. (2023). *Language Model Tokenizers Introduce Unfairness Between Languages*. NeurIPS 2023. https://arxiv.org/abs/2305.15425
* Boucher, N. & Anderson, R. (2021). *Trojan Source: Invisible Vulnerabilities*. USENIX Security 2023. https://arxiv.org/abs/2111.00169
* Morris, J. X. et al. (2023). *Text Embeddings Reveal (Almost) As Much As Text*. EMNLP 2023. https://arxiv.org/abs/2310.06816
* Liu, N. F. et al. (2023). *Lost in the Middle: How Language Models Use Long Contexts*. TACL 12 (2024). https://arxiv.org/abs/2307.03172
* Chapelle, O. et al. (2012). *Large-scale validation and analysis of interleaved search evaluation*. ACM TOIS 30(1). · Kohavi, R., Tang, D., Xu, Y. (2020). *Trustworthy Online Controlled Experiments*. Cambridge UP.
* Patel, L. et al. (2024). *ACORN: Performant and Predicate-Agnostic Search Over Vector Embeddings and Structured Data*. SIGMOD 2024. https://arxiv.org/abs/2403.04871
* Material del curso: `extras/GUIA_ENTREVISTAS.md` (preguntas con respuestas modelo y rúbrica) y `extras/LECTURA_PAPERS.md` (lectura guiada por módulo).
''')
