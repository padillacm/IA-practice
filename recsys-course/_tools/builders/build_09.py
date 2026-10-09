"""Construye los notebooks del módulo 09_sequential.

Ejecutar desde la raíz del repo:  python recsys-course/_tools/builders/build_09.py
"""
import os
import sys

sys.path.insert(0, "recsys-course/_tools")
sys.path.insert(0, "recsys-course/_tools/builders")
from nbbuild import Notebook  # noqa: E402
from _b4_common import UTILS_MD, UTILS_LOAD, UTILS_SEQ, UTILS_EVAL  # noqa: E402

MOD = "recsys-course/09_sequential"
LESSON = f"{MOD}/09_sequential.ipynb"
PROJECT = f"{MOD}/09_proyecto_sasrec_cinematch.ipynb"
os.makedirs(MOD, exist_ok=True)

# ---------------------------------------------------------------------------
# Celdas compartidas lección/proyecto
# ---------------------------------------------------------------------------
IMPORTS = r"""
import math, time, random, collections, subprocess
import numpy as np, pandas as pd
import scipy.sparse as sp
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import seaborn as sns
import torch, torch.nn as nn, torch.nn.functional as F

seed = 42
random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
device = "cuda" if torch.cuda.is_available() else "cpu"
USE_AMP = device == "cuda" and torch.cuda.is_bf16_supported()   # bf16 en L4/A100 (no en T4)
FAST_DEV_RUN = False          # True = iterar rápido (pocas épocas, subconjunto); False = experimento completo en GPU
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.3})
print("device:", device, "| bf16:", USE_AMP, "| torch", torch.__version__)
"""

DRAW_HELPERS = r"""
# Helpers para dibujar diagramas con matplotlib (sin imágenes externas)
def box(ax, x, y, w, h, text, fc="#dbeafe", ec="#1e3a8a", fs=9, weight="normal"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02", fc=fc, ec=ec, lw=1.2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, weight=weight)

def arrow(ax, x1, y1, x2, y2, color="#334155", lw=1.2, style="-|>"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle=style, color=color, lw=lw))

def blank(ax, xlim=(0, 10), ylim=(0, 5)):
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.axis("off")
"""

LOAD_DATA = r"""
ratings, movies = load_movielens_1m()
seqs, item2idx, idx2item = build_sequences(ratings, min_len=5)
n_items = len(item2idx)
train_seqs, valid, test = leave_one_out(seqs)
title_of = dict(zip(movies["item"], movies["title"]))
genre_of = dict(zip(movies["item"], movies["genres"].str.split("|").str[0]))
idx_title = lambda i: title_of.get(int(idx2item[i]), str(i))
lens = np.array([len(s) for s in seqs])
print(f"usuarios={len(seqs):,}  ítems={n_items:,}  interacciones={lens.sum():,}  "
      f"long. mediana={np.median(lens):.0f}  máx={lens.max()}")
"""

MODELS = r"""
class GRU4Rec(nn.Module):
    '''GRU4Rec simplificado: embedding -> GRU -> proyección; salida con pesos compartidos (weight tying).'''
    def __init__(self, n_items, d=64, hidden=128, n_layers=1, dropout=0.2):
        super().__init__()
        self.n_items = n_items
        self.item_emb = nn.Embedding(n_items + 2, d, padding_idx=0)
        nn.init.normal_(self.item_emb.weight, std=0.02)
        self.gru = nn.GRU(d, hidden, n_layers, batch_first=True, dropout=dropout if n_layers > 1 else 0.0)
        self.proj = nn.Linear(hidden, d)
        self.ln = nn.LayerNorm(d)              # misma escala de salida que SASRec (acelera mucho la convergencia)
        self.drop = nn.Dropout(dropout)

    def encode(self, seq):                     # seq [B, L] -> [B, L, d]
        h, _ = self.gru(self.drop(self.item_emb(seq)))
        return self.ln(self.proj(self.drop(h)))


class SelfAttention(nn.Module):
    def __init__(self, d, n_heads, dropout):
        super().__init__()
        assert d % n_heads == 0
        self.h, self.dk = n_heads, d // n_heads
        self.qkv, self.out, self.drop = nn.Linear(d, 3 * d), nn.Linear(d, d), nn.Dropout(dropout)
        self.keep_attn, self.last_attn = False, None

    def forward(self, x, block):               # block: bool [B,1,L,L]; True = prohibido atender
        B, L, D = x.shape
        q, k, v = self.qkv(x).view(B, L, 3, self.h, self.dk).permute(2, 0, 3, 1, 4)
        att = (q @ k.transpose(-2, -1)) / math.sqrt(self.dk)
        att = att.masked_fill(block, float("-inf")).softmax(-1)
        if self.keep_attn:
            self.last_attn = att.detach().float().cpu()
        y = self.drop(att) @ v
        return self.out(y.transpose(1, 2).reshape(B, L, D))


class Block(nn.Module):
    '''Bloque Transformer pre-LN: x + Attn(LN(x)); x + FFN(LN(x)).'''
    def __init__(self, d, n_heads, dropout):
        super().__init__()
        self.ln1, self.ln2 = nn.LayerNorm(d), nn.LayerNorm(d)
        self.attn = SelfAttention(d, n_heads, dropout)
        self.ffn = nn.Sequential(nn.Linear(d, 4 * d), nn.GELU(), nn.Dropout(dropout), nn.Linear(4 * d, d))
        self.drop = nn.Dropout(dropout)

    def forward(self, x, block):
        x = x + self.drop(self.attn(self.ln1(x), block))
        return x + self.drop(self.ffn(self.ln2(x)))
"""

SASREC = r"""
def attention_block_mask(seq, causal=True):
    '''True = prohibido. Bloquea padding (claves) y, si causal, el futuro. La diagonal siempre se permite
    para que ninguna fila quede entera a -inf (evita NaN en las posiciones de padding).'''
    B, L = seq.shape
    blk = (seq == 0)[:, None, None, :].expand(B, 1, L, L).clone()
    if causal:
        blk |= torch.triu(torch.ones(L, L, dtype=torch.bool, device=seq.device), 1)
    return blk & ~torch.eye(L, dtype=torch.bool, device=seq.device)


class SASRec(nn.Module):
    '''SASRec (Kang & McAuley 2018). Con causal=False y un token [MASK] se convierte en BERT4Rec.'''
    def __init__(self, n_items, d=64, n_layers=2, n_heads=2, maxlen=200, dropout=0.2, causal=True):
        super().__init__()
        self.n_items, self.d, self.causal = n_items, d, causal
        self.item_emb = nn.Embedding(n_items + 2, d, padding_idx=0)   # n_items+1 = [MASK]
        self.pos_emb = nn.Embedding(maxlen, d)
        nn.init.normal_(self.item_emb.weight, std=0.02); nn.init.normal_(self.pos_emb.weight, std=0.02)
        self.blocks = nn.ModuleList([Block(d, n_heads, dropout) for _ in range(n_layers)])
        self.ln_f, self.drop = nn.LayerNorm(d), nn.Dropout(dropout)

    def encode(self, seq):                     # seq [B, L] (padding a la izquierda) -> [B, L, d]
        L = seq.size(1)
        x = self.item_emb(seq) + self.pos_emb(torch.arange(L, device=seq.device))
        x = self.drop(x) * (seq > 0).unsqueeze(-1)
        blk = attention_block_mask(seq, self.causal)
        for b in self.blocks:
            x = b(x, blk)
        return self.ln_f(x)

def n_params(m):
    return sum(p.numel() for p in m.parameters())
"""

LOSSES = r"""
def seq_loss(model, h, tgt, loss="ce", n_neg=1, gbce_t=0.75):
    '''h [B,L,d] estados ocultos; tgt [B,L] ítem siguiente (0 = ignorar).
    loss ∈ {"ce" (full softmax), "sampled_ce", "bce", "gbce"}.'''
    W, n, valid = model.item_emb.weight, model.n_items, tgt > 0
    if loss == "ce":                                                  # softmax sobre TODO el catálogo
        logits = h[valid] @ W[1:n + 1].T
        return F.cross_entropy(logits, tgt[valid] - 1)
    neg = torch.randint(1, n + 1, (h.size(0), n_neg), device=h.device)  # negativos uniformes por secuencia
    pos_l = (h * W[tgt]).sum(-1)[valid]                               # [N]
    neg_l = torch.einsum("bld,bkd->blk", h, W[neg])[valid]            # [N, k]
    if loss == "sampled_ce":                                          # softmax sobre {positivo} ∪ negativos
        logits = torch.cat([pos_l[:, None], neg_l], 1)
        return F.cross_entropy(logits, torch.zeros(len(pos_l), dtype=torch.long, device=h.device))
    alpha = n_neg / (n - 1)                                           # tasa de muestreo de negativos
    beta = 1.0 if loss == "bce" else alpha * (gbce_t * (1 - 1 / alpha) + 1 / alpha)
    b0 = math.log(beta / n_neg)        # offset fijo = logit de la tasa base q*=β/(β+k): no cambia el ranking,
    pos_l, neg_l = pos_l + b0, neg_l + b0   # pero evita que los embeddings colapsen a «todo negativo»
    return (-beta * F.logsigmoid(pos_l) - F.logsigmoid(-neg_l).sum(-1)).mean()
"""

