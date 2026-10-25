"""Genera el módulo 13 (lección + proyecto + README): Dense vs sparse vs late interaction.

Ejecutar desde la raíz del repo:  python tokenization-embeddings-course/_tools/builders/build_13.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from nbbuild import Notebook  # noqa: E402
import _a5_common as C  # noqa: E402
from poliglota_utils import SRC_METRICS, src_corpus_cells  # noqa: E402  (utilidades canónicas del módulo 00)

COURSE = "tokenization-embeddings-course"
MOD = f"{COURSE}/13_dense_sparse_late_interaction"
LESSON = f"{MOD}/13_dense_sparse_late_interaction.ipynb"
PROJECT = f"{MOD}/13_proyecto_dense_sparse_late_interaction.ipynb"
os.makedirs(f"{MOD}/assets", exist_ok=True)
open(f"{MOD}/assets/.gitkeep", "a").close()

# ───────────────────── celdas de código compartidas por lección y proyecto ─────────────────────
CODE_PIP = r'''
!pip install -q -U sentence-transformers transformers scikit-learn scipy matplotlib pandas rank_bm25
'''

CODE_BENCH = r'''
import pandas as pd
import matplotlib.pyplot as plt

class Bench:
    """Un corpus + sus queries + las matrices de scores (n_queries x n_docs) de cada retriever."""
    def __init__(self, nombre, corpus):
        self.nombre, self.corpus = nombre, corpus
        self.ids = [d["id"] for d in corpus["docs"]]
        self.txt = [d["text"] for d in corpus["docs"]]
        self.qs = corpus["queries"]
        self.qtxt = [q["text"] for q in self.qs]
        self.qrels = corpus["qrels"]
        self.S = {}                                   # nombre del retriever -> matriz de scores
    def run(self, S, k=10):
        return {q["qid"]: rank_from_scores(S[i], self.ids, k) for i, q in enumerate(self.qs)}
    def ndcg(self, S, k=10):
        return evaluate(self.run(S, k), self.qrels, k)["ndcg"]
    def ndcg_q(self, S, k=10):
        """nDCG@k por query (alineado con self.qs): sirve para validación cruzada y bootstrap."""
        run = self.run(S, k)
        return np.array([ndcg_at_k(run[q["qid"]], self.qrels[q["qid"]], k) for q in self.qs])
    def resumen(self):
        filas = []
        for nombre, S in self.S.items():
            r = evaluate(self.run(S), self.qrels)
            filas.append({"retriever": nombre, "nDCG@10": round(r["ndcg"], 3), "Recall@10": round(r["recall"], 3), "MRR@10": round(r["mrr"], 3)})
        return pd.DataFrame(filas).set_index("retriever")

CORPUS = carga_corpus(FAST_DEV_RUN)
PAR = corpus_parafrasis()
B1, B2 = Bench("canónico (Políglota)", CORPUS), Bench("paráfrasis ES↔EN↔código", PAR)
BENCHES = [B1, B2]
for b in BENCHES:
    print(f"{b.nombre}: fuente={b.corpus['source']} · {len(b.ids)} docs · {len(b.qs)} queries")
'''

CODE_DENSE = r'''
# Retriever denso: el primer embedder que se pueda cargar de verdad; si no, el fallback TF-IDF+SVD (módulo 12).
TEXTOS_AJUSTE = [t for b in BENCHES for t in b.txt]
emb = None
for clave in ("multilingual-e5-small", "paraphrase-multilingual-MiniLM-L12-v2"):
    emb = cargar_embedder(clave)
    if emb is not None:
        break
if emb is None:
    emb = cargar_embedder("multilingual-e5-small", textos_ajuste=TEXTOS_AJUSTE)
for b in BENCHES:
    Ed, Eq = emb.encode_docs(b.txt), emb.encode_queries(b.qtxt)
    b.S["denso"] = Eq @ Ed.T
print(f"denso = {emb.clave} · real={emb.is_real}")
'''


def lesson() -> None:
    nb = Notebook("Módulo 13 · Dense vs sparse vs late interaction", colab_path=LESSON, gpu=True)

    # ───────────────────────────── Cabecera ─────────────────────────────
    nb.md(nb.badge() + r'''

# Módulo 13 · Dense vs sparse vs late interaction: BM25, SPLADE, ColBERT, MUVERA y retrieval híbrido

**Nivel:** 🟠 Avanzado · **Duración:** ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) · **GPU recomendada:** T4 (todo corre en CPU con `FAST_DEV_RUN = True`) ·
**Cómputo estimado:** 0 unidades en CPU; ≈ 1–2 unidades de Colab en T4 si activas BGE-M3 y el reranker real (estimación orientativa).

> 🧭 **Ruta núcleo vs ampliación.** Núcleo (≈ 3 h): secciones 1–4 (BM25, ColBERT/MaxSim), 7 (fusión) y 8 (rerankers). Ampliación (≈ 1 h más): SPLADE (3), MUVERA y PLAID (5–6) y late chunking (9).

**Prerrequisitos:** módulo 00 (BM25 como baseline), 10 (similitudes, pooling), 11 (contrastivo) y 12 (embedders modernos: el retriever denso de hoy es el de allí).

**Hilo conductor — Políglota.** El CTO te enseña tres consultas reales que fallan: una con un **identificador exacto** (`ERR_CONN_RESET`) que el embedder denso no encuentra, una **parafraseada** (ES→EN) que BM25 no encuentra y una **muy específica** donde el top-10 contiene lo correcto en la posición 7. Este módulo construye el sistema que arregla las tres: **retrieval híbrido (léxico + denso + late interaction) con fusión y reranking**.

> **Estado del arte a octubre de 2026.** Toda cifra, ID de checkpoint o adopción por parte de una empresa va fechada y con fuente; lo que no se pudo verificar se marca como tal.
''')
    nb.md(r'''## 🎯 Objetivos de aprendizaje
Al terminar serás capaz de:
1. **Implementar BM25 desde cero** (índice invertido en matriz dispersa), verificarlo contra `rank_bm25` y explicar el efecto de `k1`, `b` y del *analyzer* (acentos, stemming).
2. **Explicar y calcular** la representación de SPLADE (activación MLM → ReLU → log → max-pooling, regularizador FLOPS) y usar un modelo sparse aprendido.
3. **Implementar MaxSim (ColBERT) desde cero**, vectorizado, y entender su coste de almacenamiento y la compresión residual de ColBERTv2.
4. **Implementar una versión mini de PLAID** (interacción por centroides + filtrado) y medir el *trade-off* candidatos/recall.
5. **Implementar MUVERA** (Fixed Dimensional Encodings) y medir cuánto se parece su producto interno a MaxSim.
6. **Fusionar retrievers** con RRF y con combinación lineal normalizada, y decidir cuándo usar cada una.
7. **Montar el pipeline recuperar → fusionar → reordenar** con un cross-encoder y medir el coste/beneficio por profundidad de reranking.
8. **Aplicar late chunking** y razonar cuándo ayuda.
''')
    nb.md(r'''## 🔁 Conexión con módulos anteriores
<details><summary><b>1 · (M00)</b> ¿Qué fórmula usa BM25 y qué problema de TF-IDF resuelve la saturación de <code>k1</code>?</summary>

$\text{BM25}(q,d)=\sum_{t\in q}\text{IDF}(t)\,\frac{f_{t,d}(k_1+1)}{f_{t,d}+k_1\,(1-b+b\,|d|/\overline{|d|})}$. En TF-IDF el peso crece linealmente con la frecuencia del término; BM25 lo **satura** (un término que aparece 20 veces no vale 20× más) y normaliza por longitud.
</details>
<details><summary><b>2 · (M10/M12)</b> ¿Por qué un embedder denso (un vector por texto) pierde información sobre términos raros o identificadores exactos?</summary>

Porque comprime todo el texto en $d$ números: la señal de un token raro (un código de error, un nombre propio) se diluye en el promedio y el modelo apenas vio esos tokens al entrenar. Un índice invertido, en cambio, hace match **exacto** de ese término.
</details>
<details><summary><b>3 · (M04/M05)</b> ¿Cómo influye la tokenización en un retriever léxico?</summary>

El *analyzer* decide qué es un término: minúsculas, tildes, stemming, separación de identificadores (`snake_case`, `CamelCase`). Con otra tokenización el mismo corpus produce otro índice y otras métricas. Es el primer lugar donde mirar cuando BM25 "no encuentra" algo.
</details>
<details><summary><b>4 · (M11/M12)</b> ¿Qué distingue a un <i>bi-encoder</i> de un <i>cross-encoder</i> en coste y calidad?</summary>

El bi-encoder codifica query y documento por separado (los documentos se precomputan): $O(1)$ forward por búsqueda sobre el índice, menor calidad. El cross-encoder procesa el par conjuntamente: más preciso, pero exige un forward **por candidato** y no puede precomputarse.
</details>
''')
    nb.md(r'''## 🗺️ Mapa de madurez (a oct-2026)
🟢 sólido · 🟡 emergente · 🔴 experimental.

| Técnica | Madurez | Quién la usa (respaldado) | Fuente |
|---|---|---|---|
| BM25 / índice invertido | 🟢 | motores de búsqueda léxicos (Lucene, Elasticsearch, OpenSearch, Vespa…) | Robertson & Zaragoza 2009 |
| Sparse aprendido (SPLADE, SPLADE-v3) | 🟢 inglés · 🟡 multilingüe | Elastic (ELSER) y OpenSearch (neural sparse) ofrecen modelos sparse aprendidos | Formal et al. 2021–2024; docs de Elastic/OpenSearch |
| BGE-M3 (denso + sparse + multi-vector en un modelo) | 🟢 | BAAI; integrado en el ecosistema de FlagEmbedding | Chen et al. 2024 (2402.03216) |
| Late interaction ColBERT / ColBERTv2 | 🟡 | Vespa (embedder ColBERT nativo), Qdrant (multivector `MAX_SIM`), Jina-ColBERT-v2 | Khattab & Zaharia 2020; Santhanam et al. 2021; blogs/docs |
| PLAID / WARP (motores de late interaction) | 🟡 | implementación de referencia de ColBERT (PLAID); WARP es investigación 2025 | 2205.09707; 2501.17788 |
| MUVERA (multi-vector → un vector de dimensión fija) | 🟡 | Weaviate documenta una opción de codificación MUVERA | Dhulipala et al. 2024 (2405.19504); docs de Weaviate |
| Fusión RRF / combinación convexa | 🟢 | práctica estándar de búsqueda híbrida | Cormack et al. 2009; Bruch et al. 2022 |
| Rerankers cross-encoder | 🟢 | BAAI (bge-reranker-v2-m3), muchos proveedores | Nogueira & Cho 2019 (1901.04085) |
| Rerankers basados en LLM (Qwen3-Reranker, bge-reranker-v2-gemma) | 🟡 | Alibaba, BAAI — mayor coste | 2506.05176; tarjetas |
| Late chunking | 🟡 | Jina AI | Günther et al. 2024 (2409.04701) |
| Búsqueda híbrida (léxico + denso) como configuración por defecto | 🟢 | prácticamente todas las bases vectoriales/motores modernos | docs de los motores |
''')

    # ───────────────────────────── Setup ─────────────────────────────
    nb.md(r'''## 0 · Preparación
Como en el módulo 12: celdas de utilidades autocontenidas (corpus canónico del módulo 00, métricas, embedder con fallback). Usaremos **dos bancos de pruebas** para ver *dónde gana cada retriever*:

- **Canónico (Políglota):** el corpus del módulo 00 (Wikipedia ES/EN + código si hay acceso; si no, sintético con un `⚠️`). Queries con bastante solapamiento léxico.
- **Paráfrasis ES↔EN↔código:** 29 conceptos técnicos × 3 documentos con **58 queries parafraseadas** que casi no comparten palabras con su documento (y buscan entre idiomas). Pequeño y escrito a mano: sirve para *diagnosticar*, no para reportar cifras.
''')
    nb.code(CODE_PIP)
    nb.code(C.CODE_SETUP_COMMON)
    for _src in src_corpus_cells():
        nb.code(_src)
    nb.code(SRC_METRICS)
    nb.code(C.CODE_EVAL_PQ)
    nb.code(C.CODE_CORPUS_SEED)
    nb.code(C.CODE_PARAFRASIS_LOADER)
    nb.code(C.CODE_EMBEDDER_TOOLS)
    nb.code(CODE_BENCH)
    nb.code(CODE_DENSE)

    # ───────────────────────────── 1. Intuición ─────────────────────────────
    nb.md(r'''## 1 · Intuición: tres maneras de representar un documento

| | **Sparse léxico / aprendido** | **Denso (un vector)** | **Late interaction (multi-vector)** |
|---|---|---|---|
| Representación | vector de $|V|\approx 10^5$ dimensiones, casi todo ceros | 1 vector de $d\approx 10^3$ | 1 vector **por token** ($n\times d$, $d\approx 128$) |
| Índice | **invertido** (término → documentos) | ANN (módulo 14) | ANN sobre tokens + re-score exacto, o MUVERA |
| Fortaleza | términos exactos, identificadores, explicabilidad | semántica, paráfrasis, multilingüe | precisión fina sin cross-encoder, generalización fuera de dominio |
| Debilidad | *vocabulary mismatch* | pierde detalle, términos raros | **almacenamiento** y complejidad de infraestructura |
| Analogía | `grep` con pesos | resumen en un punto del espacio | comparar **palabra por palabra** y quedarse con la mejor pareja |

> 💡 **Analogía con recsys.** BM25 ≈ filtrado por *features* explícitas; denso ≈ *two-tower* de un vector por ítem; late interaction ≈ modelos de *interacción de bajo nivel* (el score se calcula sobre pares de componentes) que son más ricos que el producto punto único pero caros de indexar. El patrón recomendador "retrieval barato → ranker caro" (recsys-course/06–07) es exactamente el de hoy: *recall* con sparse+denso, *precisión* con late interaction y cross-encoder.
''')
    nb.gemini(
        "imagen", "M13-IMG-01", "Tres paradigmas de representación para retrieval",
        "Una misma consulta y un mismo documento representados de tres formas: sparse (bolsa de términos con pesos), denso (un vector) y late interaction (un vector por token con MaxSim).",
        """
        Diagrama técnico limpio, fondo blanco, formato 16:9. Paleta: azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280. Tipografía sans-serif legible. Sin ilustraciones decorativas ni texto inventado.

        Tres columnas iguales con títulos arriba. Encima de las tres, en una barra gris: consulta "cómo reducir la memoria de los embeddings" y debajo documento "Cuantizar a int8 reduce 4 veces la memoria de un índice".
        Columna 1 (naranja) "Sparse (BM25 / SPLADE)": una fila de cajitas etiquetadas con términos y pesos: "memoria 2.1", "embeddings 1.7", "int8 1.4", "cuantizar 0.9", "índice 0.8"; el resto de la fila, muchas cajitas vacías con la nota "≈ 100 000 dimensiones, casi todas 0". Subtítulo: "índice invertido: término → documentos".
        Columna 2 (azul) "Denso (1 vector)": una única barra horizontal de 8 bloques de intensidades distintas, con la etiqueta "d = 1024 números" y una flecha circular con "coseno". Subtítulo: "ANN sobre un vector por documento".
        Columna 3 (verde) "Late interaction (1 vector por token)": dos pequeñas pilas de barras: arriba 4 barras para los tokens de la consulta, abajo 6 barras para los tokens del documento; líneas finas verdes desde cada token de la consulta hasta su mejor token del documento y la nota "MaxSim: suma de los mejores emparejamientos". Subtítulo: "más precisión, más almacenamiento".
        Pie de figura gris: "lexical ← — — → semántico".

        Evita: texto ilegible, más de cinco términos en la columna 1, flechas cruzadas confusas, logos, iconos decorativos.
        """,
        "Tres columnas que muestran la misma consulta como bolsa de términos, un vector y un vector por token",
        """
        SPARSE            |  DENSO               |  LATE INTERACTION
        memoria 2.1       |  [■▪■▫▪■▫▪] d=1024   |  q: [t1][t2][t3][t4]
        embeddings 1.7    |  coseno(q,d)         |        ↘  ↓  ↙  ↓   (mejor token de d)
        int8 1.4          |                      |  d: [u1][u2][u3][u4][u5][u6]
        ...(≈100k dims)   |                      |  score = Σ_i max_j q_i·d_j
        """,
    )
    nb.md(r'''> 👀 **Qué debes observar.** De izquierda a derecha el score deja de ser "un número por documento" y pasa a depender de **más componentes**: términos con pesos → un punto → una nube de puntos. Cada paso gana expresividad y paga en almacenamiento. Ningún paradigma domina: los sistemas buenos **combinan** al menos dos.
''')

    # ───────────────────────────── 2. BM25 ─────────────────────────────
    nb.md(r'''## 2 · BM25 desde cero (y por qué sigue ganando partidos)

$$\text{BM25}(q,d)=\sum_{t\in q}\underbrace{\ln\!\Big(1+\frac{N-n_t+0.5}{n_t+0.5}\Big)}_{\text{IDF (variante de Lucene)}}\;\cdot\;\frac{f_{t,d}\,(k_1+1)}{f_{t,d}+k_1\big(1-b+b\,\tfrac{|d|}{\overline{|d|}}\big)}$$

- $N$: nº de documentos; $n_t$: documentos que contienen $t$; $f_{t,d}$: frecuencia de $t$ en $d$; $|d|$: longitud (en términos); $\overline{|d|}$: longitud media.
- $k_1\approx1.2$ controla la **saturación** de la frecuencia (con $k_1\to0$ solo importa presencia/ausencia; con $k_1\to\infty$ se vuelve lineal como TF).
- $b\in[0,1]$ controla la **normalización por longitud** ($b=0$ la ignora; $b=1$ normaliza del todo).
- Variantes del IDF: Lucene usa $\ln(1+\cdot)$ (siempre ≥ 0); la clásica Okapi usa $\ln\frac{N-n_t+0.5}{n_t+0.5}$ que puede ser **negativa** para términos en más de la mitad de los documentos (`rank_bm25` la sustituye por un suelo $\epsilon\cdot\overline{\text{IDF}}$).

**Implementación.** Como el peso de cada par (documento, término) no depende de la query, lo **precomputamos** en una matriz dispersa $W\in\mathbb{R}^{N\times V}$; buscar es multiplicar $W$ por el vector de conteos de la query. Esto es, en esencia, lo que hace un índice invertido con *impact scores*.
''')
    nb.code(r'''
import re, unicodedata
import scipy.sparse as sp
from collections import Counter

SUFIJOS = ("aciones", "acion", "amente", "mente", "ando", "iendo", "ing", "ed", "es", "s", "ar", "er", "ir")

def quita_acentos(t):
    n = unicodedata.normalize("NFD", t)
    return "".join(c for c in n if unicodedata.category(c) != "Mn")

def stem_ligero(t):
    """Stemmer de juguete (sufijos ES/EN). En producción: Snowball/Porter u otro analyzer del motor."""
    for s in SUFIJOS:
        if len(t) > len(s) + 3 and t.endswith(s):
            return t[:-len(s)]
    return t

def toks(texto, acentos=True, stem=False):
    t = texto.lower()
    if acentos:
        t = quita_acentos(t)
    out = re.findall(r"\w+", t)
    return [stem_ligero(x) for x in out] if stem else out

class BM25:
    """BM25 con matriz de pesos precomputada. idf='lucene' o 'okapi' (como rank_bm25.BM25Okapi, epsilon=0.25)."""
    def __init__(self, k1=1.2, b=0.75, idf="lucene"):
        self.k1, self.b, self.idf_kind = k1, b, idf
    def fit(self, docs_tokens):
        self.vocab, filas, cols, vals = {}, [], [], []
        for i, tk in enumerate(docs_tokens):
            for t, c in Counter(tk).items():
                filas.append(i); cols.append(self.vocab.setdefault(t, len(self.vocab))); vals.append(c)
        N = len(docs_tokens)
        tf = sp.csr_matrix((vals, (filas, cols)), shape=(N, len(self.vocab)), dtype=np.float64)
        dl = np.array([len(t) for t in docs_tokens], dtype=float)
        avgdl = dl.mean()
        df = np.asarray((tf > 0).sum(0)).ravel()
        if self.idf_kind == "lucene":
            idf = np.log(1 + (N - df + 0.5) / (df + 0.5))
        else:
            idf = np.log(N - df + 0.5) - np.log(df + 0.5)
            idf = np.where(idf < 0, 0.25 * idf.mean(), idf)
        fila_de = np.repeat(np.arange(N), np.diff(tf.indptr))
        w = tf.data * (self.k1 + 1) / (tf.data + self.k1 * (1 - self.b + self.b * dl[fila_de] / avgdl))
        self.W = sp.csr_matrix((w * idf[tf.indices], tf.indices, tf.indptr), shape=tf.shape).tocsc()
        return self
    def scores(self, q_tokens):
        q = np.zeros(len(self.vocab))
        for t in q_tokens:
            if t in self.vocab:
                q[self.vocab[t]] += 1                 # los términos repetidos de la query suman varias veces
        return self.W @ q

def bm25_matriz(b, k1=1.2, bb=0.75, **analyzer):
    modelo = BM25(k1, bb).fit([toks(t, **analyzer) for t in b.txt])
    return np.stack([modelo.scores(toks(q, **analyzer)) for q in b.qtxt])

# Verificación contra rank_bm25 (misma variante de IDF y mismos tokens)
from rank_bm25 import BM25Okapi
docs_t = [toks(t) for t in B1.txt]
ref = BM25Okapi(docs_t, k1=1.2, b=0.75)
mio = BM25(idf="okapi").fit(docs_t)
q0 = toks(B1.qtxt[0])
print("coincide con rank_bm25.BM25Okapi:", bool(np.allclose(ref.get_scores(q0), mio.scores(q0))))
for b in BENCHES:
    b.S["bm25"] = bm25_matriz(b)
display(B1.resumen())
''')
    nb.md(r'''> 👀 **Qué debes observar.** Las puntuaciones coinciden con `rank_bm25` hasta el redondeo (`True`): tu BM25 es correcto. Compara el nDCG@10 del banco canónico con el de paráfrasis (siguiente celda): BM25 es muy fuerte cuando query y documento comparten vocabulario y se desploma cuando no.
''')
    nb.code(r'''
fig, axs = plt.subplots(1, 3, figsize=(14, 3.6))
tf_ = np.arange(0, 21)
for k1 in (0.0, 0.6, 1.2, 2.0, 5.0):
    axs[0].plot(tf_, tf_ * (k1 + 1) / (tf_ + k1 + 1e-9), label=f"k1={k1}")
axs[0].set_title("Saturación de la frecuencia (b=0)"); axs[0].set_xlabel("frecuencia del término f"); axs[0].set_ylabel("peso del término"); axs[0].legend(fontsize=8)
dl = np.linspace(0.2, 3, 50)
for bb in (0.0, 0.5, 0.75, 1.0):
    axs[1].plot(dl, 3 * 2.2 / (3 + 1.2 * (1 - bb + bb * dl)), label=f"b={bb}")
axs[1].set_title("Normalización por longitud (f=3, k1=1.2)"); axs[1].set_xlabel("|d| / longitud media"); axs[1].set_ylabel("peso del término"); axs[1].legend(fontsize=8)
nombres, valores = [], []
for nombre, kw in [("sin tildes", dict(acentos=True)), ("con tildes", dict(acentos=False)), ("sin tildes + stem", dict(acentos=True, stem=True))]:
    nombres.append(nombre); valores.append([b.ndcg(bm25_matriz(b, **kw)) for b in BENCHES])
x = np.arange(len(nombres)); w = 0.38
axs[2].bar(x - w / 2, [v[0] for v in valores], w, label=B1.nombre[:10], color="#1F6FEB")
axs[2].bar(x + w / 2, [v[1] for v in valores], w, label="paráfrasis", color="#F28E2B")
axs[2].set_xticks(x); axs[2].set_xticklabels(nombres, fontsize=8); axs[2].set_ylabel("nDCG@10"); axs[2].set_title("Efecto del analyzer"); axs[2].legend(fontsize=8)
plt.tight_layout(); plt.show()
display(pd.DataFrame(valores, index=nombres, columns=["canónico", "paráfrasis"]).round(3))
''')
    nb.md(r'''> 👀 **Qué debes observar.** (1) A la izquierda, con $k_1$ alto la curva casi no satura (comportamiento tipo TF); con $k_1$ bajo, repetir un término apenas suma. (2) En el centro, $b=1$ castiga fuertemente a los documentos largos. (3) A la derecha, el *analyzer* mueve las métricas: quitar tildes y hacer stemming acercan variantes de una palabra. El efecto es distinto en cada banco: **ajusta el analyzer a tu idioma** (módulos 01–05). BM25 en el banco de paráfrasis rinde mucho peor porque casi no hay palabras en común (y cero entre idiomas).
''')
    # ───────────────────────────── 3. SPLADE ─────────────────────────────
    nb.md(r'''## 3 · Sparse aprendido: SPLADE

BM25 solo puede dar peso a palabras que **están** en el texto. **SPLADE** (Formal et al., 2021) usa el cabezal de **lenguaje enmascarado (MLM)** de un transformer: para cada token del texto el modelo predice una distribución sobre **todo el vocabulario** $V$ (≈ 30 000–250 000 términos), de modo que el texto "activa" también sinónimos y términos relacionados (**expansión**) y re-pondera los términos originales.

Sea $z_{t,j}$ el logit MLM del token $t$ para el término $j\in V$. El peso del término $j$ en el texto es

$$w_j=\max_{t}\;\log\!\big(1+\operatorname{ReLU}(z_{t,j})\big)$$

(SPLADE v1 sumaba sobre $t$; **v2 usa max-pooling**, más estable). El score es el producto punto de dos vectores dispersos: $s(q,d)=\sum_j w^q_j\,w^d_j$, calculable con un **índice invertido** igual que BM25.

**Esparcidad por regularización.** Sin control, el MLM activaría miles de términos. Se entrena con una pérdida de ranking (contrastiva y, en SPLADE-v3, KL-Div + MarginMSE) más el regularizador **FLOPS**:
$$\mathcal{L}_{FLOPS}=\sum_{j\in V}\bar a_j^{\,2},\qquad \bar a_j=\frac1{B}\sum_{b=1}^{B}w^{(b)}_j,$$
que penaliza los términos que se activan **en muchos documentos** (porque ese es el coste del índice invertido: listas de postings largas). Se aplican pesos $\lambda_q,\lambda_d$ distintos a queries y documentos: así se pueden tener queries muy cortas y documentos más ricos.

> 💡 **Por qué importa.** SPLADE conserva la **explicabilidad** y el índice invertido de BM25 pero resuelve parcialmente el *vocabulary mismatch*. Existe también la variante **inference-free**: la query se pondera con una tabla (sin pasar por el modelo) y solo el documento se codifica con transformer; reduce la latencia de la query (trabajo de OpenSearch, Geng et al. 2024).
''')
    nb.code(r'''
def splade_pool(logits, mask):
    """logits (B,T,V) del cabezal MLM, mask (B,T). w_j = max_t log(1 + ReLU(z_tj)) -> (B,V)."""
    act = np.log1p(np.maximum(logits, 0.0)) * mask[..., None]
    return act.max(1)

def flops_reg(W):
    """Regularizador FLOPS sobre un lote de vectores sparse W (B,V): suma_j (media_b W_bj)^2."""
    return float((W.mean(0) ** 2).sum())

# ⚠️ LOGITS INVENTADOS A MANO para ilustrar la expansión (NO son salida de un modelo real).
VOC = ["gato", "felino", "mascota", "animal", "perro", "coche", "ruta", "casa"]
z_doc1 = np.array([[[4.0, 2.5, 2.0, 1.2, 0.8, -1.0, -2.0, -1.5],      # token "gato"
                    [-1.0, -0.5, 0.2, 0.9, 0.1, -1.0, -2.0, 0.6]]])    # token "duerme"
z_doc2 = np.array([[[-2.0, -2.0, -1.0, -0.5, -1.0, 3.5, 2.0, 0.3],     # token "coche"
                    [-1.5, -1.0, -1.0, -0.5, -1.0, 1.0, 3.0, 0.2]]])   # token "ruta"
m2 = np.ones((1, 2))
W1, W2 = splade_pool(z_doc1, m2)[0], splade_pool(z_doc2, m2)[0]
print("pesos doc1:", dict(zip(VOC, np.round(W1, 2).tolist())))
print("score(doc1, doc2) =", round(float(W1 @ W2), 3), "· FLOPS del par =", round(flops_reg(np.stack([W1, W2])), 3))

fig, axs = plt.subplots(1, 2, figsize=(11, 3.2), sharey=True)
for ax, W, tit, col in ((axs[0], W1, 'Documento: "el gato duerme"', "#1F6FEB"), (axs[1], W2, 'Documento: "el coche por la ruta"', "#F28E2B")):
    ax.bar(VOC, W, color=col); ax.set_title(tit, fontsize=10); ax.tick_params(axis="x", rotation=45)
axs[0].set_ylabel("peso SPLADE (ilustrativo)")
plt.suptitle("Expansión SPLADE: el texto activa términos que NO contiene (datos inventados)", fontsize=10)
plt.tight_layout(); plt.show()
''')
    nb.md(r'''> 👀 **Qué debes observar.** El primer documento no contiene "felino" ni "mascota" pero los **activa** con peso alto (expansión), y el segundo activa términos de otro dominio: su score cruzado es ~0. El regularizador FLOPS premia que los dos documentos usen **términos distintos** (listas de postings cortas). Estos números son ilustrativos; la siguiente celda lo repite con un modelo real si está disponible.
''')
    nb.gemini(
        "imagen", "M13-IMG-02", "Cómo SPLADE expande un texto con el cabezal MLM",
        "El flujo texto → transformer → logits MLM sobre todo el vocabulario → ReLU/log/max → vector disperso con términos expandidos.",
        """
        Diagrama técnico limpio, fondo blanco, formato 16:9. Paleta: azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280. Tipografía sans-serif. Sin ilustraciones decorativas ni texto inventado.

        De IZQUIERDA a DERECHA, cuatro bloques conectados por flechas grises:
        1) Bloque gris "Texto": la frase "el gato duerme" con tres tokens en cajitas: "el", "gato", "duerme".
        2) Bloque azul "Transformer + cabezal MLM": una caja con la etiqueta "logits z(t, j) para TODO el vocabulario" y debajo una matriz de 3 filas (tokens) por 8 columnas (palabras: gato, felino, mascota, animal, perro, coche, ruta, casa) con celdas más oscuras donde el valor es alto (gato-gato oscuro, gato-felino medio, gato-mascota medio).
        3) Bloque naranja "ReLU → log(1 + x) → máximo sobre los tokens": una flecha que colapsa las 3 filas en una sola fila de 8 valores.
        4) Bloque verde "Vector disperso": una fila de 8 barras verticales con alturas aproximadas gato 1.61, felino 1.25, mascota 1.10, animal 0.79, perro 0.59, coche 0, ruta 0, casa 0.47; las barras de felino, mascota, animal y perro llevan una etiqueta "expansión" (no están en el texto original) y las de coche y ruta están vacías.
        Debajo del bloque 4, una nota gris: "se guarda en un índice invertido: término → documentos".

        Evita: texto ilegible, más columnas de las indicadas, flechas cruzadas, ilustraciones de gatos, logos, valores distintos de los dados.
        """,
        "Flujo de SPLADE desde el texto hasta un vector disperso con términos expandidos",
        """
        "el gato duerme" -> [Transformer+MLM] -> z(t,j) (3 x |V|)
              -> ReLU, log(1+x), max_t ->  gato 1.61 | felino 1.25* | mascota 1.10* | animal 0.79* | perro 0.59* | casa 0.47
                                           (* = términos expandidos que no estaban en el texto)
        """,
    )
    nb.md(r'''> 👀 **Qué debes observar.** La expansión ocurre **antes** del índice: el costo en tiempo de consulta es el de un índice invertido normal, pero el documento ya "contiene" sinónimos. El precio es el tamaño del índice (más términos por documento) y la necesidad de ajustar la esparcidad.

### Con un modelo real
Primero **desde cero**: aplicamos la fórmula al cabezal MLM de un modelo *sin* entrenar para ranking (BERT multilingüe destilado) para ver por qué hace falta el entrenamiento y el regularizador: el número de términos activos es enorme. Después usamos un **sparse aprendido** con `sentence-transformers` (`SparseEncoder`).
''')
    nb.code(r'''
import torch
SPLADE_BASE = "distilbert/distilbert-base-multilingual-cased"          # MLM crudo (NO entrenado para ranking)
SPARSE_MODELOS = ["opensearch-project/opensearch-neural-sparse-encoding-multilingual-v1", "naver/splade-v3"]

def splade_mlm_encode(tok, mlm, textos, max_len=128):
    """SPLADE desde cero con transformers: logits MLM -> log(1+ReLU) -> max sobre tokens. Devuelve (B,V) denso."""
    lote = tok(textos, padding=True, truncation=True, max_length=max_len, return_tensors="pt").to(device)
    with torch.no_grad():
        z = mlm(**lote).logits                                     # (B,T,V)
    act = torch.log1p(torch.relu(z)) * lote["attention_mask"].unsqueeze(-1)
    return act.max(1).values.cpu().numpy()

def terminos_top(tok, w, k=8):
    ids = np.argsort(-w)[:k]
    return [(tok.convert_ids_to_tokens(int(i)), round(float(w[i]), 2)) for i in ids if w[i] > 0]

try:
    from transformers import AutoTokenizer, AutoModelForMaskedLM
    tok_s, mlm_s = AutoTokenizer.from_pretrained(SPLADE_BASE), AutoModelForMaskedLM.from_pretrained(SPLADE_BASE).to(device).eval()
    frase = ["El gato duerme en el sofá"]
    W = splade_mlm_encode(tok_s, mlm_s, frase)[0]
    print("MLM crudo · términos activos (>0):", int((W > 0).sum()), "de", len(W))
    print("top:", terminos_top(tok_s, W))
except Exception as e:
    tok_s = mlm_s = None
    print("MLM no disponible:", type(e).__name__, str(e)[:90])
''')
    nb.code(r'''
def carga_sparse():
    """Sparse aprendido con sentence-transformers.SparseEncoder; (nombre, modelo) o (None, None)."""
    try:
        from sentence_transformers import SparseEncoder
    except ImportError:
        return None, None
    for nombre in SPARSE_MODELOS:
        try:
            return nombre, SparseEncoder(nombre, device=device)
        except Exception as e:
            print(f"[sparse] {nombre}: no disponible ({type(e).__name__}: {str(e)[:60]})")
    return None, None

sparse_nombre, sparse_enc = carga_sparse()
if sparse_enc is not None:
    for b in BENCHES:
        sim = sparse_enc.similarity(sparse_enc.encode_query(b.qtxt), sparse_enc.encode_document(b.txt))
        b.S["sparse-aprendido"] = sim.cpu().numpy() if hasattr(sim, "cpu") else np.asarray(sim)
    d0 = sparse_enc.encode_document(B1.txt[:1])
    print(f"sparse aprendido = {sparse_nombre}")
    print("top términos del primer documento:", [(t, round(float(w), 2)) for t, w in sparse_enc.decode(d0[0], top_k=8)])
    display(B2.resumen())
else:
    print("No hay un modelo sparse aprendido accesible (sin red o modelo restringido): seguimos con BM25 + denso + late interaction.")
''')
    nb.md(r'''> 👀 **Qué debes observar.** (1) El MLM crudo activa **cientos o miles** de términos por frase (la mayoría con peso pequeño): sin entrenamiento y sin FLOPS no hay esparcidad; un índice invertido con eso sería inservible. (2) El modelo sparse entrenado (si lo ves) conserva decenas de términos y mezcla los de la frase con expansiones. (3) En el banco de **paráfrasis** el sparse aprendido debería superar a BM25, pero **no** reemplaza a un buen denso multilingüe en consultas entre idiomas (depende del checkpoint: los modelos de SPLADE originales son monolingües en inglés).
''')

    # ───────────────────────────── 4. ColBERT / MaxSim ─────────────────────────────
    nb.md(r'''## 4 · Late interaction: ColBERT y MaxSim desde cero

**Idea (Khattab & Zaharia, 2020).** El bi-encoder denso comprime el texto en un punto. ColBERT guarda **un vector por token** (normalizado, $d=128$ tras una proyección lineal sobre BERT) y calcula la relevancia con una **interacción tardía** barata (sin pasar los dos textos juntos por un transformer):

$$S(q,d)=\sum_{i=1}^{|q|}\;\max_{j=1}^{|d|}\;\langle \hat{q}_i,\hat{d}_j\rangle$$

Cada token de la query "busca" su mejor pareja en el documento y se suman las similitudes. Sigue siendo **precomputable** para los documentos (como un bi-encoder) pero conserva información fina por token. Detalles del paper original: marcadores `[Q]`/`[D]`, *query augmentation* (se rellena la query con `[MASK]` hasta una longitud fija, que actúa como expansión suave) y filtrado de puntuación en el documento.

**ColBERTv2 (Santhanam et al., 2021)** ataca el almacenamiento con **compresión residual**: guarda el id del **centroide** más cercano y el residuo $r=v-c$ cuantizado a 1–2 bits por dimensión (el paper informa reducciones del espacio de 6–10×), además de entrenar con supervisión destilada de un cross-encoder y *hard negatives*. **PLAID (2022)** acelera la búsqueda con **interacción por centroides** y poda de candidatos.

**Coste:** un documento de 200 tokens con $d=128$ en `float16` ocupa $200\times128\times2=51.2$ KB (¡frente a 2 KB de un vector denso de 1024 en `float16`!). Este es el límite práctico de la técnica.
''')
    nb.code(r'''
import zlib
_BANCO_NGRAMAS = {}

def vec_ngrama(g, d):
    v = _BANCO_NGRAMAS.get((g, d))
    if v is None:
        v = np.random.default_rng(zlib.crc32(g.encode())).normal(size=d).astype(np.float32)
        _BANCO_NGRAMAS[(g, d)] = v
    return v

def vec_token(tok, d=64):
    """Embedding de JUGUETE de un token: suma de vectores aleatorios deterministas de sus 3-gramas de caracteres.
    Palabras que comparten letras (indexación/indexar) quedan cerca. No es semántico, pero hace los ejemplos reproducibles."""
    w = f"<{tok}>"
    grams = [w[i:i + 3] for i in range(len(w) - 2)] or [w]
    v = sum(vec_ngrama(g, d) for g in grams)
    return v / np.linalg.norm(v)

def multi_juguete(textos, d=64, max_tok=48):
    out = []
    for t in textos:
        tk = toks(t)[:max_tok] or ["vacio"]
        out.append(np.stack([vec_token(x, d) for x in tk]).astype(np.float32))
    return out

def maxsim(Q, D):
    """Q (nq,d), D (nd,d), filas normalizadas. S = suma_i max_j <q_i, d_j>."""
    return float((Q @ D.T).max(axis=1).sum())

def maxsim_matriz(QV, DV, trozo=32):
    """Todos los pares (query, doc) sin bucles de Python por documento: concatena los tokens de los documentos,
    una sola multiplicación de matrices por trozo de queries y máximos por segmento con np.maximum.reduceat."""
    Dcat = np.concatenate(DV)
    ini_d = np.cumsum([0] + [len(x) for x in DV[:-1]])
    out = np.empty((len(QV), len(DV)), np.float32)
    for s in range(0, len(QV), trozo):
        qs = QV[s:s + trozo]
        Qcat = np.concatenate(qs)
        ini_q = np.cumsum([0] + [len(x) for x in qs[:-1]])
        mx = np.maximum.reduceat(Qcat @ Dcat.T, ini_d, axis=1)          # (Tq, nd): mejor token de cada doc
        out[s:s + len(qs)] = np.add.reduceat(mx, ini_q, axis=0)          # suma sobre los tokens de cada query
    return out

t0 = time.perf_counter()
for b in BENCHES:
    b.DV, b.QV = multi_juguete(b.txt), multi_juguete(b.qtxt)
    b.S["colbert-juguete"] = maxsim_matriz(b.QV, b.DV)
print(f"MaxSim de {len(B1.qs)}x{len(B1.ids)} pares en {time.perf_counter()-t0:.2f}s")
print("coincide con la versión ingenua:", bool(np.isclose(B1.S["colbert-juguete"][3, 7], maxsim(B1.QV[3], B1.DV[7]), atol=1e-4)))
display(pd.concat({b.nombre[:12]: b.resumen() for b in BENCHES}))
''')
    nb.md(r'''> 👀 **Qué debes observar.** La versión vectorizada coincide con la fórmula ingenua. El "ColBERT de juguete" usa embeddings de tokens por 3-gramas de caracteres (léxicos, no semánticos): se comporta como un **BM25 difuso** (hace match de variantes ortográficas) y sirve para entender el *mecanismo*. Con embeddings contextuales entrenados (ColBERT real, BGE-M3 más abajo) cada token ya incorpora el contexto y la sinonimia.
''')
    nb.gemini(
        "video", "M13-VID-01", "MaxSim token a token",
        "Animación de cómo cada token de la consulta busca su mejor pareja entre los tokens del documento y cómo se suman los máximos (ejemplo con números exactos).",
        """
        Video explicativo 16:9, fondo blanco, estilo diagrama técnico limpio, paleta azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280, tipografía sans-serif, ritmo calmado, SIN voz en off ni música; solo texto en pantalla en español (términos técnicos en inglés).

        Datos EXACTOS (no inventar otros). Tokens de la consulta (columna izquierda, azul): "buscar", "vecinos", "red". Tokens del documento (fila superior, gris): "grafo", "capas", "vecinos", "búsqueda". Matriz de similitudes (filas = tokens de la consulta, columnas = tokens del documento):
        buscar  : grafo 0.12, capas 0.08, vecinos 0.35, búsqueda 0.82
        vecinos : grafo 0.20, capas 0.10, vecinos 0.91, búsqueda 0.30
        red     : grafo 0.78, capas 0.25, vecinos 0.22, búsqueda 0.15

        Escena 1 (0–5 s): título "ColBERT: late interaction con MaxSim". Aparecen a la izquierda los 3 tokens de la consulta como cajitas azules y arriba los 4 tokens del documento como cajitas grises.
        Escena 2 (5–12 s): se rellena la matriz 3×4 con los 12 números, celda a celda, con un degradado de color según el valor.
        Escena 3 (12–20 s): fila por fila, se resalta en verde el máximo de cada fila ("buscar → búsqueda 0.82", "vecinos → vecinos 0.91", "red → grafo 0.78") y se dibuja una línea verde entre el token de la consulta y su mejor pareja; los demás valores se atenúan.
        Escena 4 (20–26 s): los tres máximos viajan a una suma en el lado derecho: "0.82 + 0.91 + 0.78 = 2.51" con el rótulo "score MaxSim = 2.51".
        Escena 5 (26–30 s): texto final "Cada token de la consulta elige su mejor pareja; el documento no se comprime en un solo vector".

        Evita: voz, música, números distintos de los dados, texto ilegible, elementos decorativos, cambios bruscos de cámara.
        """,
        "Animación de la matriz de similitudes 3x4 con los máximos por fila sumados en un score de 2.51",
        """
                      grafo  capas  vecinos  búsqueda
        buscar         0.12   0.08   0.35    [0.82]
        vecinos        0.20   0.10  [0.91]    0.30
        red           [0.78]  0.25   0.22     0.15
        MaxSim = 0.82 + 0.91 + 0.78 = 2.51
        """,
        duration="30 s",
    )
    nb.md(r'''> 👀 **Qué debes observar.** El score no es un coseno único sino la **suma de tres emparejamientos independientes**: cada token de la consulta elige su mejor pareja, aunque esté en otra posición del documento. Por eso late interaction tolera bien reordenamientos y paráfrasis parciales, y por eso "explica" qué parte del documento justificó el score.
''')
    nb.code(r'''
def heatmap_maxsim(q_toks, Q, d_toks, D, titulo):
    S = Q @ D.T
    fig, ax = plt.subplots(figsize=(0.6 * len(d_toks) + 3, 0.5 * len(q_toks) + 1.6))
    im = ax.imshow(S, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(d_toks))); ax.set_xticklabels(d_toks, rotation=60, ha="right", fontsize=8)
    ax.set_yticks(range(len(q_toks))); ax.set_yticklabels(q_toks, fontsize=8)
    for i, j in enumerate(S.argmax(1)):
        ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, ec="#F28E2B", lw=2.2))
    ax.set_title(f"{titulo}\nMaxSim = {S.max(1).sum():.2f}", fontsize=10)
    plt.colorbar(im, ax=ax, fraction=0.03); plt.tight_layout(); plt.show()

par = {k[0]: k for k in PARAFRASIS}["hnsw"]
q_t, d_t = toks(par[5]), toks(par[2])                       # query en español y documento en español
heatmap_maxsim(q_t, multi_juguete([par[5]])[0], d_t[:24], multi_juguete([par[2]])[0][:24], "Matriz token-token (embeddings de juguete)")
''')
    nb.md(r'''> 👀 **Qué debes observar.** Los recuadros naranjas son los máximos por fila (el `max` de MaxSim). Con vectores de juguete solo hay similitud alta entre palabras con letras en común ("vectores"/"vecinos", "grafo"); con ColBERT entrenado la fila "buscar" apuntaría a "búsqueda" o "devolviendo" por **significado**. Observa también que las palabras vacías (artículos, preposiciones) también aportan; ColBERT original filtra puntuación pero no stopwords.

### Coste de almacenamiento y compresión residual (ColBERTv2, versión mini)
Aprendemos $K$ centroides con k-means sobre los vectores de token; guardamos por token el **id del centroide** (1 byte para $K\le256$) y el **residuo** $v-c$ cuantizado a $n$ bits por dimensión (con umbrales por cuantiles; reconstruimos con la media de cada cubeta).
''')
    nb.code(r'''
from sklearn.cluster import KMeans

def comprime_residual(V, C, nbits):
    """ColBERTv2 en pequeño: (id de centroide, residuo cuantizado a nbits por dimensión). Devuelve datos para reconstruir."""
    a = (-2 * V @ C.T + (C ** 2).sum(1)).argmin(1)
    R = V - C[a]
    umbrales = np.quantile(R, np.linspace(0, 1, 2 ** nbits + 1)[1:-1]) if nbits > 1 else np.array([0.0])
    codigos = np.digitize(R, umbrales)
    valores = np.array([R[codigos == k].mean() if (codigos == k).any() else 0.0 for k in range(2 ** nbits)])
    return a, codigos.astype(np.uint8), valores

def descomprime(a, codigos, valores, C):
    V = C[a] + valores[codigos]
    return (V / np.linalg.norm(V, axis=1, keepdims=True)).astype(np.float32)

b = B1
Vtodos = np.concatenate(b.DV)
longitudes = np.array([len(x) for x in b.DV]); cortes = np.cumsum(np.r_[0, longitudes])
C = KMeans(256, n_init=1, random_state=SEED).fit(Vtodos).cluster_centers_.astype(np.float32)
dim = Vtodos.shape[1]
filas = [("float32", 4 * dim, b.ndcg(b.S["colbert-juguete"]))]
filas.append(("float16", 2 * dim, b.ndcg(maxsim_matriz(b.QV, [x.astype(np.float16).astype(np.float32) for x in b.DV]))))
for nb_ in (3, 2, 1):
    a_, cod_, val_ = comprime_residual(Vtodos, C, nb_)
    Vh = descomprime(a_, cod_, val_, C)
    DVh = [Vh[cortes[i]:cortes[i + 1]] for i in range(len(b.DV))]
    filas.append((f"centroide + residuo {nb_} bit/dim", 1 + dim * nb_ / 8, b.ndcg(maxsim_matriz(b.QV, DVh))))
tabla_c = pd.DataFrame(filas, columns=["representación", "bytes por token", "nDCG@10"])
display(tabla_c.round(3))
fig, ax = plt.subplots(figsize=(6.6, 3.5))
ax.plot(tabla_c["bytes por token"], tabla_c["nDCG@10"], "o-", color="#2CA02C")
for r in tabla_c.itertuples():
    ax.annotate(r.representación, (r._2, r._3), textcoords="offset points", xytext=(4, 6), fontsize=7)
ax.set_xscale("log"); ax.set_xlabel("bytes por token (log)"); ax.set_ylabel("nDCG@10"); ax.set_title("Compresión residual: espacio vs calidad"); ax.grid(alpha=.3)
plt.tight_layout(); plt.show()
''')
    nb.md(r'''> 👀 **Qué debes observar.** Bajar de 256 B (`float32`, $d=64$) a ≈ 9–25 B por token con residuos de 1–3 bits cuesta muy poco nDCG: **los residuos tienen poca energía** una vez que restas el centroide. Esa es la idea central de ColBERTv2. Con $d=128$ y 2 bits son 33 B por token frente a 256 B en `float16`. Atención: este es un experimento a escala diminuta con embeddings de juguete; la reducción de 6–10× es la cifra que **reporta el paper** para ColBERTv2 real.

### PLAID en pequeño: interacción por centroides
Buscar con MaxSim exacto sobre toda la colección es $O(\text{tokens})$. PLAID (Santhanam et al., 2022) usa los centroides como **proxy**: cada documento se representa por el *conjunto de centroides* de sus tokens; la similitud query-centroide ($q_i\cdot c_k$) se calcula **una sola vez por query** y el score aproximado de un documento es $\tilde S(q,d)=\sum_i\max_{k\in\text{cent}(d)} q_i\cdot c_k$ (un MaxSim con vectores "cuantizados" a su centroide). Se conservan los `ncand` mejores y solo a esos se les calcula el MaxSim exacto.
''')
    nb.code(r'''
doc_de_tok = np.repeat(np.arange(len(b.DV)), longitudes)
asig = (-2 * Vtodos @ C.T + (C ** 2).sum(1)).argmin(1)
MASK_C = np.zeros((len(b.DV), len(C)), bool)
MASK_C[doc_de_tok, asig] = True                                   # doc x centroide: ¿algún token del doc cae ahí?

def interaccion_centroides(Q):
    sqc = Q @ C.T                                                 # (nq_tokens, K): una vez por query
    return np.where(MASK_C[None], sqc[:, None, :], -np.inf).max(-1).sum(0)

exacto = b.S["colbert-juguete"]
top_exacto = np.argsort(-exacto, axis=1)[:, :10]
aprox = np.stack([interaccion_centroides(Q) for Q in b.QV])
ncands = [10, 20, 50, 100, 200]
rec = []
for nc in ncands:
    top_nc = np.argsort(-aprox, axis=1)[:, :nc]
    rec.append(np.mean([len(set(top_nc[i]) & set(top_exacto[i])) / 10 for i in range(len(b.QV))]))
fig, ax = plt.subplots(figsize=(6.4, 3.4))
ax.plot([100 * n / len(b.DV) for n in ncands], rec, "o-", color="#1F6FEB")
ax.set_xlabel("% de documentos que pasan al MaxSim exacto"); ax.set_ylabel("recall del top-10 exacto")
ax.set_title("PLAID mini: filtrar con centroides antes del MaxSim exacto"); ax.grid(alpha=.3)
plt.tight_layout(); plt.show()
print({n: round(float(r), 3) for n, r in zip(ncands, rec)})
''')
    nb.md(r'''> 👀 **Qué debes observar.** Con ~12 % de los documentos pasando al MaxSim exacto ya se recupera la mayor parte del top-10 exacto: la interacción por centroides es un **filtro barato** (una multiplicación query×centroides y búsquedas en tabla). En PLAID real esto se combina con listas invertidas centroide→documentos y con poda de centroides de baja puntuación. Con vectores de juguete la curva es peor de lo que verías con ColBERT real (menos estructura de clusters).
''')
    # ───────────────────────────── 5. BGE-M3 ─────────────────────────────
    nb.md(r'''## 5 · BGE-M3: denso + sparse + multi-vector en un solo modelo

**BGE-M3** (Chen et al., 2024) es un encoder multilingüe (base XLM-RoBERTa-large, contexto de 8192 tokens) entrenado con *self-knowledge distillation* para producir **tres representaciones a la vez** desde los mismos estados ocultos $H$:

| Modo | Cálculo | Salida |
|---|---|---|
| Denso | $e=\operatorname{norm}(H_{[CLS]})$ | 1 vector |
| Sparse | $w_t=\operatorname{ReLU}(W_s h_t)$ por token; por id de token se toma el máximo | `{token_id: peso}` |
| Multi-vector | $v_t=\operatorname{norm}(W_c h_t)$ para $t\ge1$ | 1 vector por token (ColBERT) |

Aquí lo ensamblamos **a mano** con `transformers` + las dos capas lineales del repositorio (`colbert_linear.pt`, `sparse_linear.pt`), que es la estructura que documenta FlagEmbedding. Si tienes red, es la mejor forma de ver un ColBERT multilingüe real; si no, la celda avisa y seguimos con el ColBERT de juguete.
''')
    nb.code(r'''
import torch.nn.functional as F
BGE_M3 = "BAAI/bge-m3"

def carga_bge_m3(repo=BGE_M3):
    from transformers import AutoTokenizer, AutoModel
    from huggingface_hub import hf_hub_download
    tok = AutoTokenizer.from_pretrained(repo)
    mod = AutoModel.from_pretrained(repo).to(device).eval()
    h = mod.config.hidden_size
    colbert, sparse = torch.nn.Linear(h, h), torch.nn.Linear(h, 1)
    colbert.load_state_dict(torch.load(hf_hub_download(repo, "colbert_linear.pt"), map_location="cpu"))
    sparse.load_state_dict(torch.load(hf_hub_download(repo, "sparse_linear.pt"), map_location="cpu"))
    return tok, mod, colbert.to(device).eval(), sparse.to(device).eval()

@torch.no_grad()
def m3_encode(m3, textos, max_len=256, bs=16):
    tok, mod, colbert, sparse = m3
    dens, spars, mult = [], [], []
    especiales = set(tok.all_special_ids)
    for s in range(0, len(textos), bs):
        lote = tok(textos[s:s + bs], padding=True, truncation=True, max_length=max_len, return_tensors="pt").to(device)
        H = mod(**lote).last_hidden_state
        dens.append(F.normalize(H[:, 0], dim=-1).cpu())
        sw = torch.relu(sparse(H)).squeeze(-1).cpu()
        cv = F.normalize(colbert(H[:, 1:]), dim=-1).cpu()
        ids, m = lote["input_ids"].cpu(), lote["attention_mask"].cpu()
        for i in range(len(ids)):
            d = {}
            for t, w in zip(ids[i].tolist(), sw[i].tolist()):
                if t not in especiales and w > 0:
                    d[t] = max(d.get(t, 0.0), w)           # por id de token: el máximo
            spars.append(d)
            mult.append(cv[i, : int(m[i].sum()) - 1].numpy())
    return torch.cat(dens).numpy(), spars, mult

def sparse_matriz(dq, dd):
    """Scores sparse entre listas de dicts {id: peso}: producto punto de vectores dispersos (scipy)."""
    V = 1 + max(max(d, default=0) for d in dq + dd)
    def csr(ds):
        f, c, v = [], [], []
        for i, d in enumerate(ds):
            f += [i] * len(d); c += list(d); v += list(d.values())
        return sp.csr_matrix((v, (f, c)), shape=(len(ds), V))
    return (csr(dq) @ csr(dd).T).toarray()

try:
    M3 = carga_bge_m3()
    for b in BENCHES:
        dd_, sd_, md_ = m3_encode(M3, b.txt)
        dq_, sq_, mq_ = m3_encode(M3, b.qtxt)
        b.S["m3-denso"], b.S["m3-sparse"], b.S["m3-colbert"] = dq_ @ dd_.T, sparse_matriz(sq_, sd_), maxsim_matriz(mq_, md_)
        b.M3 = (mq_, md_)
    print("BGE-M3 cargado: modos denso, sparse y multi-vector disponibles")
except Exception as e:
    M3 = None
    print(f"BGE-M3 no disponible ({type(e).__name__}: {str(e)[:70]}). Seguimos con el ColBERT de juguete.")
display(pd.concat({b.nombre[:12]: b.resumen() for b in BENCHES}))
''')
    nb.md(r'''> 👀 **Qué debes observar.** Si BGE-M3 cargó, compara en el banco de **paráfrasis** sus tres modos con BM25: los modos neuronales deberían superar claramente a BM25 en consultas entre idiomas, mientras que el modo sparse (léxico aprendido) se parece más a BM25 y se comporta peor entre idiomas. En el banco canónico (alto solapamiento léxico) BM25 puede quedar muy cerca. Eso es exactamente por qué se **combinan**.

## 6 · MUVERA: de multi-vector a un solo vector de dimensión fija

**Problema.** MaxSim exige indexar *tokens* y re-puntuar; no se puede usar un índice ANN de un vector por documento. **MUVERA** (Dhulipala et al., NeurIPS 2024) construye dos funciones, $F_q$ y $F_d$, tales que $\langle F_q(Q),F_d(D)\rangle$ **aproxima** la similitud Chamfer (MaxSim) y los vectores tienen **dimensión fija**. Así se usa MIPS estándar para generar candidatos y luego se re-puntúa con MaxSim exacto.

**Construcción de las FDE (Fixed Dimensional Encodings).**
1. Se eligen $k_{sim}$ hiperplanos aleatorios (SimHash): cada vector queda en una de $B=2^{k_{sim}}$ **cubetas** según el signo de sus proyecciones.
2. Para cada cubeta $b$: **consulta** → *suma* de sus vectores; **documento** → *media* de sus vectores (si una cubeta del documento queda vacía, se rellena con el vector del documento cuya cubeta es más cercana en Hamming).
3. Se concatenan las $B$ cubetas ($B\cdot d$ números) y se **repite** $R$ veces con particiones independientes: dimensión final $R\cdot B\cdot d$ (el paper añade proyecciones aleatorias y compresión por PQ, que omitimos).

Intuición: dentro de cada cubeta el producto de las sumas/medias aproxima "cada token de la consulta con su vecino más cercano", y más cubetas/repeticiones refinan la aproximación.
''')
    nb.gemini(
        "imagen", "M13-IMG-03", "MUVERA: de muchos vectores a un vector de dimensión fija",
        "Particionado por hiperplanos (SimHash), suma/media por cubeta y concatenación en una FDE; el producto interno aproxima MaxSim.",
        """
        Diagrama técnico limpio, fondo blanco, formato 16:9. Paleta: azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280. Tipografía sans-serif. Sin ilustraciones decorativas.

        Parte izquierda: un plano 2D con puntos de dos colores (6 puntos azules = tokens de la consulta, 8 puntos naranjas = tokens del documento) dividido por 2 líneas rectas grises que cruzan el plano y crean 4 regiones etiquetadas "00", "01", "10", "11" (cubetas). Título: "1. Particionar con hiperplanos aleatorios (k = 2 → 4 cubetas)".
        Parte central: dos filas de 4 cajas (una por cubeta). Fila superior azul: "Σ vectores de la consulta en la cubeta" (suma). Fila inferior naranja: "media de los vectores del documento en la cubeta" (media); una de las cajas del documento aparece punteada con la nota "cubeta vacía → se rellena con el vector más cercano". Título: "2. Agregar por cubeta".
        Parte derecha: las 4 cajas de cada fila se concatenan en una barra horizontal larga, y esta barra aparece repetida 3 veces en columna con la etiqueta "R = 3 repeticiones con particiones distintas". Debajo, una fórmula en caja verde: "⟨F_q(Q), F_d(D)⟩ ≈ MaxSim(Q, D)" y la nota "dimensión fija = R · 2^k · d". Título: "3. Concatenar y comparar con un producto interno".
        Pie: "Después: búsqueda MIPS con ANN + re-score con MaxSim exacto".

        Evita: texto ilegible, números distintos de los dados, flechas cruzadas, logos, decoración.
        """,
        "Tres pasos de MUVERA: particionar, agregar por cubeta y concatenar en un vector de dimensión fija",
        """
        1. Particionar:  tokens -> SimHash(k=2) -> cubetas 00 01 10 11
        2. Agregar:      consulta = Σ por cubeta · documento = media por cubeta (vacías: rellenar)
        3. Concatenar:   [c00|c01|c10|c11] x R repeticiones -> vector de R·2^k·d números
           <F_q(Q), F_d(D)> ≈ MaxSim(Q,D)
        """,
    )
    nb.md(r'''> 👀 **Qué debes observar.** La asimetría: la consulta **suma** y el documento **promedia**; la comparación entre FDE es un único producto interno. La dimensión no depende del número de tokens: es el precio de convertir un problema de "conjuntos de vectores" en uno de "un vector".
''')
    nb.code(r'''
from scipy.stats import spearmanr

def fde_planos(d, k_sim, R, seed=SEED):
    return np.random.default_rng(seed).normal(size=(R, k_sim, d)).astype(np.float32)

def cubetas(V, P):
    """V (n,d), P (R,k,d) -> id de cubeta (R,n) a partir del signo de k proyecciones (SimHash)."""
    bits = (np.einsum("nd,rkd->rnk", V, P) > 0).astype(np.int64)
    return (bits * (1 << np.arange(P.shape[1]))).sum(-1)

def fde(V, P, rol):
    """Fixed Dimensional Encoding. rol='query' -> suma por cubeta; rol='doc' -> media (+ relleno de cubetas vacías)."""
    R, k, d = P.shape
    B = 1 << k
    ids = cubetas(V, P)
    out = np.zeros((R, B, d), np.float32)
    for r in range(R):
        cnt = np.bincount(ids[r], minlength=B)
        np.add.at(out[r], ids[r], V)
        if rol == "doc":
            lleno = cnt > 0
            out[r][lleno] /= cnt[lleno, None]
            for cb in np.where(~lleno)[0]:                      # relleno: el vector con cubeta más cercana en Hamming
                ham = np.array([bin(int(x) ^ cb).count("1") for x in ids[r]])
                out[r][cb] = V[ham.argmin()]
    return out.reshape(-1)

b = B1
d_tok = b.DV[0].shape[1]
exacto = b.S["colbert-juguete"]
top_ex = np.argsort(-exacto, axis=1)[:, :10]
KS, RS = (2, 3, 4), (1, 4, 16)
rho = np.zeros((len(KS), len(RS))); rec = np.zeros_like(rho); dims_fde = np.zeros_like(rho, dtype=int)
t0 = time.perf_counter()
for i, k_sim in enumerate(KS):
    for j, R in enumerate(RS):
        P = fde_planos(d_tok, k_sim, R)
        FQ = np.stack([fde(q, P, "query") for q in b.QV]); FD = np.stack([fde(x, P, "doc") for x in b.DV])
        S_f = FQ @ FD.T
        rho[i, j] = np.mean([spearmanr(S_f[n], exacto[n])[0] for n in range(0, len(b.QV), 5)])
        top50 = np.argsort(-S_f, axis=1)[:, :50]
        rec[i, j] = np.mean([len(set(top50[n]) & set(top_ex[n])) / 10 for n in range(len(b.QV))])
        dims_fde[i, j] = FQ.shape[1]
print(f"{len(KS)*len(RS)} configuraciones de FDE en {time.perf_counter()-t0:.1f}s")
''')
    nb.code(r'''
fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.6))
for ax, M, tit in ((axs[0], rho, "Correlación de Spearman con MaxSim exacto"), (axs[1], rec, "Recall del top-10 exacto dentro del top-50 de la FDE")):
    im = ax.imshow(M, cmap="Greens", vmin=0.3, vmax=1)
    ax.set_xticks(range(len(RS))); ax.set_xticklabels([f"R={r}" for r in RS]); ax.set_yticks(range(len(KS))); ax.set_yticklabels([f"k_sim={k}" for k in KS])
    for i in range(len(KS)):
        for j in range(len(RS)):
            ax.text(j, i, f"{M[i, j]:.2f}\n({dims_fde[i, j]}d)", ha="center", va="center", fontsize=8)
    ax.set_title(tit, fontsize=9); plt.colorbar(im, ax=ax, fraction=0.04)
plt.tight_layout(); plt.show()
''')
    nb.md(r'''> 👀 **Qué debes observar.** Más cubetas (`k_sim`) y más repeticiones (`R`) mejoran la correlación y el recall **a costa de dimensión** (entre paréntesis): es el mismo trade-off memoria/calidad del módulo 12. La FDE no sustituye al MaxSim exacto: es un **generador de candidatos** con un índice ANN estándar (módulo 14). El paper reporta que, a igual recall, las FDE obligan a recuperar entre 2 y 5 veces menos candidatos que las heurísticas multi-vector previas, y que se pueden comprimir ~32× con PQ; nosotros solo hemos verificado la tendencia cualitativa con vectores de juguete.

## 7 · Fusión de resultados: RRF y combinación lineal

Cada retriever devuelve scores en **escalas incompatibles** (BM25 ≈ 0–30, coseno ≈ 0–1, MaxSim ≈ 0–30). Dos familias de soluciones:

**Reciprocal Rank Fusion** (Cormack, Clarke & Büttcher, 2009): ignora los scores y usa solo el **rango**:
$$\text{RRF}(d)=\sum_{r\in\text{retrievers}}\frac{1}{k+\operatorname{rank}_r(d)},\qquad k=60\ \text{(valor del paper)}.$$

**Combinación lineal/convexa** con normalización por query: $s(d)=\alpha\,\tilde s_1(d)+(1-\alpha)\,\tilde s_2(d)$, donde $\tilde s$ es *min-max* o *z-score* de los scores de cada retriever. Bruch, Gai y Ingber (2022) analizan ambas y muestran que la combinación convexa es competitiva y eficiente en muestras de entrenamiento, mientras que RRF es más sensible a sus parámetros de lo que se suele asumir. El coste: necesitas **datos etiquetados** para elegir $\alpha$.

> ⚠️ **Tuning sin fuga.** Si eliges $\alpha$ con las mismas queries con las que evalúas, sobreestimas. Abajo usamos **validación cruzada de 2 pliegues** sobre las queries.
''')
    nb.code(r'''
def minmax(S):
    lo, hi = S.min(1, keepdims=True), S.max(1, keepdims=True)
    return (S - lo) / np.maximum(hi - lo, 1e-9)

def zscore(S):
    return (S - S.mean(1, keepdims=True)) / np.maximum(S.std(1, keepdims=True), 1e-9)

def rrf(Ss, k=60, pesos=None):
    """Fusión RRF de varias matrices de scores (nq, nd). Devuelve una matriz de scores fusionados."""
    pesos = pesos or [1.0] * len(Ss)
    out = np.zeros_like(Ss[0], dtype=float)
    for S, w in zip(Ss, pesos):
        rangos = np.argsort(np.argsort(-S, axis=1), axis=1) + 1          # rango 1..nd de cada doc
        out += w / (k + rangos)
    return out

def lineal(Ss, pesos, norm=minmax):
    return sum(w * norm(S) for w, S in zip(pesos, Ss))

def alfa_cv(b, S1, S2, norm=minmax, grid=np.linspace(0, 1, 21)):
    """alfa elegido en un pliegue y evaluado en el otro (2 pliegues, semilla fija). Devuelve nDCG medio de validación."""
    rng = np.random.default_rng(SEED); idx = rng.permutation(len(b.qs)); mitades = np.array_split(idx, 2)
    res = []
    for tr, te in (mitades, mitades[::-1]):
        mejor = max(grid, key=lambda a: b.ndcg_q(lineal([S1, S2], [a, 1 - a], norm))[tr].mean())
        res.append(b.ndcg_q(lineal([S1, S2], [mejor, 1 - mejor], norm))[te].mean())
    return float(np.mean(res))

for b in BENCHES:
    b.S["rrf(bm25+denso)"] = rrf([b.S["bm25"], b.S["denso"]])
    b.S["rrf(bm25+denso+colbert)"] = rrf([b.S["bm25"], b.S["denso"], b.S["colbert-juguete"]])
    b.S["lineal(bm25,denso) α=0.5"] = lineal([b.S["bm25"], b.S["denso"]], [0.5, 0.5])
    b.cv = alfa_cv(b, b.S["bm25"], b.S["denso"])
    print(f"{b.nombre[:22]:>22}: lineal con α elegido por CV (2 pliegues) → nDCG@10 = {b.cv:.3f}")
display(pd.concat({b.nombre[:12]: b.resumen() for b in BENCHES}))
''')
    nb.code(r'''
alfas = np.linspace(0, 1, 21)
fig, axs = plt.subplots(1, 2, figsize=(11.5, 3.6))
for ax, b in zip(axs, BENCHES):
    for nombre, norm, col in (("min-max", minmax, "#1F6FEB"), ("z-score", zscore, "#2CA02C")):
        ax.plot(alfas, [b.ndcg(lineal([b.S["bm25"], b.S["denso"]], [a, 1 - a], norm)) for a in alfas], label=f"lineal ({nombre})", color=col)
    ax.axhline(b.ndcg(b.S["rrf(bm25+denso)"]), color="#F28E2B", ls="--", label="RRF (k=60)")
    ax.axhline(b.ndcg(b.S["bm25"]), color="#6B7280", ls=":", label="solo BM25"); ax.axhline(b.ndcg(b.S["denso"]), color="#9467BD", ls=":", label="solo denso")
    ax.set_title(b.nombre, fontsize=10); ax.set_xlabel("α (peso de BM25)"); ax.set_ylabel("nDCG@10"); ax.grid(alpha=.3); ax.legend(fontsize=7)
plt.tight_layout(); plt.show()

nombres = [n for n in ("bm25", "denso", "colbert-juguete") + (("m3-denso", "m3-sparse", "m3-colbert") if M3 else ()) if n in B1.S]
top10 = {n: [set(r) for r in B1.run(B1.S[n]).values()] for n in nombres}
J = np.array([[np.mean([len(a & c) / max(len(a | c), 1) for a, c in zip(top10[x], top10[y])]) for y in nombres] for x in nombres])
fig, ax = plt.subplots(figsize=(4.8 + 0.3 * len(nombres), 3.8))
im = ax.imshow(J, cmap="Blues", vmin=0, vmax=1)
ax.set_xticks(range(len(nombres))); ax.set_xticklabels(nombres, rotation=45, ha="right", fontsize=8); ax.set_yticks(range(len(nombres))); ax.set_yticklabels(nombres, fontsize=8)
for i in range(len(nombres)):
    for j in range(len(nombres)):
        ax.text(j, i, f"{J[i, j]:.2f}", ha="center", va="center", fontsize=7)
ax.set_title("Solapamiento (Jaccard) de los top-10", fontsize=10); plt.tight_layout(); plt.show()
''')
    nb.md(r'''> 👀 **Qué debes observar.** (1) Arriba: si un retriever es mucho mejor que el otro, la fusión **no mejora** al mejor (y puede empeorar): la fusión paga cuando los dos son **comparables y complementarios**. (2) La curva en α muestra cuánto sufre la combinación lineal con una mala elección de α o de normalización, mientras RRF no tiene ese dial pero tampoco puede aprovechar un retriever claramente superior. (3) Abajo: *Jaccard bajo entre dos retrievers = errores distintos = fusión útil*; Jaccard alto entre BM25 y el sparse aprendido es esperable (ambos son léxicos).
''')
    # ───────────────────────────── 8. Rerankers ─────────────────────────────
    nb.md(r'''## 8 · Rerankers cross-encoder: la etapa cara que decide el top-10

Un **cross-encoder** concatena `[CLS] query [SEP] documento [SEP]`, lo pasa **junto** por un transformer (la atención cruza ambos textos) y una capa lineal produce un único logit de relevancia. Es la forma más precisa de puntuar un par, pero:

- **No se puede precomputar**: hace falta un forward *por candidato y por query*.
- El coste crece **linealmente con la profundidad** $K$ del reranking y con la longitud del par.

Por eso el patrón universal es **recuperar → reordenar**: un retriever barato (híbrido) devuelve $K=20$–$200$ candidatos y el cross-encoder reordena solo esos (Nogueira & Cho, 2019, fue el primer BERT reranker de pasajes). Opciones abiertas multilingües: `BAAI/bge-reranker-v2-m3` (basado en BGE-M3), `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` (pequeño, entrenado con mMARCO) y los rerankers basados en LLM (Qwen3-Reranker, bge-reranker-v2-gemma), más precisos y más caros.

En esta celda se usa un cross-encoder real si se puede descargar. **Si no, se usa un "reranker de respaldo" que NO es un cross-encoder** (MaxSim de juguete): sirve para ejecutar el pipeline y medir costes, no para sacar conclusiones de calidad.
''')
    nb.code(r'''
RERANK_MODELOS = ["cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"] + (["BAAI/bge-reranker-v2-m3"] if device == "cuda" else [])

class RerankerRespaldo:
    """⚠️ NO es un cross-encoder: puntúa pares con el MaxSim de juguete (solo para ejecutar el pipeline sin descargas)."""
    es_real = False
    def predict(self, pares, **kw):
        return np.array([maxsim(multi_juguete([q])[0], multi_juguete([d])[0]) / max(len(toks(q)), 1) for q, d in pares])

def carga_reranker():
    from sentence_transformers import CrossEncoder
    for nombre in RERANK_MODELOS:
        try:
            ce = CrossEncoder(nombre, device=device, max_length=256)
            ce.es_real = True
            return nombre, ce
        except Exception as e:
            print(f"[reranker] {nombre}: no disponible ({type(e).__name__}: {str(e)[:60]})")
    print("[reranker] usando reranker de respaldo (NO es un cross-encoder)")
    return "respaldo (MaxSim de juguete)", RerankerRespaldo()

ce_nombre, ce = carga_reranker()
NQ_REN = 30 if FAST_DEV_RUN else None          # nº de queries para medir el reranking (el cross-encoder es lento en CPU)

def reordena(b, S_primera, profundidad, nq=NQ_REN):
    """Devuelve (run, segundos_por_query): reordena el top-`profundidad` de S_primera con el cross-encoder."""
    run, t0 = {}, time.perf_counter()
    qs = list(enumerate(b.qs))[:nq]
    for i, q in qs:
        cand = np.argsort(-S_primera[i])[:profundidad]
        sc = np.asarray(ce.predict([(b.qtxt[i], b.txt[j]) for j in cand], batch_size=16, show_progress_bar=False)).ravel()
        run[q["qid"]] = [b.ids[cand[k]] for k in np.argsort(-sc)]
    return run, (time.perf_counter() - t0) / len(qs)

def ndcg_subconjunto(b, run):
    return float(np.mean([ndcg_at_k(run[q], b.qrels[q], 10) for q in run]))

b = B1
S_hibrido = b.S["lineal(bm25,denso) α=0.5"]
profundidades = [10, 20, 50]
res_r, lat_r = [], []
base_run = b.run(S_hibrido, 10)
nq_eval = NQ_REN or len(b.qs)
sub = {q["qid"] for q in b.qs[:nq_eval]}
base = ndcg_subconjunto(b, {k: v for k, v in base_run.items() if k in sub})
for K in profundidades:
    run, seg = reordena(b, S_hibrido, K)
    res_r.append(ndcg_subconjunto(b, run)); lat_r.append(seg * 1e3)
print(f"reranker = {ce_nombre} · nDCG@10 sin rerank (mismas {nq_eval} queries) = {base:.3f}")
print({K: (round(r, 3), f"{l:.0f} ms/query") for K, r, l in zip(profundidades, res_r, lat_r)})
fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.4))
axs[0].plot(profundidades, res_r, "o-", color="#1F6FEB", label="con rerank"); axs[0].axhline(base, color="#6B7280", ls="--", label="híbrido sin rerank")
axs[0].set_xlabel("profundidad K del reranking"); axs[0].set_ylabel("nDCG@10"); axs[0].set_title("Calidad vs profundidad"); axs[0].legend(); axs[0].grid(alpha=.3)
axs[1].plot(profundidades, lat_r, "s-", color="#F28E2B"); axs[1].set_xlabel("profundidad K del reranking"); axs[1].set_ylabel("ms por query (este hardware)")
axs[1].set_title("Latencia ≈ lineal en K"); axs[1].grid(alpha=.3)
plt.tight_layout(); plt.show()
''')
    nb.md(r'''> 👀 **Qué debes observar.** (1) La latencia crece casi **linealmente** con $K$: el presupuesto de latencia fija la profundidad máxima. (2) La calidad suele subir al principio y **se aplana** (o incluso baja) cuando $K$ es grande: más candidatos = más oportunidades de que el reranker promueva un falso positivo. (3) Si ves `respaldo`, la curva de calidad no significa nada; la de latencia sí es ilustrativa. Con un cross-encoder real y el banco de paráfrasis (donde el híbrido deja el documento correcto en posiciones 5–30) es donde el reranker marca la diferencia.

## 9 · Late chunking: contexto antes de trocear

**Problema.** Para indexar documentos largos se parten en *chunks* y se embebe cada uno **por separado**; un chunk como "Su población supera los treinta mil habitantes" pierde el sujeto (¿de quién?). **Late chunking** (Günther et al., 2024) invierte el orden: pasa el **documento completo** por el transformer (de contexto largo) y **después** hace el pooling de los estados de los tokens de cada chunk. Así los vectores de cada chunk "han visto" el resto del documento durante la atención.

$$\text{naive: } e_c=\operatorname{pool}\big(f(\text{chunk}_c)\big)\qquad\text{late: } e_c=\operatorname{pool}\big(\{h_t\}_{t\in c}\big),\;\; h=f(\text{documento completo})$$

Requiere: un encoder con contexto suficiente para el documento, y acceso a los **estados a nivel de token** (no todas las APIs los exponen). No cambia el entrenamiento del modelo (aunque se puede afinar). Estado: 🟡.

Lo medimos con un ejemplo mínimo: dos ciudades ficticias con un segundo chunk **idéntico en forma** ("Su población supera…"). La pregunta nombra la ciudad; solo el contexto permite saber de cuál es cada chunk.
''')
    nb.code(r'''
CIUDADES = {
    "Villaverde del Río": "Villaverde del Río es una ciudad situada junto a un gran río navegable. Su población supera los treinta mil habitantes. Su casco antiguo conserva un puente romano.",
    "Montealegre": "Montealegre es una villa de montaña rodeada de pinares. Su población supera los cinco mil habitantes. Su casco antiguo conserva un castillo medieval.",
}

def trozos(texto):
    """Chunks = frases; devuelve [(inicio_car, fin_car)]."""
    return [(m.start(), m.end()) for m in re.finditer(r"[^.]+\.", texto)]

@torch.no_grad()
def embebe_tokens(tok, modelo, texto, prefijo=""):
    enc = tok(prefijo + texto, return_offsets_mapping=True, return_tensors="pt", truncation=True, max_length=512)
    off = enc.pop("offset_mapping")[0].tolist()
    H = modelo(**{k: v.to(device) for k, v in enc.items()}).last_hidden_state[0].cpu()
    return H, off

def pool_span(H, off, a, b):
    idx = [i for i, (s, e) in enumerate(off) if e > s and s >= a and e <= b]
    return F.normalize(H[idx].mean(0), dim=-1)

def chunks_naive(tok, modelo, texto, prefijo=""):
    out = []
    for a, b_ in trozos(texto):
        H, off = embebe_tokens(tok, modelo, texto[a:b_].strip(), prefijo)
        out.append(pool_span(H, off, len(prefijo), len(prefijo) + len(texto[a:b_].strip())))
    return torch.stack(out)

def chunks_late(tok, modelo, texto, prefijo=""):
    H, off = embebe_tokens(tok, modelo, texto, prefijo)                      # documento completo, UNA pasada
    return torch.stack([pool_span(H, off, a + len(prefijo), b_ + len(prefijo)) for a, b_ in trozos(texto)])

if emb.is_real and hasattr(emb.model, "tokenizer"):
    tok_e, mod_e = emb.model.tokenizer, emb.model[0].auto_model.to(device).eval()
    pref = emb.cfg.get("d", "")
    texto_q = emb._enc(["¿Cuántos habitantes tiene Villaverde del Río?"], emb.cfg.get("q", ""))[0]
    filas = []
    for nombre, texto in CIUDADES.items():
        for modo, fn in (("naive", chunks_naive), ("late", chunks_late)):
            E = fn(tok_e, mod_e, texto, pref).numpy()
            filas.append({"ciudad del chunk": nombre, "modo": modo, "cos(query, chunk 'Su población…')": round(float(E[1] @ texto_q), 3)})
    tabla_lc = pd.DataFrame(filas)
    display(tabla_lc)
    piv = tabla_lc.pivot(index="modo", columns="ciudad del chunk", values="cos(query, chunk 'Su población…')")
    piv["margen (Villaverde − Montealegre)"] = piv["Villaverde del Río"] - piv["Montealegre"]
    display(piv.round(3))
    fig, ax = plt.subplots(figsize=(5.6, 3.2))
    ax.bar(piv.index, piv["margen (Villaverde − Montealegre)"], color=["#F28E2B", "#2CA02C"])
    ax.axhline(0, color="k", lw=.8); ax.set_ylabel("margen de coseno"); ax.set_title("¿Distingue el chunk de la ciudad correcta?")
    plt.tight_layout(); plt.show()
else:
    print("late chunking necesita un embedder real con acceso a los estados por token; celda omitida (modo respaldo).")
''')
    nb.md(r'''> 👀 **Qué debes observar.** Con *naive chunking* los dos chunks "Su población supera…" son casi indistinguibles para la query (margen ≈ 0 o aleatorio). Con *late chunking* el chunk de Villaverde "hereda" el nombre de la ciudad por la atención y el **margen debería ser positivo**. Es un efecto **dependiente del modelo**: con un modelo muy pequeño o sin pooling medio puede ser débil o nulo (no lo asumas, mídelo). Si se ejecutó con el modelo de pesos aleatorios del entorno de pruebas, los números no significan nada.
''')

    # ───────────────────────────── 10. Pipeline y costes ─────────────────────────────
    nb.md(r'''## 10 · El pipeline híbrido de referencia y su coste de almacenamiento

```
              ┌──────────────► BM25 / sparse aprendido ─┐   (índice invertido, filtros exactos)
 query ──────►┼──────────────► denso (1 vector, ANN)  ──┼─► fusión (RRF / convexa) ─► top-100 ─► [rerank cross-encoder] ─► top-10
              └──────────────► late interaction ────────┘   (multi-vector o MUVERA + MaxSim exacto)
```
Cada rama aporta algo distinto; la rama de late interaction es la más cara de **almacenar**. Cuánto, con supuestos explícitos (10 M de documentos de 200 tokens; `float16` donde se indica):
''')
    nb.gemini(
        "imagen", "M13-IMG-04", "Pipeline híbrido: recuperar, fusionar, reordenar",
        "Las ramas de recuperación (léxica, densa, late interaction), la fusión, la etapa de reranking y los tamaños de candidatos en cada paso.",
        """
        Diagrama técnico limpio, fondo blanco, formato 16:9. Paleta: azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280. Tipografía sans-serif. Sin decoración.

        De IZQUIERDA a DERECHA. A la izquierda una caja gris "Consulta del usuario". De ella salen TRES flechas hacia tres cajas apiladas verticalmente:
        - Caja naranja "Léxico: BM25 / SPLADE" con subtítulo "índice invertido · filtros exactos".
        - Caja azul "Denso: 1 vector" con subtítulo "ANN (HNSW)".
        - Caja verde "Late interaction: ColBERT / MUVERA" con subtítulo "multi-vector · MaxSim".
        Cada caja emite una flecha con la etiqueta "top-100" hacia una caja central gris oscuro "Fusión (RRF o combinación convexa)". De la fusión sale una flecha "top-50" hacia una caja azul oscuro "Reranker cross-encoder" con subtítulo "1 forward por candidato". La flecha final sale hacia una caja verde "Top-10 para el usuario".
        Bajo las cajas, una barra de tiempo en gris con tres tramos proporcionales y etiquetas: "recuperación: ms", "fusión: <1 ms", "rerank: decenas de ms".

        Evita: texto ilegible, flechas cruzadas confusas, cifras de latencia concretas, logos, decoración.
        """,
        "Tres ramas de recuperación que se fusionan y pasan por un reranker antes del top-10",
        """
        query -> [BM25/SPLADE] --\
              -> [Denso (ANN)] ---+-> [Fusión RRF/convexa] -> top-50 -> [Cross-encoder] -> top-10
              -> [ColBERT/MUVERA] /
        """,
    )
    nb.code(r'''
N, TOK = 10_000_000, 200
def gb(bytes_por_doc): return N * bytes_por_doc / 1e9
R_f, k_f, d_f = 20, 4, 16                                          # parámetros de ejemplo de una FDE
filas = [
    ("BM25 (≈120 postings × 6 B)*", 120 * 6),
    ("SPLADE (≈150 términos × 6 B)*", 150 * 6),
    ("Denso 1024 d float32", 1024 * 4),
    ("Denso 256 d int8 (Matryoshka+int8)", 256),
    ("ColBERT 128 d float16 (200 tok)", TOK * 128 * 2),
    ("ColBERTv2: id centroide + residuo 2 bit (33 B/token)", TOK * 33),
    (f"MUVERA FDE R={R_f}, k={k_f}, d={d_f} float32", R_f * (1 << k_f) * d_f * 4),
]
costos = pd.DataFrame(filas, columns=["representación", "bytes por documento"])
costos["GB para 10 M docs"] = costos["bytes por documento"].map(gb).round(1)
display(costos)
fig, ax = plt.subplots(figsize=(8, 3.4))
ax.barh(costos["representación"], costos["GB para 10 M docs"], color=["#F28E2B", "#F28E2B", "#1F6FEB", "#1F6FEB", "#2CA02C", "#2CA02C", "#2CA02C"])
ax.set_xscale("log"); ax.invert_yaxis(); ax.set_xlabel("GB (escala log) para 10 M de documentos"); ax.set_title("Coste de almacenamiento por paradigma")
plt.tight_layout(); plt.show()
print("* estimaciones de orden de magnitud con supuestos explícitos; el tamaño real depende del motor (compresión de postings, etc.)")
''')
    nb.md(r'''> 👀 **Qué debes observar.** Entre el denso Matryoshka+`int8` y el ColBERT sin comprimir hay **tres órdenes de magnitud** (decenas de GB frente a decenas de TB). La compresión residual y MUVERA acercan late interaction a un presupuesto razonable, pero siguen siendo la rama más pesada: por eso muchos sistemas la usan solo como **reranker de los mejores candidatos** (como hace Qdrant en su tutorial, desactivando HNSW en el campo multivector) en lugar de como primer etapa.

**Cuándo NO usar cada cosa.** *Sparse aprendido:* si tu corpus es muy corto o dominado por identificadores, BM25 basta. *Denso:* no como único retriever si hay consultas con códigos o nombres exactos. *Late interaction:* si el presupuesto de almacenamiento es ajustado y un reranker cross-encoder sobre el top-50 ya cumple. *Cross-encoder:* si el presupuesto de latencia no permite $K$ forwards.
''')

    # ───────────────────────────── 11. Producción ─────────────────────────────
    nb.md(r'''## 11 · 🏭 En producción

- **Vespa** ofrece un *embedder* ColBERT nativo y expresa MaxSim en su lenguaje de ranking; su blog describe una compresión asimétrica de los vectores de token de hasta 32× (binarización en los documentos) y una variante de contexto largo (Long-ColBERT).
- **Qdrant** soporta campos **multivector** con comparador `MAX_SIM`; su tutorial recomienda usarlo para *reranking* y desactivar el índice HNSW de ese campo (`m=0`) para ahorrar cómputo y memoria.
- **Weaviate** documenta una opción de **codificación MUVERA** para reducir la memoria de los embeddings multi-vector, recomendándola para modelos tipo ColPali (módulo 16).
- **Elastic** ofrece ELSER (sparse aprendido, campo `sparse_vector`, flujo `semantic_text`) y **OpenSearch** el *neural sparse search*, incluyendo checkpoints multilingües e *inference-free* (Geng et al., 2024).
- **Jina** publicó Jina-ColBERT-v2 (89 idiomas, documentos de hasta 8192 tokens, consultas de 32, dimensiones de salida 128/96/64 por Matryoshka) y la técnica de late chunking.
- **BAAI**: BGE-M3 (tres modos) y `bge-reranker-v2-m3`.
- **Patrón común**: búsqueda híbrida (léxico + denso) como configuración por defecto de los motores modernos, con fusión RRF o convexa, y un reranker sobre el top-$K$ con $K$ de decenas.
''')
    nb.md(r'''## 12 · 🧠 Secretos de la élite

1. **Ablación antes que arquitectura.** Mide cada retriever solo y luego cada combinación (como hicimos): un sistema con cuatro ramas sin ablaciones es una apuesta. Si una rama no mejora el nDCG en tu golden set, quítala (menos infraestructura que operar).
2. **RRF con $k=60$ es una convención, no una ley** (Cormack et al., 2009); con pocos retrievers el valor de $k$ cambia poco, pero Bruch et al. (2022) muestran que RRF es más sensible a sus parámetros de lo que se cree y que una combinación convexa bien normalizada es competitiva: si tienes etiquetas, **tunea α con validación cruzada** (no en las mismas queries de test).
3. **La normalización decide la combinación lineal.** Min-max es frágil ante un único documento con score extremo (comprime al resto); z-score por query o normalizar sobre el top-$K$ son alternativas habituales. Prueba las tres.
4. **El analyzer de BM25 es parte del modelo.** Tildes, minúsculas, stemming y separación de identificadores (`snake_case`, `CamelCase`, versiones) cambian el nDCG más que ajustar $k_1$ o $b$ (módulos 01–05). Indexar el identificador completo **y** sus partes es una práctica habitual.
5. **Late interaction se paga en almacenamiento, no en cómputo de consulta.** Comprime (residual, binarización, MUVERA+PQ) y úsala como reranker de un subconjunto cuando puedas; Jina-ColBERT-v2 ofrece dimensiones de salida reducidas (128/96/64) por esta razón.
6. **MUVERA es un generador de candidatos, no un sustituto del MaxSim.** El paper lo usa como paso previo y re-puntúa con Chamfer exacto; reporta recuperar 2–5× menos candidatos que heurísticas previas a igual recall (resultado del paper, no verificado aquí).
7. **El reranker se puede romper por distribución.** Un cross-encoder entrenado en MS MARCO (inglés/web) puede degradar el orden en documentación técnica en español o en código; mídelo en tu golden set **antes** de ponerlo en el camino crítico. Fija un presupuesto de latencia p95 y calcula $K$ máximo a partir de él.
8. **Late chunking exige una cadena técnica coherente**: encoder de contexto largo, acceso a estados por token y pooling consistente con el entrenamiento (media). No lo actives "por moda": mídelo con consultas cuyo sujeto está en otro chunk.
9. **Filtros y sparse**: un índice invertido aplica filtros duros (idioma, versión, permisos) de forma exacta y barata; en ANN denso los filtros son un problema abierto (módulo 14). Esto es un argumento a favor de mantener la rama léxica aunque el denso sea mejor en promedio.
''')
    nb.md(r'''## 13 · ⚠️ Errores comunes

| Error | Síntoma | Arreglo |
|---|---|---|
| Sumar scores crudos de BM25 y coseno | un retriever domina siempre | normalizar por query o usar RRF |
| Elegir α en las queries de test | mejora "mágica" que no se reproduce | validación cruzada / split de tuning |
| Comparar BM25 de una librería con otra sin igualar el IDF y los tokens | diferencias de varios puntos | fijar variante de IDF, $k_1$, $b$ y analyzer |
| MaxSim con vectores sin normalizar | scores dominados por la norma | normalizar los vectores de token |
| Olvidar enmascarar el padding en MaxSim | tokens de relleno puntúan | usar solo posiciones con `attention_mask=1` |
| Rerank con $K$ enorme | latencia p99 fuera de SLA | calcular $K$ desde el presupuesto |
| Usar un reranker sin mirar el idioma/dominio | orden peor que sin reranker | evaluar en el golden set |
| Indexar vectores multi-vector sin plan de compresión | índice de TB | residual / binarización / MUVERA |
| Duplicados en el top-K de varias ramas | RRF cuenta dos veces el mismo doc | deduplicar por id antes de fusionar |
''')
    nb.md(r'''## 14 · Autoevaluación

<details><summary><b>1 · (Cálculo)</b> MaxSim con $q=\{q_1,q_2\}$ y un documento de 3 tokens. Las similitudes son $q_1:[0.1,0.7,0.3]$ y $q_2:[0.6,0.2,0.5]$. ¿Cuál es el score y qué pasaría si el documento tuviera un cuarto token con similitud 0.9 para $q_1$ y 0.1 para $q_2$?</summary>

Score $=\max(q_1)+\max(q_2)=0.7+0.6=1.3$. Con el cuarto token: $0.9+0.6=1.5$ (solo $q_1$ mejora; $q_2$ ya tenía su mejor pareja). Un token extra **nunca baja** el score MaxSim, por eso los documentos largos tienen ventaja (en ColBERT se compensa con la longitud máxima del documento).
</details>

<details><summary><b>2 · (Cálculo)</b> Dos retrievers dan a un documento los rangos 1 y 3. ¿Cuál es su score RRF con $k=60$? ¿Y otro documento con rangos 2 y 2?</summary>

$1/61+1/63\approx0.01639+0.01587=0.03226$. El otro: $2/62=0.03226$. Prácticamente **empate**: RRF premia la consistencia y casi no distingue (1,3) de (2,2) con $k=60$.
</details>

<details><summary><b>3 · (Cálculo)</b> Una FDE de MUVERA con $k_{sim}=5$, $R=10$ y $d=32$: ¿cuántas dimensiones tiene y cuántos GB ocupan 1 M de documentos en <code>float32</code>?</summary>

$B=2^5=32$; dimensión $=R\cdot B\cdot d=10\cdot32\cdot32=10\,240$. $10^6\cdot10\,240\cdot4$ B $=40.96$ GB (sin PQ). Con compresión PQ 32× sería ≈ 1.3 GB.
</details>

<details><summary><b>4 · (Diagnóstico)</b> Tu híbrido (BM25 + denso con RRF) rinde <i>peor</i> que el denso solo. ¿Qué compruebas?</summary>

(a) Que BM25 no sea muchísimo peor que el denso en tu corpus (la fusión de un retriever débil lo arrastra); (b) analyzer de BM25 y idioma; (c) duplicados en las listas; (d) $k$ de RRF y profundidad de las listas; (e) prueba la combinación convexa con α pequeño para BM25 o una validación cruzada; (f) revisa si las consultas son semánticas (el léxico aporta poco).
</details>

<details><summary><b>5 · (Diagnóstico)</b> Tras añadir un cross-encoder la latencia p95 pasó de 40 ms a 900 ms. ¿Qué haces?</summary>

Reducir $K$ (la latencia es lineal en el nº de pares), acortar `max_length`, usar un modelo más pequeño o cuantizado, procesar en lotes en GPU, cachear pares frecuentes, y reservar el reranking para queries donde la confianza del híbrido es baja.
</details>

<details><summary><b>6 · (Transferencia)</b> Políglota recibe consultas con códigos de error exactos y documentos en ES/EN/código. Diseña el retriever.</summary>

Híbrido: BM25 (con analyzer que conserve identificadores completos y los parta) + denso multilingüe (módulo 12, Matryoshka+int8) fusionados con RRF/convexa; reranker cross-encoder multilingüe sobre el top-50; late interaction opcional si el presupuesto lo permite (MUVERA como candidatos). Filtros de idioma/versión en la rama léxica. Evaluar cada rama y la fusión en un golden set que incluya consultas de identificador, de paráfrasis y entre idiomas.
</details>

<details><summary><b>7 · (Transferencia)</b> ¿En qué se parece el patrón "híbrido + reranker" al de un sistema de recomendación en producción?</summary>

Es el patrón de **generación de candidatos (varias fuentes) → ranker caro** (recsys-course, módulos 06–08): varias fuentes baratas y complementarias aseguran recall; un modelo caro, solo sobre un subconjunto, decide el orden final.
</details>
''')
    nb.md(r'''## 15 · Referencias (verificadas; consultadas en oct-2026)

**Papers (arXiv)**
- Khattab & Zaharia (2020). *ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT*. <https://arxiv.org/abs/2004.12832>
- Santhanam et al. (2021). *ColBERTv2: Effective and Efficient Retrieval via Lightweight Late Interaction*. <https://arxiv.org/abs/2112.01488> · Santhanam et al. (2022). *PLAID: An Efficient Engine for Late Interaction Retrieval*. <https://arxiv.org/abs/2205.09707> · Scheerer et al. (2025). *WARP: An Efficient Engine for Multi-Vector Retrieval*. <https://arxiv.org/abs/2501.17788>
- Dhulipala et al. (2024). *MUVERA: Multi-Vector Retrieval via Fixed Dimensional Encodings*. <https://arxiv.org/abs/2405.19504>
- Formal et al. (2021). *SPLADE*. <https://arxiv.org/abs/2107.05720> · *SPLADE v2*. <https://arxiv.org/abs/2109.10086> · Formal et al. (2022). *From Distillation to Hard Negative Sampling…*. <https://arxiv.org/abs/2205.04733> · Lassance et al. (2024). *SPLADE-v3: New baselines for SPLADE*. <https://arxiv.org/abs/2403.06789>
- Geng et al. (2024). *Towards Competitive Search Relevance For Inference-Free Learned Sparse Retrievers*. <https://arxiv.org/abs/2411.04403>
- Chen et al. (2024). *M3-Embedding (BGE-M3)*. <https://arxiv.org/abs/2402.03216>
- Jha et al. (2024). *Jina-ColBERT-v2: A General-Purpose Multilingual Late Interaction Retriever*. <https://arxiv.org/abs/2408.16672>
- Günther et al. (2024). *Late Chunking: Contextual Chunk Embeddings Using Long-Context Embedding Models*. <https://arxiv.org/abs/2409.04701>
- Nogueira & Cho (2019). *Passage Re-ranking with BERT*. <https://arxiv.org/abs/1901.04085>
- Bruch, Gai & Ingber (2022). *An Analysis of Fusion Functions for Hybrid Retrieval*. <https://arxiv.org/abs/2210.11934>
- Thakur et al. (2021). *BEIR*. <https://arxiv.org/abs/2104.08663>
- Cormack, Clarke & Büttcher (2009). *Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods*. SIGIR 2009.
- Robertson & Zaragoza (2009). *The Probabilistic Relevance Framework: BM25 and Beyond*. Foundations and Trends in IR.

**Documentación y blogs**
- Vespa: *Announcing the Vespa ColBERT embedder*. <https://blog.vespa.ai/announcing-colbert-embedder-in-vespa/> · *Announcing Long-Context ColBERT in Vespa*. <https://blog.vespa.ai/announcing-long-context-colbert-in-vespa/>
- Qdrant: *Multivector Representations for Reranking in Qdrant*. <https://qdrant.tech/documentation/advanced-tutorials/using-multivector-representations/>
- Weaviate: *MUVERA* (blog). <https://weaviate.io/blog/muvera>
- Jina AI: *Jina ColBERT v2*. <https://jina.ai/news/jina-colbert-v2-multilingual-late-interaction-retriever-for-embedding-and-reranking/>
- BGE: *bge-reranker-v2-m3* y tutorial de reranking. <https://bge-model.com/tutorial/5_Reranking/5.2.html>
- Librerías: `rank_bm25`, `sentence-transformers` (`SparseEncoder`, `CrossEncoder`), `FlagEmbedding`, PyLate.

**Para profundizar:** módulo 14 (cómo se indexan estos vectores: HNSW, IVF-PQ, RaBitQ), módulo 15 (evaluación rigurosa con intervalos de confianza) y módulo 16 (ColPali: late interaction visual).
''')
    # <<END_LESSON>>
    nb.save(LESSON)


def _lesson_cell(inicio: str) -> str:
    """Código de una celda de la lección ya generada (para reutilizar utilidades 'dadas' en el proyecto)."""
    import nbformat
    nbk = nbformat.read(LESSON, as_version=4)
    for c in nbk.cells:
        if c.cell_type == "code" and c.source.startswith(inicio):
            return c.source
    raise KeyError(inicio)


def _entre(src: str, a: str, b: str | None = None) -> str:
    i = src.index(a)
    j = src.index(b, i) if b else len(src)
    return src[i:j].rstrip() + "\n"


def project() -> None:
    nb = Notebook("Proyecto 13 · Retrieval híbrido de Políglota", colab_path=PROJECT, gpu=True)
    c_text = _lesson_cell("import re, unicodedata")
    c_mv = _lesson_cell("import zlib")
    c_fus = _lesson_cell("def minmax(S):")
    c_rr = _lesson_cell("RERANK_MODELOS")
    UTIL_TEXTO = _entre(c_text, "import re", "class BM25")
    SOL_BM25 = _entre(c_text, "class BM25", "def bm25_matriz")
    UTIL_MV = _entre(c_mv, "import zlib", "def maxsim_matriz")
    SOL_MAXSIM = _entre(c_mv, "def maxsim_matriz", "t0 = time.perf_counter()")
    UTIL_NORM = _entre(c_fus, "def minmax", "def rrf")
    SOL_FUSION = _entre(c_fus, "def rrf", "for b in BENCHES:")
    UTIL_RERANK = _entre(c_rr, "RERANK_MODELOS", "b = B1")

    nb.md(nb.badge() + r"""

