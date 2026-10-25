"""Lección 20 · Capstone: Políglota completo (autor A7). La llama build_20.py."""
import _a7_common as C

CODE_CAPSTONE_TOOLS = r'''
import re
from tokenizers import Tokenizer, models, trainers, pre_tokenizers, decoders, normalizers

def split_estratificado(queries, frac_test: float = 0.5, seed: int = SEED):
    """dev / test CIEGO estratificado por idioma (módulo 15). Todo lo que se elige, se elige en dev."""
    rng = random.Random(seed); dev, test = [], []
    for lang in sorted({q["lang"] for q in queries}):
        grp = [q for q in queries if q["lang"] == lang]; rng.shuffle(grp)
        cut = int(round(len(grp) * frac_test)); test += grp[:cut]; dev += grp[cut:]
    return dev, test

DEV, TEST = split_estratificado(queries)
I_DEV = np.array([qids.index(q["qid"]) for q in DEV]); I_TEST = np.array([qids.index(q["qid"]) for q in TEST])
print(f"dev={len(DEV)} · test ciego={len(TEST)} queries (estratificado por idioma)")

def entrena_bpe(textos, vocab=4000):
    """BPE byte-level con HF tokenizers (módulos 02-03): NFC + ByteLevel + BPE."""
    tk = Tokenizer(models.BPE(unk_token=None)); tk.normalizer = normalizers.NFC()
    tk.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=True); tk.decoder = decoders.ByteLevel()
    tk.train_from_iterator(textos, trainers.BpeTrainer(vocab_size=vocab, initial_alphabet=pre_tokenizers.ByteLevel.alphabet(), show_progress=False))
    return tk

def tok_ident(texto: str) -> list[str]:
    """Analizador léxico de Políglota: palabras + partes de identificadores (snake_case / camelCase), módulos 00 y 13."""
    out = tokenize_simple(texto)
    for w in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", texto):
        partes = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+", w.replace("_", " "))
        if len(partes) > 1:
            out += [p.lower() for p in partes]
    return out

class EmbedderRecortado:
    """Toma las primeras `dim` coordenadas y renormaliza (Matryoshka; con el fallback SVD equivale a PCA truncada)."""
    def __init__(self, base, dim):
        self.base, self.dim, self.clave = base, dim, f"{base.clave} [:{dim}]"
    def encode_queries(self, t):
        return l2n(self.base.encode_queries(t)[:, :self.dim])
    def encode_docs(self, t):
        return l2n(self.base.encode_docs(t)[:, :self.dim])

def rrf_mat(*Ss, k=60):
    out = np.zeros_like(Ss[0], dtype=float)
    for S in Ss:
        out += 1.0 / (k + np.argsort(np.argsort(-S, axis=1, kind="stable"), axis=1, kind="stable") + 1)
    return out

def minmax(S):
    lo, hi = S.min(1, keepdims=True), S.max(1, keepdims=True)
    return (S - lo) / np.maximum(hi - lo, 1e-9)

def lineal_lista(S1, S2, a, prof=50):
    """Igual que el servicio: cada lista se corta a su top-`prof`, se normaliza min-max dentro de la lista y los docs
    fuera de una lista aportan 0 por ella. S1 = denso, S2 = BM25 (n_queries x n_docs)."""
    def norm(S):
        thr = -np.sort(-S, axis=1)[:, min(prof, S.shape[1]) - 1][:, None]
        Sc = np.maximum(S, thr)
        return (Sc - thr) / np.maximum(Sc.max(1, keepdims=True) - thr, 1e-9)
    return a * norm(S1) + (1 - a) * norm(S2)

def int8_ida_vuelta(D):
    """Cuantiza a int8 (calibrado por dimensión) y decodifica: simula la pérdida de precisión del índice."""
    lo, hi = np.quantile(D, 0.001, axis=0), np.quantile(D, 0.999, axis=0); esc = np.maximum(hi - lo, 1e-9) / 255
    return (np.clip(np.round((D - lo) / esc) - 128, -128, 127) + 128) * esc + lo

pq_S = lambda S: ndcg_por_query(run_desde_scores(S))      # nDCG@10 por query (orden de qids)
'''