TRAIN = r"""
def make_bert_batch(batch, maxlen, mask_prob, mask_token):
    '''Cloze: enmascara ~mask_prob de las posiciones; etiqueta = ítem original (0 en las no enmascaradas).'''
    seq = pad_left(batch, maxlen)
    m = (torch.rand(seq.shape) < mask_prob) & (seq > 0)
    m[:, -1] |= torch.rand(seq.size(0)) < 0.25        # a veces enmascara el último: imita la inferencia
    return seq.masked_fill(m, mask_token), seq * m

def make_score_fn(model, maxlen, bert=False):
    @torch.no_grad()
    def f(H):
        model.eval()
        H = [h + [model.n_items + 1] for h in H] if bert else H    # BERT4Rec: [MASK] al final
        h = model.encode(pad_left(H, maxlen).to(device))[:, -1]
        return h.float() @ model.item_emb.weight[: model.n_items + 1].float().T
    return f

def train_seq_model(model, train_seqs, val, loss="ce", epochs=50, maxlen=200, batch_size=128, lr=1e-3,
                    n_neg=1, gbce_t=0.75, bert=False, mask_prob=0.2, eval_every=5, n_val=2000, name="modelo"):
    model.to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    users = [i for i, s in enumerate(train_seqs) if len(s) >= 2]
    vi = np.random.default_rng(0).choice(len(val[0]), min(n_val, len(val[0])), replace=False)
    val_sub = ([val[0][i] for i in vi], [val[1][i] for i in vi])
    score_fn, hist, t0 = make_score_fn(model, maxlen, bert), collections.defaultdict(list), time.time()
    for ep in range(1, epochs + 1):
        model.train(); perm, tot = np.random.permutation(users), 0.0
        for b in range(0, len(perm), batch_size):
            batch = [train_seqs[i] for i in perm[b:b + batch_size]]
            if bert:
                inp, tgt = make_bert_batch(batch, maxlen, mask_prob, model.n_items + 1)
            else:
                inp, tgt = pad_left([s[:-1] for s in batch], maxlen), pad_left([s[1:] for s in batch], maxlen)
            inp, tgt = inp.to(device), tgt.to(device)
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=USE_AMP):
                h = model.encode(inp)
            l = seq_loss(model, h.float(), tgt, "ce" if bert else loss, n_neg, gbce_t)
            opt.zero_grad(set_to_none=True); l.backward(); opt.step()
            tot += l.item() * len(batch)
        if ep % eval_every == 0 or ep == epochs:
            m = evaluate_next_item(score_fn, *val_sub, ks=(10,))
            hist["epoch"].append(ep); hist["loss"].append(tot / len(perm)); hist["val_NDCG@10"].append(m["NDCG@10"])
            print(f"[{name}] ep {ep:3d}  loss={tot/len(perm):.4f}  val NDCG@10={m['NDCG@10']:.4f}  "
                  f"({time.time()-t0:.0f}s)")
    hist["train_time_s"] = time.time() - t0
    return dict(hist)
"""

# ---------------------------------------------------------------------------
# LECCIÓN
# ---------------------------------------------------------------------------
nb = Notebook("Módulo 09 · Recomendación secuencial", colab_path=LESSON, gpu=True)

nb.md(f"""
{nb.badge()}

# Módulo 09 · Recomendación secuencial y por sesión
### De las cadenas de Markov a SASRec, BERT4Rec y gSASRec

| | |
|---|---|
| **Nivel** | 🟠 Avanzado |
| **Duración** | 4–5 h (lección) + 3–4 h (proyecto) |
| **GPU recomendada** | L4 (A100 si haces el barrido de negativos completo). Funciona en T4 sin bf16. |
| **Unidades Colab estimadas** | ≈ 3–5 unidades con L4 en modo completo (`FAST_DEV_RUN=False`); < 1 en modo rápido |
| **Prerrequisitos** | 01 (datos y *splits*), 02 (evaluación, NDCG), 05 (factorización/BPR), 08 (two-tower, *sampled softmax*, logQ) |

> Bloque IV — Estado del arte. Este módulo es la base de los **recomendadores generativos** del módulo 11:
> HSTU, TIGER y el *foundation model* de Netflix son, en el fondo, modelos secuenciales «a lo GPT».
""")

nb.md(r"""
## 🎯 Objetivos de aprendizaje
Al terminar serás capaz de:
1. **Formular** la recomendación secuencial como predicción del siguiente ítem $p(i_{t+1}\mid i_1,\dots,i_t)$ y distinguirla de la recomendación estática y de la basada en sesión.
2. **Implementar desde cero** en PyTorch una cadena de Markov, **GRU4Rec**, **SASRec** y **BERT4Rec** con una interfaz común.
3. **Derivar** por qué la BCE con pocos negativos produce **sobreconfianza** y cómo la corrige **gBCE** (gSASRec, RecSys 2023).
4. **Comparar** de forma justa *full softmax* (CE), *sampled softmax*, BCE y gBCE, y explicar el hallazgo de Klenitskiy & Vasilev (2023): *la función de pérdida pesa más que la arquitectura*.
5. **Visualizar e interpretar** mapas de atención causal y el espacio de *embeddings* de ítems.
6. **Evaluar** con protocolo *leave-one-out* y *full ranking* (HR@10, NDCG@10) evitando las trampas habituales.
7. **Usar** una librería de industria (RecTools) y conectar todo con sistemas reales (Pinterest, Alibaba, Kuaishou, Meta, Netflix).
""")

nb.code(r"""
# Colab ya trae torch, numpy, pandas, sklearn, matplotlib y seaborn.
# RecTools (MTS) se usa en la sección de librerías de industria.
!pip install -q "rectools[torch]"
""")
nb.code(IMPORTS)
nb.md(UTILS_MD)
nb.code(UTILS_LOAD)
nb.code(UTILS_SEQ)
nb.code(UTILS_EVAL)
nb.code(LOAD_DATA)
nb.code(DRAW_HELPERS)

# ---------------- Intuición
nb.md(r"""
## 💡 1. Intuición: el orden importa

Hasta ahora (MF, EASE, two-tower) hemos tratado el historial de un usuario como una **bolsa** de ítems: el modelo aprende $p(i \mid u)$.
Pero el comportamiento real tiene **orden y dinámica**:

- Si acabas de ver *Toy Story*, la probabilidad de *Toy Story 2* se dispara **ahora**, no «en general».
- En e-commerce, tras comprar una cámara llegan tarjetas SD y trípodes (**complementarios**), no otra cámara.
- Los gustos derivan: lo que veías hace dos años pesa menos que lo de esta semana.

💡 **Analogía con lo que ya sabes**: un recomendador secuencial es un **modelo de lenguaje** donde cada «palabra» es un ítem.
SASRec es literalmente un *decoder* tipo GPT entrenado con *next-token prediction* sobre el historial; BERT4Rec es un BERT con *masked language modeling*.
La diferencia práctica: el «vocabulario» son millones de ítems que cambian cada día y no hay gramática compartida entre usuarios.

Tres escenarios:
| Escenario | Entrada | Ejemplo | Modelo típico |
|---|---|---|---|
| **Estático** | conjunto de interacciones del usuario | «Para ti» genérico | MF, EASE, two-tower |
| **Secuencial** | historial ordenado de un usuario identificado | «Seguir viendo / porque viste X» | SASRec, BERT4Rec, HSTU |
| **Por sesión** | clics de una sesión **anónima** (sin historial) | e-commerce sin login | GRU4Rec, SR-GNN, SKNN |
""")

nb.code(r"""
# 📊 Diagrama 1 — Recomendación estática vs secuencial
fig, axes = plt.subplots(2, 1, figsize=(11, 4.6))
hist_titles = ["Toy Story", "Aladdin", "El Rey León", "Toy Story 2", "Bichos"]
for ax, mode in zip(axes, ["estatico", "secuencial"]):
    blank(ax, (0, 12), (0, 2))
    for j, t in enumerate(hist_titles):
        box(ax, 0.2 + j * 1.9, 0.6, 1.6, 0.8, t, fc="#e0f2fe" if mode == "secuencial" else "#f1f5f9")
        if mode == "secuencial" and j < len(hist_titles) - 1:
            arrow(ax, 1.8 + j * 1.9, 1.0, 2.1 + j * 1.9, 1.0)
    box(ax, 10.0, 0.6, 1.8, 0.8, "¿Monstruos S.A.?", fc="#fde68a", ec="#b45309", weight="bold")
    if mode == "estatico":
        ax.set_title("Estático: bolsa de ítems  →  p(i | u)   (el orden se pierde)", fontsize=10, loc="left")
        arrow(ax, 9.5, 1.0, 9.95, 1.0, color="#94a3b8", style="->")
    else:
        ax.set_title("Secuencial: p(i_{t+1} | i_1, …, i_t)   (como un modelo de lenguaje)", fontsize=10, loc="left")
        arrow(ax, 9.5, 1.0, 9.95, 1.0, color="#b45309", lw=2)
plt.tight_layout(); plt.show()
""")

nb.md(r"""
### 🧪 Experimento: ¿de verdad importa el orden en MovieLens?

Comparamos tres *baselines* en validación (*leave-one-out*, *full ranking*):
1. **Popularidad**: recomienda lo más visto (ignora al usuario).
2. **Markov de 1er orden** entrenado con el **orden real**: $p(j\mid i)\propto \#(i\to j)$ (transiciones consecutivas).
3. El **mismo Markov** pero entrenado tras **barajar** cada historial (destruimos el orden y conservamos los ítems).

Si (2) ≫ (3), la señal secuencial existe.
""")

nb.code(r"""
def fit_markov(train_seqs, n_items):
    src = np.concatenate([s[:-1] for s in train_seqs if len(s) > 1])
    dst = np.concatenate([s[1:] for s in train_seqs if len(s) > 1])
    return sp.csr_matrix((np.ones(len(src), dtype=np.float32), (src, dst)), shape=(n_items + 1, n_items + 1))

pop = np.bincount(np.concatenate(train_seqs), minlength=n_items + 1).astype(np.float32)
pop_score = lambda H: torch.from_numpy(np.tile(pop, (len(H), 1)))

def markov_score_fn(M, eps=1e-3):
    p = pop / pop.sum()
    return lambda H: torch.from_numpy(M[[h[-1] for h in H]].toarray() + eps * p)

rng = np.random.default_rng(seed)
M_ord = fit_markov(train_seqs, n_items)
M_shuf = fit_markov([list(rng.permutation(s)) for s in train_seqs], n_items)
base = {"Popularidad": evaluate_next_item(pop_score, *valid, ks=(10,)),
        "Markov (orden barajado)": evaluate_next_item(markov_score_fn(M_shuf), *valid, ks=(10,)),
        "Markov (orden real)": evaluate_next_item(markov_score_fn(M_ord), *valid, ks=(10,))}
display(pd.DataFrame(base).T.round(4))
""")

nb.code(r"""
# 📊 Gráfico 2 — EDA de secuencias + efecto del orden
fig, ax = plt.subplots(1, 3, figsize=(14, 3.6))
ax[0].hist(lens, bins=60, color="#3b82f6"); ax[0].set_yscale("log")
ax[0].set(title="Longitud de las secuencias", xlabel="nº interacciones por usuario", ylabel="usuarios (log)")
gaps = ratings.sort_values(["user", "ts"]).groupby("user")["ts"].diff().dropna()
ax[1].hist(np.log10(gaps.clip(lower=1)), bins=60, color="#10b981")
ax[1].set(title="Tiempo entre interacciones", xlabel="log10(segundos)", ylabel="frecuencia")
names = list(base); vals = [base[k]["NDCG@10"] for k in names]
ax[2].barh(names, vals, color=["#94a3b8", "#f59e0b", "#ef4444"])
ax[2].set(title="Validación NDCG@10", xlabel="NDCG@10")
plt.tight_layout(); plt.show()
""")

nb.md(r"""
⚠️ **Lectura del gráfico.** En MovieLens-1M muchos ratings se introducen en ráfagas (el usuario puntúa decenas de películas en minutos al registrarse; mira el pico de tiempos cortos).
El «orden» de ML-1M es, en parte, el **orden de puntuación** y no el de visionado. Aun así hay señal secuencial explotable — y por eso ML-1M es el *benchmark* estándar de SASRec/BERT4Rec/HSTU — pero recuerda esta limitación cuando extrapoles a producción.
""")

