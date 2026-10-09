"""Builder del módulo 02 · Evaluación offline rigurosa."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "recsys-course/_tools")
from _fund_common import Notebook, utils_cell, writefile_chunks  # noqa: E402

MOD = "recsys-course/02_evaluation"
LESSON = f"{MOD}/02_evaluation.ipynb"
PROJECT = f"{MOD}/02_proyecto_libreria_evaluacion.ipynb"

# =============================================================================
# LECCIÓN
# =============================================================================
nb = Notebook("Módulo 02 · Evaluación offline rigurosa", colab_path=LESSON)
M, C = nb.md, nb.code

M(rf"""
{nb.badge()}

# 📏 Módulo 02 · Evaluación offline rigurosa

**Curso «Sistemas de Recomendación: de cero a nivel Netflix»** · Bloque I — Fundamentos

| | |
|---|---|
| **Nivel** | 🟢 Básico → 🟡 Intermedio |
| **Duración estimada** | 3,5 h (lección) + 3 h (proyecto) |
| **GPU** | No necesaria. ≈ 0 unidades de Colab |
| **Prerrequisitos** | Módulos 00 y 01 (`cinematch_data.py`) |

> "Si no lo puedes medir, no lo puedes mejorar" — y en recomendación es facilísimo medir mal. Cuando Ferrari Dacrema et al. (2019) intentaron reproducir 18 modelos neuronales publicados en conferencias de primer nivel, solo 7 eran reproducibles y 6 de esos 7 perdían frente a baselines simples bien ajustados: **la "mejora" estaba en la evaluación, no en el modelo**. Este módulo te da el evaluador que usarás el resto del curso y, sobre todo, el criterio para no engañarte.
""")

M(r"""
## 🎯 Objetivos de aprendizaje

1. **Explicar** por qué RMSE/MAE no bastan para evaluar un recomendador top-K y **demostrarlo** con un experimento.
2. **Definir, derivar e implementar desde cero** Precision@K, Recall@K, HitRate@K, MRR, MAP y NDCG, y AUC/GAUC.
3. **Verificar** tu implementación contra `ranx` hasta la precisión de máquina.
4. **Medir** métricas *beyond-accuracy*: cobertura, Gini de exposición, novedad, diversidad intra-lista.
5. **Cuantificar la incertidumbre** con intervalos bootstrap y **decidir** si una diferencia es significativa con un test pareado.
6. **Demostrar** por qué las *sampled metrics* son inconsistentes (Krichene & Rendle, 2020).
7. **Aplicar** una checklist de reproducibilidad (Ferrari Dacrema et al., 2019) y **razonar** sobre el *offline-online gap*.
""")

C(r'''
!pip install -q ranx pandas pyarrow scipy matplotlib
''')

C(r'''
import time
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.sparse as sp
from matplotlib.patches import FancyBboxPatch
from scipy import stats

SEED = 42
rng = np.random.default_rng(SEED)
SCALE = "small"                 # "small" → MovieLens-100K · "full" → MovieLens-1M
SIZE = "100k" if SCALE == "small" else "1m"
K = 10
warnings.filterwarnings("ignore")
plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False})
PALETA = ["#9E9E9E", "#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3"]
''')

utils_cell(nb, ["cinematch_data.py"])

C(r'''
import cinematch_data as cd

data = cd.prepare_cinematch(SIZE)            # pipeline del módulo 01
train, val, test, items, ratings = (data[k] for k in ["train", "val", "test", "items", "ratings"])
train_full = pd.concat([train, val])         # para evaluar en test reentrenamos con train + val
print({k: len(v) for k, v in data.items()}, "· usuarios en test:", test.user_id.nunique())
''')

# ---------------------------------------------------------------------------
M(r"""
---
## 1. 💡 Intuición: la evaluación offline es una simulación del futuro

No podemos preguntar a los usuarios de mañana. Lo que hacemos es **esconder el futuro** que ya conocemos (el test del split temporal), pedirle al modelo una lista top-K para cada usuario con lo que sabía antes del corte, y contar cuántas de sus elecciones "futuras" acertó y **en qué posición**.

Es como el *backtesting* de un modelo de trading: útil, imprescindible, pero con dos trampas — (1) el futuro que escondes fue generado por **otro sistema** (el que estaba en producción), y (2) lo que mides no es exactamente lo que el negocio quiere.
""")

C(r'''
def caja(ax, x, y, w, h, t, c, fs=9):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                 boxstyle="round,pad=0.02,rounding_size=0.08", fc=c, ec="none"))
    ax.text(x, y, t, ha="center", va="center", color="white", fontsize=fs)

fig, ax = plt.subplots(figsize=(13, 2.8)); ax.set_xlim(0, 13); ax.set_ylim(0, 2.6); ax.axis("off")
pasos = [("Log de\ninteracciones", PALETA[5]), ("Split temporal\ntrain | val | test", PALETA[1]),
         ("Entrenar con train\n(ajustar en val)", PALETA[1]), ("Top-K por usuario\nde test (sin vistos)", PALETA[2]),
         ("Métricas por\nusuario", PALETA[3]), ("Media + IC 95 %\n+ test pareado", PALETA[4])]
for k, (t, c) in enumerate(pasos):
    caja(ax, 1.1 + k * 2.15, 1.5, 1.85, 1.0, t, c)
    if k:
        ax.annotate("", xy=(0.17 + k * 2.15, 1.5), xytext=(-0.12 + k * 2.15, 1.5),
                    arrowprops=dict(arrowstyle="-|>", color="#555"))
ax.text(6.5, 0.3, "protocolo = split + candidatos + métricas + agregación + test estadístico  ·  cambiar cualquiera cambia la conclusión",
        ha="center", fontsize=9, color="#555")
ax.set_title("El protocolo de evaluación offline", fontsize=12); plt.show()
''')

# ---------------------------------------------------------------------------
M(r"""
---
## 2. ¿Por qué no basta con RMSE?

En el Netflix Prize se optimizaba el **RMSE** sobre ratings observados:

$$\text{RMSE} = \sqrt{\frac{1}{|\mathcal{T}|}\sum_{(u,i)\in\mathcal{T}} (r_{ui} - \hat r_{ui})^2}, \qquad \text{MAE} = \frac{1}{|\mathcal{T}|}\sum_{(u,i)\in\mathcal{T}} |r_{ui} - \hat r_{ui}|$$

Tres problemas cuando el producto es una **lista**:
1. Solo se evalúa sobre lo que el usuario **eligió ver** (MNAR, módulo 01): nunca penaliza recomendar algo que no habría visto jamás.
2. Pesa igual un error en una película que estaría en la posición 3.000 que en la posición 1.
3. Equivocarse de 4,9 a 4,1 en tu favorita cuenta lo mismo que de 1,9 a 1,1 en una que nunca verás.

Cremonesi, Koren & Turrin (2010) lo demostraron: algoritmos con mejor RMSE no eran mejores en top-N, y un simple *top popular* era competitivo. Netflix contó después que no llevó a producción el ensemble ganador completo: la ganancia no justificaba el coste de ingeniería (Amatriain & Basilico, 2012).

### 🧪 Experimento: buen RMSE, mal top-10
Un **modelo de sesgos** clásico predice $\hat r_{ui} = \mu + b_u + b_i$ con sesgos regularizados ($b_i = \frac{\sum_u (r_{ui} - \mu - b_u)}{\lambda + n_i}$). Comparémoslo con predecir la media global en RMSE… y luego usémoslo para recomendar.
""")

C(r'''
# Ratings EXPLÍCITOS con el mismo corte temporal (sin filtrar por >= 4)
exp_tr, _, exp_te = cd.temporal_split(cd.dedup_interactions(ratings), val_frac=0.0, test_frac=0.2)

def ajustar_sesgos(df, lam_u=5.0, lam_i=10.0, iters=5):
    mu = df.rating.mean(); bu = pd.Series(0.0, index=df.user_id.unique()); bi = pd.Series(0.0, index=df.item_id.unique())
    for _ in range(iters):     # mínimos cuadrados alternos sobre los sesgos
        r = df.rating - mu - df.user_id.map(bu).values
        bi = r.groupby(df.item_id).sum() / (lam_i + df.groupby("item_id").size())
        r = df.rating - mu - df.item_id.map(bi).values
        bu = r.groupby(df.user_id).sum() / (lam_u + df.groupby("user_id").size())
    return mu, bu, bi

mu, bu, bi = ajustar_sesgos(exp_tr)
pred = mu + exp_te.user_id.map(bu).fillna(0).values + exp_te.item_id.map(bi).fillna(0).values
rmse_media = np.sqrt(np.mean((exp_te.rating - mu) ** 2))
rmse_sesgos = np.sqrt(np.mean((exp_te.rating - np.clip(pred, 1, 5)) ** 2))
print(f"RMSE media global: {rmse_media:.4f}   ·   RMSE modelo de sesgos: {rmse_sesgos:.4f}")
''')

C(r'''
def recall_simple(recs, test, k=K):
    rel = test.groupby("user_id").item_id.agg(set)
    return np.mean([len(r & set(recs.get(u, [])[:k])) / len(r) for u, r in rel.items()])

pos_tr, pos_te = exp_tr[exp_tr.rating >= 4], exp_te[exp_te.rating >= 4]
pos_te = pos_te[pos_te.user_id.isin(exp_tr.user_id) & pos_te.item_id.isin(exp_tr.item_id)]
vistos = exp_tr.groupby("user_id").item_id.agg(set)
orden_sesgos = bi.sort_values(ascending=False).index.to_numpy()   # para un usuario fijo, ordenar por mu+b_u+b_i = ordenar por b_i
orden_pop = exp_tr.item_id.value_counts().index.to_numpy()
top = lambda orden, u: [i for i in orden[: K + len(vistos.get(u, ()))] if i not in vistos.get(u, set())][:K]
us = pos_te.user_id.unique()
r_sesgos = recall_simple({u: top(orden_sesgos, u) for u in us}, pos_te)
r_pop = recall_simple({u: top(orden_pop, u) for u in us}, pos_te)

fig, axes = plt.subplots(1, 2, figsize=(11, 3.3))
axes[0].bar(["media global", "modelo de sesgos"], [rmse_media, rmse_sesgos], color=PALETA[:2])
axes[0].set(title="RMSE (más bajo = mejor)", ylim=(min(rmse_media, rmse_sesgos) * 0.9, max(rmse_media, rmse_sesgos) * 1.02))
axes[1].bar(["popularidad", "modelo de sesgos"], [r_pop, r_sesgos], color=[PALETA[2], PALETA[1]])
axes[1].set(title=f"Recall@{K} sobre positivos de test (más alto = mejor)")
plt.tight_layout(); plt.show()
''')

M(r"""
El modelo de sesgos **gana en RMSE** y **pierde en top-10** contra la popularidad, que ni siquiera predice ratings. Ordenar por "nota esperada" sube películas excelentes pero minoritarias; la popularidad captura algo que el RMSE ignora: **la probabilidad de que lo vayas a ver**. A partir de aquí, evaluaremos **listas**.
""")

# ---------------------------------------------------------------------------
M(r"""
---
## 3. 📐 Métricas de ranking (top-K)