# Proyecto 13 · Retrieval híbrido de Políglota: fusión y reranking

**Nivel:** 🟠 Avanzado · **Duración:** ≈ 2 h · **GPU:** T4 opcional (CPU basta con `FAST_DEV_RUN = True`) · **Cómputo:** ≈ 0–1 unidades de Colab.

**Conexión.** *Viene de:* módulo 12 (el embedder denso y su configuración) y de la lección 13. *Va hacia:* módulo 14 (indexar los vectores de este sistema con ANN) y 15 (evaluarlo con intervalos de confianza).

## 1 · Contexto de negocio
El CTO de **Políglota Labs** quiere pasar de «un embedder» a un **sistema de recuperación híbrido**: BM25 + denso multilingüe + late interaction, fusionados, con un **cross-encoder** que reordena el top-K bajo un **presupuesto de latencia** (≈ 200 ms por consulta para la etapa de reranking). Tu trabajo: implementar las piezas, elegir la fusión **sin hacer trampa con el tuning** y entregar el pipeline con su análisis de coste/beneficio.

## 2 · Dataset
Dos bancos de pruebas (ver lección): el **corpus canónico** del módulo 00 (`carga_corpus`; sintético con `⚠️` si no hay acceso) y el **mini golden set de paráfrasis ES↔EN↔código** (58 queries).

