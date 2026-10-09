"""Builder del módulo 05 · Factorización matricial (FunkSVD, sesgos, SVD++, iALS, BPR).

Ejecutar desde la raíz del repo:  python recsys-course/_tools/builders/build_05.py
"""
import sys
from pathlib import Path

sys.path.insert(0, "recsys-course/_tools")
sys.path.insert(0, "recsys-course/_tools/builders")
from nbbuild import Notebook  # noqa: E402
from bloque2_common import add_utils  # noqa: E402

MOD = "recsys-course/05_matrix_factorization"
Path(MOD).mkdir(parents=True, exist_ok=True)

BPR_CODE = r'''
# BPR desde cero en PyTorch (GPU si está disponible)
import torch.nn as nn
import torch.nn.functional as Fnn


class BPRMF(nn.Module):
    """x̂_ui = <p_u, q_i> + b_i.  Pérdida BPR: −log σ(x̂_ui − x̂_uj) con j muestreado."""
    def __init__(self, n_users: int, n_items: int, k: int = 64):
        super().__init__()
        self.P, self.Q, self.b = nn.Embedding(n_users, k), nn.Embedding(n_items, k), nn.Embedding(n_items, 1)
        nn.init.normal_(self.P.weight, std=0.01); nn.init.normal_(self.Q.weight, std=0.01); nn.init.zeros_(self.b.weight)

    def forward(self, u, i, j):
        pu = self.P(u)
        return (pu * (self.Q(i) - self.Q(j))).sum(1) + (self.b(i) - self.b(j)).squeeze(1)


def train_bpr(X: sp.csr_matrix, k=64, lr=5e-3, reg=1e-5, epochs=20, batch=8192, eval_every=5,
              val=None, verbose=True):
    """val = (X_val_train, rel_val) para registrar NDCG@10 durante el entrenamiento."""
    torch.manual_seed(seed)
    model = BPRMF(*X.shape, k).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    uu, ii = X.nonzero()
    uu, ii = torch.tensor(uu, device=device), torch.tensor(ii, device=device)
    hist = []
    for ep in range(1, epochs + 1):
        perm, tot = torch.randperm(len(uu), device=device), 0.0
        for s in range(0, len(uu), batch):
            b = perm[s:s + batch]; u, i = uu[b], ii[b]
            j = torch.randint(0, X.shape[1], (len(b),), device=device)      # negativo uniforme
            x = model(u, i, j)
            l2 = model.P(u).pow(2).sum() + model.Q(i).pow(2).sum() + model.Q(j).pow(2).sum()
            loss = -Fnn.logsigmoid(x).mean() + reg * l2 / len(b)
            opt.zero_grad(); loss.backward(); opt.step(); tot += loss.item() * len(b)
        row = {"epoch": ep, "loss": tot / len(uu)}
        if val is not None and (ep % eval_every == 0 or ep == epochs):
            row["NDCG@10"] = evaluate_topk(bpr_score_fn(model), *val)["NDCG@10"]
        hist.append(row)
        if verbose and "NDCG@10" in row:
            print(f"época {ep:3d} · loss {row['loss']:.4f} · NDCG@10 val {row['NDCG@10']:.4f}")
    return model, pd.DataFrame(hist)


def bpr_score_fn(model):
    P = model.P.weight.detach().cpu().numpy(); Q = model.Q.weight.detach().cpu().numpy()
    b = model.b.weight.detach().cpu().numpy().ravel()
    return lambda ub: P[ub] @ Q.T + b
'''

IALS_LIB_CODE = r'''
# iALS con la librería `implicit` (GPU si hay CUDA; si no, CPU multihilo)
import implicit
from implicit.als import AlternatingLeastSquares

USE_GPU = bool(getattr(implicit.gpu, "HAS_CUDA", False)) and torch.cuda.is_available()


def fit_ials(X: sp.csr_matrix, factors=128, reg=50.0, alpha=1.0, iters=15):
    m = AlternatingLeastSquares(factors=factors, regularization=reg, alpha=alpha, iterations=iters,
                                use_gpu=USE_GPU, random_state=seed)
    m.fit(X, show_progress=False)
    if USE_GPU:
        m = m.to_cpu()                       # factores como numpy para evaluar
    return m


def mf_score_fn(U: np.ndarray, V: np.ndarray):
    return lambda ub: U[ub] @ V.T
'''

# ---------------------------------------------------------------------------
# LECCIÓN
# ---------------------------------------------------------------------------
LESSON = f"{MOD}/05_matrix_factorization.ipynb"
nb = Notebook("Módulo 05 · Factorización matricial", colab_path=LESSON, gpu=True)
nb.md(f"""
{nb.badge()}

# Módulo 05 · Factorización matricial
### Del Netflix Prize a iALS y BPR: FunkSVD, sesgos, SVD++, ALS implícito, BPR en GPU

| | |
|---|---|
| **Nivel** | 🟡 Intermedio → 🟠 Avanzado |
| **Duración estimada** | 4–5 h |
| **GPU recomendada** | T4 (BPR en PyTorch e `implicit` en GPU) |
| **Unidades de Colab** | ≈ 1–2 (T4) |
| **Prerrequisitos** | [02_evaluation](../02_evaluation), [04_neighborhood_linear](../04_neighborhood_linear) |
""")
nb.md("""
## 🎯 Objetivos de aprendizaje

1. **Explicar** la factorización latente $\\mathbf R\\approx\\mathbf P\\mathbf Q^\\top$ y por qué la SVD clásica no sirve con datos faltantes.
2. **Derivar e implementar** FunkSVD con SGD (con y sin sesgos) y **medir** el efecto de sesgos, dimensión y regularización.
3. **Describir** SVD++ y timeSVD++ (Koren) y **usar** Surprise para compararlos.
4. **Derivar e implementar** ALS para feedback implícito (Hu, Koren & Volinsky, 2008) desde cero.
5. **Implementar** BPR (Rendle et al., 2009) en PyTorch y entrenarlo en GPU.
6. **Usar** `implicit` (GPU) y `cornac`, y **compararlos** con EASE del módulo 04.
7. **Visualizar** e **interpretar** el espacio latente; **aplicar** *fold-in* para usuarios nuevos.
""")
nb.md("## ⚙️ Setup")
nb.code("""
!pip install -q implicit scikit-surprise cornac numba pyarrow
""")
nb.code(r'''
import os, random, time, warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import torch

warnings.filterwarnings("ignore")
seed = 42
random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
device = "cuda" if torch.cuda.is_available() else "cpu"
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.3})
FAST_DEV_RUN = True        # True: menos épocas y rejillas pequeñas
EPOCHS = 15 if FAST_DEV_RUN else 40
print("device:", device)
''')
add_utils(nb)