# ---------------- Teoría
nb.md(r"""
## 📐 2. Teoría formal

### 2.1 El problema
Sea $\mathcal{I}$ el catálogo ($|\mathcal{I}| = N$) y $S_u = (i_1, i_2, \dots, i_{n_u})$ la secuencia **ordenada por tiempo** del usuario $u$.
Queremos modelar
$$p(i_{t+1} = j \mid i_1,\dots,i_t) = \frac{\exp(\mathbf{h}_t^\top \mathbf{e}_j)}{\sum_{k \in \mathcal{I}} \exp(\mathbf{h}_t^\top \mathbf{e}_k)}$$
- $\mathbf{h}_t \in \mathbb{R}^d$: **estado del usuario** tras ver $t$ ítems (lo produce un GRU, un Transformer…).
- $\mathbf{e}_j \in \mathbb{R}^d$: *embedding* del ítem $j$ (normalmente **compartido** entre entrada y salida, *weight tying*).

Igual que en un LM, entrenamos con **todas las posiciones a la vez** (*teacher forcing*): la entrada $(i_1..i_{n-1})$ predice $(i_2..i_n)$.

### 2.2 Modelos de la familia
- **Markov / FPMC** (Rendle et al., 2010): $\hat y_{u,j} = \langle \mathbf{v}_u, \mathbf{v}_j\rangle + \langle \mathbf{v}_{i_t}, \mathbf{v}'_j\rangle$: MF + transición desde el último ítem. Memoria de 1 paso.
- **GRU4Rec** (Hidasi et al., 2016): $\mathbf{h}_t = \mathrm{GRU}(\mathbf{h}_{t-1}, \mathbf{e}_{i_t})$. Memoria comprimida en un vector; nacido para **sesiones**.
- **Caser** (Tang & Wang, 2018): convoluciones horizontales/verticales sobre la «imagen» de los últimos $L$ embeddings.
- **SASRec** (Kang & McAuley, 2018): auto-atención **causal**; cada posición mira a todas las anteriores.
- **BERT4Rec** (Sun et al., 2019): atención **bidireccional** + objetivo *Cloze* (enmascarar y reconstruir).

### 2.3 Funciones de pérdida (aquí está la mitad del rendimiento)
Sea $s_j = \mathbf{h}_t^\top\mathbf{e}_j$ el *logit* del ítem $j$ y $i^+$ el ítem siguiente real.

| Pérdida | Fórmula (por posición) | Coste | Usada por |
|---|---|---|---|
| **Full softmax CE** | $-s_{i^+} + \log\sum_{k\in\mathcal{I}} e^{s_k}$ | $O(Nd)$ | BERT4Rec, SASRec+ |
| **Sampled softmax** | $-s_{i^+} + \log\big(e^{s_{i^+}} + \sum_{j\in\mathcal{N}} e^{s_j - \log Q(j)}\big)$ | $O(kd)$ | YouTube, HSTU |
| **BCE con negativos** | $-\log\sigma(s_{i^+}) - \sum_{j\in\mathcal{N}}\log(1-\sigma(s_j))$ | $O(kd)$ | SASRec original ($k=1$) |
| **gBCE** | $-\beta\log\sigma(s_{i^+}) - \sum_{j\in\mathcal{N}}\log(1-\sigma(s_j))$ | $O(kd)$ | gSASRec |

$\mathcal{N}$: $k$ negativos muestreados; $Q(j)$: probabilidad de muestrear $j$ (corrección logQ, visto en el módulo 08; con muestreo uniforme es constante y se cancela).
""")

nb.md(r"""
### 2.4 📐 Derivación: por qué la BCE con negativos es **sobreconfiada** (gSASRec)

Fijemos un estado $\mathbf{h}$ y un ítem $j$ cuya probabilidad real de ser el siguiente es $p$.
Con $k$ negativos uniformes de un catálogo de $N$ ítems, $j$ aparece como negativo con probabilidad $\approx \alpha = \frac{k}{N-1}$ (la **tasa de muestreo**).
Llamemos $q = \sigma(s_j)$ a la probabilidad que predice el modelo. La pérdida esperada para ese ítem, con la gBCE de parámetro $\beta$, es:
$$\mathcal{L}(q) = -\,p\,\beta\log q \;-\; \alpha(1-p)\log(1-q).$$
Derivando e igualando a cero:
$$\frac{\partial \mathcal{L}}{\partial q} = -\frac{p\beta}{q} + \frac{\alpha(1-p)}{1-q} = 0 \;\;\Longrightarrow\;\; q^\star = \frac{\beta p}{\beta p + \alpha(1-p)}.$$

- **BCE clásica** ($\beta = 1$): $q^\star = \frac{p}{p + \alpha(1-p)}$. Si $\alpha$ es diminuto (1 negativo entre 3.700 ítems → $\alpha\approx 2.7\cdot10^{-4}$), cualquier ítem con $p \gg \alpha$ obtiene $q^\star \approx 1$: **todos los ítems «buenos» saturan** y el modelo no sabe ordenarlos entre sí en el top. Esa es la **sobreconfianza**.
- **gBCE con $\beta = \alpha$**: $q^\star = \frac{\alpha p}{\alpha p + \alpha(1-p)} = p$ → **calibrado**.

Petrov & Macdonald parametrizan $\beta$ con una «temperatura de calibración» $t \in [0, 1]$:
$$\beta = \alpha\left(t\left(1 - \tfrac{1}{\alpha}\right) + \tfrac{1}{\alpha}\right) \qquad (t=0 \Rightarrow \beta=1 \text{ BCE};\;\; t=1 \Rightarrow \beta=\alpha \text{ calibrado}).$$
Recomiendan $t \in [0.75, 0.9]$ y **128–256 negativos**. Así gSASRec iguala o supera a BERT4Rec entrenando bastante más rápido.
""")

nb.code(r"""
# 📊 Gráfico 3 — Sobreconfianza: probabilidad predicha óptima q* vs probabilidad real p
def q_star(p, alpha, beta=1.0):
    return beta * p / (beta * p + alpha * (1 - p))

def beta_gbce(alpha, t):
    return alpha * (t * (1 - 1 / alpha) + 1 / alpha)

N = n_items; p = np.logspace(-5, 0, 400)
fig, ax = plt.subplots(1, 2, figsize=(13, 4.2))
for k, t, c in [(1, 0.0, "#ef4444"), (min(256, N - 1), 0.0, "#f59e0b"), (min(256, N - 1), 0.75, "#3b82f6"), (min(256, N - 1), 1.0, "#10b981")]:
    a = k / (N - 1); b = 1.0 if t == 0 else beta_gbce(a, t)
    lbl = f"BCE, k={k}" if t == 0 else f"gBCE, k={k}, t={t}"
    ax[0].plot(p, q_star(p, a, b), c=c, lw=2, label=lbl)
ax[0].plot(p, p, "k--", lw=1, label="calibrado (q* = p)")
ax[0].set(xscale="log", yscale="log", xlabel="probabilidad real p", ylabel="probabilidad predicha q*",
          title=f"Sobreconfianza por muestreo de negativos (N = {N:,})")
ax[0].legend(fontsize=8)
ts = np.linspace(0, 1, 101)
for k in [1, 16, 64, 256]:
    a = min(k, N - 1) / (N - 1)
    ax[1].plot(ts, [beta_gbce(a, t) for t in ts], lw=2, label=f"k = {k}  (α = {a:.1e})")
ax[1].set(yscale="log", xlabel="t (calibración)", ylabel="β", title="β de gBCE en función de t")
ax[1].legend(fontsize=8); plt.tight_layout(); plt.show()
""")

# ---------------- GRU4Rec
nb.md(r"""
## 🛠️ 3. Implementación desde cero

Todos los modelos comparten una **interfaz común**, lo que nos permite reutilizar el bucle de entrenamiento y la evaluación:
- `model.encode(seq) -> h` con `seq` de forma `[B, L]` (padding a la **izquierda**, 0 = vacío) y `h` de forma `[B, L, d]`.
- `model.item_emb`: tabla de *embeddings* de ítems, reutilizada como capa de salida (*weight tying*). El índice `n_items+1` se reserva para el token `[MASK]` de BERT4Rec.
- La puntuación de todos los ítems para el último estado es `h[:, -1] @ item_emb.weight.T`.

### 3.1 GRU4Rec (Hidasi et al., ICLR 2016)
El primer modelo profundo para recomendación por sesión. Las ecuaciones del GRU (que ya conoces de NLP):
$$\mathbf{z}_t = \sigma(W_z\mathbf{x}_t + U_z\mathbf{h}_{t-1}),\quad \mathbf{r}_t = \sigma(W_r\mathbf{x}_t + U_r\mathbf{h}_{t-1}),$$
$$\tilde{\mathbf{h}}_t = \tanh(W\mathbf{x}_t + U(\mathbf{r}_t\odot\mathbf{h}_{t-1})),\quad \mathbf{h}_t = (1-\mathbf{z}_t)\odot\mathbf{h}_{t-1} + \mathbf{z}_t\odot\tilde{\mathbf{h}}_t.$$

⚠️ **Simplificación consciente.** El GRU4Rec oficial usa *session-parallel mini-batches*, pérdidas *BPR-max*/*TOP1-max* y negativos compartidos en el *mini-batch* con muestreo por popularidad.
Aquí lo entrenamos con el mismo bucle que SASRec (todas las posiciones, CE completa) para aislar el efecto de la arquitectura.
Hidasi & Czapp (RecSys 2023) demostraron que muchas re-implementaciones de terceros de GRU4Rec rinden muchísimo peor que la oficial: si publicas una comparación, usa la implementación oficial.
""")

nb.code(r"""
# 📊 Diagrama 4 — GRU4Rec desenrollado en el tiempo
fig, ax = plt.subplots(figsize=(11, 3.8)); blank(ax, (0, 11), (0, 4.2))
for t in range(4):
    x = 0.6 + t * 2.6
    box(ax, x, 0.2, 1.6, 0.6, f"ítem $i_{t+1}$", fc="#f1f5f9")
    box(ax, x, 1.2, 1.6, 0.6, "embedding", fc="#e0f2fe")
    box(ax, x, 2.2, 1.6, 0.7, "GRU", fc="#c7d2fe", weight="bold")
    box(ax, x, 3.3, 1.6, 0.6, f"softmax → $i_{t+2}$", fc="#fde68a")
    arrow(ax, x + 0.8, 0.8, x + 0.8, 1.2); arrow(ax, x + 0.8, 1.8, x + 0.8, 2.2); arrow(ax, x + 0.8, 2.9, x + 0.8, 3.3)
    if t < 3:
        arrow(ax, x + 1.6, 2.55, x + 2.6, 2.55, color="#4338ca", lw=2)
        ax.text(x + 2.1, 2.7, "$h_t$", ha="center", fontsize=9, color="#4338ca")
ax.set_title("GRU4Rec: el estado oculto $h_t$ resume toda la historia en un único vector", fontsize=10)
plt.show()
""")