def lesson(nb):
    nb.md(nb.badge() + r'''

# Módulo 20 · Capstone: Políglota completo

**Nivel:** 🔴 Experto · **Duración:** ≈ 6 h (lección ≈ 2.5 h + proyecto ≈ 3.5 h) · **GPU:** no necesaria en `FAST_DEV_RUN` (CPU, ≈ 2 min); T4/L4 para modelos reales y el corpus completo (≈ 1–3 unidades de Colab) · **Prerrequisitos:** módulos 00–19.

> 🧭 **Ruta núcleo vs ampliación.** Núcleo: §1 criterios de aceptación → §2–§5 decisiones por componente → §7 evaluación en test ciego → §8 informe. Ampliación: §6 servicio bajo carga y §9 multimodal opcional.

**Hilo conductor — Políglota v1.0.** Has construido cada pieza por separado: tokenizer (02–05), embedder (09–12), híbrido (13), índice (14), evaluación (15), multimodal (16), interpretabilidad (17), servicio (18) y criterios de diseño (19). Esta lección es la **solución de referencia del sistema completo**: integra las piezas en un pipeline, **decide cada componente con datos de dev**, evalúa una sola vez en un **test ciego** contra el baseline BM25 del módulo 00 y genera automáticamente el **informe técnico** con métricas, costos, latencia y criterios de aceptación. El proyecto te pide hacer lo mismo con tus propias decisiones.

> **Estado del arte a octubre de 2026.** Las piezas usadas son 🟢/🟡 (ver mapa de madurez). Las cifras de este notebook salen del corpus **sintético** + fallbacks si no hay acceso a Hugging Face: el *procedimiento* es el entregable; los números, de tu ejecución.
''')
    nb.md(r'''## 🎯 Objetivos de aprendizaje
1. **Definir** criterios de aceptación medibles *antes* de construir (calidad, latencia, memoria, costo).
2. **Integrar** tokenizer, analizador léxico, embedder, fusión híbrida, índice ANN y servicio en un pipeline reproducible.
3. **Decidir** cada componente en un split de desarrollo con reglas explícitas, sin tocar el test.
4. **Evaluar** una única vez en test ciego con IC pareados y desglose por idioma contra el baseline del módulo 00.
5. **Proyectar** memoria, costo y latencia a la escala de producción (10 M de chunks).
6. **Redactar** un informe técnico de decisiones (ADR) generado desde las métricas y verificar los criterios de aceptación.
''')
    nb.md(r'''## 🔁 Conexión con módulos anteriores
<details><summary><b>1 · (M15/M19)</b> ¿Por qué separamos dev y test ciego antes de empezar?</summary>

Porque todas las decisiones (vocabulario, dimensión, fusión, índice) son selecciones entre alternativas: si se eligen mirando el test, el número final es optimista (T1/T2 del módulo 19). El test se usa **una vez**, al final.
</details>
<details><summary><b>2 · (M04)</b> ¿Qué métricas reportamos siempre de un tokenizer?</summary>

Fertilidad (tokens/palabra) y bytes por token, por idioma, y la prima de paridad respecto al inglés.
</details>
<details><summary><b>3 · (M13)</b> ¿Por qué RRF es una buena opción por defecto para fusionar?</summary>

Usa solo rangos: no necesita calibrar scores de escalas distintas y no tiene pesos que ajustar (salvo $k$), así que no hay fuga de tuning. La combinación lineal puede ganar, pero hay que ajustarla con validación cruzada.
</details>
<details><summary><b>4 · (M18)</b> ¿Qué tres cosas deben ir en la «versión» de un vector?</summary>

Modelo/checkpoint, preprocesado (normalización, truncado, prefijo, dimensión y precisión) y servidor. Va en la clave de caché y en los metadatos del índice.
</details>
''')
    nb.md(r'''## 🗺️ Mapa de madurez de las piezas de Políglota v1.0 (a oct-2026)
| Pieza | Elección de referencia | Madurez | Fuente / módulo |
|---|---|---|---|
| Normalización | NFC en indexación y consulta | 🟢 | UAX #15 · M01 |
| Tokenizer (costo y contexto) | BPE byte-level (HF `tokenizers`) | 🟢 | Sennrich et al. 2016; Wang et al. 2019 · M02–M04 |
| Analizador léxico de BM25 | palabras + partes de identificadores | 🟢 | Robertson & Zaragoza 2009 · M00, M13 |
| Embedder | bi-encoder multilingüe (e5) o fallback; dimensión recortada (Matryoshka) | 🟢 / 🟡 (Matryoshka en modelos sin entrenarla) | Wang et al. 2024; Kusupati et al. 2022 · M10–M12 |
| Precisión del índice | int8 calibrado | 🟢 | Shakir et al. 2024 · M12 |
| Fusión | RRF (lineal solo si gana con IC) | 🟢 | Cormack et al. 2009; Bruch et al. 2022 · M13 |
| Índice | Flat o HNSW según el árbol de M19 | 🟢 | Malkov & Yashunin 2016; Douze et al. 2024 · M14 |
| Evaluación | test ciego, bootstrap pareado, slices | 🟢 | Smucker et al. 2007 · M15 |
| Multimodal (opcional) | OCR + texto; ColPali en 2ª etapa | 🟡 | Faysse et al. 2024 · M16 |
| Servicio | caché versionada + alias + FastAPI | 🟢 | M18 |
''')
    nb.gemini(
        "imagen", "M20-IMG-01", "Arquitectura de Políglota v1.0",
        "El sistema completo que se integra en el capstone, con cada caja etiquetada con el módulo del curso que la construyó.",
        """Diagrama de arquitectura técnico, fondo blanco, paleta sobria: azul #1F6FEB (ruta de consulta), naranja #F28E2B (ruta de indexación), verde #2CA02C (evaluación e informe), gris #6B7280 (almacenamiento). Sans-serif legible, flechas claras, cajas con esquinas suaves.
Arriba, de izquierda a derecha (naranja), título "Indexación": "Docs ES/EN + código" → "Normalización NFC (M01)" → "Chunking" → "Tokenizer BPE: costo y fertilidad (M02–M04)" → bifurcación en dos cajas: "BM25 · palabras + identificadores (M00, M13)" y "Embedder · dimensión recortada + int8 (M10–M12)" → cilindros grises "Índice invertido" y "Índice vectorial Flat/HNSW (M14)".
Abajo, de izquierda a derecha (azul), título "Consulta": "Usuario" → "API FastAPI /search (M18)" → "Caché LRU versionada (M18)" → flechas a los dos índices → "Fusión RRF (M13)" → "Top-10".
A la derecha, una columna verde: "Evaluación: dev para decidir · test ciego una vez · IC pareado · slices (M15, M19)" → "Informe técnico + criterios de aceptación (M20)".
Una caja punteada gris opcional junto al embedder: "Opcional: páginas/capturas → ColPali MaxSim en 2ª etapa (M16)".
Evita: logotipos, texto pequeño, iconos decorativos, cifras de rendimiento.""",
        "Arquitectura de Políglota v1.0 con la ruta de indexación arriba, la de consulta abajo y la evaluación e informe a la derecha; cada caja indica su módulo.",
        """
INDEXACIÓN: Docs → NFC(M01) → chunks → BPE(M02-04) → [BM25 palabras+ident (M00,M13)] [Embedder d recortada+int8 (M10-12)] → índices (M14)
CONSULTA  : Usuario → FastAPI(M18) → Caché versionada(M18) → BM25 + denso → RRF(M13) → top-10
EVALUACIÓN: dev decide · test ciego 1 vez · IC pareado · slices (M15,M19) → INFORME + criterios (M20)
""")
    nb.md("> 👀 **Qué debes observar:** no hay ninguna caja nueva: el capstone es **integración**. Lo nuevo es la columna verde: cada decisión de la izquierda se toma con datos de *dev* y se justifica en el informe.")

    nb.md("## 0. Preparación\nPiezas canónicas del curso, copiadas para que el notebook sea autocontenido: corpus, métricas y BM25 (módulo 00), estadística pareada (15), embedders con fallback (12), caché y servicio versionado (18).")
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

    # ─────────────── §1 Criterios ───────────────
    nb.md(r'''## 1. Criterios de aceptación (se fijan ANTES de construir)
Escribirlos primero evita mover la portería después. Son los de la CTO de Políglota Labs para la beta; los umbrales de latencia son para **CPU, 1 hilo, batch = 1** (en GPU/servidor real se re-calibran).''')
    nb.code(r'''
ACEPTACION = {
    "calidad_vs_bm25":   "nDCG@10 en test ≥ BM25 del módulo 00 y límite inferior del IC95 de la diferencia pareada > −0.03",
    "peor_slice":        "ningún idioma más de 0.05 por debajo de BM25 en test",
    "recall_ann":        "neighbor recall@10 del índice elegido ≥ 0.95 frente a fuerza bruta",
    "latencia_p99_ms":   "p99 del servicio ≤ 50 ms (CPU, batch=1)",
    "ram_10M_gb":        "RAM del índice para 10 M de chunks ≤ 16 GB por réplica",
    "coste_reembed_usd": "re-embedding de 10 M chunks × 400 tokens ≤ 500 $ (API a 0.02 $/1M, oct-2026)",
    "hit_rate":          "hit rate de la caché con tráfico Zipf ≥ 0.70",
}
DECISIONES, METRICAS = {}, {}          # se rellenan sección a sección y alimentan el informe
pd.DataFrame(ACEPTACION.items(), columns=["criterio", "umbral"])
''')

    # ─────────────── §2 Tokenizer ───────────────
    nb.md(r'''## 2. Tokenizer: costo por idioma y ¿sirve como analizador de BM25?
El tokenizer de Políglota cumple dos papeles distintos que no conviene confundir:
1. **Costo y contexto**: cuántos tokens paga cada idioma (fertilidad, bytes/token) → presupuesto de embedding y de contexto en RAG.
2. **Analizador léxico** para BM25: aquí no se busca comprimir, sino que los términos de la query coincidan con los del documento.

Entrenamos BPE byte-level con HF `tokenizers` (módulos 02–03) con varios tamaños de vocabulario sobre los documentos.''')
    nb.code(r'''
VOCABS = [1000, 2000, 4000, 8000]
TK = {V: entrena_bpe(doc_texts, V) for V in VOCABS}
filas = []
for V, tk in TK.items():
    for l in ("es", "en", "code"):
        tx = [d["text"] for d in docs if d["lang"] == l]
        n_tok = sum(len(tk.encode(t).ids) for t in tx)
        filas.append({"vocab": V, "lang": l, "fertilidad": n_tok / sum(len(t.split()) for t in tx),
                      "bytes_por_token": sum(len(t.encode()) for t in tx) / n_tok})
df_tok = pd.DataFrame(filas)
fig, axs = plt.subplots(1, 2, figsize=(11, 3.8))
for l, c in zip(("es", "en", "code"), (AZUL, NARANJA, VERDE)):
    d = df_tok[df_tok.lang == l]
    axs[0].plot(d.vocab, d.fertilidad, "o-", color=c, label=l); axs[1].plot(d.vocab, d.bytes_por_token, "o-", color=c, label=l)
for ax, t in zip(axs, ("fertilidad (tokens/palabra)", "bytes por token")):
    ax.set_xscale("log", base=2); ax.set_xlabel("tamaño de vocabulario"); ax.set_ylabel(t); ax.legend()
axs[0].set_title("Fertilidad por idioma"); axs[1].set_title("Compresión por idioma"); plt.tight_layout(); plt.show()
df_tok.pivot(index="vocab", columns="lang", values="fertilidad").round(2)
''')
    nb.md(r'''> 👀 **Qué debes observar:** el código paga muchos más tokens por «palabra» que ES/EN (identificadores, símbolos, indentación) y la brecha se cierra despacio al crecer el vocabulario; ES y EN quedan cerca porque el corpus está equilibrado (en tokenizers entrenados mayoritariamente en inglés, el español paga más, módulo 04). Esta tabla es la que convierte tokens en $ en el informe.

Ahora el segundo papel: comparamos tres analizadores para BM25 **en dev**.''')
    nb.code(r'''
TK_SEL = TK[4000]
analizadores = {"palabras (módulo 00)": tokenize_simple, "palabras + identificadores": tok_ident,
                "BPE 4k (tokens del LLM)": lambda s: [t.lower() for t in TK_SEL.encode(s).tokens]}
S_LEX, filas = {}, []
for nombre, f in analizadores.items():
    bm = BM25().fit([f(t) for t in doc_texts], doc_ids)
    S_LEX[nombre] = (bm, f, np.array([bm.scores(f(q)) for q in q_texts]))
    pq = pq_S(S_LEX[nombre][2])[I_DEV]
    filas.append({"analizador": nombre, "dev nDCG@10": pq.mean(), **{l: pq[q_lang[I_DEV] == l].mean() for l in ("es", "en", "code")}})
df_lex = pd.DataFrame(filas)
mejor_lex = df_lex.sort_values("dev nDCG@10", ascending=False).iloc[0]["analizador"]
DECISIONES["analizador_bm25"] = mejor_lex
DECISIONES["tokenizer_costo"] = "BPE byte-level 4k (HF tokenizers), solo para presupuesto de tokens"
print("elegido en dev:", mejor_lex)
df_lex.round(3)
''')
    nb.md(r'''> 👀 **Qué debes observar:** los tokens de un BPE de LLM **no** son un buen analizador léxico: trocean palabras en piezas que coinciden por azar entre documentos no relacionados, y BM25 pierde. Partir identificadores (`split_ident`) es lo que ayuda en código. Decisión de ingeniería: el tokenizer del LLM se usa para **costos**, y BM25 usa su propio analizador. (El embedder trae su propio tokenizer: no se cambia sin *tokenizer transfer*, módulo 07.)''')

    # ─────────────── §3 Embedder ───────────────
    nb.md(r'''## 3. Embedder: modelo, dimensión y precisión (decididos en dev)
Regla de decisión escrita antes de mirar: **(1)** modelo con mejor nDCG@10 en dev si el IC pareado excluye el 0 (si no, el más barato); **(2)** la **menor** dimensión cuya pérdida frente a la completa sea ≤ 0.01; **(3)** int8 si pierde ≤ 0.01 frente a float32.''')
    nb.code(r'''
pq_v = {v: pq_S(EMB[v]["Q"] @ EMB[v]["D"].T)[I_DEV] for v in EMB}
r = paired_bootstrap(pq_v["v2"], pq_v["v1"])
modelo = "v2" if r["ci_low"] > 0 else "v1"
print(f"v2 − v1 en dev: Δ={r['diff']:+.3f} IC95=[{r['ci_low']:+.3f},{r['ci_high']:+.3f}] → modelo = {modelo}")
D_full, Q_full = EMB[modelo]["D"], EMB[modelo]["Q"]
dims = [d for d in (16, 32, 48, 64, 96, 128, 256, 384, 512, 768, 1024) if d <= D_full.shape[1]]
nd_dim = {d: pq_S(l2n(Q_full[:, :d]) @ l2n(D_full[:, :d]).T)[I_DEV].mean() for d in dims}
dim = min(d for d in dims if nd_dim[d] >= nd_dim[dims[-1]] - 0.01)
D_dim, Q_dim = l2n(D_full[:, :dim]), l2n(Q_full[:, :dim])
nd_i8 = pq_S(Q_dim @ int8_ida_vuelta(D_dim).T)[I_DEV].mean()
precision = "int8" if nd_i8 >= nd_dim[dim] - 0.01 else "float32"
D_sel = int8_ida_vuelta(D_dim) if precision == "int8" else D_dim
DECISIONES.update(modelo=VERS[modelo].clave, dim=dim, precision=precision)
METRICAS.update(dev_nd_dim=nd_dim, dev_nd_int8=nd_i8)
fig, ax = plt.subplots(figsize=(7.5, 4))
ax.plot(list(nd_dim), list(nd_dim.values()), "o-", color=AZUL, label="float32")
ax.scatter([dim], [nd_i8], color=NARANJA, s=80, zorder=3, label=f"int8 a d={dim}")
ax.axhline(nd_dim[dims[-1]] - 0.01, color=GRIS, ls="--", label="tolerancia: completa − 0.01")
ax.set_xscale("log", base=2); ax.set_xlabel("dimensión (primeras d coordenadas, renormalizadas)"); ax.set_ylabel("nDCG@10 en dev")
ax.set_title(f"Dimensión y precisión del embedder ({modelo})"); ax.legend(fontsize=8); plt.tight_layout(); plt.show()
print(f"decisión: d={dim}, {precision} · bytes/vector = {dim * (1 if precision == 'int8' else 4)}")
''')
    nb.md(r'''> 👀 **Qué debes observar:** la curva sube rápido y se aplana: las últimas dimensiones aportan poco, así que la regla elige una dimensión menor que la completa con pérdida acotada, e int8 apenas cambia el nDCG. ⚠️ Con el fallback (SVD), recortar equivale a una PCA y funciona por construcción; con un modelo real **solo** es seguro si se entrenó con Matryoshka (módulo 12): mide siempre.''')

    # ─────────────── §4 Híbrido ───────────────
    nb.md(r'''## 4. Fusión híbrida: RRF vs combinación lineal (en dev, con CV)
Regla: **RRF** por defecto; **lineal** solo si su estimación por validación cruzada en dev supera a RRF con un IC pareado que excluye el 0 (la simplicidad tiene valor: RRF no tiene pesos que se desajusten cuando cambie el embedder).''')
    nb.code(r'''
bm_sel, tok_sel, S_lex = S_LEX[mejor_lex]
S_den = Q_dim @ D_sel.T
cands = {"solo BM25": S_lex, "solo denso": S_den, "RRF": rrf_mat(S_den, S_lex)}
alfas = np.linspace(0, 1, 21)
PQa = np.array([pq_S(lineal_lista(S_den, S_lex, a))[I_DEV] for a in alfas])   # misma normalización que el servicio
pl = np.array_split(np.random.default_rng(SEED).permutation(len(I_DEV)), 5); lin_cv = np.zeros(len(I_DEV))
for f in pl:
    tr = np.setdiff1d(np.arange(len(I_DEV)), f); lin_cv[f] = PQa[PQa[:, tr].mean(1).argmax(), f]
pq_dev = {k: pq_S(S)[I_DEV] for k, S in cands.items()}; pq_dev["lineal (CV)"] = lin_cv
r = paired_bootstrap(lin_cv, pq_dev["RRF"])
fusion = "lineal" if r["ci_low"] > 0 else "RRF"
ALFA = float(alfas[PQa.mean(1).argmax()])
DECISIONES.update(fusion=fusion, alfa_lineal=ALFA if fusion == "lineal" else None)
METRICAS["fusion_delta"] = r
fig, ax = plt.subplots(figsize=(7.5, 3.8))
nombres = list(pq_dev); vals = [pq_dev[k].mean() for k in nombres]; cis = [bootstrap_ci(pq_dev[k]) for k in nombres]
ax.bar(nombres, vals, color=[GRIS, AZUL, VERDE, NARANJA], yerr=[[v - c[1] for v, c in zip(vals, cis)], [c[2] - v for v, c in zip(vals, cis)]], capsize=4)
ax.set_ylabel("nDCG@10 en dev (IC95)"); ax.set_title("Fusión híbrida en dev"); ax.set_ylim(min(vals) - .15, 1.0); plt.tight_layout(); plt.show()
print(f"lineal(CV) − RRF: Δ={r['diff']:+.3f} IC95=[{r['ci_low']:+.3f},{r['ci_high']:+.3f}] → fusión = {fusion}")
''')
    nb.md(r'''> 👀 **Qué debes observar:** el híbrido mejora (o iguala) al mejor componente. La barra «lineal (CV)» es una estimación **honesta** (cada pliegue se puntúa con el α elegido en los otros cuatro) y usa la **misma normalización que el servicio** (min-max dentro del top-50 de cada lista): si esa estimación supera a RRF con un IC que excluye el 0, la regla elige lineal y el servicio la implementa con el α ajustado en todo dev; si el IC incluye el 0, RRF: no pagues complejidad por una mejora que no puedes demostrar. Con un embedder neuronal real, cuyos scores están mejor calibrados que los del fallback, el resultado de esta comparación puede cambiar: por eso es una regla y no una constante.''')

    # ─────────────── §5 Índice ───────────────
    nb.md(r'''## 5. Índice: elegir con el árbol del módulo 19 y verificar recall
Con 400 documentos todo es trivial. Para tomar una decisión realista, ampliamos los vectores elegidos con **copias ruidosas** hasta $N$ = 20 000 (como el proyecto 14), medimos Flat vs HNSW y **proyectamos** memoria a 10 M de chunks.''')
    nb.code(r'''
rng = np.random.default_rng(SEED)
N_SIM = 20_000 if FAST_DEV_RUN else 200_000
base = D_sel[rng.integers(0, len(D_sel), N_SIM)]
X = l2n(base + 0.35 * rng.normal(size=base.shape).astype(np.float32) / np.sqrt(dim))
Qx = Q_dim[I_DEV]
flat = faiss.IndexFlatIP(dim); flat.add(X); gt = flat.search(Qx, 10)[1]
def mide(idx, Q, params=None):
    t = []
    for q in Q:
        t0 = time.perf_counter(); idx.search(q[None], 10, params=params); t.append((time.perf_counter() - t0) * 1e3)
    return float(np.percentile(t, 50)), float(np.percentile(t, 99))
filas = [{"índice": "Flat", "ef": None, "recall@10": 1.0, **dict(zip(("p50_ms", "p99_ms"), mide(flat, Qx)))}]
hnsw = faiss.IndexHNSWFlat(dim, 32, faiss.METRIC_INNER_PRODUCT); hnsw.hnsw.efConstruction = 80; hnsw.add(X)
for ef in (16, 32, 64, 128):
    p = faiss.SearchParametersHNSW(efSearch=ef); got = hnsw.search(Qx, 10, params=p)[1]
    filas.append({"índice": "HNSW M=32", "ef": ef, "recall@10": float(np.mean([len(set(a) & set(b)) / 10 for a, b in zip(gt, got)])),
                  **dict(zip(("p50_ms", "p99_ms"), mide(hnsw, Qx, p)))})
df_ann = pd.DataFrame(filas)
ok = df_ann[(df_ann["índice"] != "Flat") & (df_ann["recall@10"] >= 0.95)]
fila_hnsw = ok.sort_values("p99_ms").iloc[0] if len(ok) else df_ann.iloc[-1]
bpv = dim * (1 if precision == "int8" else 4)
ram_10M = {"Flat": 1e7 * bpv / 1e9, "HNSW": 1e7 * (bpv + 256) / 1e9}
DECISIONES.update(indice=f"HNSW M=32 efSearch={int(fila_hnsw.ef)}", ef_search=int(fila_hnsw.ef))
METRICAS.update(recall_ann=float(fila_hnsw["recall@10"]), ram_10M_gb=ram_10M["HNSW"])
fig, ax = plt.subplots(figsize=(7.5, 4))
h = df_ann[df_ann["índice"] != "Flat"]
ax.plot(h["recall@10"], h["p99_ms"], "o-", color=AZUL, label="HNSW (ef = 16…128)")
for _, rr in h.iterrows():
    ax.annotate(f"ef={int(rr.ef)}", (rr["recall@10"], rr["p99_ms"]), xytext=(4, 4), textcoords="offset points", fontsize=8)
ax.scatter([1.0], [df_ann.iloc[0]["p99_ms"]], color=NARANJA, s=80, label="Flat (exacto)"); ax.axvline(0.95, color=ROJO, ls="--", label="recall ≥ 0.95")
ax.set_xlabel("neighbor recall@10"); ax.set_ylabel("p99 (ms, batch=1)"); ax.set_title(f"Índice: N={N_SIM:,}, d={dim}"); ax.legend(fontsize=8)
plt.tight_layout(); plt.show()
print(f"RAM proyectada a 10 M ({precision}, d={dim}): Flat {ram_10M['Flat']:.1f} GB · HNSW {ram_10M['HNSW']:.1f} GB")
df_ann.round(3)
''')
    nb.md(r'''> 👀 **Qué debes observar:** HNSW alcanza el recall exigido con un `efSearch` moderado y su p99 casi no depende de $N$, mientras que Flat crece lineal (módulo 19, §1). Con 10 M de chunks, la dimensión y precisión elegidas en §3 deciden si el índice cabe en una réplica: por eso la decisión del embedder y la del índice **no** son independientes. En el servicio de Políglota (400 docs reales) usamos HNSW con el `efSearch` elegido para que la configuración probada sea la de producción.''')

    # ─────────────── §6 Servicio ───────────────
    nb.md(r'''## 6. El servicio integrado (módulo 18) bajo tráfico
Montamos `ServicioPoliglota` con **exactamente** las decisiones anteriores: analizador de BM25 (mismo tokenizador al indexar y al consultar: contrato F3 del módulo 19), embedder recortado a `dim`, vectores en la precisión elegida, HNSW con el `efSearch` elegido, la fusión elegida (RRF o lineal con su α, normalizada dentro de cada lista igual que en §4) y caché versionada.''')
    nb.gemini(
        "video", "M20-VID-01", "Recorrido de una consulta por Políglota v1.0",
        "Animación de una consulta real atravesando el sistema completo, con los números que el capstone mide en cada etapa.",
        """Video de diagrama técnico animado, 16:9, fondo blanco, paleta: azul #1F6FEB (consulta), naranja #F28E2B (BM25), verde #2CA02C (denso), gris #6B7280 (infraestructura). Sans-serif grande, sin voz en off, ritmo calmado.
0–4 s: aparece una tarjeta con la consulta "cómo invalidar la caché de sesiones" y el texto "Usuario → /search".
4–9 s: la consulta entra en la caja "Normalización NFC + minúsculas"; aparece la clave "versión v2-d96-int8 + texto normalizado" y una caja "Caché LRU": primero un letrero rojo "fallo", luego la consulta sigue.
9–15 s: la consulta se divide en dos flechas: naranja hacia "BM25 (palabras + identificadores)" y verde hacia "Embedder (d recortada) → HNSW efSearch". Cada flecha devuelve una lista de 5 documentos con su rango 1..5.
15–21 s: las dos listas se funden en la caja "RRF: Σ 1/(60 + rango)"; los documentos se reordenan visiblemente; un documento que estaba 3.º en ambas sube al 1.º.
21–26 s: aparece el top-3 final en una tarjeta; debajo, el texto "latencia registrada: p50 / p99" y "vector guardado en caché".
26–32 s: la misma consulta se repite y la caja "Caché LRU" muestra "acierto": la flecha verde salta directamente al índice. Texto final: "Cada etapa = una decisión medida en dev".
Evita: cifras inventadas, logotipos, transiciones bruscas, texto pequeño.""",
        "Animación de una consulta que pasa por normalización, caché, BM25 y denso en paralelo, fusión RRF y top-3, y una segunda consulta que acierta en caché.",
        """
"cómo invalidar la caché de sesiones" → NFC/minúsculas → clave(versión+texto) → caché: FALLO
   ├─ BM25 (palabras+ident) → rangos 1..k ─┐
   └─ embedder[:d] → HNSW(ef) → rangos ────┴→ RRF Σ1/(60+r) → top-3 (+latencia, +caché)
2ª vez: caché ACIERTO → salta el embedder
""", duration="30-35 s")
    nb.md("> 👀 **Qué debes observar:** la segunda consulta se salta el embedder: eso es lo que mide el *hit rate*; y la fusión puede subir al primer puesto un documento que no era el primero en ninguna lista.")
    nb.code(r'''
VERSION = f"{modelo}-d{dim}-{precision}"
FUS = dict(fusion="lineal" if DECISIONES["fusion"] == "lineal" else "rrf", alfa=ALFA)
svc = ServicioPoliglota(docs, bm_sel, cache_cap=1024, tokenizador=tok_sel, **FUS)
svc.registrar_version(VERSION, EmbedderRecortado(VERS[modelo], dim), D_sel, indice="hnsw", ef_search=DECISIONES["ef_search"])
svc.alias["prod"] = VERSION
modo = "hibrido"
run_svc = {qids[i]: [d for d, _ in svc.buscar(q_texts[i], k=10, modo=modo)] for i in range(len(qids))}   # frío
for i in range(len(qids)):
    svc.buscar(q_texts[i], k=10, modo=modo)                                                                # caliente
lat = np.array(svc.lat_ms); n = len(qids)
def trafico_zipf(n, universo, s=1.1, p_variante=0.35, seed=SEED):
    rng = np.random.default_rng(seed); p = 1.0 / np.arange(1, len(universo) + 1) ** s; p /= p.sum(); out = []
    for i in rng.choice(len(universo), size=n, p=p):
        t = universo[i]
        out.append(rng.choice([t.upper(), "  " + t, t + " "]) if rng.random() < p_variante else t)
    return out
universo = [q_texts[i % len(q_texts)] + ("" if i < len(q_texts) else f" {i // len(q_texts)}") for i in range(3000)]
svc_z = ServicioPoliglota(docs, bm_sel, cache_cap=1024, tokenizador=tok_sel, **FUS)
svc_z.registrar_version(VERSION, EmbedderRecortado(VERS[modelo], dim), D_sel, indice="hnsw", ef_search=DECISIONES["ef_search"]); svc_z.alias["prod"] = VERSION
for t in trafico_zipf(5000, universo): svc_z.buscar(t)
METRICAS.update(p50_frio=float(np.percentile(lat[:n], 50)), p99_frio=float(np.percentile(lat[:n], 99)),
                p50_caliente=float(np.percentile(lat[n:], 50)), p99_caliente=float(np.percentile(lat[n:], 99)),
                p99_zipf=float(np.percentile(svc_z.lat_ms, 99)), hit_rate=svc_z.cache.hit_rate)
fig, ax = plt.subplots(figsize=(7.5, 3.8))
ax.hist(lat[:n], bins=30, color=NARANJA, alpha=.7, label="frío (caché vacía)"); ax.hist(lat[n:], bins=30, color=AZUL, alpha=.7, label="caliente")
ax.hist(svc_z.lat_ms, bins=30, color=VERDE, alpha=.5, label=f"tráfico Zipf (hit rate {svc_z.cache.hit_rate:.2f})")
ax.set_xlabel("latencia por query (ms, CPU, batch=1)"); ax.set_ylabel("nº de queries"); ax.set_yscale("log"); ax.set_title("Latencia del servicio Políglota v1.0")
ax.legend(fontsize=8); plt.tight_layout(); plt.show()
print({k: round(v, 3) for k, v in METRICAS.items() if k.startswith(("p5", "p9", "hit"))})
''')
    nb.md(r'''> 👀 **Qué debes observar:** la distribución fría es la que ve un usuario con una query nueva y es la que cuenta para el criterio de p99; el tráfico Zipf mezcla aciertos (rápidos) y fallos (lentos), y su cola la ponen los fallos. En producción con un embedder neuronal, el embedder domina la latencia fría: ahí es donde pagan el micro-batching y la GPU (módulo 18).''')

    # ─────────────── §7 Evaluación final ───────────────
    nb.md(r'''## 7. Evaluación final: test ciego, una sola vez
Comparamos el **servicio** (no un notebook paralelo: se evalúa lo que se despliega) contra el baseline BM25 del módulo 00 y contra el denso solo, en las queries de **test** que no se usaron para ninguna decisión.''')
    nb.code(r'''
pq_final = ndcg_por_query(run_svc)[I_TEST]
pq_bm25_00 = pq_S(S_BM25)[I_TEST]
pq_denso = pq_S(S_den)[I_TEST]
comp = {"BM25 (módulo 00)": pq_bm25_00, "denso solo": pq_denso, "Políglota v1.0 (servicio)": pq_final}
r_bm = paired_bootstrap(pq_final, pq_bm25_00); r_de = paired_bootstrap(pq_final, pq_denso)
lt = q_lang[I_TEST]
slices = {l: (pq_final[lt == l].mean(), pq_bm25_00[lt == l].mean()) for l in ("es", "en", "code")}
METRICAS.update(test_final=pq_final.mean(), test_bm25=pq_bm25_00.mean(), test_denso=pq_denso.mean(), delta_bm25=r_bm, delta_denso=r_de, slices=slices)
fig, ax = plt.subplots(figsize=(9, 4)); x = np.arange(4); w = .27
for j, (k, v) in enumerate(comp.items()):
    vals = [v.mean()] + [v[lt == l].mean() for l in ("es", "en", "code")]
    ci = bootstrap_ci(v)
    ax.bar(x + (j - 1) * w, vals, w, color=[GRIS, AZUL, VERDE][j], label=k)
    ax.errorbar(x[0] + (j - 1) * w, vals[0], yerr=[[vals[0] - ci[1]], [ci[2] - vals[0]]], color="k", capsize=3)
ax.set_xticks(x); ax.set_xticklabels(["global (IC95)", "es", "en", "code"]); ax.set_ylabel("nDCG@10 en test ciego"); ax.set_ylim(0, 1.05)
ax.set_title("Políglota v1.0 vs baselines (test ciego)"); ax.legend(fontsize=8); plt.tight_layout(); plt.show()
for nombre, rr in (("vs BM25", r_bm), ("vs denso", r_de)):
    print(f"Políglota {nombre}: Δ={rr['diff']:+.3f} IC95=[{rr['ci_low']:+.3f},{rr['ci_high']:+.3f}] p={rr['p_value']:.3f}")
''')
    nb.md(r'''> 👀 **Qué debes observar:** con ~55 queries de test los IC son anchos: una mejora de pocos puntos sobre BM25 puede no ser significativa, y eso **se reporta tal cual** (el criterio de aceptación exige no ser peor, con margen). El desglose por idioma enseña dónde está el valor del híbrido (típicamente código, gracias a los identificadores y al denso) y si algún slice empeora. Con datos reales y un embedder neuronal multilingüe, espera diferencias mayores en paráfrasis y cruce ES↔EN (módulos 13 y 19).''')

    # ─────────────── §8 Informe ───────────────
    nb.md(r'''## 8. Informe técnico y criterios de aceptación (generados desde las métricas)
El informe se **genera** desde `DECISIONES` y `METRICAS`: si cambias una decisión y re-ejecutas, el informe se actualiza solo (nada de copiar números a mano). Se guarda como `poliglota_informe.md` junto a `poliglota_config.json`.''')
    nb.gemini(
        "imagen", "M20-IMG-02", "Anatomía de un informe técnico de decisiones",
        "La estructura de una página del informe que genera el capstone: decisiones con evidencia, resultados en test ciego, costos/latencia y tabla de criterios de aceptación.",
        """Maqueta de documento técnico de una página, vista frontal, fondo blanco, paleta: azul #1F6FEB (títulos), verde #2CA02C (criterio cumplido), naranja #F28E2B (criterio no cumplido), gris #6B7280 (texto de relleno). Sans-serif legible.
Título arriba: "Políglota v1.0 · Informe técnico de decisiones". Debajo, cinco bloques apilados con encabezados azules:
1 "Decisiones (tomadas en dev)": tabla de 3 columnas "Componente | Decisión | Evidencia" con filas "Tokenizer", "Analizador BM25", "Embedder", "Fusión", "Índice" (el contenido de las celdas en líneas grises, sin números).
2 "Resultados en test ciego": una barra horizontal con tres segmentos rotulados "BM25", "denso", "Políglota" y un intervalo de confianza dibujado como bigote.
3 "Costos y latencia": tres pastillas "re-embedding $", "RAM GB/réplica", "p50 / p99 ms".
4 "Criterios de aceptación": tabla "Criterio | Umbral | Valor | OK" con cinco filas: cuatro con un ✓ verde y una con un ✗ naranja.
5 "Limitaciones y siguiente iteración": tres viñetas grises.
Al margen derecho, una flecha gris vertical con el texto "generado desde las métricas, no escrito a mano".
Evita: números concretos, logotipos, texto ilegible, sombras decorativas.""",
        "Maqueta de una página de informe con decisiones, resultados en test, costos y latencia, criterios de aceptación y limitaciones.",
        """
# Políglota v1.0 · Informe técnico
[Decisiones (dev)]  Componente | Decisión | Evidencia
[Test ciego]        BM25 | denso | Políglota (IC95)
[Costos/latencia]   $ re-embedding · GB/réplica · p50/p99
[Aceptación]        Criterio | Umbral | Valor | ✓/✗
[Limitaciones]      • • •        ← generado desde METRICAS/DECISIONES
""")
    nb.md("> 👀 **Qué debes observar:** cada bloque responde a una pregunta de la CTO (¿qué elegiste?, ¿es mejor?, ¿cuánto cuesta?, ¿cumple?, ¿qué falta?). Si tu informe no contesta alguna, está incompleto aunque los números sean buenos.")
    nb.code(r'''
coste_reembed = 1e7 * 400 / 1e6 * 0.02
checks = {
    "calidad_vs_bm25": METRICAS["test_final"] >= METRICAS["test_bm25"] - 1e-12 and METRICAS["delta_bm25"]["ci_low"] > -0.03,
    "peor_slice": all(f >= b - 0.05 for f, b in METRICAS["slices"].values()),
    "recall_ann": METRICAS["recall_ann"] >= 0.95,
    "latencia_p99_ms": METRICAS["p99_frio"] <= 50,
    "ram_10M_gb": METRICAS["ram_10M_gb"] <= 16,
    "coste_reembed_usd": coste_reembed <= 500,
    "hit_rate": METRICAS["hit_rate"] >= 0.70,
}
valores = {"calidad_vs_bm25": f"{METRICAS['test_final']:.3f} vs {METRICAS['test_bm25']:.3f} (IC Δ ≥ {METRICAS['delta_bm25']['ci_low']:+.3f})",
           "peor_slice": ", ".join(f"{l}: {f:.3f}/{b:.3f}" for l, (f, b) in METRICAS["slices"].items()),
           "recall_ann": f"{METRICAS['recall_ann']:.3f}", "latencia_p99_ms": f"{METRICAS['p99_frio']:.1f} ms (frío)",
           "ram_10M_gb": f"{METRICAS['ram_10M_gb']:.1f} GB", "coste_reembed_usd": f"{coste_reembed:.0f} $", "hit_rate": f"{METRICAS['hit_rate']:.2f}"}
tabla = "\n".join(f"| {k} | {ACEPTACION[k]} | {valores[k]} | {'✅' if ok else '❌'} |" for k, ok in checks.items())
informe = f"""# Políglota v1.0 · Informe técnico de decisiones
**Fuente de datos:** {corpus['source']} · **docs:** {len(docs)} · **queries:** dev {len(DEV)} / test ciego {len(TEST)} · **semilla:** {SEED}

## Decisiones (tomadas en dev)
| Componente | Decisión | Evidencia |
|---|---|---|
| Tokenizer (costo) | {DECISIONES['tokenizer_costo']} | fertilidad code/es ≈ {df_tok[(df_tok.vocab == 4000) & (df_tok.lang == 'code')].fertilidad.item() / df_tok[(df_tok.vocab == 4000) & (df_tok.lang == 'es')].fertilidad.item():.1f}× |
| Analizador BM25 | {DECISIONES['analizador_bm25']} | mejor nDCG@10 en dev entre 3 analizadores |
| Embedder | {DECISIONES['modelo']} · d={DECISIONES['dim']} · {DECISIONES['precision']} | menor d a ≤ 0.01 de la completa; int8 pierde {METRICAS['dev_nd_dim'][dim] - METRICAS['dev_nd_int8']:+.3f} |
| Fusión | {DECISIONES['fusion']}{f" (α={ALFA:.2f})" if DECISIONES['fusion'] == 'lineal' else ''} | lineal(CV) − RRF en dev: Δ={METRICAS['fusion_delta']['diff']:+.3f}, IC95 [{METRICAS['fusion_delta']['ci_low']:+.3f}, {METRICAS['fusion_delta']['ci_high']:+.3f}] |
| Índice | {DECISIONES['indice']} | recall@10 = {METRICAS['recall_ann']:.3f} con N={N_SIM:,} |
| Versión servida | `{VERSION}` | alias `prod` → `{svc.alias['prod']}` |

## Resultados en test ciego
nDCG@10: **Políglota {METRICAS['test_final']:.3f}** · BM25 {METRICAS['test_bm25']:.3f} · denso {METRICAS['test_denso']:.3f}.
Δ vs BM25 = {METRICAS['delta_bm25']['diff']:+.3f} (IC95 [{METRICAS['delta_bm25']['ci_low']:+.3f}, {METRICAS['delta_bm25']['ci_high']:+.3f}], p = {METRICAS['delta_bm25']['p_value']:.3f}).

## Costos y latencia (proyección a 10 M chunks × 400 tokens)
Re-embedding: {coste_reembed:.0f} $ con API a 0.02 $/1M (oct-2026) · RAM del índice: {METRICAS['ram_10M_gb']:.1f} GB/réplica · latencia (CPU, batch=1): p50 {METRICAS['p50_frio']:.1f} ms / p99 {METRICAS['p99_frio']:.1f} ms en frío; hit rate Zipf {METRICAS['hit_rate']:.2f}.

## Criterios de aceptación
| Criterio | Umbral | Valor | OK |
|---|---|---|---|
{tabla}

## Limitaciones y siguiente iteración
* Golden set pequeño ({len(TEST)} queries de test): IC anchos. Ampliar con queries reales muestreadas por slice.
* {'Corpus SINTÉTICO y embedders fallback: repetir con datos y modelos reales antes de decidir en producción.' if corpus['source'] == 'synthetic' else 'Datos reales: validar online con interleaving (módulo 18).'}
* Multimodal (módulo 16) fuera de esta versión: añadir como tercer retriever en RRF y medir en un slice de capturas.
"""
open("poliglota_informe.md", "w", encoding="utf-8").write(informe)
json.dump({"version": VERSION, **{k: (v if not isinstance(v, (np.floating, np.integer)) else v.item()) for k, v in DECISIONES.items()}},
          open("poliglota_config.json", "w"), indent=1, ensure_ascii=False)
from IPython.display import Markdown, display
display(Markdown(informe))
print(f"Criterios cumplidos: {sum(checks.values())}/{len(checks)}")
''')
    nb.md(r'''> 👀 **Qué debes observar:** el informe dice **qué se decidió, con qué evidencia y qué no se cumple**, y lo dice con los números de esta ejecución. Un criterio en ❌ no es un fracaso del informe: es la información que necesita la CTO (por ejemplo, un p99 en CPU que en GPU sí se cumpliría, o un slice que exige más datos).''')

    # ─────────────── §9 Multimodal ───────────────
    nb.md(r'''## 9. (Opcional) Extensión multimodal
Para buscar en capturas y PDFs (módulo 16) sin rehacer el sistema:
1. **Primera etapa sin cambios**: OCR → texto → mismo pipeline (BM25 + denso). Es la opción barata y la que el árbol del módulo 19 elige cuando el índice multi-vector no cabe.
2. **Tercer retriever**: un embedder visual (CLIP/SigLIP para fotos, ColPali para páginas) produce su lista de rangos, que entra en la **misma RRF** (RRF no necesita calibrar escalas entre modalidades).
3. **Segunda etapa**: MaxSim visual solo sobre el top-K de páginas (vectores multi-vector en SSD).
4. **Evaluación**: un slice nuevo «capturas» en el golden set; el criterio de aceptación se amplía a ese slice.
El proyecto 16 (*Políglota Visual*) ya contiene el estudiante visual y MaxSim sobre patches: su salida (`S_visual`, matriz queries × páginas) se fusiona con `rrf_mat(S_den, S_lex, S_visual)`.''')

    # ─────────────── Cierre ───────────────
    nb.md(r'''## 🏭 En producción
* El patrón que has integrado — normalización simétrica, BM25 + denso con RRF, reranking opcional, índice HNSW/IVF cuantizado, caché versionada y alias de colección — es el que documentan los motores de búsqueda y vector DBs de uso general (Elasticsearch/OpenSearch, Vespa, Qdrant, Weaviate, pgvector) en sus guías de búsqueda híbrida (consultadas oct-2026).
* **Contextual Retrieval** (Anthropic, 2024) es un ejemplo publicado de mejora sobre este mismo esqueleto: añadir a cada chunk un resumen de contexto antes de embeber e indexar con BM25, combinado con reranking.
* Los *technical reports* de embedders recientes (Qwen3 Embedding, EmbeddingGemma, Gemini Embedding; módulo 12) reportan por tarea e idioma: tu informe debe hacer lo mismo con tus slices.
* Decidir en dev, evaluar en test ciego, confirmar online con interleaving y A/B, y migrar con alias (módulos 15, 18, 19) es el ciclo de vida que se repite en cada versión.
''')
    nb.md(r'''## 🧠 Secretos de la élite
1. **Escribe los criterios de aceptación antes del primer experimento** y no los cambies después sin dejar constancia en el informe.
2. **Evalúa lo que despliegas**: el número final sale del servicio (con su caché, su índice ANN y su cuantización), no de un notebook con fuerza bruta en float32.
3. **Las decisiones interactúan**: dimensión y precisión del embedder fijan la memoria, que fija el índice, que fija la latencia; decide en ese orden y re-verifica al final.
4. **Informe generado, no escrito a mano**: cada cifra del informe sale de una variable; así no hay números obsoletos tras re-ejecutar.
5. **La regla «lo simple salvo prueba en contra»** (RRF salvo que lineal gane con IC) protege contra el *winner's curse* del módulo 19.
6. **El tokenizer del LLM no es el analizador de tu BM25**: úsalo para costos y contexto; el analizador léxico se elige por nDCG.
7. **Un criterio en ❌ con explicación vale más que diez en ✅ con umbrales ajustados a posteriori.**
''')
    nb.md(r'''## ⚠️ Errores comunes
* Elegir la dimensión, la fusión o el `efSearch` mirando el test.
* Construir BM25 con un analizador e invocarlo con otro (contrato roto, fallo silencioso).
* Evaluar en float32 exacto y desplegar int8 + HNSW sin re-medir.
* Reportar solo la media global y esconder el slice que empeora.
* Proyectar memoria con `d` completa cuando el servicio usa `d` recortada (o al revés).
* Olvidar la versión del vector en la clave de caché al cambiar `dim` o `precision` (¡también son versión!).
''')
    nb.md(r'''## 📝 Autoevaluación
<details><summary><b>1 · (Cálculo)</b> Con d = 96 en int8 y HNSW (grafo ≈ 256 B/vector), ¿cuánta RAM ocupan 10 M de chunks? ¿Y con d = 768 float32?</summary>

$10^7 \times (96 + 256)$ B = **3.5 GB**; $10^7 \times (3072 + 256)$ B = **33.3 GB**. La elección del §3 multiplica por ~10 la capacidad por réplica.
</details>
<details><summary><b>2 · (Diagnóstico)</b> En dev el sistema gana +0.05 a BM25, en test +0.005 con IC que incluye el 0. ¿Qué concluyes y qué no?</summary>

Que no hay evidencia de mejora en test (probable optimismo de selección en dev, o un dev poco representativo). No concluyes que «es peor». Acciones: más queries de test por slice, revisar si alguna decisión se tomó con información del test, y validar online con interleaving.
</details>
<details><summary><b>3 · (Diagnóstico)</b> Cambias `dim` de 96 a 64 y redepliegas; los resultados de las queries populares son basura. ¿Por qué?</summary>

La versión servida debe incluir `dim` y `precision`; si la clave de caché o el alias no cambian, la caché sirve vectores de 96 d (o falla por dimensión, el caso «bueno»). `VERSION = f"{modelo}-d{dim}-{precision}"` existe por esto.
</details>
<details><summary><b>4 · (Transferencia)</b> Añades un slice de capturas (multimodal). ¿Qué cambia en los criterios de aceptación y en el informe?</summary>

Un criterio por slice (no peor que OCR+texto en capturas, con IC), el costo de almacenamiento multi-vector (en SSD) y la latencia de la segunda etapa MaxSim en el presupuesto de p99; el informe añade la decisión «OCR vs visual vs ambos» con su evidencia (módulo 16).
</details>
<details><summary><b>5 · (Transferencia)</b> La CTO pide pasar a GPU y a 100 M de chunks. ¿Qué secciones re-ejecutas y por qué?</summary>

§1 (umbrales de latencia en GPU), §3 (con 100 M la memoria puede forzar menos `d` o binario + rescore), §5 (índice: quizá IVF-PQ/DiskANN), §6 (latencia y micro-batching) y §8. El tokenizer y la fusión no cambian salvo que cambie el corpus.
</details>
''')
    nb.md(r'''## 📚 Referencias
* Sennrich, Haddow, Birch (2016). *Neural Machine Translation of Rare Words with Subword Units*. https://arxiv.org/abs/1508.07909 · Wang, Cho, Gu (2019). *Neural Machine Translation with Byte-Level Subwords*. https://arxiv.org/abs/1909.03341
* Robertson & Zaragoza (2009). *The Probabilistic Relevance Framework: BM25 and Beyond*. Foundations and Trends in IR.
* Wang et al. (2024). *Multilingual E5 Text Embeddings: A Technical Report*. https://arxiv.org/abs/2402.05672 · Kusupati et al. (2022). *Matryoshka Representation Learning*. https://arxiv.org/abs/2205.13147
* Cormack, Clarke, Büttcher (2009). *Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods*. SIGIR · Bruch, Gai, Ingber (2022). https://arxiv.org/abs/2210.11934
* Malkov & Yashunin (2016). *HNSW*. https://arxiv.org/abs/1603.09320 · Douze et al. (2024). *The Faiss library*. https://arxiv.org/abs/2401.08281
* Smucker, Allan, Carterette (2007). *A Comparison of Statistical Significance Tests for Information Retrieval Evaluation*. CIKM · Thakur et al. (2021). *BEIR*. https://arxiv.org/abs/2104.08663
* Faysse et al. (2024). *ColPali*. https://arxiv.org/abs/2407.01449
* Shakir, Aarsen, Lee (2024). *Binary and Scalar Embedding Quantization* (blog de Hugging Face). https://huggingface.co/blog/embedding-quantization
* Anthropic (2024). *Introducing Contextual Retrieval*. https://www.anthropic.com/news/contextual-retrieval
* Hugging Face `tokenizers`: https://github.com/huggingface/tokenizers · FAISS: https://github.com/facebookresearch/faiss
* Material del curso: `extras/GUIA_ENTREVISTAS.md` y `extras/LECTURA_PAPERS.md`.
''')