## 3 · Entregables
1. `BM25` propio (verificado contra `rank_bm25`), `maxsim_matriz` vectorizado (verificado contra la fórmula ingenua).
2. `rrf`, `lineal` y `alfa_cv` (α elegido por validación cruzada de 2 pliegues).
3. `hibrido_rerank`: pipeline fusión → cross-encoder sobre el top-K, y `elige_K` que respeta el presupuesto de latencia.
4. Tabla final de nDCG@10 por retriever, fusión y pipeline en **ambos** bancos + una conclusión escrita.

## 4 · Rúbrica (umbrales calibrados con lo que MIDE la solución de referencia)
Los umbrales son **invariantes relativas** a tu propia ejecución. La solución de referencia se ejecutó en un entorno **sin acceso a Hugging Face** (corpus sintético, embedder denso de respaldo TF-IDF+SVD, ColBERT de juguete y reranker de respaldo) y con modelos diminutos de pesos aleatorios para ejercitar las rutas de `sentence-transformers`; **no se verificó con modelos reales**. Valores medidos en la última columna.

| # | Criterio | Umbral | Medido por la solución |
|---|---|---|---|
| R1 | BM25 propio (IDF `okapi`) coincide con `rank_bm25` | `allclose` | True |
| R2 | `maxsim_matriz` coincide con la fórmula ingenua en 20 pares | atol 1e-4 | True |
| R3 | RRF reproduce el ejemplo a mano (rangos 1 y 3 → 1/61 + 1/63) | exacto | True |
| R4 | Canónico: mejor fusión ≥ mejor retriever individual − 0.03 nDCG@10 | cumplido | fusión 0.848 vs individual 0.861 (Δ = −0.013) |
| R5 | Paráfrasis: mejor fusión ≥ mejor retriever individual − 0.03 nDCG@10 | cumplido | fusión 0.318 vs individual 0.320 (Δ = −0.002) |
| R6 | El nDCG de `alfa_cv` (validación cruzada) no supera al de α elegido en las mismas queries (sin fuga) | `cv ≤ oráculo + 1e-9` | 0.848 ≤ 0.861 y 0.318 ≤ 0.323 |
| R7 | `hibrido_rerank` devuelve ≥ 10 documentos por consulta y solo reordena el top-K | cumplido | True (≥ 10 en todas las queries) |
| R8 | `elige_K` devuelve el mayor K con latencia ≤ presupuesto | cumplido | True |
| R9 | Conclusión escrita con ≥ 3 números de tus tablas | — | revisión manual |
""")
    nb.md("## 5 · Preparación (celdas dadas)")
    nb.code(CODE_PIP)
    nb.code(C.CODE_SETUP_COMMON)
    for _src in src_corpus_cells():
        nb.code(_src)
    nb.code(SRC_METRICS)
    nb.code(C.CODE_EVAL_PQ)
    nb.code(C.CODE_CORPUS_SEED)
    nb.code(C.CODE_PARAFRASIS_LOADER)
    nb.code(C.CODE_EMBEDDER_TOOLS)
    nb.code(CODE_BENCH)
    nb.code(CODE_DENSE)
    nb.code(UTIL_TEXTO)
    nb.code(UTIL_MV)
    nb.code(UTIL_NORM)
    nb.code(UTIL_RERANK)

    # ── TODO 1 ──
    nb.md(r"""## 6 · Paso 1 — BM25 desde cero (TODO 1)
