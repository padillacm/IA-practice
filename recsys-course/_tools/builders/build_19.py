"""Builder del módulo 19 · Elite Playbook (lección + proyecto «pager duty de recsys»).

Ejecutar desde la raíz del repo:  python recsys-course/_tools/builders/build_19.py
La lección es autocontenida (simulaciones con verdad conocida + implementaciones mini en NumPy/PyTorch).
El proyecto reutiliza la celda de datos del módulo 16 (MovieLens-100K con fallback sintético).
"""
import os
import sys

sys.path.insert(0, "recsys-course/_tools")
sys.path.insert(0, "recsys-course/_tools/builders")
from nbbuild import Notebook  # noqa: E402
from build_16 import DATA_CELL  # noqa: E402

MOD = "recsys-course/19_elite_playbook"
os.makedirs(MOD, exist_ok=True)

SETUP_CELL = r'''
import math, time, random, warnings, collections
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import roc_auc_score, log_loss
from IPython.display import display

warnings.filterwarnings("ignore")
seed = 42
random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
device = "cuda" if torch.cuda.is_available() else "cpu"
FAST_DEV_RUN = True          # ⇦ False en una GPU de Colab para correr las simulaciones a mayor escala
S = 1 if FAST_DEV_RUN else 4 # factor de escala de los experimentos
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.3})
print("device:", device, "| torch", torch.__version__, "| FAST_DEV_RUN:", FAST_DEV_RUN)


def box(ax, xy, w, h, text, color="#dbeafe", fs=8.5, ec="#334155"):
    ax.add_patch(mpatches.FancyBboxPatch(xy, w, h, boxstyle="round,pad=0.02", fc=color, ec=ec, lw=1.2))
    ax.text(xy[0] + w / 2, xy[1] + h / 2, text, ha="center", va="center", fontsize=fs)


def arrow(ax, a, b, text="", color="#334155", fs=7.5, rad=0.0):
    ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="->", color=color, lw=1.4,
                                                     connectionstyle=f"arc3,rad={rad}"))
    if text:
        ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 0.12, text, ha="center", fontsize=fs, color=color)


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def mix64(x):
    """Hash entero de calidad (finalizador de SplitMix64). Nunca uses `id % m` con IDs estructurados."""
    x = np.asarray(x, dtype=np.uint64)
    with np.errstate(over="ignore"):
        x = (x ^ (x >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
        x = (x ^ (x >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
        x = x ^ (x >> np.uint64(31))
    return x
'''