nb.md("""
## 💡 1. Intuición: gustos con pocos «ejes»

Imagina que cada película se puede describir con unos pocos números ocultos: *¿cuánta acción?*,
*¿es para niños?*, *¿es seria o comedia?*… y que cada usuario tiene un número por eje: *¿cuánto le
gusta la acción?*. La afinidad usuario-película sería el **producto escalar** de ambos vectores.

Nadie etiqueta esos ejes: el modelo los **descubre** a partir de la matriz de ratings. Es
exactamente lo que hace un **embedding** en deep learning (de hecho, MF es el *two-tower* más simple
posible: una tabla de embeddings por lado y un producto escalar).

$$\\underbrace{\\mathbf R}_{|U|\\times|I|}\\;\\approx\\;\\underbrace{\\mathbf P}_{|U|\\times k}\\;\\underbrace{\\mathbf Q^\\top}_{k\\times|I|},\\qquad k\\ll |I|$$

**Diferencia clave con el módulo 04**: item-kNN memoriza relaciones ítem-ítem ($|I|^2$ parámetros);
MF **comprime** en $k(|U|+|I|)$ parámetros → generaliza entre usuarios que no comparten ningún ítem.
""")
nb.code(r'''
# Diagrama: R (dispersa) ≈ P · Qᵀ
fig, ax = plt.subplots(figsize=(12, 4)); ax.axis("off"); ax.set_xlim(0, 12); ax.set_ylim(0, 4.4)
rng = np.random.default_rng(1)
def grid(x0, y0, nr, nc, cell, fill_frac, color, title):
    for r in range(nr):
        for c in range(nc):
            on = rng.random() < fill_frac
            ax.add_patch(mpatches.Rectangle((x0 + c * cell, y0 + (nr - 1 - r) * cell), cell, cell,
                         fc=color if on else "white", ec="grey", lw=0.4))
    ax.text(x0 + nc * cell / 2, y0 + nr * cell + 0.15, title, ha="center", fontsize=10)
grid(0.2, 0.3, 10, 14, 0.27, 0.18, "#4c72b0", "R  (usuarios × películas, ~4 % observado)")
ax.text(4.3, 1.6, "≈", fontsize=28)
grid(5.0, 0.3, 10, 3, 0.27, 1.0, "#55a868", "P  (k=3)")
ax.text(6.05, 1.6, "×", fontsize=22)
grid(6.6, 1.5, 3, 14, 0.27, 1.0, "#dd8452", "Qᵀ  (k=3 × películas)")
ax.text(10.7, 2.0, r"$\hat r_{ui}=\mu+b_u+b_i+\mathbf{p}_u^\top\mathbf{q}_i$", fontsize=12, ha="center")
ax.set_title("Factorización matricial: completar la matriz con un producto de dos matrices delgadas", fontsize=12); plt.show()
''')
nb.code(r'''
# Línea temporal del Netflix Prize (cifras oficiales del concurso, RMSE en el test set)
events = [(2006.75, "Oct 2006\nlanzamiento\nCinematch 0,9525"), (2006.95, "Dic 2006\nSimon Funk publica\nsu SVD con SGD"),
          (2007.85, "2007 Progress Prize\nBellKor"), (2008.85, "2008 Progress Prize\nBellKor in BigChaos"),
          (2009.55, "Jul 2009 Grand Prize\nBellKor's Pragmatic Chaos\n0,8567 (−10,06 %)"), (2012.3, "2012 Netflix explica\nqué desplegó (y qué no)")]
fig, ax = plt.subplots(figsize=(13, 2.8)); ax.axhline(0, color="k", lw=1.5)
for k_, (x, t) in enumerate(events):
    y = 1 if k_ % 2 == 0 else -1
    ax.plot([x, x], [0, 0.55 * y], color="#c44e52"); ax.scatter([x], [0], color="#c44e52", zorder=3)
    ax.text(x, 0.62 * y, t, ha="center", va="bottom" if y > 0 else "top", fontsize=8)
ax.set_ylim(-2, 2); ax.set_xlim(2006.4, 2012.8); ax.set_yticks([]); ax.grid(False)
ax.set_title("Netflix Prize (2006–2009): objetivo = mejorar un 10 % el RMSE de Cinematch"); plt.show()
''')
nb.md("""
### 🧪 Ejemplo en papel: factorizar 5×6 con $k=2$

Mismo juguete que en el módulo 04. Ajustamos $\\mathbf P,\\mathbf Q$ por descenso de gradiente **solo
en las celdas observadas** y miramos qué predice el modelo en las vacías.
""")
nb.code(r'''
toy_items = ["Alien", "Aliens", "Matrix", "Toy Story", "Shrek", "Titanic"]
R_toy = np.array([[5, 4, 5, 0, 0, 1], [4, 5, 4, 0, 1, 0], [0, 0, 1, 5, 4, 0],
                  [1, 0, 0, 4, 5, 3], [5, 0, 4, 0, 0, 0]], dtype=float)
M = R_toy > 0
r_ = np.random.default_rng(seed); P_t = r_.normal(0, .5, (5, 2)); Q_t = r_.normal(0, .5, (6, 2)); mu_t = R_toy[M].mean()
for _ in range(3000):
    E_ = np.where(M, R_toy - mu_t - P_t @ Q_t.T, 0)
    P_t += 0.02 * (E_ @ Q_t - 0.05 * P_t); Q_t += 0.02 * (E_.T @ P_t - 0.05 * Q_t)
R_hat = np.clip(mu_t + P_t @ Q_t.T, 1, 5)
fig, axes = plt.subplots(1, 3, figsize=(15, 3.6))
axes[0].imshow(np.where(M, R_toy, np.nan), cmap="YlGn", vmin=1, vmax=5); axes[0].set_title("Observado (blanco = faltante)")
axes[1].imshow(R_hat, cmap="YlGn", vmin=1, vmax=5); axes[1].set_title("Reconstrucción μ + P·Qᵀ (k=2)")
for ax, Mx in [(axes[0], np.where(M, R_toy, np.nan)), (axes[1], R_hat)]:
    ax.set_xticks(range(6), toy_items, rotation=35, ha="right"); ax.set_yticks(range(5), [f"u{i}" for i in range(5)]); ax.grid(False)
    for a in range(5):
        for b in range(6):
            if not np.isnan(Mx[a, b]): ax.text(b, a, f"{Mx[a, b]:.1f}", ha="center", va="center", fontsize=8, weight="bold" if not M[a, b] else None)
axes[2].scatter(Q_t[:, 0], Q_t[:, 1], s=80, color="#dd8452")
for t, (x, y) in zip(toy_items, Q_t): axes[2].annotate(t, (x, y), fontsize=9)
axes[2].scatter(P_t[:, 0], P_t[:, 1], marker="^", color="#4c72b0")
for i, (x, y) in enumerate(P_t): axes[2].annotate(f"u{i}", (x, y), fontsize=8, color="#4c72b0")
axes[2].set_title("Espacio latente 2D: ítems (●) y usuarios (▲)"); plt.tight_layout(); plt.show()
''')
nb.md("""
En negrita, las predicciones para celdas **no observadas**: el usuario 4 (fan de *Alien* y *Matrix*)
recibe una predicción alta para *Aliens* y baja para *Toy Story*. En el espacio latente, las
películas de ciencia ficción y las infantiles quedan en lados opuestos **sin que nadie le diga los géneros**.
""")

nb.md(r"""
## 📐 2. Teoría formal

### 2.1 ¿Por qué no la SVD de álgebra lineal?
La SVD truncada da la mejor aproximación de rango $k$ de una matriz **completa**. Pero en $\mathbf R$
falta el ~96 % de las celdas. Rellenarlas con 0 significa «lo odió» (falso); rellenarlas con la media
sesga todo. La solución de Funk (2006) y Koren: **optimizar solo sobre las celdas observadas** $\mathcal K$.

### 2.2 MF con sesgos (*biased MF*, Koren, Bell & Volinsky 2009)
$$\hat r_{ui}=\mu+b_u+b_i+\mathbf p_u^\top\mathbf q_i$$
$$\min_{b,\mathbf P,\mathbf Q}\sum_{(u,i)\in\mathcal K}\big(r_{ui}-\hat r_{ui}\big)^2+\lambda\big(\|\mathbf p_u\|^2+\|\mathbf q_i\|^2\big)+\lambda_b\big(b_u^2+b_i^2\big)$$
- $\mu$: media global; $b_u$: el usuario es «generoso» o «duro»; $b_i$: la película es buena/mala *para todo el mundo*.
- $\mathbf p_u^\top\mathbf q_i$: la **interacción** — lo que queda tras quitar los sesgos.

### 2.3 SGD (la contribución de Funk)
Para cada rating observado, con error $e_{ui}=r_{ui}-\hat r_{ui}$ y tasa $\eta$:
$$b_u\leftarrow b_u+\eta(e_{ui}-\lambda_b b_u),\quad b_i\leftarrow b_i+\eta(e_{ui}-\lambda_b b_i)$$
$$\mathbf p_u\leftarrow \mathbf p_u+\eta(e_{ui}\,\mathbf q_i-\lambda\,\mathbf p_u),\quad \mathbf q_i\leftarrow \mathbf q_i+\eta(e_{ui}\,\mathbf p_u-\lambda\,\mathbf q_i)$$
(derivada de $e_{ui}^2$ respecto de $\mathbf p_u$: $-2e_{ui}\mathbf q_i$; el 2 se absorbe en $\eta$).

### 2.4 SVD++ y timeSVD++ (Koren, 2008; 2009)
- **SVD++** añade **feedback implícito**: el usuario también se describe por *qué* valoró, no solo cómo:
  $\hat r_{ui}=\mu+b_u+b_i+\mathbf q_i^\top\big(\mathbf p_u+|N(u)|^{-1/2}\sum_{j\in N(u)}\mathbf y_j\big)$.
- **timeSVD++** hace los parámetros **funciones del tiempo**: $b_i(t)=b_i+b_{i,\text{Bin}(t)}$, $b_u(t)=b_u+\alpha_u\,\text{dev}_u(t)+b_{u,t}$ (un sesgo por usuario y **día**), $\mathbf p_u(t)$… Capturó efectos como «el usuario valora distinto los lunes» o «la película envejece».

### 2.5 ALS para feedback implícito (Hu, Koren & Volinsky, ICDM 2008)
Con datos implícitos ($r_{ui}$ = nº de vistas, minutos…) **no hay negativos**: no ver ≠ odiar. Se define
preferencia $p_{ui}=\mathbb 1[r_{ui}>0]$ y confianza $c_{ui}=1+\alpha r_{ui}$, y se minimiza sobre **todas** las celdas:
$$\min_{\mathbf P,\mathbf Q}\sum_{u,i}c_{ui}\big(p_{ui}-\mathbf p_u^\top\mathbf q_i\big)^2+\lambda\big(\textstyle\sum_u\|\mathbf p_u\|^2+\sum_i\|\mathbf q_i\|^2\big)$$
Fijando $\mathbf Q$, el problema en cada $\mathbf p_u$ es una **regresión ridge ponderada** con solución cerrada:
$$\mathbf p_u=\big(\mathbf Q^\top\mathbf C^u\mathbf Q+\lambda\mathbf I\big)^{-1}\mathbf Q^\top\mathbf C^u\mathbf p(u)$$
**El truco que lo hace escalable**: $\mathbf Q^\top\mathbf C^u\mathbf Q=\underbrace{\mathbf Q^\top\mathbf Q}_{\text{1 vez por iteración}}+\mathbf Q^\top(\mathbf C^u-\mathbf I)\mathbf Q$, y $\mathbf C^u-\mathbf I$ solo es no nula en los $n_u$ ítems vistos → coste $O(k^2 n_u + k^3)$ por usuario. Se alterna usuarios ↔ ítems.

### 2.6 BPR (Rendle et al., UAI 2009)
En vez de reconstruir la matriz, optimizamos el **orden**: el usuario prefiere un ítem visto $i$ a uno no visto $j$.
$$\max_\Theta\sum_{(u,i,j)}\ln\sigma(\hat x_{ui}-\hat x_{uj})-\lambda\|\Theta\|^2$$
Es una **regresión logística sobre pares** (como RankNet, módulo 07) y es una aproximación suave del AUC.
Se entrena con SGD muestreando $j$ al azar. **WARP** (Weston et al., 2011) muestrea negativos hasta
encontrar uno que viole el margen y pondera por el rango → optimiza mejor la cabeza del ranking (precision@k).

### 2.7 iALS revisitado (Rendle, Krichene, Zhang & Koren, RecSys 2022)
Con un tuning cuidadoso (dimensión grande, regularización escalada por frecuencia, inicialización pequeña
$\sigma\approx 0{,}1/\sqrt{k}$, peso de no-observados bien elegido), iALS es **muy competitivo** con métodos
mucho más recientes (VAEs, EASE, NCF) en ML-20M, MSD y otros benchmarks.
""")