Implementa `BM25.fit` y `BM25.scores` con una **matriz dispersa de pesos precomputada** (lección, sección 2). Variante de IDF: `lucene` → $\ln(1+\frac{N-n+.5}{n+.5})$; `okapi` → $\ln\frac{N-n+.5}{n+.5}$ con suelo $0.25\cdot\overline{\text{IDF}}$ para los negativos. Fórmula del peso de cada par (doc $i$, término $j$): `idf[j] * tf * (k1+1) / (tf + k1*(1 - b + b*dl[i]/avgdl))`.

<details><summary>🪜 Pista 1 (idea)</summary>
Cuenta <code>tf</code> con <code>Counter</code> y arma una <code>csr_matrix</code> (documentos × vocabulario). El peso de cada elemento no nulo depende de su fila (longitud del doc) y de su columna (IDF): calcula ambos arrays alineados con <code>tf.data</code>.
</details>
<details><summary>🪜 Pista 2 (casi la API)</summary>
<code>fila_de = np.repeat(np.arange(N), np.diff(tf.indptr))</code> · <code>w = tf.data*(k1+1)/(tf.data + k1*(1-b+b*dl[fila_de]/avgdl))</code> · <code>W = csr_matrix((w*idf[tf.indices], tf.indices, tf.indptr), shape=tf.shape).tocsc()</code> · <code>scores = W @ q</code> con <code>q</code> el vector de conteos de la query.
</details>
""")
    nb.code(r'''
class BM25:
    def __init__(self, k1=1.2, b=0.75, idf="lucene"):
        self.k1, self.b, self.idf_kind = k1, b, idf
    def fit(self, docs_tokens):
        # TODO 1.a: vocabulario, matriz tf (CSR), longitudes, IDF según self.idf_kind y matriz de pesos self.W
        raise NotImplementedError("TODO 1.a")
    def scores(self, q_tokens):
        # TODO 1.b: vector de conteos de la query y producto W @ q  (devuelve un array de n_docs)
        raise NotImplementedError("TODO 1.b")

def bm25_matriz(b, k1=1.2, bb=0.75, **analyzer):
    modelo = BM25(k1, bb).fit([toks(t, **analyzer) for t in b.txt])
    return np.stack([modelo.scores(toks(q, **analyzer)) for q in b.qtxt])

def paso1():
    from rank_bm25 import BM25Okapi
    docs_t = [toks(t) for t in B1.txt]
    ref, mio = BM25Okapi(docs_t, k1=1.2, b=0.75), BM25(idf="okapi").fit(docs_t)
    ok = all(np.allclose(ref.get_scores(toks(q)), mio.scores(toks(q))) for q in B1.qtxt[:10])
    print("coincide con rank_bm25:", ok)
    for b in BENCHES:
        b.S["bm25"] = bm25_matriz(b)
    return ok

try:
    R1_OK = paso1(); display(B1.resumen())
except NotImplementedError as e:
    R1_OK = False; print("⏳ pendiente:", e)
''')

    # ── TODO 2 ──
    nb.md(r"""## 7 · Paso 2 — MaxSim vectorizado (TODO 2)