def lesson() -> None:
    path = f"{MOD}/19_elite_playbook.ipynb"
    nb = Notebook("Módulo 19 · Elite Playbook", colab_path=path, gpu=True)
    M, C = nb.md, nb.code

    M(f"""
    {nb.badge()}

    # Módulo 19 · Masterclass: lo que separa a un ingeniero top de recomendación

    **Nivel:** 🔴 Experto · **Duración:** 7–9 h (lección) + 6–10 h (proyecto) · **GPU:** opcional (T4 acelera §1 y §7; todo corre en CPU con `FAST_DEV_RUN=True`) · **Unidades Colab:** 1–4

    **Prerrequisitos:** 06 (CTR y hashing), 07 (LTR y sesgo de posición), 08 (two-tower + ANN), 13 (feedback loops), 14 (OPE), 15 (A/B), 16 (serving y point-in-time), 17 (monitoreo), 18 (compendio de élite).

    > El módulo 18 te dio un **compendio** de 38 secretos de élite con su fuente. Este módulo no los repite: coge los que
    > en el 18 solo se *mencionan* (Monolith, tablas de embeddings, skew, funnel, largo plazo…) y los **abre en canal**:
    > los implementas en miniatura, los mides con simulaciones de verdad conocida y aprendes a **depurarlos** cuando
    > rompen en producción. Es lo que se aprende en los primeros 2–3 años de un equipo de ranking de una gran plataforma,
    > normalmente a base de incidentes.

    ## 🎯 Objetivos de aprendizaje

    1. **Dimensionar y comprimir** tablas de embeddings: medir colisiones de hashing ponderadas por tráfico, implementar QR, *mixed-dimension*, TT-Rec, híbrido por frecuencia y cuantización int8/fp8/int4 por fila, y elegir con una curva calidad–memoria.
    2. **Diseñar entrenamiento en tiempo real** al estilo Monolith: tabla sin colisiones con filtro de frecuencia y expiración, intervalo de sincronización, y mitigar el *catastrophic forgetting* con *replay*.
    3. **Corregir el label delay** (modelo de Chapelle 2014), elegir ventanas de atribución y **detectar fugas sutiles** en contadores en tiempo real y *training-serving skew* con *log-and-wait*.
    4. **Explicar y cuantificar** el *exposure bias* y el *candidate-set mismatch* entre etapas (paradoja de Berkson), y mejorar la consistencia del funnel con negativos no expuestos y distilación.
    5. **Medir la verdad a largo plazo**: holdouts globales, Goodhart, encuestas como etiquetas y *value models*.
    6. **Depurar** el patrón «offline ↑, online ↓» con un *casebook* de 10 incidentes (síntoma → hipótesis → diagnóstico → arreglo).
    7. **Hacer ingeniería de rendimiento**: presupuestos de latencia, *dynamic batching*, *hedged requests*, cachés, cuantización, retrieval en GPU y *capacity planning*.
    8. **Pensar como un equipo top**: cultura de experimentación, *design docs*, revisión de experimentos y señales de seniority.

    ## Índice
    0. Dónde muere un recomendador (mapa de fallos)
    1. Tablas de embeddings a escala
    2. Entrenamiento en tiempo real (Monolith) e *incremental learning*
    3. *Label delay*, fugas en contadores y *training-serving skew*
    4. Sesgos en los logs, *exposure bias* y consistencia del funnel
    5. Medir la verdad a largo plazo
    6. *Casebook*: offline ↑ online ↓
    7. Ingeniería de rendimiento y *capacity planning*
    8. Cómo piensan los equipos top
    9. 🏭 En producción · 🧠 Secretos de la élite · ⚠️ Errores comunes · Autoevaluación · Referencias
    """)

    C(r'''
    # Colab ya trae torch, numpy, pandas, matplotlib y scikit-learn; esta línea solo asegura versiones recientes.
    !pip install -q numpy pandas matplotlib scikit-learn scipy
    ''')
    C(SETUP_CELL)

    # ------------------------------------------------------------------ 0. mapa de fallos
    M(r"""
    ## 0. 💡 Dónde muere un recomendador

    Los papers describen modelos. Los incidentes de producción casi nunca son «el modelo es malo»: son **costuras** entre
    piezas. Un ingeniero top tiene en la cabeza este mapa y, ante cualquier anomalía, recorre las costuras en orden.
    Cada etiqueta roja es una sección de este módulo.
    """)
    C(r'''
    fig, ax = plt.subplots(figsize=(12, 4.6)); ax.set_xlim(0, 12); ax.set_ylim(0, 5); ax.axis("off")
    stages = [("Eventos\n(Kafka)", 0.2), ("Joiner +\netiquetas", 1.85), ("Features\n(store)", 3.5), ("Entrenamiento\n(batch/online)", 5.15),
              ("Retrieval\n(ANN)", 6.8), ("Ranking", 8.45), ("Re-rank +\nserving", 10.1)]
    for name, x in stages:
        box(ax, (x, 2.3), 1.45, 0.9, name, "#e0f2fe")
    for (_, a), (_, b) in zip(stages[:-1], stages[1:]):
        arrow(ax, (a + 1.45, 2.75), (b, 2.75))
    box(ax, (5.15, 0.25), 1.45, 0.75, "Usuario", "#fef9c3")
    arrow(ax, (10.8, 2.3), (6.6, 0.65), rad=-0.15); arrow(ax, (5.15, 0.65), (0.9, 2.3), rad=-0.15)
    fails = [(0.9, "§3 label delay\nconversiones tardías"), (2.55, "§3 fuga en contadores\npoint-in-time"),
             (4.2, "§3 training-serving skew\n(log-and-wait)"), (5.85, "§1 colisiones · §2 frescura\nforgetting"),
             (7.5, "§6 versiones de\nembeddings desalineadas"), (9.15, "§4 candidate mismatch\nexposure bias"),
             (10.8, "§7 latencia · caché stale\n§5 Goodhart")]
    for x, t in fails:
        ax.text(x, 4.25, t, ha="center", va="center", fontsize=7.6, color="#b91c1c",
                bbox=dict(fc="#fee2e2", ec="#b91c1c", boxstyle="round,pad=0.25"))
        arrow(ax, (x, 3.85), (x, 3.25), color="#b91c1c")
    ax.text(3.0, 0.55, "feedback loop: el sistema genera sus propios datos (§4)", fontsize=8, color="#475569")
    ax.set_title("Mapa de fallos: los incidentes viven en las costuras entre etapas", fontsize=11)
    plt.show()
    ''')

    # ------------------------------------------------------------------ 1. embeddings
    M(r"""
    ## 1. Tablas de embeddings a escala

    ### 💡 Intuición
    En un DLRM (Naumov et al., 2019) el MLP pesa unos pocos MB; las **tablas de embeddings** pesan de GB a TB porque hay
    una fila por cada ID categórico (usuarios, vídeos, anunciantes, hashtags…). Guan et al. (2019) reportan que en los
    modelos de recomendación de Facebook las tablas son **> 99 %** del tamaño del modelo. Por eso «el modelo es la tabla»:
    casi todas las decisiones de ingeniería (sharding, cuantización, hashing, expiración) van de **cómo almacenar,
    actualizar y comprimir filas**.

    ### 📐 Cuánto ocupa
    $$\text{Memoria} = N \cdot d \cdot b \;+\; \underbrace{N \cdot d \cdot b_{opt} \cdot k_{opt}}_{\text{estado del optimizador}}$$
    con $N$ filas, $d$ dimensiones, $b$ bytes por número (4 en fp32, 2 en fp16/bf16, 1 en int8/fp8, 0,5 en int4) y
    $k_{opt}$ tensores de estado del optimizador por parámetro (Adam: 2 → **triplica** la memoria en entrenamiento).
    🧠 Por eso los DLRMs de producción entrenan las tablas con **Adagrad por filas** (*row-wise Adagrad*, el
    optimizador por defecto de las tablas en FBGEMM/TorchRec): guarda **un escalar por fila** en lugar de $d$, y el
    estado del optimizador pasa de $N d$ a $N$.
    """)
    C(r'''
    N = np.logspace(6, 11, 60)                                   # de 1 M a 100 000 M IDs
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.2))
    for d, ls in [(64, "-"), (256, "--")]:
        for name, b, c in [("fp32", 4, "#1d4ed8"), ("fp16", 2, "#16a34a"), ("int8", 1, "#ea580c"), ("int4", 0.5, "#9333ea")]:
            axes[0].loglog(N, N * d * b / 1e9, ls, color=c, label=f"{name}, d={d}" if d == 64 else None)
    for y, t in [(80, "1 GPU H100/A100 (80 GB HBM)"), (8 * 80, "nodo de 8 GPUs (640 GB)"), (2000, "2 TB de RAM de host")]:
        axes[0].axhline(y, color="gray", lw=0.8, ls=":"); axes[0].text(1.1e6, y * 1.15, t, fontsize=7.5, color="gray")
    axes[0].set(xlabel="nº de filas (IDs)", ylabel="GB (solo pesos)", title="Memoria de una tabla (— d=64 · -- d=256)")
    axes[0].legend(fontsize=8)
    n, d = 1e9, 128
    opts = {"SGD": n * d * 4, "Adagrad por filas": n * d * 4 + n * 4, "Adagrad": 2 * n * d * 4, "Adam": 3 * n * d * 4}
    axes[1].bar(list(opts), [v / 1e9 for v in opts.values()], color=["#94a3b8", "#16a34a", "#f59e0b", "#dc2626"])
    for i, v in enumerate(opts.values()):
        axes[1].text(i, v / 1e9 * 1.01, f"{v / 1e9:,.0f} GB", ha="center", fontsize=9)
    axes[1].set(ylabel="GB en entrenamiento (fp32)", title="1 000 M de IDs × d=128: pesos + estado del optimizador")
    plt.tight_layout(); plt.show()
    ''')

    M(r"""
    ### 1.1 Hashing trick y colisiones: mídelas **ponderadas por tráfico**

    El *hashing trick* (Weinberger et al., 2009) mapea $N$ IDs a $m < N$ filas con $h(i) \bmod m$. Con hash uniforme, la
    probabilidad de que un ID comparta fila con al menos otro es
    $$P(\text{colisión}) = 1 - \left(1 - \tfrac{1}{m}\right)^{N-1} \approx 1 - e^{-N/m}.$$
    Con $N/m = 1$ ya colisiona el **63 %** de los IDs. Pero la cifra que importa no es esa, sino **qué fracción de la
    señal de cada ID pertenece a otros**. Definimos la *contaminación* de un ID como la fracción del tráfico de su fila que
    procede de otros IDs. Con frecuencias Zipf ocurre algo que los resúmenes agregados esconden:

    - Los IDs de **cabeza** dominan su fila: casi no se contaminan. La métrica global apenas se mueve.
    - Los IDs de **cola** (y los **nuevos**) quedan enterrados bajo el gradiente de un ID popular: su embedding es, en
      la práctica, el de otro. **El hashing perjudica justo al cold start y a la long tail.**
    """)
    C(r'''
    def contamination(freq, m, hash_fn=lambda i: mix64(i)):
        """Por ID: fracción del tráfico de su fila que pertenece a OTROS IDs."""
        ids = np.arange(len(freq))
        b = (hash_fn(ids) % np.uint64(m)).astype(np.int64)
        row_traffic = np.bincount(b, weights=freq, minlength=m)
        return 1 - freq / row_traffic[b], b


    rng = np.random.default_rng(seed)
    n_ids = 200_000
    freq = 1.0 / np.arange(1, n_ids + 1) ** 1.05                # Zipf: el ID 0 es el más frecuente
    freq /= freq.sum()
    ratios = np.array([0.25, 0.5, 1, 2, 4, 8, 16])               # N / m
    rows = []
    for r_ in ratios:
        m = int(n_ids / r_)
        c, b = contamination(freq, m)
        collide = np.bincount(b, minlength=m)[b] > 1
        rows.append({"N/m": r_, "IDs con colisión (empírico)": collide.mean(), "teoría 1-e^{-N/m}": 1 - np.exp(-r_),
                     "contaminación media ponderada por tráfico": (freq * c).sum(),
                     "contaminación top-1% IDs": c[: n_ids // 100].mean(), "contaminación cola (80% menos frecuente)": c[n_ids // 5:].mean()})
    coll = pd.DataFrame(rows).set_index("N/m")
    display(coll.round(3))
    fig, ax = plt.subplots(1, 2, figsize=(12.5, 4))
    ax[0].plot(ratios, coll.iloc[:, 0], "o-", label="empírico"); ax[0].plot(ratios, coll.iloc[:, 1], "k--", label="teoría")
    ax[0].set(xscale="log", xlabel="N / m (IDs por fila)", ylabel="fracción de IDs con colisión", title="Colisiones por ID"); ax[0].legend()
    for col, c_ in zip(coll.columns[2:], ["#1d4ed8", "#16a34a", "#dc2626"]):
        ax[1].plot(ratios, coll[col], "o-", color=c_, label=col)
    ax[1].set(xscale="log", xlabel="N / m", ylabel="fracción de la señal ajena", title="Lo que importa: contaminación de la señal")
    ax[1].legend(fontsize=8); plt.tight_layout(); plt.show()
    ''')
    M(r"""
    ⚠️ **El hash también importa.** Muchos sistemas generan IDs **estructurados** (*snowflake*: marca de tiempo + máquina +
    secuencia; IDs múltiplos de 64 porque los bits bajos codifican el *shard*). En Python `hash(int)` es la identidad, así
    que `id % m` con $m$ potencia de 2 usa solo unas pocas filas. Es un bug real y silencioso:
    """)
    C(r'''
    structured_ids = (np.arange(50_000, dtype=np.uint64) << np.uint64(6)) + np.uint64(7)   # bits bajos = shard 7
    m = 2 ** 14
    used_naive = np.unique(structured_ids % np.uint64(m)).size
    used_mix = np.unique(mix64(structured_ids) % np.uint64(m)).size
    print(f"filas usadas de {m}: id % m → {used_naive}  ({used_naive / m:.1%})   ·   mix64(id) % m → {used_mix} ({used_mix / m:.1%})")
    ''')

    M(r"""
    ### 1.2 Cinco formas de comprimir una tabla (implementadas y comparadas)

    | Técnica | Idea | Parámetros | Fuente |
    |---|---|---|---|
    | **Hashing** | $e_i = E[h(i) \bmod m]$ | $m d$ | Weinberger et al. 2009 |
    | **Double hashing** | $e_i = E_1[h_1(i)] + E_2[h_2(i)]$: dos IDs solo coinciden si colisionan en ambas | $m d$ | Zhang et al. (Twitter), RecSys 2020 |
    | **Quotient-Remainder (QR)** | $e_i = E_q[\lfloor i/q \rfloor] \odot E_r[i \bmod q]$: **único** para cada ID (particiones complementarias) | $(N/q + q) d$ | Shi et al. (Meta), KDD 2020 |
    | **Híbrido por frecuencia** | los $K$ IDs más frecuentes tienen fila propia; la cola comparte filas hasheadas | $(K + m) d$ | Zhang et al. 2020; Monolith 2022 (filtro de frecuencia) |
    | **Mixed-dimension** | la dimensión crece con la popularidad (bloques con $d_b$ distinta + proyección a $d$) | $\sum_b N_b d_b + d_b d$ | Ginart et al. (Meta), ISIT 2021 |
    | **TT-Rec** | la tabla $N \times d$ es un tensor de *tensor-train* de rango $r$: $e_i = G_1[i_1] G_2[i_2] G_3[i_3]$ | $\approx r^2 \sum_k n_k d_k$ | Yin et al. (Meta), MLSys 2021 |

    📐 **TT-Rec en una línea.** Factorizamos $N = n_1 n_2 n_3$ y $d = d_1 d_2 d_3$; el ID $i$ se descompone en $(i_1, i_2, i_3)$
    (como dígitos en base mixta) y la fila es el producto de tres «núcleos» pequeños
    $G_1[i_1] \in \mathbb{R}^{d_1 \times r}$, $G_2[i_2] \in \mathbb{R}^{r \times d_2 \times r}$, $G_3[i_3] \in \mathbb{R}^{r \times d_3}$.
    Con $N = 10^6$, $d=16$, $r=8$: ~13 K parámetros frente a 16 M.

    🧪 **Experimento.** Un problema de CTR sintético con 30 000 ítems Zipf y factores latentes conocidos; la torre de usuario es
    una tabla completa y comparamos solo la representación del ítem con **~1/8 de la memoria** (salvo TT-Rec, mucho menor).
    Medimos *log-loss* y AUC en total y en la **cola** (80 % de ítems menos frecuentes).
    """)
    C(r'''
    class HashEmb(nn.Module):
        def __init__(self, m, d, n_hash=1):
            super().__init__()
            self.m, self.n_hash = m, n_hash
            self.tabs = nn.ModuleList(nn.Embedding(m // n_hash, d) for _ in range(n_hash))
            for t in self.tabs: nn.init.normal_(t.weight, std=0.05)
        def forward(self, i):
            out = 0
            for k, t in enumerate(self.tabs):                      # semillas distintas por hash
                h = torch.as_tensor((mix64(i.cpu().numpy() + 1_000_003 * k) % np.uint64(t.num_embeddings)).astype(np.int64), device=i.device)
                out = out + t(h)
            return out


    class QREmb(nn.Module):
        """Quotient-remainder trick (Shi et al. 2020) con operador multiplicativo."""
        def __init__(self, n, d, q):
            super().__init__()
            self.q = q
            self.Eq, self.Er = nn.Embedding(-(-n // q), d), nn.Embedding(q, d)
            nn.init.normal_(self.Eq.weight, std=0.05); nn.init.normal_(self.Er.weight, mean=1.0, std=0.05)
        def forward(self, i):
            return self.Eq(i // self.q) * self.Er(i % self.q)


    class FreqHybridEmb(nn.Module):
        """Fila propia para los K IDs más frecuentes (rank < K) y filas hasheadas para la cola."""
        def __init__(self, rank, K, m_tail, d):
            super().__init__()
            self.register_buffer("rank", torch.as_tensor(rank)); self.K = K
            self.head, self.tail = nn.Embedding(K, d), HashEmb(m_tail, d)
            nn.init.normal_(self.head.weight, std=0.05)
        def forward(self, i):
            r = self.rank[i]
            out = self.tail(i)
            is_head = r < self.K
            return torch.where(is_head[:, None], self.head(r.clamp(max=self.K - 1)), out)


    class MixedDimEmb(nn.Module):
        """Mixed-dimension embeddings (Ginart et al.): bloques por popularidad con d_b decreciente + proyección a d."""
        def __init__(self, rank, n, d, blocks=((0.05, 16), (0.25, 8), (1.0, 2))):
            super().__init__()
            bounds = [0] + [int(f * n) for f, _ in blocks]
            blk = np.searchsorted(np.array(bounds[1:]), rank, side="right")
            self.register_buffer("blk", torch.as_tensor(blk)); self.register_buffer("loc", torch.as_tensor(rank - np.array(bounds)[blk]))
            self.tabs = nn.ModuleList(nn.Embedding(bounds[k + 1] - bounds[k], db) for k, (_, db) in enumerate(blocks))
            self.proj = nn.ModuleList(nn.Identity() if db == d else nn.Linear(db, d, bias=False) for _, db in blocks)
            for t in self.tabs: nn.init.normal_(t.weight, std=0.05)
            self.d = d
        def forward(self, i):
            out = torch.zeros(len(i), self.d, device=i.device)
            b, l = self.blk[i], self.loc[i]
            for k, (t, p) in enumerate(zip(self.tabs, self.proj)):
                mask = b == k
                if mask.any():
                    out[mask] = p(t(l[mask]))
            return out


    class TTEmb(nn.Module):
        """TT-Rec (Yin et al. 2021): tabla N×d como tensor-train de 3 núcleos y rango r."""
        def __init__(self, n, d_factors=(2, 2, 4), r=8):
            super().__init__()
            n1 = int(math.ceil(n ** (1 / 3))); self.ns = (n1, n1, int(math.ceil(n / n1 ** 2)))
            (d1, d2, d3), s = d_factors, (0.05 ** 2 / r ** 2) ** (1 / 6)          # var(salida) ≈ 0.05²
            self.G1 = nn.Parameter(torch.randn(self.ns[0], d1, r) * s)
            self.G2 = nn.Parameter(torch.randn(self.ns[1], r, d2, r) * s)
            self.G3 = nn.Parameter(torch.randn(self.ns[2], r, d3) * s)
        def forward(self, i):
            n2n3 = self.ns[1] * self.ns[2]
            i1, i2, i3 = i // n2n3, (i // self.ns[2]) % self.ns[1], i % self.ns[2]
            ab = torch.einsum("bir,brjs->bijs", self.G1[i1], self.G2[i2])
            return torch.einsum("bijs,bsk->bijk", ab, self.G3[i3]).reshape(len(i), -1)


    def n_params(mod):
        return sum(p.numel() for p in mod.parameters())
    ''')
    C(r'''
    # Datos sintéticos de CTR con verdad conocida: logit = <p_u, q_i> + sesgo del ítem
    n_users, n_items, k_true, D = 3000, 30_000, 8, 16
    n_samples = 600_000 * S
    rng = np.random.default_rng(seed)
    P = rng.normal(0, 0.6, (n_users, k_true)); Q = rng.normal(0, 0.6, (n_items, k_true)); bias_i = rng.normal(-1.0, 0.6, n_items)
    item_p = 1.0 / np.arange(1, n_items + 1) ** 1.0; item_p /= item_p.sum()
    perm = rng.permutation(n_items)                               # la popularidad no coincide con el orden del ID
    items = perm[rng.choice(n_items, n_samples, p=item_p)]
    users = rng.integers(0, n_users, n_samples)
    y = (rng.random(n_samples) < sigmoid((P[users] * Q[items]).sum(1) + bias_i[items])).astype(np.float32)
    cut = int(0.85 * n_samples)
    counts = np.bincount(items[:cut], minlength=n_items)
    rank = np.empty(n_items, dtype=np.int64); rank[np.argsort(-counts, kind="stable")] = np.arange(n_items)
    is_tail = rank[items[cut:]] >= int(0.2 * n_items)
    print(f"{n_samples:,} ejemplos · CTR medio {y.mean():.3f} · % tráfico de test en la cola: {is_tail.mean():.1%}")


    class CTRModel(nn.Module):
        def __init__(self, item_emb):
            super().__init__()
            self.user = nn.Embedding(n_users, D); nn.init.normal_(self.user.weight, std=0.05)
            self.item, self.b = item_emb, nn.Parameter(torch.zeros(1))
            self.item_bias = HashEmb(4096, 1)                     # sesgo de ítem barato y compartido por todos
        def forward(self, u, i):
            return (self.user(u) * self.item(i)).sum(1) + self.item_bias(i).squeeze(1) + self.b


    def train_ctr(item_emb, epochs=2, bs=4096, lr=0.01):
        torch.manual_seed(seed)
        model = CTRModel(item_emb).to(device)
        opt = torch.optim.Adam(model.parameters(), lr=lr)
        U, I, Y = (torch.as_tensor(a, device=device) for a in (users[:cut], items[:cut], y[:cut]))
        for _ in range(epochs):
            for s_ in torch.randperm(cut, device=device).split(bs):
                loss = F.binary_cross_entropy_with_logits(model(U[s_], I[s_]), Y[s_])
                opt.zero_grad(); loss.backward(); opt.step()
        with torch.no_grad():
            p = torch.sigmoid(model(torch.as_tensor(users[cut:], device=device), torch.as_tensor(items[cut:], device=device))).cpu().numpy()
        yt = y[cut:]
        return model, {"logloss": log_loss(yt, p), "AUC": roc_auc_score(yt, p), "AUC cola": roc_auc_score(yt[is_tail], p[is_tail]),
                       "logloss cola": log_loss(yt[is_tail], p[is_tail])}
    ''')
    C(r'''
    budget = n_items // 8                                         # ~1/8 de las filas
    variants = {
        "Completa": lambda: nn.Embedding(n_items, D),
        "Hash (m=N/8)": lambda: HashEmb(budget, D),
        "Double hash": lambda: HashEmb(budget, D, n_hash=2),
        "QR (q=8)": lambda: QREmb(n_items, D, q=8),
        "Híbrido frecuencia": lambda: FreqHybridEmb(rank, budget // 2, budget // 2, D),
        "Mixed-dim": lambda: MixedDimEmb(rank, n_items, D),
        "TT-Rec (r=8)": lambda: TTEmb(n_items, (2, 2, 4), r=8),
    }
    res, models = [], {}
    for name, make in variants.items():
        emb = make()
        if isinstance(emb, nn.Embedding): nn.init.normal_(emb.weight, std=0.05)
        t0 = time.time()
        models[name], met = train_ctr(emb)
        res.append({"variante": name, "parámetros ítem": n_params(emb), **met, "seg": time.time() - t0})
    comp = pd.DataFrame(res).set_index("variante")
    comp["compresión ×"] = comp.loc["Completa", "parámetros ítem"] / comp["parámetros ítem"]
    display(comp.round(4))
    ''')
    C(r'''
    fig, ax = plt.subplots(1, 2, figsize=(12.5, 4.2))
    cols = plt.cm.tab10(np.arange(len(comp)))
    for (name, r_), c_ in zip(comp.iterrows(), cols):
        ax[0].scatter(r_["parámetros ítem"], r_["logloss"], s=70, color=c_, label=name)
    ax[0].set(xscale="log", xlabel="parámetros de la representación del ítem (log)", ylabel="log-loss test (↓)", title="Frontera calidad–memoria")
    ax[0].legend(fontsize=8)
    x = np.arange(len(comp)); w = 0.38
    ax[1].bar(x - w / 2, comp["AUC"], w, label="AUC global"); ax[1].bar(x + w / 2, comp["AUC cola"], w, label="AUC cola")
    ax[1].set_xticks(x); ax[1].set_xticklabels(comp.index, rotation=30, ha="right", fontsize=8)
    ax[1].set_ylim(comp[["AUC", "AUC cola"]].values.min() - 0.02, comp[["AUC", "AUC cola"]].values.max() + 0.01)
    ax[1].set_title("La compresión ingenua castiga a la cola"); ax[1].legend()
    plt.tight_layout(); plt.show()
    ''')
    M(r"""
    **Cómo leerlo.** El hashing simple pierde sobre todo en la **cola** (su AUC cae más que el global). *Double hashing* y QR
    recuperan buena parte con la misma memoria porque cada ID vuelve a tener una representación (casi) única. El híbrido
    por frecuencia protege la cabeza, que es donde está el tráfico. *Mixed-dimension* gasta dimensiones donde hay datos para
    aprenderlas. TT-Rec comprime **órdenes de magnitud** a cambio de cómputo extra por *lookup* (por eso TT-Rec añade una caché
    de filas calientes) y de más sensibilidad a la inicialización. Con tus datos el orden exacto puede variar: lo que
    importa es el **método** — una curva calidad–memoria medida en la cabeza **y** en la cola, nunca solo la media.
    """)

    M(r"""
    ### 1.3 Cuantización de embeddings: por fila, no por tabla

    Para *serving* (y cada vez más para entrenamiento) las filas se guardan en 8 o 4 bits. La clave práctica es
    **cuantizar por fila** (*row-wise*): cada fila guarda su propia escala y desplazamiento (2 × fp16 = 4 bytes extra),
    porque las normas de las filas varían muchísimo (los IDs populares tienen normas grandes). Guan et al. (2019) cuantizan
    tablas de producción de Facebook a 4 bits por fila tras el entrenamiento, dejando el modelo en el 13,89 % del tamaño
    en fp32 con calidad neutra. Los formatos fp8 (E4M3/E5M2, Micikevicius et al., 2022) son la alternativa en coma flotante:
    no necesitan escala por fila para el rango, pero tienen solo 3 bits de mantisa.

    📐 Cuantización uniforme por fila a $b$ bits: $s = \frac{\max(x) - \min(x)}{2^b - 1}$, $\;q = \text{round}\left(\frac{x - \min(x)}{s}\right)$, $\;\hat{x} = q\,s + \min(x)$.

    🧪 Medimos sobre la tabla **completa** entrenada arriba: error relativo y, lo que de verdad importa en retrieval,
    **solapamiento del top-50** por producto escalar frente a fp32.
    """)
    C(r'''
    def quant_rowwise(W, bits):
        lo, hi = W.min(1, keepdims=True), W.max(1, keepdims=True)
        s = (hi - lo) / (2 ** bits - 1) + 1e-12
        return np.round((W - lo) / s) * s + lo


    def quant_tablewise(W, bits):
        lo, hi = W.min(), W.max(); s = (hi - lo) / (2 ** bits - 1)
        return np.round((W - lo) / s) * s + lo


    def quant_fp8(W):
        t = torch.as_tensor(W)
        if hasattr(torch, "float8_e4m3fn"):
            scale = t.abs().max() / 448.0                           # 448 = máximo de E4M3
            return (t / scale).to(torch.float8_e4m3fn).to(torch.float32).numpy() * scale.item()
        m, e = np.frexp(W); return np.ldexp(np.round(m * 16) / 16, e)  # fallback: 3 bits de mantisa


    Wf = models["Completa"].item.weight.detach().cpu().numpy().astype(np.float32)
    Uf = models["Completa"].user.weight.detach().cpu().numpy()[:300]
    ref_top = np.argsort(-(Uf @ Wf.T), 1)[:, :50]
    schemes = {"fp32": (Wf, 4 * D), "fp16": (Wf.astype(np.float16).astype(np.float32), 2 * D),
               "fp8 E4M3": (quant_fp8(Wf), 1 * D), "int8 por tabla": (quant_tablewise(Wf, 8), 1 * D),
               "int8 por fila": (quant_rowwise(Wf, 8), 1 * D + 4), "int4 por tabla": (quant_tablewise(Wf, 4), 0.5 * D),
               "int4 por fila": (quant_rowwise(Wf, 4), 0.5 * D + 4)}
    qrows = []
    for name, (Wq, bytes_row) in schemes.items():
        top = np.argsort(-(Uf @ Wq.T), 1)[:, :50]
        overlap = np.mean([len(set(a) & set(b)) / 50 for a, b in zip(ref_top, top)])
        qrows.append({"esquema": name, "bytes/fila": bytes_row, "error relativo": np.linalg.norm(Wq - Wf) / np.linalg.norm(Wf), "solape top-50": overlap})
    qdf = pd.DataFrame(qrows).set_index("esquema"); display(qdf.round(4))
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.scatter(qdf["bytes/fila"], qdf["solape top-50"], s=80, c=range(len(qdf)), cmap="viridis")
    for name, r_ in qdf.iterrows():
        ax.annotate(name, (r_["bytes/fila"], r_["solape top-50"]), textcoords="offset points", xytext=(5, -10), fontsize=8)
    ax.set(xlabel="bytes por fila (d=16, incluye escala/offset)", ylabel="solape del top-50 con fp32", title="Cuantización: memoria vs fidelidad del ranking")
    plt.show()
    ''')
    M(r"""
    🧠 **Detalles que solo se aprenden en producción**
    - Con $d$ pequeño el *overhead* de escala/offset por fila (4 bytes) pesa: con $d=16$, int4 por fila ocupa 12 bytes, no 8.
    - Cuantiza **más agresivamente la cola** (int4) y deja la cabeza en int8/fp16: el error en ítems raros apenas mueve
      el tráfico, y es el mismo razonamiento que *mixed-dimension*.
    - Valida la cuantización con una métrica **de ranking** (solape del top-K, recall del ANN), no con el error de
      reconstrucción: un 2 % de error puede reordenar el top-10 si los scores están muy juntos.
    - El *lookup* de embeddings está limitado por **ancho de banda de memoria**, no por FLOPs: bajar de 4 a 1 byte por
      número acelera el *serving* casi proporcionalmente (Gupta et al., HPCA 2020, caracterizan esta carga).
    """)

    # ------------------------------------------------------------------ 2. Monolith / online
    M(r"""
    ## 2. Entrenamiento en tiempo real: Monolith e *incremental learning*

    ### 💡 Intuición
    En TikTok/Douyin el catálogo cambia cada minuto: millones de vídeos nuevos al día, la mayoría con una vida útil de
    horas. Un modelo reentrenado cada noche llega tarde a casi todo. **Monolith** (Liu et al., ByteDance, ORSUM@RecSys 2022)
    describe el sistema que lo resuelve con tres ideas:

    1. **Tabla de embeddings sin colisiones** (*collisionless*, implementada con un *Cuckoo HashMap*) en lugar de una tabla
       de tamaño fijo con hashing: cada ID tiene su fila, y la tabla crece y decrece.
    2. **Control de memoria por política**, no por hashing: **filtro de frecuencia** (un ID solo recibe fila tras aparecer
       un mínimo de veces) y **expiración** (los IDs inactivos se borran tras un tiempo).
    3. **Entrenamiento online + sincronización de parámetros**: un *joiner* online une features y acciones del usuario (las
       features esperan en una caché a que llegue la acción — es *log-and-wait*, §3), los workers entrenan en streaming y
       los parámetros se sincronizan periódicamente con los servidores de inferencia. Como en cada intervalo solo cambian
       unas pocas filas, se sincronizan **solo las filas tocadas** a alta frecuencia y los parámetros densos (MLP), que
       cambian despacio, con menos frecuencia. El paper reporta que **cuanto más corto el intervalo de sincronización,
       mejor el modelo**, y que el sistema tolera perder algo de fiabilidad a cambio de frescura.
    """)
    C(r'''
    fig, ax = plt.subplots(figsize=(12, 4.6)); ax.set_xlim(0, 12); ax.set_ylim(0, 5); ax.axis("off")
    box(ax, (0.1, 3.6), 1.9, 0.9, "Logs de acciones\n(Kafka)", "#fef9c3"); box(ax, (0.1, 1.9), 1.9, 0.9, "Logs de features\n(Kafka)", "#fef9c3")
    box(ax, (2.6, 2.7), 2.0, 1.1, "Online joiner\ncaché de features\n+ neg. sampling", "#e0f2fe")
    box(ax, (5.3, 2.7), 1.9, 1.1, "Training workers\n(streaming)", "#dcfce7")
    box(ax, (5.3, 0.6), 1.9, 1.0, "Training PS\ntabla sin colisiones\nfiltro + expiración", "#dcfce7", fs=8)
    box(ax, (8.4, 0.6), 1.9, 1.0, "Serving PS", "#fee2e2"); box(ax, (8.4, 2.7), 1.9, 1.1, "Servidores de\ninferencia", "#fee2e2")
    box(ax, (10.6, 2.9), 1.3, 0.7, "Usuario", "#f1f5f9")
    arrow(ax, (2.0, 4.0), (2.6, 3.5)); arrow(ax, (2.0, 2.35), (2.6, 3.0)); arrow(ax, (4.6, 3.25), (5.3, 3.25), "ejemplos")
    arrow(ax, (6.25, 2.7), (6.25, 1.6), "grad / pull"); arrow(ax, (7.2, 1.1), (8.4, 1.1), "sync: filas tocadas\n(minutos)")
    arrow(ax, (7.2, 0.8), (8.4, 0.8)); ax.text(7.8, 0.35, "densos: menos a menudo", ha="center", fontsize=7.5, color="#334155")
    arrow(ax, (9.35, 1.6), (9.35, 2.7)); arrow(ax, (10.3, 3.25), (10.6, 3.25))
    arrow(ax, (11.2, 3.6), (1.0, 4.5), "acciones (clic, like, watch)", rad=0.12)
    ax.set_title("Monolith (ByteDance, 2022): entrenamiento online con tabla sin colisiones (esquema simplificado)", fontsize=10.5)
    plt.show()
    ''')
    M(r"""
    ### 2.1 Tabla sin colisiones con filtro de frecuencia y expiración (simulación)

    Simulamos 40 días de un catálogo de vídeo corto: cada día nacen IDs cuya popularidad decae en pocos días, más un
    núcleo *evergreen* estable. Comparamos cuatro políticas para la tabla y medimos **filas en memoria** y **cobertura**
    (fracción del tráfico del día cuyo ID ya tiene fila entrenada al empezar el día).
    """)
    C(r'''
    def simulate_table_policies(days=40, n_evergreen=30_000, new_per_day=15_000, events_per_day=250_000, tau=2.5, seed_=seed):
        r = np.random.default_rng(seed_)
        n_total = n_evergreen + new_per_day * days
        born = np.concatenate([np.full(n_evergreen, -1000), np.repeat(np.arange(days), new_per_day)])
        w0 = r.pareto(1.2, n_total) + 0.05
        w0[:n_evergreen] *= 0.3
        policies = {"sin filtro ni expiración": (1, None), "filtro (≥3 apariciones)": (3, None),
                    "expiración (7 días)": (1, 7), "filtro + expiración": (3, 7)}
        state = {p: {"count": np.zeros(n_total), "last": np.full(n_total, -10**9), "in": np.zeros(n_total, bool)} for p in policies}
        out = []
        for d in range(days):
            alive = np.where(born <= d)[0]
            age = np.where(born[alive] < 0, 0, d - born[alive])
            w = w0[alive] * np.where(born[alive] < 0, 1.0, np.exp(-age / tau))
            ev = r.choice(alive, size=events_per_day, p=w / w.sum())
            ids, cnt = np.unique(ev, return_counts=True)
            for p, (k_min, ttl) in policies.items():
                s_ = state[p]
                covered = s_["in"][ev].mean()
                s_["count"][ids] += cnt; s_["last"][ids] = d
                s_["in"] |= s_["count"] >= k_min
                if ttl is not None:
                    s_["in"] &= s_["last"] >= d - ttl
                out.append({"día": d, "política": p, "filas": int(s_["in"].sum()), "cobertura": covered})
        return pd.DataFrame(out)


    tab = simulate_table_policies(days=40 if FAST_DEV_RUN else 90)
    fig, ax = plt.subplots(1, 2, figsize=(12.5, 4))
    for p, g in tab.groupby("política", sort=False):
        ax[0].plot(g["día"], g["filas"] / 1e3, label=p); ax[1].plot(g["día"], g["cobertura"], label=p)
    ax[0].set(xlabel="día", ylabel="miles de filas en memoria", title="Tamaño de la tabla"); ax[0].legend(fontsize=8)
    ax[1].set(xlabel="día", ylabel="fracción del tráfico con fila entrenada", title="Cobertura del tráfico", ylim=(0.5, 1.0))
    plt.tight_layout(); plt.show()
    last = tab[tab["día"] == tab["día"].max()].set_index("política")[["filas", "cobertura"]]
    display(last)
    ''')
    M(r"""
    La tabla sin políticas crece sin límite (la mayoría de filas son de IDs muertos). La expiración la estabiliza casi sin
    perder cobertura, y el filtro de frecuencia elimina el enorme volumen de IDs vistos una o dos veces (que además
    tendrían embeddings casi aleatorios: **un ID con 2 eventos no aprende nada útil, solo ocupa memoria**). Las dos
    juntas dan una tabla varias veces más pequeña **sin colisiones**. El coste: los IDs recién nacidos usan un embedding
    por defecto hasta superar el umbral — por eso el filtro debe ser pequeño y los sistemas añaden features de contenido
    para el cold start.

    ### 2.2 Modelo estático vs actualizado: frescura e intervalo de sincronización

    Mundo sintético de 4 días por horas: cada hora nacen ítems con un *boost* de novedad que decae en horas. El modelo es
    una regresión logística sobre features dispersas (ID de ítem + cruce segmento×categoría + edad del ítem) entrenada con
    Adagrad, igual que un modelo de CTR clásico. Evaluamos con **validación progresiva** (cada hora se predice con el
    modelo servido antes de entrenar con ella, McMahan et al., 2013):

    - **Estático**: entrenado con el día 0 y congelado.
    - **Reentreno diario**: desde cero cada 24 h con las últimas 24 h.
    - **Online con sincronización cada S horas**: entrena continuamente; el *serving* recibe una copia cada S horas.
    """)
    C(r'''
    class SparseLR:
        """Regresión logística dispersa con Adagrad (np.add.at para gradientes de filas repetidas)."""
        def __init__(self, dim, lr=0.1):
            self.w, self.G, self.b, self.lr = np.zeros(dim), np.full(dim, 1e-6), 0.0, lr
        def predict(self, X):
            return sigmoid(self.w[X].sum(1) + self.b)
        def fit_batch(self, X, y, bs=4096):
            for s_ in range(0, len(y), bs):
                xb, yb = X[s_:s_ + bs], y[s_:s_ + bs]
                g = self.predict(xb) - yb
                gw = np.zeros_like(self.w); np.add.at(gw, xb.ravel(), np.repeat(g, xb.shape[1]))
                touched = np.unique(xb)
                self.G[touched] += gw[touched] ** 2
                self.w[touched] -= self.lr * gw[touched] / np.sqrt(self.G[touched])
                self.b -= 0.05 * g.mean()
        def copy(self):
            c = SparseLR(1); c.w, c.G, c.b, c.lr = self.w.copy(), self.G.copy(), self.b, self.lr; return c


    def make_stream(hours=96, new_per_hour=150, ev_per_hour=12_000 * S, n_seg=10, n_cat=20, seed_=seed):
        r = np.random.default_rng(seed_)
        n_items = new_per_hour * hours + 2000
        born = np.concatenate([np.full(2000, -500), np.repeat(np.arange(hours), new_per_hour)])
        q, cat = r.normal(0, 0.8, n_items), r.integers(0, n_cat, n_items)
        pop = r.pareto(1.5, n_items) + 0.1
        cross = r.normal(0, 0.8, (n_seg, n_cat))
        hours_data = []
        for h in range(hours):
            alive = np.where(born <= h)[0]
            age = np.clip(h - born[alive], 0, None)
            w = pop[alive] * (np.exp(-age / 8.0) + 0.05)
            it = r.choice(alive, size=ev_per_hour, p=w / w.sum()); seg = r.integers(0, n_seg, ev_per_hour)
            a = np.clip(h - born[it], 0, None)
            logit = -2.3 + q[it] + cross[seg, cat[it]] + 1.2 * np.exp(-a / 6.0)
            y = (r.random(ev_per_hour) < sigmoid(logit)).astype(float)
            ab = np.minimum(np.log2(a + 1).astype(int), 9)
            X = np.stack([it, n_items + seg * n_cat + cat[it], n_items + n_seg * n_cat + ab], 1)
            hours_data.append((X, y))
        return hours_data, n_items + n_seg * n_cat + 10


    stream, DIM = make_stream(hours=72 if FAST_DEV_RUN else 168)
    H = len(stream)


    def run_strategy(kind, sync=1):
        ll, trainer, served = [], SparseLR(DIM), None
        if kind == "estático":
            for X, y in stream[:24]: trainer.fit_batch(X, y)
            served = trainer
        for h in range(24, H):
            X, y = stream[h]
            if kind == "diario" and h % 24 == 0:
                trainer = SparseLR(DIM)
                for Xp, yp in stream[h - 24:h]: trainer.fit_batch(Xp, yp)
                served = trainer
            if kind == "online":
                if served is None:
                    for Xp, yp in stream[:24]: trainer.fit_batch(Xp, yp)
                if served is None or (h - 24) % sync == 0:
                    served = trainer.copy()
            ll.append(log_loss(y, np.clip(served.predict(X), 1e-6, 1 - 1e-6)))
            if kind == "online":
                trainer.fit_batch(X, y)
        return np.array(ll)


    curves = {"estático": run_strategy("estático"), "reentreno diario": run_strategy("diario")}
    syncs = [1, 3, 6, 12, 24]
    for s_ in syncs:
        curves[f"online, sync {s_} h"] = run_strategy("online", s_)
    fig, ax = plt.subplots(1, 2, figsize=(12.5, 4))
    for k_, v in curves.items():
        if k_ in ("estático", "reentreno diario", "online, sync 1 h", "online, sync 12 h"):
            ax[0].plot(np.arange(24, H), v, label=k_)
    ax[0].set(xlabel="hora", ylabel="log-loss progresiva (↓)", title="Frescura: estático vs diario vs online"); ax[0].legend(fontsize=8)
    ax[1].plot(syncs, [curves[f"online, sync {s_} h"].mean() for s_ in syncs], "o-", label="online")
    ax[1].axhline(curves["reentreno diario"].mean(), color="C1", ls="--", label="reentreno diario")
    ax[1].axhline(curves["estático"].mean(), color="C0", ls=":", label="estático")
    ax[1].set(xlabel="intervalo de sincronización (h)", ylabel="log-loss media", title="Cuanto más corto el sync, mejor (cf. Monolith)")
    ax[1].legend(fontsize=8); plt.tight_layout(); plt.show()
    print({k_: round(v.mean(), 4) for k_, v in curves.items()})
    ''')
    M(r"""
    ### 2.3 *Catastrophic forgetting* en entrenamiento incremental

    Actualizar un modelo solo con los datos más recientes tiene un riesgo: si el tráfico reciente está **sesgado** hacia un
    subgrupo (un evento deportivo, un país que se despierta, una campaña), los **parámetros compartidos** se adaptan a ese
    subgrupo y el modelo **olvida** al resto. En redes neuronales casi todos los parámetros son compartidos (el MLP); aquí lo
    reproducimos con una logística cuyo efecto de ítem es compartido entre dos grupos de usuarios que en realidad tienen
    gustos distintos.

    Durante las horas 24–48 el 95 % del tráfico es del grupo A. Medimos la log-loss **en el grupo B** con tres
    estrategias: SGD incremental con *learning rate* alto, con *learning rate* bajo y con ***replay*** (cada lote mezcla
    un 30 % de ejemplos de un *reservoir* del pasado). El *replay* (y su prima la regularización hacia los pesos
    anteriores, EWC de Kirkpatrick et al., 2017) es la defensa estándar.
    """)
    C(r'''
    def forgetting_experiment(hours=72, ev=6000 * S, n_items=1500, seed_=seed):
        r = np.random.default_rng(seed_)
        a = r.normal(0, 1, n_items); delta = r.normal(0, 1.0, n_items)          # gusto por ítem: A = a+δ, B = a-δ
        pop = r.pareto(1.5, n_items) + 0.2; pop /= pop.sum()
        def draw(n, frac_a):
            it = r.choice(n_items, n, p=pop); g = (r.random(n) < frac_a).astype(int)
            y = (r.random(n) < sigmoid(-1.5 + a[it] + np.where(g == 1, delta[it], -delta[it]))).astype(float)
            return np.stack([it, n_items + g], 1), y
        probe_B = draw(20_000, 0.0)
        results = {}
        for name, lr, replay in [("incremental lr=0.5", 0.5, 0.0), ("incremental lr=0.05", 0.05, 0.0), ("incremental lr=0.5 + replay 30%", 0.5, 0.3)]:
            w = np.zeros(n_items + 2); reservoir_X, reservoir_y = [], []
            curve = []
            for h in range(hours):
                X, y = draw(ev, 0.95 if 24 <= h < 48 else 0.5)
                if replay and reservoir_X:
                    RX, Ry = np.concatenate(reservoir_X), np.concatenate(reservoir_y)
                    k_ = int(replay * len(y)); j = r.integers(0, len(Ry), k_)
                    X, y = np.concatenate([X, RX[j]]), np.concatenate([y, Ry[j]])
                perm_ = r.permutation(len(y)); X, y = X[perm_], y[perm_]
                for s_ in range(0, len(y), 512):                              # SGD constante (sin Adagrad, para aislar el efecto)
                    xb, yb = X[s_:s_ + 512], y[s_:s_ + 512]
                    g = sigmoid(w[xb].sum(1)) - yb
                    np.add.at(w, xb.ravel(), -lr * np.repeat(g, 2) / 64)
                if h < 24 or h >= 48:                                         # el reservoir guarda tráfico "normal"
                    reservoir_X.append(X[:2000]); reservoir_y.append(y[:2000])
                    reservoir_X, reservoir_y = reservoir_X[-24:], reservoir_y[-24:]
                curve.append(log_loss(probe_B[1], np.clip(sigmoid(w[probe_B[0]].sum(1)), 1e-6, 1 - 1e-6)))
            results[name] = curve
        return results


    fg = forgetting_experiment()
    fig, ax = plt.subplots(figsize=(9, 4))
    for k_, v in fg.items():
        ax.plot(v, label=k_)
    ax.axvspan(24, 48, color="orange", alpha=0.15, label="95 % del tráfico es del grupo A")
    ax.set(xlabel="hora", ylabel="log-loss en el grupo B (↓)", title="Catastrophic forgetting y su mitigación con replay"); ax.legend(fontsize=8)
    plt.show()
    ''')
    M(r"""
    🧠 **Lo que no se cuenta en los papers de online learning**
    - El *learning rate* alto da frescura y olvido a la vez: es el mismo dial. Adagrad/FTRL lo resuelven parcialmente
      porque el paso de cada fila decrece con su historia (las filas nuevas aprenden rápido, las viejas son estables).
    - Online learning **amplifica el feedback loop** (§4): el modelo se entrena con lo que él mismo acaba de mostrar,
      minutos después. Sin tráfico de exploración y propensiones logueadas, la deriva es más rápida que con batch diario.
    - Online no sustituye al batch: los sistemas reales combinan **reentreno batch periódico** (estabilidad, cambios de
      arquitectura, *backfills*) con **actualización incremental** de filas de embeddings y, a menudo, de la capa final.
    - Necesitas **validación continua**: un lote corrupto (un bot, un bug en el joiner) se sirve en minutos. Monolith
      hace *snapshots* periódicos del PS para poder volver atrás; los equipos maduros añaden *guardrails* automáticos
      (calibración, tasa de predicciones extremas) antes de cada sincronización.
    """)

    # ------------------------------------------------------------------ 3. label delay, leakage, skew
    M(r"""
    ## 3. *Label delay*, fugas en contadores y *training-serving skew*

    ### 3.1 Conversiones tardías (Chapelle, KDD 2014)

    💡 Un clic llega en milisegundos; una **conversión** (compra, suscripción, «terminó la película», volvió mañana) llega
    horas o semanas después. Si entrenas en el instante $T$, los clics recientes sin conversión **todavía** se etiquetan
    como negativos: son *falsos negativos*. El sesgo no es uniforme: castiga lo **nuevo** (campañas, estrenos, ítems en
    crecimiento), cuyos clics son recientes. Es exactamente lo que no quieres infravalorar.

    📐 **Modelo de Chapelle.** Para cada clic, $C \in \{0, 1\}$ indica si acabará convirtiendo, $p(x) = P(C=1 \mid x)$ y el
    retraso $D \mid C=1 \sim \text{Exp}(\lambda)$. Con tiempo transcurrido $e$ desde el clic:
    $$P(\text{convertido y observado con retraso } d) = p(x)\,\lambda e^{-\lambda d}, \qquad
    P(\text{aún no observado}) = 1 - p(x) + p(x)\,e^{-\lambda e}.$$
    Maximizamos la verosimilitud conjunta en $p$ y $\lambda$. Ktena et al. (Twitter, RecSys 2019) proponen alternativas para
    entrenamiento continuo (introducir el ejemplo como negativo y corregir con pesos de importancia cuando llega el
    positivo: *fake negative weighting/calibration*).

    🧪 30 días de clics de 5 segmentos; el segmento 4 es una **campaña nueva** que empieza el día 24. Retraso medio: 4 días.
    """)
    C(r'''
    rng = np.random.default_rng(seed)
    T, mean_delay = 30.0, 4.0
    true_cvr = np.array([0.05, 0.08, 0.10, 0.12, 0.15])
    seg = rng.integers(0, 5, 60_000)
    t_click = np.where(seg == 4, rng.uniform(24, T, seg.size), rng.uniform(0, T, seg.size))
    will = rng.random(seg.size) < true_cvr[seg]
    delay = rng.exponential(mean_delay, seg.size)
    elapsed = T - t_click
    observed = will & (delay <= elapsed)                      # lo que el pipeline ve en T

    naive = np.array([observed[seg == s_].mean() for s_ in range(5)])
    wait = np.array([observed[(seg == s_) & (elapsed >= 7)].mean() if ((seg == s_) & (elapsed >= 7)).any() else np.nan for s_ in range(5)])

    # Delayed Feedback Model: p_s = sigmoid(theta_s), lambda = exp(phi)
    th = torch.zeros(5, requires_grad=True); phi = torch.zeros(1, requires_grad=True)
    S_, E_, O_ = torch.as_tensor(seg), torch.as_tensor(elapsed, dtype=torch.float32), torch.as_tensor(observed)
    Dd = torch.as_tensor(np.where(observed, delay, 0.0), dtype=torch.float32)
    opt = torch.optim.Adam([th, phi], lr=0.05)
    for _ in range(1500):
        p, lam = torch.sigmoid(th[S_]), torch.exp(phi)
        ll_pos = torch.log(p) + torch.log(lam) - lam * Dd
        ll_neg = torch.log(1 - p + p * torch.exp(-lam * E_))
        loss = -torch.where(O_, ll_pos, ll_neg).mean()
        opt.zero_grad(); loss.backward(); opt.step()
    dfm = torch.sigmoid(th).detach().numpy()
    print(f"retraso medio estimado: {1 / torch.exp(phi).item():.2f} días (real {mean_delay})")
    display(pd.DataFrame({"real": true_cvr, "ingenuo": naive, "esperar 7 días": wait, "DFM (Chapelle)": dfm},
                         index=[f"seg {s_}" + (" (campaña nueva)" if s_ == 4 else "") for s_ in range(5)]).round(4))
    ''')
    C(r'''
    fig, ax = plt.subplots(1, 3, figsize=(14, 4))
    x = np.arange(5); w = 0.2
    for k_, (v, lab) in enumerate([(true_cvr, "real"), (naive, "ingenuo"), (wait, "esperar 7 días"), (dfm, "DFM")]):
        ax[0].bar(x + (k_ - 1.5) * w, np.nan_to_num(v), w, label=lab)
    ax[0].set_xticks(x); ax[0].set_xticklabels([f"s{s_}" for s_ in range(5)]); ax[0].set(ylabel="CVR", title="CVR estimada por segmento")
    ax[0].text(4, 0.005, "sin datos\nmaduros", ha="center", fontsize=7); ax[0].legend(fontsize=7)
    bins = np.arange(0, 31, 1.0); mid = (bins[:-1] + bins[1:]) / 2
    rate = [observed[(elapsed >= a) & (elapsed < b) & (seg < 4)].mean() for a, b in zip(bins[:-1], bins[1:])]
    pbar = true_cvr[:4].mean()
    ax[1].plot(mid, rate, "o", ms=3, label="CVR observada"); ax[1].plot(mid, pbar * (1 - np.exp(-mid / mean_delay)), "k--", label=r"$p(1-e^{-\lambda e})$")
    ax[1].set(xlabel="edad del clic en T (días)", ylabel="CVR observada", title="Curva de maduración de la etiqueta"); ax[1].legend(fontsize=8)
    wins = np.linspace(0.5, 30, 60)
    for mu_, c_ in [(1, "C0"), (4, "C1"), (10, "C2")]:
        ax[2].plot(wins, 1 - np.exp(-wins / mu_), color=c_, label=f"retraso medio {mu_} d")
    ax[2].set(xlabel="ventana de atribución W (días)", ylabel="fracción de conversiones capturadas", title="Ventana de atribución: completitud vs frescura")
    ax[2].legend(fontsize=8); plt.tight_layout(); plt.show()
    ''')
    M(r"""
    **Lecturas.** El estimador ingenuo infravalora a todos, pero sobre todo a la **campaña nueva**; «esperar 7 días» es
    insesgado para lo viejo pero **no tiene datos** de lo nuevo (y en producción significa entrenar con una semana de
    retraso); el DFM recupera ambos. La curva de maduración (centro) es tu **herramienta de diagnóstico**: si la tasa de
    positivos depende de la edad del ejemplo, tienes *label delay* en el set de entrenamiento.

    🏭 **Ventanas de atribución.** Una ventana $W$ define qué cuenta como conversión («compra en 7 días tras el clic»). $W$
    corta da datos frescos pero incompletos; $W$ larga, completos pero viejos. Los equipos de ads publican la ventana como
    parte de la definición de la métrica y entrenan **varias cabezas** (conversión en 1 h, 1 día, 7 días) para tener a la
    vez una señal rápida y una completa.

    ### 3.2 Fugas sutiles en contadores en tiempo real

    El módulo 16 enseñó el *point-in-time join*. Las fugas que sobreviven a eso son más finas:

    1. **Ventana inclusiva**: el contador `clics_ultima_hora` del ejemplo incluye **su propio clic** (ventana $[t-1h, t]$
       en lugar de $[t-1h, t)$), porque el job batch agrega por hora y se une por hora.
    2. **Lag de streaming**: en *serving* el contador lo actualiza un job de streaming con un retraso de minutos; en el
       backfill de entrenamiento se calcula exacto. Mismo nombre, distinta distribución.

    🧠 La fuga 1 es **proporcional a 1/conteo**: para un ítem con 10 impresiones, su propio clic mueve el CTR un 10 %; para
    uno con 10 000, nada. Es decir, **la fuga es máxima en la cola y en lo nuevo**, y la AUC global apenas la delata.
    """)
    C(r'''
    rng = np.random.default_rng(seed)
    n_it, n_ev, Wh = 2000, 400_000 * S, 1.0                   # ventana de 1 hora; 24 horas de eventos
    base = rng.normal(-3.0, 0.7, n_it); trend_amp = rng.normal(0, 0.8, n_it); pop = rng.pareto(1.2, n_it) + 0.2
    it = rng.choice(n_it, n_ev, p=pop / pop.sum()); t = np.sort(rng.uniform(0, 24, n_ev))
    yv = (rng.random(n_ev) < sigmoid(base[it] + trend_amp[it] * np.sin(t / 24 * 2 * np.pi))).astype(int)


    def window_counts(it, t, y, lo_off, hi_off, inclusive):
        """Para cada evento: impresiones y clics del mismo ítem en [t-lo_off, t-hi_off) (o ']' si inclusive)."""
        imps, clks = np.zeros(len(t)), np.zeros(len(t))
        order = np.lexsort((t, it)); its, ts, ys = it[order], t[order], y[order]
        bounds = np.flatnonzero(np.diff(its)) + 1
        for a, b in zip(np.r_[0, bounds], np.r_[bounds, len(its)]):
            tt, cy = ts[a:b], np.r_[0, np.cumsum(ys[a:b])]
            lo = np.searchsorted(tt, tt - lo_off, "left")
            hi = np.searchsorted(tt, tt - hi_off, "right" if inclusive else "left")
            imps[order[a:b]], clks[order[a:b]] = hi - lo, cy[hi] - cy[lo]
        return imps, clks


    def ctr_feature(imps, clks):
        return np.stack([np.log((clks + 1) / (imps - clks + 30)), np.log1p(imps)], 1)


    variants = {"inclusiva (fuga)": window_counts(it, t, yv, Wh, 0.0, True),
                "point-in-time exacto": window_counts(it, t, yv, Wh, 0.0, False),
                "servida (lag 5 min)": window_counts(it, t, yv, Wh + 5 / 60, 5 / 60, False)}
    X = {k_: ctr_feature(*v) for k_, v in variants.items()}
    tr, te = t < 16, t >= 16
    from sklearn.linear_model import LogisticRegression
    rows = []
    for name in ["inclusiva (fuga)", "point-in-time exacto", "servida (lag 5 min)"]:
        clf = LogisticRegression().fit(X[name][tr], yv[tr])
        off = roc_auc_score(yv[te], clf.predict_proba(X[name][te])[:, 1])
        on = roc_auc_score(yv[te], clf.predict_proba(X["servida (lag 5 min)"][te])[:, 1])
        tail = te & (variants["point-in-time exacto"][0] < 20)
        on_tail = roc_auc_score(yv[tail], clf.predict_proba(X["servida (lag 5 min)"][tail])[:, 1])
        rows.append({"entrenado con": name, "AUC offline (misma feature)": off, "AUC online (feature servida)": on, "AUC online cola (<20 imps/h)": on_tail})
    leak = pd.DataFrame(rows).set_index("entrenado con"); display(leak.round(4))
    ax = leak.plot.bar(figsize=(9, 3.8), rot=0, ylim=(0.5, max(0.8, leak.values.max() + 0.02)))
    ax.set_title("Fuga en contadores: el offline promete, el online no cumple"); ax.set_ylabel("AUC"); ax.legend(fontsize=8, loc="lower right"); plt.show()
    ''')
    M(r"""
    El modelo entrenado con la ventana inclusiva tiene la mejor AUC offline y **la peor online**: aprendió a confiar en un
    contador que en *serving* ya no contiene la respuesta. Entrenar con la feature **tal como se sirve** (con su lag) es lo
    único que garantiza paridad — y nos lleva a *log-and-wait*.

    ### 3.3 *Training-serving skew* y *log-and-wait*

    💡 La regla 29 de *Rules of ML* (Zinkevich, Google) dice: «la mejor forma de entrenar como sirves es guardar las features
    usadas en *serving* y usarlas para entrenar». El patrón se suele llamar ***log-and-wait***: en cada petición se loguean
    las features **exactas** que vio el modelo (con `request_id` y versión del modelo), se **espera** a que lleguen las
    etiquetas (ventana de atribución) y se unen por `request_id`. Si además recalculas las features con el pipeline
    offline para las mismas peticiones, la comparación fila a fila es el **detector de skew** más potente que existe.
    """)
    C(r'''
    fig, ax = plt.subplots(figsize=(12, 3.4)); ax.set_xlim(0, 12); ax.set_ylim(0, 3.4); ax.axis("off")
    box(ax, (0.1, 1.9), 1.6, 0.9, "Petición\nrequest_id", "#fef9c3")
    box(ax, (2.2, 1.9), 1.9, 0.9, "Features online\n(store + contexto)", "#e0f2fe")
    box(ax, (4.6, 1.9), 1.6, 0.9, "Modelo vN", "#dcfce7")
    box(ax, (4.3, 0.2), 2.4, 0.9, "LOG: request_id, features,\nmodel_version, propensión", "#fee2e2", fs=8)
    box(ax, (7.3, 0.2), 1.9, 0.9, "Esperar W\n(etiquetas)", "#f1f5f9")
    box(ax, (9.8, 0.2), 2.1, 0.9, "Join por request_id\n→ ejemplos de train", "#dcfce7", fs=8)
    box(ax, (9.8, 1.9), 2.1, 0.9, "Recalcular offline\ny comparar → skew", "#fde68a", fs=8)
    arrow(ax, (1.7, 2.35), (2.2, 2.35)); arrow(ax, (4.1, 2.35), (4.6, 2.35)); arrow(ax, (3.15, 1.9), (4.9, 1.1))
    arrow(ax, (6.7, 0.65), (7.3, 0.65)); arrow(ax, (9.2, 0.65), (9.8, 0.65)); arrow(ax, (10.85, 1.1), (10.85, 1.9), "diff")
    ax.set_title("Log-and-wait: entrena con lo que sirviste y úsalo para detectar skew", fontsize=10.5); plt.show()
    ''')
    C(r'''
    rng = np.random.default_rng(seed)
    n = 20_000
    served = pd.DataFrame({
        "hora_local": rng.integers(0, 24, n),
        "seg_desde_ultima_visita": rng.exponential(3600 * 20, n),
        "n_vistas_usuario": rng.poisson(30, n).astype(float),
        "item_ctr_1h": rng.beta(2, 40, n),
        "precio": rng.choice([0.0, 4.99, 9.99], n),
        "emb_norm": rng.normal(1.0, 0.05, n),
    })
    served.loc[rng.random(n) < 0.08, "n_vistas_usuario"] = -1.0          # en serving, «sin historial» = -1
    offline = served.copy()
    tz = rng.choice([-5, 1, 8], n)
    offline["hora_local"] = (served.hora_local - tz) % 24                # offline usa UTC (bug de zona horaria)
    ms = rng.random(n) < 0.3
    offline.loc[ms, "seg_desde_ultima_visita"] *= 1000                   # una fuente nueva viene en milisegundos
    offline.loc[served.n_vistas_usuario == -1, "n_vistas_usuario"] = 0.0 # offline rellena con 0
    offline["item_ctr_1h"] = np.clip(served.item_ctr_1h + rng.normal(0, 0.004, n), 0, 1)   # lag de streaming: ruido pequeño
    offline["emb_norm"] = served.emb_norm                               # idéntico


    def psi(a, b, bins=10):
        q = np.unique(np.quantile(np.r_[a, b], np.linspace(0, 1, bins + 1)))
        pa = np.histogram(a, q)[0] / len(a) + 1e-6; pb = np.histogram(b, q)[0] / len(b) + 1e-6
        return float(((pa - pb) * np.log(pa / pb)).sum())


    def skew_report(served, offline, rtol=1e-3, atol=1e-6):
        rep = []
        for c_ in served.columns:
            a, b = served[c_].values.astype(float), offline[c_].values.astype(float)
            mism = ~np.isclose(a, b, rtol=rtol, atol=atol)
            rep.append({"feature": c_, "% filas distintas": mism.mean(), "PSI distribuciones": psi(a, b),
                        "ejemplo servido→offline": f"{a[mism][0]:.3g} → {b[mism][0]:.3g}" if mism.any() else "—"})
        r_ = pd.DataFrame(rep).set_index("feature")
        r_["veredicto"] = np.where(r_["% filas distintas"] > 0.01, "🔴 SKEW", "🟢 ok")
        return r_


    rep = skew_report(served, offline); display(rep.round(4))
    fig, ax = plt.subplots(1, 2, figsize=(12, 3.6))
    rep["% filas distintas"].plot.barh(ax=ax[0], color=np.where(rep["% filas distintas"] > 0.01, "#dc2626", "#16a34a"))
    ax[0].axvline(0.01, ls="--", color="k"); ax[0].set_title("Comparación fila a fila (log-and-wait)")
    rep["PSI distribuciones"].plot.barh(ax=ax[1], color="#64748b"); ax[1].axvline(0.2, ls="--", color="k")
    ax[1].set_title("PSI de distribuciones (lo que ve un monitor de drift)"); ax[1].set_xscale("symlog", linthresh=0.01)
    plt.tight_layout(); plt.show()
    ''')
    M(r"""
    🧠 Fíjate en `hora_local`: su **PSI es casi 0** (la distribución de horas es uniforme en ambos lados) y sin embargo el
    55–70 % de las filas son distintas. **Un monitor de drift por distribuciones no ve el skew; la comparación fila a fila,
    sí.** Igual con `item_ctr_1h`: distinto en todas las filas, pero con tolerancia relativa razonable es ruido de lag, no
    un bug. Un *skew report* maduro tiene tolerancias por feature y alerta por **filas distintas**, no solo por PSI.

    Ejemplos reales de skew que este informe pilla: zona horaria, unidades (s vs ms), valores por defecto distintos
    para «sin dato» (-1 vs 0 vs NaN), tokenización distinta del texto, versión distinta del embedding, orden de la lista
    de historial (más reciente primero vs último), *clipping* o normalización aplicada solo en un lado.
    """)

    # ------------------------------------------------------------------ 4. biases & funnel
    M(r"""
    ## 4. Sesgos en los logs: *exposure bias* y consistencia del funnel

    ### 4.1 *Exposure bias*: solo aprendes de lo que el sistema anterior mostró

    💡 Tus etiquetas existen solo para lo que se **mostró**. Lo que el sistema anterior nunca enseñó no tiene clics, y un
    modelo entrenado con *implicit feedback* («clic = positivo») aprende **la política de exposición anterior**, no los
    gustos. Es un problema MNAR (*missing not at random*). La corrección clásica es ponderar por la inversa de la
    **propensión de exposición** (Schnabel et al., ICML 2016; Saito et al., WSDM 2020). Requisito duro (**positividad**):
    la propensión debe ser > 0 para todo lo que quieras evaluar — si la política anterior era determinista, **no hay
    corrección posible** para lo que nunca mostró. Por eso los equipos top reservan tráfico de exploración.

    🧪 300 ítems y 10 segmentos con CTR real conocido. La política de logging muestra 10 ítems por petición mezclando su
    ranking (ruidoso) con exploración ε. Estimamos el score de cada ítem por segmento (a) contando clics — lo que hace un
    modelo de implicit feedback — y (b) con IPS, y medimos el NDCG@10 contra el CTR real en **todo** el catálogo.
    """)
    C(r'''
    def exposure_experiment(eps, n_items=300, n_seg=10, n_req=30_000 * S, k=10, seed_=seed):
        r = np.random.default_rng(seed_)
        true = sigmoid(r.normal(-2.5, 1.0, (n_seg, n_items)))
        old_score = np.log(true) + r.normal(0, 1.2, true.shape)       # el modelo anterior acierta solo a medias
        seg = r.integers(0, n_seg, n_req)
        clicks, ips = np.zeros((n_seg, n_items)), np.zeros((n_seg, n_items))
        for s_ in range(n_seg):
            n_s = (seg == s_).sum()
            top = np.argsort(-old_score[s_])[:k]
            p_show = np.full(n_items, eps * k / n_items); p_show[top] += (1 - eps)      # propensión de exposición por slot
            shown = np.where(r.random((n_s, k)) < eps, r.integers(0, n_items, (n_s, k)), top[None, :])
            c_ = r.random(shown.shape) < true[s_][shown]
            np.add.at(clicks[s_], shown[c_], 1)
            np.add.at(ips[s_], shown[c_], 1 / p_show[shown[c_]])
        def ndcg(est):
            out = []
            for s_ in range(n_seg):
                rank_ = np.argsort(-est[s_] - 1e-9 * r.random(n_items))[:k]
                ideal = np.sort(true[s_])[::-1][:k]
                disc = 1 / np.log2(np.arange(2, k + 2))
                out.append((true[s_][rank_] * disc).sum() / (ideal * disc).sum())
            return np.mean(out)
        return {"ε": eps, "conteo de clics (implicit)": ndcg(clicks), "IPS": ndcg(ips), "política anterior": ndcg(old_score)}


    exp_df = pd.DataFrame([exposure_experiment(e) for e in [0.0, 0.01, 0.03, 0.1, 0.3]]).set_index("ε")
    display(exp_df.round(3))
    ax = exp_df.plot(marker="o", figsize=(8, 3.8), logx=False)
    ax.set(ylabel="NDCG@10 vs CTR real (todo el catálogo)", title="Exposure bias: sin exploración no hay corrección posible"); plt.show()
    ''')
    M(r"""
    Con ε = 0 los dos estimadores solo reordenan los 10 ítems que la política vieja mostraba: el NDCG queda clavado en el
    de la política anterior. Con un poco de exploración, IPS recupera rápidamente el orden verdadero, y el conteo ingenuo
    queda sesgado hacia la exposición vieja. 🧠 La exploración no es caridad para el *long tail*: es **la única fuente de
    datos insesgados** que tendrás y la base de toda OPE (módulo 14).

    ### 4.2 *Candidate-set mismatch*: la paradoja de Berkson entre etapas

    💡 El ranker se entrena con **impresiones** (lo que pasó todas las etapas anteriores) pero en *serving* puntúa **todos
    los candidatos** del retriever, una distribución mucho más amplia. Peor: la selección previa crea **correlaciones
    espurias**. Si el retriever deja pasar los ítems con *afinidad + popularidad* alta, dentro de las impresiones un ítem
    poco popular **tiene que** tener afinidad alta para estar ahí, así que afinidad y popularidad aparecen **negativamente
    correlacionadas** aunque en el catálogo sean independientes (paradoja de Berkson, *collider bias*). El ranker aprende
    pesos que solo valen dentro de la selección.

    Esto es el *sample selection bias* de los sistemas en cascada: RankFlow (Qin et al., SIGIR 2022) entrena cada etapa con
    datos generados por las etapas anteriores; Kuaishou (Zheng et al., WWW 2024, *Full Stage Learning to Rank*) modela
    explícitamente el sesgo de selección de las etapas siguientes; Alibaba (*On Ranking Consistency of Pre-ranking Stage*,
    2022) y Meta (Wang et al., 2023, *early stage ads ranking*) atacan la consistencia entre etapas con distilación y
    multi-tarea.
    """)
    C(r'''
    rng = np.random.default_rng(seed)
    n_req, n_cand, k_imp = 4000 * S, 200, 10
    f_aff = rng.normal(size=(n_req, n_cand)); f_pop = rng.normal(size=(n_req, n_cand)); f_bait = rng.normal(size=(n_req, n_cand))
    true_logit = -3 + 1.0 * f_aff + 0.6 * f_pop - 0.8 * f_bait            # «bait»: engancha al retriever pero no convierte
    y_all = rng.random((n_req, n_cand)) < sigmoid(true_logit)
    retr = f_aff + f_pop + 0.9 * f_bait + rng.normal(0, 0.5, (n_req, n_cand))   # el retriever premia el bait
    shown = np.argsort(-retr, 1)[:, :k_imp]
    Xall = np.stack([f_aff, f_pop, f_bait], -1)
    Ximp = np.take_along_axis(Xall, shown[..., None], 1).reshape(-1, 3)
    yimp = np.take_along_axis(y_all, shown, 1).ravel()
    print("corr(afinidad, popularidad) en el catálogo:", np.corrcoef(f_aff.ravel(), f_pop.ravel())[0, 1].round(3),
          "· en las impresiones:", np.corrcoef(Ximp[:, 0], Ximp[:, 1])[0, 1].round(3))

    unexp = np.argsort(-retr, 1)[:, k_imp:]                          # candidatos NO expuestos
    j = rng.integers(0, unexp.shape[1], (n_req, 20)); unexp_s = np.take_along_axis(unexp, j, 1)
    Xun = np.take_along_axis(Xall, unexp_s[..., None], 1).reshape(-1, 3)
    from sklearn.linear_model import LogisticRegression
    half = n_req // 2 * k_imp
    m_imp = LogisticRegression().fit(Ximp[:half], yimp[:half])
    m_aug = LogisticRegression().fit(np.r_[Ximp[:half], Xun[: half * 2]], np.r_[yimp[:half], np.zeros(half * 2)],
                                     sample_weight=np.r_[np.ones(half), np.full(half * 2, 0.5)])
    m_oracle = LogisticRegression().fit(Xall[: n_req // 2].reshape(-1, 3), y_all[: n_req // 2].ravel())
    te = slice(n_req // 2, None)
    Xte, yte = Xall[te].reshape(-1, 3), y_all[te].ravel()
    rows = []
    for name, m_ in [("solo impresiones", m_imp), ("impresiones + no expuestos como negativos", m_aug), ("oráculo (todas las etiquetas)", m_oracle)]:
        sc = m_.predict_proba(Xte)[:, 1].reshape(-1, n_cand); yt = y_all[te]
        top10 = np.argsort(-sc, 1)[:, :10]
        rows.append({"ranker": name, "pesos (aff, pop, bait)": np.round(m_.coef_[0], 2),
                     "AUC sobre 200 candidatos": roc_auc_score(yte, sc.ravel()),
                     "conversiones en top-10": np.take_along_axis(yt, top10, 1).sum(1).mean()})
    cand = pd.DataFrame(rows).set_index("ranker"); display(cand)
    ''')
    C(r'''
    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    idx = rng.choice(len(Ximp), 3000, replace=False)
    ax[0].scatter(f_aff.ravel()[:3000], f_pop.ravel()[:3000], s=3, alpha=0.3, label="catálogo")
    ax[0].scatter(Ximp[idx, 0], Ximp[idx, 1], s=3, alpha=0.4, color="#dc2626", label="impresiones")
    ax[0].set(xlabel="afinidad", ylabel="popularidad", title="Berkson: la selección crea correlación negativa"); ax[0].legend(markerscale=4)
    cand["conversiones en top-10"].plot.barh(ax=ax[1], color=["#dc2626", "#2563eb", "#16a34a"])
    ax[1].set_title("Calidad del ranker sobre la distribución de serving"); ax[1].set_xlabel("conversiones esperadas en el top-10")
    plt.tight_layout(); plt.show()
    ''')
    M(r"""
    El ranker entrenado solo con impresiones **casi no penaliza el *bait*** (el retriever ya filtró el bait malo, así que
    dentro de las impresiones apenas se distingue) y sobre los 200 candidatos de *serving* elige peor. Añadir candidatos
    **no expuestos** como negativos (con peso menor, porque algunos habrían convertido) acerca el entrenamiento a la
    distribución de *serving*. Es un *trade-off* consciente: introduces un sesgo pequeño en la etiqueta para eliminar uno
    grande en la distribución. Alternativas en producción: tráfico de exploración con propensiones, y **distilación**
    del ranker final sobre los candidatos de la etapa anterior.

    ### 4.3 Consistencia del funnel y distilación entre etapas

    La etapa temprana (*pre-ranking*) tiene un presupuesto de cómputo mínimo y features baratas. Su objetivo **no** es
    predecir clics bien, sino **no perder lo que el ranker final pondría arriba**. La métrica correcta es el *recall* del
    top-k del ranker final dentro del top-N de la etapa temprana (lo que Alibaba llama *ranking consistency*).
    Comparamos un pre-ranker entrenado con clics de impresiones frente a uno **distilado** del ranker final sobre todos los
    candidatos.
    """)
    C(r'''
    rng = np.random.default_rng(seed + 1)
    n_req2, n_c = 3000 * S, 500
    Xc = rng.normal(size=(n_req2, n_c, 6))                                  # 6 features; el pre-ranker solo ve las 2 primeras
    w_final = np.array([1.0, 0.7, 0.8, 0.5, -0.6, 0.4])
    final = Xc @ w_final                                                     # ranker final (lo tomamos como verdad)
    yclk = rng.random((n_req2, n_c)) < sigmoid(final - 4)
    imp = np.argsort(-final, 1)[:, :20]                                       # solo se ven las 20 primeras
    Xi = np.take_along_axis(Xc[..., :2], imp[..., None], 1).reshape(-1, 2); yi = np.take_along_axis(yclk, imp, 1).ravel()
    from sklearn.linear_model import LinearRegression
    pre_clicks = LogisticRegression().fit(Xi, yi)
    sub = rng.integers(0, n_c, (n_req2, 50))
    Xd = np.take_along_axis(Xc[..., :2], sub[..., None], 1).reshape(-1, 2); yd = np.take_along_axis(final, sub, 1).ravel()
    pre_distill = LinearRegression().fit(Xd, yd)


    def funnel_recall(pre_scores, N, k=10):
        top_final = np.argsort(-final, 1)[:, :k]; top_pre = np.argsort(-pre_scores, 1)[:, :N]
        return np.mean([len(set(a) & set(b)) / k for a, b in zip(top_final, top_pre)])


    Ns = [10, 20, 50, 100, 200]
    flat = Xc[..., :2].reshape(-1, 2)
    sc_clk = pre_clicks.decision_function(flat).reshape(n_req2, n_c); sc_dis = pre_distill.predict(flat).reshape(n_req2, n_c)
    fig, ax = plt.subplots(figsize=(8, 3.8))
    ax.plot(Ns, [funnel_recall(sc_clk, N) for N in Ns], "o-", label="pre-ranker entrenado con clics de impresiones")
    ax.plot(Ns, [funnel_recall(sc_dis, N) for N in Ns], "s-", label="pre-ranker distilado del ranker final")
    ax.set(xlabel="N candidatos que pasan al ranker final", ylabel="recall del top-10 final", title="Consistencia del funnel")
    ax.legend(fontsize=8); plt.show()
    print("pesos pre-ranker (clics):", pre_clicks.coef_.round(2), "· (distilado):", pre_distill.coef_.round(2), "· verdad:", w_final[:2])
    ''')
    M(r"""
    🧠 **Selection bias del modelo anterior, resumido para una entrevista:** «Cada etapa se entrena con datos que filtró la
    etapa anterior *y* el modelo anterior en producción. Por eso (1) mido la calidad de cada etapa sobre la distribución
    que verá en *serving*, (2) entreno las etapas tempranas para la consistencia con la final (distilación, *recall*
    del funnel) y no para el clic, (3) mantengo tráfico de exploración con propensiones logueadas y (4) cuando cambio una
    etapa, reentreno o reevalúo las siguientes, porque su distribución de entrada ha cambiado.»

    *Counterfactual LTR* (Joachims et al., WSDM 2017; módulo 07) es el mismo principio aplicado a la posición: el clic
    depende de dónde se mostró, y la propensión de cada posición se puede estimar sin intervenir aprovechando que
    varios rankers en producción ponen el mismo documento en posiciones distintas (*intervention harvesting*, Agarwal et
    al., WSDM 2019).
    """)
