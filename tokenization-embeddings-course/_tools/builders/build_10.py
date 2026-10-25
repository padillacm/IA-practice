
"""Builder del módulo 10 · Embeddings contextuales y de oraciones  (autor A4).

Uso (desde la raíz del repo):  python tokenization-embeddings-course/_tools/builders/build_10.py
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "_tools"))
sys.path.insert(0, str(ROOT / "_tools" / "builders"))
from nbbuild import Notebook                                   # noqa: E402
from poliglota_utils import SRC_BM25, SRC_METRICS, src_corpus_cells      # noqa: E402

MOD = "10_embeddings_contextuales_oraciones"
LESSON = f"tokenization-embeddings-course/{MOD}/10_embeddings_contextuales_oraciones.ipynb"
PROJECT = f"tokenization-embeddings-course/{MOD}/10_proyecto_embeddings_contextuales_oraciones.ipynb"



SETUP10 = r'''
!pip install -q transformers sentence-transformers tokenizers datasets scipy scikit-learn matplotlib
import copy, json, math, os, random, re, time, warnings
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
from collections import Counter
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn.functional as F

warnings.filterwarnings("ignore")
import transformers
transformers.logging.set_verbosity_error(); transformers.utils.logging.disable_progress_bar()
SEED = 42
random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
device = "cuda" if torch.cuda.is_available() else "cpu"
FAST_DEV_RUN = True   # True: corpus pequeño y modelos diminutos de fallback en minutos de CPU
PAL = {"azul": "#1F6FEB", "naranja": "#F28E2B", "verde": "#2CA02C", "gris": "#6B7280", "morado": "#9467BD"}
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.25,
                     "axes.spines.top": False, "axes.spines.right": False})
print(f"device={device} · FAST_DEV_RUN={FAST_DEV_RUN} · torch {torch.__version__}")
'''

CORPUS10 = r'''
corpus = carga_corpus(FAST_DEV_RUN)
docs, queries, qrels = corpus["docs"], corpus["queries"], corpus["qrels"]
doc_ids = [d["id"] for d in docs]
doc_txt = [d["text"] for d in docs]
q_txt = [q["text"] for q in queries]
print("fuente:", corpus["source"], "| docs:", dict(Counter(d["lang"] for d in docs)), "| queries:", dict(Counter(q["lang"] for q in queries)))


def evalua(S, k=10):
    """S: (n_queries, n_docs) similitudes -> métricas canónicas @k sobre todas las queries."""
    run = {q["qid"]: rank_from_scores(S[i], doc_ids, 100) for i, q in enumerate(queries)}
    return evaluate(run, qrels, k)
'''

FALLBACK10 = r'''
# ── Fallback documentado: si no hay acceso al hub, construimos dos encoders diminutos LOCALES con la API de HF ──
#    mini-BERT "crudo" (solo MLM, como un BERT sin ajustar) y mini-SBERT (el mismo + 200 pasos contrastivos con
#    pares débiles frase-1 ↔ resto-del-documento; el módulo 11 explica este entrenamiento paso a paso).
from tokenizers import BertWordPieceTokenizer
from transformers import BertConfig, BertForMaskedLM, BertModel, BertTokenizerFast, DataCollatorForLanguageModeling


def construye_fallback(textos, out="mini_encoders", steps_mlm=200, steps_cl=200, seed=SEED):
    os.makedirs(f"{out}/raw", exist_ok=True)
    wp = BertWordPieceTokenizer(lowercase=True, strip_accents=False)
    wp.train_from_iterator(textos, vocab_size=2000, min_frequency=2)
    wp.save_model(f"{out}/raw")
    tk = BertTokenizerFast(f"{out}/raw/vocab.txt", do_lower_case=True, strip_accents=False)
    torch.manual_seed(seed); rng = random.Random(seed)
    mlm = BertForMaskedLM(BertConfig(vocab_size=len(tk), hidden_size=128, num_hidden_layers=2, num_attention_heads=4,
                                     intermediate_size=256, max_position_embeddings=128))
    coll = DataCollatorForLanguageModeling(tk, mlm_probability=0.15)
    feats = [{"input_ids": x} for x in tk(textos, truncation=True, max_length=64)["input_ids"]]
    opt = torch.optim.AdamW(mlm.parameters(), lr=1e-3)
    for _ in range(steps_mlm):
        loss = mlm(**coll([feats[rng.randrange(len(feats))] for _ in range(32)])).loss
        opt.zero_grad(); loss.backward(); opt.step()
    mlm.bert.save_pretrained(f"{out}/raw"); tk.save_pretrained(f"{out}/raw")
    # pares débiles (sin etiquetas): primera frase <-> resto del documento
    pares = []
    for t in textos:
        fr = re.split(r"(?<=[.!?])\s+", t.strip())
        if len(fr) >= 3:
            pares.append((fr[0], " ".join(fr[1:])))
    enc = copy.deepcopy(mlm.bert); opt = torch.optim.AdamW(enc.parameters(), lr=5e-4)
    def emb(b):  # media con máscara (autocontenida para no depender de otras celdas)
        m = b["attention_mask"].unsqueeze(-1).float()
        return F.normalize((enc(**b).last_hidden_state * m).sum(1) / m.sum(1), dim=-1)
    for _ in range(steps_cl):
        lote = rng.sample(pares, 32)
        a = tk([p[0] for p in lote], padding=True, truncation=True, max_length=64, return_tensors="pt")
        b = tk([p[1] for p in lote], padding=True, truncation=True, max_length=64, return_tensors="pt")
        loss = F.cross_entropy(emb(a) @ emb(b).T / 0.05, torch.arange(len(lote)))
        opt.zero_grad(); loss.backward(); opt.step()
    enc.save_pretrained(f"{out}/sbert"); tk.save_pretrained(f"{out}/sbert")
    return f"{out}/raw", f"{out}/sbert"
'''

POOLING = r'''
# ── Pooling desde cero: de (B, T, d) estados por token + máscara (B, T) a (B, d) un vector por texto ──
def media_mascara(h, mask):
    m = mask.unsqueeze(-1).to(h.dtype)
    return (h * m).sum(1) / m.sum(1).clamp(min=1e-9)


def max_mascara(h, mask):
    return h.masked_fill(mask.unsqueeze(-1) == 0, torch.finfo(h.dtype).min).max(1).values


def cls_pool(h, mask):
    return h[:, 0]


def ultimo_token(h, mask):
    """Último token REAL de cada fila (sirve con padding a la derecha o a la izquierda)."""
    T = mask.shape[1]
    idx = T - 1 - mask.flip(1).float().argmax(1)          # posición del último 1 de cada fila
    return h[torch.arange(h.shape[0]), idx]


POOLS = {"cls": cls_pool, "mean": media_mascara, "max": max_mascara, "last": ultimo_token}
'''

ENCODER = r'''
from transformers import AutoModel, AutoTokenizer


class Encoder:
    """Envuelve cualquier encoder de HF: estados por token de cualquier capa + pooling elegido. prefijos = (query, doc)."""

    def __init__(self, nombre, ruta, prefijos=("", ""), max_len=128):
        self.nombre, self.ruta, self.prefijos, self.max_len = nombre, ruta, prefijos, max_len
        self.tok = AutoTokenizer.from_pretrained(ruta)
        self.model = AutoModel.from_pretrained(ruta).to(device).eval()

    @torch.no_grad()
    def estados(self, textos, capa=-1, bs=32):
        """Lista de (h (b,T,d) en CPU, mask (b,T)) por lotes."""
        out = []
        for i in range(0, len(textos), bs):
            b = self.tok(textos[i:i + bs], padding=True, truncation=True, max_length=self.max_len, return_tensors="pt").to(device)
            hs = self.model(**b, output_hidden_states=True).hidden_states
            out.append((hs[capa].float().cpu(), b["attention_mask"].cpu()))
        return out

    def encode(self, textos, pooling="mean", capa=-1, tipo="doc"):
        pre = self.prefijos[0] if tipo == "query" else self.prefijos[1]
        return torch.cat([POOLS[pooling](h, m) for h, m in self.estados([pre + t for t in textos], capa)]).numpy()


def carga_encoders(textos):
    """Modelos reales (si hay hub) o los mini-encoders de fallback. Devuelve {nombre: Encoder}."""
    reales = [("BERT multilingüe crudo", "distilbert-base-multilingual-cased", ("", "")),
              ("SBERT multilingüe", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", ("", "")),
              ("E5 multilingüe small", "intfloat/multilingual-e5-small", ("query: ", "passage: "))]
    encs = {}
    for nombre, ruta, pre in reales:
        try:
            encs[nombre] = Encoder(nombre, ruta, pre)
        except Exception as e:
            print(f"   (sin {ruta}: {type(e).__name__})")
    if not encs:
        print("⚠️  Sin acceso al hub: construyo los mini-encoders de fallback (~1-2 min en CPU)")
        raw, sb = construye_fallback(textos)
        encs = {"mini-BERT crudo (fallback)": Encoder("mini-BERT crudo (fallback)", raw),
                "mini-SBERT (fallback)": Encoder("mini-SBERT (fallback)", sb)}
    return encs
'''

WHITEN = r'''
# ── Post-procesado desde cero: centrado, whitening (Su et al., 2021) y "all-but-the-top" (Mu & Viswanath, 2018) ──
def ajusta_whitening(X, k=None, eps=1e-6):
    """Devuelve (mu, W) tales que (x - mu) @ W tiene covarianza identidad en las k primeras direcciones."""
    mu = X.mean(0, keepdims=True)
    cov = np.cov((X - mu).T)
    U, S, _ = np.linalg.svd(cov)
    k = k or X.shape[1]
    return mu, U[:, :k] / np.sqrt(S[:k] + eps)


def quita_top(X, mu, n_top=1):
    """All-but-the-top: centra y elimina las n_top direcciones principales."""
    Xc = X - mu
    U, _, _ = np.linalg.svd(np.cov(Xc.T))
    P = U[:, :n_top]
    return Xc - Xc @ P @ P.T


def coseno(Q, D):
    Qn = Q / np.linalg.norm(Q, axis=1, keepdims=True).clip(1e-12)
    Dn = D / np.linalg.norm(D, axis=1, keepdims=True).clip(1e-12)
    return Qn @ Dn.T


def anisotropia(X, n=3000, seed=SEED):
    r = np.random.RandomState(seed)
    i, j = r.randint(0, len(X), n), r.randint(0, len(X), n)
    Xn = X / np.linalg.norm(X, axis=1, keepdims=True).clip(1e-12)
    keep = i != j
    return float((Xn[i[keep]] * Xn[j[keep]]).sum(1).mean())
'''
nb = Notebook("Módulo 10 · Embeddings contextuales y de oraciones", colab_path=LESSON)
nb.md(nb.badge() + r"""
# Módulo 10 · Embeddings contextuales y de oraciones