nb.code(MODELS)

# ---------------- SASRec
nb.md(r"""
### 3.2 SASRec (Kang & McAuley, ICDM 2018)

Sustituye el GRU por **auto-atención causal**. Para la posición $t$:
$$\mathrm{Attn}(Q,K,V) = \mathrm{softmax}\!\left(\frac{QK^\top}{\sqrt{d_k}} + M\right)V,\qquad M_{ts} = \begin{cases}0 & s \le t \\ -\infty & s > t\end{cases}$$
- $Q = XW_Q,\; K = XW_K,\; V = XW_V$ con $X$ = *embeddings* de ítem + *embeddings* de posición.
- $M$ es la **máscara causal**: la posición $t$ no puede «ver el futuro» (si no, el entrenamiento sería trivial: copiar la respuesta).
- Bloques *pre-LayerNorm* con FFN y conexiones residuales, como en GPT-2.

Ventajas frente al GRU: (1) cada predicción accede **directamente** a cualquier ítem anterior (sin cuello de botella de un vector), (2) entrenamiento **paralelo** en la secuencia, (3) la atención es **interpretable**.

Detalles de implementación que importan:
- **Padding a la izquierda** y posición absoluta dentro de la ventana: el último ítem real siempre está en la posición `L-1` (equivale a la *inverse positional encoding* de RecTools).
- Bloqueamos la atención **hacia** posiciones de padding y dejamos la diagonal libre para que ninguna fila quede a $-\infty$ (evita `NaN`).
""")

nb.code(r"""
# 📊 Diagrama 5 — Arquitectura SASRec
fig, ax = plt.subplots(figsize=(11, 5.4)); blank(ax, (0, 11), (0, 6))
items = ["$i_1$", "$i_2$", "$i_3$", "$i_4$"]
for j, it in enumerate(items):
    x = 1.0 + j * 2.0
    box(ax, x, 0.2, 1.4, 0.5, it, fc="#f1f5f9")
    box(ax, x, 0.95, 1.4, 0.5, "emb + pos", fc="#e0f2fe", fs=8)
    arrow(ax, x + 0.7, 0.7, x + 0.7, 0.95)
    box(ax, x, 4.4, 1.4, 0.5, f"$h_{j+1}$", fc="#c7d2fe")
    box(ax, x, 5.25, 1.4, 0.5, f"→ {['$i_2$','$i_3$','$i_4$','$i_5$'][j]}", fc="#fde68a", fs=9)
    arrow(ax, x + 0.7, 4.9, x + 0.7, 5.25)
box(ax, 0.8, 1.8, 7.8, 2.2, "", fc="#eef2ff", ec="#6366f1")
ax.text(4.7, 3.7, "× L bloques Transformer (pre-LN)", ha="center", fontsize=9, weight="bold", color="#4338ca")
box(ax, 1.2, 2.9, 7.0, 0.55, "Multi-Head Self-Attention CAUSAL  (máscara triangular)", fc="#ddd6fe", fs=9)
box(ax, 1.2, 2.05, 7.0, 0.55, "Feed-Forward (d → 4d → d) + residual + LayerNorm", fc="#ddd6fe", fs=9)
for j in range(4):
    x = 1.7 + j * 2.0
    arrow(ax, x, 1.45, x, 2.05); arrow(ax, x, 3.45, x, 4.4)
for j in range(1, 4):                       # flechas de atención hacia el pasado
    for s in range(j):
        ax.annotate("", xy=(1.7 + s * 2.0, 3.47), xytext=(1.7 + j * 2.0, 3.47),
                    arrowprops=dict(arrowstyle="->", color="#a855f7", lw=0.8, connectionstyle="arc3,rad=0.35"))
box(ax, 9.0, 2.3, 1.8, 1.4, "Salida:\n$h_t^\\top E^\\top$\n(weight tying)", fc="#fef3c7", fs=8)
ax.set_title("SASRec: cada posición atiende sólo a las anteriores y predice el siguiente ítem", fontsize=10)
plt.show()
""")

nb.code(SASREC)

nb.code(r"""
# 📊 Gráfico 6 — Máscaras de atención: causal (SASRec), bidireccional (BERT4Rec) y efecto del padding
toy = torch.tensor([[0, 0, 5, 9, 2, 7, 3, 8]])
fig, ax = plt.subplots(1, 3, figsize=(13, 3.8))
for a, (causal, title) in zip(ax, [(True, "SASRec (causal)"), (False, "BERT4Rec (bidireccional)")]):
    allowed = (~attention_block_mask(toy, causal))[0, 0].int().numpy()
    sns.heatmap(allowed, ax=a, cbar=False, cmap="Blues", linewidths=0.5, linecolor="white",
                xticklabels=toy[0].tolist(), yticklabels=toy[0].tolist())
    a.set(title=title + "\n(1 = puede atender)", xlabel="clave (posición atendida)", ylabel="consulta")
causal_only = np.tril(np.ones((8, 8)))
sns.heatmap(causal_only, ax=ax[2], cbar=False, cmap="Greens", linewidths=0.5, linecolor="white")
ax[2].set(title="Máscara causal «pura» (sin padding)", xlabel="clave", ylabel="consulta")
plt.tight_layout(); plt.show()
""")

nb.md(r"""
### 3.3 Las cuatro pérdidas en código
Fíjate en cómo **la misma red** se entrena con cuatro objetivos distintos cambiando una sola línea.

🧠 **Truco que no viene en los papers (y que nos costó descubrir):** con BCE/gBCE y muchos negativos, al principio casi toda la señal dice «baja todas las puntuaciones»
(hay $k$ negativos por cada positivo). Con *weight tying*, la red lo consigue añadiendo una componente común a **todos** los embeddings, se queda atascada en la solución
«puntuación constante» ($q = \beta/(\beta+k)$ para todo ítem) y el NDCG no despega. La solución es sumar a los logits un **offset fijo** $b_0 = \log(\beta/k)$ (el logit de esa tasa base):
el ranking no cambia (es la misma constante para todos los ítems) y la red ya no necesita deformar los embeddings para aprender la tasa base.
Es la misma idea que la inicialización del sesgo con la *prior* de clase en RetinaNet (Lin et al., 2017).
Para no disparar la memoria con 256 negativos, compartimos los negativos entre todas las posiciones de una secuencia (tensor `[B, L, k]` en vez de `[B, L, k, d]`).
""")
nb.code(LOSSES)
nb.code(r"""
# Prueba rápida: las cuatro pérdidas sobre un modelo sin entrenar (deben ser finitas y del orden esperado)
_m = SASRec(n_items, d=32, n_layers=1, n_heads=1, maxlen=20).to(device)
_inp = pad_left([s[:-1] for s in train_seqs[:4]], 20).to(device)
_tgt = pad_left([s[1:] for s in train_seqs[:4]], 20).to(device)
_h = _m.encode(_inp)
for name in ["ce", "sampled_ce", "bce", "gbce"]:
    print(f"{name:11s} -> {seq_loss(_m, _h, _tgt, name, n_neg=min(256, n_items - 1)).item():.3f}")
print("log(N) =", round(math.log(n_items), 3), "(valor esperado de la CE con un modelo aleatorio)")
""")

nb.md(r"""
### 3.4 Bucle de entrenamiento común + BERT4Rec

**BERT4Rec** (Sun et al., CIKM 2019) usa el mismo *encoder* pero **sin máscara causal** y con objetivo *Cloze*:
se reemplaza aleatoriamente un ~20 % de los ítems por `[MASK]` y se predice el original con *full softmax*.
En inferencia se añade `[MASK]` al final del historial y se lee su salida.

Un matiz importante (Petrov & Macdonald, RecSys 2022): BERT4Rec necesita **muchas** más épocas que SASRec para converger;
muchas comparaciones «BERT4Rec pierde» se debían a entrenarlo poco. Aquí le damos el **mismo presupuesto de épocas** a todos — tenlo en cuenta al leer los resultados.
""")
nb.code(TRAIN)

# ---------------- Experimentos
nb.md(r"""
## 🧪 4. Experimentos: GRU4Rec vs SASRec (BCE, gBCE, CE) vs BERT4Rec

Mismo *split* (leave-one-out), misma longitud máxima (200), mismo tamaño ($d=64$, 2 capas, 2 cabezas), mismas épocas.
Selección por NDCG@10 en validación (2.000 usuarios) y número final en **test con todos los usuarios**.

⏱️ En L4 cada modelo tarda ~1–3 min en modo completo. Valores de referencia en ML-1M (leave-one-out, *full ranking*) del repositorio oficial de HSTU:
SASRec con *sampled softmax* HR@10 ≈ 0,285 y NDCG@10 ≈ 0,160. Con CE completa y más épocas se llega más lejos (SASRec+ en Klenitskiy & Vasilev 2023).
""")

nb.code(r"""
MAXLEN = 200
CFG = dict(epochs=4 if FAST_DEV_RUN else 100, maxlen=MAXLEN, batch_size=128, lr=1e-3,
           eval_every=1 if FAST_DEV_RUN else 10)
ARCH = dict(d=64, n_layers=2, n_heads=2, maxlen=MAXLEN, dropout=0.2)
N_NEG = min(256, n_items - 1)
results, histories, models = {}, {}, {}

def run(name, model, **kw):
    torch.manual_seed(seed); np.random.seed(seed)
    histories[name] = train_seq_model(model, train_seqs, valid, name=name, **{**CFG, **kw})
    bert = kw.get("bert", False)
    results[name] = evaluate_next_item(make_score_fn(model, MAXLEN, bert), *test, ks=(10, 20))
    results[name]["train_time_s"] = histories[name]["train_time_s"]
    models[name] = model
    print(name, {k: round(v, 4) for k, v in results[name].items()})
""")

nb.code(r"""
torch.manual_seed(seed)
run("GRU4Rec (CE)", GRU4Rec(n_items, d=64, hidden=128), loss="ce")
""")
nb.code(r"""
torch.manual_seed(seed)
run("SASRec (BCE, 1 neg)", SASRec(n_items, **ARCH), loss="bce", n_neg=1)
""")
nb.code(r"""
torch.manual_seed(seed)
run(f"gSASRec (gBCE, {N_NEG} neg, t=0.75)", SASRec(n_items, **ARCH), loss="gbce", n_neg=N_NEG, gbce_t=0.75)
""")
nb.code(r"""
torch.manual_seed(seed)
run("SASRec+ (CE completa)", SASRec(n_items, **ARCH), loss="ce")
""")
nb.code(r"""
torch.manual_seed(seed)
run("BERT4Rec (Cloze, CE)", SASRec(n_items, **{**ARCH, "causal": False}), bert=True, mask_prob=0.2)
""")

