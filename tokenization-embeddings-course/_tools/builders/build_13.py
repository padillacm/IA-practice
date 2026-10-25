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
    # <<APPEND_LESSON_3>>
    nb.save(LESSON)


def project() -> None:
    nb = Notebook("Proyecto 13 · Retrieval híbrido de Políglota", colab_path=PROJECT, gpu=True)
    # <<APPEND_PROJECT>>
    nb.save(PROJECT)


def readme() -> None:
    pass  # <<APPEND_README>>


if __name__ == "__main__":
    lesson()
    project()
    readme()