| | |
|---|---|
| **Nivel** | 🟡 Intermedio |
| **Duración** | ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) |
| **Cómputo** | CPU basta en `FAST_DEV_RUN` (≈ 5 min); con modelos reales, T4 recomendada (≈ 0.5 h de T4: multiplica por la tarifa de unidades/hora que muestra tu panel de recursos de Colab) |
| **Prerrequisitos** | 09 (capa de embedding, anisotropía de $E$), atención y Transformers |
| **Hilo conductor** | Políglota necesita **un vector por documento y por consulta**. Hoy aprendes a sacarlo de un encoder preentrenado y a medir cuál funciona en nuestro corpus |

> **Dónde estamos.** En el 09 cada token tenía **un** vector fijo (fila de $E$). Un Transformer produce un vector por token **en contexto** (capa $\ell$), y para buscar necesitamos comprimir la secuencia en **un** vector: *pooling*. Este módulo compara cómo hacerlo, por qué los vectores «crudos» de BERT funcionan mal para similitud (anisotropía) y cómo se arregla sin entrenar (centrado, *whitening*). Entrenar el encoder para similitud es el módulo 11.
""")

nb.md(r"""
## Objetivos de aprendizaje
1. **Distinguir** embeddings estáticos (fila de $E$) de contextuales (estado oculto de la capa $\ell$) y **medir** la contextualidad por capa (*self-similarity*, Ethayarajh 2019).
2. **Implementar desde cero** pooling CLS, media, máximo y último token con máscaras correctas, y **verificarlo** contra `sentence-transformers`.
3. **Explicar** la arquitectura bi-encoder (SBERT) frente a cross-encoder y su coste.
4. **Cuantificar** la anisotropía y las dimensiones dominantes (*rogue dimensions*) de un encoder.
5. **Aplicar** centrado, *whitening* (Su et al., 2021) y *all-but-the-top*, y **evaluar** su efecto en nDCG@10 sobre Políglota.
6. **Elegir** entre coseno, producto escalar y L2 sabiendo cuándo son equivalentes.
7. **Usar** prefijos/instrucciones (E5: `query:`/`passage:`) y justificar por qué existen.
""")

nb.md(r"""
## 🔁 Conexión con módulos anteriores
<details><summary><b>1.</b> (09) ¿Por qué no sirve usar directamente filas de $E$ promediadas como embedding de una frase?</summary>

Porque $E$ es una tabla *sin contexto* («banco» tiene un solo vector) y además es **anisótropa**: una media común grande domina el coseno. El promedio hereda ambas cosas.
</details>

<details><summary><b>2.</b> (09) En la lección anterior, el coseno medio entre pares aleatorios de filas bajaba a ≈ 0 al **centrar**. ¿Qué conclusión geométrica sacaste?</summary>

Que la anisotropía venía de una **dirección media compartida**: restarla devuelve vectores repartidos alrededor del origen. Hoy aplicamos lo mismo (y más: *whitening*) a embeddings de frases.
</details>

<details><summary><b>3.</b> (00) ¿Qué mide nDCG@10 y por qué lo usamos en Políglota?</summary>

La calidad del top-10 con descuento logarítmico por posición, normalizada por el ranking ideal. Es la métrica estándar de BEIR/MTEB y la del baseline BM25 del módulo 00.
</details>
""")

nb.code(SETUP10)
nb.md("### Utilidades del curso: corpus Políglota y métricas canónicas (módulo 00)")
for _src in src_corpus_cells():
    nb.code(_src)
nb.code(SRC_METRICS)
nb.code(SRC_BM25)
nb.code(CORPUS10)

nb.md(r"""
## 1. Intuición: de un vector por token a un vector por frase

En un Transformer, el vector de un token en la capa $\ell$ es $\mathbf h^{(\ell)}_i = f_\ell(\mathbf x_1,\dots,\mathbf x_T)_i$: depende de **toda** la frase. «banco» en *«me senté en el banco del parque»* y en *«el banco subió los tipos»* entra con la misma fila de $E$ (capa 0) y sale con vectores distintos en las capas altas.
**BERT** (Devlin et al., 2019) es un encoder bidireccional preentrenado con *masked language modeling*; su token especial `[CLS]` se pensó como resumen para clasificación.

Para buscar documentos necesitamos un **único** vector por texto: $\mathbf s = \text{pool}(\mathbf h_1,\dots,\mathbf h_T)$. La pregunta del módulo es **qué pooling y qué post-procesado** hacen que $\cos(\mathbf s_q,\mathbf s_d)$ refleje relevancia.

> 💡 **Analogía con recsys.** En un *two-tower* (`recsys-course/08_deep_retrieval_ann`) cada torre convierte un usuario/ítem con muchas *features* en un vector y el score es un producto escalar. Un **bi-encoder** de texto es lo mismo: la torre es un Transformer + pooling, y el «ítem» es un documento. Todo lo que sabes de *two-tower* (indexabilidad del producto escalar, sesgo por normas, ANN) aplica aquí.
""")

nb.gemini(
    "imagen", "M10-IMG-01", "Estático vs contextual: la palabra «banco»",
    "Contrasta un embedding estático (una fila de E, igual en cualquier frase) con los embeddings contextuales de la última capa, que separan los dos sentidos de «banco».",
    """
    Diagrama técnico limpio, fondo blanco, 16:9, sin decoración. Paleta: azul #1F6FEB (sentido «asiento»), naranja #F28E2B (sentido «entidad financiera»), gris #6B7280 (elementos neutros), verde #2CA02C (flechas de contexto). Tipografía sans-serif.
    Mitad izquierda, título «Embedding estático (fila de E)»: dos frases en cajas grises: «Me senté en el banco del parque» y «El banco subió los tipos de interés». De la palabra «banco» de ambas frases salen flechas grises hacia UN ÚNICO punto gris en un plano 2D rotulado «E[banco]» con la nota «mismo vector en las dos frases».
    Mitad derecha, título «Embedding contextual (capa final del Transformer)»: las mismas dos frases; flechas verdes desde las palabras vecinas («parque», «senté» / «tipos», «interés») hacia «banco» indicando atención. En un plano 2D, un punto azul rotulado «banco (asiento)» cerca de puntos azules pequeños «silla», «parque», y un punto naranja «banco (entidad)» cerca de puntos naranjas «crédito», «tipos». Línea discontinua entre ambos puntos con el texto «coseno bajo».
    Pie común: «Capa 0 = estático; capas altas = cada vez más dependiente del contexto».
    Evita: texto ilegible, flechas ambiguas, números inventados, iconos decorativos.
    """,
    "Comparación de embedding estático (un punto para «banco») y contextual (dos puntos según el sentido).",
    """
    ESTÁTICO (E):   "banco" (parque) ─┐
                    "banco" (tipos)  ─┴─► • E[banco]   (mismo vector)
    CONTEXTUAL:     "banco" (parque) ─► • cerca de {silla, parque}
                    "banco" (tipos)  ─► • cerca de {crédito, tipos}   (coseno bajo)
    """,
)
nb.md(r"""
> 👀 **Qué debes observar.** La diferencia no es «más dimensiones», sino que el vector **depende de los vecinos** vía atención. Por eso el embedding de una frase puede capturar el sentido, cosa imposible promediando filas de $E$.
""")

nb.md(r"""
## 2. Pooling desde cero
Dados los estados $H\in\mathbb R^{B\times T\times d}$ de un lote y la máscara $M\in\{0,1\}^{B\times T}$ (1 = token real, 0 = *padding*):

| Pooling | Fórmula | Típico en |
|---|---|---|
| CLS | $\mathbf s=\mathbf h_1$ | BERT original, DPR |
| media | $\mathbf s=\dfrac{\sum_i M_i\mathbf h_i}{\sum_i M_i}$ | SBERT (por defecto), E5 |
| máximo | $s_k=\max_{i:M_i=1} h_{ik}$ | variante de SBERT |
| último token | $\mathbf s=\mathbf h_{i^*}$, $i^*$ = último token real | LLMs decoder (SGPT, e5-mistral; módulo 12) |