nb.md("## 📦 3. Datos")
nb.code(r'''
ratings, movies, users = load_movielens_1m()
train, test = temporal_split(ratings)
enc = Encoder(train)
tr, te = enc.transform(train), enc.transform(test)
X = enc.csr(tr)                                 # implícito (cualquier rating)
rel = test_relevance(te)
titles = movies.set_index("item_id").title.loc[enc.items].values
genres_ = movies.set_index("item_id").genres.loc[enc.items].values
pop = np.asarray(X.sum(0)).ravel().astype(np.float32)
tr_in, val = temporal_split(train, test_frac=0.1)
enc_v = Encoder(tr_in); tv, vv = enc_v.transform(tr_in), enc_v.transform(val)
Xv, relv = enc_v.csr(tv), test_relevance(vv)
print(f"train {len(tr):,} · test {len(te):,} (explícito) · usuarios top-K test {len(rel)}")

# Deriva temporal: la media de los ratings cambia con el tiempo (motivación de timeSVD++)
m_ = ratings.assign(month=pd.to_datetime(ratings.timestamp, unit="s").dt.to_period("M")).groupby("month").rating.agg(["mean", "size"])
fig, ax = plt.subplots(figsize=(10, 3)); ax.plot(m_.index.astype(str), m_["mean"], "o-")
ax2 = ax.twinx(); ax2.bar(m_.index.astype(str), m_["size"], alpha=0.25, color="grey"); ax2.set_yscale("log"); ax2.grid(False)
ax.axvline(str(pd.to_datetime(train.timestamp.max(), unit="s").to_period("M")), color="#c44e52", ls="--", label="corte train/test")
ax.set_ylabel("rating medio"); ax2.set_ylabel("nº ratings (log)"); ax.tick_params(axis="x", rotation=90, labelsize=7)
ax.set_title("ML-1M: la media de ratings deriva con el tiempo"); ax.legend(); plt.tight_layout(); plt.show()
''')

nb.md("""
## 🔨 4. FunkSVD con SGD desde cero (explícito, RMSE)

El bucle de SGD sobre ~800 k ratings en Python puro tardaría minutos por época; con **numba** (JIT,
preinstalado en Colab) baja a décimas de segundo, y el código sigue siendo el de la fórmula.
""")
nb.code(r'''
try:
    from numba import njit
except ImportError:                                          # fallback (lento) sin numba
    def njit(*a, **k):
        return a[0] if a and callable(a[0]) else (lambda f: f)


@njit(fastmath=True)
def sgd_epoch(u, i, r, perm, mu, bu, bi, P, Q, lr, reg, reg_b, use_bias):
    se = 0.0
    k = P.shape[1]
    for t in perm:
        uu, ii = u[t], i[t]
        pred = mu + (bu[uu] + bi[ii] if use_bias else 0.0)
        for f in range(k):
            pred += P[uu, f] * Q[ii, f]
        e = r[t] - pred
        se += e * e
        if use_bias:
            bu[uu] += lr * (e - reg_b * bu[uu])
            bi[ii] += lr * (e - reg_b * bi[ii])
        for f in range(k):
            pf, qf = P[uu, f], Q[ii, f]
            P[uu, f] += lr * (e * qf - reg * pf)
            Q[ii, f] += lr * (e * pf - reg * qf)
    return np.sqrt(se / len(perm))
''')
nb.code(r'''
class FunkSVD:
    def __init__(self, k=64, lr=0.01, reg=0.05, reg_b=0.01, epochs=20, use_bias=True, init_std=0.1):
        self.__dict__.update(locals()); del self.__dict__["self"]

    def predict(self, u, i):
        p = self.mu + (self.bu[u] + self.bi[i] if self.use_bias else 0) + (self.P[u] * self.Q[i]).sum(1)
        return np.clip(p, 1, 5)

    def fit(self, df, n_users, n_items, eval_df=None):
        rng = np.random.default_rng(seed)
        u, i, r = df.uidx.values.astype(np.int64), df.iidx.values.astype(np.int64), df.rating.values.astype(np.float64)
        self.mu = r.mean()
        self.bu, self.bi = np.zeros(n_users), np.zeros(n_items)
        self.P = rng.normal(0, self.init_std, (n_users, self.k)); self.Q = rng.normal(0, self.init_std, (n_items, self.k))
        self.history = []
        for ep in range(self.epochs):
            tr_rmse = sgd_epoch(u, i, r, rng.permutation(len(r)), self.mu, self.bu, self.bi, self.P, self.Q,
                                self.lr, self.reg, self.reg_b, self.use_bias)
            row = {"epoch": ep + 1, "train": tr_rmse}
            if eval_df is not None:
                row["test"] = rmse(self.predict(eval_df.uidx.values, eval_df.iidx.values), eval_df.rating.values)
            self.history.append(row)
        return self


def rmse(pred, y):
    return float(np.sqrt(np.mean((np.asarray(pred) - np.asarray(y)) ** 2)))
''')
nb.code(r'''
# Escalera de modelos: media global → sesgos → MF sin sesgos → MF con sesgos
rm = {"Media global μ": rmse(np.full(len(te), tr.rating.mean()), te.rating)}
models_rmse = {}
for name, kw in [("Solo sesgos (k=0)", dict(k=0, use_bias=True)), ("MF sin sesgos (k=64)", dict(k=64, use_bias=False)),
                 ("MF + sesgos (k=64)", dict(k=64, use_bias=True))]:
    t0 = time.time()
    models_rmse[name] = FunkSVD(epochs=EPOCHS, lr=0.007, **kw).fit(tr, enc.n_users, enc.n_items, eval_df=te)
    rm[name] = min(h["test"] for h in models_rmse[name].history)
    print(f"{name:22s} RMSE test = {rm[name]:.4f}  ({time.time() - t0:.1f}s)")
fig, axes = plt.subplots(1, 2, figsize=(14, 4))
for name, m in models_rmse.items():
    h = pd.DataFrame(m.history)
    axes[0].plot(h.epoch, h.train, "--", label=f"{name} · train"); axes[0].plot(h.epoch, h.test, "-", label=f"{name} · test")
axes[0].set_xlabel("época"); axes[0].set_ylabel("RMSE"); axes[0].set_title("Curvas de convergencia (SGD)"); axes[0].legend(fontsize=7)
pd.Series(rm).plot.barh(ax=axes[1], color=["grey", "#8da0cb", "#fc8d62", "#66c2a5"])
axes[1].set_xlim(min(rm.values()) - 0.03, max(rm.values()) + 0.01); axes[1].set_title("Mejor RMSE en test temporal ↓")
plt.tight_layout(); plt.show()
''')
nb.md("""
🧪 **Lección del Netflix Prize en una gráfica**: los **sesgos solos** se llevan la mayor parte de la
mejora sobre la media global. La interacción $\\mathbf p_u^\\top\\mathbf q_i$ añade el resto, y **sin
sesgos** el modelo tiene que gastar factores en aprender «esta película es buena», y converge peor.
Fíjate también en el **sobreajuste**: el RMSE de train sigue bajando mientras el de test se estanca o sube.
""")
nb.code(r'''
# Efecto de la regularización λ y de la dimensión k
regs = [0.0, 0.02, 0.05, 0.1, 0.2] if FAST_DEV_RUN else [0.0, 0.01, 0.02, 0.035, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3]
ks_ = [8, 32, 128] if FAST_DEV_RUN else [4, 8, 16, 32, 64, 128, 256]
reg_res = {lam: FunkSVD(k=64, reg=lam, lr=0.007, epochs=EPOCHS).fit(tr, enc.n_users, enc.n_items, eval_df=te).history[-1] for lam in regs}
k_res = {kk: FunkSVD(k=kk, reg=0.05, lr=0.007, epochs=EPOCHS).fit(tr, enc.n_users, enc.n_items, eval_df=te).history[-1] for kk in ks_}
fig, axes = plt.subplots(1, 2, figsize=(13, 3.8))
axes[0].plot(regs, [reg_res[l]["train"] for l in regs], "o--", label="train"); axes[0].plot(regs, [reg_res[l]["test"] for l in regs], "o-", label="test")
axes[0].set_xlabel("λ (regularización L2)"); axes[0].set_ylabel("RMSE"); axes[0].set_title("Sesgo-varianza: λ pequeño sobreajusta"); axes[0].legend()
axes[1].semilogx(ks_, [k_res[k]["train"] for k in ks_], "o--", label="train"); axes[1].semilogx(ks_, [k_res[k]["test"] for k in ks_], "o-", label="test")
axes[1].set_xlabel("k (dimensión latente)"); axes[1].set_title("Más factores ≠ mejor test sin más regularización"); axes[1].legend()
plt.tight_layout(); plt.show()
''')