Notación: para un usuario $u$, $L_u = (i_1, \dots, i_K)$ es su lista recomendada y $\mathcal{R}_u$ el conjunto de ítems relevantes (sus positivos de test). $\text{rel}_u(p) = \mathbb{1}[i_p \in \mathcal{R}_u]$. Todas se calculan **por usuario** y se promedian sobre los usuarios de test.

| Métrica | Fórmula | Qué mide | Sensible a la posición |
|---|---|---|---|
| Precision@K | $\frac{1}{K}\sum_{p=1}^{K}\text{rel}_u(p)$ | qué fracción de la lista acierta | no |
| Recall@K | $\frac{1}{\lvert\mathcal{R}_u\rvert}\sum_{p=1}^{K}\text{rel}_u(p)$ | qué fracción de lo relevante recupero | no |
| HitRate@K | $\mathbb{1}\left[\sum_{p\le K}\text{rel}_u(p) > 0\right]$ | ¿al menos un acierto? | no |
| MRR@K | $\frac{1}{p^\*}$, $p^\*$ = posición del primer acierto (0 si no hay) | lo arriba que está el primer acierto | sí (solo el primero) |
| AP@K | $\frac{1}{\lvert\mathcal{R}_u\rvert}\sum_{p=1}^{K}\text{Prec@}p \cdot \text{rel}_u(p)$ | precisión media en cada acierto | sí |
| NDCG@K | $\frac{\text{DCG@}K}{\text{IDCG@}K}$ | ganancia descontada por posición, normalizada | sí |

**MAP** es la media de AP sobre usuarios. Ojo con el denominador de AP: ranx/trec_eval usan $|\mathcal{R}_u|$; otras librerías usan $\min(K, |\mathcal{R}_u|)$. **Comprueba siempre cuál usa un paper.**

### Derivación de NDCG
Järvelin & Kekäläinen (2002) querían una métrica que (1) admitiera relevancia **graduada** y (2) premiara poner lo relevante **arriba**, porque el usuario recorre la lista de arriba abajo y cada vez es menos probable que siga. Suman la ganancia de cada posición **descontada** por un factor que decrece lentamente:

$$\text{DCG@}K = \sum_{p=1}^{K} \frac{g(\text{rel}_u(p))}{\log_2(p+1)}, \qquad g(r) = r \;\;\text{(lineal)} \quad\text{o}\quad g(r) = 2^{r}-1 \;\;\text{(exponencial, Burges et al. 2005)}$$

¿Por qué $\log_2(p+1)$? Es un descuento **suave**: la posición 1 vale 1, la 3 vale 0,5, la 7 vale 0,33 — modela que el usuario mira varias posiciones, no solo la primera (MRR) ni todas por igual (Recall). El DCG no es comparable entre usuarios (depende de $|\mathcal{R}_u|$), así que se normaliza por el DCG de la **lista ideal** (todos los relevantes arriba, ordenados por relevancia):

$$\text{IDCG@}K = \sum_{p=1}^{\min(K, |\mathcal{R}_u|)} \frac{g(\text{rel}^{\downarrow}_{(p)})}{\log_2(p+1)} \quad\Rightarrow\quad \text{NDCG@}K \in [0, 1]$$

Con relevancia binaria, ambas ganancias coinciden.

### AUC y GAUC
La **AUC** de un usuario es la probabilidad de que un positivo puntúe más que un negativo: $\text{AUC}_u = \frac{1}{|\mathcal{R}_u||\mathcal{N}_u|}\sum_{i\in\mathcal{R}_u}\sum_{j\in\mathcal{N}_u}\mathbb{1}[s_{ui} > s_{uj}]$. Mide **todo** el orden por igual (la posición 1 y la 3.000 pesan lo mismo), por eso es poco útil para top-K. En ranking de anuncios/CTR se usa la **GAUC** (Zhou et al., 2018, DIN de Alibaba): la AUC por usuario ponderada por nº de impresiones, porque la AUC global mezcla usuarios con tasas de clic muy distintas.
""")

C(r'''
# Ejemplo visual: una lista de 10 con 3 relevantes (de 4 que tiene el usuario)
lista = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
relevantes = {"B", "E", "F", "Z"}           # Z es relevante pero no está en la lista
rel = np.array([i in relevantes for i in lista], int)
desc = 1 / np.log2(np.arange(2, 12))
fig, axes = plt.subplots(1, 2, figsize=(13, 3.0), gridspec_kw={"width_ratios": [1.4, 1]})
for p, (i, r) in enumerate(zip(lista, rel)):
    axes[0].add_patch(plt.Rectangle((p, 0), 0.9, 0.9, color=PALETA[3] if r else "#DDDDDD"))
    axes[0].text(p + 0.45, 0.45, i, ha="center", va="center", fontsize=12)
    axes[0].text(p + 0.45, -0.3, f"{desc[p]:.2f}", ha="center", fontsize=8, color="#555")
axes[0].text(-0.2, -0.3, "descuento\n1/log2(p+1)", ha="right", fontsize=8, color="#555")
axes[0].set_xlim(-1.6, 10); axes[0].set_ylim(-0.7, 1.1); axes[0].axis("off")
axes[0].set_title("Lista top-10 (verde = relevante). El usuario tiene 4 relevantes: B, E, F, Z")
dcg = (rel * desc).sum(); idcg = desc[:4].sum()
ap = sum(rel[:p + 1].sum() / (p + 1) for p in range(10) if rel[p]) / 4
vals = {"P@10": rel.sum() / 10, "R@10": rel.sum() / 4, "HR@10": 1.0, "MRR": 1 / (np.argmax(rel) + 1),
        "AP@10": ap, "NDCG@10": dcg / idcg}
axes[1].barh(list(vals)[::-1], list(vals.values())[::-1], color=PALETA[1])
for y, v in enumerate(list(vals.values())[::-1]):
    axes[1].text(v + 0.01, y, f"{v:.3f}", va="center", fontsize=9)
axes[1].set_xlim(0, 1.1); axes[1].set_title("Las 6 métricas de esta lista")
plt.tight_layout(); plt.show()
''')

# ---------------------------------------------------------------------------
M(r"""
---
## 4. Implementación desde cero

Funciones por usuario (lista recomendada `rec`, conjunto `rel`) y un agregador que promedia sobre **todos** los usuarios de test — un usuario sin recomendaciones cuenta como 0, nunca se "olvida" (olvidarlo es una forma clásica de inflar métricas).
""")

C(r'''
def precision_at_k(rec, rel, k):  return sum(i in rel for i in rec[:k]) / k
def recall_at_k(rec, rel, k):     return sum(i in rel for i in rec[:k]) / len(rel) if rel else 0.0
def hit_rate_at_k(rec, rel, k):   return float(any(i in rel for i in rec[:k]))

def mrr_at_k(rec, rel, k):
    for p, i in enumerate(rec[:k], 1):
        if i in rel:
            return 1.0 / p
    return 0.0

def ap_at_k(rec, rel, k):
    hits, s = 0, 0.0
    for p, i in enumerate(rec[:k], 1):
        if i in rel:
            hits += 1; s += hits / p
    return s / len(rel) if rel else 0.0

def ndcg_at_k(rec, rel, k):
    dcg = sum(1 / np.log2(p + 1) for p, i in enumerate(rec[:k], 1) if i in rel)
    idcg = sum(1 / np.log2(p + 1) for p in range(1, min(k, len(rel)) + 1))
    return dcg / idcg if idcg else 0.0

METRICAS = {"precision": precision_at_k, "recall": recall_at_k, "hit_rate": hit_rate_at_k,
            "mrr": mrr_at_k, "map": ap_at_k, "ndcg": ndcg_at_k}

def evaluar_por_usuario(recs: dict, test: pd.DataFrame, k: int = K) -> pd.DataFrame:
    rel = test.groupby("user_id").item_id.agg(set)
    filas = {u: {f"{m}@{k}": f(list(recs.get(u, [])), r, k) for m, f in METRICAS.items()} for u, r in rel.items()}
    return pd.DataFrame.from_dict(filas, orient="index")

print({m: round(f(lista, relevantes, 10), 4) for m, f in METRICAS.items()})
''')

M(r"""
### Modelos a evaluar
Usaremos cuatro recomendadores sobre el split temporal de CineMatch: **aleatorio**, **popularidad**, **popularidad reciente** (módulo 01) y un **item-kNN por co-ocurrencia** muy simple — la puntuación de un ítem es la suma de sus similitudes coseno con lo que el usuario ya vio. Lo estudiarás a fondo en el módulo 04; aquí es solo "un modelo personalizado razonable".