nb.code(r"""
# 📊 Gráfico 7 — Curvas de entrenamiento (pérdida no comparable entre objetivos; NDCG sí)
fig, ax = plt.subplots(1, 2, figsize=(13, 4))
for name, h in histories.items():
    ax[0].plot(h["epoch"], h["val_NDCG@10"], marker="o", ms=3, label=name)
    ax[1].plot(h["epoch"], np.array(h["loss"]) / h["loss"][0], marker="o", ms=3, label=name)
ax[0].set(title="NDCG@10 en validación", xlabel="época", ylabel="NDCG@10"); ax[0].legend(fontsize=8)
ax[1].set(title="Pérdida de entrenamiento (normalizada a la 1ª evaluación)", xlabel="época", ylabel="loss / loss₀")
plt.tight_layout(); plt.show()
""")

nb.code(r"""
# 📊 Gráfico 8 — Comparación final en test (+ baselines)
res = pd.DataFrame(results).T
for bname, fn in [("Popularidad", pop_score), ("Markov 1er orden", markov_score_fn(fit_markov([s[:-1] for s in seqs], n_items)))]:
    res.loc[bname, ["HR@10", "NDCG@10", "HR@20", "NDCG@20"]] = pd.Series(evaluate_next_item(fn, *test, ks=(10, 20)))
res = res.sort_values("NDCG@10")
display(res.round(4))
fig, ax = plt.subplots(1, 2, figsize=(13, 4))
res["NDCG@10"].plot.barh(ax=ax[0], color="#6366f1"); ax[0].set(title="Test NDCG@10 (full ranking)", xlabel="NDCG@10")
res["train_time_s"].dropna().plot.barh(ax=ax[1], color="#f59e0b"); ax[1].set(title="Tiempo de entrenamiento", xlabel="segundos")
plt.tight_layout(); plt.show()
""")

nb.md(r"""
### 🧪 4.1 Barrido de negativos: BCE vs gBCE
La predicción de la teoría: con **pocos negativos** α es diminuto, la BCE está muy sobreconfiada y gBCE aplica la corrección más fuerte (β ≪ 1), así que la ventaja de gBCE debería ser **máxima con k pequeño**.
Al **aumentar k** ambas mejoran (más señal negativa por paso) y la diferencia se reduce, pero la BCE no llega a la CE completa.
Lo comprobamos empíricamente (es el experimento central de gSASRec). Pon `RUN_NEG_SWEEP = False` si vas justo de cómputo (~8 entrenamientos).
""")
nb.code(r"""
RUN_NEG_SWEEP = True
sweep = []
if RUN_NEG_SWEEP:
    ks_neg = [1, 4, 16] if FAST_DEV_RUN else [1, 16, 64, 256]
    for k in ks_neg:
        k = min(k, n_items - 1)
        for loss in ["bce", "gbce"]:
            torch.manual_seed(seed)
            m = SASRec(n_items, **ARCH)
            train_seq_model(m, train_seqs, valid, loss=loss, n_neg=k, gbce_t=0.75, name=f"{loss}-k{k}",
                            **{**CFG, "eval_every": CFG["epochs"]})
            r = evaluate_next_item(make_score_fn(m, MAXLEN), *valid, ks=(10,))
            sweep.append({"k": k, "loss": loss.upper(), "NDCG@10": r["NDCG@10"]})
    sw = pd.DataFrame(sweep)
    fig, ax = plt.subplots(figsize=(7, 3.8))
    for loss, g in sw.groupby("loss"):
        ax.plot(g["k"], g["NDCG@10"], marker="o", lw=2, label=loss)
    if "SASRec+ (CE completa)" in results:
        ax.axhline(results["SASRec+ (CE completa)"]["NDCG@10"], ls="--", c="k", label="CE completa (test)")
    ax.set(xscale="log", xlabel="nº de negativos k", ylabel="NDCG@10 (validación)", title="BCE vs gBCE según nº de negativos")
    ax.legend(); plt.show()
""")

nb.code(r"""
# 📊 Gráfico 9 — Mapas de atención de SASRec+ sobre un usuario real (últimos 25 ítems)
m = models["SASRec+ (CE completa)"]; m.eval()
u = int(np.argmax([len(h) for h in test[0]][:500]))
hist_u = test[0][u][-25:]
for b in m.blocks: b.attn.keep_attn = True
with torch.no_grad():
    m.encode(pad_left([hist_u], len(hist_u)).to(device))
labels = [idx_title(i)[:22] for i in hist_u]
fig, ax = plt.subplots(1, len(m.blocks), figsize=(7 * len(m.blocks), 6.5))
ax = np.atleast_1d(ax)
for l, b in enumerate(m.blocks):
    A = b.attn.last_attn[0].mean(0).numpy()            # media sobre cabezas
    sns.heatmap(A, ax=ax[l], cmap="magma", xticklabels=labels, yticklabels=labels, cbar=l == len(m.blocks) - 1)
    ax[l].set_title(f"Capa {l+1}: atención causal (media de cabezas)")
    ax[l].tick_params(labelsize=6)
    b.attn.keep_attn = False
plt.tight_layout(); plt.show()
print("Recomendación top-5 para este usuario:",
      [idx_title(int(i)) for i in make_score_fn(m, MAXLEN)([test[0][u]])[0].topk(5).indices])
""")

nb.md(r"""
**Cómo leerlo.** Cada fila es una consulta (posición $t$); las columnas son los ítems pasados a los que atiende. El triángulo superior es negro por la máscara causal.
Suele verse (a) atención fuerte a los **ítems más recientes** (diagonal), (b) columnas «verticales» = ítems que muchas posiciones consultan (anclas del gusto del usuario) y (c) en capas altas, patrones más difusos.
⚠️ La atención **no es una explicación causal** del modelo (Jain & Wallace, 2019): úsala para depurar, no para justificar ante negocio.
""")

nb.code(r"""
# 📊 Gráfico 10 — t-SNE de los embeddings de ítems de SASRec+ (coloreados por género principal)
from sklearn.manifold import TSNE
top = np.argsort(-pop[1:])[:1500] + 1
E = models["SASRec+ (CE completa)"].item_emb.weight[top].detach().float().cpu().numpy()
Z = TSNE(n_components=2, init="pca", perplexity=30, random_state=seed).fit_transform(E)
g = pd.Series([genre_of.get(int(idx2item[i]), "?") for i in top])
main = g.value_counts().index[:8]
fig, ax = plt.subplots(figsize=(8.5, 6.5))
for gg in main:
    msk = (g == gg).values
    ax.scatter(Z[msk, 0], Z[msk, 1], s=8, alpha=0.7, label=gg)
ax.scatter(Z[~g.isin(main).values, 0], Z[~g.isin(main).values, 1], s=5, c="lightgray", alpha=0.4, label="otros")
ax.set(title="t-SNE de embeddings de ítems (SASRec+, 1.500 más populares)", xticks=[], yticks=[]); ax.legend(fontsize=8, markerscale=2)
plt.show()
""")

# ---------------- Sesiones
nb.md(r"""
## 🛒 5. Recomendación por sesión: RetailRocket

En muchos e-commerce el usuario **no está logueado**: sólo tenemos los clics de la sesión actual. El mismo código sirve (las sesiones son secuencias), pero cambian cosas importantes:
- Secuencias **cortas** (mediana de 2–4 eventos) → la arquitectura importa menos; los *baselines* simples (Markov, SKNN) son durísimos de batir (Ludewig & Jannach, 2018).
- Las **repeticiones** son frecuentes (vuelves a mirar el mismo producto): *no* hay que enmascarar los ítems ya vistos.
- El *split* es **temporal** (últimos días como test), nunca aleatorio.

Dataset: **RetailRocket** (Kaggle, `retailrocket/ecommerce-dataset`, fichero `events.csv`: ~2,7 M vistas, *add-to-cart* y transacciones de 4,5 meses).
Para descargarlo necesitas la API de Kaggle: sube `kaggle.json` (Kaggle → *Settings* → *Create New Token*) a `~/.kaggle/` con permisos 600.
Si no está disponible, el notebook genera sesiones sintéticas. Alternativas clásicas: **Yoochoose** (RecSys Challenge 2015) y **Diginetica** (CIKM Cup 2016).
""")

nb.code(r"""
def load_retailrocket(data_dir="data/retailrocket"):
    path = os.path.join(data_dir, "events.csv")
    if not os.path.exists(path):
        os.makedirs(data_dir, exist_ok=True)
        try:
            subprocess.run(["kaggle", "datasets", "download", "-d", "retailrocket/ecommerce-dataset",
                            "-p", data_dir, "--unzip", "-q"], check=True, timeout=600)
        except Exception as e:
            print(f"⚠️ Kaggle no disponible ({type(e).__name__}). Uso sesiones SINTÉTICAS.")
    if os.path.exists(path):
        ev = pd.read_csv(path)
        ev = ev[ev["event"] == "view"].rename(columns={"visitorid": "user", "itemid": "item", "timestamp": "ts"})
        ev["ts"] = ev["ts"] // 1000
        return ev[["user", "item", "ts"]]
    return make_synthetic_sessions()

def make_synthetic_sessions(n_sessions=20000, n_items=900, seed=7):
    '''Sesiones anónimas de juguete: clics cada 10–300 s, sesiones separadas por días, transiciones locales.'''
    rng = np.random.default_rng(seed); rows = []; t = 1_430_000_000
    pop = np.minimum(rng.zipf(1.4, n_items), 60).astype(float); pop /= pop.sum()
    for sid in range(n_sessions):
        t += int(rng.integers(600, 4 * 3600)); it = int(rng.choice(n_items, p=pop))
        for _ in range(1 + int(rng.geometric(0.3))):
            rows.append((sid, it, t)); t += int(rng.integers(10, 300))
            it = (it + int(rng.integers(1, 4))) % n_items if rng.random() < 0.6 else int(rng.choice(n_items, p=pop))
    return pd.DataFrame(rows, columns=["user", "item", "ts"])

def sessionize(ev, gap_s=1800, min_item_supp=5, min_len=2):
    ev = ev.sort_values(["user", "ts"], kind="mergesort")
    new = (ev["user"].diff() != 0) | (ev["ts"].diff() > gap_s)            # 30 min de inactividad => nueva sesión
    ev = ev.assign(session=new.cumsum())
    ev = ev[(ev["item"] != ev.groupby("session")["item"].shift())]        # quita recargas consecutivas del mismo ítem
    for _ in range(2):                                                    # filtrado iterativo
        ev = ev[ev.groupby("item")["item"].transform("size") >= min_item_supp]
        ev = ev[ev.groupby("session")["item"].transform("size") >= min_len]
    return ev

ev = sessionize(load_retailrocket())
t_split = ev.groupby("session")["ts"].min().quantile(0.9)                 # último 10 % del tiempo => test
s_start = ev.groupby("session")["ts"].transform("min")
tr_ev, te_ev = ev[s_start < t_split], ev[s_start >= t_split]
s_items = {int(it): i + 1 for i, it in enumerate(np.sort(tr_ev["item"].unique()))}
to_seq = lambda d: [[s_items[x] for x in g if x in s_items] for g in d.groupby("session")["item"].apply(list)]
sess_train = [s for s in to_seq(tr_ev) if len(s) >= 2]
sess_test = [s for s in to_seq(te_ev) if len(s) >= 2]
n_sess_items = len(s_items)
print(f"sesiones train={len(sess_train):,}  test={len(sess_test):,}  ítems={n_sess_items:,}  "
      f"long. mediana={np.median([len(s) for s in sess_train]):.0f}")
""")

