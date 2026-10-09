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
        ax.text(x, 4.25, t, ha="center", va="center", fontsize=6.6, color="#b91c1c",
                bbox=dict(fc="#fee2e2", ec="#b91c1c", boxstyle="round,pad=0.25"))
        arrow(ax, (x, 3.85), (x, 3.25), color="#b91c1c")
    ax.text(1.2, 1.25, "feedback loop: el sistema\ngenera sus propios datos (§4)", fontsize=8, color="#475569")
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

    🧪 **Experimento.** Un problema de CTR sintético con 20 000 ítems Zipf y factores latentes conocidos; la torre de usuario es
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
    n_users, n_items, k_true, D = 2000, 20_000, 8, 16
    n_samples = 600_000 * S
    rng = np.random.default_rng(seed)
    P = rng.normal(0, 0.8, (n_users, k_true)); Q = rng.normal(0, 0.8, (n_items, k_true)); bias_i = rng.normal(-2.0, 0.6, n_items)
    item_p = 1.0 / np.arange(1, n_items + 1) ** 0.9; item_p /= item_p.sum()
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

    🧠 **El fenómeno de una época.** Alibaba (Zhang et al., CIKM 2022) documentó que los modelos de CTR profundos
    **empeoran bruscamente al empezar la segunda época**: las tablas de embeddings, muy dispersas y con optimizadores de
    convergencia rápida (Adam), memorizan los ejemplos de la cola. Por eso en la industria se entrena **una sola pasada**
    sobre los datos (y por eso el *streaming* encaja tan bien). Lo reproducimos con la tabla completa:
    """)
    C(r'''
    torch.manual_seed(seed)
    model_ep = CTRModel(nn.Embedding(n_items, D)).to(device); nn.init.normal_(model_ep.item.weight, std=0.05)
    opt = torch.optim.Adam(model_ep.parameters(), lr=0.01)
    U, I, Y = (torch.as_tensor(a, device=device) for a in (users[:cut], items[:cut], y[:cut]))
    Ut, It = torch.as_tensor(users[cut:], device=device), torch.as_tensor(items[cut:], device=device)
    curve, steps_per_epoch = [], math.ceil(cut / 4096)
    for ep in range(4):
        for k_, s_ in enumerate(torch.randperm(cut, device=device).split(4096)):
            loss = F.binary_cross_entropy_with_logits(model_ep(U[s_], I[s_]), Y[s_])
            opt.zero_grad(); loss.backward(); opt.step()
            if k_ % (steps_per_epoch // 4) == 0:
                with torch.no_grad():
                    p = torch.sigmoid(model_ep(Ut, It)).cpu().numpy()
                curve.append((ep + k_ / steps_per_epoch, log_loss(y[cut:], p), loss.item()))
    cv = np.array(curve)
    plt.figure(figsize=(8, 3.6)); plt.plot(cv[:, 0], cv[:, 1], "o-", label="log-loss test"); plt.plot(cv[:, 0], cv[:, 2], ".", alpha=0.5, label="log-loss del lote de train")
    for e_ in range(1, 4): plt.axvline(e_, color="gray", ls=":")
    plt.xlabel("época"); plt.ylabel("log-loss"); plt.title("One-epoch phenomenon: la segunda pasada memoriza la cola"); plt.legend(); plt.show()
    ''')

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

    # ------------------------------------------------------------------ 5. long term
    M(r"""
    ## 5. Medir la verdad a largo plazo

    ### 💡 El problema
    Todo lo que optimizas es un **proxy**: clic, *watch time*, conversión a 7 días. La métrica de verdad (retención,
    satisfacción, valor de vida del cliente) llega tarde y es ruidosa. Ley de Goodhart: *cuando una medida se convierte en
    objetivo, deja de ser una buena medida*. En recomendación el caso típico es el **clickbait**: sube el CTR, baja la
    satisfacción y, semanas después, la retención. Un A/B de dos semanas puede declarar ganador al sistema que está
    destruyendo valor. Hohnhold, O'Brien & Tang (Google, KDD 2015) midieron cómo los usuarios **aprenden** a ignorar
    anuncios de baja calidad (*ads blindness*) con experimentos de larga duración, y usaron el resultado para reducir la
    carga de anuncios en móvil.

    ### Las herramientas de los equipos top
    - **Holdouts globales / long-term holdbacks**: un % pequeño de usuarios no recibe los lanzamientos de un periodo
      (trimestre, semestre). Mide el efecto **acumulado** de todos los lanzamientos y detecta los que solo funcionaban por
      novedad. Coste: esos usuarios reciben un producto peor.
    - **Encuestas como etiquetas**: YouTube mide *valued watchtime* con encuestas de 1 a 5 estrellas tras ver un vídeo,
      cuenta solo las de 4–5 y entrena un modelo que **predice la respuesta** para todo el mundo (blog oficial de YouTube,
      2021). Netflix habla de una recompensa *proxy* de satisfacción a largo plazo (Netflix TechBlog, 2024).
    - ***Value models***: el score final es una fusión de predicciones (clic, *watch*, like, compartir, encuesta, «no me
      interesa») con **pesos de negocio** que se fijan con experimentos, no con *grid search* offline.
    - ***Surrogate index*** (módulo 15): predecir el efecto a largo plazo desde métricas tempranas.

    🧪 **Simulación.** 4 000 usuarios durante 90 días. Cada ítem tiene un nivel de *clickbait* $c$ y de calidad $q$. El
    clic sube con ambos; la satisfacción tras el clic sube con $q$ y **baja** con $c$. La probabilidad de volver al día
    siguiente depende de la satisfacción acumulada. Comparamos políticas que ordenan por
    $\;V_w = p_{clic} \cdot p_{sat}^{\,w}$, de $w=0$ (solo clic) a $w=2$, más un holdout no personalizado.
    """)
    C(r'''
    def long_term_sim(w, days=90, n_users=4000 * S, n_items=500, k=10, seed_=seed, holdout=False):
        r = np.random.default_rng(seed_)
        c = r.normal(0, 1, n_items); q = r.normal(0, 1, n_items)
        aff = r.normal(0, 0.7, (n_users, n_items))
        p_click = sigmoid(-2.2 + 0.9 * c + 0.5 * q + aff)
        p_sat = sigmoid(0.2 + 1.2 * q - 0.9 * c)
        score = r.normal(size=(n_users, n_items)) if holdout else p_click * p_sat ** w
        top = np.argsort(-score, 1)[:, :k]
        pc_top, ps_top = np.take_along_axis(p_click, top, 1), p_sat[top]
        h = np.zeros(n_users); active = np.ones(n_users, bool); out = []
        for d in range(days):
            clicks = (r.random(pc_top.shape) < pc_top) & active[:, None]
            sat = clicks & (r.random(pc_top.shape) < ps_top)
            unsat = clicks & ~sat
            h = 0.85 * h + 0.15 * (sat.sum(1) - 1.5 * unsat.sum(1))
            out.append({"día": d, "DAU": active.mean(), "CTR": clicks.sum() / max(active.sum() * k, 1),
                        "clics por usuario": clicks.sum() / n_users, "satisfechos por usuario": sat.sum() / n_users})
            active = r.random(n_users) < sigmoid(1.2 + 1.2 * h)
        return pd.DataFrame(out)


    ws = [0.0, 0.5, 1.0, 1.5, 2.0]
    sims = {w: long_term_sim(w) for w in ws}
    hold = long_term_sim(0, holdout=True)
    fig, ax = plt.subplots(1, 3, figsize=(15, 4))
    for w in [0.0, 1.0, 2.0]:
        ax[0].plot(sims[w]["CTR"].rolling(3, min_periods=1).mean(), label=f"w={w}")
        ax[1].plot(sims[w]["DAU"], label=f"w={w}")
    ax[1].plot(hold["DAU"], "k:", label="holdout (sin personalizar)")
    ax[0].axvspan(0, 14, color="orange", alpha=0.12); ax[0].text(1, ax[0].get_ylim()[1] * 0.98, "A/B de 2 semanas", fontsize=8, va="top")
    ax[0].set(xlabel="día", ylabel="CTR", title="Proxy: CTR"); ax[1].set(xlabel="día", ylabel="usuarios activos", title="Verdad: retención")
    ax[0].legend(fontsize=8); ax[1].legend(fontsize=8)
    short = [sims[w]["clics por usuario"][:14].sum() for w in ws]; long_ = [sims[w]["clics por usuario"].sum() for w in ws]
    sat_ = [sims[w]["satisfechos por usuario"].sum() for w in ws]
    ax[2].plot(ws, np.array(short) / short[0], "o-", label="clics totales, 14 días")
    ax[2].plot(ws, np.array(long_) / long_[0], "s-", label="clics totales, 90 días")
    ax[2].plot(ws, np.array(sat_) / sat_[0], "^-", label="visionados satisfechos, 90 días")
    ax[2].set(xlabel="peso w de la satisfacción en el value model", ylabel="relativo a w=0", title="Goodhart: el óptimo depende del horizonte")
    ax[2].legend(fontsize=8); plt.tight_layout(); plt.show()
    display(pd.DataFrame({"CTR 14 días": [sims[w]["CTR"][:14].mean() for w in ws], "DAU día 90": [sims[w]["DAU"].iloc[-1] for w in ws],
                          "clics 90 días / usuario": long_}, index=[f"w={w}" for w in ws]).round(4))
    ''')
    M(r"""
    El A/B de dos semanas elige **w = 0** (más CTR). A 90 días gana un *value model* con peso en la satisfacción: menos clics
    por sesión, pero muchos más usuarios que vuelven, y más clics **totales**. El holdout sin personalizar te da la
    referencia del **valor acumulado** del sistema. 🧠 Nota cómo el ranking de políticas **se invierte con el horizonte**:
    por eso los equipos top deciden con *guardrails* de satisfacción y holdouts largos, y no solo con el proxy del A/B.

    ### 5.1 Encuestas como etiquetas: corrige el sesgo de respuesta

    Solo responde quien quiere. Si los usuarios muy activos (y más satisfechos) responden más, la media de las respuestas
    sobreestima la satisfacción y un modelo entrenado con ellas hereda el sesgo. Corrección: modelar la **probabilidad de
    responder** con features que tienes de todos y ponderar las respuestas por su inversa (IPW), o predecir la respuesta
    para todos (lo que describe YouTube).
    """)
    C(r'''
    rng = np.random.default_rng(seed)
    n = 100_000
    engagement = rng.normal(0, 1, n)
    sat_true = (rng.random(n) < sigmoid(0.3 + 0.9 * engagement)).astype(int)     # 1 = satisfecho (4–5 estrellas)
    p_resp = sigmoid(-3 + 1.2 * engagement)                                        # los activos responden más
    resp = rng.random(n) < p_resp
    resp_model = LogisticRegression().fit(engagement[:, None], resp)
    p_hat = resp_model.predict_proba(engagement[:, None])[:, 1]
    pred_model = LogisticRegression().fit(engagement[resp][:, None], sat_true[resp])
    est = {"verdad (toda la población)": sat_true.mean(), "media de respuestas": sat_true[resp].mean(),
           "IPW por propensión de respuesta": np.sum(sat_true[resp] / p_hat[resp]) / np.sum(1 / p_hat[resp]),
           "predecir la respuesta para todos": pred_model.predict_proba(engagement[:, None])[:, 1].mean()}
    print(f"tasa de respuesta: {resp.mean():.1%}")
    pd.Series(est).plot.barh(figsize=(8, 2.8), color=["#16a34a", "#dc2626", "#2563eb", "#7c3aed"], title="% satisfechos estimado")
    plt.xlim(0.4, 0.8); plt.show()
    ''')
    M(r"""
    ### 5.2 ¿Cuánto holdout? Coste vs sensibilidad

    Un holdout de fracción $h$ sobre $N$ usuarios detecta efectos con $\text{MDE} \approx (z_{1-\alpha/2} + z_{1-\beta})\,\sigma
    \sqrt{\tfrac{1}{hN} + \tfrac{1}{(1-h)N}}$ y cuesta $h \cdot \Delta$ del valor que aportan los lanzamientos. Como el MDE
    mejora solo con $\sqrt{h}$, los holdouts de 1–5 % son la norma en plataformas grandes: con decenas de millones de
    usuarios, incluso el 1 % detecta efectos acumulados pequeños.
    """)
    C(r'''
    hs = np.linspace(0.002, 0.2, 100)
    fig, ax = plt.subplots(figsize=(8, 3.8)); ax2 = ax.twinx()
    for N, c_ in [(1e6, "C0"), (1e7, "C1"), (1e8, "C2")]:
        mde = 2.8 * 1.0 * np.sqrt(1 / (hs * N) + 1 / ((1 - hs) * N))      # σ = 1 (métrica estandarizada)
        ax.plot(hs * 100, mde * 100, color=c_, label=f"N = {N:.0e} usuarios")
    ax2.plot(hs * 100, hs * 100, "k--", label="coste: % de usuarios sin lanzamientos")
    ax.set(xlabel="tamaño del holdout (%)", ylabel="MDE (% de σ)", yscale="log", title="Holdout global: sensibilidad vs coste")
    ax2.set_ylabel("coste (% usuarios)"); ax.legend(fontsize=8, loc="upper center"); ax2.legend(fontsize=8, loc="upper right"); plt.show()
    ''')

    # ------------------------------------------------------------------ 6. casebook
    M(r"""
    ## 6. *Casebook*: «offline ↑, online ↓»

    Es el incidente más común y más caro de la profesión: el modelo nuevo gana offline, se lanza, y el A/B sale plano o
    negativo. Un ingeniero top no adivina: **formula hipótesis comprobables** y las descarta en orden de coste. Diez casos
    reales o realistas (los marcados con 📄 tienen fuente pública del patrón):

    | # | Síntoma | Hipótesis | Diagnóstico | Arreglo |
    |---|---|---|---|---|
    | 1 | +3 % NDCG offline, 0 % online | **Fuga temporal**: split aleatorio o features calculadas con el futuro 📄 (Ji et al., TOIS 2023) | Reevaluar con split temporal global; *time-travel audit* de cada feature (recalcular *as-of* y comparar) | Point-in-time en todo el pipeline; split temporal en el CI |
    | 2 | El ranker nuevo empeora al cambiar el retriever | **Candidate mismatch**: entrenado con impresiones del sistema viejo 📄 (RankFlow, 2022) | *Adversarial validation*: clasificador «train vs serving» sobre las features; AUC ≫ 0,5 = distribuciones distintas | Entrenar con candidatos del retriever actual, negativos no expuestos, distilación |
    | 3 | Tras un rediseño de UI, el CTR predicho deja de cuadrar | **Cambio de posición/layout**: el sesgo de posición aprendido ya no vale 📄 (PAL, 2019) | Calibración por posición y superficie antes/después; *reliability diagram* por slot | Posición como feature solo en train (fijada en serving); reestimar propensiones |
    | 4 | Gana offline, pierde en *novelty* y diversidad | **Popularidad**: el modelo nuevo concentra en la cabeza; la métrica offline premia acertar lo popular | Desglosar métricas por decil de popularidad; cobertura y Gini de exposición | Métricas por segmento como *guardrail*; corrección de popularidad; re-ranking |
    | 5 | La personalización «llega tarde» tras una sesión | **Caché stale**: embedding de usuario o recomendaciones cacheadas con TTL largo | Histograma de edad de la caché por petición; % de recomendados ya vistos | Invalidación por evento; TTL corto para usuarios activos; clave con versión |
    | 6 | Tras desplegar, el recall cae a casi aleatorio en un % de tráfico | **Embeddings desalineados**: torre de usuario vN con índice de ítems vN-1 | *Golden queries*: consultas con resultados conocidos; distribución de scores coseno | Desplegar torre e índice **atómicamente**, versión en la clave; canario con golden set |
    | 7 | Los ítems nuevos nunca despegan | **Cold start**: filas por defecto + test offline que excluye ítems nuevos | Métricas por edad del ítem; % de impresiones a ítems < 7 días | Features de contenido, *boost* de exploración, embeddings iniciales desde contenido |
    | 8 | El A/B gana la primera semana y luego se desvanece | **Efecto novedad** 📄 (Kohavi et al., 2020) | Efecto por día desde la primera exposición (cohortes) | Duraciones mínimas, análisis por cohorte, holdback |
    | 9 | Offline mejora el clic, online cae el tiempo de visionado | **Etiqueta equivocada**: optimizas clic (incluye clickbait) | Correlación entre ganancia offline del proxy y métrica online en lanzamientos previos | *Value model* multiobjetivo, encuestas, *guardrails* |
    | 10 | Calidad online diferente entre apps (iOS vs Android) | **Skew de features**: un cliente envía otra unidad o el valor por defecto | Informe de skew por plataforma con log-and-wait | Contrato de features versionado y validado en el *edge* |

    ### Árbol de triaje (en este orden, de más barato a más caro)
    """)
    C(r'''
    fig, ax = plt.subplots(figsize=(12, 5)); ax.set_xlim(0, 12); ax.set_ylim(0, 6); ax.axis("off")
    steps = [("¿El A/B es válido?\nSRM, logging, bucketing", "#fee2e2"), ("¿Sirves el modelo que crees?\nversión, caché, índice", "#ffedd5"),
             ("¿Las features coinciden?\nlog-and-wait skew report", "#fef9c3"), ("¿La evaluación offline\nes honesta? fuga / split", "#dcfce7"),
             ("¿Misma distribución?\ncandidatos, posición, UI", "#e0f2fe"), ("¿Proxy ≠ objetivo?\nGoodhart, novedad, largo plazo", "#ede9fe")]
    for k_, (t_, c_) in enumerate(steps):
        x = 0.2 + k_ * 1.95
        box(ax, (x, 3.3), 1.75, 1.3, t_, c_, fs=7.8)
        if k_ < len(steps) - 1:
            arrow(ax, (x + 1.75, 3.95), (x + 1.95, 3.95), "no")
        ax.text(x + 0.87, 2.85, "sí → arreglar aquí", ha="center", fontsize=7.5, color="#b91c1c")
    costs = ["minutos", "minutos", "horas", "horas", "días", "semanas"]
    for k_, c_ in enumerate(costs):
        ax.text(0.2 + k_ * 1.95 + 0.87, 2.4, f"coste: {c_}", ha="center", fontsize=7.5, color="#475569")
    ax.text(6, 5.3, "Triaje de «offline ↑ online ↓»: descarta primero lo barato y lo que invalida todo lo demás", ha="center", fontsize=10.5)
    ax.text(6, 1.4, "Regla: no investigues el modelo hasta que los pasos 1–3 estén limpios — la mayoría de incidentes muere ahí.", ha="center", fontsize=9, style="italic")
    plt.show()
    ''')
    M(r"""
    ### 6.1 Caso 6 en código: embeddings desalineados y *golden queries*

    El bug más silencioso del retrieval: se publica la torre de usuario v2 mientras el índice ANN sigue con ítems v1 (o
    al revés), o una caché guarda vectores de usuario de la versión anterior. No hay error, no hay excepción: solo
    recomendaciones peores. Si v2 se entrenó desde cero, los espacios no tienen relación (rotación arbitraria) y el recall
    se desploma; si se hizo *warm-start*, están **parcialmente** alineados y la caída es moderada — lo cual es peor,
    porque nadie la nota. Defensa: un conjunto de ***golden queries*** (usuarios sintéticos o reales con vecinos conocidos)
    que se evalúa en cada despliegue, y vigilar la **distribución de scores** del top-K.
    """)
    C(r'''
    rng = np.random.default_rng(seed)
    n_it, dim = 20_000, 32
    true_items = rng.normal(size=(n_it, dim)); true_items /= np.linalg.norm(true_items, axis=1, keepdims=True)
    users_ = rng.normal(size=(500, dim)); users_ /= np.linalg.norm(users_, axis=1, keepdims=True)
    gold = np.argsort(-(users_ @ true_items.T), 1)[:, :20]                  # vecinos «correctos» de cada golden query


    def rotation(angle):
        A_ = rng.normal(size=(dim, dim)); A_ = (A_ - A_.T) / 2; A_ /= np.linalg.norm(A_, 2)
        from scipy.linalg import expm
        return expm(angle * A_)


    rows = []
    for name, R in [("misma versión", np.eye(dim)), ("warm-start (rotación 0,3 rad)", rotation(0.3)),
                    ("warm-start (rotación 0,8 rad)", rotation(0.8)), ("reentreno desde cero", np.linalg.qr(rng.normal(size=(dim, dim)))[0])]:
        q = users_ @ R                                                       # vector de usuario de OTRA versión
        sc = q @ true_items.T
        top = np.argsort(-sc, 1)[:, :20]
        rows.append({"caso": name, "recall@20 golden": np.mean([len(set(a) & set(b)) / 20 for a, b in zip(top, gold)]),
                     "score medio top-1": np.sort(sc, 1)[:, -1].mean(), "scores": np.sort(sc, 1)[:, -20:].ravel()})
    gq = pd.DataFrame(rows).set_index("caso")
    display(gq.drop(columns="scores").round(3))
    fig, ax = plt.subplots(1, 2, figsize=(12, 3.8))
    gq["recall@20 golden"].plot.barh(ax=ax[0], color=["#16a34a", "#f59e0b", "#ea580c", "#dc2626"]); ax[0].set_title("Golden queries: recall@20")
    for name, r_ in gq.iterrows():
        ax[1].hist(r_["scores"], bins=40, alpha=0.5, density=True, label=name)
    ax[1].set(title="Distribución de scores del top-20 (un monitor barato)", xlabel="producto escalar"); ax[1].legend(fontsize=7)
    plt.tight_layout(); plt.show()
    ''')
    M(r"""
    ### 6.2 Caso 8 en código: separar el efecto novedad del efecto real

    En un A/B el efecto medio por **día de calendario** mezcla usuarios que acaban de descubrir el cambio con usuarios que
    llevan semanas con él. Analiza el efecto por **días desde la primera exposición**: si decae, es novedad.
    """)
    C(r'''
    rng = np.random.default_rng(seed)
    n_u, days = 20_000, 28
    first = rng.integers(0, days, n_u)                                      # día en que cada usuario entra al experimento
    treat = rng.random(n_u) < 0.5
    rows = []
    for d in range(days):
        act = first <= d
        tenure = d - first[act]
        effect = np.where(treat[act], 0.01 + 0.06 * np.exp(-tenure / 3.0), 0.0)    # efecto real 1 % + novedad 6 % que decae
        y = rng.normal(1.0 + effect, 0.5)
        rows.append(pd.DataFrame({"día": d, "antigüedad": tenure, "trat": treat[act], "y": y}))
    ab = pd.concat(rows)
    by_day = ab.groupby(["día", "trat"]).y.mean().unstack(); by_ten = ab.groupby(["antigüedad", "trat"]).y.mean().unstack()
    fig, ax = plt.subplots(1, 2, figsize=(12, 3.8))
    ax[0].plot((by_day[True] / by_day[False] - 1) * 100, "o-"); ax[0].set(xlabel="día de calendario", ylabel="lift %", title="Vista habitual: lift por día")
    ax[1].plot((by_ten[True] / by_ten[False] - 1) * 100, "o-", color="C1"); ax[1].axhline(1, ls="--", color="k", label="efecto real (1 %)")
    ax[1].set(xlabel="días desde la primera exposición", ylabel="lift %", title="Vista correcta: lift por antigüedad"); ax[1].legend()
    plt.tight_layout(); plt.show()
    ''')

    # ------------------------------------------------------------------ 7. performance
    M(r"""
    ## 7. Ingeniería de rendimiento y *capacity planning*

    ### 7.1 Presupuesto de latencia por etapa

    El SLO es de **extremo a extremo** y en p99. Cada etapa recibe un presupuesto, y el *fan-out* (pedir features a 20
    servicios, buscar en 50 shards) hace que el p99 de la etapa sea el p99 del **más lento**. Cifras ilustrativas de un feed
    con SLO de 200 ms p99 (no son de ninguna empresa concreta; los órdenes de magnitud sí son típicos):
    """)
    C(r'''
    stages_ = pd.DataFrame({
        "etapa": ["red + gateway", "features de usuario", "retrieval (ANN, 5 fuentes)", "features de candidatos", "pre-ranking (2 000)",
                  "ranking (500, GPU)", "re-ranking + reglas", "hidratación + respuesta"],
        "p50 ms": [8, 4, 10, 8, 6, 18, 3, 5], "p99 ms": [25, 15, 30, 25, 12, 45, 8, 15]})
    fig, ax = plt.subplots(figsize=(11, 3.8))
    left = 0
    for k_, r_ in stages_.iterrows():
        ax.barh(1, r_["p99 ms"], left=left, color=plt.cm.tab10(k_), edgecolor="w"); ax.text(left + r_["p99 ms"] / 2, 1, r_["etapa"], ha="center", va="center", fontsize=7, rotation=90)
        left += r_["p99 ms"]
    left = 0
    for k_, r_ in stages_.iterrows():
        ax.barh(0, r_["p50 ms"], left=left, color=plt.cm.tab10(k_), edgecolor="w"); left += r_["p50 ms"]
    ax.axvline(200, color="#dc2626", ls="--"); ax.text(201, 1.45, "SLO 200 ms p99", color="#dc2626", fontsize=8)
    ax.set_yticks([0, 1]); ax.set_yticklabels(["suma de p50", "suma de p99\n(cota pesimista)"]); ax.set_xlabel("ms")
    ax.set_title(f"Presupuesto de latencia: suma de p99 = {stages_['p99 ms'].sum()} ms (las colas no se suman linealmente, pero es la cota que usa el SRE)")
    plt.show()
    ''')
    M(r"""
    ### 7.2 *Dynamic batching*: throughput contra latencia

    Una GPU (o una CPU con SIMD) es mucho más eficiente procesando lotes. El servidor espera hasta reunir $B_{max}$
    peticiones **o** hasta que pasa un *timeout* $\tau$, y procesa el lote con coste $a + bB$ ($a$ = coste fijo: lanzamiento de
    kernels, RPC, copia; $b$ = coste marginal por ejemplo). Es lo que hacen Triton (*dynamic batcher*) y DeepRecSys
    (Gupta et al., ISCA 2020, que duplica el throughput limitado por latencia ajustando el tamaño de lote y el paralelismo).
    Simulación de eventos discretos:
    """)
    C(r'''
    def batching_sim(qps, b_max, tau_ms, a_ms=4.0, b_ms=0.15, n=20_000, seed_=seed):
        r = np.random.default_rng(seed_)
        arr = np.cumsum(r.exponential(1000 / qps, n))
        lat, i, free_at = np.empty(n), 0, 0.0
        while i < n:
            start_wait = max(arr[i], free_at)
            j = i
            deadline = arr[i] + tau_ms
            while j + 1 < n and j + 1 - i < b_max and arr[j + 1] <= max(deadline, free_at):
                j += 1
            full = j + 1 - i == b_max
            launch = max(free_at, arr[j] if full else deadline)      # lote lleno: sale ya; si no, espera al timeout
            launch = max(launch, start_wait)
            done = launch + a_ms + b_ms * (j + 1 - i)
            lat[i:j + 1] = done - arr[i:j + 1]
            free_at, i = done, j + 1
        return np.percentile(lat, 50), np.percentile(lat, 99)


    loads = np.array([100, 200, 400, 800, 1200, 1600, 2000, 2400])
    fig, ax = plt.subplots(figsize=(8.5, 4))
    for b_max, tau in [(1, 0), (8, 2), (32, 5), (128, 10)]:
        p99 = [batching_sim(q, b_max, tau)[1] for q in loads]
        ax.plot(loads, p99, "o-", label=f"B_max={b_max}, τ={tau} ms")
    ax.axhline(50, color="#dc2626", ls="--", lw=0.8); ax.text(110, 53, "presupuesto de la etapa: 50 ms", color="#dc2626", fontsize=8)
    ax.set(xlabel="QPS por réplica", ylabel="p99 latencia (ms)", yscale="log", title="Dynamic batching: sin lotes la réplica se satura a ~250 QPS")
    ax.legend(fontsize=8); plt.show()
    ''')
    M(r"""
    Sin batching ($B_{max}=1$) cada petición paga el coste fijo $a$: la réplica se satura cuando $\text{QPS} \cdot (a+b) > 1000$
    ms. Con lotes, el coste fijo se reparte y la capacidad se multiplica, a cambio de unos ms de espera ($\tau$). El punto
    óptimo es **el mayor throughput que cumple el presupuesto de p99**, no el máximo throughput.

    ### 7.3 *Fan-out* y *hedged requests*

    Si una petición consulta $n$ shards en paralelo y cada uno tiene un 1 % de respuestas lentas, la probabilidad de que
    **alguno** sea lento es $1-0{,}99^n$: con 100 shards, el 63 %. *The Tail at Scale* (Dean & Barroso, 2013) propone
    ***hedged requests***: si un shard no responde en su p95, envía un duplicado a otra réplica y quédate con la primera
    respuesta. Coste: ~5 % más de carga.
    """)
    C(r'''
    rng = np.random.default_rng(seed)
    def shard_lat(size):
        base = rng.lognormal(np.log(5), 0.3, size)
        return np.where(rng.random(size) < 0.01, base * 12, base)           # 1 % de respuestas lentas (GC, colas, red)
    p95 = np.percentile(shard_lat(100_000), 95)
    fan = [1, 5, 10, 25, 50, 100, 200]
    plain, hedged = [], []
    for n_ in fan:
        a_, b_ = shard_lat((5000, n_)), shard_lat((5000, n_))
        plain.append(np.percentile(a_.max(1), 99))
        hedged.append(np.percentile(np.where(a_ > p95, np.minimum(a_, p95 + b_), a_).max(1), 99))
    plt.figure(figsize=(8, 3.6)); plt.plot(fan, plain, "o-", label="sin hedging"); plt.plot(fan, hedged, "s-", label="hedged en p95")
    plt.xscale("log"); plt.xlabel("nº de shards (fan-out)"); plt.ylabel("p99 de la petición (ms)"); plt.legend()
    plt.title("Tail at scale: el fan-out convierte el 1 % lento en la norma"); plt.show()
    ''')
    M(r"""
    ### 7.4 Caché del embedding de usuario: *hit rate* vs frescura

    Calcular la torre de usuario en cada petición cuesta; cachearla ahorra cómputo pero **sirve un usuario del pasado**. Si
    el usuario acaba de ver tres películas de terror, una caché con TTL de 1 h ignora su intención de la sesión. La
    alternativa madura es **invalidación por evento** (precomputación *nearline*: cada evento relevante recalcula el
    vector en segundo plano) con un TTL de seguridad.
    """)
    C(r'''
    rng = np.random.default_rng(seed)
    def cache_sim(ttl_min, invalidate=False, n_users=2000, horizon_min=24 * 60, dim=16):
        rate_req, rate_evt = 1 / 30, 1 / 45                                  # una petición cada 30 min, un evento cada 45 min
        hits = tot = 0; cos = []
        for _ in range(n_users):
            t_req = np.cumsum(rng.exponential(1 / rate_req, 80)); t_req = t_req[t_req < horizon_min]
            t_evt = np.cumsum(rng.exponential(1 / rate_evt, 80)); t_evt = t_evt[t_evt < horizon_min]
            v = rng.normal(size=dim); states = [v.copy()]
            for _e in t_evt:
                v = 0.8 * v + 0.6 * rng.normal(size=dim); states.append(v.copy())
            cached_t, cached_v = -1e9, None
            for tr in t_req:
                cur = states[np.searchsorted(t_evt, tr)]
                stale_evt = invalidate and cached_v is not None and np.any((t_evt > cached_t) & (t_evt < tr))
                if cached_v is not None and tr - cached_t < ttl_min and not stale_evt:
                    hits += 1; cos.append(cur @ cached_v / np.linalg.norm(cur) / np.linalg.norm(cached_v))
                else:
                    cached_t, cached_v = tr, cur; cos.append(1.0)
                tot += 1
        return hits / tot, np.mean(cos)
    ttls = [1, 5, 15, 30, 60, 120, 360]
    res_c = [cache_sim(t_) for t_ in ttls]; res_i = [cache_sim(t_, invalidate=True) for t_ in ttls]
    fig, ax = plt.subplots(1, 2, figsize=(12, 3.6))
    ax[0].plot(ttls, [r_[0] for r_ in res_c], "o-", label="solo TTL"); ax[0].plot(ttls, [r_[0] for r_ in res_i], "s-", label="TTL + invalidación por evento")
    ax[1].plot(ttls, [r_[1] for r_ in res_c], "o-", label="solo TTL"); ax[1].plot(ttls, [r_[1] for r_ in res_i], "s-", label="TTL + invalidación por evento")
    ax[0].set(xscale="log", xlabel="TTL (min)", ylabel="hit rate", title="Ahorro de cómputo"); ax[1].set(xscale="log", xlabel="TTL (min)", ylabel="coseno(cacheado, actual)", title="Frescura del vector servido")
    ax[0].legend(fontsize=8); ax[1].legend(fontsize=8); plt.tight_layout(); plt.show()
    ''')
    M(r"""
    ### 7.5 Cuantización del ranker y retrieval en GPU

    Dos palancas de cómputo que se usan siempre: **cuantización int8 de las capas densas** del ranker (PyTorch
    `quantize_dynamic` en CPU; TensorRT/Triton en GPU) y **retrieval por fuerza bruta en GPU**: para catálogos de hasta
    decenas de millones, un `matmul` + `topk` en GPU es más simple y a menudo más rápido que un índice ANN (FAISS GPU,
    Johnson, Douze & Jégou, 2017). Medimos ambos (en CPU con `FAST_DEV_RUN`; en una T4 verás la diferencia real).
    """)
    C(r'''
    ranker = nn.Sequential(nn.Linear(256, 512), nn.ReLU(), nn.Linear(512, 256), nn.ReLU(), nn.Linear(256, 1)).eval()
    xb = torch.randn(500, 256)                                              # 500 candidatos × 256 features
    def bench(fn, reps=30):
        fn(); t0 = time.perf_counter()
        for _ in range(reps): fn()
        return (time.perf_counter() - t0) / reps * 1000
    with torch.no_grad():
        ref = ranker(xb).squeeze()
        try:
            qr = torch.ao.quantization.quantize_dynamic(ranker, {nn.Linear}, dtype=torch.qint8)
            out_q = qr(xb).squeeze(); t_q = bench(lambda: qr(xb))
        except Exception as e:                                              # algunos builds no traen backend de cuantización
            print("quantize_dynamic no disponible:", type(e).__name__); qr, out_q, t_q = None, ref, float("nan")
        t_f = bench(lambda: ranker(xb))
    from scipy.stats import spearmanr
    print(f"fp32: {t_f:.2f} ms · int8 dinámico: {t_q:.2f} ms · Spearman de los scores: {spearmanr(ref, out_q).correlation:.4f}")

    sizes = [100_000, 1_000_000] if FAST_DEV_RUN else [100_000, 1_000_000, 10_000_000]
    rows = []
    for n_ in sizes:
        E = torch.randn(n_, 64, device=device, dtype=torch.float16 if device == "cuda" else torch.float32)
        for bsz in [1, 32, 256]:
            Qb = torch.randn(bsz, 64, device=device, dtype=E.dtype)
            def run():
                s_ = Qb @ E.T; v_, i_ = torch.topk(s_, 100, dim=1)
                if device == "cuda": torch.cuda.synchronize()
            ms_ = bench(run, reps=5)
            rows.append({"catálogo": n_, "batch": bsz, "ms/lote": ms_, "consultas/s": bsz / ms_ * 1000})
        del E
    gpu_df = pd.DataFrame(rows); display(gpu_df.round(2))
    for n_, g in gpu_df.groupby("catálogo"):
        plt.plot(g["batch"], g["consultas/s"], "o-", label=f"{n_:,} ítems")
    plt.xscale("log"); plt.yscale("log"); plt.xlabel("consultas por lote"); plt.ylabel("consultas/s")
    plt.title(f"Retrieval exacto por fuerza bruta en {device.upper()}: el batching multiplica el throughput"); plt.legend(); plt.show()
    ''')
    M(r"""
    ### 7.6 *Capacity planning* con órdenes de magnitud

    Dimensionar una flota es aritmética con supuestos explícitos. Para el ranking:
    $$\text{FLOP/s necesarios} = \text{QPS}_{pico} \times \text{candidatos} \times \text{FLOPs por candidato}$$
    $$\text{GPUs} = \left\lceil \frac{\text{FLOP/s necesarios}}{\text{FLOP/s efectivos por GPU} \times \text{utilización objetivo}} \right\rceil \times \text{redundancia}$$
    Los FLOP/s **efectivos** de un ranker de recsys son una fracción pequeña del pico de la hoja de datos (los *lookups* de
    embeddings están limitados por memoria). Suponemos un 10–20 %; mídelo con tu modelo antes de comprar nada.
    """)
    C(r'''
    def capacity(name, dau, req_per_user_day, peak_factor, n_cand, mflops_per_cand, gpu_tflops=65, eff=0.15, util=0.6, redundancy=1.5):
        qps_peak = dau * req_per_user_day / 86400 * peak_factor
        need = qps_peak * n_cand * mflops_per_cand * 1e6
        gpus = math.ceil(need / (gpu_tflops * 1e12 * eff * util) * redundancy)
        return {"caso": name, "QPS pico": f"{qps_peak:,.0f}", "PFLOP/s necesarios": round(need / 1e15, 2), "GPUs (con N+50 %)": gpus}
    plan = pd.DataFrame([
        capacity("CineMatch (10 M DAU)", 10e6, 6, 3, 500, 20),
        capacity("Feed vídeo corto (500 M DAU)", 500e6, 60, 2, 1000, 50),
        capacity("Feed vídeo corto, ranker 10× más grande", 500e6, 60, 2, 1000, 500),
    ]).set_index("caso"); display(plan)
    cands = np.array([100, 250, 500, 1000, 2000, 4000])
    plt.figure(figsize=(8, 3.6))
    for mf in [10, 50, 200]:
        plt.plot(cands, [capacity("x", 500e6, 60, 2, c_, mf)["GPUs (con N+50 %)"] for c_ in cands], "o-", label=f"{mf} MFLOPs/candidato")
    plt.xscale("log"); plt.yscale("log"); plt.xlabel("candidatos rankeados por petición"); plt.ylabel("GPUs (T4 fp16 ≈ 65 TFLOP/s pico)")
    plt.title("El nº de candidatos es el dial de coste más caro del sistema"); plt.legend(fontsize=8); plt.show()
    ''')
    M(r"""
    🧠 **Lo que un staff engineer dice en la revisión de capacidad:** «el coste escala con QPS × candidatos × FLOPs; antes
    de pedir GPUs, ¿podemos (1) recortar candidatos con un pre-ranker más consistente (§4.3), (2) cachear los scores de
    ítems que no dependen del usuario, (3) mover cómputo de usuario a *nearline*, (4) cuantizar, (5) *batchear*? Y el
    presupuesto se aprueba con el **ROI medido en un A/B**: cuánto engagement compra cada GPU extra».
    """)

    # ------------------------------------------------------------------ 8. culture
    M(r"""
    ## 8. Cómo piensan los equipos top

    ### 8.1 La experimentación como forma de decidir (la «Netflix way»)
    La serie *Decision Making at Netflix* (Tingley et al., Netflix TechBlog, 2021) parte de una idea: las alternativas a
    experimentar (que decida el jefe, copiar a la competencia, debatir) incorporan pocos puntos de vista; un A/B bien
    diseñado deja que decidan los miembros. Lo que eso implica en el día a día de un equipo de recomendación:

    - **Hipótesis antes que modelo.** Cada experimento empieza con una hipótesis causal sobre el usuario («los perfiles
      nuevos abandonan porque la primera fila no refleja lo que eligieron en el onboarding»), no con «probar un transformer».
    - **Métricas decididas antes de ver datos**: primaria, secundarias y *guardrails*, con su MDE y duración. Cambiar la
      métrica primaria a posteriori es *p-hacking*.
    - **Embudo de evaluación**: offline → (OPE) → interleaving para podar → A/B para decidir → holdback para confirmar.
    - **El coste de ingeniería cuenta**: del Netflix Prize, Netflix integró dos algoritmos (SVD y RBM) pero no el ensemble
      ganador, porque la ganancia de precisión adicional no justificaba el esfuerzo de ingeniería (Amatriain & Basilico,
      *Netflix Recommendations: Beyond the 5 stars*, 2012).
    - **Métricas que se validan**: una métrica nueva se adopta tras comprobar su **sensibilidad** (¿se mueve con cambios
      reales?) y su **direccionalidad** (¿se mueve en el sentido de la north star?) sobre experimentos históricos — Deng &
      Shi (Microsoft), KDD 2016, *Data-Driven Metric Development for Online Controlled Experiments*.
    """)
    C(r'''
    fig, ax = plt.subplots(figsize=(12, 4)); ax.set_xlim(0, 12); ax.set_ylim(0, 4.4); ax.axis("off")
    box(ax, (4.6, 3.3), 2.8, 0.8, "North star\nretención · valor a largo plazo", "#fde68a", fs=8.5)
    for k_, (t_, c_) in enumerate([("Proxies online\nhoras de calidad, take rate", "#dcfce7"), ("Guardrails\nlatencia, quejas, diversidad,\nsatisfacción (encuestas)", "#fee2e2"),
                                   ("Métricas offline\nNDCG temporal, calibración,\nrecall del funnel", "#e0f2fe")]):
        x = 0.6 + k_ * 3.9
        box(ax, (x, 1.7), 3.0, 0.95, t_, c_, fs=8)
        arrow(ax, (x + 1.5, 2.65), (6.0, 3.3))
    for k_, t_ in enumerate(["debug: CTR por slot, % ya visto", "debug: p99 por etapa, skew", "debug: AUC por cohorte, cola"]):
        x = 0.6 + k_ * 3.9
        box(ax, (x, 0.3), 3.0, 0.7, t_, "#f1f5f9", fs=7.8); arrow(ax, (x + 1.5, 1.0), (x + 1.5, 1.7))
    ax.set_title("Árbol de métricas: cada nivel se valida contra el de arriba (sensibilidad y direccionalidad)", fontsize=10.5); plt.show()
    ''')
    M(r"""
    ### 8.2 Revisión de experimentos: un *checklist* ejecutable

    En los equipos maduros, ningún experimento se lanza sin pasar una revisión ligera. Convertirla en código (un linter
    del *experiment doc*) hace que la cultura escale más allá de los seniors que la tienen en la cabeza.
    """)
    C(r'''
    REQUIRED = {
        "hipótesis": "hipótesis causal sobre el usuario",
        "métrica_primaria": "una sola métrica primaria", "guardrails": "≥ 2 guardrails (latencia, satisfacción…)",
        "mde": "efecto mínimo detectable", "duración_días": "duración ≥ 1 semana completa (estacionalidad semanal)",
        "unidad": "unidad de aleatorización", "chequeo_srm": "chequeo de sample ratio mismatch",
        "análisis_novedad": "análisis por antigüedad de exposición", "plan_rollback": "plan de rollback",
        "riesgos_skew": "verificación de paridad de features (log-and-wait)",
    }


    def review_experiment(doc: dict) -> pd.DataFrame:
        rows = []
        for k_, desc in REQUIRED.items():
            v = doc.get(k_)
            ok = v not in (None, "", [], 0)
            if k_ == "guardrails" and ok: ok = len(v) >= 2
            if k_ == "duración_días" and ok: ok = v >= 7
            if k_ == "métrica_primaria" and ok: ok = isinstance(v, str)
            rows.append({"item": k_, "requisito": desc, "estado": "✅" if ok else "❌", "valor": v})
        return pd.DataFrame(rows).set_index("item")


    doc = {"hipótesis": "La fila 'Porque viste X' con candidatos secuenciales sube las horas de calidad de usuarios con < 5 títulos",
           "métrica_primaria": ["horas", "CTR"], "guardrails": ["p99 latencia"], "mde": 0.01, "duración_días": 5,
           "unidad": "perfil", "chequeo_srm": True, "plan_rollback": "flag en el router"}
    rev = review_experiment(doc); display(rev)
    print(f"{(rev['estado'] == '❌').sum()} bloqueos antes del lanzamiento")
    ''')
    M(r"""
    ### 8.3 *Design docs* de recomendación: la plantilla que usan los buenos
    1. **Contexto y problema** (con datos: «el 38 % de los perfiles nuevos no reproduce nada en 7 días»).
    2. **Objetivos y no-objetivos** (qué *no* vamos a resolver).
    3. **Métricas**: north star, proxy, guardrails; cómo se relacionan (evidencia histórica).
    4. **Diseño**: datos y etiquetas (definición exacta del positivo, ventana de atribución, *label delay*), features
       (con *owner* y PIT), modelo, etapa del funnel afectada y **qué etapas aguas abajo cambian de distribución**.
    5. **Alternativas descartadas** y por qué (incluido «no hacer nada» y la heurística simple).
    6. **Plan de evaluación**: offline (split, métricas por segmento), OPE, interleaving, A/B, holdback.
    7. **Coste**: cómputo de entrenamiento y *serving* (capacity planning §7.6), latencia por etapa, mantenimiento.
    8. **Riesgos y *pre-mortem***: «es dentro de 6 meses y esto ha fallado, ¿por qué?» — skew, feedback loop, Goodhart,
       fairness, privacidad.
    9. **Plan de lanzamiento y rollback**, con *kill switch* y *owner* de guardia.

    ### 8.4 Señales de seniority en entrevistas (y en el trabajo)

    | Tema | Respuesta junior | Respuesta senior / staff |
    |---|---|---|
    | «¿Cómo evalúas el modelo?» | NDCG en un split aleatorio | Split temporal, *full ranking*, por segmento (nuevos, cola), y por qué la métrica offline correlaciona (o no) con la online |
    | «El A/B salió plano» | Probar otro modelo | Triaje §6: validez del A/B, versión servida, skew, fuga, distribución, proxy |
    | Features | Lista de features | PIT, *owner*, frescura, coste de *serving*, cómo se loguean (log-and-wait) |
    | Escala | «Usamos FAISS» | QPS × candidatos × FLOPs, presupuesto por etapa, p99, caché, coste por mil peticiones |
    | Datos | «Usamos los clics» | Exposure bias, propensiones, exploración, *label delay*, definición del positivo |
    | Objetivo | «Maximizar CTR» | *Value model*, guardrails de satisfacción, holdouts, efecto a largo plazo |
    | Lanzamiento | «Si gana, se lanza» | Shadow → canary → A/B con duración prefijada → holdback; *rollback* probado |
    | Trade-offs | Elige una opción | Hace explícitas las alternativas, sus costes y **qué evidencia cambiaría su decisión** |

    🧠 La señal más fuerte de seniority no es saber más modelos: es **preguntar por los datos y por la medición antes que
    por la arquitectura**, y cuantificar con órdenes de magnitud.
    """)

    # ------------------------------------------------------------------ 9. closing
    M(r"""
    ## 9. 🏭 En producción (resumen con fuentes)

    - **ByteDance / Monolith** (2022): tabla sin colisiones (Cuckoo HashMap), filtro de frecuencia, expiración de IDs,
      entrenamiento online con *joiner* y sincronización frecuente de filas tocadas; en producción en BytePlus Recommend.
    - **Meta**: tablas de embeddings como cuello de botella (DLRM 2019; Gupta et al., HPCA 2020); QR embeddings (KDD 2020),
      mixed-dimension (2019/2021), TT-Rec (MLSys 2021), cuantización 4 bits por fila en producción (Guan et al., 2019);
      consistencia entre etapas en *early-stage ads ranking* (Wang et al., 2023).
    - **Twitter**: *double hashing* por frecuencia redujo ~90 % el tamaño de modelos (Zhang et al., RecSys 2020); entrenamiento
      continuo con *delayed feedback* (Ktena et al., RecSys 2019).
    - **Criteo / Chapelle** (KDD 2014): modelo de *delayed feedback* para conversiones.
    - **Alibaba**: *one-epoch phenomenon* (CIKM 2022); consistencia del pre-ranking (2022).
    - **Kuaishou**: *Full Stage Learning to Rank* (WWW 2024) para el sesgo de selección de un sistema multi-etapa.
    - **YouTube**: *valued watchtime* medido con encuestas y predicho para todos (2021).
    - **Google**: efectos a largo plazo con experimentos de larga duración (Hohnhold et al., KDD 2015); *Rules of ML* (log de
      features servidas, regla 29).
    - **Netflix**: experimentación como forma de decidir (2021), interleaving + A/B, recompensa *proxy* de satisfacción a
      largo plazo (2024).

    ## 🧠 Secretos de la élite (nuevos: complementan los 38 del módulo 18)

    1. **Mide las colisiones ponderadas por tráfico y separadas cabeza/cola.** La métrica global casi no se mueve porque la
       cabeza domina sus filas; la cola y los ítems nuevos quedan enterrados (§1.1).
    2. **Nunca `id % m`.** Con IDs estructurados (snowflake, bits de shard) usarás una fracción ridícula de la tabla; pasa
       siempre por un hash mezclador (§1.1).
    3. **El estado del optimizador puede pesar más que el modelo**: Adam triplica la memoria de las tablas; Adagrad por
       filas guarda un escalar por fila (FBGEMM/TorchRec) (§1).
    4. **Cuantiza por fila y valida con el top-K**, no con el error de reconstrucción; cuantiza más la cola (§1.3).
    5. **Una sola época**: los modelos de CTR con tablas dispersas sobreajustan bruscamente en la segunda pasada (Alibaba,
       CIKM 2022) (§1.2).
    6. **El intervalo de sincronización es un hiperparámetro de calidad** y el filtro de frecuencia no pierde nada: un ID
       con dos eventos no aprende, solo ocupa memoria (Monolith) (§2).
    7. **El *learning rate* online es un dial frescura↔olvido**; usa *replay* y *guardrails* antes de cada sync (§2.3).
    8. **La curva de maduración de la etiqueta** (tasa de positivos vs edad del ejemplo) es el detector de *label delay*;
       el sesgo castiga a lo nuevo (§3.1).
    9. **Las fugas de ventana inclusiva escalan como 1/conteo**: son máximas en la cola, invisibles en la AUC global (§3.2).
    10. **El PSI no ve el skew fila a fila**: compara features servidas vs recalculadas por `request_id` (§3.3).
    11. **Dentro de las impresiones las correlaciones son mentira** (Berkson): evalúa cada etapa sobre la distribución que
        verá en *serving* (§4.2).
    12. **El objetivo de una etapa temprana es la consistencia con la final**, no el CTR: mide el *recall* del funnel (§4.3).
    13. **El ranking de políticas se invierte con el horizonte**: decide con holdouts y *guardrails* de satisfacción (§5).
    14. **Los *warm-starts* hacen silenciosos los bugs de versión**: *golden queries* en cada despliegue (§6.1).
    15. **El efecto novedad se ve por antigüedad de exposición**, no por día de calendario (§6.2).
    16. **El nº de candidatos es el dial de coste más caro**; el mejor ahorro suele ser un pre-ranker más consistente (§7.6).

    ## ⚠️ Errores comunes
    - Elegir el tamaño de la tabla hasheada mirando la log-loss global (oculta la cola).
    - Entrenar varias épocas sobre tablas dispersas «porque en visión se hace».
    - Activar entrenamiento online sin validación continua ni *snapshots* para volver atrás.
    - Entrenar conversiones con los clics de las últimas horas como negativos sin corrección.
    - Contadores agregados por hora y unidos por hora (ventana inclusiva).
    - Monitorizar el skew solo con PSI/KS por distribuciones.
    - Evaluar el ranker nuevo solo sobre impresiones del sistema viejo.
    - Decidir lanzamientos con un A/B de una semana sobre un proxy de clic.
    - Desplegar la torre de usuario y el índice de ítems por separado.
    - Optimizar el throughput máximo en lugar del throughput que cumple el p99.
    """)
    M(r"""
    ## 📝 Autoevaluación

    1. Con $N/m = 2$, ¿qué fracción de IDs colisiona y por qué esa cifra **no** basta para decidir el tamaño de la tabla?
    <details><summary>Respuesta</summary>≈ 1 − e^{-2} ≈ 86 %. Lo relevante es la contaminación ponderada por tráfico y por segmento: con Zipf, la cabeza domina sus filas y casi no se contamina, mientras que la cola (y los nuevos) recibe sobre todo el gradiente de otros IDs. Hay que medir calidad en cabeza y cola.</details>

    2. ¿Por qué QR embeddings dan una representación única con $(N/q + q)\,d$ parámetros y el hashing no?
    <details><summary>Respuesta</summary>Porque (⌊i/q⌋, i mod q) identifica unívocamente a i (particiones complementarias): dos IDs comparten como mucho una de las dos filas, y la combinación (producto, suma) es distinta. En hashing dos IDs que colisionan son indistinguibles.</details>

    3. En Monolith, ¿qué problema resuelven el filtro de frecuencia y la expiración, y qué coste tienen?
    <details><summary>Respuesta</summary>Acotan la memoria de una tabla sin colisiones que si no crecería sin límite (IDs efímeros, IDs muertos). Coste: los IDs nuevos usan un embedding por defecto hasta superar el umbral, y un ID expirado que vuelve empieza de cero; se mitiga con features de contenido.</details>

    4. Escribe la verosimilitud de un clic no convertido observado tras $e$ días en el modelo de Chapelle y explica qué segmento sufre más el estimador ingenuo.
    <details><summary>Respuesta</summary>1 − p + p·e^{−λe}. El ingenuo trata todos los no observados como negativos; sufre más lo que tiene clics recientes (campañas, estrenos, ítems en crecimiento).</details>

    5. Un contador `ctr_1h` da +4 puntos de AUC offline y nada online. Da dos hipótesis concretas y cómo las comprobarías.
    <details><summary>Respuesta</summary>(a) Ventana inclusiva: el contador incluye el propio evento → recalcular con ventana [t−1h, t) y comparar AUC; mirar la fuga por número de impresiones (mayor en la cola). (b) Skew por lag de streaming: comparar la feature logueada en serving con la recalculada offline para los mismos request_id.</details>

    6. ¿Por qué un ranker entrenado solo con impresiones puede aprender pesos con el signo equivocado?
    <details><summary>Respuesta</summary>Por la paradoja de Berkson: la selección de las etapas anteriores condiciona en una combinación de features, induciendo correlaciones espurias (p. ej. negativa entre afinidad y popularidad) y quitando variación en las features que el retriever ya filtró. Fuera de la selección esos pesos no valen.</details>

    7. Un A/B de 14 días favorece la política A en CTR. ¿Qué harías antes de lanzarla?
    <details><summary>Respuesta</summary>Mirar guardrails de satisfacción (encuestas, «no me interesa», abandono), analizar el efecto por antigüedad de exposición (novedad), comparar con un holdback/holdout más largo y, si hay riesgo de clickbait, un value model que incluya satisfacción.</details>

    8. Tienes 500 M DAU, 60 peticiones/usuario/día, pico ×2, 1 000 candidatos y 50 MFLOPs por candidato. ¿Cuántos PFLOP/s necesitas en pico?
    <details><summary>Respuesta</summary>QPS pico = 500e6·60/86 400·2 ≈ 694 000. FLOP/s = 694 000 · 1 000 · 50e6 ≈ 3,5·10^16 = 35 PFLOP/s efectivos — de ahí que el nº de candidatos y los FLOPs por candidato sean los diales de coste.</details>
    """)
    M(r"""
    ## 📚 Referencias

    **Tablas de embeddings**
    - Naumov et al. (2019). *Deep Learning Recommendation Model for Personalization and Recommendation Systems* (DLRM). [arXiv:1906.00091](https://arxiv.org/abs/1906.00091)
    - Weinberger et al. (2009). *Feature Hashing for Large Scale Multitask Learning*. ICML. [arXiv:0902.2206](https://arxiv.org/abs/0902.2206)
    - Shi, Mudigere, Naumov & Yang (2020). *Compositional Embeddings Using Complementary Partitions for Memory-Efficient Recommendation Systems*. KDD. [arXiv:1909.02107](https://arxiv.org/abs/1909.02107)
    - Ginart, Naumov, Mudigere, Yang & Zou (2019/2021). *Mixed Dimension Embeddings with Application to Memory-Efficient Recommendation Systems*. [arXiv:1909.11810](https://arxiv.org/abs/1909.11810)
    - Yin, Acun, Liu & Wu (2021). *TT-Rec: Tensor Train Compression for Deep Learning Recommendation Model Embeddings*. MLSys. [arXiv:2101.11714](https://arxiv.org/abs/2101.11714)
    - Zhang et al. (2020). *Model Size Reduction Using Frequency Based Double Hashing for Recommender Systems*. RecSys. [arXiv:2007.14523](https://arxiv.org/abs/2007.14523)
    - Guan et al. (2019). *Post-Training 4-bit Quantization on Embedding Tables*. [arXiv:1911.02079](https://arxiv.org/abs/1911.02079)
    - Micikevicius et al. (2022). *FP8 Formats for Deep Learning*. [arXiv:2209.05433](https://arxiv.org/abs/2209.05433)
    - Zhang et al. (2022). *Towards Understanding the Overfitting Phenomenon of Deep Click-Through Rate Prediction Models*. CIKM. [arXiv:2209.06053](https://arxiv.org/abs/2209.06053)
    - Gupta et al. (2020). *The Architectural Implications of Facebook's DNN-based Personalized Recommendation*. HPCA. [arXiv:1906.03109](https://arxiv.org/abs/1906.03109)

    **Entrenamiento online**
    - Liu et al. (2022). *Monolith: Real Time Recommendation System With Collisionless Embedding Table*. ORSUM@RecSys. [arXiv:2209.07663](https://arxiv.org/abs/2209.07663)
    - McMahan et al. (2013). *Ad Click Prediction: a View from the Trenches*. KDD.
    - Kirkpatrick et al. (2017). *Overcoming catastrophic forgetting in neural networks*. PNAS. [arXiv:1612.00796](https://arxiv.org/abs/1612.00796)
    - Wang et al. (2020). *A Practical Incremental Method to Train Deep CTR Models*. [arXiv:2009.02147](https://arxiv.org/abs/2009.02147)

    **Etiquetas, fugas y skew**
    - Chapelle (2014). *Modeling Delayed Feedback in Display Advertising*. KDD. [doi:10.1145/2623330.2623634](https://doi.org/10.1145/2623330.2623634)
    - Ktena et al. (2019). *Addressing Delayed Feedback for Continuous Training with Neural Networks in CTR prediction*. RecSys. [arXiv:1907.06558](https://arxiv.org/abs/1907.06558)
    - Zinkevich. *Rules of Machine Learning: Best Practices for ML Engineering* (Google). [developers.google.com](https://developers.google.com/machine-learning/guides/rules-of-ml)
    - Ji, Sun, Zhang & Li (2023). *A Critical Study on Data Leakage in Recommender System Offline Evaluation*. ACM TOIS. [arXiv:2010.11060](https://arxiv.org/abs/2010.11060)

    **Sesgos y funnel**
    - Schnabel et al. (2016). *Recommendations as Treatments: Debiasing Learning and Evaluation*. ICML. [arXiv:1602.05352](https://arxiv.org/abs/1602.05352)
    - Saito et al. (2020). *Unbiased Recommender Learning from Missing-Not-At-Random Implicit Feedback*. WSDM. [arXiv:1909.03601](https://arxiv.org/abs/1909.03601)
    - Joachims, Swaminathan & Schnabel (2017). *Unbiased Learning-to-Rank with Biased Feedback*. WSDM. [arXiv:1608.04468](https://arxiv.org/abs/1608.04468)
    - Agarwal, Zaitsev, Li & Joachims (2019). *Estimating Position Bias without Intrusive Interventions*. WSDM. [arXiv:1812.05161](https://arxiv.org/abs/1812.05161)
    - Qin et al. (2022). *RankFlow: Joint Optimization of Multi-Stage Cascade Ranking Systems as Flows*. SIGIR. [doi:10.1145/3477495.3532050](https://doi.org/10.1145/3477495.3532050)
    - Zheng et al. (2024). *Full Stage Learning to Rank: A Unified Framework for Multi-Stage Systems*. WWW. [arXiv:2405.04844](https://arxiv.org/abs/2405.04844)
    - *On Ranking Consistency of Pre-ranking Stage* (Alibaba, 2022). [arXiv:2205.01289](https://arxiv.org/abs/2205.01289)
    - Wang et al. (2023). *Towards the Better Ranking Consistency: A Multi-task Learning Framework for Early Stage Ads Ranking* (Meta). [arXiv:2307.11096](https://arxiv.org/abs/2307.11096)

    **Largo plazo y cultura**
    - Hohnhold, O'Brien & Tang (2015). *Focusing on the Long-term: It's Good for Users and Business*. KDD.
    - YouTube (2021). *On YouTube's recommendation system*. [blog.youtube](https://blog.youtube/inside-youtube/on-youtubes-recommendation-system/)
    - Netflix TechBlog (2024). *Recommending for Long-Term Member Satisfaction at Netflix*.
    - Tingley et al. (2021). *Decision Making at Netflix* (serie). Netflix TechBlog.
    - Amatriain & Basilico (2012). *Netflix Recommendations: Beyond the 5 stars (Part 1)*. Netflix TechBlog.
    - Deng & Shi (2016). *Data-Driven Metric Development for Online Controlled Experiments: Seven Lessons Learned*. KDD.
    - Kohavi, Tang & Xu (2020). *Trustworthy Online Controlled Experiments*. Cambridge University Press.

    **Rendimiento**
    - Dean & Barroso (2013). *The Tail at Scale*. CACM.
    - Gupta et al. (2020). *DeepRecSys: A System for Optimizing End-To-End At-scale Neural Recommendation Inference*. ISCA. [arXiv:2001.02772](https://arxiv.org/abs/2001.02772)
    - Johnson, Douze & Jégou (2017). *Billion-scale similarity search with GPUs*. [arXiv:1702.08734](https://arxiv.org/abs/1702.08734)
    """)
    nb.save(path)


# ---------------------------------------------------------------------------
# PROYECTO: pager duty de recsys
# ---------------------------------------------------------------------------
WORLD_CELL = r'''
# ⚙️ EL GEMELO DIGITAL — es la «realidad» del proyecto: NO lo modifiques.
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds
from scipy.linalg import expm
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

FAST_DEV_RUN = True                       # ⇦ False para la entrega (más días de logs y de producción)
N_LOG_DAYS, N_ONLINE_DAYS = (14, 4) if FAST_DEV_RUN else (21, 7)
REQ_FRAC = 0.3                            # fracción de usuarios que visita CineMatch cada día
rng = np.random.default_rng(seed)

N_U, N_I = int(ratings.user_id.max()) + 1, int(items_df.item_id.max()) + 1
X_ = csr_matrix((np.ones(len(ratings), np.float32), (ratings.user_id, ratings.item_id)), shape=(N_U, N_I))
u_, s_, vt_ = svds(X_, k=16, random_state=seed)
U_TRUE, V_TRUE = u_ * np.sqrt(s_), vt_.T * np.sqrt(s_)
A_TRUE = U_TRUE @ V_TRUE.T
A_TRUE = ((A_TRUE - A_TRUE.mean()) / A_TRUE.std()).astype(np.float32)          # afinidad real usuario×película
pop_hist = np.asarray(X_.sum(0)).ravel()
pop_z = (np.log1p(pop_hist) - np.log1p(pop_hist).mean()) / np.log1p(pop_hist).std()
quality = 0.4 * pop_z + 0.8 * np.minimum(pop_z, 0) + 0.8 * rng.normal(size=N_I)   # la cola larga tiene mucho «relleno»
release = -rng.integers(30, 1500, N_I).astype(float)                              # día de alta en el catálogo
new_items = rng.choice(np.arange(1, N_I), size=int(0.12 * N_I), replace=False)
release[new_items] = rng.uniform(-3, N_LOG_DAYS + N_ONLINE_DAYS, len(new_items))  # estrenos durante la simulación
release[0] = 1e9                                                                  # el ítem 0 no existe
pop_feat = pop_z.copy(); pop_feat[new_items] = 0.0       # la «popularidad histórica» de un estreno no se conoce: se imputa la media
POS_BIAS = 1.0 / (1 + np.arange(10)) ** 0.7
CONV_DELAY_MEAN = 3.0                                                             # días entre el clic y «terminó la película»
history = {u: list(g) for u, g in ratings.groupby("user_id").item_id}
for u in range(1, N_U):
    history.setdefault(u, [])


def sigmoid(x):
    return 1 / (1 + np.exp(-x))


def true_click_logit(u, items, day):
    age = day - release[items]
    trend = np.where(age >= 0, 1.6 * np.exp(-np.clip(age, 0, None) / 4.0), -np.inf)   # los estrenos tiran mucho unos días
    return -4.3 + 1.1 * A_TRUE[u, items] + 0.3 * pop_z[items] + trend


def true_conv_prob(u, items):
    return sigmoid(-2.0 + 0.5 * A_TRUE[u, items] + 1.3 * quality[items])


def available(day):
    return np.where(release <= day)[0]


def _learned(noise, seed_):
    r = np.random.default_rng(seed_)
    Q, _ = np.linalg.qr(r.normal(size=(16, 16)))
    E = (V_TRUE + noise * V_TRUE.std() * r.normal(size=V_TRUE.shape)) @ Q
    return (E / (np.linalg.norm(E, axis=1, keepdims=True) + 1e-8)).astype(np.float32)


def _rotation(angle, seed_):
    W = np.random.default_rng(seed_).normal(size=(16, 16)); W = (W - W.T) / 2
    return expm(angle * W / np.linalg.norm(W, 2))


EMB = {"v2": _learned(0.6, 2)}                                  # embeddings de ítem de la torre nueva (v2)
_v1 = (EMB["v2"] + 0.125 * np.random.default_rng(3).normal(size=EMB["v2"].shape)) @ _rotation(1.0, 4)
EMB["v1"] = (_v1 / np.linalg.norm(_v1, axis=1, keepdims=True)).astype(np.float32)   # v2 se entrenó con warm-start desde v1


def user_embedding(hist, version):
    v = EMB[version][hist[-50:]].mean(0) if len(hist) else np.zeros(16, np.float32)
    return v / (np.linalg.norm(v) + 1e-8)


print(f"{DATASET}: {N_U - 1} usuarios, {N_I - 1} películas, {len(new_items)} estrenos · {N_LOG_DAYS} días de logs + {N_ONLINE_DAYS} de producción")
'''

LOGS_CELL = r'''
def v1_policy(u, day, hist, k=10, r=rng):
    """CineMatch v1 (el sistema anterior): top-300 popular + estrenos, y 1 hueco de exploración aleatoria."""
    av = available(day); av = av[~np.isin(av, hist)]
    pool = av[(np.argsort(np.argsort(-pop_hist[av])) < 300) | (day - release[av] < 10)]
    sc = 1.0 * pop_z[pool] + 3.0 * (EMB["v1"][pool] @ user_embedding(hist, "v1"))
    if r is not None:
        sc = sc + r.gumbel(size=len(pool)) * 0.5
    shown = list(pool[np.argsort(-sc)[:k - (r is not None)]])
    explore = np.zeros(k, int)
    if r is not None:
        rest = av[~np.isin(av, shown)]; pos = int(r.integers(k))
        shown.insert(pos, int(r.choice(rest))); explore[pos] = 1
    return np.array(shown), explore


def generate_logs():
    rows, hist = [], {u: list(h) for u, h in history.items()}
    for day in range(N_LOG_DAYS):
        for u in rng.choice(np.arange(1, N_U), size=int(REQ_FRAC * N_U), replace=False):
            t = day + rng.random()
            shown, explore = v1_policy(u, day, hist[u])
            clk = rng.random(len(shown)) < POS_BIAS * sigmoid(true_click_logit(u, shown, day))
            conv = clk & (rng.random(len(shown)) < true_conv_prob(u, shown))
            delay = rng.exponential(CONV_DELAY_MEAN, len(shown))
            for p in range(len(shown)):
                rows.append((u, int(shown[p]), day, t, p, int(clk[p]), int(conv[p]), t + delay[p] if conv[p] else np.inf, int(explore[p])))
            hist[u] += [int(i) for i in shown[clk]]
    cols = ["user_id", "item_id", "day", "t", "position", "click", "conv", "conv_t", "explore"]
    return pd.DataFrame(rows, columns=cols), hist


logs, hist_after_logs = generate_logs()
print(f"logs: {len(logs):,} impresiones · CTR {logs.click.mean():.3f} · conversiones/clic {logs.conv.sum() / logs.click.sum():.2f} · exploración {logs.explore.mean():.1%}")
display(logs.head())
'''

PROD_CELL = r'''
# ============================  src/cinematch_v2.py  (código de PRODUCCIÓN)  ============================
PROD_CONFIG = dict(
    counter_window="inclusive",            # cómo se cortan las ventanas de los contadores en el pipeline de train
    hash_buckets=97,                       # tamaño de la tabla de contadores por ítem (None = exacta)
    age_unit_serving="hours",              # unidad con la que el servicio calcula la edad del título
    label_policy="observed",               # cómo se etiquetan los clics sin conversión todavía
    train_on="impressions_no_explore",     # qué filas de los logs usa el entrenamiento
    cache_key="user_id",                   # clave de la caché de usuario del servicio
    cache_invalidate_on_event=False,       # ¿se invalida la caché cuando el usuario hace clic?
)
FEATS = ["retr_score", "item_ctr_1d", "item_cvr_7d", "item_imps_7d", "item_age_days", "item_pop_hist", "user_n_hist", "position"]
T_TRAIN = float(N_LOG_DAYS)                # el pipeline de entrenamiento corre al final del último día de logs
SERVING_VERSION = "v2"


class Counters:
    """Contadores diarios por ítem (impresiones, clics, conversiones llegadas) en una tabla, opcionalmente hasheada."""
    def __init__(self, logs, n_days, hash_buckets=None):
        self.m = hash_buckets
        nb = hash_buckets or N_I
        self.imps, self.clk, self.cnv = (np.zeros((n_days + 2, nb)) for _ in range(3))
        b = self.bucket(logs.item_id.values)
        np.add.at(self.imps, (logs.day.values, b), 1); np.add.at(self.clk, (logs.day.values, b), logs.click.values)
        cv = logs[np.isfinite(logs.conv_t) & (logs.conv_t < n_days)]
        np.add.at(self.cnv, (np.floor(cv.conv_t.values).astype(int), self.bucket(cv.item_id.values)), 1)

    def bucket(self, items):
        items = np.asarray(items, dtype=np.int64)
        return items if self.m is None else (items * 2654435761 % 2**32) % self.m

    def asof(self, items, day, inclusive):
        """CTR del último día, CVR y log-impresiones de los últimos 7 días."""
        b, s_ = self.bucket(items), int(inclusive)
        ctr = (self.clk[day - 1 + s_, b] + 0.5) / (self.imps[day - 1 + s_, b] + 10.0)
        lo, hi = max(0, day - 7 + s_), day + s_
        cvr = (self.cnv[lo:hi, b].sum(0) + 1.0) / (self.clk[lo:hi, b].sum(0) + 4.0)
        return ctr, cvr, np.log1p(self.imps[lo:hi, b].sum(0))


def features(items, day, hist, emb_user, cfg, counters, serving, position=None):
    ctr, cvr, imps = counters.asof(items, int(day), inclusive=(cfg["counter_window"] == "inclusive") and not serving)
    age = day - release[items]
    if serving and cfg["age_unit_serving"] == "hours":
        age = age * 24
    return pd.DataFrame({"retr_score": EMB["v2"][items] @ emb_user, "item_ctr_1d": ctr, "item_cvr_7d": cvr,
                         "item_imps_7d": imps, "item_age_days": age, "item_pop_hist": pop_feat[items],
                         "user_n_hist": np.full(len(items), np.log1p(len(hist))),
                         "position": position if position is not None else np.zeros(len(items))})


def retrieve(emb_user, day, seen, k=100):
    av = available(day); av = av[~np.isin(av, seen)]
    sc = EMB["v2"][av] @ emb_user
    top = np.argpartition(-sc, min(k, len(av) - 1))[:k]
    return av[top[np.argsort(-sc[top])]]


def make_labels(L, cfg, T=T_TRAIN):
    """Etiqueta = «terminó la película» (conversión) observada en el instante T del pipeline."""
    L = L.copy()
    L["label"] = ((L.conv == 1) & (L.conv_t <= T)).astype(float)
    if cfg["label_policy"] == "soft":
        L = soft_labels(L, T)              # ← corrección (la implementas tú en el bug 5)
    return L


def build_training_frame(L, cfg, counters, logs_all):
    frames = []
    clicks = {u: g for u, g in logs_all[logs_all.click == 1].groupby("user_id")}
    if cfg["train_on"] == "impressions_no_explore":
        L = L[L.explore == 0]                          # «el tráfico de exploración ensucia las métricas»
    for (u, day), g in L.groupby(["user_id", "day"]):
        c_u = clicks.get(u)
        h = history[u] + ([] if c_u is None else c_u.item_id[c_u.day < day].tolist())
        f = features(g.item_id.values, day, h, user_embedding(h, "v2"), cfg, counters, serving=False, position=g.position.values)
        f["label"] = g.label.values
        f["w"] = np.where(g.explore.values == 1, EXPLORE_WEIGHT, 1.0) if cfg["train_on"] == "all_ipw" else 1.0
        f["user_id"], f["day"], f["item_id"], f["t"] = u, day, g.item_id.values, g.t.values
        frames.append(f)
    return pd.concat(frames, ignore_index=True)


def expand_soft(frame):
    """Etiquetas en (0,1) → dos filas ponderadas (y=1 con peso p, y=0 con peso 1−p)."""
    soft = (frame.label > 0) & (frame.label < 1)
    hard = frame[~soft].assign(label=frame.label[~soft].astype(int))
    if not soft.any():
        return hard
    pos = frame[soft].assign(w=lambda d: d.w * d.label, label=1)
    neg = frame[soft].assign(w=lambda d: d.w * (1 - d.label), label=0)
    return pd.concat([hard, pos, neg], ignore_index=True)


def train_ranker(frame):
    fr = expand_soft(frame)
    m = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.06, max_leaf_nodes=15, min_samples_leaf=40, random_state=seed)
    return m.fit(fr[FEATS], fr.label, sample_weight=fr.w)


def run_pipeline(cfg):
    """Pipeline nocturno: contadores → etiquetas → frame de train → ranker → evaluación offline en el último día."""
    counters = Counters(logs, N_LOG_DAYS + N_ONLINE_DAYS, cfg["hash_buckets"])
    L = make_labels(logs, cfg)
    val_day = N_LOG_DAYS - 1
    tr = build_training_frame(L[L.day < val_day], cfg, counters, logs)
    va = build_training_frame(L[(L.day == val_day) & (L.explore == 0)], cfg, counters, logs)
    model = train_ranker(tr)
    va = va[va.label.isin([0, 1])]
    auc = roc_auc_score(va.label, model.predict_proba(va[FEATS])[:, 1])
    return {"model": model, "counters": counters, "auc_offline": auc, "train_frame": tr, "val_frame": va, "cfg": cfg}


EXPLORE_WEIGHT = 5.0
'''

SERVE_CELL = r'''
import copy


def simulate_online(pipe, days=N_ONLINE_DAYS, seed_=7, policy="v2", log_requests=True):
    """Producción: CineMatch sirve a los usuarios durante `days` días. Devuelve métricas por petición y un log
    (log-and-wait) con las features EXACTAS servidas y el estado de la caché. Las métricas «reales» usan el gemelo digital."""
    cfg, model = pipe["cfg"], pipe["model"]
    counters = copy.deepcopy(pipe["counters"])            # el streaming de producción sigue alimentando los contadores
    r = np.random.default_rng(seed_)
    hist = {u: list(h) for u, h in hist_after_logs.items()}
    recent = set(logs[logs.day >= N_LOG_DAYS - 3].user_id)
    cache = {u: {"emb": user_embedding(hist[u], "v1"), "version": "v1", "hist": list(hist[u]), "ts": N_LOG_DAYS - 0.5} for u in recent}
    res, served_log = [], []
    for day in range(N_LOG_DAYS, N_LOG_DAYS + days):
        for u in r.choice(np.arange(1, N_U), size=int(REQ_FRAC * N_U), replace=False):
            t = day + r.random()
            if policy == "v1":
                top, _ = v1_policy(u, day, hist[u], r=None); ent = None
            else:
                ent = cache.get(u)
                if ent is None or (cfg["cache_key"] != "user_id" and ent["version"] != SERVING_VERSION):
                    ent = {"emb": user_embedding(hist[u], SERVING_VERSION), "version": SERVING_VERSION, "hist": list(hist[u]), "ts": t}
                    cache[u] = ent
                cands = retrieve(ent["emb"], day, ent["hist"], k=100)
                f = features(cands, day, ent["hist"], ent["emb"], cfg, counters, serving=True)
                order = np.argsort(-model.predict_proba(f[FEATS])[:, 1])
                top = cands[order[:10]]
                if log_requests:
                    served_log.append(f.assign(user_id=u, day=day, t=t, item_id=cands, served=np.isin(np.arange(len(cands)), order[:10]),
                                               cache_version=ent["version"], cache_age=t - ent["ts"], hist_len=len(ent["hist"]),
                                               true_hist_len=len(hist[u])))
            already = np.isin(top, hist[u])
            p_click = POS_BIAS * sigmoid(true_click_logit(u, top, day)) * np.where(already, 0.1, 1.0)   # re-recomendar lo visto casi no rinde
            exp_conv = float((p_click * true_conv_prob(u, top)).sum())
            clk = r.random(10) < p_click
            hist[u] += [int(i) for i in top[clk]]
            b = counters.bucket(top)
            np.add.at(counters.imps[day], b, 1); np.add.at(counters.clk[day], b, clk)
            conv = clk & (r.random(10) < true_conv_prob(u, top))
            conv_day = np.floor(t + r.exponential(CONV_DELAY_MEAN, 10)).astype(int)
            ok = conv & (conv_day < counters.cnv.shape[0])
            np.add.at(counters.cnv, (conv_day[ok], b[ok]), 1)
            if policy != "v1" and cfg["cache_invalidate_on_event"] and clk.any():
                cache.pop(u, None)
            res.append({"day": day, "user_id": u, "conv_esperadas": exp_conv, "ya_visto": already.mean(),
                        "estrenos": np.mean(day - release[top] < 7), "cache_v1": ent is not None and ent["version"] == "v1"})
    return OnlineRun(pd.DataFrame(res), pd.concat(served_log, ignore_index=True) if served_log else None, cache, hist)


class OnlineRun:
    """Resultado de producción: métricas por petición (se accede como a un DataFrame) + log servido, caché e historiales."""
    def __init__(self, df, served_log, cache, hist):
        self.df, self.served_log, self.cache, self.hist = df, served_log, cache, hist

    def __getattr__(self, name):
        return getattr(self.df, name)


def evaluate(cfg, label=""):
    pipe = run_pipeline(cfg)
    on = simulate_online(pipe)
    return pipe, on, {"config": label, "AUC offline": pipe["auc_offline"], "conv/petición": on.conv_esperadas.mean(),
                      "% ya visto": on.ya_visto.mean(), "% estrenos": on.estrenos.mean()}
'''


def project() -> None:
    path = f"{MOD}/19_proyecto_debugging_produccion.ipynb"
    nb = Notebook("Proyecto 19 · Pager duty de recsys", colab_path=path)
    M, C = nb.md, nb.code

    M(f"""
    {nb.badge()}

    # Proyecto 19 · *Pager duty* de recsys: depura CineMatch v2 en producción

    **Nivel:** 🔴 Experto · **Duración:** 6–10 h · **GPU:** no necesaria (CPU de Colab; `FAST_DEV_RUN=False` tarda ~15–25 min en total) · **Unidades Colab:** < 1

    **Prerrequisitos:** lección 19 (§3, §4, §6), módulos 16 (serving) y 17 (monitoreo).

    ## 📟 Contexto: son las 03:12 y suena el *pager*

    > **[ALERTA P1] cinematch-home · conversiones por petición −10 % vs semana anterior (48 h sostenido)**

    Hace dos días el equipo lanzó **CineMatch v2**: un retriever *two-tower* nuevo (embeddings v2, *warm-start* desde v1)
    y un ranker GBDT con contadores en tiempo real. En la revisión de lanzamiento, el ranker v2 tenía **una AUC offline
    excelente**. Online, las conversiones («el usuario terminó la película») han caído por debajo de las de v1.

    Eres la persona de guardia. Tienes el código de producción, los logs de los últimos días y un **gemelo digital** del
    tráfico (en la vida real no lo tendrías: aquí sirve para que puedas **medir el impacto real** de cada bug). El equipo
    sospecha que hay **varios** problemas a la vez: se han identificado **6 bugs plantados**, todos realistas y todos
    vistos en sistemas de verdad. Tu trabajo, como en un incidente real: **detectar** cada bug con una herramienta de
    diagnóstico (no leyendo el código: en producción el código tiene 200 000 líneas), **cuantificar** su impacto y
    **arreglarlo**, y escribir el *postmortem*.

    ## 📦 Dataset
    **MovieLens-100K** (GroupLens). Sus factores latentes (SVD) definen los gustos «reales» de los usuarios del gemelo
    digital; sobre ellos se simulan 14 días de logs del sistema v1 (con un 10 % de exploración) y los días de producción de
    v2. Sin red, se usa un MovieLens sintético con el mismo esquema (el notebook nunca se bloquea).

    ## ✅ Entregables y rúbrica (100 puntos)

    | Bloque | Puntos | Criterio |
    |---|---|---|
    | 6 bugs × (detección 5 + cuantificación 5 + arreglo 5) | 90 | **Detección**: la herramienta implementada muestra la anomalía con un número (no vale «leí el código»). **Cuantificación**: Δ conv/petición al arreglar solo ese bug sobre la config de producción. **Arreglo**: el cambio de config/código y la herramienta vuelve a verde |
    | *Postmortem* | 10 | Línea temporal, causa raíz de cada bug, por qué no lo vio la revisión de lanzamiento, acciones preventivas con *owner* |

    **Objetivos numéricos** (el *scorecard* final los comprueba):
    - conv/petición con todo arreglado ≥ **1,10 ×** la de la config de producción **y** ≥ **0,98 ×** la de v1;
    - % de recomendaciones ya vistas < **1 %**;
    - la AUC offline del pipeline arreglado es **honesta**: su diferencia con una evaluación sin fugas < 0,01.

    ## 🗺️ Plan
    1. Carga el gemelo digital, los logs y el código de producción (dado).
    2. Reproduce el incidente (dado).
    3. Construye tu caja de herramientas de diagnóstico (**TODOs**).
    4. Bug por bug, en el orden del árbol de triaje de la lección (§6): detecta → cuantifica → arregla.
    5. *Scorecard* y *postmortem*.
    6. ⛔ Solución de referencia completa.
    """)
    C(r'''
    !pip install -q numpy pandas matplotlib scikit-learn scipy
    ''')
    C(DATA_CELL)
    C(WORLD_CELL)
    M(r"""
    ## 1. Los logs del sistema anterior (v1)

    Cada fila es una impresión: usuario, película, día, instante `t`, posición, clic, conversión, instante de la conversión
    (`conv_t`, infinito si no convirtió) y si era el **hueco de exploración** (1 de cada 10, aleatorio sobre el catálogo).
    """)
    C(LOGS_CELL)
    M(r"""
    ## 2. El código de producción de CineMatch v2

    Esto es lo que corre en producción: contadores por ítem, features, retriever, pipeline de entrenamiento del ranker y
    servicio con caché de usuario. **Los bugs están aquí dentro.** Puedes leerlo, pero la rúbrica exige que cada bug lo
    **demuestre una herramienta** con un número: así es como se trabaja cuando el código es enorme y el incidente es ahora.
    """)
    C(PROD_CELL)
    C(SERVE_CELL)
    M(r"""
    ## 3. Reproduce el incidente

    Comparamos v1 (lo que había) con v2 tal como se lanzó. La «AUC offline» es la que vio la revisión de lanzamiento; la
    «conv/petición» es la métrica online (conversiones esperadas por petición, con el gemelo digital).
    """)
    C(r'''
    t0 = time.time()
    pipe_prod, online_prod, row_prod = evaluate(PROD_CONFIG, "v2 producción")
    online_v1 = simulate_online(pipe_prod, policy="v1")
    def v1_scores(frame):
        """Score heurístico de v1 sobre las mismas filas de validación (para comparar AUC offline)."""
        out = pd.Series(0.0, index=frame.index)
        clicks = logs[logs.click == 1]
        for (u, day), g in frame.groupby(["user_id", "day"]):
            h = history[u] + clicks.item_id[(clicks.user_id == u) & (clicks.day < day)].tolist()
            out[g.index] = pop_z[g.item_id.values] + 3.0 * (EMB["v1"][g.item_id.values] @ user_embedding(h, "v1"))
        return out
    v1_auc = roc_auc_score(pipe_prod["val_frame"].label, v1_scores(pipe_prod["val_frame"]))
    incident = pd.DataFrame([{"config": "v1 (anterior)", "AUC offline": v1_auc, "conv/petición": online_v1.conv_esperadas.mean(),
                              "% ya visto": online_v1.ya_visto.mean(), "% estrenos": online_v1.estrenos.mean()}, row_prod]).set_index("config")
    display(incident.round(4)); print(f"({time.time() - t0:.0f} s)")
    fig, ax = plt.subplots(1, 2, figsize=(12, 3.8))
    incident["AUC offline"].plot.bar(ax=ax[0], color=["#94a3b8", "#2563eb"], rot=0, ylim=(0.5, 1), title="Lo que vio la revisión de lanzamiento")
    for name, on in [("v1", online_v1), ("v2 producción", online_prod)]:
        ax[1].plot(on.groupby("day").conv_esperadas.mean(), "o-", label=name)
    ax[1].set(title="Lo que ve el pager: conv/petición por día", xlabel="día"); ax[1].legend(); plt.tight_layout(); plt.show()
    ''')
    M(r"""
    *(La AUC de v1 es la de su score heurístico sobre los mismos ejemplos de validación.)*

    **Offline ↑, online ↓.** A partir de aquí, trabajo de guardia.

    ## 4. Tu caja de herramientas de diagnóstico (TODOs)

    Implementa estas seis herramientas. Son genéricas: te servirán en cualquier sistema real. Cada una debe devolver
    **números** que permitan decir «verde / rojo».
    """)
    C(r'''
    def cache_audit(online_df) -> dict:
        """Herramienta 1 · ¿Sirves el modelo que crees?
        Devuelve: % de peticiones servidas con vector de usuario de una versión distinta de SERVING_VERSION,
        % de recomendaciones ya vistas y la similitud coseno media entre el vector cacheado y uno recalculado
        ahora con la versión correcta e historial completo (online_df.cache, online_df.hist)."""
        # TODO
        raise NotImplementedError


    def skew_report(online_df, pipe, n_sample=3000) -> pd.DataFrame:
        """Herramienta 2 · Log-and-wait: para una muestra de filas servidas (online_df.served_log, served=True),
        recalcula las features con el PIPELINE OFFLINE (features(..., serving=False) con la config de pipe, el historial
        real del usuario en ese instante y su embedding v2 recalculado) y compara fila a fila.
        Devuelve por feature: % filas distintas (np.isclose, rtol=1e-3) y la mediana del cociente servido/offline.
        Pista: el historial real en el instante de la petición es online_df.hist[u][:true_hist_len]."""
        # TODO
        raise NotImplementedError


    def time_travel_audit(pipe, n_sample=5000) -> pd.DataFrame:
        """Herramienta 3 · Para filas de pipe["train_frame"], recalcula las features de contadores ESTRICTAMENTE
        point-in-time (solo datos anteriores al día de la impresión) y compara con lo que usó el entrenamiento.
        Devuelve por feature: % filas distintas y AUC univariante de la feature contra la etiqueta en ambas versiones."""
        # TODO
        raise NotImplementedError


    def hash_collision_audit(counters, logs) -> dict:
        """Herramienta 4 · Nº de películas activas por fila de la tabla, contaminación ponderada por impresiones
        (fracción de las impresiones de la fila que son de OTRAS películas) y correlación entre el CTR de la fila y el
        CTR exacto de la película."""
        # TODO
        raise NotImplementedError


    def label_maturity_curve(logs, T=T_TRAIN, bins=np.arange(0, 15)) -> pd.DataFrame:
        """Herramienta 5 · Para los CLICS, tasa de conversión observada en T según la edad del clic (T − t), por
        tramos de 1 día. Si la tasa cae para los clics recientes, hay label delay en el set de entrenamiento."""
        # TODO
        raise NotImplementedError


    def adversarial_validation(train_frame, served_log, feats=None) -> dict:
        """Herramienta 6 · Entrena un clasificador que distinga filas de entrenamiento de candidatos de serving
        (served_log, TODOS los candidatos, no solo los servidos). Devuelve la AUC y la AUC univariante por feature.
        AUC ≈ 0,5 → misma distribución. Excluye features con skew ya conocido o con distinta semántica (position)."""
        # TODO
        raise NotImplementedError
    ''')
    M(r"""
    ## 5. Bug por bug (en el orden del árbol de triaje)

    Para **cuantificar**, usa este *helper*: arregla **un solo** parámetro sobre la config de producción y mide Δ online.
    """)
    C(r'''
    def quantify(change: dict, base=PROD_CONFIG, label=None):
        cfg = {**base, **change}
        _, on, row = evaluate(cfg, label or str(change))
        base_val = incident.loc["v2 producción", "conv/petición"]
        row["Δ conv/petición vs prod"] = row["conv/petición"] / base_val - 1
        return on, row
    ''')
    bugs = [
        ("Bug 1 · ¿Sirves el modelo que crees?",
         "El pager dice que la caída empezó **justo** con el despliegue. Primer paso del triaje: comprueba versión y caché.",
         "Usa `cache_audit(online_prod)`. Arreglo: en la config hay dos parámetros de caché."),
        ("Bug 2 · ¿Las features que sirves son las que entrenaste?",
         "Con la caché bajo control, compara las features servidas con las recalculadas offline (*log-and-wait*).",
         "Usa `skew_report(online_prod, pipe_prod)`. Varias features saldrán en rojo (algunas son síntomas de los bugs 1 y 3); el bug 2 es la que tiene un **factor constante** entre ambos lados."),
        ("Bug 3 · ¿La evaluación offline es honesta?",
         "La AUC offline de v2 es sospechosamente alta. Audita las features de contadores con *time-travel*.",
         "Usa `time_travel_audit(pipe_prod)`. ¿Qué ventana usa el pipeline de train vs el servicio?"),
        ("Bug 4 · Contadores que no distinguen películas",
         "Los contadores de CTR/CVR por película parecen poco informativos. Audita la tabla.",
         "Usa `hash_collision_audit(pipe_prod['counters'], logs)`."),
        ("Bug 5 · Etiquetas que aún no han llegado",
         "La conversión tarda días. ¿Qué pasa con los clics de los últimos días del set de entrenamiento?",
         "Usa `label_maturity_curve(logs)`. Arreglo: implementa `soft_labels(L, T)` (posterior de convertir dado que aún no ha convertido, modelo de Chapelle con retraso exponencial) y usa `label_policy='soft'`."),
        ("Bug 6 · El ranker nunca vio estos candidatos",
         "v2 tiene un retriever nuevo que no aplica el prefiltro de popularidad de v1. ¿Con qué datos aprendió el ranker?",
         "Usa `adversarial_validation(pipe['train_frame'], served_log)` (con los bugs 1–2 ya arreglados para que no contaminen la comparación). Arreglo: usa también las impresiones de exploración, ponderadas (`train_on='all_ipw'`)."),
    ]
    for k_, (title, ctx, hint) in enumerate(bugs, 1):
        M(f"""
        ### 🚨 {title}
        {ctx}

        💡 *Pista:* {hint}
        """)
        C(f'''
        # TODO bug {k_}: (1) detecta con la herramienta y muestra el número que lo delata,
        #               (2) cuantifica con quantify({{...}}), (3) deja aquí el cambio de config que lo arregla.
        FIX_{k_} = {{}}   # p. ej. {{"parametro": valor}}
        ''')
    C(r'''
    def soft_labels(L, T):
        """TODO (bug 5): para clics con label == 0, sustituye la etiqueta por P(convertirá | aún no convirtió tras e = T − t)
        = p·S(e) / (1 − p + p·S(e)), con S(e) = exp(−e/μ). Estima p y μ con clics maduros (t ≤ T − 7)."""
        raise NotImplementedError
    ''')
    M(r"""
    ## 6. *Scorecard*
    """)
    C(r'''
    FIXED_CONFIG = {**PROD_CONFIG, **FIX_1, **FIX_2, **FIX_3, **FIX_4, **FIX_5, **FIX_6}


    def scorecard(fixed_cfg):
        pipe, on, row = evaluate(fixed_cfg, "v2 arreglado")
        v1v, prodv = incident.loc["v1 (anterior)", "conv/petición"], incident.loc["v2 producción", "conv/petición"]
        honest = {**fixed_cfg, "counter_window": "pit"}
        auc_honest = run_pipeline(honest)["auc_offline"]
        checks = {
            "conv/petición ≥ 1,10 × producción": row["conv/petición"] >= 1.10 * prodv,
            "conv/petición ≥ 0,98 × v1": row["conv/petición"] >= 0.98 * v1v,
            "% ya visto < 1 %": row["% ya visto"] < 0.01,
            "AUC offline honesta (|Δ| < 0,01)": abs(row["AUC offline"] - auc_honest) < 0.01,
        }
        display(pd.DataFrame([incident.loc["v1 (anterior)"].to_dict() | {"config": "v1"}, incident.loc["v2 producción"].to_dict() | {"config": "v2 prod"}, row]).set_index("config").round(4))
        for k_, v in checks.items():
            print(("✅ " if v else "❌ ") + k_)
        return pipe, on, row

    try:
        _ = scorecard(FIXED_CONFIG)
    except NotImplementedError:
        print("Implementa las herramientas y los arreglos para ver el scorecard.")
    ''')
    M(r"""
    ## 7. *Postmortem* (plantilla)

    ```text
    Título: Caída de conversiones tras el lanzamiento de CineMatch v2
    Severidad: P1 · Duración: … · Impacto: −…% conv/petición (… conversiones perdidas)
    Línea temporal: lanzamiento → alerta → mitigación → arreglos
    Causas raíz (una por bug): qué, por qué pasó, por qué no lo vio la revisión de lanzamiento
    Qué funcionó / qué no
    Acciones (con owner y fecha):  p. ej. golden queries en el CI de despliegue; skew report diario con log-and-wait;
      contadores PIT por construcción (ventana semiabierta en la librería); curva de maduración en el dashboard del
      pipeline; adversarial validation train-vs-serving como gate; tabla de contadores sin hash…
    ```
    """)

    # ------------------------------------------------------------------ SOLUTION
    M(r"""
    ---
    # ⛔ SPOILER — intenta resolverlo primero

    Solución de referencia completa: las seis herramientas, el diagnóstico de cada bug con su número, la cuantificación
    (arreglar uno sobre producción **y** romper uno sobre el sistema arreglado — los bugs interactúan) y el *scorecard*.
    """)
    C(r'''
    def cache_audit(online_df):
        cache, hist = online_df.cache, online_df.hist
        cos = [float(e["emb"] @ user_embedding(hist[u], SERVING_VERSION)) for u, e in cache.items()]
        stale_hist = np.mean([len(e["hist"]) < len(hist[u]) for u, e in cache.items()])
        return {"% peticiones con vector de otra versión": online_df.cache_v1.mean(),
                "% recomendaciones ya vistas": online_df.ya_visto.mean(),
                "coseno medio caché vs recalculado": float(np.mean(cos)),
                "% entradas con historial desactualizado": float(stale_hist)}


    def skew_report(online_df, pipe, n_sample=3000):
        sl_all, final_hist = online_df.served_log, online_df.hist
        sl = sl_all[sl_all.served].sample(n_sample, random_state=0)
        rows = []
        for (u, day, t), g in sl.groupby(["user_id", "day", "t"]):
            h = final_hist[u][: g.true_hist_len.iloc[0]]                    # historial real en el instante de la petición
            f = features(g.item_id.values, day, h, user_embedding(h, SERVING_VERSION), pipe["cfg"], pipe["counters"], serving=False)
            rows.append(f.set_index(g.index))
        off = pd.concat(rows).loc[sl.index]
        rep = []
        for c_ in [f_ for f_ in FEATS if f_ != "position"]:
            a, b = sl[c_].values, off[c_].values
            mism = ~np.isclose(a, b, rtol=1e-3, atol=1e-6)
            ratio = np.median(a[mism] / np.where(b[mism] == 0, np.nan, b[mism])) if mism.any() else np.nan
            rep.append({"feature": c_, "% filas distintas": mism.mean(), "mediana servido/offline": ratio})
        out = pd.DataFrame(rep).set_index("feature")
        out["veredicto"] = np.where(out["% filas distintas"] > 0.02, "🔴", "🟢")
        return out
    ''')
    C(r'''
    def time_travel_audit(pipe, n_sample=5000):
        tr = pipe["train_frame"]; tr = tr[tr.label.isin([0, 1])]
        tr = tr.sample(min(n_sample, len(tr)), random_state=0)
        ctr, cvr, imps = [], [], []
        for day, g in tr.groupby("day"):
            a, b, c_ = pipe["counters"].asof(g.item_id.values, int(day), inclusive=False)
            ctr.append(pd.Series(a, g.index)); cvr.append(pd.Series(b, g.index)); imps.append(pd.Series(c_, g.index))
        pit = pd.DataFrame({"item_ctr_1d": pd.concat(ctr), "item_cvr_7d": pd.concat(cvr), "item_imps_7d": pd.concat(imps)}).loc[tr.index]
        rep = []
        for c_ in pit.columns:
            mism = ~np.isclose(tr[c_].values, pit[c_].values, rtol=1e-6)
            rep.append({"feature": c_, "% filas distintas": mism.mean(), "AUC usada en train": roc_auc_score(tr.label, tr[c_]),
                        "AUC point-in-time": roc_auc_score(tr.label, pit[c_])})
        return pd.DataFrame(rep).set_index("feature")


    def hash_collision_audit(counters, logs):
        imps = logs.item_id.value_counts()
        b = counters.bucket(imps.index.values)
        row_imps = pd.Series(imps.values).groupby(b).transform("sum").values
        contamination = 1 - imps.values / row_imps
        ctr_exact = logs.groupby("item_id").click.mean().loc[imps.index].values
        row_ctr = pd.Series(logs.click.values).groupby(counters.bucket(logs.item_id.values)).mean()
        return {"películas activas": len(imps), "filas usadas": int(np.unique(b).size),
                "películas por fila (media)": len(imps) / np.unique(b).size,
                "contaminación ponderada por impresiones": float((imps.values * contamination).sum() / imps.values.sum()),
                "corr(CTR fila, CTR exacto)": float(np.corrcoef(row_ctr.loc[b].values, ctr_exact)[0, 1])}


    def label_maturity_curve(logs, T=T_TRAIN, bins=np.arange(0, 15)):
        c_ = logs[logs.click == 1].copy()
        c_["edad_clic"] = T - c_.t
        c_["observada"] = (c_.conv == 1) & (c_.conv_t <= T)
        c_["tramo"] = pd.cut(c_.edad_clic, np.r_[bins, np.inf], right=False, labels=bins)
        return c_.groupby("tramo", observed=True).agg(clics=("observada", "size"), cvr_observada=("observada", "mean"),
                                                     cvr_final_oraculo=("conv", "mean"))


    def adversarial_validation(train_frame, served_log, feats=None):
        feats = feats or ["retr_score", "item_ctr_1d", "item_cvr_7d", "item_imps_7d", "item_pop_hist", "user_n_hist"]
        a = train_frame[feats].sample(min(20_000, len(train_frame)), random_state=0)
        b = served_log[feats].sample(min(20_000, len(served_log)), random_state=0)
        Xa = pd.concat([a, b]); ya = np.r_[np.zeros(len(a)), np.ones(len(b))]
        from sklearn.model_selection import cross_val_predict
        p = cross_val_predict(HistGradientBoostingClassifier(max_iter=100, random_state=seed), Xa, ya, cv=3, method="predict_proba")[:, 1]
        uni = {f_: max(roc_auc_score(ya, Xa[f_]), 1 - roc_auc_score(ya, Xa[f_])) for f_ in feats}
        return {"AUC train-vs-serving": roc_auc_score(ya, p), "AUC univariante": pd.Series(uni).sort_values(ascending=False).round(3)}


    def soft_labels(L, T):
        mature = L[(L.click == 1) & (L.t <= T - 7)]
        p = mature.label.mean()
        mu = (mature.conv_t - mature.t)[mature.label == 1].mean()
        pending = (L.click == 1) & (L.label == 0)
        surv = np.exp(-(T - L.t) / mu)
        L.loc[pending, "label"] = (p * surv / (1 - p + p * surv))[pending]
        return L
    ''')
    M(r"""
    ### Diagnóstico bug por bug
    """)
    C(r'''
    t0 = time.time()
    print("🚨 Bug 1 · caché:", {k_: round(v, 3) for k_, v in cache_audit(online_prod).items()})
    FIX_1 = {"cache_key": "user_id+version", "cache_invalidate_on_event": True}
    print("🚨 Bug 2 · skew (log-and-wait):"); display(skew_report(online_prod, pipe_prod).round(3))
    FIX_2 = {"age_unit_serving": "days"}
    print("🚨 Bug 3 · time-travel:"); display(time_travel_audit(pipe_prod).round(3))
    FIX_3 = {"counter_window": "pit"}
    print("🚨 Bug 4 · hash:", {k_: round(v, 3) for k_, v in hash_collision_audit(pipe_prod["counters"], logs).items()})
    FIX_4 = {"hash_buckets": None}
    print(f"({time.time() - t0:.0f} s)")
    ''')
    C(r'''
    mat = label_maturity_curve(logs)
    print("🚨 Bug 5 · maduración de la etiqueta:"); display(mat.round(3).T)
    FIX_5 = {"label_policy": "soft"}
    ax = mat[["cvr_observada", "cvr_final_oraculo"]].plot(marker="o", figsize=(8, 3.4), title="Curva de maduración: los clics recientes parecen negativos")
    ax.set(xlabel="edad del clic en el momento de entrenar (días)", ylabel="conversiones / clic"); plt.show()

    pipe_12 = run_pipeline({**PROD_CONFIG, **FIX_1, **FIX_2})
    on_12 = simulate_online(pipe_12)
    av_bad = adversarial_validation(pipe_12["train_frame"], on_12.served_log)
    pipe_6 = run_pipeline({**PROD_CONFIG, **FIX_1, **FIX_2, "train_on": "all_ipw"})
    av_good = adversarial_validation(pipe_6["train_frame"], on_12.served_log)
    print(f"🚨 Bug 6 · adversarial validation: AUC train-vs-serving {av_bad['AUC train-vs-serving']:.3f} (solo impresiones) "
          f"→ {av_good['AUC train-vs-serving']:.3f} (con exploración ponderada)")
    print("   La AUC multivariante ≈ 1 en ambos casos (impresiones ≠ top-100 del retriever siempre); lo que delata el bug es QUÉ "
          "feature separa: item_pop_hist (el prefiltro de popularidad de v1) y cómo baja al añadir la exploración.")
    display(pd.DataFrame({"solo impresiones": av_bad["AUC univariante"], "con exploración": av_good["AUC univariante"]}))
    FIX_6 = {"train_on": "all_ipw"}
    ''')
    M(r"""
    ### Cuantificación: arreglar uno sobre producción y romper uno sobre el sistema arreglado

    Los bugs **interactúan** (p. ej. con la caché rota, el resto apenas importa porque el retriever ya devuelve basura).
    Por eso un *postmortem* serio da las dos vistas.
    """)
    C(r'''
    t0 = time.time()
    FIXES = {"1 caché": FIX_1, "2 skew edad": FIX_2, "3 fuga contadores": FIX_3, "4 hash": FIX_4, "5 label delay": FIX_5, "6 candidate mismatch": FIX_6}
    FIXED_CONFIG = {**PROD_CONFIG, **FIX_1, **FIX_2, **FIX_3, **FIX_4, **FIX_5, **FIX_6}
    pipe_fix, online_fix, row_fix = evaluate(FIXED_CONFIG, "todo arreglado")
    rows = []
    for name, fx in FIXES.items():
        _, r1 = quantify(fx, label=name)
        broken = {**FIXED_CONFIG, **{k_: PROD_CONFIG[k_] for k_ in fx}}
        _, _, r2 = evaluate(broken, name)
        rows.append({"bug": name, "Δ al arreglar solo este (sobre prod)": r1["Δ conv/petición vs prod"],
                     "Δ al romper solo este (sobre arreglado)": r2["conv/petición"] / row_fix["conv/petición"] - 1,
                     "AUC offline con el bug (resto arreglado)": r2["AUC offline"]})
    impact = pd.DataFrame(rows).set_index("bug"); display(impact.round(4))
    print(f"({time.time() - t0:.0f} s)")
    ax = impact.iloc[:, :2].mul(100).plot.barh(figsize=(9, 4), title="Impacto de cada bug en conv/petición (%)")
    ax.axvline(0, color="k", lw=0.8); ax.set_xlabel("%"); plt.show()
    ''')
    C(r'''
    pipe_fix, online_fix, row_fix = scorecard(FIXED_CONFIG)
    fig, ax = plt.subplots(figsize=(8, 3.6))
    for name, on in [("v1", online_v1), ("v2 producción", online_prod), ("v2 arreglado", online_fix)]:
        ax.plot(on.groupby("day").conv_esperadas.mean(), "o-", label=name)
    ax.set(title="Después del incidente", xlabel="día", ylabel="conv/petición"); ax.legend(); plt.show()
    ''')
    M(r"""
    ### Lectura de la solución (con FAST_DEV_RUN; tus números variarán algo)

    1. **Caché**: casi todos los usuarios recientes se sirven con su vector **v1** contra el índice **v2**; como v2 viene
       de un *warm-start* el espacio está parcialmente alineado y el sistema «funciona» peor sin dar error. Además, sin
       invalidación por evento, el filtro de «ya visto» usa un historial congelado. Arreglo: versión en la clave +
       invalidación por evento (y en un sistema real: *golden queries* en el despliegue).
    2. **Skew**: `item_age_days` servido = 24 × offline (horas vs días). Los estrenos parecen viejos y desaparecen de la
       home (mira `% estrenos`).
    3. **Fuga**: el pipeline de train agrega los contadores **incluyendo el día de la impresión** (ventana inclusiva):
       el CTR y la CVR «del último día» contienen el propio clic/conversión. La AUC univariante de esas features cae al
       recalcularlas PIT, y la AUC offline del modelo baja: la revisión de lanzamiento estaba viendo una fuga.
    4. **Hash**: 97 filas para ~1 600 películas → ~15 películas por fila; la CTR de la fila apenas correlaciona con la de la
       película. Su impacto aquí es **pequeño** (≈ −0,5–1 %): con pocos clics por película los contadores exactos ya son
       ruidosos y otras features compensan. En catálogos de millones, donde los contadores son features principales, el
       mismo bug cuesta mucho más. Lección de guardia: **prioriza por impacto medido**, no por lo feo que es el bug — y aun
       así arréglalo, porque la tabla exacta no cuesta nada con este catálogo.
    5. **Label delay**: la tasa de conversión observada de los clics de los últimos 3–4 días es una fracción de la real
       (curva de maduración). El ranker aprende que lo reciente —los estrenos— no convierte. Las etiquetas suaves de
       Chapelle lo corrigen sin tirar los datos frescos.
    6. **Candidate mismatch**: el ranker solo vio películas populares (el prefiltro de v1); el retriever v2 trae cola larga
       con mucho «relleno» de baja calidad que el ranker no sabe penalizar. La *adversarial validation* lo delata
       (`item_pop_hist` separa train de serving) y usar el tráfico de exploración ponderado lo corrige.

    ⚠️ **Sobre el ruido.** Con `FAST_DEV_RUN` hay solo 4 días de producción: los efectos de ±1–2 % (skew, hash, candidate
    mismatch) están cerca del ruido de simulación y a veces cambian de signo entre las dos vistas de la tabla de impacto.
    Es exactamente lo que pasa en un incidente real: los bugs grandes (caché, fuga, label delay) se ven claros; los pequeños
    hay que confirmarlos con más tráfico (`FAST_DEV_RUN=False`, varias semillas) antes de atribuirles impacto en el
    *postmortem*. Todos se arreglan igualmente: son defectos, aunque hoy cuesten poco.

    ## 🚀 Retos extra (nivel experto)
    - Sustituye `EXPLORE_WEIGHT` por pesos IPS exactos a partir de la propensión de cada hueco de exploración y compara.
    - Implementa *golden queries* para el despliegue: 200 usuarios con vecinos conocidos en v2; el despliegue falla si el
      recall@20 cae > 5 %. Comprueba que habría parado el bug 1 antes de llegar a usuarios.
    - Haz que el *skew report* corra «cada noche» sobre el log de un día y dispare una alerta (módulo 17).
    - Añade un bug 7 tuyo (p. ej. orden del historial invertido en serving) y comprueba qué herramienta lo detecta.
    - Estima con OPE (módulo 14) el valor de v2 arreglado usando solo el tráfico de exploración, antes de desplegar.

    ## 🤔 Reflexión
    1. ¿Qué tres *gates* automáticos en el CI/CD habrían evitado este incidente? ¿Cuánto cuestan?
    2. ¿Por qué la AUC offline no detectó ninguno de los bugs de *serving* (1, 2) y sí «premió» el 3?
    3. Si solo pudieras tener **una** de las seis herramientas en producción, ¿cuál y por qué?
    4. ¿Cómo cambiaría tu respuesta al bug 5 si el retraso medio fuese de 14 días? ¿Y de 1 hora?
    5. ¿Qué parte del tráfico de exploración «pagas» y cómo lo justificas ante producto?
    """)
    nb.save(path)


def readme() -> None:
    text = """# Módulo 19 · Masterclass: lo que separa a un ingeniero top de recomendación

**Nivel:** 🔴 Experto · **Duración:** 7–9 h (lección) + 6–10 h (proyecto) · **GPU:** opcional (T4 acelera §1 y §7; todo corre en CPU con `FAST_DEV_RUN=True`) · **Unidades Colab:** 1–4

**Prerrequisitos:** 06, 07, 08, 13, 14, 15, 16, 17 y 18.

## Resumen
El módulo 18 reúne un compendio de 38 secretos de élite. Este módulo coge los que allí solo se mencionan y los
**implementa en miniatura**, los **mide** con simulaciones de verdad conocida y enseña a **depurarlos** en producción:

1. **Tablas de embeddings a escala**: memoria y estado del optimizador (Adagrad por filas), colisiones de hashing
   ponderadas por tráfico (cabeza vs cola), IDs estructurados, *double hashing*, **QR embeddings**, **mixed-dimension**,
   **TT-Rec**, híbrido por frecuencia, cuantización **fp16/fp8/int8/int4 por fila vs por tabla**, *one-epoch phenomenon*.
2. **Entrenamiento en tiempo real** (Monolith): tabla sin colisiones con filtro de frecuencia y expiración, estático vs
   diario vs online, **intervalo de sincronización**, *catastrophic forgetting* y *replay*.
3. **Label delay** (modelo de Chapelle ajustado en PyTorch), ventanas de atribución, **fugas de ventana inclusiva** en
   contadores en tiempo real, lag de streaming y **skew report con log-and-wait** (por qué el PSI no lo ve).
4. **Exposure bias** (IPS y positividad), **candidate-set mismatch** y paradoja de Berkson entre etapas, **consistencia
   del funnel** y distilación del ranker final al pre-ranker.
5. **Verdad a largo plazo**: clickbait vs satisfacción con retención simulada, Goodhart y *value models*, encuestas
   como etiquetas (sesgo de respuesta), tamaño de holdouts globales.
6. **Casebook** de 10 incidentes «offline ↑ online ↓», árbol de triaje, *golden queries* para versiones de embeddings y
   análisis de novedad por antigüedad de exposición.
7. **Rendimiento**: presupuesto de latencia, *dynamic batching* (simulación de eventos), *hedged requests*, caché de
   usuario con invalidación por evento, cuantización del ranker, retrieval por fuerza bruta en GPU, *capacity planning*.
8. **Cultura**: experimentación al estilo Netflix, árbol de métricas, linter de *experiment docs*, plantilla de *design
   doc* y señales de seniority.

## Contenido
| Archivo | Qué es |
|---|---|
| `19_elite_playbook.ipynb` | Lección (≥ 25 gráficos, todo ejecutable en CPU con `FAST_DEV_RUN=True`) |
| `19_proyecto_debugging_produccion.ipynb` | Proyecto «pager duty»: CineMatch v2 con 6 bugs plantados (caché stale con versión de embeddings, skew de unidades, fuga en contadores, colisiones de hashing, label delay, candidate mismatch). Herramientas de diagnóstico con TODOs, cuantificación por ablación, *scorecard*, *postmortem* y solución ⛔ SPOILER |

## Datasets
- **Lección**: simulaciones con verdad conocida (no descarga nada).
- **Proyecto**: **MovieLens-100K** (GroupLens) como base de un gemelo digital de usuarios; *fallback* sintético sin red.

## Lecturas clave
- Liu et al. (2022) *Monolith* · Shi et al. (2020) *QR embeddings* · Ginart et al. (2019) *Mixed Dimension Embeddings* · Yin et al. (2021) *TT-Rec* · Guan et al. (2019) *4-bit embedding quantization*.
- Chapelle (2014) *Delayed Feedback* · Ktena et al. (2019) · Zinkevich, *Rules of ML*.
- Schnabel et al. (2016) · Qin et al. (2022) *RankFlow* · Zheng et al. (2024) *Full Stage LTR* · Wang et al. (2023, Meta) *ranking consistency*.
- Hohnhold et al. (2015) *Focusing on the Long-term* · YouTube (2021) *valued watchtime* · Tingley et al. (2021) *Decision Making at Netflix*.
- Dean & Barroso (2013) *The Tail at Scale* · Gupta et al. (2020) *DeepRecSys*.

## Conexión con CineMatch
El proyecto es el «día 2» del capstone (módulo 18): el sistema ya está en producción y falla. Las herramientas que
construyes (cache audit, skew report, time-travel audit, hash audit, curva de maduración, adversarial validation) son
los *gates* que deberías añadir al pipeline de los módulos 16 y 17.

Los notebooks se generan con `python recsys-course/_tools/builders/build_19.py` (desde la raíz del repo).
"""
    with open(f"{MOD}/README.md", "w", encoding="utf-8") as f:
        f.write(text)
    print(f"OK {MOD}/README.md")


if __name__ == "__main__":
    lesson()
    project()
    readme()