`maxsim(Q, D)` (ingenuo, dado) calcula un par. Implementa `maxsim_matriz(QV, DV)` que devuelve la matriz `(n_queries, n_docs)` **sin bucle por par**: concatena los tokens de todos los documentos, multiplica una vez por trozo de queries y toma máximos/sumas **por segmento**.

<details><summary>🪜 Pista 1 (idea)</summary>
<code>Qcat @ Dcat.T</code> da todas las similitudes token-token. El máximo por documento es un máximo sobre un <i>rango contiguo de columnas</i>; la suma por query, sobre un rango contiguo de filas.
</details>
<details><summary>🪜 Pista 2 (casi la API)</summary>
<code>np.maximum.reduceat(sims, inicios_docs, axis=1)</code> y después <code>np.add.reduceat(mx, inicios_queries, axis=0)</code>; los inicios salen de <code>np.cumsum([0] + longitudes[:-1])</code>. Procesa las queries en trozos de ~32 para no agotar RAM.
</details>
""")
    nb.code(r'''
def maxsim_matriz(QV, DV, trozo=32):
    # TODO 2: matriz (len(QV), len(DV)) de scores MaxSim, vectorizada con np.maximum.reduceat / np.add.reduceat
    raise NotImplementedError("TODO 2")

def paso2():
    for b in BENCHES:
        b.DV, b.QV = multi_juguete(b.txt), multi_juguete(b.qtxt)
        b.S["colbert-juguete"] = maxsim_matriz(b.QV, b.DV)
    rng = np.random.default_rng(0)
    pares = [(int(rng.integers(len(B1.QV))), int(rng.integers(len(B1.DV)))) for _ in range(20)]
    ok = all(np.isclose(B1.S["colbert-juguete"][i, j], maxsim(B1.QV[i], B1.DV[j]), atol=1e-4) for i, j in pares)
    print("coincide con la fórmula ingenua:", ok)
    return ok

try:
    R2_OK = paso2()
except NotImplementedError as e:
    R2_OK = False; print("⏳ pendiente:", e)
''')

    # ── TODO 3-4 ──
    nb.md(r"""## 8 · Paso 3 — Fusión: RRF y combinación lineal (TODO 3) y α sin fuga (TODO 4)