nb.code(r"""
# Entrenamos GRU4Rec y SASRec sobre sesiones y comparamos con Markov/popularidad (predecir el último clic)
S_MAXLEN = 50
s_hist, s_tgt = [s[:-1] for s in sess_test], [s[-1] for s in sess_test]
s_cfg = dict(epochs=2 if FAST_DEV_RUN else 15, maxlen=S_MAXLEN, batch_size=256, lr=1e-3,
             eval_every=1 if FAST_DEV_RUN else 5, loss="ce")
s_val = (s_hist[:2000], s_tgt[:2000])
sess_res = {}
for name, mdl in [("GRU4Rec", GRU4Rec(n_sess_items, d=64, hidden=128)),
                  ("SASRec+", SASRec(n_sess_items, d=64, n_layers=2, n_heads=2, maxlen=S_MAXLEN))]:
    torch.manual_seed(seed)
    train_seq_model(mdl, sess_train, s_val, name=f"sesión-{name}", **s_cfg)
    sess_res[name] = evaluate_next_item(make_score_fn(mdl, S_MAXLEN), s_hist, s_tgt, ks=(20,), mask_history=False)
M_s = fit_markov(sess_train, n_sess_items)
pop_s = np.bincount(np.concatenate(sess_train), minlength=n_sess_items + 1).astype(np.float32)
sess_res["Markov"] = evaluate_next_item(lambda H: torch.from_numpy(M_s[[h[-1] for h in H]].toarray() + 1e-3 * pop_s / pop_s.sum()),
                                        s_hist, s_tgt, ks=(20,), mask_history=False)
sess_res["Popularidad"] = evaluate_next_item(lambda H: torch.from_numpy(np.tile(pop_s, (len(H), 1))), s_hist, s_tgt,
                                             ks=(20,), mask_history=False)
sr = pd.DataFrame(sess_res).T.sort_values("NDCG@20"); display(sr.round(4))
fig, ax = plt.subplots(1, 2, figsize=(12, 3.5))
ax[0].hist([len(s) for s in sess_train], bins=np.arange(2, 40), color="#0ea5e9"); ax[0].set_yscale("log")
ax[0].set(title="Longitud de sesión (train)", xlabel="eventos", ylabel="sesiones (log)")
sr["HR@20"].plot.barh(ax=ax[1], color="#14b8a6"); ax[1].set(title="Sesiones: HR@20 (predecir el último clic)")
plt.tight_layout(); plt.show()
""")

# ---------------- Librería
nb.md(r"""
## 🏗️ 6. Librerías de industria: RecTools (MTS)

En producción rara vez se mantiene un SASRec escrito a mano. Opciones reales:
- **RecTools** (MTS, Rusia): SASRec, BERT4Rec y HSTU en PyTorch Lightning con pérdidas `softmax`, `BCE`, `gBCE` y `sampled_softmax`. API muy simple sobre *dataframes*.
- **NVIDIA Transformers4Rec** (Moreira et al., RecSys 2021): integra Hugging Face Transformers (XLNet, GPT-2…) con el ecosistema Merlin para *session-based* a escala GPU.
- **RecBole** (RUC): +90 modelos, ideal para *benchmarks* (cuidado con su evaluación por defecto).
- **Meta generative-recommenders**: HSTU y SASRec de referencia (lo veremos en el módulo 11).

Comparamos el SASRec de RecTools (CE completa = `loss="softmax"`) con el nuestro. RecTools entrena sobre $s_{:-1}$ (incluye el ítem de validación), así que puede salir ligeramente mejor.
""")
nb.code(r"""
try:
    from rectools import Columns
    from rectools.dataset import Dataset as RTDataset
    from rectools.models import SASRecModel
    rows = [(u, it, 1.0, t) for u, h in enumerate(test[0]) for t, it in enumerate(h)]
    df_rt = pd.DataFrame(rows, columns=[Columns.User, Columns.Item, Columns.Weight, Columns.Datetime])
    df_rt[Columns.Datetime] = pd.to_datetime(df_rt[Columns.Datetime], unit="s")   # sólo importa el orden
    rt_model = SASRecModel(n_factors=64, n_blocks=2, n_heads=2, session_max_len=MAXLEN, loss="softmax",
                           dropout_rate=0.2, epochs=3 if FAST_DEV_RUN else 100, lr=1e-3, batch_size=128, verbose=0)
    t0 = time.time(); rt_model.fit(RTDataset.construct(df_rt))
    reco = rt_model.recommend(users=np.arange(len(test[0])), dataset=RTDataset.construct(df_rt), k=20, filter_viewed=True)
    tgt = pd.Series(test[1], name="target")
    hit = reco.merge(tgt.rename_axis(Columns.User).reset_index(), on=Columns.User)
    hit = hit[hit[Columns.Item] == hit["target"]]
    r10 = hit[hit[Columns.Rank] <= 10]
    results["RecTools SASRec (softmax)"] = {"HR@10": len(r10) / len(tgt), "NDCG@10": float((1 / np.log2(r10[Columns.Rank] + 1)).sum() / len(tgt)),
                                            "train_time_s": time.time() - t0}
    print(results["RecTools SASRec (softmax)"])
except Exception as e:
    print("RecTools no disponible en este entorno:", type(e).__name__, e)
""")

# ---------------- Producción
nb.md(r"""
## 🏭 7. En producción

| Empresa | Sistema | Idea clave | Referencia |
|---|---|---|---|
| **Alibaba (Taobao)** | BST — Behavior Sequence Transformer | Transformer sobre los últimos clics como *feature* del *ranker* CTR | Chen et al., 2019 (arXiv:1905.06874) |
| **Alibaba** | SIM — Search-based Interest Model | Historias de **decenas de miles** de eventos: primero *buscar* los relevantes al candidato, luego atención | Pi et al., CIKM 2020 (arXiv:2006.05639) |
| **Kuaishou** | TWIN | Atención sobre historias *lifelong* con la misma métrica de relevancia en las dos etapas | Chang et al., KDD 2023 (arXiv:2302.02352) |
| **Pinterest** | PinnerFormer | Transformer causal entrenado para predecir acciones de los **próximos 14 días** (*dense all-action loss*), se computa en **batch diario** | Pancha et al., KDD 2022 (arXiv:2205.04507) |
| **Meta** | HSTU / Generative Recommenders | Transductor secuencial a escala de billones de parámetros (→ módulo 11) | Zhai et al., ICML 2024 (arXiv:2402.17152) |
| **Netflix** | *Foundation model* de recomendación | Transformer autoregresivo sobre el historial de interacciones de todos los usuarios, predicción multi-token (→ módulo 11) | Netflix Tech Blog, marzo 2025 |

**Trade-offs de serving.**
- *Stateless* (recalcular el *encoder* con todo el historial en cada petición): siempre fresco, caro. Con historias de 1.000+ eventos se necesita *KV-cache* o atención lineal.
- *Stateful/batch* (PinnerFormer): embedding de usuario precalculado (diario) + señales en tiempo real en el *ranker*. Pinterest mostró que entrenar para el **horizonte largo** reduce la pérdida de calidad por no ser real-time.
- El *encoder* secuencial se usa en **retrieval** (embedding de usuario + ANN, como el two-tower del módulo 08) o como *feature* en **ranking** (BST, SIM, TWIN). Son usos distintos con latencias distintas.
""")

nb.md(r"""
## 🧠 8. Secretos de la élite

1. **La pérdida importa más que la arquitectura.** Klenitskiy & Vasilev (RecSys 2023) mostraron que la supuesta superioridad de BERT4Rec sobre SASRec venía de la *full softmax*: SASRec entrenado con CE (SASRec+) supera a BERT4Rec en calidad **y** tiempo. Antes de cambiar de arquitectura, cambia la pérdida.
2. **BCE con 1 negativo es la configuración por defecto… y la peor.** Sobreconfianza (gSASRec, Petrov & Macdonald RecSys 2023). Si el catálogo es enorme y no cabe la softmax completa: *sampled softmax* con logQ, gBCE con 128–256 negativos o SCE (Mezentsev et al., RecSys 2024), que busca negativos «duros» vía MIPS y reduce mucho la memoria frente a la CE completa.
3. **Las métricas muestreadas mienten.** Evaluar contra 100 negativos aleatorios puede **invertir** el orden entre modelos (Krichene & Rendle, KDD 2020). Usa *full ranking* siempre que el catálogo lo permita.
4. **Leave-one-out filtra el futuro.** Con *leave-one-out* el «último ítem» de un usuario de 2003 se predice usando un modelo entrenado con interacciones de 2004 de otros usuarios. Para decisiones de producto usa un **split temporal global** (módulo 01) y compara en ambos.
5. **Re-implementaciones de terceros.** Hidasi & Czapp (RecSys 2023) encontraron implementaciones populares de GRU4Rec con errores que hundían la precisión. Valida tu *baseline* reproduciendo un número publicado antes de compararte con él.
6. **Repeticiones.** En música, *grocery* o sesiones, re-consumir es lo normal: enmascarar lo visto destruye la métrica y el producto. En películas suele convenir enmascarar. Decide por dominio, no por costumbre.
7. **Más negativos > más capas.** En nuestro barrido, pasar de 1 a 256 negativos mueve más el NDCG que duplicar profundidad. Las mejoras de los papers recientes (eSASRec, RecSys 2025) combinan pérdida *sampled softmax* + capas modernas (LiGR) sobre el objetivo de SASRec.
8. **El token de posición y el *padding* son fuentes de bugs silenciosos**: si haces padding a la derecha con posiciones absolutas, el último ítem cae en posiciones distintas por usuario y el modelo rinde peor sin dar error.
""")