Para poder evaluar también *sampled metrics* y AUC, cada modelo expone una función `scores(u) → vector sobre todo el catálogo`.
""")

C(r'''
X, u2i, i2i = cd.to_csr(train_full)
idx2item = np.array(sorted(i2i, key=i2i.get))
n_items = len(idx2item)
Xb = (X > 0).astype(np.float32)
co = (Xb.T @ Xb).toarray()
n = np.diag(co).copy()
S = co / (np.sqrt(np.outer(n, n)) + 1e-9); np.fill_diagonal(S, 0)       # coseno ítem-ítem
pop = np.asarray(Xb.sum(0)).ravel()
t_max = train_full.timestamp.max()
rec_df = train_full[train_full.timestamp >= t_max - 30 * 86_400]
pop_rec = np.bincount(rec_df.item_id.map(i2i), minlength=n_items) + 1e-3 * pop   # desempate por global

MODELOS = {
    "Aleatorio": lambda u: rng.random(n_items),
    "Popularidad": lambda u: pop.astype(float),
    "Popularidad 30 d": lambda u: pop_rec.astype(float),
    "Item-kNN": lambda u: np.asarray(Xb[u2i[u]] @ S).ravel(),
}

def top_k(score_fn, users, k=K):
    out = {}
    for u in users:
        s = score_fn(u).copy()
        s[Xb[u2i[u]].indices] = -np.inf                                   # excluir lo ya visto
        idx = np.argpartition(-s, k)[:k]
        out[u] = idx2item[idx[np.argsort(-s[idx])]].tolist()
    return out

usuarios_test = test.user_id.unique()
recs = {m: top_k(f, usuarios_test, 100) for m, f in MODELOS.items()}      # top-100 para curvas @K
por_usuario = {m: evaluar_por_usuario(r, test, K) for m, r in recs.items()}
tabla = pd.DataFrame({m: d.mean() for m, d in por_usuario.items()}).T
tabla.round(4)
''')

# ---------------------------------------------------------------------------
M(r"""
---
## 5. Verificación contra una librería de industria: `ranx`