- `rrf(Ss, k=60)`: para cada matriz de scores calcula el **rango** (1 = mejor) de cada documento por query y suma `1/(k+rango)`.
- `lineal(Ss, pesos, norm)`: suma ponderada de las matrices **normalizadas por query** (`minmax` o `zscore`, dadas).
- `alfa_cv(b, S1, S2, norm)`: elige α en la rejilla `np.linspace(0,1,21)` maximizando el nDCG medio sobre un pliegue de queries y evalúa en el **otro** (2 pliegues, `rng = np.random.default_rng(SEED)`, `idx = rng.permutation(n)`, `np.array_split(idx, 2)`); devuelve la media de los dos nDCG de validación. Usa `b.ndcg_q(S)` (nDCG por query).

<details><summary>🪜 Pista 1 (idea)</summary>
El rango de un documento es la posición en el orden descendente: <code>argsort(argsort(-S))+1</code> por fila. La fusión lineal normaliza cada fila antes de mezclar para que las escalas sean comparables.
</details>
<details><summary>🪜 Pista 2 (casi la API)</summary>
<code>rangos = np.argsort(np.argsort(-S, axis=1), axis=1) + 1</code> · <code>out += peso / (k + rangos)</code> · en <code>alfa_cv</code>: <code>mejor = max(grid, key=lambda a: b.ndcg_q(lineal([S1,S2],[a,1-a],norm))[tr].mean())</code>.
</details>
""")
    nb.code(r'''
def rrf(Ss, k=60, pesos=None):
    # TODO 3.a: fusión RRF de varias matrices de scores (nq, nd) -> matriz de scores fusionados
    raise NotImplementedError("TODO 3.a")

def lineal(Ss, pesos, norm=minmax):
    # TODO 3.b: sum_i peso_i * norm(S_i)
    raise NotImplementedError("TODO 3.b")

def alfa_cv(b, S1, S2, norm=minmax, grid=np.linspace(0, 1, 21)):
    # TODO 4: validación cruzada de 2 pliegues para elegir alfa; devuelve el nDCG@10 medio de validación
    raise NotImplementedError("TODO 4")

def paso3():
    r = rrf([np.array([[3.0, 1.0, 2.0]]), np.array([[1.0, 3.0, 2.0]])], k=60)
    # doc 0: rangos (1,3); doc 1: (3,1); doc 2: (2,2)
    ok_rrf = bool(np.isclose(r[0, 0], 1 / 61 + 1 / 63) and np.isclose(r[0, 2], 2 / 62))
    print("RRF ejemplo a mano:", ok_rrf)
    for b in BENCHES:
        b.S["rrf(bm25+denso)"] = rrf([b.S["bm25"], b.S["denso"]])
        b.S["rrf(bm25+denso+colbert)"] = rrf([b.S["bm25"], b.S["denso"], b.S["colbert-juguete"]])
        b.S["lineal α=0.5"] = lineal([b.S["bm25"], b.S["denso"]], [0.5, 0.5])
        b.cv = alfa_cv(b, b.S["bm25"], b.S["denso"])
        b.oraculo = max(b.ndcg(lineal([b.S["bm25"], b.S["denso"]], [a, 1 - a])) for a in np.linspace(0, 1, 21))
    return ok_rrf

try:
    R3_OK = paso3()
    for b in BENCHES:
        print(f"{b.nombre[:22]:>22}: α por CV → {b.cv:.3f} · α oráculo (mismas queries) → {b.oraculo:.3f}")
    display(pd.concat({b.nombre[:12]: b.resumen() for b in BENCHES}))
except (NotImplementedError, KeyError) as e:
    R3_OK = False; print("⏳ pendiente:", repr(e))
''')

    # ── TODO 5-6 ──
    nb.md(r"""## 9 · Paso 4 — Pipeline con reranking (TODO 5) y presupuesto de latencia (TODO 6)