nb.md(r"""
## ⚠️ 9. Errores comunes
- **Fugas del futuro** en la máscara (olvidar la máscara causal o atender al padding con información del objetivo) → métricas absurdamente altas.
- Evaluar con **muestreo de 100 negativos** y comparar con papers que usan *full ranking* (o viceversa).
- Calcular el NDCG con **empates pesimistas/optimistas** distintos entre modelos (aquí: optimistas, `rank = #(score > score_obj)`).
- Ordenar por `ts` con un *sort* inestable: en ML-1M hay muchos empates de *timestamp* y el orden cambia entre ejecuciones.
- Entrenar BERT4Rec con las mismas épocas que SASRec y concluir que es peor (necesita muchas más).
- Olvidar que en *session-based* **no** hay usuario: no puedes usar *embeddings* de usuario ni historial previo.
- No fijar semillas ni promediar varias ejecuciones: diferencias < 2–3 % en NDCG@10 en ML-1M suelen ser ruido.
""")

nb.md(r"""
## ✅ 10. Autoevaluación

1. ¿Por qué SASRec necesita una máscara causal y BERT4Rec no? ¿Qué cambia en inferencia?
<details><summary>Respuesta</summary>SASRec se entrena prediciendo el siguiente ítem en cada posición: sin máscara la posición t vería el ítem t+1 (la respuesta). BERT4Rec reconstruye ítems enmascarados y la entrada ya no contiene la respuesta en esa posición, por eso puede atender en ambas direcciones. En inferencia BERT4Rec añade un [MASK] al final y lee su salida; SASRec lee la salida de la última posición real.</details>

2. Con 3.700 ítems y 1 negativo, ¿cuánto vale α? ¿Qué predice la BCE para un ítem con p = 0,01?
<details><summary>Respuesta</summary>α = 1/3699 ≈ 2,7·10⁻⁴. q* = p/(p + α(1−p)) ≈ 0,01/(0,01 + 0,00027) ≈ 0,97: el modelo está casi seguro de un ítem que sólo tiene un 1 % de probabilidad → sobreconfianza.</details>

3. ¿Qué valor de β hace que gBCE esté calibrada y qué valor de t le corresponde?
<details><summary>Respuesta</summary>β = α, que corresponde a t = 1 (β = α(t(1−1/α)+1/α) = α·1 = α). En la práctica se usa t entre 0,75 y 0,9.</details>

4. ¿Por qué la *full softmax* no escala a 100 M de ítems y qué alternativas hay?
<details><summary>Respuesta</summary>El coste por posición es O(N·d) en cómputo y memoria de logits. Alternativas: sampled softmax con corrección logQ, negativos in-batch (módulo 08), gBCE con muchos negativos, SCE (negativos duros por MIPS) o semantic IDs (módulo 11).</details>

5. Un compañero reporta HR@10 = 0,85 en ML-1M con SASRec. ¿Qué sospechas?
<details><summary>Respuesta</summary>Métrica muestreada (100 negativos) en vez de full ranking, o fuga del futuro (máscara causal mal puesta, el objetivo dentro de la entrada). Con full ranking los valores realistas están en torno a 0,3.</details>

6. ¿En qué se diferencia el problema por sesión del secuencial y por qué los *baselines* simples son tan fuertes allí?
<details><summary>Respuesta</summary>No hay identidad de usuario ni historial largo: sólo la sesión actual, típicamente de 2–5 eventos. Con tan poco contexto, las transiciones del último ítem (Markov) o la vecindad de sesiones (SKNN) capturan casi toda la señal.</details>

7. ¿Por qué PinnerFormer entrena para predecir acciones de los próximos días en lugar del siguiente ítem?
<details><summary>Respuesta</summary>Porque el embedding se calcula en batch una vez al día: debe ser útil durante todo el día siguiente, no sólo para la próxima acción. Optimizar el horizonte largo reduce la diferencia con un modelo real-time.</details>
""")

nb.md(r"""
## 📚 11. Referencias

**Papers**
- Rendle, Freudenthaler & Schmidt-Thieme (2010). *Factorizing Personalized Markov Chains for Next-Basket Recommendation* (FPMC). WWW. https://doi.org/10.1145/1772690.1772773
- Hidasi, Karatzoglou, Baltrunas & Tikk (2016). *Session-based Recommendations with Recurrent Neural Networks* (GRU4Rec). ICLR. https://arxiv.org/abs/1511.06939
- Tang & Wang (2018). *Personalized Top-N Sequential Recommendation via Convolutional Sequence Embedding* (Caser). WSDM. https://arxiv.org/abs/1809.07426
- Kang & McAuley (2018). *Self-Attentive Sequential Recommendation* (SASRec). ICDM. https://arxiv.org/abs/1808.09781
- Sun et al. (2019). *BERT4Rec: Sequential Recommendation with Bidirectional Encoder Representations from Transformer*. CIKM. https://arxiv.org/abs/1904.06690
- Ludewig & Jannach (2018). *Evaluation of Session-based Recommendation Algorithms*. UMUAI. https://arxiv.org/abs/1803.09587
- Krichene & Rendle (2020). *On Sampled Metrics for Item Recommendation*. KDD. https://doi.org/10.1145/3394486.3403226
- Petrov & Macdonald (2022). *A Systematic Review and Replicability Study of BERT4Rec for Sequential Recommendation*. RecSys. https://arxiv.org/abs/2207.07483
- Petrov & Macdonald (2023). *gSASRec: Reducing Overconfidence in Sequential Recommendation Trained with Negative Sampling*. RecSys. https://arxiv.org/abs/2308.07192
- Klenitskiy & Vasilev (2023). *Turning Dross Into Gold Loss: is BERT4Rec really better than SASRec?* RecSys. https://arxiv.org/abs/2309.07602
- Hidasi & Czapp (2023). *The Effect of Third Party Implementations on Reproducibility*. RecSys. https://arxiv.org/abs/2307.14956
- Mezentsev, Gusak, Oseledets & Frolov (2024). *Scalable Cross-Entropy Loss for Sequential Recommendations with Large Item Catalogs*. RecSys. https://arxiv.org/abs/2409.18721
- Tikhonovich et al. (2025). *eSASRec: Enhancing Transformer-based Recommendations in a Modular Fashion*. RecSys. https://arxiv.org/abs/2508.06450
- Chen et al. (2019). *Behavior Sequence Transformer for E-commerce Recommendation in Alibaba*. https://arxiv.org/abs/1905.06874
- Pi et al. (2020). *Search-based User Interest Modeling with Lifelong Sequential Behavior Data for CTR Prediction* (SIM). CIKM. https://arxiv.org/abs/2006.05639
- Chang et al. (2023). *TWIN: TWo-stage Interest Network for Lifelong User Behavior Modeling in CTR Prediction at Kuaishou*. KDD. https://arxiv.org/abs/2302.02352
- Pancha, Zhai, Leskovec & Rosenberg (2022). *PinnerFormer: Sequence Modeling for User Representation at Pinterest*. KDD. https://arxiv.org/abs/2205.04507
- Moreira et al. (2021). *Transformers4Rec: Bridging the Gap between NLP and Sequential / Session-Based Recommendation*. RecSys. https://doi.org/10.1145/3460231.3474255
- Jain & Wallace (2019). *Attention is not Explanation*. NAACL. https://arxiv.org/abs/1902.10186

**Código y librerías**
- gSASRec (oficial, PyTorch): https://github.com/asash/gSASRec-pytorch
- GRU4Rec oficial: https://github.com/hidasib/GRU4Rec
- RecTools: https://github.com/MobileTeleSystems/RecTools
- Transformers4Rec: https://github.com/NVIDIA-Merlin/Transformers4Rec
- Meta generative-recommenders (incluye baselines SASRec): https://github.com/meta-recsys/generative-recommenders

**Datasets**: MovieLens-1M (GroupLens), RetailRocket (Kaggle `retailrocket/ecommerce-dataset`), Yoochoose (RecSys Challenge 2015), Diginetica (CIKM Cup 2016).
""")

nb.save(LESSON)