nb.md("""
## 🗺️ 5. Visualizar el espacio latente

Tomamos los vectores $\\mathbf q_i$ de la MF con sesgos, los proyectamos con PCA y coloreamos por género.
Solo usamos películas con ≥ 100 ratings (los vectores de ítems raros son casi ruido + regularización).
""")
nb.code(r'''
from sklearn.decomposition import PCA
mf = models_rmse["MF + sesgos (k=64)"]
mask = pop >= 100
Z = PCA(2, random_state=seed).fit_transform(mf.Q[mask])
gsel = ["Children's", "Horror", "Romance", "Sci-Fi", "Documentary", "Film-Noir"]
lab = np.array([next((g for g in gsel if g in gs), "otro") for gs in genres_[mask]])
fig, axes = plt.subplots(1, 2, figsize=(15, 6))
for k_, g in enumerate(gsel + ["otro"]):
    m = lab == g
    axes[0].scatter(Z[m, 0], Z[m, 1], s=8 if g == "otro" else 16, alpha=0.35 if g == "otro" else 0.8,
                    color="lightgrey" if g == "otro" else plt.get_cmap("tab10")(k_), label=g)
for q in ["Toy Story (1995)", "Star Wars: Episode IV", "Scream (1996)", "Titanic (1997)", "Pulp Fiction", "Godfather, The (1972)"]:
    hits = np.flatnonzero(pd.Series(titles[mask]).str.contains(q, regex=False))
    if len(hits): axes[0].annotate(titles[mask][hits[0]][:24], Z[hits[0]], fontsize=8, weight="bold")
axes[0].legend(fontsize=8, markerscale=2); axes[0].set_title("Espacio latente de FunkSVD (PCA de q_i)")
axes[1].scatter(np.log10(pop[mask]), mf.bi[mask], s=6, alpha=0.5, c=np.linalg.norm(mf.Q[mask], axis=1), cmap="viridis")
axes[1].set_xlabel("log10(popularidad)"); axes[1].set_ylabel("sesgo del ítem b_i"); axes[1].set_title("b_i vs popularidad (color = ‖q_i‖)")
plt.tight_layout(); plt.show()
''')
nb.md("""
💡 El eje principal suele separar películas «de nicho/autor» de *blockbusters* familiares, y los
géneros forman regiones sin haberlos usado nunca. El sesgo $b_i$ captura la «calidad percibida»
(observa que no es lo mismo que popularidad).

## 🏭 6. Surprise: SVD y SVD++ (explícito)
`surprise.SVD` es exactamente la MF con sesgos de arriba; `SVDpp` añade el término implícito de SVD++.
SVD++ es mucho más lento (cada predicción suma los $\\mathbf y_j$ de todo el historial), así que en
`FAST_DEV_RUN` lo entrenamos sobre las 1 500 películas más populares.
""")
nb.code(r'''
from surprise import Dataset, Reader, SVD, SVDpp, accuracy

top_items = set(np.argsort(-pop)[: (1500 if FAST_DEV_RUN else len(pop))])
tr_s, te_s = tr[tr.iidx.isin(top_items)], te[te.iidx.isin(top_items)]
reader = Reader(rating_scale=(1, 5))
trainset = Dataset.load_from_df(tr_s[["uidx", "iidx", "rating"]], reader).build_full_trainset()
testset = list(te_s[["uidx", "iidx", "rating"]].itertuples(index=False, name=None))
sur = {}
for name, algo in [("Surprise SVD", SVD(n_factors=64, n_epochs=EPOCHS, lr_all=0.007, reg_all=0.05, random_state=seed)),
                   ("Surprise SVD++", SVDpp(n_factors=32, n_epochs=max(5, EPOCHS // 3), lr_all=0.007, reg_all=0.05, random_state=seed, cache_ratings=True))]:
    t0 = time.time(); algo.fit(trainset)
    sur[name] = (accuracy.rmse(algo.test(testset), verbose=False), time.time() - t0)
ours = FunkSVD(k=64, epochs=EPOCHS, lr=0.007).fit(tr_s, enc.n_users, enc.n_items, eval_df=te_s)
sur["FunkSVD (nuestro)"] = (ours.history[-1]["test"], np.nan)
pd.DataFrame(sur, index=["RMSE test", "tiempo (s)"]).T.round(4)
''')

nb.md("""
## 🔨 7. Feedback implícito: iALS desde cero

Ahora cambiamos de problema: **top-K con datos implícitos** (¿lo vio?), evaluado con NDCG@10 como
en los módulos 03–04. Implementamos las ecuaciones de la sección 2.5 con el truco de $\\mathbf Q^\\top\\mathbf Q$.
""")
nb.code(r'''
def als_half_step(Cm: sp.csr_matrix, Y: np.ndarray, reg: float) -> np.ndarray:
    """Resuelve todas las filas: x_u = (YᵀY + Yᵀ(C_u−I)Y + λI)⁻¹ Yᵀ C_u p_u.
    Cm guarda (c_ui − 1) = α·r_ui en las celdas observadas."""
    k = Y.shape[1]
    YtY = Y.T @ Y + reg * np.eye(k)
    out = np.zeros((Cm.shape[0], k))
    for u in range(Cm.shape[0]):
        a, b = Cm.indptr[u], Cm.indptr[u + 1]
        if a == b:
            continue
        idx, cu = Cm.indices[a:b], Cm.data[a:b]
        Yu = Y[idx]
        A = YtY + (Yu.T * cu) @ Yu                     # YᵀY + Yᵀ(C_u − I)Y + λI
        rhs = Yu.T @ (1.0 + cu)                        # Yᵀ C_u p_u (p=1 solo en observados)
        out[u] = np.linalg.solve(A, rhs)
    return out


def ials_scratch(X, k=64, alpha=1.0, reg=50.0, iters=10, val=None):
    rng = np.random.default_rng(seed)
    U = rng.normal(0, 0.1 / np.sqrt(k), (X.shape[0], k)); V = rng.normal(0, 0.1 / np.sqrt(k), (X.shape[1], k))
    Cu = (X * alpha).tocsr(); Ci = Cu.T.tocsr()
    hist = []
    for it in range(1, iters + 1):
        t0 = time.time()
        U = als_half_step(Cu, V, reg); V = als_half_step(Ci, U, reg)
        row = {"iter": it, "seg": time.time() - t0}
        if val is not None:
            row["NDCG@10"] = evaluate_topk(mf_score_fn(U, V), *val)["NDCG@10"]
        hist.append(row)
    return U, V, pd.DataFrame(hist)


mf_score_fn = lambda U, V: (lambda ub: U[ub] @ V.T)
U_s, V_s, h_ials = ials_scratch(Xv, k=64, alpha=1.0, reg=50.0, iters=5 if FAST_DEV_RUN else 15, val=(Xv, relv))
h_ials
''')
nb.code(r'''
# Mismos hiperparámetros, entrenado con todo train → test
U_s, V_s, _ = ials_scratch(X, k=64, alpha=1.0, reg=50.0, iters=5 if FAST_DEV_RUN else 15)
results = {"Popularidad": evaluate_topk(lambda ub: np.tile(pop, (len(ub), 1)), X, rel),
           "iALS desde cero (k=64)": evaluate_topk(mf_score_fn(U_s, V_s), X, rel)}
results["iALS desde cero (k=64)"]
''')

nb.md("""
### 7.1 Fold-in: recomendar a un usuario **nuevo** sin re-entrenar

Con $\\mathbf Q$ fijo, el vector de un usuario nuevo es **una sola** resolución ridge (la misma
ecuación de ALS). Es como funciona el *cold start* «suave» en producción: el usuario marca 3
películas en el onboarding y en milisegundos tiene recomendaciones.
""")
nb.code(r'''
def fold_in(item_idx, V, alpha=1.0, reg=50.0):
    Vu = V[item_idx]; cu = np.full(len(item_idx), alpha)
    A = V.T @ V + (Vu.T * cu) @ Vu + reg * np.eye(V.shape[1])
    return np.linalg.solve(A, Vu.T @ (1 + cu))


def find(t):
    return int(np.flatnonzero(pd.Series(titles).str.contains(t, regex=False))[0])


for liked in [["Alien (1979)", "Terminator, The (1984)", "Blade Runner (1982)"],
              ["Toy Story (1995)", "Lion King, The (1994)", "Aladdin (1992)"]]:
    items = [find(t) for t in liked]
    s = V_s @ fold_in(items, V_s); s[items] = -np.inf
    print("👤 Le gustan:", liked, "\n   →", list(titles[np.argsort(-s)[:6]]))
''')