- `hibrido_rerank(b, S_fusion, K, nq)`: para cada query toma el top-`K` de `S_fusion`, puntúa los pares con `ce.predict` (cross-encoder real o de respaldo, ya cargado como `ce`) y devuelve `(run, ms_por_query)` donde `run[qid]` es la lista de **al menos 10** ids: los K reordenados seguidos del resto del ranking de `S_fusion` (así el nDCG@10 es comparable aunque `K<10`).
- `elige_K(latencias_ms, presupuesto_ms)`: dado un dict `{K: ms}` devuelve el **mayor K** cuya latencia sea ≤ presupuesto (o `None`).

<details><summary>🪜 Pista 1 (idea)</summary>
El reranking solo permuta los primeros K; el resto de la lista se mantiene en el orden de la fusión. Mide el tiempo con <code>time.perf_counter()</code> alrededor del bucle de queries.
</details>
<details><summary>🪜 Pista 2 (casi la API)</summary>
<code>cand = np.argsort(-S[i])</code> · <code>sc = ce.predict([(b.qtxt[i], b.txt[j]) for j in cand[:K]], batch_size=16, show_progress_bar=False)</code> · <code>orden = cand[:K][np.argsort(-np.asarray(sc).ravel())]</code> · <code>run[qid] = [b.ids[j] for j in list(orden) + list(cand[K:])][:max(10, K)]</code>.
</details>
""")
    nb.code(r'''
ce_nombre, ce = carga_reranker()
NQ_REN = 30 if FAST_DEV_RUN else None
PRESUPUESTO_MS = 200

def hibrido_rerank(b, S_fusion, K, nq=NQ_REN):
    # TODO 5: devuelve (run, ms_por_query) con el top-K reordenado por el cross-encoder `ce`
    raise NotImplementedError("TODO 5")

def elige_K(latencias_ms, presupuesto_ms=PRESUPUESTO_MS):
    # TODO 6: mayor K con latencia <= presupuesto (None si ninguno cabe)
    raise NotImplementedError("TODO 6")

def paso4():
    b = B1
    S_f = b.S["lineal α=0.5"]
    sub = {q["qid"] for q in b.qs[: (NQ_REN or len(b.qs))]}
    filas, lat = [], {}
    base = np.mean([ndcg_at_k(r, b.qrels[q], 10) for q, r in b.run(S_f, 10).items() if q in sub])
    filas.append(("sin rerank", float(base), 0.0))
    for K in (10, 20, 50):
        run, ms = hibrido_rerank(b, S_f, K)
        lat[K] = ms
        filas.append((f"rerank K={K}", float(np.mean([ndcg_at_k(r, b.qrels[q], 10) for q, r in run.items()])), ms))
    tabla = pd.DataFrame(filas, columns=["pipeline", "nDCG@10 (mismas queries)", "ms/query"])
    return tabla, lat, run

try:
    TABLA_REN, LAT, RUN_ULT = paso4()
    K_ELEGIDO = elige_K(LAT)
    display(TABLA_REN.round(3)); print("reranker:", ce_nombre, "· K elegido para", PRESUPUESTO_MS, "ms:", K_ELEGIDO)
except (NotImplementedError, KeyError) as e:
    TABLA_REN = LAT = RUN_ULT = K_ELEGIDO = None; print("⏳ pendiente:", repr(e))
''')
    nb.md("## 10 · Autocomprobación de la rúbrica")
    nb.code(r'''
def autograder():
    ch = {}
    ch["R1 BM25 == rank_bm25"] = bool(R1_OK)
    ch["R2 maxsim_matriz == ingenuo"] = bool(R2_OK)
    ch["R3 RRF ejemplo a mano"] = bool(R3_OK)
    for etiqueta, b in (("R4 canónico", B1), ("R5 paráfrasis", B2)):
        try:
            indiv = max(b.ndcg(b.S[n]) for n in ("bm25", "denso", "colbert-juguete"))
            fus = max(b.cv, max(b.ndcg(b.S[n]) for n in ("rrf(bm25+denso)", "rrf(bm25+denso+colbert)", "lineal α=0.5")))
            ch[f"{etiqueta}: mejor fusión ≥ mejor individual − 0.03"] = bool(fus >= indiv - 0.03)
        except Exception:
            ch[f"{etiqueta}: mejor fusión ≥ mejor individual − 0.03"] = False
    try:
        ch["R6 CV sin fuga (cv ≤ oráculo)"] = all(b.cv <= b.oraculo + 1e-9 for b in BENCHES)
    except Exception:
        ch["R6 CV sin fuga (cv ≤ oráculo)"] = False
    try:
        ch["R7 pipeline devuelve ≥ 10 docs"] = all(len(v) >= 10 for v in RUN_ULT.values())
    except Exception:
        ch["R7 pipeline devuelve ≥ 10 docs"] = False
    try:
        ok = elige_K({10: 50, 20: 120, 50: 300}, 200) == 20 and elige_K({10: 500}, 200) is None
        ch["R8 elige_K respeta el presupuesto"] = bool(ok)
    except Exception:
        ch["R8 elige_K respeta el presupuesto"] = False
    for k, v in ch.items():
        print("✅" if v else "❌", k)
    return ch

_ = autograder()
''')
    nb.md(r"""## 11 · Tu conclusión (R9)
