"""Genera el módulo 12 (lección + proyecto + README): Embedders modernos.

Ejecutar desde la raíz del repo:  python tokenization-embeddings-course/_tools/builders/build_12.py
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
MOD = f"{COURSE}/12_embedders_modernos"
LESSON = f"{MOD}/12_embedders_modernos.ipynb"
PROJECT = f"{MOD}/12_proyecto_embedders_modernos.ipynb"
os.makedirs(f"{MOD}/assets", exist_ok=True)
open(f"{MOD}/assets/.gitkeep", "a").close()

# ───────────────────────── celdas de código compartidas por lección y proyecto ─────────────────────────
CODE_PIP = r'''
!pip install -q sentence-transformers transformers scikit-learn matplotlib pandas mteb
'''

CODE_EMBEDDER_TOOLS = C.CODE_EMBEDDER_TOOLS

CODE_LOAD_CORPUS_EMB = r'''
CORPUS = carga_corpus(FAST_DEV_RUN)
DOC_IDS = [d["id"] for d in CORPUS["docs"]]
DOC_TXT = [d["text"] for d in CORPUS["docs"]]
QRYS = CORPUS["queries"]
QRELS = CORPUS["qrels"]
print(CORPUS["source"], len(DOC_IDS), "docs ·", len(QRYS), "queries")

def run_denso(Eq, Ed, k=10):
    """Búsqueda exacta por producto escalar (embeddings normalizados -> coseno)."""
    S = Eq @ Ed.T
    return {q["qid"]: rank_from_scores(S[i], DOC_IDS, k) for i, q in enumerate(QRYS)}

# Embedder "principal" de la lección: el primero que se pueda cargar de verdad; si no, el fallback.
emb = None
for clave in ("multilingual-e5-small", "paraphrase-multilingual-MiniLM-L12-v2"):
    emb = cargar_embedder(clave)
    if emb is not None:
        break
if emb is None:
    emb = cargar_embedder("multilingual-e5-small", textos_ajuste=DOC_TXT)
t0 = time.perf_counter()
E_d = emb.encode_docs(DOC_TXT)
E_q = emb.encode_queries([q["text"] for q in QRYS])
print(f"embedder = {emb.clave} · real={emb.is_real} · dim={E_d.shape[1]} · {time.perf_counter()-t0:.1f}s")
base = evaluate(run_denso(E_q, E_d), QRELS)
print({k: round(float(v), 3) for k, v in base.items()})
'''


def lesson() -> None:
    nb = Notebook("Módulo 12 · Embedders modernos", colab_path=LESSON, gpu=True)

    # ───────────────────────────── 1. Cabecera ─────────────────────────────
    nb.md(nb.badge() + r'''

# Módulo 12 · Embedders modernos: instrucciones, Matryoshka y cuantización

**Tokenización y Embeddings: de BPE a los modelos modernos**

| | |
|---|---|
| **Nivel** | 🟠 Avanzado |
| **Duración estimada** | ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) |
| **GPU recomendada** | T4 (todo corre en CPU con `FAST_DEV_RUN = True`); 0 unidades en CPU, ≈ 1–3 unidades de Colab en T4 con `FAST_DEV_RUN = False` (estimación orientativa: depende de cuántos modelos actives) |
| **Prerrequisitos** | Módulo 09 (matriz de embeddings y geometría), módulo 10 (pooling, anisotropía, similitudes) y módulo 11 (InfoNCE, hard negatives, MRL como "ingrediente" contrastivo) |

**Hilo conductor — Políglota.** Eres ML engineer en *Políglota Labs*. Ya tienes un baseline BM25 (00) y entrenaste tu propio embedder (11). Ahora el CTO pregunta:
*«¿Qué embedder comprobado ponemos en producción, a qué dimensión y con qué cuantización, para que 10 M de documentos quepan en un nodo?»*
Este módulo te da el criterio (y el código) para contestar con datos, no con el leaderboard.

> **Estado del arte a octubre de 2026.** Este campo cambia cada pocas semanas: toda cifra, ID de modelo o precio va **fechado** y debe re-verificarse en la tarjeta del modelo antes de decidir. Lo que no pude verificar no aparece como cifra.
''')

    nb.md(r'''## 🎯 Objetivos de aprendizaje
Al terminar el módulo serás capaz de:
1. **Explicar** las tres olas de embedders (encoders contrastivos → LLM-as-embedder → modelos multi-tarea con Matryoshka/QAT) y el rol de cada ingrediente de la receta.
2. **Implementar desde cero** los pooling CLS / mean / max / **last-token** / **latent attention** (NV-Embed) con máscaras de padding correctas, y detectar el bug de *padding side*.
3. **Aplicar** prefijos e instrucciones de query/documento de cada familia (E5, Qwen3-Embedding, EmbeddingGemma, Nomic…) y **medir** su impacto.
4. **Derivar e implementar** la pérdida Matryoshka (MRL), el truncado + renormalización, y **demostrar** con un experimento por qué truncar un modelo *no* entrenado con MRL falla.
5. **Implementar desde cero** cuantización escalar `int8` (con calibración por dimensión) y **binaria** (bits empaquetados + distancia de Hamming + *rescoring*), y compararla con `sentence-transformers`.
6. **Comparar** embedders reales con `sentence-transformers` en calidad (nDCG@10), memoria y latencia, con **intervalos de confianza** por bootstrap.
7. **Leer críticamente** MTEB/MMTEB: qué miden, qué no, y por qué tu golden set manda.
8. **Decidir** con un árbol de decisión explícito qué embedder, dimensión y precisión usar para un caso de negocio.
''')

    nb.md(r'''## 🔁 Conexión con módulos anteriores
Antes de empezar, intenta contestar de memoria (la respuesta está plegada):

<details><summary><b>1 · (M11)</b> ¿Qué hace InfoNCE con los negativos <i>in-batch</i> y qué controla la temperatura $\tau$?</summary>

Trata a los otros $B-1$ documentos del lote como negativos de cada query y maximiza la probabilidad softmax del positivo: $\mathcal{L}=-\log\frac{e^{s(q,d^+)/\tau}}{\sum_j e^{s(q,d_j)/\tau}}$. Una $\tau$ pequeña (≈ 0.02–0.05) afila la distribución y da más peso a los negativos duros. Hoy ese mismo bloque de código se *reusa* para Matryoshka: se calcula varias veces sobre prefijos del vector.
</details>

<details><summary><b>2 · (M10)</b> ¿Por qué el <i>mean pooling</i> suele ganar al CLS en modelos sin fine-tuning contrastivo, y qué es la anisotropía?</summary>

El estado del `[CLS]` solo se entrena para la tarea de pre-entrenamiento (NSP/MLM no lo exigen como resumen), mientras que el promedio agrega información de todos los tokens. La anisotropía es que los embeddings ocupan un cono estrecho del espacio (cosenos altos entre textos no relacionados); el entrenamiento contrastivo la corrige.
</details>

<details><summary><b>3 · (M09)</b> ¿Qué dimensión tiene la capa de embedding de tokens de un LLM pequeño y qué relación tiene con la dimensión de salida del embedder de oraciones?</summary>

La dimensión oculta $d_{model}$ (p. ej. 1024 en un decoder de ≈ 0.6 B). Un embedder basado en ese LLM suele exponer $d_{model}$ como dimensión del vector (y Matryoshka permite usar prefijos más cortos).
</details>

<details><summary><b>4 · (M04)</b> ¿Por qué la tokenización influye en el "contexto efectivo" de un embedder en español vs inglés?</summary>

Porque la <i>fertilidad</i> (tokens por palabra) del español suele ser mayor que la del inglés en vocabularios sesgados al inglés: el mismo texto ocupa más tokens y se trunca antes en `max_seq_length`. Por eso Políglota fija `max_len` en tokens, no en caracteres.
</details>
<details><summary><b>5 · (M08 + M02, Cálculo)</b> ¿Cuántos bits ocupa un vector de 768 dimensiones en float32 y en binario? Compáralo con un token VQ de un codebook de 8 192 entradas.</summary>

float32: $768 \times 32 = 24\,576$ bits; binario: **768 bits** (32× menos); un token VQ: $\log_2 8192 = 13$ bits. Las tres son compresión con pérdida (módulo 08) con distinto punto en la curva tasa-distorsión; la binaria es una cuantización escalar de 1 bit por dimensión, y el PQ del módulo 14 queda entre medias (VQ por subespacios). Como en bits por byte (02), lo que importa es la calidad por bit.
</details>
''')


    # ───────────────────────────── 2. Setup ─────────────────────────────
    nb.md(r'''## 0. Preparación del entorno
Las celdas de utilidades (corpus, métricas, embedder) están en esta lección porque **cada notebook del curso es autocontenido**.
Si no hay acceso a Hugging Face (proxy, sin red), todo sigue funcionando con un **fallback** que te avisa con un `⚠️`: los números cambian, los conceptos no.
''')
    nb.code(CODE_PIP)
    nb.code(C.CODE_SETUP_COMMON)
    nb.md(r'''### Corpus Políglota y métricas
`carga_corpus(fast_dev)` sigue el **contrato común del curso**: devuelve `{"docs", "queries", "qrels", "source"}` con cadena *oficial → espejo → sintético*. Si ves `source = "synthetic"`, estás usando el corpus **sintético** del módulo 00 (texto ES/EN generado con plantillas + funciones reales de la biblioteca estándar de Python como "código"): el mismo esquema que el real, pero **los números no son comparables** con los del corpus real. Es la implementación **canónica** de `carga_corpus` escrita en el módulo 00 (cadena oficial → espejo → sintético).
''')
    for _src in src_corpus_cells():
        nb.code(_src)
    nb.code(SRC_METRICS)
    nb.code(C.CODE_EVAL_PQ)
    nb.md(r'''### Un envoltorio común para embedders
`Embedder` aplica el prefijo correcto de cada familia y siempre devuelve vectores `float32` normalizados. Si el modelo no se puede descargar, `cargar_embedder` devuelve un **fallback TF-IDF+SVD** (no semántico ni multilingüe): el pipeline sigue ejecutándose para que puedas practicar truncado, cuantización y métricas.
''')
    nb.code(CODE_EMBEDDER_TOOLS)
    nb.code(CODE_LOAD_CORPUS_EMB)

    # ───────────────────────────── 3. Intuición ─────────────────────────────
    nb.md(r'''## 1. Intuición: tres olas de embedders

**Ola 1 (2019–2022) — encoders contrastivos pequeños.** Sentence-BERT, luego E5/BGE/GTE: un encoder bidireccional (BERT/XLM-R) con *mean pooling*, entrenado primero con una enorme cantidad de pares débilmente supervisados y luego con datos etiquetados y *hard negatives*. 100–500 M de parámetros, 384–1024 dimensiones, 512 tokens.

**Ola 2 (2023–2024) — LLM-as-embedder.** Se observa que un decoder grande (Mistral-7B) fine-tuneado con pérdida contrastiva supera a los encoders: e5-mistral (datos sintéticos generados por LLM), NV-Embed (pooling *latent attention*, máscara causal retirada), LLM2Vec (convertir un decoder en encoder bidireccional). Coste: un decoder de 7 B tiene ≈ 20× más parámetros que un encoder de 300 M, y eso se paga en cada texto que indexas.

**Ola 3 (2025–2026) — modelos "de producto".** Familias con **varios tamaños**, **contexto largo (8k–32k)**, **instrucciones**, **Matryoshka** y a veces **cuantización consciente** (QAT), multilingües y, cada vez más, **multimodales** (módulo 16): Qwen3-Embedding (0.6B/4B/8B), Gemini Embedding, EmbeddingGemma (≈ 300 M), Jina v4/v5, Nomic v2 (MoE), Voyage-4, Cohere Embed v4.

> 💡 **Analogía con compresión y recsys.** Un embedder es un *codec con pérdida* diseñado para que la **distancia** (no la reconstrucción) se preserve. Matryoshka es un codec *escalable* (como JPEG progresivo: los primeros bytes ya dan una imagen útil) y la cuantización es el *segundo* codec encima. En recsys, la torre del ítem hace el mismo papel: producir un vector indexable (módulo `recsys-course/08`).
''')
    nb.gemini(
        "imagen", "M12-IMG-01", "La receta de un embedder moderno",
        "Pipeline de entrenamiento de un embedder de 2025-2026 (backbone → pretraining contrastivo → fine-tuning con instrucciones y hard negatives → Matryoshka/QAT → vector) y las dos variantes de backbone.",
        """
        Diagrama técnico limpio, fondo blanco, formato 16:9, estilo de infografía de ingeniería. Paleta: azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280. Tipografía sans-serif legible. Sin ilustraciones decorativas ni texto inventado.

        Composición de IZQUIERDA a DERECHA con 5 cajas redondeadas conectadas por flechas grises gruesas:
        1) Caja gris con título "Backbone". Dentro, dos mini-opciones apiladas: "Encoder bidireccional (XLM-R, ModernBERT)" en azul y "Decoder LLM (Qwen3, Gemma, Mistral)" en naranja.
        2) Caja azul: "Pretraining contrastivo" con subtítulo "pares débilmente supervisados · InfoNCE · in-batch negatives".
        3) Caja azul: "Fine-tuning supervisado" con subtítulo "hard negatives · instrucciones de tarea · multilingüe".
        4) Caja verde: "Matryoshka + QAT (opcional)" con subtítulo "pérdida sobre prefijos del vector · cuantización consciente".
        5) Caja gris final: "Vector de 1024 dimensiones" dibujado como una barra horizontal segmentada en bloques; los primeros 4 bloques resaltados en verde con la etiqueta "prefijo útil (Matryoshka)".

        Debajo de las cajas 1 y 2, una fina línea punteada naranja con la etiqueta "pooling: mean (encoder) / last-token o latent attention (decoder)".
        En la parte inferior, un pie de figura pequeño: "Cada flecha = una etapa de entrenamiento".

        Evita: texto ilegible o diminuto, flechas ambiguas o cruzadas, logos de empresas, iconos decorativos, números de parámetros inventados.
        """,
        "Pipeline de entrenamiento de un embedder moderno de izquierda a derecha con cinco etapas",
        """
        [Backbone: encoder | decoder] -> [Pretraining contrastivo] -> [Fine-tuning: hard negatives + instrucciones]
                                     -> [Matryoshka + QAT] -> [vector 1024-d: ████ prefijo útil | ░░░░░░░░░░]
        pooling: mean (encoder) / last-token o latent attention (decoder)
        """,
    )
    nb.md(r'''> 👀 **Qué debes observar.** La diferencia entre familias casi nunca está en la *arquitectura* sino en las **dos últimas cajas**: la calidad y variedad de los datos de fine-tuning y la forma de empaquetar el vector (Matryoshka, cuantización). Eso explica por qué dos modelos del mismo tamaño pueden diferir 5–10 puntos en tu dominio.
''')

    # ───────────────────────────── 4. Pooling ─────────────────────────────
    nb.md(r'''## 2. Pooling en encoders y en decoders (desde cero)

Un transformer produce una matriz de estados ocultos $H\in\mathbb{R}^{T\times d}$ por texto. El embedder necesita **un** vector $e\in\mathbb{R}^d$:

| Pooling | Fórmula | Quién lo usa |
|---|---|---|
| CLS | $e = h_0$ | BGE (denso), muchos encoders |
| Mean | $e = \frac{\sum_t m_t h_t}{\sum_t m_t}$ | E5, SBERT, Nomic |
| Max | $e_j = \max_t h_{t,j}$ | histórico |
| **Last-token** | $e = h_{\ell-1}$ (último token **real**, con $\ell=\sum_t m_t$) | e5-mistral, Qwen3-Embedding (según sus papers/tarjetas) |
| **Latent attention** | $e = \text{mean}_t\big(\text{MLP}(\text{softmax}(HL^\top/\sqrt d)\,L)\big)$ con diccionario entrenable $L\in\mathbb{R}^{r\times d}$ | NV-Embed |

$m_t\in\{0,1\}$ es la **máscara de atención** (1 = token real). En un decoder con atención causal el único estado que "ha visto" todo el texto es el **último**, por eso se usa last-token (típicamente tras añadir un token de fin de secuencia).

> ⚠️ **El bug clásico del last-token.** Con *padding a la derecha*, el último índice del tensor es un token de relleno; hay que tomar el índice $\ell-1$ por fila. Con *padding a la izquierda* el último índice sí es el correcto. Mezclar ambos convenios degrada la calidad **sin dar error**.
''')
    nb.code(r'''
def softmax(x, axis=-1):
    x = x - x.max(axis=axis, keepdims=True)
    e = np.exp(x)
    return e / e.sum(axis=axis, keepdims=True)

def gelu(x):
    return 0.5 * x * (1 + np.tanh(np.sqrt(2 / np.pi) * (x + 0.044715 * x ** 3)))

def pool_cls(H, m):  return H[:, 0]
def pool_mean(H, m):
    w = m[..., None].astype(H.dtype)
    return (H * w).sum(1) / np.maximum(w.sum(1), 1)
def pool_max(H, m):
    return np.where(m[..., None] == 1, H, -np.inf).max(1)
def pool_last(H, m, padding_side="right"):
    if padding_side == "left":                 # el último índice del tensor ya es el último token real
        return H[:, -1]
    idx = m.sum(1) - 1                         # padding a la derecha: índice del último token real por fila
    return H[np.arange(len(H)), idx]
def pool_latent(H, m, L, W1, W2):
    """Latent attention de NV-Embed: los estados H consultan un diccionario entrenable L (r x d); luego MLP y media."""
    att = softmax(H @ L.T / np.sqrt(H.shape[-1]))        # (B,T,r)
    O = att @ L                                          # (B,T,d)
    O = O + gelu(O @ W1) @ W2                            # MLP residual
    return pool_mean(O, m)

rng = np.random.default_rng(SEED)
B, T, D = 2, 6, 8
H = rng.normal(size=(B, T, D))
m_right = np.array([[1, 1, 1, 1, 0, 0], [1, 1, 1, 1, 1, 1]])   # fila 0 tiene 2 tokens de relleno a la derecha
cos = lambda a, b: float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))

correcto = pool_last(H, m_right, "right")[0]
ingenuo = H[0, -1]                                             # el bug: tomar siempre el último índice
print("last-token correcto  = estado del token 3:", np.allclose(correcto, H[0, 3]))
print("last-token ingenuo   = estado del PAD   :", np.allclose(ingenuo, H[0, 5]), "· coseno con el correcto:", round(cos(correcto, ingenuo), 3))

L = rng.normal(size=(4, D)); W1 = rng.normal(size=(D, 2 * D)) * 0.2; W2 = rng.normal(size=(2 * D, D)) * 0.2
for nombre, f in [("cls", pool_cls), ("mean", pool_mean), ("max", pool_max), ("last", pool_last)]:
    print(f"{nombre:>5} ->", np.round(f(H, m_right)[0][:4], 2))
print("latent ->", np.round(pool_latent(H, m_right, L, W1, W2)[0][:4], 2))
''')
    nb.code(r'''
import matplotlib.pyplot as plt

T = 6
causal = np.tril(np.ones((T, T)))
bidir = np.ones((T, T))
pesos = {                                   # peso de cada token en el vector final (texto de 6 tokens, sin padding)
    "CLS": np.eye(T)[0], "Mean": np.ones(T) / T, "Last-token": np.eye(T)[-1],
}
fig, axs = plt.subplots(1, 3, figsize=(13, 3.6), gridspec_kw={"width_ratios": [1, 1, 1.25]})
for ax, mat, tit in ((axs[0], bidir, "Encoder: atención bidireccional"), (axs[1], causal, "Decoder: atención causal")):
    ax.imshow(mat, cmap="Blues", vmin=0, vmax=1.4)
    ax.set_title(tit, fontsize=10); ax.set_xlabel("token atendido (clave)"); ax.set_ylabel("token que atiende (query)")
    ax.set_xticks(range(T)); ax.set_yticks(range(T))
im = axs[2].imshow(np.stack(list(pesos.values())), cmap="Oranges", vmin=0, vmax=1, aspect="auto")
axs[2].set_yticks(range(len(pesos))); axs[2].set_yticklabels(list(pesos)); axs[2].set_xticks(range(T))
axs[2].set_xlabel("posición del token"); axs[2].set_title("Peso de cada token en el embedding", fontsize=10)
plt.tight_layout(); plt.show()
''')
    nb.md(r'''> 👀 **Qué debes observar.** (1) En el decoder (triángulo) solo la **última fila** ve a todos los tokens: por eso last-token es el único estado "completo". (2) Mean pooling reparte peso uniforme, CLS y last-token dependen de **un solo** estado. (3) Esto explica por qué LLM2Vec y NV-Embed **quitan la máscara causal** al entrenar: con atención bidireccional, hasta el mean pooling pasa a ser razonable en un decoder.
''')
    nb.md(r'''### LLM2Vec y NV-Embed en dos párrafos
- **LLM2Vec** (BehnamGhader et al., 2024) convierte *cualquier* decoder en encoder con 3 pasos baratos: (1) **activar atención bidireccional**, (2) **MNTP** (*masked next token prediction*), (3) **SimCSE no supervisado**. Es 🟡: mejora mucho al decoder "crudo", pero un modelo entrenado desde el principio para embeddings (Qwen3-Embedding, e5-mistral) suele ser más sólido.
- **NV-Embed** (Lee et al., 2024) aplica el pooling *latent attention* de la tabla, **elimina la máscara causal** durante el entrenamiento contrastivo y usa un fine-tuning contrastivo en **dos etapas** (primero con instrucciones y negativos in-batch para retrieval; luego mezcla tareas no-retrieval).
- **e5-mistral** (Wang et al., 2023/24) genera datos sintéticos con un LLM propietario para muchísimas tareas e idiomas y fine-tunea Mistral-7B con pérdida contrastiva; el embedding es el estado oculto del **token EOS final** (last-token).

Todo esto se resume en: *el backbone importa menos que los datos y que la forma de empaquetar el vector*.
''')

    # ───────────────────────────── 5. Instrucciones y prefijos ─────────────────────────────
    nb.md(r'''## 3. Embeddings con instrucciones y prefijos

Un embedder moderno es **asimétrico**: la *query* ("¿cómo recorto un vector?") y el *documento* (un párrafo que lo explica) son textos de naturaleza distinta. La solución estándar es **anteponer un prefijo** distinto a cada lado:

| Familia | Query | Documento | Fuente |
|---|---|---|---|
| E5 (multilingual-e5) | `query: …` | `passage: …` | tarjeta del modelo |
| Nomic Embed | `search_query: …` | `search_document: …` | tarjeta del modelo |
| Qwen3-Embedding | `Instruct: {tarea}\nQuery:{texto}` | sin prefijo | tarjeta del modelo |
| EmbeddingGemma | `task: search result \| query: …` | `title: none \| text: …` | tarjeta / blog de HF |
| BGE-M3, GTE-multilingual | sin prefijo | sin prefijo | tarjetas |

Con `sentence-transformers` ≥ 5 los métodos `encode_query()` / `encode_document()` aplican automáticamente los prompts que el autor guardó en la configuración del modelo (si existen). Aquí usamos prefijos **explícitos** para ver qué pasa.

> 🧪 **Experimento.** Mide el mismo embedder con (a) prefijos correctos, (b) sin prefijos y (c) prefijos **invertidos**. Con un modelo entrenado con prefijos (E5, Qwen3, EmbeddingGemma…), (b) y (c) dañan la calidad; con modelos sin prefijos no pasa nada. Si estás en el *fallback* TF-IDF, el prefijo es solo ruido de texto: el experimento sigue ejecutándose pero no representa al modelo real.
''')
    nb.code(r'''
def ndcg_con_prefijos(emb, prefijo_q, prefijo_d):
    Eq = emb._enc([q["text"] for q in QRYS], prefijo_q)
    Ed = emb._enc(DOC_TXT, prefijo_d)
    return evaluate(run_denso(Eq, Ed), QRELS)["ndcg"]

cfg = emb.cfg
experimentos = {
    "prefijos correctos": (cfg.get("q", ""), cfg.get("d", "")),
    "sin prefijos": ("", ""),
    "invertidos": (cfg.get("d", ""), cfg.get("q", "")),
}
res_prefijos = {nombre: ndcg_con_prefijos(emb, *pq) for nombre, pq in experimentos.items()}
for k, v in res_prefijos.items():
    print(f"{k:>20}: nDCG@10 = {v:.3f}")

import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(6.4, 3.2))
colores = ["#2CA02C", "#6B7280", "#F28E2B"]
ax.bar(list(res_prefijos), list(res_prefijos.values()), color=colores)
ax.set_ylabel("nDCG@10"); ax.set_title(f"Efecto del prefijo en {emb.clave}")
ax.set_ylim(0, max(res_prefijos.values()) * 1.25)
for i, v in enumerate(res_prefijos.values()):
    ax.text(i, v + 0.01, f"{v:.3f}", ha="center")
plt.tight_layout(); plt.show()
''')
    nb.md(r'''> 👀 **Qué debes observar.** Con un modelo de la familia E5 real, la barra verde (prefijos correctos) suele ser la más alta y los prefijos invertidos pierden calidad; el tamaño de la caída depende del modelo y del dominio, **mídelo con tu golden set** en vez de asumirlo. Con modelos sin prefijos las tres barras son casi iguales. El error silencioso más común en producción es **olvidar el prefijo del lado de la query o del documento** (ver «Errores comunes»).
''')

    # ───────────────────────────── 6. Matryoshka ─────────────────────────────
    nb.md(r'''## 4. Matryoshka (MRL): vectores que se pueden recortar

**Problema.** Un embedder de 1024 dimensiones cuesta 4 KB por documento en `float32`. Si solo necesitas 256 dimensiones, ¿puedes quedarte con las *primeras* 256? Con un modelo normal, **no**: la información está repartida por igual en todas las coordenadas (cualquier rotación ortogonal del espacio es equivalente para el coseno).

**Idea (Kusupati et al., 2022).** Entrenar de modo que **cada prefijo** $z_{1:m}$ ($m\in\mathcal{M}$, típicamente potencias de 2) sea por sí solo un buen embedding. Sea $z=f_\theta(x)\in\mathbb{R}^{d}$ y $\mathcal{M}=\{m_1<\dots<m_K=d\}$:

$$\mathcal{L}_{MRL}=\sum_{m\in\mathcal{M}} c_m\;\mathcal{L}_{InfoNCE}\!\left(\frac{z^q_{1:m}}{\lVert z^q_{1:m}\rVert},\frac{z^d_{1:m}}{\lVert z^d_{1:m}\rVert}\right)$$

- $c_m$: peso de cada escala (en la práctica 1 para todas, o más peso a las pequeñas).
- La **renormalización** de cada prefijo dentro de la pérdida es esencial: es la misma operación que harás al truncar en inferencia.
- Coste de entrenamiento: $K$ evaluaciones de una matriz $B\times B$ de similitudes (despreciable frente al backbone).

**En inferencia:** `e_m = e[:, :m] / ||e[:, :m]||`. Sin la renormalización, el producto escalar mezcla normas distintas y el ranking cambia.

**Cuándo NO usarlo:** si tu modelo *no* fue entrenado con MRL, truncar degrada rápido; en ese caso usa PCA (aprende una base ordenada por varianza) o un modelo con MRL. Lo comprobamos a continuación.
''')
    nb.code(r'''
import torch.nn as nn, torch.nn.functional as F

def toy_datos(n, d_in=128, d_lat=24, ruido=0.35, seed=0):
    """Dos 'vistas' ruidosas del mismo vector latente: el par positivo del aprendizaje contrastivo."""
    g = torch.Generator().manual_seed(seed)
    A = torch.randn(d_lat, d_in, generator=g) / math.sqrt(d_lat)
    Z = torch.randn(n, d_lat, generator=g)
    vista = lambda: Z @ A + ruido * torch.randn(n, d_in, generator=g)
    return vista(), vista()

def info_nce(a, b, tau=0.05):
    a, b = F.normalize(a, dim=-1), F.normalize(b, dim=-1)
    logits = a @ b.T / tau
    y = torch.arange(len(a))
    return 0.5 * (F.cross_entropy(logits, y) + F.cross_entropy(logits.T, y))

def entrena_toy(dims_mrl, d_out=64, pasos=300, bs=256, seed=0):
    torch.manual_seed(seed)
    enc = nn.Sequential(nn.Linear(128, 256), nn.GELU(), nn.Linear(256, d_out))
    opt = torch.optim.Adam(enc.parameters(), lr=2e-3)
    x1, x2 = toy_datos(8000, seed=1)
    for _ in range(pasos):
        idx = torch.randint(0, len(x1), (bs,))
        a, b = enc(x1[idx]), enc(x2[idx])
        loss = sum(info_nce(a[:, :m], b[:, :m]) for m in dims_mrl) / len(dims_mrl)   # <- la pérdida MRL
        opt.zero_grad(); loss.backward(); opt.step()
    return enc

@torch.no_grad()
def recall1_por_dim(enc, dims, n=2000):
    t1, t2 = toy_datos(n, seed=7)
    a, b = enc(t1), enc(t2)
    out = {}
    for m in dims:
        s = F.normalize(a[:, :m], dim=-1) @ F.normalize(b[:, :m], dim=-1).T
        out[m] = (s.argmax(1) == torch.arange(n)).float().mean().item()
    return out

DIMS_EVAL = [2, 4, 8, 16, 32, 48, 64]
enc_std = entrena_toy([64])                 # entrenamiento estándar: solo la dimensión completa
enc_mrl = entrena_toy([8, 16, 32, 64])      # Matryoshka: pérdida en 4 prefijos
r_std, r_mrl = recall1_por_dim(enc_std, DIMS_EVAL), recall1_por_dim(enc_mrl, DIMS_EVAL)
print("dim   estándar   MRL")
for m in DIMS_EVAL:
    print(f"{m:>3}   {r_std[m]:.3f}      {r_mrl[m]:.3f}")
''')
    nb.code(r'''
fig, ax = plt.subplots(figsize=(6.8, 3.8))
ax.plot(DIMS_EVAL, [r_std[m] for m in DIMS_EVAL], "o-", color="#F28E2B", label="entrenamiento estándar")
ax.plot(DIMS_EVAL, [r_mrl[m] for m in DIMS_EVAL], "s-", color="#1F6FEB", label="Matryoshka (dims 8/16/32/64)")
ax.set_xscale("log", base=2); ax.set_xticks(DIMS_EVAL); ax.set_xticklabels(DIMS_EVAL)
ax.set_xlabel("dimensiones conservadas (prefijo renormalizado)"); ax.set_ylabel("Recall@1 (retrieval del par)")
ax.set_title("Juguete: truncar un embedder con y sin pérdida Matryoshka"); ax.legend(); ax.grid(alpha=.3)
plt.tight_layout(); plt.show()
''')
    nb.md(r'''> 👀 **Qué debes observar.** A 64 dimensiones ambos modelos son prácticamente iguales (MRL **no** cuesta calidad a plena dimensión). A 8–16 dimensiones, el modelo estándar se desploma mientras el Matryoshka conserva buena parte del recall: la información "importante" quedó concentrada en las primeras coordenadas. Fuera de las escalas entrenadas (p. ej. 48) la curva MRL sigue siendo suave, pero lo seguro es truncar **solo** a dimensiones soportadas por el proveedor.
''')
    nb.gemini(
        "imagen", "M12-IMG-02", "Matryoshka: el vector como muñecas rusas",
        "Un vector de 1024 dimensiones con sus prefijos de 512, 256, 128 y 64 dimensiones anidados, el paso de renormalización y el coste en memoria de cada escala.",
        """
        Diagrama técnico limpio, fondo blanco, formato 16:9. Paleta: azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280. Tipografía sans-serif legible. Sin ilustraciones decorativas.

        Dibuja CINCO barras horizontales anidadas alineadas a la izquierda (como muñecas rusas), de arriba abajo, cada una más corta que la anterior, todas con el mismo alto:
        - Barra gris muy larga con la etiqueta "1024 dims · 4096 bytes (float32)".
        - Barra azul a la mitad de longitud: "512 dims · 2048 bytes".
        - Barra azul más corta: "256 dims · 1024 bytes".
        - Barra azul aún más corta: "128 dims · 512 bytes".
        - Barra verde la más corta: "64 dims · 256 bytes".
        Los primeros 64 bloques de todas las barras comparten el mismo color verde para mostrar que el prefijo es común, con una llave vertical a la izquierda que dice "mismo prefijo".

        A la derecha de la barra de 256 dims, una flecha naranja hacia un cuadro con el texto "renormalizar: e / ||e||" y debajo una circunferencia pequeña (vector unitario) con la leyenda "||e|| = 1".
        Arriba a la izquierda, el título: "Matryoshka: cada prefijo es un embedding útil".
        Abajo, una nota en gris: "Recortar + renormalizar = ahorrar memoria sin reentrenar (solo si el modelo se entrenó con MRL)".

        Evita: añadir más barras o números distintos a los indicados, texto ilegible, efectos 3D, imágenes de muñecas reales, logos.
        """,
        "Cinco barras anidadas de 1024 a 64 dimensiones con su coste en bytes y el paso de renormalización",
        """
        1024 dims  ████████████████████████████████  4096 B
         512 dims  ████████████████                  2048 B
         256 dims  ████████                          1024 B   -> renormalizar e/||e||
         128 dims  ████                               512 B
          64 dims  ██                                 256 B   (prefijo común)
        """,
    )
    nb.md(r'''> 👀 **Qué debes observar.** La memoria baja **linealmente** con la dimensión (÷2 por cada escala), mientras que, en un modelo con MRL, la calidad cae mucho más despacio. Esa asimetría es lo que hace rentable el truncado: pasar de 1024 a 256 dimensiones ahorra 4× de RAM por una pérdida de calidad que *debes medir* en tu corpus.
''')
    nb.gemini(
        "video", "M12-VID-01", "Truncar y renormalizar paso a paso",
        "Animación de un embedding que se recorta a un prefijo, se renormaliza y se usa para ordenar 5 documentos; contrasta un modelo con Matryoshka y otro sin él.",
        """
        Video explicativo de 16:9, fondo blanco, estilo diagrama técnico limpio, paleta azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280, tipografía sans-serif, ritmo calmado, sin voz en off, sin música; solo texto en pantalla en español (términos técnicos en inglés).

        Escena 1 (0–5 s): aparece una barra horizontal gris dividida en 16 bloques con la etiqueta "embedding completo (d = 16, ejemplo)". Título arriba: "Truncar un embedding".
        Escena 2 (5–10 s): los 8 primeros bloques se vuelven azules y los otros 8 se desvanecen; etiqueta "m = 8: nos quedamos con el prefijo". Un contador de memoria cambia de "64 bytes" a "32 bytes".
        Escena 3 (10–16 s): una flecha naranja vector 2D (dibujada como flecha desde el origen) crece o se encoge hasta tocar un círculo unitario punteado; etiqueta "renormalizar: e / ||e||". La flecha termina con longitud 1.
        Escena 4 (16–24 s): se muestran 5 documentos D1…D5 como puntos en el círculo y una query Q como flecha verde; una lista a la derecha ordena los documentos por similitud coseno. Con "modelo Matryoshka" el orden es D3 > D1 > D4 > D2 > D5 (igual que con el vector completo); con "modelo estándar truncado" el orden cambia a D2 > D5 > D3 > D1 > D4 y se marca en naranja "ranking roto". Pie pequeño: "rankings ilustrativos".
        Escena 5 (24–28 s): fundido con el texto "Matryoshka: el prefijo ya es un buen embedding. Sin MRL, el truncado destruye el ranking."

        Evita: voz, música, texto ilegible, números distintos a los dados, elementos decorativos, cambios bruscos de cámara.
        """,
        "Animación de truncado y renormalización de un embedding con dos rankings comparados",
        """
        [d=16] ████████████████  64 B
        [m=8 ] ████████          32 B  -> renormalizar (||e||=1)
        Matryoshka : D3 > D1 > D4 > D2 > D5  (ranking conservado)
        Estándar   : D2 > D5 > D3 > D1 > D4  (ranking roto)
        """,
        duration="25-30 s",
    )
    nb.md(r'''> 👀 **Qué debes observar.** La renormalización devuelve el vector a la esfera unidad (el coseno vuelve a ser un producto escalar) y, con un modelo Matryoshka, el **orden** de los documentos no cambia. Con un modelo no entrenado así, el ranking se rompe.
''')
    nb.md(r'''### Truncado en un embedder real (o fallback)
Medimos nDCG@10 al truncar `E_d`/`E_q` a distintas dimensiones con tres estrategias: **prefijo + renormalizar** (lo correcto para MRL), **prefijo sin renormalizar** (el error típico) y **PCA** (la alternativa cuando el modelo *no* es Matryoshka).
''')
    nb.code(r'''
def trunc_renorm(E, m):
    X = E[:, :m]
    return (X / np.maximum(np.linalg.norm(X, axis=1, keepdims=True), 1e-9)).astype(np.float32)

def pca_fit(Ed, m):
    mu = Ed.mean(0, keepdims=True)
    _, _, Vt = np.linalg.svd(Ed - mu, full_matrices=False)
    return mu, Vt[:m]

def ndcg_de(Eq, Ed):
    return evaluate(run_denso(Eq, Ed), QRELS)["ndcg"]

D = E_d.shape[1]
dims = sorted({m for m in (8, 16, 32, 64, 128, 256, 384, 512, 768, 1024) if m < D} | {D})
curvas = {"prefijo + renormalizar": [], "prefijo sin renormalizar (dot)": [], "PCA + renormalizar": []}
for m in dims:
    curvas["prefijo + renormalizar"].append(ndcg_de(trunc_renorm(E_q, m), trunc_renorm(E_d, m)))
    curvas["prefijo sin renormalizar (dot)"].append(ndcg_de(E_q[:, :m], E_d[:, :m]))
    mu, W = pca_fit(E_d, m)
    proy = lambda E: trunc_renorm((E - mu) @ W.T, W.shape[0])
    curvas["PCA + renormalizar"].append(ndcg_de(proy(E_q), proy(E_d)))

fig, ax = plt.subplots(figsize=(7, 3.8))
for (nombre, ys), c in zip(curvas.items(), ["#1F6FEB", "#F28E2B", "#2CA02C"]):
    ax.plot(dims, ys, "o-", label=nombre, color=c)
ax.set_xscale("log", base=2); ax.set_xticks(dims); ax.set_xticklabels(dims, rotation=45)
ax.set_xlabel("dimensiones conservadas"); ax.set_ylabel("nDCG@10")
ax.set_title(f"Truncado de {emb.clave} en Políglota ({CORPUS['source']})"); ax.legend(); ax.grid(alpha=.3)
plt.tight_layout(); plt.show()
print({m: round(float(v), 3) for m, v in zip(dims, curvas["prefijo + renormalizar"])})
''')
    nb.md(r'''> 👀 **Qué debes observar.** (1) Si el modelo es **Matryoshka** (Nomic v2, Qwen3-Embedding, EmbeddingGemma…), "prefijo + renormalizar" cae despacio. (2) Si **no** lo es (p. ej. `multilingual-e5-small`, el modelo por defecto de esta celda, o el fallback), la curva del prefijo cae antes y **PCA** la supera: ordena las direcciones por varianza en tu corpus. (3) La curva naranja (sin renormalizar) es la del error típico: puede quedar por debajo de la azul porque el producto escalar mezcla normas. Prueba a cambiar `emb` por un modelo con MRL y repite.
''')

    # ───────────────────────────── 7. Cuantización ─────────────────────────────
    nb.md(r'''## 5. Cuantización de embeddings: `int8` y binaria (desde cero)

Después de reducir las *dimensiones*, se reducen los *bits por dimensión*. Para $N$ documentos de $d$ dimensiones:

| Precisión | Bytes por vector | Con $d=1024$ | Ratio |
|---|---|---|---|
| `float32` | $4d$ | 4096 B | 1× |
| `float16` | $2d$ | 2048 B | 2× |
| `int8` | $d$ | 1024 B | 4× |
| binaria (1 bit) | $d/8$ | 128 B | 32× |

**Escalar `int8`.** Para cada dimensión $j$ se calibra un rango $[lo_j, hi_j]$ sobre una muestra del **corpus** y se mapea linealmente a 256 niveles:
$$q_{ij}=\operatorname{round}\!\Big(\tfrac{x_{ij}-lo_j}{(hi_j-lo_j)/255}\Big)-128\quad\in[-128,127].$$

**Binaria.** $b_{ij}=\mathbb{1}[x_{ij}>0]$, empaquetado 8 bits por byte. La similitud se aproxima con la **distancia de Hamming** (XOR + popcount). Para vectores $\pm1$, $\langle a,b\rangle=d-2\,H(a,b)$: es decir, ordenar por Hamming ordena por producto escalar de los signos.

✍️ **Ejemplo a mano.** *int8:* en una dimensión con $[lo, hi] = [-0.5, 0.5]$, el paso es $1/255 \approx 0.00392$; $x = 0.12$ → $\operatorname{round}(0.62/0.00392) - 128 = 158 - 128 = $ **30**, y al decodificar $30 + 128 = 158 \to 158 \cdot 0.00392 - 0.5 = 0.1196$ (error $4\times10^{-4}$, menor que medio paso). *Binaria:* $a = (0.12, -0.50, 0.33, 0.01) \to$ `1011`, $b = (0.20, 0.10, -0.30, 0.05) \to$ `1101`; difieren en $H = 2$ bits, y en $\pm1$: $\langle a, b\rangle = 4 - 2\cdot2 = 0$ (compruébalo: $1 - 1 - 1 + 1$). Fíjate en que $a_4 = 0.01$ cuenta igual que $a_3 = 0.33$: la binaria tira la magnitud, y por eso hace falta el rescoring.

**Rescoring (clave).** La binaria sola pierde calidad; la receta estándar es **recuperar $k\times$`over` candidatos con Hamming** y **reordenarlos con la query en `float32` contra los vectores `int8`** (que pueden vivir en disco). Es la receta del post de Hugging Face (Shakir, Aarsen, Lee, 2024).

> ⚠️ **Calibra con el corpus, no con las queries**: las queries tienen una distribución distinta (más cortas) y el rango resultante es inadecuado. `sentence-transformers` recomienda calibrar con un conjunto grande de embeddings representativo de lo que vas a cuantizar (`calibration_embeddings`).
''')
    nb.code(r'''
POPCNT = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)

def ajusta_rangos(E_calib):
    """Rango [lo, hi] por dimensión calculado sobre el CORPUS (no sobre las queries)."""
    return E_calib.min(0), E_calib.max(0)

def cuantiza_int8(E, lo, hi):
    paso = np.maximum(hi - lo, 1e-9) / 255.0
    return np.clip(np.round((E - lo) / paso) - 128, -128, 127).astype(np.int8)

def descuantiza_int8(Q, lo, hi):
    paso = np.maximum(hi - lo, 1e-9) / 255.0
    return (Q.astype(np.float32) + 128) * paso + lo

def cuantiza_binario(E, umbral=0.0):
    return np.packbits(E > umbral, axis=1)                      # (N, d/8) uint8

def hamming(qb, db, bloque=2048):
    out = np.empty((len(qb), len(db)), dtype=np.int32)
    for s in range(0, len(db), bloque):
        x = qb[:, None, :] ^ db[None, s:s + bloque, :]            # XOR byte a byte
        out[:, s:s + bloque] = POPCNT[x].sum(-1)                  # popcount por tabla de 256 entradas
    return out

def topk_scores(S, k):
    idx = np.argpartition(-S, min(k, S.shape[1] - 1), axis=1)[:, :k]
    orden = np.take_along_axis(S, idx, 1).argsort(1)[:, ::-1]
    return np.take_along_axis(idx, orden, 1)

def busca_binario_rescore(Eq, Db, Qi8, lo, hi, k=10, over=4, umbral=0.0):
    H = hamming(np.packbits(Eq > umbral, axis=1), Db)
    cand = topk_scores(-H.astype(np.float32), min(k * over, H.shape[1]))     # menor Hamming = mejor
    out = np.empty((len(Eq), k), dtype=np.int64)
    for i in range(len(Eq)):
        v = descuantiza_int8(Qi8[cand[i]], lo, hi)
        out[i] = cand[i][np.argsort(-(v @ Eq[i]))[:k]]
    return out

# Verificación frente a sentence-transformers
try:
    from sentence_transformers.util import quantize_embeddings
except ImportError:
    from sentence_transformers.quantization import quantize_embeddings
lo, hi = ajusta_rangos(E_d)
mi_bin, st_bin = cuantiza_binario(E_d), quantize_embeddings(E_d, "ubinary")
mi_i8, st_i8 = cuantiza_int8(E_d, lo, hi), quantize_embeddings(E_d, "int8", ranges=np.stack([lo, hi]))
print("binario idéntico a sentence-transformers:", bool((mi_bin == st_bin).all()))
print("int8 difiere como máximo en", int(np.abs(mi_i8.astype(int) - st_i8.astype(int)).max()), "nivel (redondeo vs truncado)")
print(f"memoria del corpus: float32 {E_d.nbytes/1e3:.1f} KB · int8 {mi_i8.nbytes/1e3:.1f} KB · binario {mi_bin.nbytes/1e3:.1f} KB")
''')
    nb.md(r'''### Corpus ampliado para ver las diferencias
Con ≈ 90 documentos todo satisface al 100 %. Para estresar la cuantización **ampliamos el corpus con copias perturbadas** (casi-duplicados que actúan como *hard negatives*) y medimos qué fracción del **top-10 exacto en `float32`** conserva cada método (*neighbor recall@10*). Es la métrica estándar de ANN y aísla el error de cuantización del error del modelo.
''')
    nb.code(r'''
def aumenta(E, copias=40, sigma=0.5, seed=0):
    """Añade `copias` versiones ruidosas de cada vector (cos ≈ 0.9) para crear vecinos difíciles."""
    rng = np.random.default_rng(seed)
    bloques = [E]
    for _ in range(copias):
        ruido = rng.normal(size=E.shape)
        ruido *= sigma / np.linalg.norm(ruido, axis=1, keepdims=True)
        X = E + ruido
        bloques.append((X / np.linalg.norm(X, axis=1, keepdims=True)).astype(np.float32))
    return np.vstack(bloques)

def overlap_at_k(est, ref):
    return float(np.mean([len(set(a) & set(b)) / len(b) for a, b in zip(est, ref)]))

def exacto_topk(Eq, Ed, k=10):
    return topk_scores(Eq @ Ed.T, k)

E_big = aumenta(E_d)
Dd = E_big.shape[1]
ref = exacto_topk(E_q, E_big)
lo, hi = ajusta_rangos(E_big)
Q8 = cuantiza_int8(E_big, lo, hi)
filas = []   # (método, bytes por vector en RAM, overlap@10)
filas.append(("float32", 4 * Dd, 1.0))
for frac in (2, 4, 8):
    m = max(Dd // frac, 8)
    filas.append((f"float32 · {m} dims", 4 * m, overlap_at_k(exacto_topk(trunc_renorm(E_q, m), trunc_renorm(E_big, m)), ref)))
S8 = E_q @ descuantiza_int8(Q8, lo, hi).T
filas.append(("int8", Dd, overlap_at_k(topk_scores(S8, 10), ref)))
Bb = cuantiza_binario(E_big)
filas.append(("binario (Hamming)", Dd // 8, overlap_at_k(topk_scores(-hamming(np.packbits(E_q > 0, axis=1), Bb).astype(np.float32), 10), ref)))
filas.append(("binario + rescoring int8 (x4)", Dd // 8, overlap_at_k(busca_binario_rescore(E_q, Bb, Q8, lo, hi, 10, 4), ref)))
mu = E_big.mean(0)
Bc = cuantiza_binario(E_big, mu)
filas.append(("binario centrado + rescoring", Dd // 8, overlap_at_k(busca_binario_rescore(E_q, Bc, Q8, lo, hi, 10, 4, umbral=mu), ref)))
import pandas as pd
tabla_q = pd.DataFrame(filas, columns=["método", "bytes/vec (RAM)", "overlap@10 vs float32"])
tabla_q["MB para 10 M docs"] = (tabla_q["bytes/vec (RAM)"] * 10_000_000 / 1e6).round(0)
display(tabla_q.round(3))
''')
    nb.code(r'''
fig, ax = plt.subplots(figsize=(7.4, 4))
for nombre, b, o in filas:
    color = "#1F6FEB" if "float32" in nombre else ("#2CA02C" if nombre == "int8" else "#F28E2B")
    ax.scatter(b, o, s=70, color=color, zorder=3)
    ax.annotate(nombre, (b, o), textcoords="offset points", xytext=(6, -10), fontsize=8)
ax.set_xscale("log", base=2); ax.set_xlabel("bytes por vector en RAM (escala log)"); ax.set_ylabel("overlap@10 con el top-10 float32")
ax.set_title("Calidad vs memoria: recortar dimensiones vs recortar bits"); ax.grid(alpha=.3)
plt.tight_layout(); plt.show()
''')
    nb.md(r'''> 👀 **Qué debes observar.** (1) `int8` ocupa 4× menos y queda casi encima de `float32`: es la optimización "gratis". (2) La binaria sin rescoring cae mucho y **con rescoring** sube de forma notable ocupando 32× menos en RAM (los vectores `int8` pueden vivir en disco/SSD). *Cuánto* sube depende de la **dimensión**: con los 64 bits del fallback verás una recuperación parcial, mientras que con embeddings reales de 384–1024 dimensiones la binaria conserva mucha más información (el post de Hugging Face de 2024 reporta hasta ≈ 96 % del rendimiento con rescoring; mídelo con tu modelo). (3) Con el mismo presupuesto de bytes, **recortar bits suele dominar a recortar dimensiones** si el modelo no es Matryoshka; si lo es, combinarlos (p. ej. 512 dims binarias) forma la frontera de Pareto. (4) Centrar antes de binarizar ayuda cuando el modelo no produce coordenadas simétricas alrededor de 0. (5) **Memoria ≠ latencia**: en NumPy puro, Hamming con tabla de popcount es *más lento* que el producto matricial en `float32` (que usa BLAS). La binaria brilla en RAM; la velocidad llega con instrucciones `POPCNT`/SIMD de FAISS (`IndexBinaryFlat`) o de un motor de búsqueda, no con este código didáctico.
''')
    nb.code(r'''
factores = [1, 2, 4, 8, 16, 32]
ov = [overlap_at_k(busca_binario_rescore(E_q, Bb, Q8, lo, hi, 10, f), ref) for f in factores]
fig, ax = plt.subplots(figsize=(6.4, 3.4))
ax.plot(factores, ov, "o-", color="#F28E2B")
ax.set_xscale("log", base=2); ax.set_xticks(factores); ax.set_xticklabels(factores)
ax.set_xlabel("factor de sobre-muestreo 'over' (candidatos = 10 x over)"); ax.set_ylabel("overlap@10 con float32")
ax.set_title("Binaria + rescoring: más candidatos, más calidad (y más lecturas del int8)"); ax.grid(alpha=.3)
plt.tight_layout(); plt.show()
print({f: round(v, 3) for f, v in zip(factores, ov)})
''')
    nb.md(r'''> 👀 **Qué debes observar.** La curva sube rápido y luego se aplana: el rescoring de 4–10× candidatos suele bastar. Cada candidato extra implica **una lectura del vector `int8`** (a menudo de disco), así que `over` es un dial de latencia, no solo de calidad.
''')
    nb.gemini(
        "imagen", "M12-IMG-03", "De float32 a int8 y a bits",
        "Tres representaciones de un mismo embedding (float32, int8, binario) con su coste en bytes y el flujo de búsqueda binaria + rescoring.",
        """
        Diagrama técnico limpio, fondo blanco, formato 16:9. Paleta: azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280. Tipografía sans-serif. Sin elementos decorativos.

        PARTE SUPERIOR (3 filas, de arriba abajo): un mismo vector de 8 coordenadas de ejemplo [0.12, -0.50, 0.33, 0.01, -0.27, 0.64, -0.08, 0.41].
        Fila 1 (gris): "float32 · 4 bytes por dimensión" mostrando los 8 números en cajas anchas. A la derecha: "d = 1024 → 4096 bytes".
        Fila 2 (azul): "int8 · 1 byte por dimensión" mostrando los 8 enteros que da la cuantización con rango de calibración [lo, hi] = [-0.5, 0.5] en cada dimensión (q = round((x − lo)·255/(hi − lo)) − 128, recortado a [-128, 127]): [30, -128, 84, 2, -69, 127, -21, 104]; el 127 de la sexta casilla lleva la nota "recortado (0.64 > hi)". A la derecha: "d = 1024 → 1024 bytes".
        Fila 3 (naranja): "binario · 1 bit por dimensión" mostrando 8 cajitas con los bits 1 0 1 1 0 1 0 1 (1 si la coordenada es positiva). A la derecha: "d = 1024 → 128 bytes".

        PARTE INFERIOR: un flujo de izquierda a derecha con 3 cajas y flechas: "Query float32" → "Hamming (XOR + popcount) sobre bits: top 40 candidatos" (naranja) → "Rescoring: query float32 × vectores int8: top 10" (verde). Debajo una nota gris: "RAM: bits · Disco/SSD: int8".

        Evita: valores numéricos distintos a los indicados, texto ilegible, flechas cruzadas, ilustraciones de chips, logos.
        """,
        "Un vector en float32, int8 y bits con su coste en bytes, y el flujo de búsqueda binaria con rescoring",
        """
        float32 : [ 0.12 -0.50  0.33  0.01 -0.27  0.64 -0.08  0.41]   4096 B (d=1024)
        int8    : [  30 -128   84    2   -69  127   -21  104]          1024 B   ([lo,hi]=[-0.5,0.5])
        bits    : [   1    0    1    1     0    1     0    1]           128 B
        flujo   : query f32 -> Hamming top-40 -> rescoring int8 -> top-10
        """,
    )
    nb.md(r'''> 👀 **Qué debes observar.** Cada fila reduce el tamaño: 4× (float32→int8) y luego 8× (int8→bit), en total 32×. El flujo inferior es la receta que usan los sistemas de búsqueda: la compresión fuerte filtra y la precisión alta decide.
''')
    # ───────────────────────────── 8. Librerías de industria ─────────────────────────────
    nb.md(r'''## 6. Con librerías de industria: comparar embedders reales

`sentence-transformers` unifica la carga y el `encode` de casi todas las familias (con `trust_remote_code=True` en las que traen código propio, como GTE y Nomic). Comparamos los candidatos del catálogo en **tres ejes**: calidad (nDCG@10 en Políglota), **memoria** (bytes del corpus por dimensión) y **latencia** (ms por documento/consulta en tu hardware).

- Con `FAST_DEV_RUN = True` solo se prueban 2 modelos pequeños. Con `False` y una GPU se intentan todos (los modelos con licencia, como EmbeddingGemma, requieren aceptar los términos en Hugging Face y un token `HF_TOKEN`; si fallan, se omiten).
- Si ningún modelo se puede descargar, la tabla usa **dos fallbacks TF-IDF+SVD** de distinta dimensión: no representan a ningún modelo real, pero mantienen el notebook ejecutable.
''')
    nb.code(r'''
import gc
CANDIDATOS = list(MODELOS) if (not FAST_DEV_RUN and device == "cuda") else ["multilingual-e5-small", "paraphrase-multilingual-MiniLM-L12-v2"]
filas_zoo, POR_MODELO = [], {}

def mide(clave, e):
    t0 = time.perf_counter(); Ed = e.encode_docs(DOC_TXT); t_doc = (time.perf_counter() - t0) / len(DOC_TXT) * 1e3
    t0 = time.perf_counter(); Eq = e.encode_queries([q["text"] for q in QRYS]); t_q = (time.perf_counter() - t0) / len(QRYS) * 1e3
    run = run_denso(Eq, Ed)
    res, pq = evaluate(run, QRELS), ndcgs_por_query(run, QRELS)
    POR_MODELO[clave] = dict(Eq=Eq, Ed=Ed, ndcg_q=pq)
    filas_zoo.append(dict(modelo=clave, real=e.is_real, dim=Ed.shape[1], params_M=round(e.n_params / 1e6, 1),
                          ndcg10=round(res["ndcg"], 3), recall10=round(res["recall"], 3),
                          ms_por_doc=round(t_doc, 2), ms_por_query=round(t_q, 2),
                          GB_10M_docs_f32=round(Ed.shape[1] * 4 * 10e6 / 1e9, 1)))

for clave in CANDIDATOS:
    e = cargar_embedder(clave)
    if e is not None:
        mide(clave, e)
    del e; gc.collect()
if len(filas_zoo) < 2:                                   # sin modelos reales: dos fallbacks para poder comparar
    for d_fb in (32, 64):
        mide(f"tfidf-svd-{d_fb} (fallback)", Embedder("fb", {}, fallback=HashSVDEmbedder(d_fb).fit(DOC_TXT)))
zoo = pd.DataFrame(filas_zoo).sort_values("ndcg10", ascending=False).reset_index(drop=True)
display(zoo)
''')
    nb.code(r'''
fig, ax = plt.subplots(figsize=(7.2, 4))
for r in zoo.itertuples():
    ax.scatter(r.ms_por_doc, r.ndcg10, s=40 + r.dim / 4, alpha=.75, color="#1F6FEB" if r.real else "#6B7280")
    ax.annotate(f"{r.modelo[:22]} ({r.dim}d)", (r.ms_por_doc, r.ndcg10), textcoords="offset points", xytext=(6, 4), fontsize=8)
ax.set_xscale("log"); ax.set_xlabel("latencia de indexación (ms por documento, escala log)"); ax.set_ylabel("nDCG@10")
ax.set_title(f"Calidad vs latencia (tamaño = dimensión) · corpus {CORPUS['source']} · device={device}"); ax.grid(alpha=.3)
plt.tight_layout(); plt.show()
''')
    nb.md(r'''> 👀 **Qué debes observar.** Busca la **frontera**: el punto arriba-izquierda domina. Un modelo 2–3× más lento solo vale la pena si sube varios puntos de nDCG **en tu corpus**. El tamaño de la burbuja (dimensión) es el coste *de almacenamiento*; la abscisa, el coste *de indexación*. Los puntos grises son fallbacks sin significado de modelo real. Recuerda que la latencia depende de GPU/CPU, `batch_size` y longitud máxima: repite la medición en tu hardware de producción.
''')

    # ───────────────────────────── 9. Intervalos de confianza ─────────────────────────────
    nb.md(r'''### ¿La diferencia entre dos modelos es real? Bootstrap pareado
Con 58 queries, una diferencia de 0.02 de nDCG puede ser ruido. El **bootstrap pareado** remuestrea queries con reemplazo y calcula la distribución de la diferencia de medias; si el intervalo de confianza (IC) del 95 % incluye 0, no puedes afirmar que un modelo gane. (El módulo 15 formaliza esto.)
''')
    nb.code(r'''
def bootstrap_medias(x, n=2000, seed=SEED):
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(n, len(x)))
    return x[idx].mean(1)

def bootstrap_diff(a, b, n=2000, seed=SEED):
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(a), size=(n, len(a)))
    d = (a[idx] - b[idx]).mean(1)
    return d.mean(), np.percentile(d, [2.5, 97.5]), float((d > 0).mean())

claves = list(POR_MODELO)
fig, ax = plt.subplots(figsize=(7, 0.7 * len(claves) + 1.5))
for i, c in enumerate(claves):
    medias = bootstrap_medias(POR_MODELO[c]["ndcg_q"])
    lo_, hi_ = np.percentile(medias, [2.5, 97.5])
    ax.errorbar(medias.mean(), i, xerr=[[medias.mean() - lo_], [hi_ - medias.mean()]], fmt="o", color="#1F6FEB", capsize=4)
ax.set_yticks(range(len(claves))); ax.set_yticklabels([c[:34] for c in claves]); ax.invert_yaxis()
ax.set_xlabel("nDCG@10 con IC 95 % (bootstrap sobre queries)"); ax.set_title("¿Se distinguen los modelos?"); ax.grid(alpha=.3)
plt.tight_layout(); plt.show()
if len(claves) >= 2:
    a, b = claves[0], claves[1]
    media, ic, p = bootstrap_diff(POR_MODELO[a]["ndcg_q"], POR_MODELO[b]["ndcg_q"])
    print(f"{a} − {b}: Δ={media:+.3f} · IC95%=[{ic[0]:+.3f}, {ic[1]:+.3f}] · P(Δ>0)={p:.2f}")
    print("→ diferencia", "significativa" if ic[0] > 0 or ic[1] < 0 else "NO concluyente (el IC contiene 0)")
''')
    nb.md(r'''> 👀 **Qué debes observar.** Si las barras de error de dos modelos se solapan mucho y el IC de la diferencia contiene 0, **no hay evidencia para elegir uno**: decide por memoria, latencia o licencia. Con un golden set pequeño (decenas de queries) esto ocurre a menudo; la solución es **más queries**, no más modelos.
''')

    # ───────────────────────────── 10. MTEB ─────────────────────────────
    nb.md(r'''## 7. MTEB y MMTEB: qué miden y qué no

**MTEB** (Muennighoff et al., 2022) agrupa tareas de 8 tipos (clasificación, clustering, clasificación de pares, reranking, retrieval, STS, resumen, bitext mining). **MMTEB** (Enevoldsen et al., 2025) lo extiende de forma colaborativa a cientos de tareas y a más de 250 idiomas. La librería `mteb` (v2 en 2026) expone `mteb.get_benchmark(...)`, `mteb.get_model(...)` y `mteb.evaluate(...)`.

**Límites que debes conocer**
1. Un **promedio** mezcla tareas que quizá no te importan (p. ej. clasificación de sentimiento) con tu caso (retrieval en tu dominio).
2. **Contaminación y entrenamiento en el benchmark:** hay modelos que ven conjuntos de entrenamiento de las propias tareas; la librería marca para ello un indicador de *zero-shot* (`show_zero_shot` en la definición de cada benchmark). Un modelo "primero" puede no generalizar a tus datos.
3. **Idioma y dominio:** pocas tareas miden documentación técnica ES/EN/código, que es lo que busca Políglota.
4. Las diferencias de décimas en el leaderboard suelen estar **dentro del ruido**.
5. Las cifras de ranking cambian cada semana: **no las copies en un documento de decisión sin fecha ni enlace**.

Veamos qué contiene realmente `MTEB(Multilingual, v2)` (esto no descarga datos; solo lee los metadatos de la librería).
''')
    nb.code(r'''
try:
    import mteb
    from collections import Counter
    bench = mteb.get_benchmark("MTEB(Multilingual, v2)")
    tipos = Counter(t.metadata.type for t in bench.tasks)
    idiomas = {l for t in bench.tasks for l in t.metadata.languages}
    idiomas_ret = {l for t in bench.tasks if t.metadata.type == "Retrieval" for l in t.metadata.languages}
    print(f"mteb {mteb.__version__} · {len(bench.tasks)} tareas · {len(idiomas)} códigos de idioma en total, "
          f"pero solo {len(idiomas_ret)} en las tareas de Retrieval · tipos: {dict(tipos)}")
    print("¿hay retrieval en español?", "spa" in idiomas_ret)
    fig, ax = plt.subplots(figsize=(7, 3.4))
    orden = sorted(tipos.items(), key=lambda kv: -kv[1])
    ax.barh([k for k, _ in orden], [v for _, v in orden], color="#1F6FEB"); ax.invert_yaxis()
    ax.set_xlabel("nº de tareas"); ax.set_title(f"Composición de MTEB(Multilingual, v2) · {len(bench.tasks)} tareas")
    plt.tight_layout(); plt.show()
except Exception as e:
    print("mteb no disponible:", type(e).__name__, str(e)[:80])
''')
    nb.md(r'''> 👀 **Qué debes observar.** El benchmark es mayoritariamente de *clasificación, retrieval y STS* y los "cientos de idiomas" vienen sobre todo de tareas de *bitext mining*: si tu producto es retrieval, una parte importante del "promedio global" mide otra cosa y la cobertura de idiomas en retrieval es mucho menor. Por eso los equipos reportan **la columna de la tarea relevante** (p. ej. solo *Retrieval*), no el promedio.

Si tienes red, puedes **ejecutar una tarea pequeña** con `mteb` (celda protegida: cambia `RUN_MTEB = True`). `SciFact` es una de las tareas de retrieval más pequeñas de BEIR; el resultado principal es nDCG@10.
''')
    nb.code(r'''
RUN_MTEB = False          # pon True en Colab (necesita red y descarga el dataset + modelo)
if RUN_MTEB:
    import mteb
    modelo_mteb = mteb.get_model("intfloat/multilingual-e5-small")         # usa los prompts oficiales del modelo si MTEB los conoce
    tareas = mteb.get_tasks(tasks=["SciFact"])
    resultados = mteb.evaluate(modelo_mteb, tareas, encode_kwargs={"batch_size": 32})
    print(resultados)
else:
    print("RUN_MTEB=False: celda omitida (requiere red). La API v2 es mteb.get_model / mteb.get_tasks / mteb.evaluate.")
''')

    # ───────────────────────────── 11. Elegir ─────────────────────────────
    nb.md(r'''## 8. Cómo elegir un embedder: árbol de decisión

```
¿Tus documentos pueden salir de tu infraestructura y aceptas coste por llamada?
├─ SÍ → API (OpenAI text-embedding-3 · Cohere Embed v4 · Voyage · Gemini Embedding)
│        └─ elige por: idioma (ES/EN/código), contexto, dimensiones Matryoshka, precio, residencia de datos
└─ NO → pesos abiertos
         ├─ ¿CPU / dispositivo / latencia muy baja?   → EmbeddingGemma-300M · multilingual-e5-small/base · gte-multilingual-base
         ├─ ¿Una GPU T4/L4 y calidad alta?              → Qwen3-Embedding-0.6B/4B · BGE-M3 · Nomic Embed v2 (MoE)
         ├─ ¿Necesitas sparse + multi-vector del mismo modelo? → BGE-M3 (módulo 13)
         └─ ¿Presupuesto de GPU grande y calidad máxima? → Qwen3-Embedding-8B · NV-Embed (revisa la licencia)

Después, SIEMPRE, en este orden:
 1) mide en TU golden set (con IC)        2) ¿cabe en RAM? → Matryoshka (dims)   3) → int8   4) → binario + rescoring
 5) ¿contexto largo o multimodal? → módulos 13 (late chunking) y 16        6) licencia y plan de migración (módulo 18)
```

La tabla siguiente resume **solo atributos que pude verificar** (a oct-2026; `—` = no verificado, consulta la tarjeta/documentación). Las cifras de dimensión, contexto y licencia **cambian con las versiones**.
''')
    nb.code(r'''
FAMILIAS = pd.DataFrame([
    # familia, acceso, dim. completa / Matryoshka, contexto, multimodal, notas
    ("multilingual-e5 (small/base/large)", "abierto (MIT)", "384 / 768 / 1024 · no", "512 (paper)", False, "prefijos query:/passage:; 94 idiomas según la tarjeta"),
    ("BGE-M3", "abierto (MIT)", "1024 / no", "8192", False, "denso + sparse + multi-vector en un modelo (Chen et al. 2024)"),
    ("gte-multilingual-base", "abierto (Apache-2.0)", "768 / dimensiones elásticas", "8192", False, "305 M parámetros; también genera vectores sparse"),
    ("nomic-embed-text-v2-moe", "abierto (Apache-2.0)", "768 → 256 / sí", "512", False, "MoE: 475 M totales, 305 M activos; ≈ 100 idiomas"),
    ("Qwen3-Embedding (0.6B/4B/8B)", "abierto (Apache-2.0)", "0.6B: hasta 1024 / sí (32–1024)", "32k", False, "decoder, last-token, instrucciones en la query"),
    ("EmbeddingGemma-300m", "pesos con licencia Gemma (gated)", "768 → 128 / sí", "2k", False, "308 M parámetros; prompts por tarea"),
    ("jina-embeddings-v5-text (nano/small)", "pesos; CC-BY-NC-4.0 según la tarjeta", "nano 768 · small 1024 / sí (hasta 32)", "small 32k; nano 8k (8192 según el anuncio de Jina y Elastic; la página del modelo dice 32k)", False, "18-feb-2026 (239 M / 677 M); LoRA por tarea; hay variante omni (may-2026)"),
    ("gemini-embedding-001 (API)", "API", "3072 / sí (128–3072)", "2048", False, "solo el vector de 3072 sale normalizado: renormaliza tú al reducir"),
    ("gemini-embedding-2 (API; preview 10-mar-2026, GA 22-abr-2026)", "API", "3072 / sí (128–3072)", "8192 (texto)", True, "texto, imagen, video, audio y PDF en un espacio (módulo 16)"),
    ("OpenAI text-embedding-3-small/large (API)", "API", "1536 / 3072 · parámetro dimensions", "—", False, "ene-2024; el parámetro recorta dimensiones"),
    ("Cohere Embed v4 (API)", "API", "256/512/1024/1536 / sí", "128k", True, "texto + imágenes en un embedding"),
    ("Voyage-4 (API)", "API (large: cerrado)", "2048/1024/512/256 / sí + QAT", "32k", False, "anunciada el 15-ene-2026 (large, base, lite y nano de pesos abiertos); salidas float/int8/binario"),
], columns=["familia", "acceso", "dim / Matryoshka", "contexto", "multimodal", "notas"])

def shortlist(abierto=None, multimodal=None, matryoshka=None):
    t = FAMILIAS.copy()
    if abierto is not None:
        t = t[t["acceso"].str.contains("abierto|pesos", case=False) == abierto]
    if multimodal is not None:
        t = t[t["multimodal"] == multimodal]
    if matryoshka:
        t = t[t["dim / Matryoshka"].str.contains("sí|elásticas|parámetro", case=False)]
    return t[["familia", "acceso", "dim / Matryoshka", "contexto"]]

print("Caso Políglota (pesos abiertos + Matryoshka):")
display(shortlist(abierto=True, matryoshka=True))
''')
    nb.md(r'''> 👀 **Qué debes observar.** El filtro reduce 12 familias a unas pocas **candidatas**; el árbol no decide, **acota**. La decisión final sale de la tabla de la sección 6 (tu golden set) + el presupuesto de memoria de la sección 5.

### Ejemplo opcional: embeddings por API (protegido por variable de entorno)
No necesitas ninguna API para este curso. Si tienes `GEMINI_API_KEY`, esta celda embebe dos textos con `gemini-embedding-001`, reduce a 768 dimensiones y **renormaliza** (los vectores recortados no vienen unitarios).
''')
    nb.code(r'''
if os.environ.get("GEMINI_API_KEY"):
    from google import genai
    from google.genai import types
    cliente = genai.Client()
    r = cliente.models.embed_content(
        model="gemini-embedding-001",
        contents=["¿Cómo recorto un embedding?", "Truncate an embedding and renormalize it."],
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT", output_dimensionality=768),
    )
    V = np.array([e.values for e in r.embeddings], dtype=np.float32)
    V /= np.linalg.norm(V, axis=1, keepdims=True)            # renormalizar SIEMPRE tras reducir dimensiones
    print(V.shape, "coseno ES↔EN =", float(V[0] @ V[1]))
else:
    print("GEMINI_API_KEY no definida: celda omitida (opcional).")
''')

    # ───────────────────────────── 12. Producción ─────────────────────────────
    nb.md(r'''## 🗺️ Mapa de madurez (a oct-2026)
Ya has visto por dentro cada pieza (pooling last-token, prefijos, Matryoshka, int8/binaria, MTEB); la tabla las sitúa por madurez antes de pasar a cómo las usa la industria.

🟢 sólido (estándar de industria) · 🟡 emergente (resultados publicados, adopción parcial) · 🔴 experimental.

| Técnica | Madurez | Quién la usa (respaldado) | Fuente |
|---|---|---|---|
| Encoders contrastivos multilingües pequeños/medianos (E5, BGE-M3, GTE) | 🟢 | Microsoft (E5), BAAI (BGE-M3), Alibaba (mGTE) | Wang et al. 2024 (2402.05672); Chen et al. 2024 (2402.03216); Zhang et al. 2024 (2407.19669) |
| Prefijos / instrucciones de query y documento | 🟢 | E5 (`query:`/`passage:`), Qwen3-Embedding (`Instruct:`), EmbeddingGemma (prompts por tarea) | tarjetas de modelo; Wang et al. 2023 (2401.00368) |
| **Matryoshka (MRL)**: truncar + renormalizar | 🟢 | OpenAI (`dimensions`), Cohere Embed v4, Nomic v2, EmbeddingGemma, Qwen3-Embedding, Gemini Embedding, Voyage | Kusupati et al. 2022 (2205.13147); docs de cada proveedor |
| Cuantización `int8` de embeddings | 🟢 | `sentence-transformers`, Voyage (salida int8), Cohere | HF blog (Shakir, Aarsen, Lee 2024); docs |
| Cuantización **binaria** + rescoring | 🟡 | Cohere/Voyage ofrecen salida binaria; Elastic BBQ (vía RaBitQ, módulo 14). La calidad depende del modelo | HF blog 2024; Elastic Search Labs |
| *Quantization-aware training* de embedders | 🟡 | Voyage-4 (según su documentación en MongoDB/Azure) | docs de Voyage |
| LLM-as-embedder 0.5–1 B (Qwen3-Embedding-0.6B, Jina v5) | 🟢 | Alibaba, Jina | 2506.05176; página del modelo |
| LLM-as-embedder 7–8 B (e5-mistral, NV-Embed, Qwen3-Embedding-8B) | 🟡 | NVIDIA, Microsoft, Alibaba — coste de inferencia alto | 2401.00368; 2405.17428; 2506.05176 |
| Pooling *latent attention* (NV-Embed) | 🟡 | NVIDIA | 2405.17428 |
| LLM2Vec (decoder → encoder bidireccional) | 🟡 | investigación (McGill/Mila) | 2404.05961 |
| Embeddings multimodales unificados (Gemini Embedding 2, Jina v4/v5-omni) | 🟡 | Google (GA abr-2026), Jina — recientes; tema del módulo 16 | blog de Google (mar/abr-2026); Elastic (may-2026) |
| MoE para embeddings (Nomic Embed v2) | 🟡 | Nomic | 2502.07972 |
| Elegir embedder **solo** por el promedio de MTEB | 🔴 (mala práctica) | — | ver sección 7 |
| Evaluar en tu propio golden set con intervalos de confianza | 🟢 | práctica estándar en equipos de search | módulo 15 |
''')
    nb.md(r'''## 🏭 En producción

- **OpenAI** ofrece `text-embedding-3-small` y `-large` (25-ene-2024) con el parámetro `dimensions`, que acorta el vector descartando valores del final conservando sus propiedades (documentación y anuncio de OpenAI). *Es Matryoshka de cara al usuario.*
- **Google** publicó `gemini-embedding-001` (paper: Lee et al., 2025) y **EmbeddingGemma** (≈ 300 M, pensado para ejecutarse en dispositivo; Google indica que cuantizado cabe en menos de 200 MB de RAM). **Gemini Embedding 2** salió en *vista previa pública* el 10-mar-2026 como primer modelo nativamente multimodal de Google y pasó a disponibilidad general (`gemini-embedding-2`) el 22-abr-2026 (blog de Google; módulo 16).
- **Cohere Embed v4**: dimensiones Matryoshka 256/512/1024/1536, contexto de 128k y entrada multimodal (changelog oficial de Cohere).
- **Voyage-4** (familia): según la documentación de Voyage en MongoDB/Azure, entrenada con Matryoshka y *quantization-aware training*, con salidas float/int8/binario y un espacio de embeddings compartido entre tamaños (pudiendo indexar con el modelo grande y consultar con uno más barato). La familia (voyage-4-large, voyage-4, voyage-4-lite y voyage-4-nano de pesos abiertos) se anunció el 15-ene-2026 (MongoDB); algunos catálogos de terceros muestran fechas posteriores de versión.
- **Jina** (v3 con *task LoRA*, v4 multimodal, v5 en feb-2026 y v5-omni en may-2026 según Elastic), **Alibaba** (Qwen3-Embedding, Apache-2.0), **Nomic** (código y datos abiertos) y **Hugging Face** (TEI para servir, módulo 18) cubren el mundo de pesos abiertos.
- **Elastic** y otros motores aplican cuantización binaria derivada de RaBitQ (BBQ) para reducir memoria (módulo 14).

**Aritmética de coste** (10 M documentos, $d=1024$): `float32` = 40.96 GB · `int8` = 10.24 GB · binario = 1.28 GB (+ 10.24 GB de `int8` en disco si haces rescoring). Con $d=256$ Matryoshka + `int8`: 2.56 GB. Esa es la diferencia entre un clúster y un nodo.
''')
    nb.md(r'''## 🧠 Secretos de la élite

1. **Tu golden set manda sobre MTEB.** La librería `mteb` marca explícitamente qué resultados son *zero-shot*; un modelo puede liderar el promedio por haber visto datos de las tareas. Valida con IC (bootstrap) en tus queries (módulo 15).
2. **El prefijo/instrucción no es opcional.** Las tarjetas de E5, Nomic, Qwen3-Embedding y EmbeddingGemma definen formatos distintos; el README de Qwen3-Embedding indica que usar la instrucción «suele mejorar entre un 1 % y un 5 %» en la mayoría de tareas. Un fallo de prefijo es silencioso: ningún error, solo peor ranking.
3. **Last-token + padding a la derecha = bug silencioso.** Usa siempre el índice del último token *real* (`attention_mask.sum(1)-1`) o `padding_side="left"`; lo reproducimos en la sección 2.
4. **Calibra `int8` con el corpus, no con las queries.** `sentence-transformers` pide `calibration_embeddings` representativos; rangos calculados con pocas queries (más cortas, otra distribución) recortan los valores del corpus.
5. **Renormaliza siempre tras truncar o cuantizar.** No cuesta nada y evita mezclar normas en el producto escalar. Con `gemini-embedding-001`, fuentes de terceros indican que solo la salida de 3072 dimensiones viene normalizada: verifica en la documentación y renormaliza.
6. **Binaria = barata en RAM, pero con rescoring.** El post de Hugging Face (2024) y la documentación de `sentence-transformers` reportan hasta ≈ 96 % del rendimiento con 32× menos memoria *con rescoring*; la cifra depende del modelo y de la dimensión: mídela.
7. **La dimensión es una decisión de capacidad, no solo de memoria.** Weller et al. (2025) muestran, teórica y empíricamente (dataset sintético LIMIT), que una dimensión fija limita qué conjuntos top-k pueden representarse: dimensiones muy pequeñas fallan en consultas "combinatorias" aunque el promedio de MTEB parezca bueno. Se retoma en el módulo 15.
8. **Cambiar de embedder = reindexar todo.** Planifica versionado y migración (módulo 18); un espacio compartido entre tamaños (reportado para Voyage-4) permite asimetría query/documento sin reindexar.
''')
    nb.md(r'''## ⚠️ Errores comunes

| Error | Síntoma | Arreglo |
|---|---|---|
| Olvidar `query:`/`passage:` (o la instrucción) | nDCG baja unos puntos sin error | centraliza el formateo en un único `Embedder` y testéalo |
| Truncar un modelo sin MRL | calidad se desploma a < 256 dims | usa un modelo Matryoshka o PCA |
| No renormalizar tras truncar | ranking inestable con producto escalar | `e / ‖e‖` siempre |
| Calibrar `int8` con las queries | pérdida de calidad inexplicable | rangos sobre el corpus |
| Binarizar sin rescoring | recall muy inferior | `top-(k·over)` con Hamming + rescoring `int8` |
| Mezclar `padding_side` | embeddings de decoders raros | índice del último token real |
| Comparar modelos con 20 queries sin IC | "ganador" que cambia al re-muestrear | bootstrap pareado y más queries |
| Cortar `max_seq_length` sin mirar la fertilidad | español truncado antes que inglés | mide longitud en tokens por idioma |
| Mezclar embeddings de dos modelos/versiones en el mismo índice | recall aleatorio | un índice por (modelo, versión, dimensión, precisión) |
| Citar un rango de leaderboard sin fecha | decisión basada en dato caducado | fecha + enlace en el documento de decisión |
''')

    # ───────────────────────────── 13. Autoevaluación ─────────────────────────────
    nb.md(r'''## 📝 Autoevaluación

<details><summary><b>1 · (Cálculo)</b> Tienes 25 M de documentos con $d=768$. ¿Cuánta RAM ocupa el índice en <code>float32</code>, en <code>int8</code> y en binario? ¿Y si usas Matryoshka a 256 dimensiones + <code>int8</code>?</summary>

`float32`: $25\cdot10^6\cdot768\cdot4 = 76.8$ GB. `int8`: $19.2$ GB. Binario: $768/8=96$ B por vector → $2.4$ GB. Matryoshka 256 + `int8`: $256$ B por vector → $6.4$ GB. (Más los metadatos y la estructura del índice ANN, que no están incluidos.)
</details>

<details><summary><b>2 · (Cálculo)</b> Dos vectores binarios de 1024 bits difieren en 100 bits. ¿Cuál es el producto escalar de sus versiones $\pm1$ y su "coseno"?</summary>

$\langle a,b\rangle = d-2H = 1024-200 = 824$. Como $\lVert a\rVert=\lVert b\rVert=\sqrt{1024}$, el coseno es $824/1024\approx0.805$.
</details>

<details><summary><b>3 · (Diagnóstico)</b> Cambias de un modelo a otro de la misma familia y el nDCG@10 cae 6 puntos, sin errores. ¿Qué compruebas primero?</summary>

Los **prefijos/instrucciones** del nuevo modelo (cada versión puede cambiarlos), la **normalización** de los vectores, el **pooling/padding side** y el `max_seq_length`. Después, que el índice se haya reconstruido con el modelo nuevo (no mezclar espacios).
</details>

<details><summary><b>4 · (Diagnóstico)</b> Truncas un embedder de 768 a 128 dimensiones y el nDCG@10 pasa de 0.62 a 0.31. ¿Por qué y qué haces?</summary>

Muy probablemente el modelo **no** se entrenó con Matryoshka: la información está repartida por todas las coordenadas. Opciones: usar un modelo con MRL (Nomic v2, Qwen3-Embedding, EmbeddingGemma…), aprender una proyección **PCA** sobre tu corpus, o recortar bits (`int8`/binario) en lugar de dimensiones.
</details>

<details><summary><b>5 · (Transferencia)</b> Políglota tiene 50 M de fragmentos ES/EN/código y un nodo de 32 GB de RAM para el índice. Diseña la configuración de embedder, dimensión y precisión.</summary>

Presupuesto ≈ 20 GB para vectores (el resto, grafo ANN y overhead) → ≈ 400 B por vector con $50\cdot10^6$ vectores. Opciones: **384 dims `int8`** = 19.2 GB (justo), **256 dims `int8`** = 12.8 GB, o **512 dims binarias** = 3.2 GB en RAM con los `int8` de 512 dims (25.6 GB) en SSD para rescoring. Elegiría un modelo con MRL multilingüe que entienda código (Qwen3-Embedding-0.6B, Nomic v2 o EmbeddingGemma), mediría nDCG@10 en el golden set con IC para cada (dim, precisión) y escogería el punto de la frontera de Pareto que cumpla el SLA de latencia y recall.
</details>

<details><summary><b>6 · (Transferencia)</b> ¿Por qué un decoder con last-token pooling necesita que el texto termine con un token especial (EOS)?</summary>

Porque el vector es el estado del **último token**, y con atención causal solo ese estado ha atendido a todo el texto. El token final designado hace de "marcador de resumen" y el modelo se entrena para que ese estado condense el significado.
</details>

<details><summary><b>7 · (Recuerdo)</b> ¿Qué dos ingredientes de entrenamiento hacen que un prefijo del vector sea útil por sí solo?</summary>

La pérdida contrastiva evaluada en **varios prefijos** (anidados) y la **renormalización de cada prefijo** dentro de la pérdida.
</details>
''')

    # ───────────────────────────── 14. Referencias ─────────────────────────────
    nb.md(r'''## 📚 Referencias (verificadas; consultadas en oct-2026)

**Papers (arXiv)**
- Kusupati et al. (2022). *Matryoshka Representation Learning*. NeurIPS 2022. <https://arxiv.org/abs/2205.13147>
- Wang et al. (2024). *Multilingual E5 Text Embeddings: A Technical Report*. <https://arxiv.org/abs/2402.05672>
- Wang et al. (2023). *Improving Text Embeddings with Large Language Models* (e5-mistral). ACL 2024. <https://arxiv.org/abs/2401.00368>
- Chen et al. (2024). *M3-Embedding: Multi-Linguality, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation* (BGE-M3). Findings of ACL 2024. <https://arxiv.org/abs/2402.03216>
- Zhang et al. (2024). *mGTE: Generalized Long-Context Text Representation and Reranking Models for Multilingual Text Retrieval*. EMNLP 2024 (Industry Track). <https://arxiv.org/abs/2407.19669>
- Nussbaum et al. (2024). *Nomic Embed: Training a Reproducible Long Context Text Embedder*. TMLR. <https://arxiv.org/abs/2402.01613> · Nussbaum & Duderstadt (2025). *Training Sparse Mixture Of Experts Text Embedding Models*. <https://arxiv.org/abs/2502.07972>
- Lee et al. (2024). *NV-Embed: Improved Techniques for Training LLMs as Generalist Embedding Models*. ICLR 2025. <https://arxiv.org/abs/2405.17428>
- BehnamGhader et al. (2024). *LLM2Vec: Large Language Models Are Secretly Powerful Text Encoders*. COLM 2024. <https://arxiv.org/abs/2404.05961>
- Zhang et al. (2025). *Qwen3 Embedding: Advancing Text Embedding and Reranking Through Foundation Models*. <https://arxiv.org/abs/2506.05176>
- Lee et al. (2025). *Gemini Embedding: Generalizable Embeddings from Gemini*. <https://arxiv.org/abs/2503.07891>
- Vera et al. (2025). *EmbeddingGemma: Powerful and Lightweight Text Representations*. <https://arxiv.org/abs/2509.20354>
- Sturua et al. (2024). *jina-embeddings-v3: Multilingual Embeddings With Task LoRA*. <https://arxiv.org/abs/2409.10173> · Günther et al. (2025). *jina-embeddings-v4: Universal Embeddings for Multimodal Multilingual Retrieval*. <https://arxiv.org/abs/2506.18902>
- Muennighoff et al. (2022). *MTEB: Massive Text Embedding Benchmark*. EACL 2023. <https://arxiv.org/abs/2210.07316> · Enevoldsen et al. (2025). *MMTEB: Massive Multilingual Text Embedding Benchmark*. ICLR 2025. <https://arxiv.org/abs/2502.13595>
- Weller et al. (2025). *On the Theoretical Limitations of Embedding-Based Retrieval*. ICLR 2026. <https://arxiv.org/abs/2508.21038>
- Warner et al. (2024). *Smarter, Better, Faster, Longer: A Modern Bidirectional Encoder for Fast, Memory Efficient, and Long Context Finetuning and Inference* (ModernBERT). <https://arxiv.org/abs/2412.13663>

**Blogs de ingeniería y documentación**
- Shakir, Aarsen, Lee (2024). *Binary and Scalar Embedding Quantization for Significantly Faster & Cheaper Retrieval*. <https://huggingface.co/blog/embedding-quantization>
- Documentación de `sentence-transformers`: *Embedding Quantization*. <https://sbert.net/examples/applications/embedding-quantization/README.html>
- OpenAI (2024). *New embedding models and API updates*. <https://openai.com/index/new-embedding-models-and-api-updates/>
- Google (2026). *Gemini Embedding 2: Our first natively multimodal embedding model*. <https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-embedding-2/>
- Google (22-abr-2026). *Gemini Embedding 2 is now generally available*. <https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-embedding-2-generally-available/>
- Google AI for Developers. *EmbeddingGemma model overview*. <https://ai.google.dev/gemma/docs/embeddinggemma>
- Cohere. *Announcing Embed Multimodal v4* (changelog). <https://docs.cohere.com/v2/changelog/embed-multimodal-v4>
- MongoDB / Voyage AI. *Dimensions and quantization* (tutorial). <https://www.mongodb.com/docs/voyageai/tutorials/dimensions-and-quantization/>
- Jina AI. *jina-embeddings-v5-text-small*. <https://jina.ai/en-US/models/jina-embeddings-v5-text-small/> · Jina AI (feb-2026). *jina-embeddings-v5-text: New SOTA Small Multilingual Embeddings* (anuncio; tabla con el contexto de nano = 8192). <https://jina.ai/news/jina-embeddings-v5-text-distilling-4b-quality-into-sub-1b-multilingual-embeddings>
- Qwen. *Qwen3-Embedding* (README: tamaños, 32K, MRL, mejora del 1–5 % con instrucción). <https://github.com/QwenLM/Qwen3-Embedding>
- Solomatin, Enevoldsen, Chung (20-oct-2025, blog de Hugging Face). *Introducing MTEB v2: Evaluation of embedding and retrieval systems for more than just text*. <https://huggingface.co/blog/isaacchung/mteb-v2> · paquete `mteb` en PyPI. <https://pypi.org/project/mteb/>

**Para profundizar:** la lección del módulo 13 (BGE-M3 en sus tres modos), el módulo 14 (qué hace un índice ANN con estos vectores y RaBitQ) y el módulo 15 (evaluación rigurosa).
''')
    # <<APPEND_LESSON_4>>
    nb.save(LESSON)


def project() -> None:
    nb = Notebook("Proyecto 12 · Comparativa de embedders", colab_path=PROJECT, gpu=True)
    nb.md(nb.badge() + r'''

# Proyecto 12 · Comparativa de embedders para Políglota: calidad vs memoria vs latencia

| | |
|---|---|
| **Nivel** | 🟠 Avanzado |
| **Duración estimada** | ≈ 2 h |
| **GPU recomendada** | T4 para los 4–6 modelos (CPU basta con `FAST_DEV_RUN = True` y 2 modelos); ≈ 1–2 unidades de Colab con `FAST_DEV_RUN = False` |
| **Prerrequisitos** | Lección 12 · módulo 11 (tu embedder contrastivo, si lo guardaste) |

**Conexión.** *Viene de:* módulo 11 (tu embedder contrastivo ES/EN: lo medirás contra estos baselines si lo tienes guardado) y de la lección 12. *Va hacia:* módulo 13 (el mejor embedder será el retriever denso del sistema híbrido) y 14 (la configuración elegida decide el tamaño del índice).
''')
    nb.md(r'''## 1. Contexto de negocio
Eres ML engineer en **Políglota Labs**. Vamos a indexar **10 millones de fragmentos** de documentación (ES/EN/código). El CTO te da un límite: **el índice de vectores debe caber en ≈ 20 GB de RAM** y la búsqueda debe ser rápida. Tu tarea: construir una **comparativa reproducible de 4–6 embedders**, cada uno con **truncado Matryoshka** y **cuantización** (`float32`, `int8`, binaria, binaria+rescoring), y entregar una **recomendación justificada** con la frontera de Pareto calidad-memoria-latencia.

## 2. Dataset
Corpus Políglota vía `carga_corpus()` (Wikipedia ES/EN + CodeSearchNet si hay acceso a Hugging Face; si no, el **corpus sintético** del módulo 00: texto ES/EN de plantillas + funciones de la stdlib como código — verás un `⚠️`). Con el corpus sintético los números **no son comparables** con los del real, pero el pipeline y las conclusiones relativas (int8 ≈ float32, binaria necesita rescoring…) sí se ejercitan.

## 3. Entregables
1. `construye_store` / `buscar` funcionando para 4 precisiones (`float32`, `int8`, `binario`, `binario+rescore`) y 4 escalas de dimensión (D, D/2, D/4, D/8).
2. Una **tabla de resultados** (`RESULTS`) con: modelo, dimensión, precisión, nDCG@10, overlap@10 vs float32, bytes/vector, MB para 10 M docs, ms/query.
3. La **frontera de Pareto** (memoria vs nDCG@10) y una **recomendación** para el presupuesto de 20 GB.
4. Una conclusión escrita (≤ 10 líneas) que cite números de **tu** tabla.

## 4. Rúbrica (umbrales calibrados con lo que MIDE la solución de referencia)
Los umbrales de abajo son **invariantes relativas** a la propia ejecución (no valores absolutos), porque el nDCG absoluto depende del corpus y de los modelos que puedas descargar. La solución de referencia se ejecutó en un entorno **sin acceso a Hugging Face** (corpus sintético + embedders de respaldo TF-IDF+SVD + un modelo local diminuto con pesos aleatorios para ejercitar la ruta de `sentence-transformers`); los valores medidos están en la última columna. **No se verificó con modelos reales descargados**; si en Colab tus números reales son mejores, mejor.

| # | Criterio | Umbral | Medido por la solución de referencia |
|---|---|---|---|
| R1 | `trunc_renorm` devuelve vectores de norma 1 | `max |‖x‖−1| < 1e-5` | 1.2e-7 (precisión de float32) |
| R2 | Binario idéntico a `sentence-transformers` (`ubinary`) e `int8` a ≤ 1 nivel | exacto / ≤ 1 | binario idéntico; int8 ≤ 1 nivel |
| R3 | `int8` conserva la calidad: nDCG@10 ≥ float32 − 0.03 en **todas** las filas | cumplido en el 100 % de filas | peor caso −0.008 de nDCG@10 |
| R4 | `int8` conserva el ranking: overlap@10 (vs float32 a igual dimensión) medio ≥ 0.85 | ≥ 0.85 | media 0.948 con los respaldos TF-IDF+SVD y 0.895 con el modelo diminuto aleatorio (mínimos 0.865 y 0.811) |
| R5 | El rescoring ayuda: overlap(binario+rescore) ≥ overlap(binario) en ≥ 90 % de las filas | ≥ 90 % | 100 % de las filas |
| R6 | Memoria: `int8` = m bytes/vec y binario = m/8 bytes/vec | exacto | exacto |
| R7 | La frontera de Pareto tiene ≥ 3 puntos y ≥ 1 punto que **no** es `float32` | ≥ 3 | 8 puntos (respaldos) / 5 puntos (modelo diminuto) |
| R8 | La recomendación respeta el presupuesto de 20 GB (10 M docs) | ≤ 20 GB | 3.2 GB (respaldos) / 0.64 GB (modelo diminuto) |
| R9 | Conclusión escrita con ≥ 3 números de tu tabla | — | revisión manual |
''')

    # ── setup (mismas utilidades que la lección) ──
    nb.md(r'''## 5. Preparación (celdas dadas, no hay que modificarlas)''')
    nb.code(CODE_PIP)
    nb.code(C.CODE_SETUP_COMMON)
    for _src in src_corpus_cells():
        nb.code(_src)
    nb.code(SRC_METRICS)
    nb.code(C.CODE_EVAL_PQ)
    nb.code(CODE_EMBEDDER_TOOLS)
    nb.code(r'''
import pandas as pd
import matplotlib.pyplot as plt

CORPUS = carga_corpus(FAST_DEV_RUN)
DOC_IDS = [d["id"] for d in CORPUS["docs"]]
DOC_TXT = [d["text"] for d in CORPUS["docs"]]
QRYS, QRELS = CORPUS["queries"], CORPUS["qrels"]
Q_TXT = [q["text"] for q in QRYS]

POPCNT = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)

def topk_scores(S, k):
    """Índices de los k mayores scores por fila, ordenados de mayor a menor."""
    idx = np.argpartition(-S, min(k, S.shape[1] - 1), axis=1)[:, :k]
    orden = np.take_along_axis(S, idx, 1).argsort(1)[:, ::-1]
    return np.take_along_axis(idx, orden, 1)

def overlap_at_k(est, ref):
    return float(np.mean([len(set(a) & set(b)) / len(b) for a, b in zip(est, ref)]))

def aumenta(E, copias=40, sigma=0.5, seed=0):
    """Corpus ampliado con casi-duplicados (cos ≈ 0.9) para crear vecinos difíciles."""
    rng = np.random.default_rng(seed)
    bloques = [E]
    for _ in range(copias):
        ruido = rng.normal(size=E.shape)
        ruido *= sigma / np.linalg.norm(ruido, axis=1, keepdims=True)
        X = E + ruido
        bloques.append((X / np.linalg.norm(X, axis=1, keepdims=True)).astype(np.float32))
    return np.vstack(bloques)

def run_desde_indices(idx):
    return {q["qid"]: [DOC_IDS[j] for j in idx[i]] for i, q in enumerate(QRYS)}

N_DOCS_PROD = 10_000_000          # tamaño de producción para extrapolar memoria
PRESUPUESTO_GB = 20               # límite del CTO
print(CORPUS["source"], len(DOC_IDS), "docs ·", len(QRYS), "queries")
''')

    # ── TODO 1: embedders ──
    nb.md(r'''## 6. Paso 1 — Codificar con 4–6 embedders (TODO 1)
Usa `cargar_embedder(clave)` (ya definido): devuelve un `Embedder` con `encode_queries` / `encode_docs` que **aplican el prefijo correcto**. Si no se puede descargar, devuelve `None`. En ese caso el proyecto añade **embedders de respaldo** (TF-IDF+SVD con distintas configuraciones) para que la comparativa siga ejecutándose.

Mide para cada modelo: embeddings de queries/documentos, **ms por documento** y **ms por query**, y el número de parámetros.

<details><summary>🪜 Pista 1 (idea)</summary>
Itera sobre una lista de claves de <code>MODELOS</code>; por cada una llama a <code>cargar_embedder</code>, mide el tiempo con <code>time.perf_counter()</code> alrededor de <code>encode_docs</code> y <code>encode_queries</code>, y guarda todo en un diccionario <code>BANCO[clave]</code>.
</details>
<details><summary>🪜 Pista 2 (casi la API)</summary>
<code>t0 = time.perf_counter(); Ed = e.encode_docs(DOC_TXT); ms_doc = (time.perf_counter()-t0)/len(DOC_TXT)*1e3</code> · guarda <code>dict(Eq=Eq, Ed=Ed, ms_doc=..., ms_q=..., params_M=e.n_params/1e6, real=e.is_real)</code>.
</details>
''')
    nb.code(r'''
CLAVES_REALES = (["multilingual-e5-small", "paraphrase-multilingual-MiniLM-L12-v2"] if FAST_DEV_RUN else
                 ["multilingual-e5-small", "multilingual-e5-base", "gte-multilingual-base",
                  "Qwen3-Embedding-0.6B", "bge-m3", "embeddinggemma-300m"])
FALLBACKS = {   # respaldo si no hay red: (dim, n-gramas, analizador)
    "tfidf-svd-64 (fallback)": (64, (3, 5), "char_wb"),
    "tfidf-svd-32 (fallback)": (32, (2, 4), "char_wb"),
    "tfidf-svd-80 (fallback)": (80, (3, 5), "char_wb"),
    "palabras-svd-48 (fallback)": (48, (1, 2), "word"),
}

def codifica_modelo(clave, e):
    """TODO 1: devuelve dict(Eq, Ed, ms_doc, ms_q, params_M, real) para el embedder `e`."""
    # TODO 1.a: mide el tiempo de encode_docs(DOC_TXT) y encode_queries(Q_TXT)
    # TODO 1.b: devuelve el diccionario descrito arriba
    raise NotImplementedError("TODO 1")

def construye_banco():
    banco = {}
    for clave in CLAVES_REALES:
        e = cargar_embedder(clave)
        if e is not None:
            banco[clave] = codifica_modelo(clave, e)
    if len(banco) < 4:                                    # completa hasta 4 con respaldos (solo sin red)
        for nombre, (dim, ng, an) in FALLBACKS.items():
            if len(banco) >= 4:
                break
            fb = Embedder(nombre, {}, fallback=HashSVDEmbedder(dim, ng, an).fit(DOC_TXT))
            banco[nombre] = codifica_modelo(nombre, fb)
    return banco

try:
    BANCO = construye_banco()
    print({k: (v["Ed"].shape, round(v["ms_doc"], 2)) for k, v in BANCO.items()})
except NotImplementedError as e:
    BANCO = {}
    print("⏳ pendiente:", e)
''')

    # ── TODO 2: truncado ──
    nb.md(r'''## 7. Paso 2 — Truncado Matryoshka (TODO 2)
Implementa `trunc_renorm(E, m)`: conserva las primeras `m` dimensiones y **renormaliza** cada fila a norma 1 (protege la división por cero con `np.maximum(norma, 1e-9)`).
Después `dims_grid(D)` devuelve las 4 escalas `D, D/2, D/4, D/8` redondeadas a múltiplos de 8 (la binaria empaqueta de 8 en 8) y nunca menores que 8.
''')
    nb.code(r'''
def trunc_renorm(E, m):
    """Primeras m dimensiones + renormalización L2."""
    # TODO 2: implementa el truncado y la renormalización
    raise NotImplementedError("TODO 2")

def dims_grid(D):
    """D, D/2, D/4, D/8 redondeadas a múltiplos de 8, sin repetir y >= 8."""
    return sorted({max(8, (D // f) // 8 * 8) for f in (1, 2, 4, 8)}, reverse=True)

try:
    X = trunc_renorm(next(iter(BANCO.values()))["Ed"], 16) if BANCO else None
    if X is not None:
        print("normas:", np.linalg.norm(X, axis=1)[:3])
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''')

    # ── TODO 3-4: cuantización ──
    nb.md(r'''## 8. Paso 3 — Cuantización `int8` y binaria (TODO 3 y 4)
**TODO 3 (`int8`).** `ajusta_rangos` calcula `lo`/`hi` por dimensión **sobre el corpus**. `cuantiza_int8` aplica $q=\operatorname{round}((x-lo)/((hi-lo)/255))-128$ recortado a $[-128,127]$ (`np.int8`) y `descuantiza_int8` lo invierte.

**TODO 4 (binaria).** `cuantiza_binario` empaqueta `E > 0` con `np.packbits(..., axis=1)`. `hamming(qb, db)` devuelve la matriz (nº queries × nº docs) de distancias de Hamming usando XOR + la tabla `POPCNT` (procesa los documentos por bloques para no agotar RAM).

<details><summary>🪜 Pista 1 (idea)</summary>
Hamming = nº de bits distintos = popcount(a XOR b). Un byte tiene 256 valores posibles: <code>POPCNT[x]</code> te da el popcount por tabla. Suma sobre los bytes de cada vector.
</details>
<details><summary>🪜 Pista 2 (casi la API)</summary>
<code>x = qb[:, None, :] ^ db[None, s:s+bloque, :]</code> y después <code>POPCNT[x].sum(-1)</code>. Para int8: <code>paso = np.maximum(hi-lo, 1e-9)/255</code>; <code>np.clip(np.round((E-lo)/paso)-128, -128, 127).astype(np.int8)</code>.
</details>
''')
    nb.code(r'''
def ajusta_rangos(E_calib):
    # TODO 3.a: devuelve (lo, hi) por dimensión calculados sobre el corpus
    raise NotImplementedError("TODO 3.a")

def cuantiza_int8(E, lo, hi):
    # TODO 3.b: cuantización escalar a int8 con 256 niveles
    raise NotImplementedError("TODO 3.b")

def descuantiza_int8(Q, lo, hi):
    # TODO 3.c: inversa aproximada, devuelve float32
    raise NotImplementedError("TODO 3.c")

def cuantiza_binario(E, umbral=0.0):
    # TODO 4.a: bits (E > umbral) empaquetados en uint8, forma (N, D/8)
    raise NotImplementedError("TODO 4.a")

def hamming(qb, db, bloque=2048):
    # TODO 4.b: matriz (nq, nd) de distancias de Hamming (XOR + POPCNT), por bloques de documentos
    raise NotImplementedError("TODO 4.b")

try:
    ref_bin = np.packbits(np.random.default_rng(0).normal(size=(4, 32)) > 0, axis=1)
    print("hamming(x, x) = 0:", int(hamming(ref_bin, ref_bin).trace()) == 0)
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''')

    # ── TODO 5: búsqueda ──
    nb.md(r'''## 9. Paso 4 — Búsqueda con cada precisión (TODO 5)
`construye_store(Ed, m)` prepara, para una escala `m`, los vectores truncados en las tres representaciones; `buscar(Eq, store, precision, k, over)` devuelve los índices del top-k:

- `float32`: producto escalar exacto sobre los vectores truncados y renormalizados.
- `int8`: la query en `float32` contra los documentos `int8` **descuantizados**.
- `binario`: ordena por menor Hamming entre `Q > 0` empaquetada y los bits de los documentos.
- `binario+rescore`: recupera `k*over` candidatos por Hamming y **reordena** con la query `float32` contra los `int8` descuantizados.

<details><summary>🪜 Pista 1 (idea)</summary>
El rescoring es "dos etapas": primero un top-(k·over) barato (Hamming), luego un top-k caro pero solo sobre esos candidatos (producto escalar con vectores descuantizados).
</details>
<details><summary>🪜 Pista 2 (casi la API)</summary>
<code>H = hamming(np.packbits(Q &gt; 0, axis=1), store["bin"])</code> · <code>cand = topk_scores(-H.astype(np.float32), k*over)</code> · para cada query <code>v = descuantiza_int8(store["int8"][cand[i]], lo, hi)</code> y <code>cand[i][np.argsort(-(v @ Q[i]))[:k]]</code>.
</details>
''')
    nb.code(r'''
def construye_store(Ed, m):
    # TODO 5.a: trunca+renormaliza, ajusta rangos, cuantiza a int8 y a binario. Devuelve un dict con
    #           claves "m", "f32", "int8", "lo", "hi", "bin"
    raise NotImplementedError("TODO 5.a")

def buscar(Eq, store, precision, k=10, over=4):
    # TODO 5.b: implementa las 4 precisiones: "float32", "int8", "binario", "binario+rescore"
    raise NotImplementedError("TODO 5.b")

try:
    c0 = next(iter(BANCO.values()))
    st0 = construye_store(c0["Ed"], dims_grid(c0["Ed"].shape[1])[1])
    print({p: buscar(c0["Eq"], st0, p).shape for p in ("float32", "int8", "binario", "binario+rescore")})
except (NotImplementedError, StopIteration) as e:
    print("⏳ pendiente:", repr(e))
''')

    # ── TODO 6: evaluación de la rejilla ──
    nb.md(r'''## 10. Paso 5 — La rejilla completa (TODO 6)
Para cada modelo × escala × precisión calcula:
- `ndcg10` y `recall10` sobre el corpus original (`store` construido con `Ed`),
- `overlap10`: fracción del top-10 exacto en `float32` **a la misma dimensión m** que conserva el método (aísla el error de *cuantización* del de truncado), medido sobre el **corpus ampliado** `aumenta(Ed)` (vecinos difíciles),
- `bytes_vec` en RAM (`float32`: 4m · `int8`: m · `binario` y `binario+rescore`: m/8), `MB_10M` = bytes · 10 M / 10⁶ y `ms_query` (latencia media por query sobre el corpus ampliado).

<details><summary>🪜 Pista 1 (idea)</summary>
Construye dos <code>store</code> por (modelo, m): uno con <code>Ed</code> (para nDCG) y otro con <code>E_big</code> (para overlap y latencia). La referencia <code>ref_m</code> es el top-10 exacto <code>float32</code> a la misma dimensión <code>m</code> sobre <code>E_big</code>: se obtiene con <code>buscar(Eq, st_big, "float32")</code>.
</details>
''')
    nb.code(r'''
BYTES = {"float32": lambda m: 4 * m, "int8": lambda m: m, "binario": lambda m: m // 8, "binario+rescore": lambda m: m // 8}

def evalua_rejilla(banco):
    """TODO 6: devuelve un DataFrame con una fila por (modelo, dim, precision)."""
    filas = []
    # TODO 6.a: para cada modelo: E_big = aumenta(Ed)
    # TODO 6.b: para cada m en dims_grid(D): ref_m = buscar(Eq, st_big, "float32"); y para cada precision:
    #           ndcg10/recall10 (store con Ed), overlap10 vs ref_m y ms_query (store con E_big)
    # TODO 6.c: añade bytes_vec = BYTES[precision](m) y MB_10M = bytes_vec * N_DOCS_PROD / 1e6
    raise NotImplementedError("TODO 6")

try:
    RESULTS = evalua_rejilla(BANCO)
    display(RESULTS.round(3).head(12))
except NotImplementedError as e:
    RESULTS = None
    print("⏳ pendiente:", e)
''')

    # ── TODO 7: Pareto y recomendación ──
    nb.md(r'''## 11. Paso 6 — Frontera de Pareto y recomendación (TODO 7)
Una configuración está en la **frontera de Pareto** si ninguna otra tiene a la vez **menos memoria y mejor (o igual) nDCG@10**. Implementa:
- `frontera_pareto(df)`: devuelve las filas no dominadas ordenadas por `bytes_vec` creciente (recorre en orden de memoria y conserva una fila solo si su `ndcg10` supera estrictamente el mejor visto).
- `recomienda(df, presupuesto_gb, n_docs)`: entre las filas que caben en el presupuesto (`bytes_vec * n_docs / 1e9 <= presupuesto_gb`), elige la de mayor `ndcg10` (desempate: menos bytes, luego menos `ms_query`).
Después dibuja la frontera (`bytes_vec` en escala log vs `ndcg10`) coloreando por precisión.

<details><summary>🪜 Pista 1 (idea)</summary>
Es el «skyline» de un problema con dos objetivos: si ordenas por memoria creciente, una fila solo entra en la frontera si mejora el mejor nDCG visto hasta entonces. Es la misma lectura que la curva tasa-distorsión del módulo 08 (bits frente a calidad).
</details>
<details><summary>🪜 Pista 2 (casi la API)</summary>
<code>d = df.sort_values(["bytes_vec", "ndcg10"], ascending=[True, False])</code>; recorre <code>d.itertuples()</code> guardando <code>r.Index</code> cuando <code>r.ndcg10 &gt; mejor</code>; devuelve <code>d.loc[keep]</code>. Para <code>recomienda</code>: filtra con la condición de presupuesto y <code>sort_values(["ndcg10", "bytes_vec", "ms_query"], ascending=[False, True, True]).iloc[0]</code>. El gráfico: <code>ax.scatter</code> por grupo de <code>precision</code>, <code>ax.plot</code> de la frontera y <code>ax.set_xscale("log", base=2)</code>.
</details>
''')
    nb.code(r'''
def frontera_pareto(df):
    # TODO 7.a: filas no dominadas (menos memoria y mejor ndcg10), ordenadas por bytes_vec
    raise NotImplementedError("TODO 7.a")

def recomienda(df, presupuesto_gb=PRESUPUESTO_GB, n_docs=N_DOCS_PROD):
    # TODO 7.b: mejor configuración que cabe en el presupuesto
    raise NotImplementedError("TODO 7.b")

def dibuja_frontera(df, frontera):
    # TODO 7.c: scatter de todas las filas (color por precision) y línea que une la frontera
    raise NotImplementedError("TODO 7.c")

try:
    FRONT = frontera_pareto(RESULTS)
    REC = recomienda(RESULTS)
    dibuja_frontera(RESULTS, FRONT)
    plt.show()
    print("Recomendación:", REC.to_dict())
except (NotImplementedError, AttributeError, TypeError) as e:
    FRONT = REC = None
    print("⏳ pendiente:", repr(e))
''')
    nb.md(r'''> 👀 **Qué debes observar:** ¿qué precisiones forman la frontera? Si contiene puntos que no son `float32` (la solución de referencia los tiene: R7), a igual memoria te conviene más recortar **bits** que dimensiones; si no, comprueba tus `bytes_vec`. Mira dónde cruza la frontera la línea del presupuesto: esa es tu recomendación. Si un modelo entero queda por debajo de la frontera en todas sus escalas, está dominado y se descarta por datos, no por opinión. Con el corpus de respaldo los valores absolutos cambian; la forma de la frontera es lo que debes defender.''')
    nb.md(r'''## 12. Autocomprobación de la rúbrica
Esta celda evalúa R1–R8 sobre **tus** funciones y resultados. Debe imprimir `✅` en todo cuando termines (R9 es manual: escribe tu conclusión en la celda de abajo).
''')
    CODE_GRADER = r'''
def autograder():
    checks = {}
    try:
        X = trunc_renorm(np.random.default_rng(1).normal(size=(50, 40)).astype(np.float32), 24)
        checks["R1 trunc_renorm norma 1"] = bool(np.abs(np.linalg.norm(X, axis=1) - 1).max() < 1e-5)
    except Exception as e:
        checks["R1 trunc_renorm norma 1"] = False
    try:
        from sentence_transformers.util import quantize_embeddings
        E = np.random.default_rng(2).normal(size=(60, 64)).astype(np.float32)
        lo, hi = ajusta_rangos(E)
        ok_bin = bool((cuantiza_binario(E) == quantize_embeddings(E, "ubinary")).all())
        d = np.abs(cuantiza_int8(E, lo, hi).astype(int) - quantize_embeddings(E, "int8", ranges=np.stack([lo, hi])).astype(int)).max()
        checks["R2 binario == ubinary e int8 ≤ 1 nivel"] = ok_bin and d <= 1
    except Exception as e:
        checks["R2 binario == ubinary e int8 ≤ 1 nivel"] = False
    R = RESULTS
    if R is not None:
        piv = R.pivot_table(index=["modelo", "dim"], columns="precision", values=["ndcg10", "overlap10"])
        checks["R3 int8 ≥ float32 − 0.03 (nDCG, todas las filas)"] = bool((piv["ndcg10"]["int8"] >= piv["ndcg10"]["float32"] - 0.03).all())
        checks["R4 overlap int8 medio ≥ 0.85"] = bool(piv["overlap10"]["int8"].mean() >= 0.85)
        checks["R5 rescoring ≥ binario en ≥ 90 % de filas"] = bool((piv["overlap10"]["binario+rescore"] >= piv["overlap10"]["binario"] - 1e-9).mean() >= 0.90)
        okmem = all(r.bytes_vec == BYTES[r.precision](r.dim) for r in R.itertuples())
        checks["R6 memoria exacta (int8=m, binario=m/8)"] = bool(okmem)
    else:
        for k in ("R3 int8 ≥ float32 − 0.03 (nDCG, todas las filas)", "R4 overlap int8 medio ≥ 0.85",
                  "R5 rescoring ≥ binario en ≥ 90 % de filas", "R6 memoria exacta (int8=m, binario=m/8)"):
            checks[k] = False
    checks["R7 Pareto ≥ 3 puntos y ≥ 1 no-float32"] = bool(FRONT is not None and len(FRONT) >= 3 and (FRONT["precision"] != "float32").any())
    checks["R8 recomendación dentro del presupuesto"] = bool(REC is not None and REC["bytes_vec"] * N_DOCS_PROD / 1e9 <= PRESUPUESTO_GB)
    for k, v in checks.items():
        print("✅" if v else "❌", k)
    return checks

_ = autograder()
'''
    nb.code(CODE_GRADER)
    nb.md(r'''## 13. Tu conclusión (R9)
Escribe aquí (≤ 10 líneas, con números de tu tabla): ¿qué configuración recomiendas para 10 M de documentos en 20 GB, por qué, y qué riesgos tiene (licencia, latencia, calidad en código, drift)?

> *(Edita esta celda.)*
''')

    nb.md(r'''## 14. Retos extra (nivel experto)
1. **PCA en lugar de truncado** para los modelos sin Matryoshka: compara la curva nDCG vs dimensión con y sin PCA (aprende la proyección con el corpus).
2. **Product Quantization** (anticipo del módulo 14): comprime a 32–64 bytes/vector y colócala en la gráfica de Pareto.
3. **Bootstrap pareado** (lección, sección 6): añade intervalos de confianza al nDCG y marca qué diferencias son significativas.
4. **Tu embedder del módulo 11** como un modelo más: ¿le gana a `multilingual-e5-small` en código?
5. **Asimetría**: indexa documentos con un modelo grande y consulta con uno pequeño de la misma familia (solo si comparten espacio de embeddings; compruébalo midiendo, no lo asumas).

## 15. Reflexión (conecta con producción y con el hilo conductor)
- ¿Qué cambia si el 80 % de las queries son en español y los documentos están mayoritariamente en inglés? ¿Qué métrica añadirías por idioma?
- El rescoring `int8` vive en disco: ¿qué latencia p99 añade leer `k·over` vectores por query? (módulo 14)
- ¿Cómo versionarías el índice para migrar de embedder sin downtime? (módulo 18)
- ¿Qué parte de tu comparativa se rompería con un corpus de 100 M de documentos?
''')

    # ── Solución ──
    nb.md(r'''---
# ⛔ SPOILER — intenta resolverlo primero
Debajo está la solución de referencia completa. Si ejecutas las celdas siguientes **sobrescribes** tus funciones con las de la solución.
''')
    nb.code(r'''
# ── SOLUCIÓN DE REFERENCIA: TODO 1 ──
def codifica_modelo(clave, e):
    t0 = time.perf_counter(); Ed = e.encode_docs(DOC_TXT); ms_doc = (time.perf_counter() - t0) / len(DOC_TXT) * 1e3
    t0 = time.perf_counter(); Eq = e.encode_queries(Q_TXT); ms_q = (time.perf_counter() - t0) / len(Q_TXT) * 1e3
    return dict(Eq=Eq, Ed=Ed, ms_doc=ms_doc, ms_q=ms_q, params_M=e.n_params / 1e6, real=e.is_real)

# ── TODO 2 ──
def trunc_renorm(E, m):
    X = E[:, :m]
    return (X / np.maximum(np.linalg.norm(X, axis=1, keepdims=True), 1e-9)).astype(np.float32)

# ── TODO 3 ──
def ajusta_rangos(E_calib):
    return E_calib.min(0), E_calib.max(0)

def cuantiza_int8(E, lo, hi):
    paso = np.maximum(hi - lo, 1e-9) / 255.0
    return np.clip(np.round((E - lo) / paso) - 128, -128, 127).astype(np.int8)

def descuantiza_int8(Q, lo, hi):
    paso = np.maximum(hi - lo, 1e-9) / 255.0
    return (Q.astype(np.float32) + 128) * paso + lo

# ── TODO 4 ──
def cuantiza_binario(E, umbral=0.0):
    return np.packbits(E > umbral, axis=1)

def hamming(qb, db, bloque=2048):
    out = np.empty((len(qb), len(db)), dtype=np.int32)
    for s in range(0, len(db), bloque):
        out[:, s:s + bloque] = POPCNT[qb[:, None, :] ^ db[None, s:s + bloque, :]].sum(-1)
    return out

# ── TODO 5 ──
def construye_store(Ed, m):
    X = trunc_renorm(Ed, m)
    lo, hi = ajusta_rangos(X)
    return {"m": m, "f32": X, "int8": cuantiza_int8(X, lo, hi), "lo": lo, "hi": hi, "bin": cuantiza_binario(X)}

def buscar(Eq, store, precision, k=10, over=4):
    Q = trunc_renorm(Eq, store["m"])
    if precision == "float32":
        return topk_scores(Q @ store["f32"].T, k)
    if precision == "int8":
        return topk_scores(Q @ descuantiza_int8(store["int8"], store["lo"], store["hi"]).T, k)
    H = hamming(np.packbits(Q > 0, axis=1), store["bin"])
    if precision == "binario":
        return topk_scores(-H.astype(np.float32), k)
    cand = topk_scores(-H.astype(np.float32), min(k * over, H.shape[1]))
    out = np.empty((len(Q), k), dtype=np.int64)
    for i in range(len(Q)):
        v = descuantiza_int8(store["int8"][cand[i]], store["lo"], store["hi"])
        out[i] = cand[i][np.argsort(-(v @ Q[i]))[:k]]
    return out
''')
    nb.code(r'''
# ── TODO 6: la rejilla ──
def evalua_rejilla(banco):
    filas = []
    for nombre, c in banco.items():
        Eq, Ed = c["Eq"], c["Ed"]
        E_big = aumenta(Ed)
        for m in dims_grid(Ed.shape[1]):
            st_small, st_big = construye_store(Ed, m), construye_store(E_big, m)
            ref_m = buscar(Eq, st_big, "float32")                               # top-10 exacto a la misma dimensión m
            for prec in BYTES:
                res = evaluate(run_desde_indices(buscar(Eq, st_small, prec)), QRELS)
                t0 = time.perf_counter(); idx = buscar(Eq, st_big, prec); ms = (time.perf_counter() - t0) / len(Eq) * 1e3
                b = BYTES[prec](m)
                filas.append(dict(modelo=nombre, real=c["real"], dim=m, precision=prec, ndcg10=res["ndcg"], recall10=res["recall"],
                                  overlap10=overlap_at_k(idx, ref_m), bytes_vec=b, MB_10M=b * N_DOCS_PROD / 1e6, ms_query=ms))
    return pd.DataFrame(filas)

# ── TODO 7: Pareto y recomendación ──
def frontera_pareto(df):
    d = df.sort_values(["bytes_vec", "ndcg10"], ascending=[True, False])
    mejor, keep = -1.0, []
    for r in d.itertuples():
        if r.ndcg10 > mejor + 1e-12:
            keep.append(r.Index); mejor = r.ndcg10
    return d.loc[keep]

def recomienda(df, presupuesto_gb=PRESUPUESTO_GB, n_docs=N_DOCS_PROD):
    ok = df[df["bytes_vec"] * n_docs / 1e9 <= presupuesto_gb]
    return ok.sort_values(["ndcg10", "bytes_vec", "ms_query"], ascending=[False, True, True]).iloc[0]

def dibuja_frontera(df, frontera):
    colores = {"float32": "#1F6FEB", "int8": "#2CA02C", "binario": "#F28E2B", "binario+rescore": "#9467BD"}
    fig, ax = plt.subplots(figsize=(8, 4.4))
    for prec, g in df.groupby("precision"):
        ax.scatter(g["bytes_vec"], g["ndcg10"], s=28, alpha=.55, color=colores[prec], label=prec)
    ax.plot(frontera["bytes_vec"], frontera["ndcg10"], "k--", lw=1.4, label="frontera de Pareto")
    ax.axvline(PRESUPUESTO_GB * 1e9 / N_DOCS_PROD, color="#6B7280", ls=":", label=f"presupuesto {PRESUPUESTO_GB} GB / 10 M")
    ax.set_xscale("log", base=2); ax.set_xlabel("bytes por vector en RAM (log)"); ax.set_ylabel("nDCG@10")
    ax.set_title(f"Calidad vs memoria · corpus {CORPUS['source']}"); ax.legend(fontsize=8); ax.grid(alpha=.3)
    plt.tight_layout()

BANCO = construye_banco()
RESULTS = evalua_rejilla(BANCO)
FRONT = frontera_pareto(RESULTS)
REC = recomienda(RESULTS)
dibuja_frontera(RESULTS, FRONT); plt.show()
display(FRONT.round(3))
print("Recomendación:", REC[["modelo", "dim", "precision", "ndcg10", "bytes_vec", "MB_10M"]].to_dict())
''')
    nb.md("> 👀 **Qué debes observar:** compara tu frontera con esta. Si difieren, revisa primero `bytes_vec` (binario = m/8) y que el overlap se mida contra float32 **a la misma dimensión**.")
    nb.code(r'''
_ = autograder()
lat = RESULTS.groupby("precision")[["ms_query", "overlap10"]].mean().round(3)
display(lat)
''')
    nb.md(r'''### Conclusión de referencia (ejemplo)
Con los números de la tabla anterior: `int8` da casi el mismo nDCG@10 que `float32` ocupando 4× menos; la binaria sin rescoring pierde calidad y el rescoring recupera la mayor parte; recortar dimensiones en modelos sin Matryoshka pierde más que recortar bits. Para 10 M de documentos y 20 GB, la configuración recomendada es la de mayor nDCG@10 que cabe (ver `REC`), y debe validarse con el golden set real y con IC antes de producción. Riesgos: licencia del modelo (p. ej. pesos no comerciales), latencia del rescoring en disco, y que el corpus sintético no representa la distribución real.
''')
    # <<END_PROJECT>>
    nb.save(PROJECT)


def readme() -> None:
    texto = """# Módulo 12 · Embedders modernos