nb.md("""
## 🔨 8. BPR desde cero en PyTorch (GPU)

BPR es el primer modelo del curso que se entrena como una red: embeddings + pérdida por pares +
Adam en mini-batches. Exactamente el patrón que escalará a two-tower (módulo 08).
""")
nb.code(BPR_CODE)
nb.code(r'''
t0 = time.time()
bpr_model, h_bpr = train_bpr(Xv, k=64, lr=5e-3, reg=1e-5, epochs=EPOCHS, eval_every=5, val=(Xv, relv))
print(f"BPR (val) entrenado en {time.time() - t0:.0f}s en {device}")
fig, ax = plt.subplots(figsize=(8, 3.4)); ax.plot(h_bpr.epoch, h_bpr.loss, "o-", label="pérdida BPR")
ax2 = ax.twinx(); hv = h_bpr.dropna(); ax2.plot(hv.epoch, hv["NDCG@10"], "s--", color="#c44e52", label="NDCG@10 val"); ax2.grid(False)
ax.set_xlabel("época"); ax.set_ylabel("−log σ(x_uij)"); ax2.set_ylabel("NDCG@10", color="#c44e52")
ax.set_title("BPR: la pérdida baja… ¿y el ranking?"); plt.show()
bpr_full, _ = train_bpr(X, k=64, lr=5e-3, reg=1e-5, epochs=EPOCHS, verbose=False)
results["BPR desde cero (k=64)"] = evaluate_topk(bpr_score_fn(bpr_full), X, rel)
''')

nb.md("""
## 🏭 9. Librerías de industria: `implicit` (GPU) y `cornac`

`implicit` (Ben Frederickson) es la librería de referencia para iALS/BPR: Cython + OpenMP en CPU y
**kernels CUDA propios** en GPU. Las *wheels* de PyPI para Linux incluyen soporte GPU (requieren un
toolkit CUDA compatible); comprobamos `implicit.gpu.HAS_CUDA` y, si no hay GPU, cae a CPU.
""")
nb.code(IALS_LIB_CODE)
nb.code(r'''
print("implicit en GPU:", USE_GPU)
lib_rows = {}
for factors in ([64, 128] if FAST_DEV_RUN else [64, 128, 256]):
    t0 = time.time(); m = fit_ials(X, factors=factors, reg=50.0, alpha=1.0, iters=15)
    results[f"implicit iALS (k={factors})"] = evaluate_topk(mf_score_fn(m.user_factors, m.item_factors), X, rel)
    lib_rows[f"iALS k={factors}"] = time.time() - t0
from implicit.bpr import BayesianPersonalizedRanking
t0 = time.time()
mb = BayesianPersonalizedRanking(factors=64, learning_rate=0.01, regularization=0.01, iterations=100, use_gpu=USE_GPU, random_state=seed)
mb.fit(X, show_progress=False); mb = mb.to_cpu() if USE_GPU else mb
results["implicit BPR (k=64)"] = evaluate_topk(mf_score_fn(mb.user_factors, mb.item_factors), X, rel)
lib_rows["BPR k=64"] = time.time() - t0
print({k: f"{v:.1f}s" for k, v in lib_rows.items()})
''')
nb.code(r'''
# Mapa de hiperparámetros de iALS en VALIDACIÓN: α (confianza) × λ (regularización)
alphas_ = [0.5, 1.0, 5.0] if FAST_DEV_RUN else [0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
regs_ = [1.0, 10.0, 50.0, 200.0] if FAST_DEV_RUN else [0.1, 1.0, 5.0, 10.0, 25.0, 50.0, 100.0, 200.0, 500.0]
H = np.zeros((len(alphas_), len(regs_)))
for a_i, a in enumerate(alphas_):
    for r_i, lam in enumerate(regs_):
        m = fit_ials(Xv, factors=64, reg=lam, alpha=a, iters=10)
        H[a_i, r_i] = evaluate_topk(mf_score_fn(m.user_factors, m.item_factors), Xv, relv)["NDCG@10"]
fig, ax = plt.subplots(figsize=(8, 3.6))
im = ax.imshow(H, cmap="magma", aspect="auto"); ax.grid(False)
ax.set_xticks(range(len(regs_)), regs_); ax.set_yticks(range(len(alphas_)), alphas_)
ax.set_xlabel("λ (regularization)"); ax.set_ylabel("α (alpha)")
for a_i in range(len(alphas_)):
    for r_i in range(len(regs_)): ax.text(r_i, a_i, f"{H[a_i, r_i]:.3f}", ha="center", va="center", color="w", fontsize=8)
ax.set_title("iALS (implicit): NDCG@10 en validación"); plt.colorbar(im); plt.show()
''')
nb.code(r'''
# cornac: otra librería de investigación con decenas de modelos (aquí su BPR en Cython)
try:
    import cornac
    from cornac.data import Dataset as CDataset
    uir = list(zip(tr.uidx.astype(str), tr.iidx.astype(str), np.ones(len(tr))))
    cds = CDataset.from_uir(uir, seed=seed)
    t0 = time.time()
    cbpr = cornac.models.BPR(k=64, max_iter=100, learning_rate=0.01, lambda_reg=0.01, seed=seed, verbose=False).fit(cds)
    u_int = np.array([cds.uid_map[str(u)] for u in range(enc.n_users)])
    i_int = np.array([cds.iid_map[str(i)] for i in range(enc.n_items)])
    Uc, Vc, bc = cbpr.u_factors[u_int], cbpr.i_factors[i_int], cbpr.i_biases[i_int]
    results["cornac BPR (k=64)"] = evaluate_topk(lambda ub: Uc[ub] @ Vc.T + bc, X, rel)
    print(f"cornac BPR: {time.time() - t0:.1f}s")
except Exception as e:
    print("cornac no disponible:", e)
''')

nb.md("""
## 🧪 10. ¿Gana la MF a EASE? (y a la popularidad)

Añadimos EASE del módulo 04 (con λ elegido en validación) como referencia obligatoria.
""")
nb.code(r'''
def ease(Xm, lam):
    G = torch.tensor((Xm.T @ Xm).toarray(), dtype=torch.float32, device=device)
    P = torch.linalg.inv(G + lam * torch.eye(G.shape[0], device=device)); B = -P / torch.diag(P); B.fill_diagonal_(0)
    return B.cpu().numpy()


lam_best = max([500, 1000, 3000, 10000], key=lambda l: evaluate_topk(lambda ub: np.asarray(Xv[ub] @ ease(Xv, l)), Xv, relv)["NDCG@10"])
B = ease(X, lam_best)
results[f"EASE (λ={lam_best})"] = evaluate_topk(lambda ub: np.asarray(X[ub] @ B), X, rel)
res_df = pd.DataFrame(results).T.drop(columns="n_users").sort_values("NDCG@10")
fig, axes = plt.subplots(1, 2, figsize=(14, 4.4))
res_df["NDCG@10"].plot.barh(ax=axes[0], color=["#c44e52" if ("Popularidad" in i or "EASE" in i) else "#4c72b0" for i in res_df.index])
axes[0].set_xlim(res_df["NDCG@10"].min() * 0.9, None); axes[0].set_title("NDCG@10 en test temporal")
axes[1].scatter(res_df["Coverage"], res_df["NDCG@10"])
for n_, r_ in res_df.iterrows(): axes[1].annotate(n_, (r_["Coverage"], r_["NDCG@10"]), fontsize=7)
axes[1].set_xlabel("Coverage"); axes[1].set_ylabel("NDCG@10"); axes[1].set_title("Precisión vs cobertura")
plt.tight_layout(); plt.show()
res_df.round(4)
''')
nb.md("""
🧪 En este split temporal, **iALS bien regularizado** queda a la par o por encima de EASE y de la
popularidad; BPR con muestreo uniforme queda por debajo salvo que lo tunees a fondo (lo harás en el
proyecto con Optuna). Mira el heatmap: con λ pequeño, iALS **pierde contra la popularidad**. Esa es la
razón de tantos papers que «baten a iALS»: compararon contra un iALS mal tuneado.
""")