En ≤ 10 líneas, con números de tus tablas: ¿qué combinación de retrievers y qué fusión recomiendas? ¿Mejoró el reranker (con el modelo que tuvieras)? ¿Qué K cabe en 200 ms? ¿Qué riesgos ves (idioma, dominio, latencia p95, almacenamiento de la rama multi-vector)?

> *(Edita esta celda.)*

## 12 · Retos extra (nivel experto)
1. Añade la rama **sparse aprendido** o los tres modos de **BGE-M3** (lección, secciones 3 y 5) y repite las fusiones; ¿qué rama aporta más a la fusión en el banco de paráfrasis?
2. Implementa **MUVERA** (lección, sección 6) como primera etapa del multi-vector y mide recall del top-10 exacto vs número de candidatos.
3. Calcula **intervalos de confianza bootstrap** de la diferencia entre la mejor fusión y el mejor retriever individual.
4. Prueba un reranker **basado en LLM** (p. ej. Qwen3-Reranker) en una GPU y compara calidad/latencia con el cross-encoder.
5. Añade **filtros** (idioma, `lang` del documento) a la rama léxica y a la densa y mide qué pasa con el recall (anticipo del módulo 14).

## 13 · Reflexión (producción e hilo conductor)
- ¿Qué parte de este pipeline pondrías en el índice (offline) y cuál en la consulta (online)?
- Si el 30 % de las consultas son identificadores exactos, ¿qué peso darías a la rama léxica y cómo lo validarías?
- ¿Cómo monitorizarías la deriva de cada rama por separado? (módulo 18)
- ¿Cuánto crece el índice si activas late interaction para 10 M de documentos? (lección, sección 10)
""")

    nb.md(r"""---
# ⛔ SPOILER — intenta resolverlo primero
Las celdas siguientes **sobrescriben** tus funciones con la solución de referencia.
""")
    nb.code(SOL_BM25)
    nb.code(SOL_MAXSIM)
    nb.code(SOL_FUSION)
    nb.code(r'''
def hibrido_rerank(b, S_fusion, K, nq=NQ_REN):
    run, t0 = {}, time.perf_counter()
    qs = list(enumerate(b.qs))[:nq]
    for i, q in qs:
        cand = np.argsort(-S_fusion[i])
        sc = np.asarray(ce.predict([(b.qtxt[i], b.txt[j]) for j in cand[:K]], batch_size=16, show_progress_bar=False)).ravel()
        orden = cand[:K][np.argsort(-sc)]
        run[q["qid"]] = [b.ids[j] for j in list(orden) + list(cand[K:])][:max(10, K)]
    return run, (time.perf_counter() - t0) / len(qs) * 1e3

def elige_K(latencias_ms, presupuesto_ms=PRESUPUESTO_MS):
    ok = [K for K, ms in latencias_ms.items() if ms <= presupuesto_ms]
    return max(ok) if ok else None

R1_OK = paso1()
R2_OK = paso2()
R3_OK = paso3()
for b in BENCHES:
    print(f"{b.nombre[:22]:>22}: α por CV → {b.cv:.3f} · oráculo → {b.oraculo:.3f}")
display(pd.concat({b.nombre[:12]: b.resumen() for b in BENCHES}))
TABLA_REN, LAT, RUN_ULT = paso4()
K_ELEGIDO = elige_K(LAT)
display(TABLA_REN.round(3)); print("reranker:", ce_nombre, "· K elegido:", K_ELEGIDO)
_ = autograder()
''')
    nb.md(r"""### Conclusión de referencia (ejemplo)
En el entorno de pruebas (sin modelos reales) BM25 domina el banco canónico porque las queries comparten vocabulario con los documentos, y la fusión no lo supera pero queda a menos de 0.03 de nDCG@10; en el banco de paráfrasis todas las ramas léxicas sufren y la fusión rinde como la mejor rama. El α elegido por validación cruzada es ≤ al α oráculo (el oráculo está sesgado). El reranking de respaldo no es un cross-encoder: su calidad no es informativa, pero su latencia crece ≈ lineal en K, y K se elige desde el presupuesto de 200 ms. Con modelos reales esperarías que denso y late interaction aporten en paráfrasis y entre idiomas y que el cross-encoder suba el nDCG@10 en el banco de paráfrasis; **verifícalo con tus números**.
""")
    nb.save(PROJECT)


def readme() -> None:
    texto = """# Módulo 13 · Dense vs sparse vs late interaction

**Nivel:** 🟠 Avanzado · **Duración:** ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) · **GPU:** T4 opcional (CPU en `FAST_DEV_RUN`)

Un solo vector por texto no basta: los identificadores exactos piden **índice invertido**, las paráfrasis piden **semántica** y la precisión fina
pide **interacción por token**. Este módulo construye cada pieza desde cero y las combina en un pipeline **híbrido**: BM25, sparse aprendido (SPLADE),
**MaxSim/ColBERT** (con compresión residual y un PLAID mini), **MUVERA**, BGE-M3 (tres modos), **fusión** (RRF y combinación convexa sin fuga de tuning),
**rerankers cross-encoder** con presupuesto de latencia y **late chunking**.

## Contenido
| Notebook | Qué hay dentro |
|---|---|
| [`13_dense_sparse_late_interaction.ipynb`](13_dense_sparse_late_interaction.ipynb) | Lección: BM25 desde cero (matriz dispersa, verificada contra `rank_bm25`) · SPLADE (fórmula, FLOPS, `SparseEncoder`) · MaxSim vectorizado · compresión residual de ColBERTv2 · PLAID mini · BGE-M3 a mano · MUVERA (FDE) · RRF y combinación lineal con CV · cross-encoder y latencia vs K · late chunking · costes de almacenamiento · 🏭 producción · 🧠 secretos · autoevaluación |
| [`13_proyecto_dense_sparse_late_interaction.ipynb`](13_proyecto_dense_sparse_late_interaction.ipynb) | Proyecto: retrieval híbrido de Políglota con fusión y reranking. Plantilla con TODOs, pistas 🪜, autocomprobación de rúbrica y solución tras ⛔ SPOILER |

## Objetivos
1. Implementar BM25 y MaxSim desde cero y verificarlos contra librerías/fórmula ingenua.
2. Entender SPLADE, ColBERTv2/PLAID y MUVERA y medir sus trade-offs.
3. Fusionar retrievers con RRF y combinación convexa sin fuga de tuning.
4. Montar recuperar → fusionar → reordenar y elegir K desde un presupuesto de latencia.

## Datasets
Banco canónico (`carga_corpus()` del módulo 00: Wikipedia ES/EN + código; sintético con aviso si no hay acceso) y un **mini golden set de paráfrasis ES↔EN↔código**
(29 conceptos, 58 queries) escrito a mano para diagnosticar dónde gana cada retriever.

## Lecturas clave (verificadas)
- Khattab & Zaharia (2020), *ColBERT* (2004.12832) · Santhanam et al. (2021), *ColBERTv2* (2112.01488) · *PLAID* (2205.09707).
- Dhulipala et al. (2024), *MUVERA* (2405.19504).
- Formal et al., *SPLADE* (2107.05720), *SPLADE-v3* (Lassance et al., 2403.06789).
- Chen et al. (2024), *BGE-M3* (2402.03216) · Günther et al. (2024), *Late Chunking* (2409.04701).
- Bruch, Gai, Ingber (2022), *An Analysis of Fusion Functions for Hybrid Retrieval* (2210.11934).

## Conexión con Políglota
El módulo 12 aporta el retriever denso; aquí lo combinas con BM25 y late interaction y añades un reranker. El módulo 14 indexará estos vectores con ANN.

*Los notebooks se generan con `python tokenization-embeddings-course/_tools/builders/build_13.py` (desde la raíz del repo). Estado del arte a octubre de 2026.*
"""
    with open(f"{MOD}/README.md", "w", encoding="utf-8") as f:
        f.write(texto)
    print(f"OK {MOD}/README.md")


if __name__ == "__main__":
    lesson()
    project()
    readme()