**Nivel:** 🟠 Avanzado · **Duración:** ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) · **GPU:** T4 recomendada (CPU en `FAST_DEV_RUN`)

Ya sabes entrenar un embedder (módulo 11). Aquí aprendes qué hay **en el mercado** a oct-2026, cómo funcionan por dentro sus piezas
(pooling last-token y latent attention, prefijos e instrucciones, **Matryoshka**, **cuantización int8 y binaria con rescoring**),
cómo leer MTEB/MMTEB con ojo crítico y cómo **elegir** un embedder con datos de tu propio corpus.

## Contenido
| Notebook | Qué hay dentro |
|---|---|
| [`12_embedders_modernos.ipynb`](12_embedders_modernos.ipynb) | Lección: las tres olas de embedders · pooling desde cero (CLS/mean/max/last-token/latent attention) · LLM2Vec y NV-Embed · prefijos e instrucciones (E5, Qwen3, EmbeddingGemma, Nomic) · pérdida **Matryoshka** y experimento de juguete · truncado + renormalización vs PCA · **int8 y binaria desde cero** + rescoring · comparación de modelos con `sentence-transformers` · bootstrap pareado · MTEB/MMTEB y sus límites · árbol de decisión · 🏭 producción · 🧠 secretos · autoevaluación |
| [`12_proyecto_embedders_modernos.ipynb`](12_proyecto_embedders_modernos.ipynb) | Proyecto: comparativa de 4–6 embedders × escalas Matryoshka × 4 precisiones en Políglota; frontera de Pareto (calidad vs memoria vs latencia) y recomendación para 10 M de documentos en 20 GB. Plantilla con TODOs, pistas 🪜, autocomprobación de la rúbrica y solución tras ⛔ SPOILER |