nb.md("""
## 🏭 11. En producción

- **Netflix**: tras el Prize, Netflix contó que puso en producción **dos** de los algoritmos del
  Progress Prize de 2007 (una variante de SVD/MF y RBMs, combinados linealmente), pero que el
  *ensemble* ganador del Grand Prize **no compensaba** el esfuerzo de ingeniería frente a la ganancia
  medida, y que el negocio ya se había movido al **streaming** (feedback implícito, no estrellas)
  (Amatriain & Basilico, Netflix Tech Blog, 2012).
- **Spotify**: Johnson (2014, *Logistic Matrix Factorization for Implicit Feedback Data*) describe la
  factorización implícita de escuchas que usaban a escala; los vectores se sirven con ANN (**Annoy**, la
  librería de vecinos aproximados que Erik Bernhardsson creó en Spotify).
- **Facebook/Meta**: ALS distribuido en Apache Giraph para recomendar a más de mil millones de
  personas (Kabiljo & Ilic, *Recommending items to more than a billion people*, Engineering at Meta, 2015).
- **Google**: WALS (*weighted* ALS, la misma idea que iALS) en TensorFlow y en sus soluciones de
  recomendación de Cloud; Rendle, Krichene y colegas (Google Research) son quienes «revisitaron» iALS.

**Serving**: los vectores de ítem se indexan en un ANN de producto escalar (MIPS: FAISS/ScaNN,
módulo 08); el vector de usuario se recalcula *offline* o con **fold-in** online con sus últimas
interacciones. MF hoy es sobre todo un **generador de candidatos** o una **feature** (el score $\\mathbf p_u^\\top\\mathbf q_i$)
para el ranker.
""")
nb.md("""
## 🧠 12. Secretos de la élite

1. **Los sesgos primero.** En el Netflix Prize, el modelo de *baseline* $\\mu+b_u+b_i$ (con sus versiones
   temporales) explicaba gran parte de la señal; Koren dedica secciones enteras a afinarlos. Si tu MF no
   tiene sesgos (o no centras), estás gastando factores en aprender la media.
2. **RMSE ≠ ranking.** Cremonesi, Koren & Turrin (RecSys 2010) mostraron que modelos optimizados para
   RMSE pueden ser peores en top-N que métodos simples como PureSVD (SVD sobre la matriz con ceros) o
   popularidad. Por eso la industria migró a objetivos implícitos (iALS, BPR, softmax).
3. **iALS bien tuneado bate a muchos modelos modernos** (Rendle, Krichene, Zhang & Koren, RecSys 2022):
   el truco está en la **regularización** (mucha, y escalada por frecuencia), la **dimensión** (cientos o miles)
   y la **inicialización pequeña**. En la misma línea, Rendle et al. (RecSys 2020) mostraron que un **producto
   escalar** bien tuneado supera al MLP de NCF como función de similitud.
4. **Netflix nunca desplegó el ensemble ganador.** La ganancia marginal de mezclar muchísimos modelos no
   justificaba la complejidad; los objetivos del negocio (streaming, implícito, filas de la home) habían
   cambiado. Lección: el mejor modelo offline no es necesariamente el mejor sistema.
5. **BPR uniforme aprende despacio** porque casi todos los negativos aleatorios ya son fáciles. Muestreo
   adaptativo/por popularidad (Rendle & Freudenthaler, WSDM 2014) o WARP aceleran y mejoran la cabeza del ranking.
6. **Fold-in en vez de re-entrenar.** Con ALS, un usuario nuevo es una resolución ridge $k\\times k$: tiempo real
   sin re-entrenar el modelo. Re-entrenos completos nocturnos + fold-in online es el patrón clásico.
7. **La norma del vector codifica popularidad.** Con producto escalar, los ítems de norma grande salen en
   todas las listas; si quieres más diversidad, normaliza (coseno) o penaliza la norma en el re-ranking.
""")
nb.md("""
## ⚠️ 13. Errores comunes

- **Rellenar los faltantes con 0** y hacer SVD clásica para ratings explícitos (el modelo aprende que «no visto = 0 estrellas»).
- **Evaluar RMSE en ítems/usuarios sin train** sin una estrategia de cold start (el modelo predice solo μ + b).
- **Learning rate demasiado alto en SGD** → divergencia (NaN). Empieza en 0,005–0,01 y monitoriza train y test.
- **Comparar iALS con `regularization` por defecto** contra tu modelo tuneado: es un baseline de paja.
- **Muestrear negativos de BPR que en realidad son positivos** de test (fuga) o de train (ruido): filtra los vistos si puedes.
- Olvidar `model.to_cpu()` al usar `implicit` en GPU y luego intentar operar con numpy los factores.
""")
nb.md(r"""
## ✅ 14. Autoevaluación

1. ¿Por qué SGD solo itera sobre las celdas observadas y no sobre toda la matriz?
<details><summary>Respuesta</summary>Porque en feedback explícito las celdas no observadas no son «0 estrellas» sino desconocidas; optimizar sobre ellas sesgaría el modelo. Además hay muchísimas más celdas vacías que observadas.</details>

2. Escribe la regla de actualización de $\mathbf q_i$ en FunkSVD.
<details><summary>Respuesta</summary>$\mathbf q_i\leftarrow\mathbf q_i+\eta(e_{ui}\mathbf p_u-\lambda\mathbf q_i)$ con $e_{ui}=r_{ui}-\hat r_{ui}$.</details>

3. En iALS, ¿por qué el coste por usuario no depende del número total de ítems?
<details><summary>Respuesta</summary>Porque $\mathbf Q^\top\mathbf C^u\mathbf Q=\mathbf Q^\top\mathbf Q+\mathbf Q^\top(\mathbf C^u-\mathbf I)\mathbf Q$: el primer término se calcula una vez por iteración y el segundo solo involucra los $n_u$ ítems vistos.</details>

4. ¿Qué optimiza BPR y con qué métrica está relacionado?
<details><summary>Respuesta</summary>La probabilidad de que un ítem positivo puntúe más que uno negativo (log-sigmoide de la diferencia); es una aproximación suave del AUC por usuario.</details>

5. ¿Qué es el fold-in y por qué es útil en producción?
<details><summary>Respuesta</summary>Calcular el vector de un usuario nuevo resolviendo el problema ridge con los factores de ítem fijos. Permite recomendar en tiempo real a usuarios nuevos o actualizar usuarios sin re-entrenar todo.</details>

6. ¿Por qué Netflix no desplegó el ensemble ganador del Prize?
<details><summary>Respuesta</summary>Porque la ganancia de precisión adicional medida no justificaba el coste de ingeniería, y el producto se había movido al streaming con feedback implícito y otros objetivos.</details>

7. Un paper afirma batir a iALS por un 20 %. ¿Qué preguntas harías?
<details><summary>Respuesta</summary>¿Se tunearon los hiperparámetros de iALS (λ, α, dimensión, iteraciones) con el mismo presupuesto? ¿Mismo split y protocolo (full ranking vs sampled metrics)? ¿Se reportan IC? Ver Rendle et al. 2022 y Dacrema et al. 2019.</details>
""")
nb.md("""
## 📚 15. Referencias

**Papers**
- Funk (2006). *Netflix Update: Try This at Home*. Blog. https://sifter.org/~simon/journal/20061211.html
- Bennett & Lanning (2007). *The Netflix Prize*. KDD Cup and Workshop.
- Koren (2008). *Factorization Meets the Neighborhood: a Multifaceted Collaborative Filtering Model* (SVD++). KDD.
- Hu, Koren & Volinsky (2008). *Collaborative Filtering for Implicit Feedback Datasets*. ICDM.
- Koren (2009). *Collaborative Filtering with Temporal Dynamics* (timeSVD++). KDD.
- Koren, Bell & Volinsky (2009). *Matrix Factorization Techniques for Recommender Systems*. IEEE Computer.
- Koren (2009). *The BellKor Solution to the Netflix Grand Prize*.
- Rendle, Freudenthaler, Gantner & Schmidt-Thieme (2009). *BPR: Bayesian Personalized Ranking from Implicit Feedback*. UAI. [arXiv:1205.2618](https://arxiv.org/abs/1205.2618)
- Cremonesi, Koren & Turrin (2010). *Performance of Recommender Algorithms on Top-N Recommendation Tasks*. RecSys.
- Weston, Bengio & Usunier (2011). *WSABIE: Scaling Up to Large Vocabulary Image Annotation* (WARP). IJCAI.
- Rendle & Freudenthaler (2014). *Improving Pairwise Learning for Item Recommendation from Implicit Feedback*. WSDM.
- Johnson (2014). *Logistic Matrix Factorization for Implicit Feedback Data*. NIPS Workshop.
- Kula (2015). *Metadata Embeddings for User and Item Cold-start Recommendations* (LightFM). CBRecSys.
- Rendle, Krichene, Zhang & Anderson (2020). *Neural Collaborative Filtering vs. Matrix Factorization Revisited*. RecSys. [arXiv:2005.09683](https://arxiv.org/abs/2005.09683)
- Rendle, Krichene, Zhang & Koren (2022). *Revisiting the Performance of iALS on Item Recommendation Benchmarks*. RecSys. [arXiv:2110.14037](https://arxiv.org/abs/2110.14037)
- Rendle, Krichene, Zhang & Koren (2021). *iALS++: Speeding up Matrix Factorization with Subspace Optimization*. [arXiv:2110.14044](https://arxiv.org/abs/2110.14044)

**Blogs de ingeniería**
- Amatriain & Basilico (2012). *Netflix Recommendations: Beyond the 5 stars (Part 1)*. Netflix Tech Blog. https://netflixtechblog.com/netflix-recommendations-beyond-the-5-stars-part-1-55838468f429
- Kabiljo & Ilic (2015). *Recommending items to more than a billion people*. Engineering at Meta.
- Frederickson (2017). *Implicit Matrix Factorization on the GPU*. https://www.benfrederickson.com/implicit-matrix-factorization-on-the-gpu/

**Librerías**: [implicit](https://github.com/benfred/implicit) · [Surprise](https://surpriselib.com) · [cornac](https://cornac.preferred.ai) · [LightFM](https://github.com/lyst/lightfm) · [Optuna](https://optuna.org)
""")
nb.save(LESSON)