# ---------------------------------------------------------------------------
# PROYECTO
# ---------------------------------------------------------------------------
pj = Notebook("Proyecto 09 · Siguiente película con SASRec", colab_path=PROJECT, gpu=True)
pj.md(f"""
{pj.badge()}

# Proyecto 09 · «Siguiente película» para CineMatch con SASRec en GPU

| | |
|---|---|
| **Nivel** | 🟠 Avanzado |
| **Duración** | 3–4 h |
| **GPU** | L4 recomendada (A100 para los retos extra) |
| **Unidades Colab** | ≈ 2–4 (L4) |
| **Prerrequisitos** | Lección 09 |
""")
pj.md(r"""
## 🏢 Contexto de negocio
Eres ML engineer en **CineMatch**. La fila de la home *«Porque acabas de ver…»* usa hoy un item-kNN estático (módulo 04) y el equipo de producto observa que
**ignora lo que el usuario está viendo esta semana**. Tu misión: construir el modelo de **siguiente película** que alimentará esa fila (y, más adelante, la etapa de *retrieval* del capstone).

Producto te pide una comparación honesta entre un GRU4Rec (barato) y un SASRec (más caro de servir) para decidir qué desplegar.

## 📦 Dataset
**MovieLens-1M** (GroupLens): 6.040 usuarios, ~3.700 películas, 1 M de ratings con *timestamp*. Lo tratamos como feedback implícito ordenado por tiempo.
Protocolo: *leave-one-out* (último ítem = test, penúltimo = validación), *full ranking*, enmascarando lo ya visto.

## ✅ Entregables y rúbrica
| Criterio | Objetivo |
|---|---|
| Popularidad y Markov implementados y evaluados | obligatorio |
| GRU4Rec entrenado (CE) | NDCG@10 test > Markov |
| SASRec entrenado con **CE completa** | **NDCG@10 ≥ 0,15** y HR@10 ≥ 0,27 en test (orientativo, ML-1M real) |
| Comparación BCE(1 neg) vs gBCE vs CE en SASRec | tabla + gráfico + 3 frases de interpretación |
| Intervalo de confianza *bootstrap* del ΔNDCG@10 SASRec − GRU4Rec | IC 95 % reportado |
| Recomendación final a producto (coste vs calidad) | ≤ 10 líneas |
""")
pj.code(r"""
!pip install -q seaborn
""")
pj.code(IMPORTS)
pj.md(UTILS_MD)
pj.code(UTILS_LOAD)
pj.code(UTILS_SEQ)
pj.code(UTILS_EVAL)
pj.code(LOAD_DATA)
pj.md(r"""
## Paso 1 · Baselines (popularidad y Markov)
Implementa dos `score_fn` compatibles con `evaluate_next_item`: reciben una lista de historiales y devuelven un tensor `[B, n_items+1]`.
""")
pj.code(r"""
def popularity_score_fn(train_seqs, n_items):
    # TODO: cuenta apariciones de cada ítem en train y devuelve una función H -> tensor [len(H), n_items+1]
    # Pista: np.bincount(np.concatenate(train_seqs), minlength=n_items+1)
    raise NotImplementedError

def markov_score_fn(train_seqs, n_items, eps=1e-3):
    # TODO: matriz dispersa de transiciones i -> j (consecutivas) y puntuación = fila del último ítem + eps * popularidad
    raise NotImplementedError

print(evaluate_next_item(popularity_score_fn(train_seqs, n_items), *valid))
print(evaluate_next_item(markov_score_fn(train_seqs, n_items), *valid))
""")
pj.md(r"""
## Paso 2 · Modelos
Implementa `GRU4Rec` y `SASRec` con la interfaz `encode(seq) -> [B, L, d]` y atributos `n_items`, `item_emb` (tamaño `n_items + 2`, 0 = padding).
Pistas: máscara causal con `torch.triu(..., 1)`, no atender a padding, permitir la diagonal; LayerNorm final.
""")
pj.code(r"""
class GRU4Rec(nn.Module):
    def __init__(self, n_items, d=64, hidden=128, dropout=0.2):
        super().__init__()
        # TODO
        raise NotImplementedError

    def encode(self, seq):
        raise NotImplementedError


class SASRec(nn.Module):
    def __init__(self, n_items, d=64, n_layers=2, n_heads=2, maxlen=200, dropout=0.2):
        super().__init__()
        # TODO: item_emb, pos_emb, bloques Transformer (puedes usar nn.TransformerEncoderLayer con norm_first=True
        #       y una máscara float/bool combinada de forma [B*heads, L, L]) y LayerNorm final
        raise NotImplementedError

    def encode(self, seq):
        raise NotImplementedError
""")
pj.md(r"""
## Paso 3 · Pérdidas y entrenamiento
Implementa `seq_loss` con `"ce"`, `"bce"` y `"gbce"` (β = α(t(1−1/α)+1/α), α = k/(N−1)) y un bucle de entrenamiento que evalúe en validación cada pocas épocas.
""")
pj.code(r"""
def seq_loss(model, h, tgt, loss="ce", n_neg=1, gbce_t=0.75):
    # TODO
    raise NotImplementedError

def train(model, loss="ce", epochs=100, n_neg=1, gbce_t=0.75, maxlen=200, batch_size=128, lr=1e-3):
    # TODO: devuelve historial con NDCG@10 de validación
    raise NotImplementedError
""")
pj.md(r"""
## Paso 4 · Experimentos y bootstrap
1. Entrena GRU4Rec (CE), SASRec (BCE, 1 neg), gSASRec (gBCE, 256 neg, t = 0,75) y SASRec+ (CE).
2. Evalúa en test. 3. Calcula un IC 95 % *bootstrap* (1.000 remuestreos de usuarios) de ΔNDCG@10 entre SASRec+ y GRU4Rec.
Pista: modifica `evaluate_next_item` (o copia su lógica) para devolver el NDCG **por usuario**.
""")
pj.code(r"""
def per_user_ndcg(score_fn, histories, targets, k=10):
    # TODO: vector de NDCG@k por usuario
    raise NotImplementedError

def bootstrap_ci(a, b, n_boot=1000, seed=42):
    # TODO: IC 95 % de mean(a - b) remuestreando usuarios con reemplazo
    raise NotImplementedError
""")

pj.md(r"""
---
# ⛔ SPOILER — Solución de referencia
Intenta resolverlo primero. La solución reutiliza el código de la lección (versión compacta).
""")
pj.code(r"""
# --- Solución: baselines ---
def popularity_score_fn(train_seqs, n_items):
    pop = np.bincount(np.concatenate(train_seqs), minlength=n_items + 1).astype(np.float32)
    return lambda H: torch.from_numpy(np.tile(pop, (len(H), 1)))

def markov_score_fn(train_seqs, n_items, eps=1e-3):
    src = np.concatenate([s[:-1] for s in train_seqs if len(s) > 1]); dst = np.concatenate([s[1:] for s in train_seqs if len(s) > 1])
    M = sp.csr_matrix((np.ones(len(src), dtype=np.float32), (src, dst)), shape=(n_items + 1, n_items + 1))
    pop = np.bincount(np.concatenate(train_seqs), minlength=n_items + 1).astype(np.float32); pop /= pop.sum()
    return lambda H: torch.from_numpy(M[[h[-1] for h in H]].toarray() + eps * pop)

base_res = {"Popularidad": evaluate_next_item(popularity_score_fn(train_seqs, n_items), *test, ks=(10,)),
            "Markov": evaluate_next_item(markov_score_fn(train_seqs, n_items), *test, ks=(10,))}
print(base_res)
""")
pj.code(MODELS)
pj.code(SASREC)
pj.code(LOSSES)
pj.code(TRAIN)
pj.code(r"""
MAXLEN = 200
CFG = dict(epochs=3 if FAST_DEV_RUN else 100, maxlen=MAXLEN, batch_size=128, lr=1e-3, eval_every=1 if FAST_DEV_RUN else 10)
ARCH = dict(d=64, n_layers=2, n_heads=2, maxlen=MAXLEN, dropout=0.2)
N_NEG = min(256, n_items - 1)
exps = {"GRU4Rec (CE)": (lambda: GRU4Rec(n_items), dict(loss="ce")),
        "SASRec (BCE, 1 neg)": (lambda: SASRec(n_items, **ARCH), dict(loss="bce", n_neg=1)),
        "gSASRec (gBCE)": (lambda: SASRec(n_items, **ARCH), dict(loss="gbce", n_neg=N_NEG, gbce_t=0.75)),
        "SASRec+ (CE)": (lambda: SASRec(n_items, **ARCH), dict(loss="ce"))}
trained, hists, final = {}, {}, {}
for name, (ctor, kw) in exps.items():
    torch.manual_seed(seed); np.random.seed(seed)
    trained[name] = ctor()
    hists[name] = train_seq_model(trained[name], train_seqs, valid, name=name, **CFG, **kw)
    final[name] = evaluate_next_item(make_score_fn(trained[name], MAXLEN), *test, ks=(10,))
    final[name]["min"] = hists[name]["train_time_s"] / 60
final.update(base_res)
display(pd.DataFrame(final).T.sort_values("NDCG@10").round(4))
""")
pj.code(r"""
@torch.no_grad()
def per_user_ndcg(score_fn, histories, targets, k=10, batch_size=512):
    out = []
    for b in range(0, len(histories), batch_size):
        H, T = histories[b:b + batch_size], torch.as_tensor(targets[b:b + batch_size])
        s = score_fn(H).float().cpu(); tgt = s.gather(1, T[:, None]).clone()
        s[:, 0] = -float("inf")
        for i, h in enumerate(H):
            s[i, h] = -float("inf")
        s.scatter_(1, T[:, None], tgt)
        r = (s > tgt).sum(1).numpy()
        out.append((r < k) / np.log2(r + 2))
    return np.concatenate(out)

def bootstrap_ci(a, b, n_boot=1000, seed=42):
    rng = np.random.default_rng(seed); d = a - b
    boots = np.array([d[rng.integers(0, len(d), len(d))].mean() for _ in range(n_boot)])
    return d.mean(), np.percentile(boots, 2.5), np.percentile(boots, 97.5)

nd_sas = per_user_ndcg(make_score_fn(trained["SASRec+ (CE)"], MAXLEN), *test)
nd_gru = per_user_ndcg(make_score_fn(trained["GRU4Rec (CE)"], MAXLEN), *test)
delta, lo, hi = bootstrap_ci(nd_sas, nd_gru)
print(f"ΔNDCG@10 (SASRec+ − GRU4Rec) = {delta:.4f}   IC95% [{lo:.4f}, {hi:.4f}]")
""")
pj.code(r"""
fig, ax = plt.subplots(1, 2, figsize=(13, 4))
for name, h in hists.items():
    ax[0].plot(h["epoch"], h["val_NDCG@10"], marker="o", ms=3, label=name)
ax[0].set(title="Validación NDCG@10", xlabel="época"); ax[0].legend(fontsize=8)
fr = pd.DataFrame(final).T.sort_values("NDCG@10")
fr["NDCG@10"].plot.barh(ax=ax[1], color="#6366f1"); ax[1].set(title="Test NDCG@10")
plt.tight_layout(); plt.show()
""")
pj.md(r"""
**Interpretación esperada (con ML-1M real):** SASRec+ (CE) > gSASRec ≳ GRU4Rec > SASRec-BCE(1 neg) > Markov > Popularidad.
La brecha BCE(1) → gBCE ilustra la sobreconfianza; la brecha gBCE → CE, el valor de ver todo el catálogo como negativo.
Si el IC del Δ no incluye 0, la mejora de SASRec+ sobre GRU4Rec es estadísticamente sólida para este *split*.

**Recomendación a producto (ejemplo):** desplegar SASRec+ como generador de candidatos de la fila «Porque acabas de ver…»: el coste de serving
(un *forward* de 2 capas sobre ≤200 ítems, ~ms en GPU, o precálculo por lotes cada hora) es asumible y la ganancia de NDCG es significativa.

## 🚀 Retos extra (nivel experto)
1. **Split temporal global**: re-evalúa todos los modelos cortando por fecha (módulo 01). ¿Se mantiene el ranking?
2. **Sampled softmax con logQ** con negativos muestreados por popularidad (módulo 08) y compáralo con gBCE.
3. **Features de contenido**: suma al embedding del ítem un embedding de géneros (como hace RecTools con `CatFeaturesItemNet`) y mide el efecto en ítems poco populares.
4. **Escala**: repite con MovieLens-20M o -32M en A100 (`d=128`, 4 capas, `maxlen=200`). ¿Crece la ventaja de SASRec?
5. **Exporta el encoder** a ONNX/TorchScript y mide la latencia p99 de inferencia para un usuario (preparación del módulo 16).

## 🤔 Reflexión (producción / MLOps)
- ¿Calcularías el embedding de usuario en cada petición (*stateless*) o en batch (como PinnerFormer)? ¿Qué frescura necesita esta fila?
- ¿Cómo detectarías en producción que el modelo se ha degradado (módulo 17)? Propón 2 métricas online y 1 offline.
- Los ítems nuevos no tienen embedding: ¿cómo los introducirías en el catálogo sin reentrenar (pista: módulo 03 y semantic IDs del módulo 11)?
""")
pj.save(PROJECT)