## Objetivos
1. Explicar la receta de un embedder moderno y la diferencia entre encoder y decoder-as-embedder.
2. Implementar los pooling y el bug del *padding side* en last-token.
3. Aplicar prefijos/instrucciones y medir su efecto.
4. Derivar e implementar Matryoshka (truncar + renormalizar) y saber cuándo falla.
5. Implementar cuantización int8 y binaria + rescoring, y compararla con `sentence-transformers`.
6. Comparar embedders con intervalos de confianza y decidir con un árbol de decisión.

## Datasets
Corpus Políglota vía `carga_corpus()` (cadena oficial → espejo → sintético): Wikipedia ES/EN y CodeSearchNet si hay acceso (o el espejo de la API de Wikipedia); si no, el
corpus sintético del módulo 00 (texto ES/EN de plantillas + código de la stdlib) con el mismo esquema. Los modelos se descargan de Hugging Face; sin red se usa un fallback TF-IDF+SVD
(el notebook avisa con `⚠️`).

## Lecturas clave (verificadas)
- Kusupati et al. (2022), *Matryoshka Representation Learning* (arXiv 2205.13147).
- Wang et al. (2024), *Multilingual E5 Text Embeddings* (2402.05672) · Chen et al. (2024), *M3-Embedding / BGE-M3* (2402.03216).
- Lee et al. (2024), *NV-Embed* (2405.17428) · BehnamGhader et al. (2024), *LLM2Vec* (2404.05961).
- Zhang et al. (2025), *Qwen3 Embedding* (2506.05176) · Vera et al. (2025), *EmbeddingGemma* (2509.20354) · Lee et al. (2025), *Gemini Embedding* (2503.07891).
- Muennighoff et al. (2022), *MTEB* (2210.07316) · Enevoldsen et al. (2025), *MMTEB* (2502.13595).
- Shakir, Aarsen, Lee (2024), *Binary and Scalar Embedding Quantization* (blog de Hugging Face).

## Conexión con Políglota
El embedder y la configuración (dimensión, precisión) que elijas aquí serán el **retriever denso** del módulo 13 y fijarán el tamaño del índice del módulo 14.

*Los notebooks se generan con `python tokenization-embeddings-course/_tools/builders/build_12.py` (desde la raíz del repo). Estado del arte a octubre de 2026: re-verifica IDs de modelos y cifras antes de usarlas.*
"""
    with open(f"{MOD}/README.md", "w", encoding="utf-8") as f:
        f.write(texto)
    print(f"OK {MOD}/README.md")


if __name__ == "__main__":
    lesson()
    project()
    readme()