# ---------------------------------------------------------------------------
# PROYECTO
# ---------------------------------------------------------------------------
PROJ = f"{MOD}/05_proyecto_ials_bpr.ipynb"
pj = Notebook("Proyecto 05 · iALS + BPR en GPU con Optuna", colab_path=PROJ, gpu=True)
pj.md(f"""
{pj.badge()}

# Proyecto 05 · «Recomendado para ti» v2: iALS + BPR en GPU, tuneados con Optuna
| | |
|---|---|
| **Nivel** | 🟠 Avanzado |
| **Duración** | 4–6 h |
| **GPU** | T4 (≈ 1–2 unidades con `FAST_DEV_RUN=False`) |
| **Prerrequisitos** | Lección 05, proyecto 04 |

## 🏢 Contexto de negocio
La fila «Recomendado para ti» de CineMatch usa EASE (proyecto 04). El equipo de plataforma quiere
pasar a **factores latentes** porque (1) los vectores se pueden indexar en un ANN y servir a escala,
(2) permiten **fold-in** de usuarios nuevos en tiempo real y (3) sirven como features del ranker.
Tu misión: entrenar **iALS** y **BPR** en GPU, tunearlos con **Optuna** con el mismo presupuesto, y
demostrar si igualan o superan a EASE.

## 📦 Dataset
MovieLens 1M, split temporal global (utilidades), validación temporal dentro de train. Implícito =
cualquier rating; relevante = rating ≥ 4.

## 📋 Entregables y rúbrica
| # | Entregable | Criterio |
|---|---|---|
| 1 | `train_bpr()` en PyTorch con negativos uniformes y opción de **negativos por popularidad** | Corre en GPU; curva de pérdida y NDCG |
| 2 | Estudios Optuna para iALS y BPR (mismo nº de trials) | ≥ 40 trials cada uno con `FAST_DEV_RUN=False` (en GPU) |
| 3 | Tabla final en test (NDCG@10, Recall@10, Coverage) con Popularidad, EASE, iALS, BPR | **iALS ≥ 0,225** NDCG@10; **BPR ≥ 0,17** (reto: ≥ 0,21, el nivel de `cornac` BPR en la lección) |
| 4 | Importancia de hiperparámetros (Optuna) + interpretación | 1 párrafo |
| 5 | `recommend_new_user(liked_titles)` con **fold-in** y su latencia | < 5 ms por usuario en CPU |
""")
pj.code("""
!pip install -q implicit optuna pyarrow
""")
pj.code(r'''
import os, random, time, warnings
import numpy as np, pandas as pd, matplotlib.pyplot as plt, torch
warnings.filterwarnings("ignore")
seed = 42; random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
device = "cuda" if torch.cuda.is_available() else "cpu"
FAST_DEV_RUN = True
N_TRIALS = 8 if FAST_DEV_RUN else 40
print("device:", device)
''')
add_utils(pj)
pj.code(r'''
ratings, movies, users = load_movielens_1m()
train, test = temporal_split(ratings)
enc = Encoder(train); X = enc.csr(enc.transform(train)); rel = test_relevance(enc.transform(test))
tr_in, val = temporal_split(train, test_frac=0.1)
enc_v = Encoder(tr_in); Xv = enc_v.csr(enc_v.transform(tr_in)); relv = test_relevance(enc_v.transform(val))
titles = movies.set_index("item_id").title.loc[enc.items].values
pop = np.asarray(X.sum(0)).ravel().astype(np.float32)
''')
pj.code(IALS_LIB_CODE)
pj.md("""
## Paso 1 · BPR en PyTorch  ✏️ TODO
Implementa `train_bpr(X, k, lr, reg, epochs, neg="uniform"|"pop", pop_power=0.75)`:
- Modelo: embeddings de usuario/ítem + sesgo de ítem; pérdida $-\\log\\sigma(\\hat x_{ui}-\\hat x_{uj})$ + L2.
- `neg="pop"`: muestrea $j \\propto n_j^{0.75}$ (como word2vec) con `torch.multinomial`.
- Devuelve el modelo y una función `score_fn(ub)` compatible con `evaluate_topk`.
""")
pj.code(r'''
def train_bpr(X, k=64, lr=5e-3, reg=1e-5, epochs=20, batch=8192, neg="uniform", pop_power=0.75):
    # TODO
    raise NotImplementedError
''')
pj.md("""
## Paso 2 · Optuna  ✏️ TODO
Define `objective_ials(trial)` (factors ∈ {32…512}, regularization log ∈ [0,1; 1 000], alpha log ∈ [0,1; 50],
iterations ∈ [5, 30]) y `objective_bpr(trial)` (k, lr, reg, epochs, neg). Maximiza NDCG@10 en validación
con `TPESampler(seed=42)`. Usa el mismo `N_TRIALS` para ambos (comparación justa).
""")
pj.code(r'''
# TODO: estudios de Optuna
''')
pj.md("""
## Paso 3 · Evaluación final y comparación con EASE  ✏️ TODO
Re-entrena con todo `X` usando los mejores hiperparámetros. Añade Popularidad y EASE (λ en validación).
""")
pj.code(r'''
# TODO: tabla final
''')
pj.md("""
## Paso 4 · Fold-in para usuarios nuevos  ✏️ TODO
`recommend_new_user(liked_titles, k=10)` usando los factores de ítem del mejor iALS. Mide la latencia.
""")
pj.code(r'''
# TODO: fold-in
''')
pj.md("""
---
# ⛔ SPOILER — intenta resolverlo primero
Solución de referencia completa.
""")
pj.code(r'''
import torch.nn as nn
import torch.nn.functional as Fnn


class BPRMF(nn.Module):
    def __init__(self, n_users, n_items, k):
        super().__init__()
        self.P, self.Q, self.b = nn.Embedding(n_users, k), nn.Embedding(n_items, k), nn.Embedding(n_items, 1)
        nn.init.normal_(self.P.weight, std=0.01); nn.init.normal_(self.Q.weight, std=0.01); nn.init.zeros_(self.b.weight)

    def forward(self, u, i, j):
        return (self.P(u) * (self.Q(i) - self.Q(j))).sum(1) + (self.b(i) - self.b(j)).squeeze(1)


def train_bpr(X, k=64, lr=5e-3, reg=1e-5, epochs=20, batch=8192, neg="uniform", pop_power=0.75, return_hist=False):
    torch.manual_seed(seed)
    model = BPRMF(*X.shape, k).to(device); opt = torch.optim.Adam(model.parameters(), lr=lr)
    uu, ii = X.nonzero(); uu, ii = torch.tensor(uu, device=device), torch.tensor(ii, device=device)
    probs = torch.tensor(np.asarray(X.sum(0)).ravel() ** pop_power, dtype=torch.float32, device=device)
    hist = []
    for ep in range(epochs):
        perm, tot = torch.randperm(len(uu), device=device), 0.0
        for s in range(0, len(uu), batch):
            b = perm[s:s + batch]; u, i = uu[b], ii[b]
            j = (torch.randint(0, X.shape[1], (len(b),), device=device) if neg == "uniform"
                 else torch.multinomial(probs, len(b), replacement=True))
            l2 = model.P(u).pow(2).sum() + model.Q(i).pow(2).sum() + model.Q(j).pow(2).sum()
            loss = -Fnn.logsigmoid(model(u, i, j)).mean() + reg * l2 / len(b)
            opt.zero_grad(); loss.backward(); opt.step(); tot += loss.item() * len(b)
        hist.append(tot / len(uu))
    P = model.P.weight.detach().cpu().numpy(); Q = model.Q.weight.detach().cpu().numpy(); bb = model.b.weight.detach().cpu().numpy().ravel()
    score_fn = lambda ub: P[ub] @ Q.T + bb
    return (model, score_fn, hist) if return_hist else (model, score_fn)
''')
pj.code(r'''
import optuna
optuna.logging.set_verbosity(optuna.logging.WARNING)


def objective_ials(trial):
    factor_grid = [32, 64, 128] if FAST_DEV_RUN else [32, 64, 128, 256, 512]
    m = fit_ials(Xv, factors=trial.suggest_categorical("factors", factor_grid),
                 reg=trial.suggest_float("reg", 0.1, 1000.0, log=True), alpha=trial.suggest_float("alpha", 0.1, 50.0, log=True),
                 iters=trial.suggest_int("iters", 5, 20 if FAST_DEV_RUN else 30))
    return evaluate_topk(mf_score_fn(m.user_factors, m.item_factors), Xv, relv)["NDCG@10"]


def objective_bpr(trial):
    _, f = train_bpr(Xv, k=trial.suggest_categorical("k", [32, 64, 128]), lr=trial.suggest_float("lr", 1e-3, 3e-2, log=True),
                     reg=trial.suggest_float("reg", 1e-7, 1e-3, log=True), epochs=trial.suggest_int("epochs", 3, 12 if FAST_DEV_RUN else 60),
                     neg=trial.suggest_categorical("neg", ["uniform", "pop"]))
    return evaluate_topk(f, Xv, relv)["NDCG@10"]


studies = {}
for name, obj in [("iALS", objective_ials), ("BPR", objective_bpr)]:
    t0 = time.time()
    st = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=seed))
    st.optimize(obj, n_trials=N_TRIALS)
    studies[name] = st
    print(f"{name}: mejor NDCG@10 val = {st.best_value:.4f} · {st.best_params} · {time.time() - t0:.0f}s")
''')
pj.code(r'''
fig, axes = plt.subplots(1, 3, figsize=(16, 3.8))
for name, st in studies.items():
    v = [t.value for t in st.trials]
    axes[0].plot(np.maximum.accumulate(v), "o-", label=name)
axes[0].set_xlabel("trial"); axes[0].set_ylabel("mejor NDCG@10 val"); axes[0].set_title("Historial de optimización"); axes[0].legend()
for ax, (name, st) in zip(axes[1:], studies.items()):
    try:
        imp = optuna.importance.get_param_importances(st)
        ax.barh(list(imp)[::-1], list(imp.values())[::-1], color="#4c72b0"); ax.set_title(f"Importancia de hiperparámetros · {name}")
    except Exception as e:
        ax.text(0.1, 0.5, f"importancia no disponible: {e.__class__.__name__}"); ax.set_title(name)
plt.tight_layout(); plt.show()
''')
pj.code(r'''
def ease(Xm, lam):
    G = torch.tensor((Xm.T @ Xm).toarray(), dtype=torch.float32, device=device)
    P = torch.linalg.inv(G + lam * torch.eye(G.shape[0], device=device)); B = -P / torch.diag(P); B.fill_diagonal_(0)
    return B.cpu().numpy()


lam_b = max([500, 1000, 3000, 10000], key=lambda l: evaluate_topk(lambda ub: np.asarray(Xv[ub] @ ease(Xv, l)), Xv, relv)["NDCG@10"])
B = ease(X, lam_b)
bi = studies["iALS"].best_params
ials = fit_ials(X, factors=bi["factors"], reg=bi["reg"], alpha=bi["alpha"], iters=bi["iters"])
bb = studies["BPR"].best_params
bpr_model, bpr_fn, bpr_hist = train_bpr(X, k=bb["k"], lr=bb["lr"], reg=bb["reg"], epochs=bb["epochs"], neg=bb["neg"], return_hist=True)
final = {"Popularidad": evaluate_topk(lambda ub: np.tile(pop, (len(ub), 1)), X, rel),
         f"EASE (λ={lam_b})": evaluate_topk(lambda ub: np.asarray(X[ub] @ B), X, rel),
         "iALS (Optuna)": evaluate_topk(mf_score_fn(ials.user_factors, ials.item_factors), X, rel),
         "BPR (Optuna)": evaluate_topk(bpr_fn, X, rel)}
final_df = pd.DataFrame(final).T.drop(columns="n_users")
fig, axes = plt.subplots(1, 2, figsize=(13, 3.6))
final_df["NDCG@10"].plot.barh(ax=axes[0], color="#4c72b0"); axes[0].set_xlim(final_df["NDCG@10"].min() * 0.9, None); axes[0].set_title("NDCG@10 test")
axes[1].plot(bpr_hist, "o-"); axes[1].set_xlabel("época"); axes[1].set_ylabel("pérdida BPR"); axes[1].set_title("Entrenamiento final de BPR")
plt.tight_layout(); plt.show()
final_df.round(4)
''')
pj.code(r'''
V_items = ials.item_factors
lam_fold = bi["reg"]; alpha_fold = bi["alpha"]
VtV = V_items.T @ V_items + lam_fold * np.eye(V_items.shape[1])      # precomputable una vez


def recommend_new_user(liked_titles, k=10):
    idx = [int(np.flatnonzero(pd.Series(titles).str.contains(t, regex=False))[0]) for t in liked_titles]
    Vu = V_items[idx]; cu = np.full(len(idx), alpha_fold)
    # implicit usa confianza c = α·r en las celdas observadas (sin el +1 de Hu et al.); replicamos su ecuación
    u = np.linalg.solve(VtV + (Vu.T * (cu - 1)) @ Vu, Vu.T @ cu)
    s = V_items @ u; s[idx] = -np.inf
    return list(titles[np.argsort(-s)[:k]])


t0 = time.time()
for _ in range(100):
    recs = recommend_new_user(["Alien (1979)", "Terminator, The (1984)", "Blade Runner (1982)"])
print(f"Latencia fold-in + scoring: {(time.time() - t0) * 10:.2f} ms/usuario")
print("Fan de la ciencia ficción ochentera →", recs[:8])
print("Familia con niños →", recommend_new_user(["Toy Story (1995)", "Lion King, The (1994)", "Aladdin (1992)"])[:8])
''')
pj.md("""
### 📝 Interpretación (solución de referencia)
- En ML-1M temporal, la **regularización** de iALS es con diferencia el hiperparámetro más importante:
  valores altos empujan hacia lo popular (que en el futuro paga) y valores bajos sobreajustan al pasado.
- En la lección viste que la NDCG de validación de BPR **baja** mientras la pérdida sigue bajando: con
  negativos uniformes el modelo aprende a separar lo visto de lo impopular (fácil) y se aleja de la
  popularidad reciente. El nº de épocas y el *learning rate* actúan como regularizadores.
- BPR con negativos por popularidad suele converger más rápido que con negativos uniformes y es más
  sensible al *learning rate*; con el mismo presupuesto de trials suele quedar por detrás de iALS.
- iALS iguala o supera a EASE con vectores de 64–512 dimensiones que **sí** se pueden indexar en un ANN
  y servir con fold-in: es la opción para producción a escala.

## 🚀 Retos extra (nivel experto)
1. **iALS revisitado**: implementa la regularización escalada por frecuencia de Rendle et al. (2022) en
   tu iALS desde cero y comprueba si mejora con dimensiones grandes (512–2048).
2. **WARP** con LightFM (`pip install lightfm`; puede requerir compilar) o implementa WARP en PyTorch
   (muestrear negativos hasta violar el margen). Compara precision@5 con BPR.
3. **Fold-in con implicit**: usa `model.recommend(..., recalculate_user=True)` y compara con tu versión.
4. **Ensemble** EASE + iALS (combinación lineal de scores z-normalizados con peso en validación).
5. Indexa los vectores de ítem en **FAISS** (`IndexFlatIP`) y mide recall@100 del ANN vs. scoring exacto.

## 🤔 Reflexión (producción / MLOps)
- ¿Qué artefactos versionarías en MLflow (factores, mapeos de IDs, hiperparámetros, estudio de Optuna)?
- Los vectores de usuario se quedan obsoletos: ¿re-entreno nocturno, fold-in online o ambos?
- ¿Cómo detectarías *embedding drift* entre dos re-entrenos (pista: alinear con Procrustes o comparar vecinos)?
""")
pj.save(PROJ)