La máscara **no es opcional**: sin ella, el padding cambia el embedding de un texto según con quién compartió lote.
""")
nb.code(POOLING)
nb.code(r'''
# El padding importa: la media SIN máscara depende del lote; con máscara, no.
torch.manual_seed(SEED)
h = torch.randn(2, 6, 4)
mask = torch.tensor([[1, 1, 1, 1, 1, 1], [1, 1, 1, 0, 0, 0]])         # el 2.º texto tiene 3 tokens + 3 de padding
solo = media_mascara(h[1:, :3], torch.ones(1, 3, dtype=torch.long))    # el mismo texto codificado solo, sin padding
print("media CON máscara == texto solo:", torch.allclose(media_mascara(h, mask)[1], solo[0]))
print("media SIN máscara == texto solo:", torch.allclose(h.mean(1)[1], solo[0]))
print("último token real por fila:", (mask.shape[1] - 1 - mask.flip(1).float().argmax(1)).tolist(), "(padding a la derecha)")
mask_izq = torch.tensor([[1, 1, 1, 1, 1, 1], [0, 0, 0, 1, 1, 1]])
print("último token real con padding a la izquierda:", (mask_izq.shape[1] - 1 - mask_izq.flip(1).float().argmax(1)).tolist())
''')
nb.md(r"""
> 👀 **Qué debes observar.** `True` con máscara y `False` sin ella: un bug de pooling sin máscara hace que **el mismo documento tenga embeddings distintos** según el lote (y el índice no es reproducible). `ultimo_token` funciona con padding a la izquierda o a la derecha; `h[:, -1]` solo con padding a la izquierda (error clásico con LLMs-embedders, módulo 12).
""")

nb.md(r"""
## 3. Encoders: reales y *fallback*
La celda carga tres encoders multilingües reales del hub (si hay acceso):
- **BERT multilingüe crudo** (`distilbert-base-multilingual-cased`): preentrenado solo con MLM, **sin** ajustar para similitud.
- **SBERT multilingüe** (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`): bi-encoder ajustado para similitud y multilingüe por destilación (Reimers & Gurevych, 2020).
- **E5 multilingüe small** (`intfloat/multilingual-e5-small`): entrenado contrastivamente con prefijos `query:` / `passage:` (Wang et al., 2022).

Sin acceso al hub se construyen dos encoders diminutos **locales** con la misma API (fallback documentado): un mini-BERT solo-MLM («crudo») y su versión con 200 pasos de ajuste contrastivo con pares débiles («mini-SBERT»). Los números con el fallback **no** son comparables con los de los modelos reales; los mecanismos sí.
""")
nb.code(FALLBACK10)
nb.code(ENCODER)
nb.md("Utilidades de similitud y post-procesado (`coseno`, `anisotropia`, whitening). Las explicamos en la sección 6; aquí solo las definimos.")
nb.code(WHITEN)
nb.code(r'''
t0 = time.time()
encs = carga_encoders(doc_txt)
print("encoders:", list(encs), f"({time.time() - t0:.0f}s)")
''')

nb.md(r"""
## 4. ¿Cuán contextuales son las representaciones? (por capa)
Ethayarajh (2019) define la **self-similarity** de una palabra en la capa $\ell$ como el coseno medio entre sus representaciones en contextos distintos, y la compara con la **anisotropía** de esa capa (coseno medio entre tokens aleatorios). Si ambas son altas, la palabra *parece* estable solo porque *todo* es parecido; la medida útil es la diferencia.
""")
nb.code(r'''
def contextualidad(enc, textos, max_docs=60):
    """Por capa: (self-similarity del token más frecuente de ≥ 5 letras, anisotropía entre tokens aleatorios)."""
    ids_txt = enc.tok(textos, truncation=True, max_length=enc.max_len)["input_ids"]
    cnt = Counter(i for ids in ids_txt for i in set(ids))
    vocab_inv = {v: k for k, v in enc.tok.get_vocab().items()}
    cand = [i for i, n in cnt.most_common() if re.fullmatch(r"[^\W\d_]{5,}", vocab_inv[i].lstrip("▁Ġ#"))]
    wid = cand[0]
    con = [t for t, ids in zip(textos, ids_txt) if wid in ids][:max_docs]
    b = enc.tok(con, padding=True, truncation=True, max_length=enc.max_len, return_tensors="pt").to(device)
    with torch.no_grad():
        hs = enc.model(**b, output_hidden_states=True).hidden_states
    pos = (b["input_ids"] == wid) & (b["attention_mask"] == 1)
    res_ = []
    for h in hs:
        h = h.float().cpu()
        w = F.normalize(h[pos.cpu()], dim=-1)
        ss = (w @ w.T)[~torch.eye(len(w), dtype=bool)].mean().item()
        toks = h[b["attention_mask"].cpu() == 1]
        res_.append((ss, anisotropia(toks.numpy())))
    return vocab_inv[wid], np.array(res_)


fig, ax = plt.subplots(1, len(encs), figsize=(5.2 * len(encs), 3.4), squeeze=False)
for a, (n, e) in zip(ax[0], encs.items()):
    palabra, r_ = contextualidad(e, doc_txt)
    capas = np.arange(len(r_))
    a.plot(capas, r_[:, 0], "o-", color=PAL["azul"], label=f"self-similarity «{palabra}»")
    a.plot(capas, r_[:, 1], "s--", color=PAL["naranja"], label="anisotropía (tokens aleatorios)")
    a.plot(capas, r_[:, 0] - r_[:, 1], "^-", color=PAL["verde"], label="self-sim − anisotropía")
    a.set(xlabel="capa (0 = embeddings de entrada)", ylabel="coseno medio", title=n); a.legend(fontsize=7)
plt.tight_layout(); plt.show()
''')
nb.md(r"""
> 👀 **Qué debes observar.** En la capa 0 la *self-similarity* es 1 (es la misma fila de $E$, salvo la suma de posiciones) y cae al subir: las capas altas son **más contextuales**. La anisotropía (naranja) no es cero en ninguna capa: Ethayarajh (2019) la midió alta en las capas superiores de BERT y GPT-2, y Godey et al. (2024) argumentan que es en buena parte inherente a la auto-atención. La curva verde es la contextualidad «real».
""")

nb.md(r"""
## 5. Pooling × modelo en Políglota
Codificamos documentos y consultas con cada pooling y medimos nDCG@10 con coseno. Recuerda la referencia: **BM25** del módulo 00 en este corpus.
""")
nb.gemini(
    "imagen", "M10-IMG-02", "Cuatro formas de resumir una secuencia (pooling)",
    "Muestra sobre la misma matriz de estados ocultos qué posiciones usa cada pooling (CLS, media, máximo, último token) y el papel de la máscara de padding.",
    """
    Diagrama técnico limpio, fondo blanco, 16:9. Paleta: azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280; tipografía sans-serif.
    Arriba: una frase tokenizada en 8 fichas: «[CLS]», «cómo», «configurar», «la», «caché», «[SEP]», «[PAD]», «[PAD]». Las dos fichas [PAD] en gris claro con la etiqueta «máscara = 0».
    Debajo, una cuadrícula de 8 columnas × 6 filas (estados ocultos h₁…h₈ de dimensión d), con las columnas [PAD] sombreadas en gris y tachadas.
    Debajo, cuatro paneles en fila, cada uno con una flecha desde la cuadrícula a un vector de 6 casillas:
    1) «CLS»: solo la columna 1 resaltada en azul.
    2) «media (con máscara)»: columnas 1–6 resaltadas en verde y la fórmula «Σ mᵢ hᵢ / Σ mᵢ».
    3) «máximo»: casillas sueltas resaltadas en naranja en distintas columnas (el máximo por dimensión), nunca en [PAD].
    4) «último token real»: solo la columna 6 ([SEP]) resaltada en azul oscuro con la nota «no la columna 8».
    Pie: «El pooling debe coincidir con el que se usó al entrenar el modelo».
    Evita: texto ilegible, flechas ambiguas, números inventados, decoración.
    """,
    "Cuatro paneles que muestran qué estados ocultos usa cada pooling y que el padding se excluye con la máscara.",
    """
    tokens: [CLS] cómo configurar la caché [SEP] [PAD] [PAD]
    máscara:  1    1      1       1    1     1     0     0
    CLS   -> h1           media -> Σ m_i h_i / Σ m_i (h1..h6)
    max   -> max por dim (sin PAD)   último -> h6 (último real, no h8)
    """,
)
nb.md(r"""
> 👀 **Qué debes observar.** Cada pooling es una decisión de **entrenamiento**, no solo de inferencia: un modelo entrenado con media espera media. La máscara aparece en tres de los cuatro paneles.
""")
nb.code(r'''
bm25 = BM25().fit([tokenize_simple(t) for t in doc_txt], doc_ids)          # BM25 canónico del módulo 00
S_bm25 = np.array([bm25.scores(tokenize_simple(q)) for q in q_txt])
ndcg_bm25 = evalua(S_bm25)["ndcg"]

tabla = {}
for n, e in encs.items():
    for p in POOLS:
        D, Q = e.encode(doc_txt, p, tipo="doc"), e.encode(q_txt, p, tipo="query")
        tabla[(n, p)] = evalua(coseno(Q, D))["ndcg"]
fig, ax = plt.subplots(figsize=(8.5, 3.6))
x = np.arange(len(POOLS)); w = 0.8 / len(encs)
for k, (n, col) in enumerate(zip(encs, [PAL["gris"], PAL["azul"], PAL["verde"]])):
    vals = [tabla[(n, p)] for p in POOLS]
    ax.bar(x + k * w - 0.4 + w / 2, vals, w, color=col, label=n)
ax.axhline(ndcg_bm25, ls="--", color=PAL["naranja"], label=f"BM25 (módulo 00) = {ndcg_bm25:.3f}")
ax.set_xticks(x, list(POOLS)); ax.set(ylabel="nDCG@10", title="Pooling × encoder en Políglota (coseno)"); ax.legend(fontsize=7)
plt.tight_layout(); plt.show()
for (n, p), v in tabla.items():
    print(f"{n:30s} {p:5s} nDCG@10={v:.3f}")
''')
nb.md(r"""
> 👀 **Qué debes observar.** (1) El encoder **crudo** (solo MLM) es el peor con cualquier pooling: preentrenar para predecir palabras no basta para que el coseno mida relevancia. SBERT lo documentó: con BERT sin ajustar, el promedio de STS fue 54.81 (media) y 29.19 (CLS), por debajo de promediar GloVe (61.32) (Reimers & Gurevych, 2019, tabla 1).
> (2) El pooling que mejor funciona es, casi siempre, **el que se usó al entrenar** (media para SBERT/E5). (3) En este corpus de «ítem conocido», BM25 es un rival durísimo: las consultas comparten palabras exactas con su documento. En el fallback los mini-encoders quedan muy por debajo; con los modelos reales, compara tú mismo.
""")

nb.code(r'''
# Librería de industria: sentence-transformers con módulos Transformer + Pooling. ¿Da lo mismo que nuestro pooling?
try:
    from sentence_transformers import SentenceTransformer
    from sentence_transformers.models import Pooling, Transformer
    e = next(iter(encs.values()))
    tr = Transformer(e.ruta, max_seq_length=e.max_len)
    st = SentenceTransformer(modules=[tr, Pooling(tr.get_word_embedding_dimension(), pooling_mode="mean")], device=device)
    ref = st.encode(doc_txt[:16], convert_to_numpy=True, batch_size=8)
    mio = e.encode(doc_txt[:16], "mean")
    print(f"{e.nombre}: max |ST − nuestro mean pooling| = {np.abs(ref - mio).max():.2e}")
except Exception as ex:
    print("sentence-transformers no disponible:", type(ex).__name__, ex)
''')
nb.md(r"""
> 👀 **Qué debes observar.** Diferencia del orden de $10^{-6}$ o menor: `sentence-transformers` hace exactamente la media con máscara. En producción usarás la librería (gestiona lotes, *truncation*, normalización y configuración guardada con el modelo); implementarlo una vez te permite **auditar** que el pooling del modelo coincide con el de tu índice.
""")

nb.md(r"""
## 6. Anisotropía, dimensiones dominantes y cómo corregirlas sin entrenar

**Anisotropía.** Si todos los embeddings comparten una dirección grande, $\cos(\mathbf s_a,\mathbf s_b)$ es alto para *cualquier* par y el ranking lo deciden diferencias pequeñas. Además, unas pocas **dimensiones dominantes** (*rogue dimensions*, Timkey & van Schijndel, 2021) pueden concentrar casi todo el coseno.
La contribución de la dimensión $k$ al coseno medio entre pares es $\;c_k=\mathbb E\big[\tfrac{u_k v_k}{\|\mathbf u\|\|\mathbf v\|}\big]$, con $\sum_k c_k$ = coseno medio.
""")
nb.code(r'''
def contribucion_dims(X, n=3000, seed=SEED):
    r = np.random.RandomState(seed)
    i, j = r.randint(0, len(X), n), r.randint(0, len(X), n)
    Xn = X / np.linalg.norm(X, axis=1, keepdims=True).clip(1e-12)
    return (Xn[i] * Xn[j]).mean(0)                        # vector (d,) que suma el coseno medio


fig, ax = plt.subplots(1, len(encs), figsize=(5.2 * len(encs), 3.2), squeeze=False)
EMB = {}
for a, (n, e) in zip(ax[0], encs.items()):
    D, Q = e.encode(doc_txt, "mean"), e.encode(q_txt, "mean", tipo="query")
    EMB[n] = (D, Q)
    c = contribucion_dims(D)
    top = np.argsort(-np.abs(c))[:3]
    a.bar(np.arange(len(c)), c, color=PAL["gris"])
    a.bar(top, c[top], color=PAL["naranja"])
    a.set(xlabel="dimensión", ylabel="contribución al coseno medio",
          title=f"{n}\ncos medio={c.sum():.2f} · top-3 dims={c[top].sum() / c.sum():.0%}")
plt.tight_layout(); plt.show()
''')
nb.md(r"""
> 👀 **Qué debes observar.** La suma de barras es el coseno medio entre documentos aleatorios (la anisotropía). Si 3 dimensiones naranjas explican una fracción grande, el coseno está dominado por ellas: es lo que Timkey & van Schijndel (2021) llaman *rogue dimensions*, y por eso el centrado o la estandarización por dimensión pueden cambiar mucho el ranking.
""")

nb.md(r"""
### 📐 Whitening, paso a paso (Su et al., 2021)
Queremos una transformación lineal $\tilde{\mathbf x}=(\mathbf x-\boldsymbol\mu)W$ tal que los vectores transformados tengan **media 0 y covarianza identidad** (isótropos):
1. $\boldsymbol\mu=\frac1N\sum_i\mathbf x_i$ y $\Sigma=\frac1N\sum_i(\mathbf x_i-\boldsymbol\mu)^\top(\mathbf x_i-\boldsymbol\mu)$.
2. Descomposición espectral $\Sigma=U\Lambda U^\top$ ($U$ ortogonal, $\Lambda$ diagonal con varianzas $\lambda_1\ge\dots\ge\lambda_d$).
3. $W=U\Lambda^{-1/2}$. Comprobación: $\operatorname{Cov}(\tilde{\mathbf x}) = W^\top\Sigma W=\Lambda^{-1/2}U^\top U\Lambda U^\top U\Lambda^{-1/2}=I$.
4. **Reducción**: quedarse con las $k$ primeras columnas de $W$ (las direcciones de más varianza) reduce dimensión *y* ruido.

**Relación con BERT-flow** (Li et al., 2020): aprende un *normalizing flow* invertible que lleva los embeddings a una gaussiana isótropa; whitening es el caso **lineal** de esa idea y Su et al. reportan resultados comparables o mejores sin entrenar nada. **All-but-the-top** (Mu & Viswanath, 2018) es aún más simple: centrar y quitar las primeras componentes principales.
⚠️ $\boldsymbol\mu$ y $W$ se ajustan **con los documentos del índice** (o un corpus de referencia), nunca con las consultas de evaluación.
""")
nb.code(r'''
ks = [8, 16, 32, 64, 128, 256]
fig, ax = plt.subplots(figsize=(7.5, 3.6))
post = {}
for (n, (D, Q)), col in zip(EMB.items(), [PAL["gris"], PAL["azul"], PAL["verde"]]):
    base = evalua(coseno(Q, D))["ndcg"]
    mu = D.mean(0, keepdims=True)
    cent = evalua(coseno(Q - mu, D - mu))["ndcg"]
    abtt = evalua(coseno(quita_top(Q, mu, 1), quita_top(D, mu, 1)))["ndcg"]
    kk = [k for k in ks if k <= D.shape[1]]
    wh = []
    for k in kk:
        m_, W = ajusta_whitening(D, k)
        wh.append(evalua(coseno((Q - m_) @ W, (D - m_) @ W))["ndcg"])
    post[n] = dict(base=base, centrado=cent, abtt=abtt, whitening=dict(zip(kk, wh)), aniso=anisotropia(D),
                   aniso_w=anisotropia((D - mu) @ ajusta_whitening(D)[1]))
    ax.plot(kk, wh, "o-", color=col, label=f"{n}: whitening-k")
    ax.axhline(base, ls=":", color=col)
ax.set_xscale("log", base=2); ax.set(xlabel="k (dimensiones tras whitening)", ylabel="nDCG@10", title="Whitening con reducción a k dims (punteado: sin post-procesado)")
ax.legend(fontsize=7); plt.tight_layout(); plt.show()
for n, r_ in post.items():
    best_k = max(r_["whitening"], key=r_["whitening"].get)
    print(f"{n:30s} base={r_['base']:.3f} | centrado={r_['centrado']:.3f} | ABTT-1={r_['abtt']:.3f} | whitening mejor k={best_k} (elegido en test: optimista): {r_['whitening'][best_k]:.3f} | anisotropía {r_['aniso']:.2f} → {r_['aniso_w']:.2f}")
''')
nb.md(r"""
> 👀 **Qué debes observar.** (1) Tras el whitening completo la anisotropía cae a ≈ 0 por construcción. (2) Que eso **mejore el retrieval** no está garantizado: el whitening iguala *todas* las direcciones, también las de ruido. Con $k$ pequeño se pierde información; con $k$ grande se amplifica ruido; suele haber un óptimo intermedio, y debe elegirse con un conjunto de validación, no con el test.
> (3) En el *fallback* el efecto **no es estable**: en tres ejecuciones el whitening ($k=64$) llevó el nDCG@10 del mini-SBERT de 0.23 a 0.35, de 0.30 a 0.28 y, en el proyecto, quedó a ±0.02 de la *default* en test; con el mini-BERT crudo nunca ayudó (0.12–0.13 → 0.11–0.13). El entrenamiento diminuto en CPU no es determinista bit a bit (p. ej. el entrenamiento del vocabulario WordPiece), y la lección es justo esa: un post-procesado no crea señal que el encoder no tiene, y su efecto hay que **validarlo**, no suponerlo. Su et al. (2021) reportan mejoras grandes sobre BERT crudo en STS; para encoders bien entrenados contrastivamente la ganancia suele ser pequeña o negativa: mídelo con tus modelos.
""")

nb.gemini(
    "imagen", "M10-IMG-03", "Anisotropía: del cono a la esfera (centrado y whitening)",
    "Visualiza el efecto geométrico de centrar y de blanquear un conjunto de embeddings anisótropos, conectando con la caída del coseno medio.",
    """
    Diagrama técnico limpio, fondo blanco, 16:9, tres paneles de izquierda a derecha con flechas entre ellos. Paleta: azul #1F6FEB para los puntos, naranja #F28E2B para la dirección media, gris #6B7280 para ejes y texto.
    Panel 1, título «Anisótropo»: ejes 2D con el origen marcado; una nube alargada y estrecha de 40 puntos azules lejos del origen, todos dentro de un cono delgado; una flecha naranja gruesa desde el origen hasta el centro de la nube rotulada «μ (dirección media)». Texto bajo el panel: «coseno medio ≈ 0.8».
    Flecha a la derecha con el rótulo «restar μ».
    Panel 2, título «Centrado»: la misma nube, ahora centrada en el origen pero todavía alargada en diagonal (elipse). Texto: «coseno medio ≈ 0, pero varianza desigual».
    Flecha a la derecha con el rótulo «× U Λ^(-1/2)».
    Panel 3, título «Whitening»: nube redonda (círculo) centrada en el origen. Texto: «covarianza = I (isótropo)».
    Franja inferior: «Whitening = (x − μ) · U Λ^(-1/2); con k columnas también reduce dimensión».
    Evita: texto ilegible, flechas ambiguas, añadir números distintos de los indicados, decoración.
    """,
    "Tres paneles: nube anisótropa en un cono con su media, la nube centrada (elipse) y la nube blanqueada (círculo).",
    """
     [cono estrecho lejos del origen] --restar μ--> [elipse centrada] --×UΛ^-1/2--> [círculo centrado]
       cos medio ≈ 0.8                          cos medio ≈ 0               covarianza = I
    """,
)
nb.md(r"""
> 👀 **Qué debes observar.** El centrado arregla el *coseno medio*; el whitening además iguala la varianza por dirección. Son transformaciones lineales que se aplican igual a consultas y documentos y se pueden «hornear» en el índice.
""")

nb.md(r"""
### Idioma como dirección dominante
En un encoder multilingüe, una parte de la varianza codifica **qué idioma** es el texto, no de qué trata. Libovický et al. (2019) mostraron que restar la **media por idioma** hace las representaciones de mBERT más «neutras» respecto al idioma. Lo comprobamos visualmente en Políglota (ES, EN y código).
""")
nb.code(r'''
langs = np.array([d["lang"] for d in docs])
n_sel = list(EMB)[-1]                                  # el encoder ajustado para similitud (último de la lista)
D, Q = EMB[n_sel]
D_lc = D.copy()
for l in np.unique(langs):
    D_lc[langs == l] -= D[langs == l].mean(0)


def pca2(X):
    Xc = X - X.mean(0)
    _, _, Vt = np.linalg.svd(Xc, full_matrices=False)
    return Xc @ Vt[:2].T


fig, ax = plt.subplots(1, 2, figsize=(10.5, 3.8))
for a, X, tit in ((ax[0], D, "original"), (ax[1], D_lc, "tras restar la media de cada idioma")):
    P = pca2(X)
    for l, col in zip(["es", "en", "code"], [PAL["azul"], PAL["naranja"], PAL["verde"]]):
        a.scatter(P[langs == l, 0], P[langs == l, 1], s=8, alpha=.6, color=col, label=l)
    a.set(title=f"{n_sel}: PCA ({tit})", xlabel="PC1", ylabel="PC2"); a.legend()
plt.tight_layout(); plt.show()
print("silhouette por idioma (↑ = idiomas más separados):", end=" ")
from sklearn.metrics import silhouette_score
print(f"original={silhouette_score(D, langs, metric='cosine'):.3f} | centrado por idioma={silhouette_score(D_lc, langs, metric='cosine'):.3f}")
''')
nb.md(r"""
> 👀 **Qué debes observar.** En el panel izquierdo los documentos se agrupan **por idioma** (sobre todo el código frente a la prosa): las primeras componentes principales codifican la lengua. Tras centrar por idioma, el *silhouette* por idioma baja. Para búsqueda **cruzada** (consulta en ES, documento en EN) eso ayuda; para búsqueda monolingüe puede dar igual o empeorar. Ojo: para centrar la consulta necesitas conocer (o detectar) su idioma.
""")

nb.md(r"""
## 7. Coseno, producto escalar y L2
Para vectores $\mathbf q,\mathbf d$: $\;\|\mathbf q-\mathbf d\|^2=\|\mathbf q\|^2+\|\mathbf d\|^2-2\,\mathbf q\cdot\mathbf d$.
- Si **todos** los vectores tienen norma 1: $\|\mathbf q-\mathbf d\|^2 = 2-2\cos(\mathbf q,\mathbf d)$, así que **coseno, producto escalar y L2 dan el mismo ranking**.
- Sin normalizar, para una consulta fija $\|\mathbf q\|$ es constante, pero $\|\mathbf d\|^2$ no: L2 penaliza documentos de norma grande y el producto escalar los **premia**. La norma pasa a ser una *feature* (en recsys suele correlacionar con popularidad; Steck et al., 2024, discuten cuándo el coseno sobre embeddings aprendidos no mide lo que creemos).
- Regla práctica: usa la métrica **con la que se entrenó** el modelo (DPR: producto escalar; SBERT/E5: coseno) y, si normalizas, guarda los vectores normalizados en el índice (módulo 14).
""")
nb.code(r'''
from scipy.stats import kendalltau

D, Q = EMB[n_sel]
metricas = {"coseno": coseno(Q, D), "producto": Q @ D.T, "−L2": -((Q ** 2).sum(1)[:, None] + (D ** 2).sum(1)[None] - 2 * Q @ D.T)}
Dn, Qn = D / np.linalg.norm(D, axis=1, keepdims=True), Q / np.linalg.norm(Q, axis=1, keepdims=True)
metricas["producto (normalizado)"] = Qn @ Dn.T
nombres = list(metricas)
tau = np.zeros((len(nombres), len(nombres)))
for a_, na in enumerate(nombres):
    for b_, nb_ in enumerate(nombres):
        tau[a_, b_] = np.mean([kendalltau(metricas[na][i], metricas[nb_][i]).statistic for i in range(0, len(Q), 3)])
fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
im = ax[0].imshow(tau, vmin=0, vmax=1, cmap="Blues")
ax[0].set_xticks(range(len(nombres)), nombres, rotation=30, ha="right"); ax[0].set_yticks(range(len(nombres)), nombres)
for i in range(len(nombres)):
    for j in range(len(nombres)):
        ax[0].text(j, i, f"{tau[i, j]:.2f}", ha="center", va="center", color="k" if tau[i, j] < .7 else "w")
ax[0].set_title("τ de Kendall medio entre rankings"); plt.colorbar(im, ax=ax[0])
ax[1].hist(np.linalg.norm(D, axis=1), bins=40, color=PAL["gris"]); ax[1].set(xlabel="‖d‖", ylabel="nº de documentos", title="Normas de los documentos")
plt.tight_layout(); plt.show()
for k_, S in metricas.items():
    print(f"{k_:24s} nDCG@10={evalua(S)['ndcg']:.3f}")
''')
nb.md(r"""
> 👀 **Qué debes observar.** «coseno» y «producto (normalizado)» tienen τ = 1.00: son el mismo ranking. Producto escalar y −L2 sin normalizar se separan tanto más cuanto más varían las normas de los documentos (histograma derecho). Si tu modelo no normaliza y las normas varían mucho, la elección de métrica cambia resultados: compruébalo antes de elegir el tipo de índice.
""")

nb.md(r"""
## 8. Prefijos e instrucciones
Un bi-encoder **simétrico** (misma torre, sin marcas) trata igual «consulta» y «documento». Pero una consulta corta («caché redis timeout») y un párrafo no son el mismo tipo de texto. E5 (Wang et al., 2022) entrena con prefijos `query: ` y `passage: ` («rompen la simetría»; el paper dice que importa sobre todo cuando el corpus contiene paráfrasis de la consulta). INSTRUCTOR (Su et al., 2022) generaliza la idea a **instrucciones** en lenguaje natural por tarea, y los embedders basados en LLMs del módulo 12 las usan de forma sistemática.
Regla de oro: **usa exactamente los prefijos con los que se entrenó el modelo**; omitirlos o inventarlos es una de las causas más comunes de «el modelo funciona peor que en el leaderboard».
""")
nb.code(r'''
# Ablación de prefijos: solo tiene sentido con E5 real; con el fallback se ejecuta igual pero el modelo nunca vio prefijos.
n_pref = next((n for n, e in encs.items() if e.prefijos != ("", "")), list(encs)[-1])
e = encs[n_pref]
variantes = {"query:/passage:": ("query: ", "passage: "), "sin prefijos": ("", ""), "query: en ambos lados": ("query: ", "query: ")}
orig = e.prefijos
if orig == ("", ""):
    print(f"(nota: {n_pref} NO se entrenó con prefijos; las diferencias aquí son ruido, no un efecto)")
for nombre, pre in variantes.items():
    e.prefijos = pre
    S = coseno(e.encode(q_txt, "mean", tipo="query"), e.encode(doc_txt, "mean", tipo="doc"))
    print(f"{n_pref} · {nombre:34s} nDCG@10={evalua(S)['ndcg']:.3f}")
e.prefijos = orig
''')
nb.md(r"""
> 👀 **Qué debes observar.** Con E5 real, quitar los prefijos o usar `query:` en ambos lados cambia el nDCG@10: el modelo aprendió a tratar distinto cada lado. Con el *fallback* (sin prefijos en su entrenamiento) las diferencias son ruido: ese contraste es justo la lección, un prefijo solo significa algo si el modelo se entrenó con él.
""")

nb.md(r"""
## 9. Bi-encoder vs cross-encoder
- **Bi-encoder** (SBERT): $\text{score}(q,d)=\cos(f(q),f(d))$. Los documentos se codifican **una vez** y se indexan; una consulta cuesta 1 forward + una búsqueda ANN. Coste de buscar en $N$ documentos: $O(1)$ forwards por consulta.
- **Cross-encoder**: $\text{score}(q,d)=g([q;d])$, un Transformer que lee consulta y documento juntos (atención cruzada completa). Más preciso, pero cuesta **$N$ forwards por consulta**: inviable como primera etapa, ideal para **re-rankear** los top-100 (módulo 13).
- SBERT (Reimers & Gurevych, 2019) mostró que entrenar el bi-encoder siamés (pesos compartidos) para similitud resolvía el problema de BERT crudo: es el patrón que entrenarás tú en el módulo 11.
""")
nb.gemini(
    "imagen", "M10-IMG-04", "Bi-encoder (siamés) frente a cross-encoder",
    "Compara las dos arquitecturas de similitud y su coste: dos torres con pesos compartidos y coseno vs un único Transformer que lee el par concatenado.",
    """
    Diagrama técnico limpio, fondo blanco, 16:9, dos mitades separadas por una línea vertical gris. Paleta: azul #1F6FEB (bi-encoder), naranja #F28E2B (cross-encoder), verde #2CA02C (salidas), gris #6B7280 (texto secundario).
    Mitad izquierda, título «Bi-encoder (SBERT)»: dos cajas de texto abajo «consulta: cómo configurar la caché» y «documento: La caché es una memoria rápida…». Encima de cada una, una torre azul idéntica rotulada «Transformer + pooling» y entre las dos torres un candado con el texto «pesos compartidos». Sobre cada torre un vector verde «u» y «v», y arriba una caja «cos(u, v)». A un lado: «documentos: se codifican UNA vez y se indexan (ANN)» y «coste por consulta: 1 forward + búsqueda».
    Mitad derecha, título «Cross-encoder»: una sola caja de texto «[CLS] consulta [SEP] documento [SEP]», encima una única torre naranja más ancha rotulada «Transformer (atención cruzada completa)» y arriba una caja verde «score ∈ ℝ». A un lado: «coste por consulta: N forwards (uno por documento)» y «uso típico: re-rankear el top-100».
    Evita: texto ilegible, flechas ambiguas, números inventados, decoración.
    """,
    "Bi-encoder con dos torres de pesos compartidos y coseno frente a cross-encoder con un único Transformer sobre el par concatenado.",
    """
    BI-ENCODER                          | CROSS-ENCODER
    q ─► [Transformer+pool] ─► u ┐      | [CLS] q [SEP] d [SEP] ─► [Transformer] ─► score
    d ─► [Transformer+pool] ─► v ┴ cos  | coste: N forwards/consulta → re-ranking
    (pesos compartidos; d se indexa)    |
    """,
)
nb.md(r"""
> 👀 **Qué debes observar.** La única diferencia estructural es **dónde** se mezclan consulta y documento: al final (un coseno, factorizable e indexable) o desde la primera capa (atención cruzada, no indexable). Es el mismo *trade-off* que *two-tower* vs *ranker* en recsys.
""")

nb.md(r"""
## Mapa de madurez (a oct-2026)

| Técnica | Madurez | Quién la usa (verificable) | Fuente |
|---|---|---|---|
| Bi-encoder siamés + mean pooling | 🟢 sólido | sentence-transformers (SBERT), E5 (*average pooling*) | Reimers & Gurevych 2019; Wang et al. 2022 |
| CLS pooling | 🟢 sólido (según modelo) | DPR usa la representación de `[CLS]` | Karpukhin et al. 2020 |
| Last-token pooling en decoders | 🟡 emergente → estándar en LLM-embedders | SGPT; embedders basados en LLMs (módulo 12) | Muennighoff 2022 |
| Prefijos / instrucciones | 🟢 sólido | E5 (`query:`/`passage:`), INSTRUCTOR | Wang et al. 2022; Su et al. 2022 |
| Whitening / centrado post-hoc | 🟡 útil para encoders crudos; poco usado con embedders modernos | — | Su et al. 2021; Mu & Viswanath 2018 |
| BERT-flow | 🔴 mayormente superado (whitening lineal comparable) | — | Li et al. 2020; Su et al. 2021 |
| Multilingüe por destilación | 🟢 sólido | `paraphrase-multilingual-*` de sentence-transformers | Reimers & Gurevych 2020 |
| Cross-encoder para re-ranking | 🟢 sólido | ver módulo 13 | Reimers & Gurevych 2019 |
""")

nb.md(r"""
## 🏭 En producción
- **El pooling viaja con el modelo.** En sentence-transformers el módulo `Pooling` se guarda en la configuración del modelo; si reimplementas la inferencia (ONNX, TEI, tu propio servidor), verifica numéricamente contra la librería como hicimos arriba (error ~1e-6).
- **Prefijos en producción.** Los modelos tipo E5 requieren `query: `/`passage: `; muchos embedders recientes usan instrucciones por tarea (módulo 12). Un servicio que indexa con un prefijo y consulta con otro degrada en silencio: inclúyelo en tests de integración.
- **Normaliza una vez.** Si el modelo se entrenó con coseno, guarda vectores L2-normalizados y usa producto escalar en el índice (FAISS `IndexFlatIP`, HNSW con IP): más rápido y equivalente (módulo 14).
- **Post-procesado como transformación del índice.** Centrado/whitening son una matriz $d\times k$: se aplican al indexar y al consultar, se versionan junto al modelo y, con $k<d$, reducen memoria.
- **Para Políglota:** el bi-encoder será la primera etapa (recall), con BM25 en híbrido (13) y un cross-encoder opcional para re-rankear.
""")

nb.md(r"""
## 🧠 Secretos de la élite
1. **Embeddings crudos de BERT ≠ embeddings de similitud.** SBERT midió que la media de BERT sin ajustar (54.81 de media en STS) y su CLS (29.19) quedaban por debajo de promediar GloVe (61.32). Antes de culpar al índice, comprueba que el modelo fue entrenado para similitud.
2. **Audita el pooling contra la librería.** Una diferencia de pooling (CLS vs mean, o media sin máscara) puede hundir el nDCG sin dar ningún error; nuestra comprobación numérica tarda segundos.
3. **`h[:, -1]` no es el último token** con *padding* a la derecha: usa la máscara (como `ultimo_token`). Es un bug clásico al convertir LLMs en embedders.
4. **El whitening se ajusta con documentos, y $k$ se elige en validación.** Ajustarlo con las consultas de test es *leakage*; y su efecto depende del encoder (en nuestro fallback osciló entre ×1.5 y −10 % según la ejecución).
5. **El idioma es una dirección.** En multilingüe, centrar por idioma reduce la separación por lengua (lo mediste con silhouette); útil para búsqueda cruzada, pero exige saber el idioma de la consulta.
6. **Coseno = producto con vectores normalizados (τ = 1.00).** Si la norma varía, el producto escalar introduce un sesgo hacia documentos de norma grande, análogo al sesgo de popularidad en recsys.
7. **Respeta los prefijos del entrenamiento.** Es la primera comprobación cuando un embedder rinde menos que en MTEB.
""")

nb.md(r"""
## ⚠️ Errores comunes
- Media sin máscara de *padding* (embeddings que dependen del lote).
- Usar CLS en un modelo entrenado con media (o al revés).
- Ajustar whitening/centrado con el conjunto de test.
- Mezclar métrica: entrenado con coseno, indexado con producto escalar sin normalizar.
- Olvidar los prefijos `query:`/`passage:` o aplicarlos en un modelo que no los usa.
- Truncar documentos largos sin darse cuenta (`max_length`): el final del documento no existe para el modelo.
- Concluir que «los embeddings no funcionan» comparando con BM25 en un benchmark de ítem conocido con fuerte solapamiento léxico.
""")

nb.md(r"""
## Autoevaluación
<details><summary><b>1. (Cálculo)</b> Dos vectores unitarios tienen coseno 0.8. ¿Cuál es su distancia L2? ¿Y si el coseno es 0.2?</summary>

$\|\mathbf q-\mathbf d\|=\sqrt{2-2\cdot0.8}=\sqrt{0.4}\approx0.632$; con 0.2: $\sqrt{1.6}\approx1.265$.
</details>

<details><summary><b>2. (Cálculo)</b> Un cross-encoder tarda 5 ms por par en GPU. ¿Cuánto tarda en puntuar 1 M de documentos para una consulta? ¿Y re-rankear el top-100?</summary>

$10^6\times5$ ms $=5000$ s ≈ 83 min por consulta; el top-100, 0.5 s (y en lote, menos). Por eso el cross-encoder va **después** del bi-encoder.
</details>

<details><summary><b>3. (Diagnóstico)</b> Tu servicio da nDCG 0.42 y el mismo modelo en tu notebook 0.55. El código de pooling es «el mismo». ¿Qué tres cosas compruebas?</summary>

(a) Máscara de padding en la media (el servicio agrupa en lotes de tamaño distinto); (b) prefijos/instrucciones idénticos al indexar y al consultar; (c) normalización y métrica del índice (coseno vs producto sin normalizar), y de paso `max_length`.
</details>

<details><summary><b>4. (Diagnóstico)</b> Tras whitening completo ($k=d$), el coseno medio entre documentos es ≈ 0 pero el nDCG bajó. ¿Contradicción?</summary>

No. Isotropía no es relevancia: el whitening da el mismo peso a direcciones de ruido que a las informativas. Reduce $k$ (quedarte con las direcciones de mayor varianza) y elige $k$ en validación, o usa solo centrado.
</details>

<details><summary><b>5. (Transferencia)</b> En tu *two-tower* de recsys, los ítems populares tienen normas grandes. ¿Coseno o producto escalar para recuperar candidatos? ¿Qué cambia?</summary>

Con producto escalar la norma actúa como prior de popularidad (más clics, menos diversidad); con coseno se elimina. La elección depende del objetivo; lo correcto es usar la del entrenamiento y, si quieres controlar popularidad, hacerlo explícitamente (logQ, re-ranking).
</details>

<details><summary><b>6.</b> ¿Por qué la self-similarity de una palabra en la capa 0 es casi 1?</summary>

Porque la capa 0 es el embedding de entrada: la misma fila de $E$ (más la posición) en todos los contextos.
</details>

<details><summary><b>7. (Transferencia)</b> Políglota recibe consultas en ES y documentos en EN. ¿Qué técnica de este módulo probarías primero sin reentrenar y cómo la validarías?</summary>

Centrado por idioma (restar la media de documentos de cada idioma y la de las consultas de su idioma detectado) y medir nDCG@10 en un conjunto de validación **cruzado** (consulta ES → documento EN), comparando con el modelo sin centrar.
</details>
""")

nb.md(r"""
## Referencias
- Devlin, J., Chang, M.-W., Lee, K., & Toutanova, K. (2019). *BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding.* [arXiv:1810.04805](https://arxiv.org/abs/1810.04805)
- Reimers, N., & Gurevych, I. (2019). *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks.* EMNLP. [arXiv:1908.10084](https://arxiv.org/abs/1908.10084)
- Reimers, N., & Gurevych, I. (2020). *Making Monolingual Sentence Embeddings Multilingual using Knowledge Distillation.* [arXiv:2004.09813](https://arxiv.org/abs/2004.09813)
- Ethayarajh, K. (2019). *How Contextual are Contextualized Word Representations? Comparing the Geometry of BERT, ELMo, and GPT-2 Embeddings.* EMNLP. [arXiv:1909.00512](https://arxiv.org/abs/1909.00512)
- Li, B., Zhou, H., He, J., et al. (2020). *On the Sentence Embeddings from Pre-trained Language Models* (BERT-flow). [arXiv:2011.05864](https://arxiv.org/abs/2011.05864)
- Su, J., Cao, J., Liu, W., et al. (2021). *Whitening Sentence Representations for Better Semantics and Faster Retrieval.* [arXiv:2103.15316](https://arxiv.org/abs/2103.15316)
- Mu, J., Bhat, S., & Viswanath, P. (2018). *All-but-the-Top: Simple and Effective Postprocessing for Word Representations.* ICLR. [arXiv:1702.01417](https://arxiv.org/abs/1702.01417)
- Timkey, W., & van Schijndel, M. (2021). *All Bark and No Bite: Rogue Dimensions in Transformer Language Models Obscure Representational Quality.* [arXiv:2109.04404](https://arxiv.org/abs/2109.04404)
- Godey, N., de la Clergerie, É., & Sagot, B. (2024). *Anisotropy Is Inherent to Self-Attention in Transformers.* [arXiv:2401.12143](https://arxiv.org/abs/2401.12143)
- Libovický, J., Rosa, R., & Fraser, A. (2019). *How Language-Neutral is Multilingual BERT?* [arXiv:1911.03310](https://arxiv.org/abs/1911.03310)
- Wang, L., Yang, N., Huang, X., et al. (2022). *Text Embeddings by Weakly-Supervised Contrastive Pre-training* (E5). [arXiv:2212.03533](https://arxiv.org/abs/2212.03533)
- Su, H., Shi, W., Kasai, J., et al. (2022). *One Embedder, Any Task: Instruction-Finetuned Text Embeddings* (INSTRUCTOR). [arXiv:2212.09741](https://arxiv.org/abs/2212.09741)
- Muennighoff, N. (2022). *SGPT: GPT Sentence Embeddings for Semantic Search.* [arXiv:2202.08904](https://arxiv.org/abs/2202.08904)
- Karpukhin, V., Oğuz, B., Min, S., et al. (2020). *Dense Passage Retrieval for Open-Domain Question Answering.* [arXiv:2004.04906](https://arxiv.org/abs/2004.04906)
- Steck, H., Ekanadham, C., & Kallus, N. (2024). *Is Cosine-Similarity of Embeddings Really About Similarity?* [arXiv:2403.05440](https://arxiv.org/abs/2403.05440)
- Librería: sentence-transformers (https://pypi.org/project/sentence-transformers/), módulos `Transformer` y `Pooling`.

## Siguiente módulo
**11 · Aprendizaje contrastivo**: entrenar tú el bi-encoder de Políglota con InfoNCE, negativos en el lote y *hard negatives*, desde cero en PyTorch y con sentence-transformers.
""")
nb.save(LESSON)

# ════════════════════════════════════════════════════════════════════════════════════════
#  PROYECTO 10
# ════════════════════════════════════════════════════════════════════════════════════════
pj = Notebook("Proyecto 10 · Pooling y whitening para Políglota", colab_path=PROJECT)
pj.md(pj.badge() + r"""
# Proyecto 10 · ¿Qué vector por documento? Pooling y post-procesado en el retrieval de Políglota

| | |
|---|---|
| **Nivel** | 🟡 Intermedio |
| **Duración** | ≈ 2 h |
| **Cómputo** | CPU en `FAST_DEV_RUN` (≈ 4 min, la mayor parte construyendo los encoders de fallback); con modelos reales, T4 recomendada |
| **Requisitos** | Lección 10 |

## Contexto de negocio
En **Políglota Labs** aún no hay embedder propio (llega en el módulo 11). Producto quiere una primera versión de búsqueda semántica **ya**, con encoders preentrenados.
Tu tarea: decidir, **con datos y sin hacer trampas con el test**, qué combinación *encoder × pooling × post-procesado* usar, y documentar cuánto se gana o pierde frente a la configuración «por defecto» (media, sin post-procesado) y frente a BM25 (módulo 00).

**Conexión.** Usa el corpus y las métricas del módulo 00; la configuración ganadora es el *baseline* denso que tu embedder entrenado deberá batir en el módulo 11.

## Dataset
Corpus Políglota (`carga_corpus`): Wikipedia ES/EN + código (CodeSearchNet o stdlib) o, sin red, sintético con el mismo esquema. Las consultas se parten **50/50 en validación y test** de forma determinista: eliges en validación y reportas en test.

## Entregables y rúbrica
Umbrales calibrados con la solución de referencia en la ejecución que pudo correrse al construir el curso (fallback: mini-BERT crudo + mini-SBERT, corpus sintético, semilla 42). Con modelos reales, ejecuta la solución y usa sus números menos el margen.

| # | Entregable | Criterio |
|---|---|---|
| R1 | `media_mascara`, `max_mascara`, `cls_pool`, `ultimo_token` | pasan los tests unitarios de la celda de comprobación |
| R2 | `ajusta_whitening(X, k)` | con $k=d/2$, la covarianza de $(X-\mu)W$ difiere de $I_k$ en < 1e-3 (máx. absoluto) |
| R3 | `centra_por_idioma` | la media por idioma de los documentos transformados es ≈ 0 (< 1e-6) |
| R4 | Tabla en **validación** con ≥ 2 encoders × 4 poolings × 4 post-procesados (ninguno, centrado, whitening-k, centrado por idioma) | 32+ filas |
| R5 | Configuración elegida en validación, medida en **test** | nDCG@10 test ≥ el de «media sin post-procesado» del mismo encoder − 0.03 (referencia: la elegida, *whitening*, ganó +0.05 en validación pero en test quedó entre −0.017 y −0.003 respecto a la *default* en dos ejecuciones del fallback (el entrenamiento en CPU no es bit-a-bit determinista): con ~55 consultas por partición la selección es ruidosa, y eso es parte de lo que debes analizar) |
| R6 | Desglose por idioma (es/en/code) de la configuración elegida y comparación con BM25 | tabla impresa |
""")
pj.code(SETUP10)
pj.md("### Utilidades (corpus, métricas, BM25 canónicos y encoders). No hace falta modificarlas.")
for _src in src_corpus_cells():
    pj.code(_src)
pj.code(SRC_METRICS)
pj.code(SRC_BM25)
pj.code(CORPUS10)
pj.code(r'''
# Partición determinista de las consultas: validación / test (≈ 50/50 por hash del qid; no estratificada)
import zlib
split = {q["qid"]: ("val" if zlib.crc32(q["qid"].encode()) % 2 == 0 else "test") for q in queries}
idx = {s: [i for i, q in enumerate(queries) if split[q["qid"]] == s] for s in ("val", "test")}


def evalua_split(S, s, k=10, lang=None):
    ii = [i for i in idx[s] if lang is None or queries[i]["lang"] == lang]
    run = {queries[i]["qid"]: rank_from_scores(S[i], doc_ids, 100) for i in ii}
    return evaluate(run, {queries[i]["qid"]: qrels[queries[i]["qid"]] for i in ii}, k)


print({s: len(v) for s, v in idx.items()})
''')
pj.code(FALLBACK10)
pj.code(ENCODER)
pj.code(r'''
def coseno(Q, D):
    Qn = Q / np.linalg.norm(Q, axis=1, keepdims=True).clip(1e-12)
    Dn = D / np.linalg.norm(D, axis=1, keepdims=True).clip(1e-12)
    return Qn @ Dn.T


encs = carga_encoders(doc_txt)
langs_doc = np.array([d["lang"] for d in docs])
langs_q = np.array([q["lang"] for q in queries])
''')

pj.md(r"""
## TODO 1 · Pooling con máscara
Implementa las cuatro funciones: entrada `h` (B, T, d) y `mask` (B, T) con 1 = token real; salida (B, d).

<details><summary>🪜 Pista 1</summary>

Media: multiplica por la máscara expandida a (B, T, 1) y divide por el nº de tokens reales. Máximo: rellena las posiciones de padding con el mínimo representable antes de `max`.
</details>
<details><summary>🪜 Pista 2</summary>

Último token real: `T - 1 - mask.flip(1).float().argmax(1)` da el índice del último 1 de cada fila (funciona con padding a la izquierda y a la derecha). Luego `h[torch.arange(B), idx]`.
</details>
""")
pj.code(r'''
def media_mascara(h, mask):
    # TODO 1a
    raise NotImplementedError


def max_mascara(h, mask):
    # TODO 1b
    raise NotImplementedError


def cls_pool(h, mask):
    return h[:, 0]


def ultimo_token(h, mask):
    # TODO 1c
    raise NotImplementedError


POOLS = {"cls": cls_pool, "mean": media_mascara, "max": max_mascara, "last": ultimo_token}
''')
pj.code(r'''
# Tests de R1 (no los modifiques)
def tests_pooling():
    torch.manual_seed(0)
    h = torch.randn(2, 5, 3)
    m = torch.tensor([[1, 1, 1, 1, 1], [1, 1, 0, 0, 0]])
    assert torch.allclose(media_mascara(h, m)[1], h[1, :2].mean(0)), "media"
    assert torch.allclose(max_mascara(h, m)[1], h[1, :2].max(0).values), "máximo"
    assert torch.equal(ultimo_token(h, m)[1], h[1, 1]), "último (padding derecha)"
    m2 = torch.tensor([[1, 1, 1, 1, 1], [0, 0, 0, 1, 1]])
    assert torch.equal(ultimo_token(h, m2)[1], h[1, 4]), "último (padding izquierda)"
    return True


try:
    R1 = tests_pooling(); print("✅ R1 pooling")
except NotImplementedError:
    R1 = False; print("⏳ TODO 1 pendiente")
''')

pj.md(r"""
## TODO 2 · Whitening y TODO 3 · centrado por idioma
- `ajusta_whitening(X, k)` → `(mu, W)` con `W = U[:, :k] / sqrt(S[:k] + eps)` a partir de la SVD de la covarianza de `X`.
- `centra_por_idioma(X, langs, medias=None)` → `(X_centrado, medias)`: resta a cada fila la media de su idioma; si `medias` se pasa (calculadas con los **documentos**), úsalas (así se transforman las consultas).

<details><summary>🪜 Pista 1</summary>

¿Con qué datos ajustas `mu`, `W` y las medias por idioma? Solo con los **documentos** (el índice). Las consultas se transforman con esos parámetros.
</details>
""")
pj.code(r'''
def ajusta_whitening(X, k=None, eps=1e-6):
    # TODO 2
    raise NotImplementedError


def centra_por_idioma(X, langs, medias=None):
    # TODO 3
    raise NotImplementedError
''')

pj.md(r"""
## TODO 4 · Rejilla de configuraciones en validación
Completa `postprocesa(D, Q, modo)` para los modos `"ninguno"`, `"centrado"`, `"whitening"` (con $k$ = mitad de la dimensión) y `"idioma"`. La celda siguiente recorre encoders × poolings × modos y guarda nDCG@10 de **validación**.

<details><summary>🪜 Pista 1</summary>

`"centrado"`: resta `D.mean(0)` a ambos. `"whitening"`: `mu, W = ajusta_whitening(D, D.shape[1] // 2)` y aplica `(X - mu) @ W` a ambos. `"idioma"`: `centra_por_idioma(D, langs_doc)` y luego las consultas con las medias de los documentos (`langs_q`; el código de las consultas `code` usa la media de los documentos `code`).
</details>
""")
pj.code(r'''
MODOS = ["ninguno", "centrado", "whitening", "idioma"]


def postprocesa(D, Q, modo):
    # TODO 4
    raise NotImplementedError


def rejilla():
    filas, cache = [], {}
    for n, e in encs.items():
        for p in POOLS:
            D, Q = e.encode(doc_txt, p, tipo="doc"), e.encode(q_txt, p, tipo="query")
            cache[(n, p)] = (D, Q)
            for modo in MODOS:
                D2, Q2 = postprocesa(D, Q, modo)
                filas.append(dict(encoder=n, pooling=p, modo=modo, ndcg_val=evalua_split(coseno(Q2, D2), "val")["ndcg"]))
    return filas, cache


try:
    filas, cache = rejilla()
    print(f"{len(filas)} configuraciones evaluadas en validación")
except NotImplementedError:
    filas = None; print("⏳ TODO 1–4 pendientes")
''')

pj.md(r"""
## TODO 5 · Elegir en validación, reportar en test y rúbrica
La celda ya está escrita: elige la mejor configuración **en validación**, la mide en **test**, la compara con «media sin post-procesado» del mismo encoder y con BM25, desglosa por idioma y comprueba la rúbrica. Escribe después 4–5 frases con tu recomendación para Producto.
""")
pj.code(r'''
def informe_y_rubrica(filas, cache):
    import pandas as pd
    df = pd.DataFrame(filas).sort_values("ndcg_val", ascending=False)
    best = df.iloc[0]
    D, Q = cache[(best.encoder, best.pooling)]
    D2, Q2 = postprocesa(D, Q, best.modo)
    S_best = coseno(Q2, D2)
    S_def = coseno(*cache[(best.encoder, "mean")][::-1])
    bm = BM25().fit([tokenize_simple(t) for t in doc_txt], doc_ids)
    S_bm = np.array([bm.scores(tokenize_simple(q)) for q in q_txt])
    t_best, t_def, t_bm = (evalua_split(S, "test")["ndcg"] for S in (S_best, S_def, S_bm))
    print(df.head(8).to_string(index=False))
    print(f"\nElegida en validación: {best.encoder} · {best.pooling} · {best.modo}")
    print(f"TEST nDCG@10: elegida={t_best:.3f} | media sin post-procesado={t_def:.3f} | BM25={t_bm:.3f}")
    for l in ("es", "en", "code"):
        print(f"   {l:5s} elegida={evalua_split(S_best, 'test', lang=l)['ndcg']:.3f} | BM25={evalua_split(S_bm, 'test', lang=l)['ndcg']:.3f}")
    mu, W = ajusta_whitening(D, D.shape[1] // 2)
    Xw = (D - mu) @ W
    R2 = np.abs(np.cov(Xw.T) - np.eye(Xw.shape[1])).max() < 1e-3
    Dl, med = centra_por_idioma(D, langs_doc)
    R3 = max(np.abs(Dl[langs_doc == l].mean(0)).max() for l in np.unique(langs_doc)) < 1e-6
    checks = {"R1 pooling": R1, "R2 whitening ≈ identidad": R2, "R3 centrado por idioma": R3,
              "R4 ≥ 32 configuraciones": len(df) >= 32, "R5 test ≥ default − 0.03": t_best >= t_def - 0.03, "R6 desglose impreso": True}
    for k_, ok in checks.items():
        print(("✅ " if ok else "❌ ") + k_)
    return dict(best=best.to_dict(), test_best=t_best, test_default=t_def, test_bm25=t_bm)


if filas:
    informe = informe_y_rubrica(filas, cache)
''')
pj.md(r"""
## Retos extra
1. **Elegir $k$ del whitening en validación** (8, 16, 32, 64, …) en vez de fijar $d/2$. ¿Cuánto cambia el resultado en test? ¿Y su varianza con otra semilla de partición?
2. **Intervalos de confianza**: bootstrap por consulta del nDCG@10 de test (módulo 15) para la elegida y la *default*. ¿Es significativa la diferencia?
3. **Híbrido rápido**: suma normalizada de scores densos y BM25 ($\alpha\in\{0.3, 0.5, 0.7\}$, elegido en validación). Es el adelanto del módulo 13.
4. **Coseno vs producto**: repite la mejor configuración con producto escalar sin normalizar.

## Reflexión
- ¿Por qué elegir en validación y reportar en test es imprescindible incluso con solo 32 configuraciones?
- ¿Qué parámetros de post-procesado tendrías que versionar junto al modelo en producción?
- Si BM25 gana en este benchmark de ítem conocido, ¿significa que la búsqueda semántica no sirve para Políglota? ¿Qué consultas faltan en el *golden set*?
""")
pj.md(r"""
---
## ⛔ SPOILER — intenta resolverlo primero
Solución de referencia completa: redefine las funciones y vuelve a ejecutar tests, rejilla, informe y rúbrica.
""")
pj.code(r'''
def media_mascara(h, mask):
    m = mask.unsqueeze(-1).to(h.dtype)
    return (h * m).sum(1) / m.sum(1).clamp(min=1e-9)


def max_mascara(h, mask):
    return h.masked_fill(mask.unsqueeze(-1) == 0, torch.finfo(h.dtype).min).max(1).values


def ultimo_token(h, mask):
    idx_ = mask.shape[1] - 1 - mask.flip(1).float().argmax(1)
    return h[torch.arange(h.shape[0]), idx_]


POOLS = {"cls": cls_pool, "mean": media_mascara, "max": max_mascara, "last": ultimo_token}


def ajusta_whitening(X, k=None, eps=1e-6):
    mu = X.mean(0, keepdims=True)
    U, S, _ = np.linalg.svd(np.cov((X - mu).T))
    k = k or X.shape[1]
    return mu, U[:, :k] / np.sqrt(S[:k] + eps)


def centra_por_idioma(X, langs, medias=None):
    medias = medias or {l: X[langs == l].mean(0) for l in np.unique(langs)}
    Xc = X.copy()
    for l, m in medias.items():
        Xc[langs == l] -= m
    return Xc, medias


def postprocesa(D, Q, modo):
    if modo == "ninguno":
        return D, Q
    if modo == "centrado":
        mu = D.mean(0, keepdims=True)
        return D - mu, Q - mu
    if modo == "whitening":
        mu, W = ajusta_whitening(D, D.shape[1] // 2)
        return (D - mu) @ W, (Q - mu) @ W
    if modo == "idioma":
        D2, med = centra_por_idioma(D, langs_doc)
        Q2, _ = centra_por_idioma(Q, langs_q, med)
        return D2, Q2
    raise ValueError(modo)


R1 = tests_pooling(); print("✅ R1 pooling")
filas, cache = rejilla()
informe = informe_y_rubrica(filas, cache)
''')
pj.save(PROJECT)

README = r"""# Módulo 10 · Embeddings contextuales y de oraciones

**Nivel:** 🟡 Intermedio · **Duración:** ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) · **Cómputo:** CPU en `FAST_DEV_RUN`; T4 recomendada con modelos reales (≈ 0.5 h)

| Archivo | Contenido |
|---|---|
| [`10_embeddings_contextuales_oraciones.ipynb`](10_embeddings_contextuales_oraciones.ipynb) | Lección: estático vs contextual · pooling CLS/media/máximo/último token desde cero (máscaras, padding) y verificación contra sentence-transformers · contextualidad por capa (self-similarity vs anisotropía, Ethayarajh 2019) · pooling × encoder en Políglota vs BM25 · rogue dimensions · centrado, whitening (derivación) y all-but-the-top; BERT-flow · el idioma como dirección (centrado por idioma) · coseno vs producto vs L2 · prefijos e instrucciones (E5) · bi-encoder vs cross-encoder |
| [`10_proyecto_embeddings_contextuales_oraciones.ipynb`](10_proyecto_embeddings_contextuales_oraciones.ipynb) | Proyecto Políglota: rejilla encoder × pooling × post-procesado elegida en validación y medida en test (nDCG@10), con desglose por idioma y comparación con BM25 |
| `assets/` | Imágenes de Gemini `M10-IMG-01` … `M10-IMG-04` |

## Modelos
`distilbert-base-multilingual-cased` (crudo), `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (SBERT multilingüe) e `intfloat/multilingual-e5-small` (prefijos `query:`/`passage:`).
**Fallback documentado** (sin hub): mini-BERT solo-MLM («crudo») y mini-SBERT (el mismo + 200 pasos contrastivos con pares débiles frase-1 ↔ resto), entrenados en el notebook (~2 min de CPU).

## Datos
Corpus Políglota canónico del módulo 00 (`carga_corpus`), métricas y BM25 canónicos.

## Estado de pruebas (entorno de autoría)
Hugging Face bloqueado por el proxy: lección y proyecto ejecutados completos **solo con el fallback** y el corpus sintético + stdlib. Las celdas con modelos reales no pudieron ejecutarse aquí (protegidas con `try/except`). Umbrales de la rúbrica calibrados con esa ejecución.

## Lecturas clave
Reimers & Gurevych 2019 (SBERT) · Ethayarajh 2019 · Su et al. 2021 (whitening) · Li et al. 2020 (BERT-flow) · Wang et al. 2022 (E5) · Timkey & van Schijndel 2021.

Los notebooks se generan con `python tokenization-embeddings-course/_tools/builders/build_10.py` (desde la raíz del repo).
"""
(ROOT / MOD / "README.md").write_text(README, encoding="utf-8")
(ROOT / MOD / "assets").mkdir(exist_ok=True)
(ROOT / MOD / "assets" / ".gitkeep").touch()
print("OK README y assets/")