[`ranx`](https://github.com/AmenRa/ranx) (Bassani, ECIR 2022) es una librería de evaluación de ranking muy rápida (Numba) que replica las definiciones de `trec_eval`. Convertimos `recs` a su formato (`Qrels` = relevantes, `Run` = puntuaciones) y comparamos. **Nunca confíes en tu implementación de métricas hasta verificarla contra una de referencia.**
""")

C(r'''
from ranx import Qrels, Run, compare
from ranx import evaluate as rx_evaluate

def a_ranx(recs: dict, test: pd.DataFrame, nombre="run", k=K):
    qrels = Qrels({str(u): {str(i): 1 for i in g} for u, g in test.groupby("user_id").item_id})
    run = Run({str(u): ({str(i): float(k - p) for p, i in enumerate(recs.get(u, [])[:k])} or {"__vacio__": 0.0})
               for u in test.user_id.unique()}, name=nombre)
    return qrels, run

nombres_rx = {"precision": "precision", "recall": "recall", "hit_rate": "hit_rate", "mrr": "mrr",
              "map": "map", "ndcg": "ndcg"}
t0 = time.time()
for m, r in recs.items():
    q, run = a_ranx(r, test, m)
    ref = rx_evaluate(q, run, [f"{v}@{K}" for v in nombres_rx.values()])
    nuestro = tabla.loc[m]
    dif = max(abs(nuestro[f"{k_}@{K}"] - ref[f"{v}@{K}"]) for k_, v in nombres_rx.items())
    print(f"{m:18s} máx |nuestro - ranx| = {dif:.2e}")
    assert dif < 1e-9
print(f"✔ todas las métricas coinciden con ranx ({time.time() - t0:.1f} s, la 1.ª vez Numba compila)")
''')

M(r"""
Otras librerías que verás en papers y equipos:

| Librería | Qué es | Cuándo usarla |
|---|---|---|
| **ranx** | evaluación de rankings + tests estadísticos + fusión | verificar métricas, comparar runs con significancia |
| **RecBole** | framework con +90 modelos y protocolos configurables | benchmarks amplios en investigación |
| **Elliot** | framework de evaluación reproducible (config YAML) | experimentos completos y reproducibles |
| **Microsoft Recommenders** | notebooks y utilidades de buenas prácticas | referencia de implementaciones y métricas |
| **RecPack** | toolkit de experimentación (scenarios, métricas) | splits y pipelines de evaluación |

Aun así, en este curso usaremos **tu** evaluador (`cinematch_eval.py`, que construirás en el proyecto) para entender cada número.
""")

# ---------------------------------------------------------------------------
M(r"""
---
## 6. 🧪 Experimentos

### 6.1 Comparación de modelos y curvas @K
""")

C(r'''
fig, axes = plt.subplots(1, 3, figsize=(15, 3.6))
tabla[[f"recall@{K}", f"ndcg@{K}", f"hit_rate@{K}"]].plot.bar(ax=axes[0], rot=15, color=PALETA[1:4])
axes[0].set(title=f"Métricas @{K} en test (split temporal)")
ks = [1, 2, 5, 10, 20, 50, 100]
for c, (m, r) in zip(PALETA, recs.items()):
    axes[1].plot(ks, [evaluar_por_usuario(r, test, k)[f"recall@{k}"].mean() for k in ks], marker="o", color=c, label=m)
    axes[2].plot(ks, [evaluar_por_usuario(r, test, k)[f"ndcg@{k}"].mean() for k in ks], marker="o", color=c, label=m)
axes[1].set(xscale="log", title="Recall@K", xlabel="K"); axes[2].set(xscale="log", title="NDCG@K", xlabel="K")
axes[1].legend(fontsize=8); plt.tight_layout(); plt.show()
''')

M(r"""
Lee el gráfico como un practicante: (1) ¿cuánto separa cada modelo del aleatorio? (2) ¿el orden entre modelos se mantiene para todo $K$? Si las curvas se cruzan, "el mejor modelo" depende del $K$ del producto (una fila de 10 carátulas no es una lista de 100 candidatos para el ranker).

### 6.2 Beyond-accuracy: cobertura, concentración, novedad y diversidad

- **Cobertura de catálogo**: $\frac{|\bigcup_u L_u|}{|\mathcal{I}|}$ — ¿qué fracción del catálogo llega a enseñarse?
- **Gini de exposición**: Gini de cuántas veces aparece cada ítem en las listas (0 = reparto uniforme).
- **Novedad**: autoinformación media $-\log_2 p(i)$, con $p(i)$ = fracción de usuarios que vieron $i$ (Zhou et al., 2010).
- **Diversidad intra-lista (ILD)**: media de $1 - \cos(\mathbf{g}_i, \mathbf{g}_j)$ entre pares de la lista (aquí, vectores de género).
- **Serendipia**: aciertos *inesperados* — p. ej. relevantes que **no** recomendaría la popularidad. **Calibración** (Steck, 2018): que la mezcla de géneros de la lista refleje la del historial. Ambas las desarrollarás en el módulo 13.
""")

C(r'''
G = items.set_index("item_id").genres.str.get_dummies(sep="|").astype(float)
Gn = G.div(np.linalg.norm(G.values, axis=1).clip(1e-12), axis=0)
p_item = train_full.groupby("item_id").user_id.nunique() / train_full.user_id.nunique()
top_pop = set(idx2item[np.argsort(-pop)[:K]])

def beyond(recs_m, k=K):
    listas = [r[:k] for r in recs_m.values()]
    cnt = pd.Series([i for l in listas for i in l]).value_counts()
    expo = np.sort(cnt.reindex(idx2item, fill_value=0).values.astype(float))
    gini = (2 * np.arange(1, len(expo) + 1) - len(expo) - 1) @ expo / (len(expo) * expo.sum())
    ild = np.mean([1 - (lambda V: (V @ V.T).sum() - len(l))(Gn.loc[l].values) / (len(l) * (len(l) - 1)) for l in listas])
    rel = test.groupby("user_id").item_id.agg(set)
    seren = np.mean([len((set(recs_m[u][:k]) & r) - top_pop) / k for u, r in rel.items()])
    return {"cobertura": len(cnt) / n_items, "gini": gini, "novedad": np.mean([-np.log2(p_item[i]) for l in listas for i in l]),
            "ILD": ild, "serendipia": seren}

ba = pd.DataFrame({m: beyond(r) for m, r in recs.items()}).T
fig, axes = plt.subplots(1, 2, figsize=(12, 3.6))
for c, m in zip(PALETA, ba.index):
    axes[0].scatter(ba.loc[m, "cobertura"], tabla.loc[m, f"ndcg@{K}"], s=120, color=c, label=m)
axes[0].set(xlabel="cobertura de catálogo", ylabel=f"NDCG@{K}", title="Precisión vs cobertura"); axes[0].legend(fontsize=8)
(ba[["cobertura", "gini", "ILD"]]).plot.bar(ax=axes[1], rot=15, color=PALETA[1:4], title="Métricas beyond-accuracy")
plt.tight_layout(); plt.show()
ba.round(3)
''')

M(r"""
El aleatorio tiene cobertura y novedad máximas y precisión nula; la popularidad, al revés. **Ninguna métrica sola es suficiente**: los equipos de producto fijan una métrica principal (NDCG, recall) y varias *guardrail* (cobertura, diversidad, novedad) que no pueden empeorar.

### 6.3 Incertidumbre: intervalos de confianza y tests pareados
Una media sobre unos cientos de usuarios tiene **mucho ruido**. Dos herramientas:

- **Bootstrap** (Efron): remuestrea usuarios con reemplazo $B$ veces, recalcula la media, y toma los percentiles 2,5 % y 97,5 % → IC 95 %.
- **Test pareado**: los dos modelos se evalúan sobre **los mismos usuarios**, así que compara las diferencias por usuario $d_u = m_A(u) - m_B(u)$ (t-test pareado, Wilcoxon, o bootstrap/permutación de $d_u$). Mucho más potente que comparar dos IC que se solapan.
""")

C(r'''
def bootstrap_ic(v, B=2000, seed=SEED):
    v = np.asarray(v); r = np.random.default_rng(seed)
    medias = v[r.integers(0, len(v), (B, len(v)))].mean(1)
    return v.mean(), *np.quantile(medias, [0.025, 0.975])

col = f"ndcg@{K}"
ic = pd.DataFrame({m: bootstrap_ic(d[col]) for m, d in por_usuario.items()}, index=["media", "lo", "hi"]).T
fig, axes = plt.subplots(1, 2, figsize=(12, 3.4))
axes[0].errorbar(ic.index, ic.media, yerr=[ic.media - ic.lo, ic.hi - ic.media], fmt="o", capsize=6, color=PALETA[1])
axes[0].set(title=f"{col} con IC 95 % (bootstrap sobre usuarios)", ylabel=col)
# ¿Cuántos usuarios necesito? Anchura del IC al submuestrear usuarios
d_knn = por_usuario["Item-kNN"][col].values
tam = sorted({n_ for n_ in [25, 50, 100, 200, 400] if n_ < len(d_knn)} | {len(d_knn)})
anch = [np.diff(bootstrap_ic(rng.choice(d_knn, n_, replace=False))[1:])[0] for n_ in tam]
axes[1].plot(tam, anch, marker="o", color=PALETA[4])
axes[1].set(title="Anchura del IC 95 % vs nº de usuarios de test (Item-kNN)", xlabel="usuarios", ylabel="anchura")
plt.tight_layout(); plt.show()

a, b = por_usuario["Item-kNN"][col], por_usuario["Popularidad"][col]
t = stats.ttest_rel(a, b); w = stats.wilcoxon(a, b, zero_method="zsplit")
print(f"Item-kNN − Popularidad = {np.mean(a - b):+.4f} · t-test pareado p = {t.pvalue:.3g} · Wilcoxon p = {w.pvalue:.3g}")
''')

C(r'''
# ranx también hace la comparación estadística (t-test pareado de Student, Fisher, Tukey...)
q = a_ranx(recs["Popularidad"], test)[0]
runs = [a_ranx(recs[m], test, m.replace(" ", "_"))[1] for m in ["Popularidad", "Popularidad 30 d", "Item-kNN"]]
print(compare(q, runs=runs, metrics=[f"ndcg@{K}", f"recall@{K}"], max_p=0.05, stat_test="student"))
''')

M(r"""
> ⚠️ Si comparas **muchos** modelos o métricas, corrige por comparaciones múltiples (Bonferroni, Holm) o acabarás "descubriendo" mejoras que son ruido. Y recuerda: *significativo* ≠ *importante*; con millones de usuarios todo es significativo.

### 6.4 🧠 *Sampled metrics*: por qué no debes muestrear negativos al evaluar

Durante años muchos papers (NCF, entre otros) evaluaron así: para cada usuario, coger su ítem de test + **100 negativos aleatorios**, ordenar esos 101 y medir HR@10 / NDCG@10. Es barato… y **engañoso**. Krichene & Rendle (KDD 2020, *best paper*) demostraron que las métricas muestreadas **no son consistentes** con las completas: pueden **invertir el orden** de dos modelos, y cuantos menos negativos, más se parecen todas a la AUC.

Intuición: si el ítem de test está en la posición $r$ de $N$ en el ranking completo, con $m$ negativos uniformes el número de negativos que lo superan es $\sim \text{Binomial}(m, \frac{r-1}{N-1})$. Un modelo que pone el ítem en la posición 50 de 1.600 (¡fuera del top-10 real!) casi siempre queda en el top-10 de la muestra.

Primero, con nuestros modelos en un split *leave-one-out* (el protocolo típico de esos papers):
""")

C(r'''
tr_l, te_l = cd.leave_one_out_split(cd.to_implicit(ratings))
tr_l = tr_l[tr_l.item_id.isin(idx2item)]; te_l = te_l[te_l.item_id.isin(idx2item) & te_l.user_id.isin(u2i)]
Xl, _, _ = cd.to_csr(tr_l, u2i, i2i)          # mismos índices de usuario/ítem que antes
Xl = (Xl > 0).astype(np.float32)
col_l = np.asarray(Xl.sum(0)).ravel()
co_l = (Xl.T @ Xl).toarray(); nl = np.diag(co_l).copy()
S_l = co_l / (np.sqrt(np.outer(nl, nl)) + 1e-9); np.fill_diagonal(S_l, 0)
modelos_l = {"Popularidad": lambda u: col_l.astype(float), "Item-kNN": lambda u: np.asarray(Xl[u2i[u]] @ S_l).ravel(),
             "Aleatorio": lambda u: rng.random(n_items)}

def rangos(score_fn, m_neg=100, seed=SEED):
    """Rango completo (1 = mejor) y rango entre m_neg negativos muestreados del ítem de test."""
    r = np.random.default_rng(seed); full, samp, auc = [], [], []
    for u, it in zip(te_l.user_id, te_l.item_id):
        s = score_fn(u).copy(); vis = Xl[u2i[u]].indices
        s[vis] = -np.inf; t = i2i[it]; st = s[t]
        cand = np.setdiff1d(np.arange(n_items), np.append(vis, t))
        mejores = (s[cand] > st).sum() + 0.5 * (s[cand] == st).sum()
        full.append(1 + mejores); auc.append(1 - mejores / len(cand))
        neg = r.choice(cand, m_neg, replace=False)
        samp.append(1 + (s[neg] > st).sum() + 0.5 * (s[neg] == st).sum())
    return np.array(full), np.array(samp), np.array(auc)

res_s = {}
for m, f in modelos_l.items():
    full, samp, auc = rangos(f)
    res_s[m] = {"HR@10 completo": np.mean(full <= 10), "HR@10 muestreado (100 neg.)": np.mean(samp <= 10), "AUC": auc.mean()}
res_s = pd.DataFrame(res_s).T
res_s.plot.bar(rot=0, figsize=(9, 3.4), color=PALETA[1:4], title="Leave-one-out: métrica completa vs muestreada")
plt.tight_layout(); plt.show()
res_s.round(3)
''')

M(r"""
Las métricas muestreadas son **muchísimo** más altas (incluso un modelo mediocre parece excelente) y sus diferencias se comprimen. Ahora el caso que preocupa: **¿pueden invertir el orden?** Construimos dos modelos hipotéticos sobre un catálogo de $N = 1.600$ ítems:

- **Modelo A — "francotirador"**: acierta de lleno (ítem de test en el top-5) para el 40 % de usuarios; con el resto falla por completo.
- **Modelo B — "bueno en todo, excelente en nada"**: el ítem de test siempre cae entre las posiciones 20 y 80.

En producción (top-10 real), A es mucho mejor: B no acierta nunca. Calculamos el HR@10 muestreado **exacto** (esperanza bajo la binomial) en función del nº de negativos $m$.
""")

C(r'''
N = 1600
rA = np.concatenate([rng.integers(1, 6, 400), rng.integers(N // 2, N, 600)])
rB = rng.integers(20, 81, 1000)

def hr_muestreado(rangos, m, k=10, N=N):
    # P(rango muestreado <= k) = P(Binomial(m, (r-1)/(N-1)) <= k-1)
    return stats.binom.cdf(k - 1, m, (rangos - 1) / (N - 1)).mean()

ms = [10, 20, 50, 100, 200, 500, 1000, N - 1]
fig, ax = plt.subplots(figsize=(8.5, 3.6))
ax.plot(ms, [hr_muestreado(rA, m) for m in ms], marker="o", color=PALETA[4], label="Modelo A (francotirador)")
ax.plot(ms, [hr_muestreado(rB, m) for m in ms], marker="o", color=PALETA[1], label="Modelo B (mediocre uniforme)")
ax.axhline(np.mean(rA <= 10), color=PALETA[4], ls=":", label=f"A — HR@10 completo = {np.mean(rA <= 10):.2f}")
ax.axhline(np.mean(rB <= 10), color=PALETA[1], ls=":", label=f"B — HR@10 completo = {np.mean(rB <= 10):.2f}")
ax.set(xscale="log", xlabel="nº de negativos muestreados m", ylabel="HR@10 muestreado",
       title="Sampled metrics invierten el ranking de modelos (Krichene & Rendle, 2020)")
ax.legend(fontsize=8); plt.tight_layout(); plt.show()
''')

M(r"""
Con 100 negativos (el protocolo "estándar" de muchos papers), **B gana con claridad**; con el catálogo completo, **A gana** y B vale cero. Una métrica que puede invertir la conclusión no sirve para decidir. Krichene & Rendle proponen correcciones, pero su recomendación principal es simple: **evalúa sobre el catálogo completo** (*full ranking*). Con FAISS/GPUs es barato incluso con millones de ítems.

### 6.5 El protocolo cambia la conclusión
Mismos dos modelos (popularidad vs item-kNN), dos splits distintos:
""")

C(r'''
def comparar_en_split(tr, te, k=K):
    tr = tr[tr.item_id.isin(idx2item)]
    users_tr = {u: j for j, u in enumerate(sorted(tr.user_id.unique()))}
    Xs, _, _ = cd.to_csr(tr, users_tr, i2i); Xs = (Xs > 0).astype(np.float32)
    te = te[te.user_id.isin(users_tr) & te.item_id.isin(i2i)]
    c = (Xs.T @ Xs).toarray(); d = np.diag(c).copy(); Ss = c / (np.sqrt(np.outer(d, d)) + 1e-9); np.fill_diagonal(Ss, 0)
    p_ = np.asarray(Xs.sum(0)).ravel()
    out = {}
    for nombre, fn in {"Popularidad": lambda u: p_.astype(float), "Item-kNN": lambda u: np.asarray(Xs[users_tr[u]] @ Ss).ravel()}.items():
        rs = {}
        for u in te.user_id.unique():
            s = fn(u).copy(); s[Xs[users_tr[u]].indices] = -np.inf
            idx = np.argpartition(-s, k)[:k]; rs[u] = idx2item[idx[np.argsort(-s[idx])]].tolist()
        out[nombre] = evaluar_por_usuario(rs, te, k)[f"ndcg@{k}"].mean()
    return out

pos_all = cd.to_implicit(ratings)
splits_cmp = {"Aleatorio 80/20": cd.random_split(pos_all, 0.2), "Temporal global": (train_full, test)}
cmp = pd.DataFrame({s: comparar_en_split(*v) for s, v in splits_cmp.items()}).T
cmp["mejora relativa kNN vs pop"] = cmp["Item-kNN"] / cmp["Popularidad"] - 1
cmp.round(4)
''')

M(r"""
El tamaño de la mejora (y, en algunos datasets, su signo) depende del protocolo. Ji et al. (2023) y Sun et al. (2020) documentan cómo el split, el filtrado y el muestreo de negativos cambian las conclusiones publicadas.

---
## 7. 🧠 La crisis de reproducibilidad

- **Ferrari Dacrema, Cremonesi & Jannach (RecSys 2019)** analizaron 18 algoritmos neuronales de top-N publicados en conferencias de primer nivel: **solo 7** pudieron reproducirse con esfuerzo razonable, y **6 de esos 7** eran superados a menudo por métodos simples (vecinos más cercanos o grafos) **bien ajustados**. El restante no superaba de forma consistente a un método lineal bien afinado. *Best paper* en RecSys 2019.
- **Rendle, Zhang & Koren (2019)**, *On the Difficulty of Evaluating Baselines*: una factorización matricial bien ajustada en MovieLens-10M superaba a resultados publicados durante años como estado del arte.
- **Rendle, Krichene, Zhang & Anderson (RecSys 2020)**, *Neural Collaborative Filtering vs. Matrix Factorization Revisited*: el producto escalar bien ajustado supera al MLP de NCF; aprender un producto escalar con un MLP es sorprendentemente difícil.
- **Krichene & Rendle (KDD 2020)**: las *sampled metrics* invalidan comparaciones (sección 6.4).

**Causas recurrentes**: baselines sin ajustar (hiperparámetros por defecto contra el modelo propio tuneado durante semanas), *early stopping* sobre el test, splits y filtrados distintos, métricas muestreadas, código no publicado.

### ✅ Checklist de evaluación rigurosa (la que usaremos en todo el curso)
1. Split **temporal global**; hiperparámetros elegidos en **val**; test tocado **una vez**.
2. **Full ranking** sobre todo el catálogo, excluyendo lo ya visto.
3. Baselines **ajustados con el mismo presupuesto** que tu modelo: popularidad (reciente), item-kNN, EASE (módulo 04), iALS (módulo 05).
4. Métricas a varios $K$ y al menos una *beyond-accuracy*.
5. **IC 95 %** y test pareado; corrección por comparaciones múltiples.
6. Semillas fijas, versiones de librerías y **hash del dataset** (proyecto 01) en cada resultado.
7. Publica la config completa: positivo, filtrado, split, $K$, denominador de MAP, ganancia de NDCG.
""")

M(r"""
---
## 8. 🏭 En producción: el *offline-online gap*

Una mejora offline **no garantiza** una mejora online. Motivos:
- **Sesgo de exposición**: el test offline lo generó la política antigua; un modelo distinto recomendaría cosas para las que no tienes feedback (y que el usuario podría haber amado). Offline premia **imitar** al sistema anterior.
- **Métrica ≠ objetivo**: NDCG sobre clics no es retención a 30 días ni horas de visualización.
- **Efectos de página e interacción**: la lista convive con otras filas, carátulas, búsqueda…
- **Dinámica**: novedad (los usuarios clican lo nuevo por curiosidad), *feedback loops*, estacionalidad.

Garcin et al. (RecSys 2014, swissinfo.ch) compararon el mismo conjunto de recomendadores de noticias offline y online: **recomendar lo más popular era la mejor estrategia offline y la peor online**, mientras que modelos que perfilaban al usuario en tiempo real (*context trees*) mejoraban el CTR hasta un 35 %. La evaluación offline no predecía el comportamiento con usuarios reales. Por eso los equipos maduros:
- usan la evaluación offline como **filtro** (descartar lo claramente peor, depurar) y el **A/B test** como juez (Gomez-Uribe & Hunt, 2015, describen así el proceso de Netflix);
- llevan un registro histórico de experimentos para medir **qué métrica offline correlaciona** con las métricas online de su producto;
- usan **interleaving** (Netflix, 2017) para comparar rankers online con mucho menos tráfico (módulo 15) y **off-policy evaluation** (IPS, DR) con logs de propensiones (módulo 14).

## 🧠 Secretos de la élite
1. **Nunca uses sampled metrics para decidir** (Krichene & Rendle, 2020). Si un paper las usa, sus conclusiones pueden no sobrevivir al full ranking.
2. **Tunea los baselines como si fueran tu modelo.** 6 de los 7 modelos neuronales reproducibles de Ferrari Dacrema et al. (2019) perdían contra kNN/grafos bien ajustados, y Rendle, Zhang & Koren (2019) batieron años de "estado del arte" en ML-10M con una simple MF bien tuneada. Mismo presupuesto de búsqueda de hiperparámetros (nº de pruebas, mismo val) para todos.
3. **La popularidad (reciente) en split temporal es el listón real.** Si tu modelo no la bate con un **test pareado** significativo (no "IC que no se solapan", que es demasiado conservador; ver pregunta 5), no hay mejora.
4. **Las definiciones de métricas varían entre librerías** (denominador de AP, ganancia de NDCG, cómo se tratan los usuarios sin relevantes o sin recomendaciones). Diferencias de "+3 %" entre papers pueden ser solo eso. Verifica contra `ranx`.
5. **Evalúa por segmentos**: usuarios nuevos vs veteranos, cabeza vs cola, por país/dispositivo. Una mejora media puede ocultar un empeoramiento grave en usuarios nuevos — que son los que más churn tienen.
6. **Elige el $K$ y el candidato set del producto**: una fila de la home muestra ~10 ítems en pantalla; un retrieval alimenta al ranker con ~1.000. Mide Recall@1000 para retrieval y NDCG@10 para ranking.
7. **Offline es un filtro, no un juez.** Correlaciona tus métricas offline con resultados de A/B pasados antes de confiar en ellas.
8. **Declara lo que quitas del test.** Filtrar el test a usuarios e ítems vistos en train (como hace `prepare_cinematch`) evalúa solo el caso *warm*; en producción una parte del tráfico es de usuarios nuevos y estrenos. Reporta qué fracción de interacciones de test descartas y evalúa el *cold start* aparte (módulo 03).
""")

M(r"""
## ⚠️ Errores comunes
- Promediar solo sobre usuarios con recomendaciones (o con al menos un acierto).
- No excluir los ítems vistos en train de la lista (o excluirlos del test pero no de la lista).
- Elegir hiperparámetros o hacer *early stopping* mirando el test.
- Reportar Precision@10 sin decir cuántos relevantes tiene cada usuario (con 1 relevante por usuario, P@10 ≤ 0,1).
- Comparar modelos evaluados con splits, filtrados o $K$ distintos.
- Concluir "A es mejor" con diferencias dentro del ruido (sin IC ni test pareado).
- Usar AUC global para un problema top-K (pesa igual la posición 1 que la 3.000).
""")

M(r"""
---
## 📝 Autoevaluación

**1.** Un modelo tiene mejor RMSE que otro pero peor NDCG@10. ¿Es posible? ¿Por qué?
<details><summary>Respuesta</summary>Sí. RMSE solo mide el error en ítems que el usuario eligió valorar (MNAR) y pesa igual todos los ítems; NDCG@10 mide si lo que el usuario va a consumir está arriba de una lista sobre todo el catálogo. Ordenar por rating predicho prioriza ítems "buenos" pero minoritarios (Cremonesi et al., 2010).</details>

**2.** Calcula NDCG@3 para la lista [a, b, c] si los relevantes son {b, d}.
<details><summary>Respuesta</summary>DCG = 1/log2(3) = 0,631. IDCG (2 relevantes) = 1 + 1/log2(3) = 1,631. NDCG = 0,387.</details>

**3.** ¿Por qué el descuento de NDCG es logarítmico y no 1/p?
<details><summary>Respuesta</summary>1/p (como MRR) descuenta muy rápido: casi solo importa la primera posición. El logaritmo modela que el usuario examina varias posiciones con probabilidad decreciente suave; es la elección de Järvelin & Kekäläinen (2002).</details>

**4.** ¿Qué dice el resultado de Krichene & Rendle sobre las métricas con 100 negativos muestreados?
<details><summary>Respuesta</summary>Que son inconsistentes con las métricas completas: pueden invertir el orden de dos modelos incluso en esperanza, y con pocos negativos todas tienden a la AUC (que pesa igual todo el ranking). Recomiendan evaluar con el catálogo completo o, si no queda otra, usar correcciones.</details>

**5.** Dos modelos tienen NDCG@10 de 0,081 y 0,085 con IC 95 % [0,070; 0,092] y [0,074; 0,096]. ¿Puedes concluir que no hay diferencia?
<details><summary>Respuesta</summary>No necesariamente: el solapamiento de IC marginales es un criterio conservador. Como se evalúan sobre los mismos usuarios, hay que hacer un test pareado sobre las diferencias por usuario, que suele ser mucho más potente.</details>

**6.** ¿Qué es la GAUC y por qué Alibaba la prefiere a la AUC?
<details><summary>Respuesta</summary>AUC calculada por usuario y promediada ponderando por impresiones. La AUC global compara pares de usuarios distintos (el usuario muy activo frente al poco activo) y puede mejorar sin que mejore el orden dentro de la lista de cada usuario, que es lo que importa.</details>

**7.** Enumera tres causas de la crisis de reproducibilidad.
<details><summary>Respuesta</summary>Baselines sin ajustar, protocolos de evaluación inconsistentes (splits aleatorios, sampled metrics, filtrados distintos) y falta de código/datos; también selección de hiperparámetros sobre el test.</details>

**8.** ¿Por qué una mejora offline puede no trasladarse online?
<details><summary>Respuesta</summary>Sesgo de exposición (el test lo generó otra política), desalineación métrica-objetivo de negocio, efectos de página, novedad y feedback loops. Por eso offline filtra y el A/B (o interleaving) decide.</details>
""")

M(r"""
---
## 📚 Referencias

- Järvelin & Kekäläinen (2002). *Cumulated Gain-Based Evaluation of IR Techniques*. ACM TOIS 20(4). <https://doi.org/10.1145/582415.582418>
- Burges et al. (2005). *Learning to Rank using Gradient Descent* (RankNet; ganancia $2^r-1$). ICML. <https://doi.org/10.1145/1102351.1102363>
- Cremonesi, Koren & Turrin (2010). *Performance of Recommender Algorithms on Top-N Recommendation Tasks*. RecSys. <https://doi.org/10.1145/1864708.1864721>
- Zhou et al. (2010). *Solving the apparent diversity-accuracy dilemma of recommender systems*. PNAS. <https://doi.org/10.1073/pnas.1000488107>
- Steck (2018). *Calibrated Recommendations*. RecSys. <https://doi.org/10.1145/3240323.3240372>
- Zhou et al. (2018). *Deep Interest Network for Click-Through Rate Prediction* (GAUC). KDD. <https://arxiv.org/abs/1706.06978>
- Garcin et al. (2014). *Offline and Online Evaluation of News Recommender Systems at swissinfo.ch*. RecSys. <https://doi.org/10.1145/2645710.2645745>
- Gomez-Uribe & Hunt (2015). *The Netflix Recommender System: Algorithms, Business Value, and Innovation*. ACM TMIS. <https://doi.org/10.1145/2843948>
- Ferrari Dacrema, Cremonesi & Jannach (2019). *Are We Really Making Much Progress? A Worrying Analysis of Recent Neural Recommendation Approaches*. RecSys. <https://arxiv.org/abs/1907.06902> · código: <https://github.com/MaurizioFD/RecSys2019_DeepLearning_Evaluation>
- Rendle, Zhang & Koren (2019). *On the Difficulty of Evaluating Baselines: A Study on Recommender Systems*. <https://arxiv.org/abs/1905.01395>
- Krichene & Rendle (2020). *On Sampled Metrics for Item Recommendation*. KDD (best paper). <https://research.google/pubs/on-sampled-metrics-for-item-recommendation/> · versión previa de Rendle: <https://arxiv.org/abs/1912.02263>
- Rendle, Krichene, Zhang & Anderson (2020). *Neural Collaborative Filtering vs. Matrix Factorization Revisited*. RecSys. <https://arxiv.org/abs/2005.09683>
- Sun et al. (2020). *Are We Evaluating Rigorously? Benchmarking Recommendation for Reproducible Evaluation and Fair Comparison*. RecSys. <https://doi.org/10.1145/3383313.3412489>
- Ji, Sun, Zhang & Li (2023). *A Critical Study on Data Leakage in Recommender System Offline Evaluation*. ACM TOIS. <https://arxiv.org/abs/2010.11060>
- Bassani (2022). *ranx: A Blazing-Fast Python Library for Ranking Evaluation and Comparison*. ECIR. <https://github.com/AmenRa/ranx>
- Amatriain & Basilico (2012). *Netflix Recommendations: Beyond the 5 stars (Part 1)*. Netflix Tech Blog. <https://netflixtechblog.com/netflix-recommendations-beyond-the-5-stars-part-1-55838468f429>
- Librerías: RecBole <https://recbole.io/> · Elliot <https://github.com/sisinflab/elliot> · Microsoft Recommenders <https://github.com/recommenders-team/recommenders> · RecPack <https://github.com/LienM/recpack>
""")

nb.save(LESSON)

# =============================================================================
# PROYECTO
# =============================================================================
pj = Notebook("Proyecto 02 · Librería de evaluación de CineMatch", colab_path=PROJECT)
M, C = pj.md, pj.code

M(rf"""
{pj.badge()}

# 🛠️ Proyecto 02 · `cinematch_eval`: tu propia librería de evaluación, validada contra `ranx`

| | |
|---|---|
| **Nivel** | 🟢 Básico → 🟡 Intermedio |
| **Duración estimada** | 3 h |
| **GPU** | No necesaria. ≈ 0 unidades de Colab |
| **Prerrequisitos** | Lección 02, proyecto 01 (`cinematch_data.py`) |

## 🎬 Contexto de negocio
En CineMatch ya hay tres científicos de datos probando modelos y **cada uno reporta números distintos para el mismo modelo**: uno promedia solo sobre usuarios con aciertos, otro usa 100 negativos muestreados, otro divide AP por $K$. La Head of ML te pide **la librería de evaluación oficial del equipo**: métricas exactas (verificadas contra una referencia externa), métricas *beyond-accuracy*, intervalos de confianza y tests pareados, con una interfaz única que usarán **todos los módulos siguientes del curso**:

```python
from cinematch_eval import evaluate, evaluate_per_user, bootstrap_ci, paired_bootstrap_test
res = evaluate(recs, test, k=10, train=train, items=items)
```

## 📦 Dataset
CineMatch (MovieLens-100K o 1M) con el pipeline del proyecto 01: `cinematch_data.prepare_cinematch(...)` → train / val / test temporales, positivo = rating ≥ 4.

## ✅ Entregables y rúbrica
| # | Entregable | Criterio |
|---|---|---|
| 1 | Métricas por usuario | P, R, HR, MRR, AP, NDCG (binaria y graduada, ganancia lineal y $2^r-1$) — pasan los tests unitarios |
| 2 | `evaluate_per_user` / `evaluate` | promedian sobre **todos** los usuarios de test (sin recomendaciones = 0) |
| 3 | Validación externa | diferencia máxima con `ranx` < $10^{-9}$ en todas las métricas y en 3+ "runs" distintos |
| 4 | Beyond-accuracy | cobertura, Gini, novedad, ILD, miscalibración (KL de Steck) |
| 5 | Métricas de *scoring* | RMSE, MAE, AUC (Mann-Whitney) y GAUC; AUC coincide con `sklearn` |
| 6 | Estadística | `bootstrap_ci` y `paired_bootstrap_test`; p-valor coherente con el t-test pareado |
| 7 | Informe | tabla de baselines de CineMatch con IC 95 % y test pareado **Item-kNN vs Popularidad** |
| 8 | `cinematch_eval.py` | guardado con `%%writefile`, importable, pasa todos los tests |
""")

C(r'''
!pip install -q ranx pandas pyarrow scipy scikit-learn matplotlib
''')

C(r'''
import importlib
import types

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

SEED = 42
rng = np.random.default_rng(SEED)
SCALE = "small"
SIZE = "100k" if SCALE == "small" else "1m"
K = 10
plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False})
''')

utils_cell(pj, ["cinematch_data.py"])

C(r'''
import cinematch_data as cd

data = cd.prepare_cinematch(SIZE)
train, val, test, items = data["train"], data["val"], data["test"], data["items"]
train_full = pd.concat([train, val])
print({k: len(v) for k, v in data.items()})
''')

M(r"""
### Recomendaciones a evaluar
Generamos las listas de 4 baselines (aleatorio, popularidad, popularidad 30 días, item-kNN por co-ocurrencia) con `cinematch_data` y una implementación mínima de item-kNN. **Tu trabajo es evaluarlas**, no construirlas.
""")

C(r'''
def item_knn_recs(train: pd.DataFrame, users, k: int = 100) -> dict:
    X, u2i, i2i = cd.to_csr(train); X = (X > 0).astype(np.float32)
    idx2item = np.array(sorted(i2i, key=i2i.get))
    co = (X.T @ X).toarray(); d = np.diag(co).copy()
    S = co / (np.sqrt(np.outer(d, d)) + 1e-9); np.fill_diagonal(S, 0)
    out = {}
    for u in users:
        if u not in u2i:
            continue                                   # usuario sin historial: sin recomendación (cuenta 0)
        s = np.asarray(X[u2i[u]] @ S).ravel(); s[X[u2i[u]].indices] = -np.inf
        idx = np.argpartition(-s, k)[:k]; out[u] = idx2item[idx[np.argsort(-s[idx])]].tolist()
    return out

us = test.user_id.unique()
RECS = {"Aleatorio": cd.recommend_random(train_full, us, k=100),
        "Popularidad": cd.recommend_popular(train_full, us, k=100),
        "Popularidad 30 d": cd.recommend_popular(train_full, us, k=100, window_days=30),
        "Item-kNN": item_knn_recs(train_full, us)}
{m: len(r) for m, r in RECS.items()}
''')

M(r"""
---
## Parte 1 · Métricas por usuario

### TODO 1 — Seis métricas
Firma común: `(rec: list, rel: set | dict, k: int) -> float`. Convenciones obligatorias (las de `ranx`/`trec_eval`):
- `precision_at_k` divide por $k$ aunque la lista sea más corta.
- `average_precision_at_k(rec, rel, k, denominator="rel")` divide por $|\mathcal{R}|$; con `denominator="min"` por $\min(k, |\mathcal{R}|)$.
- `ndcg_at_k(rec, rel, k, exp_gain=False)`: si `rel` es un `dict` ítem → relevancia graduada; ganancia lineal $r$ o, con `exp_gain=True`, $2^r - 1$.
""")

C(r'''
def precision_at_k(rec, rel, k):
    raise NotImplementedError  # TODO

def recall_at_k(rec, rel, k):
    raise NotImplementedError  # TODO

def hit_rate_at_k(rec, rel, k):
    raise NotImplementedError  # TODO

def mrr_at_k(rec, rel, k):
    raise NotImplementedError  # TODO

def average_precision_at_k(rec, rel, k, denominator="rel"):
    raise NotImplementedError  # TODO

def ndcg_at_k(rec, rel, k, exp_gain=False):
    raise NotImplementedError  # TODO
''')

M(r"""
### Tests unitarios (calculados a mano)
Lista `[1, 2, 3, 4, 5]`, relevantes `{2, 5, 9}`, $k=5$: P = 0,4 · R = 2/3 · HR = 1 · MRR = 0,5 · AP = (1/2 + 2/5)/3 = 0,3 · NDCG = $\frac{1/\log_2 3 + 1/\log_2 6}{1 + 1/\log_2 3 + 1/\log_2 4}$ = 0,47762. La función recibe un "espacio de nombres" con tus funciones para poder reutilizarla luego con el módulo.
""")

C(r'''
def tests_unitarios(m) -> None:
    rec, rel = [1, 2, 3, 4, 5], {2, 5, 9}
    assert np.isclose(m.precision_at_k(rec, rel, 5), 0.4)
    assert np.isclose(m.precision_at_k([2], rel, 5), 0.2), "precision divide por k"
    assert np.isclose(m.recall_at_k(rec, rel, 5), 2 / 3)
    assert m.hit_rate_at_k(rec, rel, 5) == 1.0 and m.hit_rate_at_k(rec, rel, 1) == 0.0
    assert np.isclose(m.mrr_at_k(rec, rel, 5), 0.5) and m.mrr_at_k(rec, rel, 1) == 0.0
    assert np.isclose(m.average_precision_at_k(rec, rel, 5), 0.3)
    assert np.isclose(m.average_precision_at_k([2, 5], rel, 2, "min"), 1.0)
    assert np.isclose(m.ndcg_at_k(rec, rel, 5), 0.4776237035032179)
    assert np.isclose(m.ndcg_at_k([9, 2, 5], rel, 3), 1.0), "lista ideal → NDCG = 1"
    graded = {1: 1, 3: 3, 7: 2}
    assert np.isclose(m.ndcg_at_k([1, 2, 3], graded, 3), 0.5250049893849101)
    assert np.isclose(m.ndcg_at_k([1, 2, 3], graded, 3, exp_gain=True), 0.47909091485969846)
    assert m.recall_at_k([], rel, 5) == 0.0 and m.ndcg_at_k([], rel, 5) == 0.0
    print("✔ tests unitarios superados")

tests_unitarios(types.SimpleNamespace(**globals()))
''')

M(r"""
### TODO 2 — Agregación
- `evaluate_per_user(recs, test, k, metrics, rel_col=None, exp_gain=False, ap_denominator="rel") -> DataFrame` con índice `user_id` y columnas `"ndcg@10"`, etc. **Todos** los usuarios de `test`; si `rel_col` (p. ej. `"rating"`) se pasa, NDCG usa relevancia graduada y el resto usa como relevantes los de relevancia > 0.
- `evaluate(recs, test, k, metrics, rel_col=None, train=None, items=None, **kw) -> dict` con las medias, y si se pasa `train` (e `items`) añade las métricas *beyond-accuracy* del TODO 4.
""")

C(r'''
DEFAULT_METRICS = ("precision", "recall", "hit_rate", "mrr", "map", "ndcg")

def evaluate_per_user(recs, test, k=10, metrics=DEFAULT_METRICS, rel_col=None, exp_gain=False, ap_denominator="rel"):
    raise NotImplementedError  # TODO

def evaluate(recs, test, k=10, metrics=DEFAULT_METRICS, rel_col=None, train=None, items=None, **kw):
    raise NotImplementedError  # TODO
''')

M(r"""
### TODO 3 — Validación contra `ranx`
Implementa `to_ranx(recs, test, rel_col=None) -> (Qrels, Run)` (puntuación decreciente con la posición; un usuario sin recomendaciones necesita una entrada "centinela" porque `ranx` no admite consultas vacías) y `validar_contra_ranx(m)`, que para cada run de `RECS` y para $k \in \{5, 10, 20\}$ compruebe las 6 métricas binarias **y** NDCG graduado con `rel_col="rating"` (lineal → `ndcg`, exponencial → `ndcg_burges`). Diferencia máxima < $10^{-9}$.
""")

C(r'''
from ranx import Qrels, Run, compare
from ranx import evaluate as rx_evaluate

def to_ranx(recs, test, rel_col=None):
    raise NotImplementedError  # TODO

def validar_contra_ranx(m) -> None:
    raise NotImplementedError  # TODO

validar_contra_ranx(types.SimpleNamespace(**globals()))
''')

M(r"""
---
## Parte 2 · Más allá de la precisión, *scoring* y estadística

### TODO 4 — Beyond-accuracy
- `catalog_coverage(recs, catalog, k)`, `gini_index(recs, catalog, k)` (de la **exposición**: cuántas veces aparece cada ítem del catálogo en los top-k).
- `novelty(recs, train, k)`: media de $-\log_2 p(i)$, $p(i)$ = fracción de usuarios de train que vieron $i$.
- `intra_list_diversity(recs, items, k)`: media de $1-\cos$ entre pares, con vectores multi-hot de `genres`.
- `miscalibration_kl(recs, train, items, k, alpha=0.01)`: Steck (2018). $p(g\mid u)$ = distribución de géneros del historial (cada película reparte 1 entre sus géneros), $q(g\mid u)$ = la de la lista; $\text{KL}(p \,\|\, \tilde q)$ con $\tilde q = (1-\alpha) q + \alpha p$.

### TODO 5 — Métricas de *scoring*
`rmse`, `mae`, `auc_score(labels, scores)` (Mann-Whitney con rangos promedio para empates; compárala con `sklearn.metrics.roc_auc_score`) y `gauc(df, user_col, label_col, score_col)` (AUC por usuario ponderada por nº de filas; ignora usuarios con una sola clase).

### TODO 6 — Estadística
`bootstrap_ci(values, n_boot=2000, alpha=0.05, seed=42) -> (media, lo, hi)` y `paired_bootstrap_test(a, b, n_boot=10_000, seed=42) -> dict(diff, ci_low, ci_high, p_value)` (p-valor bilateral centrando la distribución bootstrap de la diferencia en 0).
""")

C(r'''
def catalog_coverage(recs, catalog, k=10):         raise NotImplementedError  # TODO
def gini_index(recs, catalog, k=10):               raise NotImplementedError  # TODO
def novelty(recs, train, k=10):                    raise NotImplementedError  # TODO
def intra_list_diversity(recs, items, k=10):       raise NotImplementedError  # TODO
def miscalibration_kl(recs, train, items, k=10, alpha=0.01): raise NotImplementedError  # TODO

def rmse(y_true, y_pred):                          raise NotImplementedError  # TODO
def mae(y_true, y_pred):                           raise NotImplementedError  # TODO
def auc_score(labels, scores):                     raise NotImplementedError  # TODO
def gauc(df, user_col="user_id", label_col="label", score_col="score"): raise NotImplementedError  # TODO

def bootstrap_ci(values, n_boot=2000, alpha=0.05, seed=42):        raise NotImplementedError  # TODO
def paired_bootstrap_test(a, b, n_boot=10_000, seed=42):           raise NotImplementedError  # TODO
''')

C(r'''
def tests_parte2(m) -> None:
    recs = {1: [1, 2], 2: [1, 3]}
    assert np.isclose(m.catalog_coverage(recs, [1, 2, 3, 4], 2), 0.75)
    assert np.isclose(m.gini_index({1: [1], 2: [2]}, [1, 2], 1), 0.0)
    tr = pd.DataFrame({"user_id": [1, 2, 2, 3], "item_id": [1, 1, 2, 3]})
    assert np.isclose(m.novelty({9: [1]}, tr, 1), -np.log2(2 / 3))
    it = pd.DataFrame({"item_id": [1, 2, 3], "genres": ["A", "A", "B"]})
    assert np.isclose(m.intra_list_diversity({1: [1, 2]}, it, 2), 0.0)
    assert np.isclose(m.intra_list_diversity({1: [1, 3]}, it, 2), 1.0)
    assert m.miscalibration_kl({1: [1]}, pd.DataFrame({"user_id": [1], "item_id": [2]}), it, 1) < 1e-9
    from sklearn.metrics import roc_auc_score
    y = rng.integers(0, 2, 500); s = rng.normal(size=500) + y; s[:50] = np.round(s[:50])
    assert np.isclose(m.auc_score(y, s), roc_auc_score(y, s))
    df = pd.DataFrame({"user_id": [1, 1, 1, 2, 2, 3], "label": [1, 0, 0, 1, 0, 1], "score": [.9, .1, .5, .2, .8, .3]})
    assert np.isclose(m.gauc(df), (3 * 1.0 + 2 * 0.0) / 5)
    assert np.isclose(m.rmse([1, 2], [1, 4]), np.sqrt(2)) and np.isclose(m.mae([1, 2], [1, 4]), 1.0)
    v = rng.normal(0.1, 0.05, 400)
    mean, lo, hi = m.bootstrap_ci(v)
    assert lo < mean < hi and np.isclose(mean, v.mean())
    a = v + rng.normal(0.01, 0.02, 400)
    r = m.paired_bootstrap_test(a, v)
    assert r["p_value"] < 0.01 and r["ci_low"] > 0
    e = rng.normal(0, 0.02, 400); e -= e.mean()                       # diferencia media exactamente 0
    assert m.paired_bootstrap_test(v, v + e)["p_value"] > 0.5
    print("✔ tests de la parte 2 superados")

tests_parte2(types.SimpleNamespace(**globals()))
''')

M(r"""
---
## Parte 3 · Informe y empaquetado

### TODO 7 — Informe de baselines de CineMatch
Con **tus** funciones: tabla con `evaluate(..., k=10, train=train_full, items=items)` para los 4 modelos; NDCG@10 con IC 95 % (gráfico de barras de error); test pareado Item-kNN vs Popularidad (tu bootstrap y `scipy.stats.ttest_rel`) y `ranx.compare`. Conclusión en 3 frases.
""")

C(r'''
# TODO
''')

M(r"""
### TODO 8 — Guarda tu librería
Copia **todas** tus funciones (con sus imports y docstrings) en la celda de abajo, ejecútala y verifica que el módulo pasa los tres bloques de tests.
""")

C(r'''
%%writefile cinematch_eval.py
"""cinematch_eval — evaluador offline de CineMatch."""
# TODO: pega aquí tus imports y funciones
''')

C(r'''
import cinematch_eval
importlib.reload(cinematch_eval)
tests_unitarios(cinematch_eval); tests_parte2(cinematch_eval); validar_contra_ranx(cinematch_eval)
''')

M(r"""
---
## ⛔ SPOILER — Solución de referencia

Intenta resolverlo primero. La solución de referencia es el módulo canónico del curso, `cinematch_eval.py`: lo escribimos en disco por partes, lo importamos, pasamos **todos los tests** y generamos el informe.
""")

writefile_chunks(pj, "cinematch_eval.py")

C(r'''
import cinematch_eval
importlib.reload(cinematch_eval)
from cinematch_eval import *          # noqa: F401,F403  (sustituye a las funciones TODO)

tests_unitarios(cinematch_eval)
tests_parte2(cinematch_eval)
''')

C(r'''
def validar_contra_ranx(m) -> None:
    nombres = {"precision": "precision", "recall": "recall", "hit_rate": "hit_rate",
               "mrr": "mrr", "map": "map", "ndcg": "ndcg"}
    peor = 0.0
    for nombre, recs in RECS.items():
        q, run = m.to_ranx(recs, test)
        qg, rung = m.to_ranx(recs, test, rel_col="rating")
        for k in (5, 10, 20):
            ours = m.evaluate(recs, test, k)
            ref = rx_evaluate(q, run, [f"{v}@{k}" for v in nombres.values()])
            peor = max(peor, *(abs(ours[f"{a}@{k}"] - ref[f"{b}@{k}"]) for a, b in nombres.items()))
            g_lin = m.evaluate(recs, test, k, metrics=["ndcg"], rel_col="rating")[f"ndcg@{k}"]
            g_exp = m.evaluate(recs, test, k, metrics=["ndcg"], rel_col="rating", exp_gain=True)[f"ndcg@{k}"]
            ref_g = rx_evaluate(qg, rung, [f"ndcg@{k}", f"ndcg_burges@{k}"])
            peor = max(peor, abs(g_lin - ref_g[f"ndcg@{k}"]), abs(g_exp - ref_g[f"ndcg_burges@{k}"]))
    assert peor < 1e-9, f"diferencia con ranx = {peor:.2e}"
    print(f"✔ coincide con ranx en {len(RECS)} runs × 3 valores de k × 8 métricas (máx. dif. {peor:.1e})")

validar_contra_ranx(cinematch_eval)
''')

C(r'''
informe = pd.DataFrame({m: evaluate(r, test, K, train=train_full, items=items) for m, r in RECS.items()}).T
per_user = {m: evaluate_per_user(r, test, K) for m, r in RECS.items()}
ic = pd.DataFrame({m: bootstrap_ci(d[f"ndcg@{K}"]) for m, d in per_user.items()}, index=["media", "lo", "hi"]).T
fig, ax = plt.subplots(figsize=(8, 3.4))
ax.errorbar(ic.index, ic.media, yerr=[ic.media - ic.lo, ic.hi - ic.media], fmt="o", capsize=6, color="#4C72B0")
ax.set(title=f"CineMatch · NDCG@{K} en test con IC 95 % (bootstrap)", ylabel=f"NDCG@{K}")
plt.tight_layout(); plt.show()
informe.round(4)
''')

C(r'''
a, b = per_user["Item-kNN"][f"ndcg@{K}"], per_user["Popularidad"][f"ndcg@{K}"]
print("Bootstrap pareado (kNN − pop):", {k: round(v, 4) for k, v in paired_bootstrap_test(a, b).items()})
print("t-test pareado: p =", f"{stats.ttest_rel(a, b).pvalue:.3g}")
q = to_ranx(RECS["Popularidad"], test)[0]
runs = []
for m in ["Popularidad", "Popularidad 30 d", "Item-kNN"]:
    run = to_ranx(RECS[m], test)[1]; run.name = m.replace(" ", "_"); runs.append(run)
print(compare(q, runs=runs, metrics=[f"ndcg@{K}", f"recall@{K}"], max_p=0.05, stat_test="student"))
''')

M(r"""
**Conclusión de referencia** (los números exactos dependen de los datos): el item-kNN supera a la popularidad en NDCG@10 y la diferencia es (o no) significativa según el test pareado — **ese** es el dato que decide, no la comparación de medias a ojo. Además gana en cobertura y novedad, lo que lo convierte en un candidato claro para el siguiente A/B. La popularidad reciente no siempre bate a la global: depende de la dinámica del catálogo, y por eso se ajusta en validación.

Desde ahora, todos los módulos del curso evaluarán así:
```python
from cinematch_eval import evaluate, evaluate_per_user, bootstrap_ci, paired_bootstrap_test
```

---
## 🚀 Retos extra
1. **Rendimiento**: vectoriza `evaluate_per_user` con NumPy (matriz de aciertos usuarios × K) y compara tiempos con `ranx` en MovieLens-1M.
2. **Métricas por segmento**: añade `evaluate_by_segment(recs, test, segment_of)` (usuarios nuevos vs veteranos, cabeza vs cola de ítems). ¿Dónde gana el kNN a la popularidad?
3. **Sampled metrics con corrección**: implementa la evaluación con 100 negativos y la corrección de Krichene & Rendle (2020); compara con full ranking.
4. **Comparaciones múltiples**: añade corrección de Holm-Bonferroni a una función `compare_models(per_user_dict, baseline)`.
5. **Tests automáticos**: convierte `tests_unitarios` y `tests_parte2` en un fichero `test_cinematch_eval.py` para `pytest` e intégralo en un workflow de CI (GitHub Actions).
6. **Serendipia**: define e implementa una métrica de serendipia (relevante ∧ no recomendado por la popularidad) y añádela a `evaluate`.

## 🤔 Reflexión (producción / MLOps)
- ¿Cómo versionarías esta librería para que un cambio en una definición de métrica no invalide en silencio la comparación con experimentos antiguos?
- ¿Qué métricas de este informe pondrías como *guardrail* en el pipeline de reentreno (módulo 17), bloqueando el despliegue si empeoran?
- Si tu métrica offline favorita no correlaciona con los resultados de los A/B de los últimos 6 meses, ¿qué harías?
""")

pj.save(PROJECT)