Path(f"{MOD}/README.md").write_text("""# 05 · Factorización matricial

🟡→🟠 · 4–5 h (lección) + 4–6 h (proyecto) · GPU T4 recomendada (≈ 1–2 unidades de Colab)

Del Netflix Prize a la recomendación implícita moderna: factores latentes, sesgos, SGD, ALS y BPR.

## Contenido
| Notebook | Qué hay dentro |
|---|---|
| [`05_matrix_factorization.ipynb`](05_matrix_factorization.ipynb) | FunkSVD con SGD (numba) desde cero · escalera μ → sesgos → MF · curvas de convergencia, efecto de λ y k · espacio latente (PCA) · Surprise SVD/SVD++ · iALS desde cero (truco QᵀQ) · fold-in · BPR en PyTorch (GPU) · `implicit` (GPU) iALS/BPR · `cornac` · comparación con EASE |
| [`05_proyecto_ials_bpr.ipynb`](05_proyecto_ials_bpr.ipynb) | «Recomendado para ti» v2: iALS + BPR en GPU tuneados con Optuna, comparación con EASE, fold-in de usuarios nuevos |

## Objetivos
- Derivar e implementar FunkSVD, iALS y BPR; entender el papel de sesgos y regularización.
- Usar `implicit`, `Surprise` y `cornac`; tunear con Optuna sin fuga.
- Conocer la historia del Netflix Prize y qué se llevó a producción.

## Datasets
- **MovieLens 1M** (GroupLens; espejo en GitHub como fallback). Explícito para RMSE; implícito (cualquier rating) para top-K, relevante = rating ≥ 4.

## Lecturas clave
- Koren, Bell & Volinsky (2009), *Matrix Factorization Techniques for Recommender Systems*.
- Hu, Koren & Volinsky (2008), *Collaborative Filtering for Implicit Feedback Datasets*.
- Rendle et al. (2009), *BPR*; Rendle et al. (2022), *Revisiting the Performance of iALS*.
- Amatriain & Basilico (2012), *Netflix Recommendations: Beyond the 5 stars*.

## Conexión con CineMatch
Los vectores de iALS son la primera fuente de candidatos indexable en ANN (módulo 08) y una feature
para el ranker (módulo 06).

Generado con `python recsys-course/_tools/builders/build_05.py`.
""", encoding="utf-8")
print("README OK")
