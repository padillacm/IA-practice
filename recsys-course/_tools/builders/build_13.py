"""Builder del módulo 13 · Más allá de la precisión (diversidad, calibración, fairness, Pareto, página).

Genera:
  recsys-course/13_beyond_accuracy/13_beyond_accuracy.ipynb             (lección)
  recsys-course/13_beyond_accuracy/13_proyecto_reranker_home.ipynb      (proyecto)

Ejecutar desde la raíz del repo:  python recsys-course/_tools/builders/build_13.py
"""
import sys
from pathlib import Path

sys.path.insert(0, "recsys-course/_tools")
from nbbuild import Notebook  # noqa: E402

def code_parts(book, src: str) -> None:
    """Añade `src` como varias celdas, partiendo por las marcas '#---split---' (celdas ≤ ~60 líneas)."""
    for part in src.split("\n#---split---\n"):
        book.code(part)


MOD = "13_beyond_accuracy"
OUT = Path("recsys-course") / MOD
OUT.mkdir(parents=True, exist_ok=True)
LESSON = f"recsys-course/{MOD}/{MOD}.ipynb"
PROJECT = f"recsys-course/{MOD}/13_proyecto_reranker_home.ipynb"

# ---------------------------------------------------------------------------
# Celdas de utilidades compartidas (copiadas de los módulos 01/02/08)
# ---------------------------------------------------------------------------
UTILS_DATA = r'''
# ==== Utilidades mínimas (vienen del módulo 01: datos) ====
import io, zipfile, urllib.request
from pathlib import Path

DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
ML_URLS = {
    "ml-latest-small": "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip",
    "ml-1m": "https://files.grouplens.org/datasets/movielens/ml-1m.zip",
}
ML_GENRES = ["Action", "Adventure", "Animation", "Children", "Comedy", "Crime", "Documentary",
             "Drama", "Fantasy", "Film-Noir", "Horror", "Musical", "Mystery", "Romance",
             "Sci-Fi", "Thriller", "War", "Western"]

def _download_movielens(variant: str) -> Path:
    zpath = DATA_DIR / f"{variant}.zip"
    if not zpath.exists():
        urllib.request.urlretrieve(ML_URLS[variant], zpath)
    with zipfile.ZipFile(zpath) as z:
        z.extractall(DATA_DIR)
    return DATA_DIR / variant

def make_synthetic_movielens(n_users=600, n_items=1500, seed=42):
    """Fallback sintético con la MISMA forma que MovieLens (por si no hay red)."""
    rng = np.random.default_rng(seed)
    words = {g: [f"{g[:4]}{k}" for k in range(6)] for g in ML_GENRES}
    rows_m = []
    for i in range(n_items):
        gs = list(rng.choice(ML_GENRES, size=rng.integers(1, 4), replace=False))
        year = int(rng.integers(1950, 2019))
        title = " ".join(rng.choice(words[gs[0]], 2)) + f" {i} ({year})"
        rows_m.append((i, title, "|".join(gs)))
    movies = pd.DataFrame(rows_m, columns=["item_id", "title", "genres"])
    G = np.array([[g in m.split("|") for g in ML_GENRES] for m in movies.genres], float)
    pop = rng.zipf(1.6, n_items).clip(1, 500).astype(float)
    rows_r = []
    for u in range(n_users):
        taste = rng.dirichlet(np.full(len(ML_GENRES), 0.2))
        aff = G @ taste / G.sum(1)
        p = pop ** 0.6 * np.exp(10 * aff); p /= p.sum()
        n = int(rng.integers(20, 150))
        items = rng.choice(n_items, size=n, replace=False, p=p)
        rat = np.clip(np.round(2.5 + 8 * aff[items] + rng.normal(0, .7, n)), 1, 5)
        ts = np.sort(rng.integers(9e8, 1.5e9, n))
        rows_r += list(zip([u] * n, items, rat, ts))
    ratings = pd.DataFrame(rows_r, columns=["user_id", "item_id", "rating", "timestamp"])
    return ratings, movies

#---split---
def load_movielens(variant: str = "ml-latest-small"):
    """Devuelve (ratings[user_id,item_id,rating,timestamp], movies[item_id,title,genres,year]) con ids contiguos."""
    try:
        d = _download_movielens(variant)
        if variant == "ml-1m":
            ratings = pd.read_csv(d / "ratings.dat", sep="::", engine="python",
                                  names=["user_id", "item_id", "rating", "timestamp"])
            movies = pd.read_csv(d / "movies.dat", sep="::", engine="python", encoding="latin-1",
                                 names=["item_id", "title", "genres"])
        else:
            ratings = pd.read_csv(d / "ratings.csv").rename(columns={"userId": "user_id", "movieId": "item_id"})
            movies = pd.read_csv(d / "movies.csv").rename(columns={"movieId": "item_id"})
        print(f"MovieLens {variant} descargado de GroupLens")
    except Exception as e:  # sin red / URL caída → nunca bloqueamos el notebook
        print(f"⚠️ No se pudo descargar MovieLens ({type(e).__name__}). Uso datos SINTÉTICOS con la misma forma.")
        ratings, movies = make_synthetic_movielens()
    movies = movies[movies.item_id.isin(ratings.item_id.unique())].reset_index(drop=True)
    item_map = {old: new for new, old in enumerate(movies.item_id)}
    user_map = {old: new for new, old in enumerate(sorted(ratings.user_id.unique()))}
    ratings = ratings.assign(item_id=ratings.item_id.map(item_map), user_id=ratings.user_id.map(user_map))
    movies = movies.assign(item_id=movies.item_id.map(item_map))
    movies["year"] = movies.title.str.extract(r"\((\d{4})\)\s*$")[0].astype(float)
    movies["genre_list"] = movies.genres.str.replace("Children's", "Children").str.split("|")   # ml-1m → mismo nombre
    return ratings.sort_values(["user_id", "timestamp"]).reset_index(drop=True), movies
'''

UTILS_EVAL = r'''
# ==== Utilidades mínimas (vienen de los módulos 01 y 02: split temporal + métricas) ====
def split_temporal_per_user(ratings: pd.DataFrame, test_frac: float = 0.2, min_train: int = 5):
    """Para cada usuario, el último `test_frac` de sus interacciones (por tiempo) va a test."""
    r = ratings.sort_values(["user_id", "timestamp"]).copy()
    r["rank_t"] = r.groupby("user_id").cumcount()
    r["n_u"] = r.groupby("user_id")["item_id"].transform("size")
    n_test = np.maximum(1, np.floor(r["n_u"] * test_frac)).astype(int)
    is_test = (r["rank_t"] >= r["n_u"] - n_test) & (r["n_u"] > min_train)
    return r[~is_test].drop(columns=["rank_t", "n_u"]), r[is_test].drop(columns=["rank_t", "n_u"])

def recall_at_k(recs, truth, k=10):
    return len(set(recs[:k]) & truth) / max(1, min(k, len(truth)))

def ndcg_at_k(recs, truth, k=10):
    dcg = sum(1 / np.log2(i + 2) for i, it in enumerate(recs[:k]) if it in truth)
    idcg = sum(1 / np.log2(i + 2) for i in range(min(k, len(truth))))
    return dcg / idcg if idcg > 0 else 0.0

def evaluate(recs_by_user: dict, truth_by_user: dict, k: int = 10) -> dict:
    us = [u for u in recs_by_user if u in truth_by_user and truth_by_user[u]]
    return {f"Recall@{k}": float(np.mean([recall_at_k(recs_by_user[u], truth_by_user[u], k) for u in us])),
            f"NDCG@{k}": float(np.mean([ndcg_at_k(recs_by_user[u], truth_by_user[u], k) for u in us]))}
'''

UTILS_RETR = r'''
# ==== Utilidades mínimas (vienen del módulo 08: retriever de embeddings + FAISS) ====
import scipy.sparse as sp
from sklearn.decomposition import TruncatedSVD
try:
    import faiss
except ImportError:
    faiss = None

def build_interaction_matrix(train: pd.DataFrame, n_users: int, n_items: int):
    return sp.csr_matrix((np.ones(len(train), np.float32), (train.user_id, train.item_id)),
                         shape=(n_users, n_items))

class EmbeddingRetriever:
    """Top-K por producto interno con FAISS (IndexFlatIP); fallback NumPy si no hay FAISS."""
    def __init__(self, item_emb: np.ndarray):
        self.item_emb = np.ascontiguousarray(item_emb, dtype=np.float32)
        self.index = None
        if faiss is not None:
            self.index = faiss.IndexFlatIP(self.item_emb.shape[1]); self.index.add(self.item_emb)

    def search(self, q: np.ndarray, k: int = 100, exclude=None):
        q = np.ascontiguousarray(np.atleast_2d(q), dtype=np.float32)
        extra = max((len(e) for e in exclude), default=0) if exclude is not None else 0
        kk = min(k + extra, len(self.item_emb))
        if self.index is not None:
            scores, ids = self.index.search(q, kk)
        else:
            s = q @ self.item_emb.T
            ids = np.argsort(-s, axis=1)[:, :kk]; scores = np.take_along_axis(s, ids, 1)
        out = []
        for row, (sc, ii) in enumerate(zip(scores, ids)):
            ex = exclude[row] if exclude is not None else set()
            keep = [(int(i), float(s)) for i, s in zip(ii, sc) if i >= 0 and i not in ex][:k]
            out.append(keep)
        return out

class PureSVDRecommender:
    """CF ligero (PureSVD, Cremonesi 2010) como sustituto del two-tower del módulo 08."""
    def __init__(self, X: sp.csr_matrix, dim: int = 64, seed: int = 42):
        self.X = X
        svd = TruncatedSVD(n_components=dim, random_state=seed).fit(X)
        self.item_emb = svd.components_.T.astype(np.float32)      # V  (n_items × d)
        self.retriever = EmbeddingRetriever(self.item_emb)

    def user_emb(self, users):
        return np.asarray(self.X[users] @ self.item_emb)          # u = x_u V

    def recommend(self, users, k=10, exclude_seen=True):
        users = list(users)
        excl = [set(self.X[u].indices) for u in users] if exclude_seen else None
        res = self.retriever.search(self.user_emb(users), k, excl)
        return {u: [i for i, _ in r] for u, r in zip(users, res)}
'''

PIP = r'''
!pip install -q faiss-cpu
'''

SETUP = r'''
import os, re, json, time, math, random, itertools, collections, warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
warnings.filterwarnings("ignore")

SEED = 42
random.seed(SEED); np.random.seed(SEED)
FAST_DEV_RUN = True                      # True: muestra de usuarios y menos rondas de simulación
DATASET = "ml-latest-small"              # o "ml-1m" (6.040 usuarios) con FAST_DEV_RUN=False
K = 10                                   # longitud de la lista final
N_CAND = 100                             # candidatos que llegan al re-ranker
N_EVAL_USERS = 300 if FAST_DEV_RUN else 3000
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": .3,
                     "axes.spines.top": False, "axes.spines.right": False})
print("Este módulo es 100 % CPU: no necesitas GPU.")
'''

PREP = r'''
ratings, movies = load_movielens(DATASET)
n_users, n_items = ratings.user_id.nunique(), len(movies)
train, test = split_temporal_per_user(ratings, test_frac=0.2)
X = build_interaction_matrix(train, n_users, n_items)
pop = np.asarray(X.sum(0)).ravel()
truth = test.groupby("user_id").item_id.apply(set).to_dict()
hist_by_user = train.groupby("user_id").item_id.apply(list).to_dict()

GENRES = sorted({g for gs in movies.genre_list for g in gs if g in ML_GENRES})
G = np.array([[g in gs for g in GENRES] for gs in movies.genre_list], dtype=np.float32)
G[G.sum(1) == 0, GENRES.index("Drama")] = 1                      # ítems sin género → Drama
P_gi = G / G.sum(1, keepdims=True)                                # p(g|i) uniforme entre sus géneros
G_unit = G / np.linalg.norm(G, axis=1, keepdims=True)
SIM = lambda ids: G_unit[ids] @ G_unit[ids].T                     # similitud coseno por géneros

cf = PureSVDRecommender(X, dim=64)
rng = np.random.default_rng(SEED)
eval_users = sorted(int(u) for u in rng.choice(sorted(truth), size=min(N_EVAL_USERS, len(truth)), replace=False))

def candidates(u, n=N_CAND):
    """Top-n del retriever con su puntuación de relevancia normalizada a [0, 1]."""
    ids, sc = zip(*cf.retriever.search(cf.user_emb([u]), n, [set(hist_by_user[u])])[0])
    sc = np.array(sc); sc = (sc - sc.min()) / (sc.max() - sc.min() + 1e-9)
    return np.array(ids), sc

CANDS = {u: candidates(u) for u in eval_users}
print(f"{n_users} usuarios · {n_items} películas · {len(GENRES)} géneros · {len(eval_users)} usuarios de evaluación")
'''

METRICS = r'''
def ild(ids) -> float:
    """Intra-List Diversity: distancia media (1 - coseno de géneros) entre pares de la lista."""
    ids = list(ids)
    if len(ids) < 2:
        return 0.0
    S = SIM(ids); n = len(ids)
    return float((1 - S)[np.triu_indices(n, 1)].mean())

def novelty(ids) -> float:
    """Novedad media: -log2 p(i), con p(i) = fracción de usuarios que vieron i."""
    p = (pop[list(ids)] + 1) / (n_users + 1)
    return float(np.mean(-np.log2(p)))

def genre_dist_history(u, recency=True) -> np.ndarray:
    """p(g|u) de Steck: mezcla de p(g|i) del historial (pesos crecientes con la recencia)."""
    h = hist_by_user[u]
    w = np.linspace(.5, 1., len(h)) if recency else np.ones(len(h))
    p = (w[:, None] * P_gi[h]).sum(0); return p / p.sum()

def genre_dist_list(ids) -> np.ndarray:
    q = P_gi[list(ids)].sum(0); return q / max(q.sum(), 1e-12)

def kl_calibration(p, q, alpha=0.01) -> float:
    """KL(p || q~) con q~ = (1-alpha) q + alpha p para evitar log(0) (Steck, 2018)."""
    qt = (1 - alpha) * q + alpha * p
    m = p > 0
    return float(np.sum(p[m] * np.log(p[m] / qt[m])))

def gini(x) -> float:
    """Gini de un vector de exposiciones (0 = igualdad perfecta, 1 = todo en un ítem)."""
    x = np.sort(np.asarray(x, float)); n = len(x)
    if x.sum() == 0:
        return 0.0
    return float((2 * np.arange(1, n + 1) - n - 1) @ x / (n * x.sum()))

def evaluate_lists(lists: dict, k=K) -> dict:
    us = list(lists)
    exp = np.zeros(n_items)
    for u in us:
        exp[list(lists[u][:k])] += 1
    return {"NDCG@10": np.mean([ndcg_at_k(list(lists[u]), truth[u], k) for u in us]),
            "ILD@10": np.mean([ild(lists[u][:k]) for u in us]),
            "Novedad": np.mean([novelty(lists[u][:k]) for u in us]),
            "KL calibración": np.mean([kl_calibration(genre_dist_history(u), genre_dist_list(lists[u][:k])) for u in us]),
            "Cobertura": float((exp > 0).mean()), "Gini exposición": gini(exp)}

NOV = (lambda v: (v - v.min()) / (v.max() - v.min() + 1e-9))(-np.log2((pop + 1) / (n_users + 1)))   # novedad ∈ [0,1]

baseline = {u: list(CANDS[u][0][:K]) for u in eval_users}
res_base = evaluate_lists(baseline)
pd.Series(res_base, name="Baseline CF top-10").round(4)
'''

MMR = r'''
def mmr(ids, rel, k=K, lam=0.7, sim_fn=SIM):
    """Maximal Marginal Relevance (Carbonell & Goldstein, 1998), greedy O(k·N)."""
    ids, rel = np.asarray(ids), np.asarray(rel)
    S = sim_fn(ids)
    chosen, max_sim = [], np.full(len(ids), -np.inf)
    avail = np.ones(len(ids), bool)
    for _ in range(min(k, len(ids))):
        score = lam * rel - (1 - lam) * np.where(np.isinf(max_sim), 0, max_sim)
        score[~avail] = -np.inf
        j = int(np.argmax(score)); chosen.append(j); avail[j] = False
        max_sim = np.maximum(max_sim, S[j])
    return list(ids[chosen])
'''

DPP = r'''
def dpp_greedy_fast(L: np.ndarray, k: int, eps: float = 1e-10) -> list:
    """Greedy MAP para DPP con Cholesky incremental (Chen, Zhang & Zhou, NeurIPS 2018). O(N k^2)."""
    N = L.shape[0]
    c = np.zeros((k, N))                      # filas = vectores de Cholesky acumulados
    d2 = np.diag(L).astype(float).copy()      # d_i^2 = ganancia marginal de log det
    chosen = [int(np.argmax(d2))]
    while len(chosen) < k:
        j, t = chosen[-1], len(chosen) - 1
        e = (L[j] - c[:t, j] @ c[:t]) / np.sqrt(d2[j])
        c[t] = e; d2 = d2 - e ** 2
        d2[chosen] = -np.inf
        nxt = int(np.argmax(d2))
        if d2[nxt] < eps:                     # ya no cabe más "volumen": parar
            break
        chosen.append(nxt)
    return chosen

def dpp_kernel(rel, S, theta=0.7):
    """L = Diag(q) S Diag(q) con q_i = exp(alpha·r_i), alpha = theta / (2(1-theta)) (Chen et al. 2018)."""
    a = theta / (2 * (1 - theta) + 1e-9)
    q = np.exp(a * np.asarray(rel))
    return q[:, None] * S * q[None, :]

def dpp_rerank(ids, rel, k=K, theta=0.7, sim_fn=SIM, jitter=1e-3):
    S = sim_fn(np.asarray(ids)) + jitter * np.eye(len(ids))      # jitter: S de géneros es singular
    sel = dpp_greedy_fast(dpp_kernel(rel, S, theta), k)
    rest = [j for j in np.argsort(-np.asarray(rel)) if j not in set(sel)]   # si el DPP para antes de k
    return list(np.asarray(ids)[(sel + rest)[:k]])
'''

CALIB = r'''
def kl_rows(p, Q, alpha=0.01):
    """KL(p || q~) para cada fila de Q a la vez (vectorizado)."""
    Qt = (1 - alpha) * Q + alpha * p
    m = p > 0
    return (p[m] * np.log(p[m] / Qt[:, m])).sum(1)

def calibrated_rerank(u, ids, rel, k=K, lam=0.5, alpha=0.01):
    """Steck (2018): max (1-λ)·Σ s(i) − λ·KL(p || q~(I)), greedy.

    En cada paso evaluamos TODOS los candidatos a la vez: Q[j] = distribución de géneros
    de la lista si añadimos j. Como Σ_{i∈S} s(i) es constante en el paso, basta con
    (1-λ)·s(j) − λ·KL(p || q~(S ∪ {j}))."""
    ids, rel = np.asarray(ids), np.asarray(rel)
    p = genre_dist_history(u)
    acc, chosen, avail = np.zeros(len(GENRES)), [], np.ones(len(ids), bool)
    for _ in range(min(k, len(ids))):
        Q = acc + P_gi[ids]; Q = Q / Q.sum(1, keepdims=True)
        val = (1 - lam) * rel - lam * kl_rows(p, Q, alpha)
        val[~avail] = -np.inf
        j = int(np.argmax(val)); chosen.append(j); avail[j] = False; acc += P_gi[ids[j]]
    return list(ids[chosen])
'''

COMBINED = r'''
def combined_rerank(u, ids, rel, k=K, w_div=0.0, w_cal=0.0, w_nov=0.0):
    """Greedy multi-objetivo: rel + w_div·(1 - max sim) + w_nov·novedad - w_cal·KL(p || q(S ∪ {i}))."""
    ids, rel = np.asarray(ids), np.asarray(rel)
    p, S = genre_dist_history(u), SIM(ids)
    chosen, acc = [], np.zeros(len(GENRES))
    max_sim = np.zeros(len(ids)); avail = np.ones(len(ids), bool)
    for t in range(min(k, len(ids))):
        score = rel + w_nov * NOV[ids]
        if t > 0:
            score = score + w_div * (1 - max_sim)
        if w_cal:
            Q = acc + P_gi[ids]; Q = Q / Q.sum(1, keepdims=True)
            score = score - w_cal * kl_rows(p, Q)
        score[~avail] = -np.inf
        j = int(np.argmax(score)); chosen.append(j); avail[j] = False
        acc += P_gi[ids[j]]; max_sim = np.maximum(max_sim, S[j])
    return list(ids[chosen])

def pareto_mask(P: np.ndarray) -> np.ndarray:
    """True si el punto no está dominado (todas las columnas se MAXIMIZAN)."""
    keep = np.ones(len(P), bool)
    for i in range(len(P)):
        dominated = np.all(P >= P[i], axis=1) & np.any(P > P[i], axis=1)
        keep[i] = not dominated.any()
    return keep
'''

# ===========================================================================
# LECCIÓN
# ===========================================================================
nb = Notebook("Módulo 13 · Más allá de la precisión", colab_path=LESSON, gpu=False)

nb.md(f"""
{nb.badge()}

# Módulo 13 · Más allá de la precisión: diversidad, calibración, sesgos, fairness y la página completa

**Nivel:** 🟠 Avanzado → 🔴 Experto · **Duración:** 6–7 h · **GPU:** no necesaria (todo es NumPy en CPU) · **Unidades de Colab:** ~0–1.
**Prerrequisitos:** 01 (datos, long tail), 02 (métricas, incluidas las *beyond-accuracy*), 05/08 (un recomendador que genere candidatos). Conecta con 14 (exploración) y 15 (A/B tests).
""")

nb.md("""
## 🎯 Objetivos de aprendizaje

1. **Medir** diversidad intra-lista, cobertura, Gini de exposición, novedad, serendipia y miscalibración, e interpretar sus *trade-offs* con NDCG.
2. **Implementar desde cero** MMR, DPP (greedy MAP rápido con Cholesky incremental de Chen et al. 2018 y el kernel de YouTube 2018) y la calibración de Steck (2018) con KL.
3. **Simular un feedback loop** y cuantificar cómo se concentra la exposición con el tiempo según la política (popularidad, CF, diversificación, exploración).
4. **Evaluar y corregir la fairness de exposición** de proveedores (Singh & Joachims 2018) y la equidad entre grupos de usuarios.
5. **Optimizar multi-objetivo**: barrer pesos, calcular el **frente de Pareto** y elegir un punto operativo con restricciones ε.
6. **Construir una página completa** estilo Netflix (filas × columnas) con optimización a nivel de página (deduplicación, modelo de atención) frente a filas independientes.
7. **Diseñar un motor de reglas de negocio** auditable que se aplica sin romper el aprendizaje del sistema.

### 🔁 Conexión con módulos anteriores
Este módulo reutiliza muchas piezas; comprueba que las tienes frescas:
1. Define ILD, cobertura y novedad (módulo 02). ¿Cuál de ellas es una propiedad de **una lista** y cuál del **catálogo** entero?
2. En la simulación 3 del módulo 01, ¿por qué los ítems que «ganaban» el *feedback loop* no eran los mejores?
3. En los módulos 04 (RP3β) y 07 (fusión de objetivos) ya trazaste un frente de Pareto. ¿Qué significa que un punto «domine» a otro?
4. ¿En qué etapa del embudo del módulo 00 vive todo lo de este módulo, y por qué no se resuelve dentro del ranker?

<details><summary>Respuestas</summary>
1. ILD y novedad se calculan por lista (y se promedian); la cobertura es del catálogo: cuántos ítems distintos aparecen en <b>alguna</b> lista. Por eso MMR (que sube la ILD) no arregla la cobertura del feedback loop (§7).
2. Porque tuvieron suerte al principio: recibieron exposición, clics y más exposición (<i>rich get richer</i>), aunque su atractivo real fuera casi igual al del resto.
3. Que es al menos igual de bueno en todos los objetivos y estrictamente mejor en alguno. Aquí lo formalizarás con varios objetivos a la vez (§9).
4. En el <b>re-ranking</b>: el ranker puntúa cada ítem por separado; la redundancia, la calibración o la equidad son propiedades del <b>conjunto</b> (lista, página, tiempo), que solo se ven cuando ya tienes los candidatos puntuados.
</details>
""")

nb.code(PIP)
nb.code(SETUP)

nb.md("""
## 0 · Utilidades mínimas (de los módulos 01, 02 y 08)
Descarga de MovieLens con *fallback* sintético y split temporal (módulo 01), `Recall/NDCG@K` (módulo 02) y un retriever **PureSVD + FAISS** (módulo 08) que nos da los **100 candidatos** de cada usuario. Todo este módulo trabaja en la etapa de **re-ranking**: recibimos candidatos con su relevancia y decidimos *qué lista final* mostrar.
""")
code_parts(nb, UTILS_DATA)
nb.code(UTILS_EVAL)
nb.code(UTILS_RETR)
nb.code(PREP)
nb.md("Métricas *beyond-accuracy* que usaremos en todo el módulo (las derivamos una a una en §2; amplían las del módulo 02):")
nb.code(METRICS)

# --------------------------------------------------------------- 1. Intuición
nb.md("""
## 1 · 💡 Intuición: el problema de las "10 clones"

Un ranker entrenado para precisión puntúa cada ítem **por separado**: $s(u,i)$. Si a un usuario le gustan las comedias (70 %) y los documentales (30 %), los 10 ítems con mayor $s$ suelen ser **10 comedias** — cada una es individualmente la mejor apuesta, pero la lista **como conjunto** es mala: si hoy no le apetece comedia, fallan todas. Es el mismo argumento que la diversificación de una cartera de inversión: maximizar el retorno esperado de cada activo por separado no es maximizar el de la cartera.

> 💡 La relevancia de una **lista** no es la suma de relevancias de sus ítems: hay *redundancia*. Todas las técnicas de este módulo modelan algo a nivel de conjunto (lista, página, catálogo o tiempo).

Dónde vive esto en el embudo: en el **re-ranking**, después del ranker y antes de la UI, junto con las reglas de negocio.
""")

nb.code(r'''
def draw_pipeline():
    fig, ax = plt.subplots(figsize=(12, 2.8)); ax.axis("off"); ax.set_xlim(0, 12); ax.set_ylim(0, 3)
    boxes = [("Retrieval\n10⁶ → 10³", .2, "#dbe9f6"), ("Ranking\n10³ → 10²", 2.6, "#dbe9f6"),
             ("Re-ranking de lista\nMMR · DPP · calibración\nfairness · novedad", 5.0, "#fde2b5"),
             ("Página\nfilas × columnas\ndeduplicación", 7.6, "#fde2b5"), ("Reglas de negocio\nfiltros · cuotas · pins", 10.0, "#f9c6c6")]
    for t, x, c in boxes:
        ax.add_patch(plt.Rectangle((x, .7), 1.9, 1.6, fc=c, ec="gray")); ax.text(x + .95, 1.5, t, ha="center", va="center", fontsize=8.5)
    for (_, x1, _), (_, x2, _) in zip(boxes[:-1], boxes[1:]):
        ax.annotate("", (x2, 1.5), (x1 + 1.9, 1.5), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.text(5.0, 2.55, "← este módulo →", fontsize=10, color="#c05621", weight="bold")
    ax.text(.2, .25, "Precisión ítem a ítem", fontsize=9, color="#2b6cb0"); ax.text(5.0, .25, "Objetivos de conjunto: lista, página, catálogo, tiempo", fontsize=9, color="#c05621")
    plt.show()
draw_pipeline()
''')

nb.code(r'''
# Un usuario real: distribución de géneros de su historial vs. de su top-10 por precisión
u_demo = max(eval_users, key=lambda u: kl_calibration(genre_dist_history(u), genre_dist_list(baseline[u])))
p_h, p_l = genre_dist_history(u_demo), genre_dist_list(baseline[u_demo])
order = np.argsort(-(p_h + p_l))[:10]
x = np.arange(len(order))
fig, ax = plt.subplots(figsize=(10, 3.2))
ax.bar(x - .2, p_h[order], .4, label="historial del usuario p(g|u)")
ax.bar(x + .2, p_l[order], .4, label="top-10 por precisión q(g|lista)")
ax.set_xticks(x, [GENRES[g] for g in order], rotation=30); ax.set_ylabel("proporción")
ax.set_title(f"Usuario {u_demo}: la lista 'precisa' amplifica sus géneros mayoritarios (KL={kl_calibration(p_h, p_l):.2f})")
ax.legend(); plt.tight_layout(); plt.show()
''')

# --------------------------------------------------------------- 2. Métricas
nb.md("""
## 2 · 📐 Métricas *beyond-accuracy* (desde cero)

| Métrica | Fórmula | Nivel | Qué mide |
|---|---|---|---|
| **ILD@K** (diversidad intra-lista) | $\\frac{2}{K(K-1)} \\sum_{i<j \\in L} \\big(1 - \\operatorname{sim}(i,j)\\big)$ | lista | variedad dentro de la lista |
| **Cobertura** | $\\frac{\\lvert \\bigcup_u L_u \\rvert}{\\lvert \\mathcal{I} \\rvert}$ | catálogo | qué parte del catálogo llega a mostrarse |
| **Gini de exposición** | $\\frac{\\sum_k (2k-n-1)\\, x_{(k)}}{n \\sum_k x_k}$ | catálogo | concentración de la exposición (0 igualdad, 1 monopolio) |
| **Novedad** | $\\frac{1}{K}\\sum_{i \\in L} -\\log_2 p(i)$ | lista | cuán poco conocidos son los ítems |
| **Serendipia** | $\\frac{1}{K}\\lvert \\{ i \\in L : i \\text{ relevante} \\wedge i \\notin L^{\\text{obvia}} \\}\\rvert$ | lista | aciertos que un recomendador "obvio" no habría dado |
| **Miscalibración** | $\\mathrm{KL}(p \\,\\Vert\\, \\tilde q) = \\sum_g p(g\\mid u) \\log \\frac{p(g\\mid u)}{\\tilde q(g\\mid L)}$ | lista | si la lista respeta las proporciones de gustos del usuario |

Aquí $\\operatorname{sim}$ es el coseno entre vectores de géneros (interpretable; en producción se usan embeddings), $p(i)$ la fracción de usuarios que consumieron $i$, y $x_{(k)}$ las exposiciones ordenadas de menor a mayor.

### En papel: 4 películas
""")

nb.code(r'''
toy = pd.DataFrame({"película": ["Comedia A", "Comedia B", "Comedia-Romance C", "Documental D"],
                    "Comedy": [1, 1, 1, 0], "Romance": [0, 0, 1, 0], "Documentary": [0, 0, 0, 1]})
V = toy[["Comedy", "Romance", "Documentary"]].to_numpy(float); V /= np.linalg.norm(V, axis=1, keepdims=True)
def toy_ild(idx):
    S = V[idx] @ V[idx].T; return (1 - S)[np.triu_indices(len(idx), 1)].mean()
for name, idx in [("{A, B, C}", [0, 1, 2]), ("{A, C, D}", [0, 2, 3])]:
    print(f"ILD{name} = {toy_ild(idx):.3f}")
print("cos(A,C) =", round(float(V[0] @ V[2]), 3), "→ distancia 1-cos =", round(1 - float(V[0] @ V[2]), 3))
''')

nb.code(r'''
def serendipity(lists, obvious, k=K):
    """Ge et al. (2010): aciertos que el recomendador 'obvio' (popularidad) no habría hecho."""
    return np.mean([len((set(lists[u][:k]) & truth[u]) - set(obvious[u][:k])) / k for u in lists])

pop_order = np.argsort(-pop)
obvious = {u: [int(i) for i in pop_order if i not in set(hist_by_user[u])][:K] for u in eval_users}
print(f"Serendipia baseline CF: {serendipity(baseline, obvious):.4f} · popularidad: {serendipity(obvious, obvious):.4f} (0 por definición)")
pd.DataFrame({"CF top-10": res_base, "Popularidad": evaluate_lists(obvious)}).round(4)
''')

# --------------------------------------------------------------- 3. MMR
nb.md("""
## 3 · MMR: Maximal Marginal Relevance

### 📐 Formulación (Carbonell & Goldstein, 1998)
Construimos la lista $S$ de forma *greedy*; en cada paso elegimos
$$i^* = \\arg\\max_{i \\in C \\setminus S} \\Big[\\lambda\\, \\operatorname{rel}(i) - (1-\\lambda) \\max_{j \\in S} \\operatorname{sim}(i, j)\\Big]$$
- $\\lambda = 1$: precisión pura. $\\lambda = 0$: diversidad pura.
- Coste $O(K \\cdot N)$ manteniendo $\\max_{j \\in S}\\operatorname{sim}(i,j)$ incrementalmente.
- Intuición: el bonus de un ítem es lo que **añade** a lo ya elegido (relevancia *marginal*).
""")
nb.code(MMR)

nb.code(r'''
lams = [1.0, .9, .8, .7, .6, .5, .4, .3]
mmr_curve = []
for lam in lams:
    lists = {u: mmr(*CANDS[u], k=K, lam=lam) for u in eval_users}
    mmr_curve.append({"lam": lam, **evaluate_lists(lists)})
mmr_curve = pd.DataFrame(mmr_curve)
fig, ax = plt.subplots(figsize=(6.5, 4))
ax.plot(mmr_curve["ILD@10"], mmr_curve["NDCG@10"], "o-")
for _, r in mmr_curve.iterrows():
    ax.annotate(f"λ={r.lam}", (r["ILD@10"], r["NDCG@10"]), fontsize=8, xytext=(4, 3), textcoords="offset points")
ax.set_xlabel("ILD@10 (diversidad)"); ax.set_ylabel("NDCG@10"); ax.set_title("MMR: frontera precisión–diversidad"); plt.show()
mmr_curve.round(4)
''')

nb.md("""
🧪 **Observa la forma de la curva**: los primeros pasos (λ de 1 a ~0,8) suelen ganar mucha diversidad perdiendo muy poca precisión — e incluso NDCG puede **subir**, porque una lista diversa "cubre más apuestas" sobre lo que el usuario verá en el futuro. Después el coste en precisión se dispara. Ese "codo" es donde suelen operar los sistemas reales.

## 4 · DPP: Determinantal Point Processes

### 💡 Intuición geométrica
Representa cada ítem $i$ por un vector $\\mathbf{b}_i = q_i \\mathbf{f}_i$: longitud $q_i$ = **calidad** (relevancia), dirección $\\mathbf{f}_i$ = **características** (géneros, embedding). El kernel $L = B^\\top B$ tiene $L_{ij} = q_i q_j \\operatorname{sim}(i,j)$ y
$$\\det(L_S) = \\operatorname{Vol}^2\\big(\\{\\mathbf{b}_i\\}_{i\\in S}\\big) = \\Big(\\prod_{i \\in S} q_i^2\\Big) \\det(S_S).$$
El volumen es grande si los vectores son **largos** (relevantes) y **apuntan en direcciones distintas** (diversos). Un DPP asigna $P(S) \\propto \\det(L_S)$, y la recomendación es su **MAP**: el conjunto de tamaño $K$ con mayor determinante.
""")

nb.code(r'''
fig, axes = plt.subplots(1, 3, figsize=(11, 3.3))
cases = [("Similares y relevantes", [2, .3], [1.8, .9]), ("Diversos y relevantes", [2, .3], [-.4, 1.9]),
         ("Diversos, uno poco relevante", [2, .3], [-.1, .5])]
for ax, (t, a, b) in zip(axes, cases):
    a, b = np.array(a), np.array(b)
    ax.add_patch(plt.Polygon([[0, 0], a, a + b, b], fc="#fde2b5", ec="#c05621", alpha=.8))
    for v, c in [(a, "#2b6cb0"), (b, "#2f855a")]:
        ax.annotate("", v, (0, 0), arrowprops=dict(arrowstyle="->", lw=2, color=c))
    area = abs(a[0] * b[1] - a[1] * b[0])
    ax.set_title(f"{t}\ndet = área² = {area ** 2:.2f}", fontsize=9); ax.set_xlim(-1, 4); ax.set_ylim(-.5, 3); ax.set_aspect("equal")
plt.suptitle("DPP: el determinante premia calidad (longitud) Y diversidad (ángulo)"); plt.tight_layout(); plt.show()
''')

nb.md("""
### 📐 Greedy MAP rápido (Chen, Zhang & Zhou, NeurIPS 2018)
El MAP exacto es NP-difícil; el *greedy* añade en cada paso $j = \\arg\\max_i \\log\\det(L_{S \\cup \\{i\\}}) - \\log\\det(L_S)$. Ingenuamente cada paso cuesta $O(N K^3)$. La clave de Chen et al.: mantener la **descomposición de Cholesky** $L_S = V V^\\top$ incrementalmente. Para cada candidato $i$ guardamos un vector $\\mathbf{c}_i$ y un escalar $d_i$ con
$$\\det(L_{S\\cup\\{i\\}}) = \\det(L_S)\\, d_i^2, \\qquad d_i^2 = L_{ii} - \\lVert \\mathbf{c}_i \\rVert^2 .$$
Al añadir $j$, para cada $i$:
$$e_i = \\frac{L_{ji} - \\langle \\mathbf{c}_j, \\mathbf{c}_i \\rangle}{d_j}, \\qquad \\mathbf{c}_i \\leftarrow [\\mathbf{c}_i,\\ e_i], \\qquad d_i^2 \\leftarrow d_i^2 - e_i^2 .$$
Coste total $O(N K^2)$ — milisegundos para $N=500$, $K=50$. El *trade-off* calidad/diversidad se controla con $q_i = \\exp(\\alpha\\, r_i)$, $\\alpha = \\theta / (2(1-\\theta))$, $\\theta \\in [0, 1)$.
""")
nb.code(DPP)

nb.code(r'''
def dpp_greedy_naive(L, k):
    """Greedy de referencia: recalcula log det para cada candidato en cada paso. O(N K^4)."""
    chosen = []
    for _ in range(k):
        best, best_v = None, -np.inf
        for i in range(L.shape[0]):
            if i in chosen:
                continue
            S = chosen + [i]
            sign, v = np.linalg.slogdet(L[np.ix_(S, S)])
            if sign > 0 and v > best_v:
                best, best_v = i, v
        if best is None:
            break
        chosen.append(best)
    return chosen

g = np.random.default_rng(0)
B = g.normal(size=(30, 200)); Lr = B.T @ B / 30 + 1e-3 * np.eye(200)        # kernel PSD de prueba
assert dpp_greedy_fast(Lr, 10) == dpp_greedy_naive(Lr, 10), "¡Las dos versiones deben coincidir!"
print("✅ greedy rápido == greedy ingenuo")

times = []
for N in [100, 200, 400, 800]:
    B = g.normal(size=(64, N)); Ln = B.T @ B / 64 + 1e-3 * np.eye(N)
    t0 = time.perf_counter(); dpp_greedy_fast(Ln, 20); tf = time.perf_counter() - t0
    tn = np.nan
    if N <= 200:
        t0 = time.perf_counter(); dpp_greedy_naive(Ln, 20); tn = time.perf_counter() - t0
    times.append({"N": N, "rápido (Cholesky)": tf * 1e3, "ingenuo": tn * 1e3})
times = pd.DataFrame(times).set_index("N")
ax = times.plot(marker="o", logy=True, figsize=(6, 3.4)); ax.set_ylabel("ms (K=20)"); ax.set_title("Greedy MAP DPP: coste"); plt.show()
times.round(2)
''')

nb.md("""
### El kernel de YouTube (Wilhelm et al., CIKM 2018)
En YouTube el DPP re-ordena el feed móvil con un kernel parametrizado:
$$L_{ii} = q_i^2, \\qquad L_{ij} = \\alpha\\, q_i\\, q_j\\, \\exp\\!\\Big(-\\frac{D_{ij}}{2\\sigma^2}\\Big) \\ (i \\neq j)$$
con $q_i$ la calidad predicha por el ranker y $D_{ij}$ una distancia entre ítems. $\\alpha$ y $\\sigma$ se ajustan con búsqueda en rejilla **contra métricas online** (y $L$ puede dejar de ser semidefinida positiva si $\\alpha > 1$: se proyecta recortando autovalores negativos). Para listas largas aplican el DPP sobre **ventanas** sucesivas. Reportaron mejoras en métricas de satisfacción a largo plazo, no solo de clics.
""")

nb.code(r'''
def youtube_kernel(rel, ids, a=0.8, sigma=0.5):
    D = 1 - SIM(np.asarray(ids))                              # distancia por géneros
    q = 0.1 + np.asarray(rel)                                   # calidad > 0
    L = a * np.outer(q, q) * np.exp(-D / (2 * sigma ** 2))
    np.fill_diagonal(L, q ** 2)
    w, V = np.linalg.eigh(L)                                    # proyección a PSD
    return (V * np.clip(w, 1e-6, None)) @ V.T

def dpp_youtube(ids, rel, k=K, a=0.8, sigma=0.5):
    return list(np.asarray(ids)[dpp_greedy_fast(youtube_kernel(rel, ids, a, sigma), k)])

dpp_curve = [{"metodo": "DPP (Chen θ)", "param": th, **evaluate_lists({u: dpp_rerank(*CANDS[u], theta=th) for u in eval_users})}
             for th in [.95, .9, .8, .7, .6, .5]]
dpp_curve += [{"metodo": "DPP (YouTube α)", "param": a, **evaluate_lists({u: dpp_youtube(*CANDS[u], a=a) for u in eval_users})}
              for a in [.2, .5, .8, .95]]
dpp_curve = pd.DataFrame(dpp_curve)
fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(mmr_curve["ILD@10"], mmr_curve["NDCG@10"], "o-", label="MMR (λ)")
for m, d in dpp_curve.groupby("metodo"):
    ax.plot(d["ILD@10"], d["NDCG@10"], "s-", label=m)
ax.scatter(res_base["ILD@10"], res_base["NDCG@10"], c="k", s=80, marker="*", zorder=5, label="baseline")
ax.set_xlabel("ILD@10"); ax.set_ylabel("NDCG@10"); ax.legend(); ax.set_title("MMR vs DPP: fronteras precisión–diversidad"); plt.show()
''')

nb.md("""
> 👀 **Qué debes observar:** (figura de los paralelogramos) el área crece con la **longitud** de los vectores (relevancia) y con el **ángulo** entre ellos (diversidad); dos ítems casi paralelos dan un área ≈ 0 aunque ambos sean relevantes. (coste) la versión con Cholesky escala casi linealmente en N mientras la ingenua se dispara: es lo que hace al DPP desplegable. (fronteras) cada curva es un re-ranker barriendo su parámetro; **la que queda arriba y a la derecha domina**. Si MMR y DPP se solapan en tu ejecución, MMR es más simple de operar; la ventaja del DPP suele aparecer con *embeddings* ricos y listas largas.
""")

# --------------------------------------------------------------- 5. Calibración
nb.md("""
## 5 · Calibración (Steck, RecSys 2018)

### 💡 Idea
Diversidad no es lo mismo que **respetar las proporciones**. Si has visto 70 % comedias y 30 % documentales, una lista "calibrada" tiene ~7 comedias y ~3 documentales; la lista "precisa" tiende a 10 comedias (los intereses minoritarios **desaparecen**), y una lista MMR puede meter géneros que no te interesan.

### 📐 Formulación
- Distribución del usuario: $p(g\\mid u) = \\dfrac{\\sum_{i \\in H_u} w_{u,i}\\, p(g\\mid i)}{\\sum_{i \\in H_u} w_{u,i}}$, con $p(g\\mid i)$ uniforme entre los géneros de $i$ y $w_{u,i}$ creciente con la recencia.
- Distribución de la lista: $q(g\\mid u) = \\dfrac{\\sum_{i \\in L} w_{r(i)}\\, p(g\\mid i)}{\\sum_{i \\in L} w_{r(i)}}$ (pesos por posición opcionales).
- Miscalibración: $C_{KL}(p, q) = \\mathrm{KL}(p \\Vert \\tilde q) = \\sum_g p(g\\mid u) \\log \\dfrac{p(g\\mid u)}{\\tilde q(g\\mid u)}$ con $\\tilde q = (1-\\alpha) q + \\alpha p$, $\\alpha = 0{,}01$ (evita $\\log 0$ cuando la lista omite un género).
- Re-ranking: $\\displaystyle L^* = \\arg\\max_{\\lvert L \\rvert = K} (1-\\lambda) \\sum_{i \\in L} s(u,i) - \\lambda\\, C_{KL}(p, q(L))$, resuelto *greedy*: en cada paso añadimos el ítem que más mejora el objetivo (Steck argumenta que este objetivo es submodular, de modo que el greedy tiene la garantía clásica $(1-1/e)$).
""")
nb.code(CALIB)

nb.code(r'''
cal_curve = []
for lam in [0, .2, .4, .6, .8, .95]:
    lists = {u: calibrated_rerank(u, *CANDS[u], lam=lam) for u in eval_users}
    cal_curve.append({"lam": lam, **evaluate_lists(lists)})
    if lam == .6:
        cal_lists = lists
cal_curve = pd.DataFrame(cal_curve)
fig, ax = plt.subplots(1, 2, figsize=(12, 3.8))
ax[0].plot(cal_curve["KL calibración"], cal_curve["NDCG@10"], "o-", c="#2f855a")
for _, r in cal_curve.iterrows():
    ax[0].annotate(f"λ={r.lam}", (r["KL calibración"], r["NDCG@10"]), fontsize=8, xytext=(4, 3), textcoords="offset points")
ax[0].invert_xaxis(); ax[0].set_xlabel("KL de miscalibración (→ mejor)"); ax[0].set_ylabel("NDCG@10"); ax[0].set_title("Calibración vs precisión")
p_c = genre_dist_list(cal_lists[u_demo]); x = np.arange(len(order))
for off, (lab, v) in zip([-.27, 0, .27], [("historial", p_h), ("top-10 precisión", p_l), ("top-10 calibrado (λ=0,6)", p_c)]):
    ax[1].bar(x + off, v[order], .27, label=lab)
ax[1].set_xticks(x, [GENRES[g] for g in order], rotation=30); ax[1].legend(fontsize=8); ax[1].set_title(f"Usuario {u_demo}")
plt.tight_layout(); plt.show()
cal_curve.round(4)
''')

nb.code(r'''
kl_b = [kl_calibration(genre_dist_history(u), genre_dist_list(baseline[u])) for u in eval_users]
kl_c = [kl_calibration(genre_dist_history(u), genre_dist_list(cal_lists[u])) for u in eval_users]
plt.figure(figsize=(7, 3.2))
plt.hist(kl_b, bins=30, alpha=.6, label="CF top-10"); plt.hist(kl_c, bins=30, alpha=.6, label="calibrado λ=0,6")
plt.xlabel("KL(p‖q̃) por usuario"); plt.ylabel("usuarios"); plt.title("Distribución de la miscalibración"); plt.legend(); plt.show()
''')

nb.md("""
> 👀 **Qué debes observar:** en las barras del usuario de ejemplo, la lista «precisa» infla el género dominante del historial y hace **desaparecer** los minoritarios; la calibrada recupera las proporciones. En el histograma, el re-ranking calibrado desplaza toda la distribución de KL hacia la izquierda, no solo la media: mejora sobre todo a los usuarios con gustos **mixtos**, que son los peor servidos por un top-K puro. Mira cuánto NDCG cuesta en la curva de la izquierda: la calibración suele ser barata en precisión.
""")

# --------------------------------------------------------------- 6. Novedad
nb.md("""
## 6 · Novedad, serendipia y la cola larga

La **novedad** mide lo poco conocido de lo recomendado; la **serendipia**, los aciertos *inesperados*. Un re-ranker simple añade una penalización de popularidad:
$$s'(u,i) = s(u,i) + \\beta\\, \\operatorname{nov}(i), \\qquad \\operatorname{nov}(i) \\propto -\\log_2 p(i).$$
Lo dibujamos sobre la **cola larga** y medimos qué fracción de las recomendaciones cae en la *cabeza* (el top-20 % del catálogo por popularidad).
""")

nb.code(r'''
order_pop = np.argsort(-pop)
cum = np.cumsum(pop[order_pop]) / pop.sum()
head = set(order_pop[: int(.2 * n_items)].tolist())
tail_cut = int(np.searchsorted(cum, .8))
fig, ax = plt.subplots(1, 2, figsize=(12, 3.6))
ax[0].plot(np.arange(1, n_items + 1), pop[order_pop]); ax[0].set_xscale("log"); ax[0].set_yscale("log")
ax[0].set_xlabel("ranking de popularidad del ítem"); ax[0].set_ylabel("interacciones (train)")
ax[0].set_title(f"Cola larga: el top-20 % del catálogo concentra el {cum[int(.2 * n_items)]:.0%} de interacciones")
nov_rows = []
for beta in [0, .1, .2, .4, .8]:
    lists = {u: list(CANDS[u][0][np.argsort(-(CANDS[u][1] + beta * NOV[CANDS[u][0]]))][:K]) for u in eval_users}
    rec = np.concatenate([lists[u] for u in eval_users])
    nov_rows.append({"beta": beta, **evaluate_lists(lists), "% cabeza (top-20% pop)": np.mean([i in head for i in rec])})
nov_df = pd.DataFrame(nov_rows)
ax[1].plot(nov_df["Novedad"], nov_df["NDCG@10"], "o-", c="#9467bd")
for _, r in nov_df.iterrows():
    ax[1].annotate(f"β={r.beta}  cabeza={r['% cabeza (top-20% pop)']:.0%}", (r["Novedad"], r["NDCG@10"]), fontsize=7.5, xytext=(3, 3), textcoords="offset points")
ax[1].set_xlabel("novedad media (bits)"); ax[1].set_ylabel("NDCG@10"); ax[1].set_title("Penalizar popularidad: novedad vs precisión")
plt.tight_layout(); plt.show(); nov_df.round(4)
''')

nb.md("""
> 👀 **Qué debes observar:** al subir β, la anotación «cabeza» baja (menos recomendaciones del 20 % más popular) y la novedad sube; el NDCG aguanta al principio y luego cae. Ojo con leer esto como «la novedad no compensa»: el NDCG offline **premia la popularidad** porque el test lo generó un sistema sesgado hacia ella (módulo 02, sección 8). El valor de la cola larga solo se mide bien online (módulo 15) o con OPE (módulo 14).
""")

# --------------------------------------------------------------- 7. Feedback loops
nb.md("""
## 7 · Sesgo de popularidad y *feedback loops*

### 💡 El bucle
El recomendador se entrena con lo que los usuarios **vieron**, y los usuarios ven lo que el recomendador **les mostró**. Lo popular se muestra más → recibe más clics → parece aún mejor → se muestra más. Chaney, Stewart & Engelhardt (RecSys 2018) mostraron en simulación que este *algorithmic confounding* **homogeneiza** el comportamiento de los usuarios y reduce la utilidad, y Mansoury et al. (CIKM 2020) que **amplifica el sesgo de popularidad** con cada ronda de reentrenamiento.

### 🧪 Simulación
Escenario con **re-consumo** (re-visionados, música, noticias): lo ya consumido puede volver a recomendarse y el sistema aprende de **conteos** de interacciones. Para que el bucle domine, el sistema arranca con solo el 20 % de los datos de train (como un producto joven): casi todo lo que aprende después viene de **su propio feedback**.
1. **Verdad oculta**: entrenamos un modelo con *todos* los datos y lo convertimos en probabilidad de clic $p^\\star(u,i)$ (el "mundo real" que el sistema no ve).
2. Cada ronda: la política recomienda $K$ ítems a cada usuario → clics $\\sim \\operatorname{Bernoulli}(p^\\star)$ → se suman a los conteos → se **reentrena** (PureSVD sobre $\\log(1+\\text{conteo})$).
3. Políticas: **Popularidad**, **CF (PureSVD)**, **CF + MMR** (λ = 0,7, diversidad por géneros) y **CF + exploración** (2 de 10 huecos aleatorios, enlaza con el módulo 14).
4. Medimos, **ronda a ronda**, la concentración de la exposición (cobertura del catálogo, Gini, cuota del top-1 %) y la utilidad (clics).
""")

nb.code(r'''
def make_ground_truth(dim=32, base_ctr=0.03, temp=1.0, seed=SEED):
    Xall = build_interaction_matrix(ratings, n_users, n_items)
    svd = TruncatedSVD(dim, random_state=seed).fit(Xall)
    S = (Xall @ svd.components_.T) @ svd.components_                     # n_users × n_items
    Z = (S - S.mean(1, keepdims=True)) / (S.std(1, keepdims=True) + 1e-9)
    b = np.log(base_ctr / (1 - base_ctr))
    return 1 / (1 + np.exp(-(temp * np.clip(Z, -3, 3) + b)))             # p*(u,i), colas recortadas

P_TRUE = make_ground_truth()
print(f"p* medio={P_TRUE.mean():.3f} · p* del top-10 ideal de cada usuario={np.sort(P_TRUE, 1)[:, -10:].mean():.3f}")
''')

nb.code(r'''
def recommend_round(name, C, g, k=K):
    """C: matriz de conteos observados. Devuelve recs (n_users × k)."""
    if name == "Popularidad":
        S = np.tile(np.asarray(C.sum(0)).ravel(), (n_users, 1))
    else:
        Xl = C.copy(); Xl.data = np.log1p(Xl.data)
        svd = TruncatedSVD(32, random_state=SEED).fit(Xl)
        S = np.asarray((Xl @ svd.components_.T) @ svd.components_)
    top = np.argpartition(-S, 50, axis=1)[:, :50]
    top = np.take_along_axis(top, np.argsort(-np.take_along_axis(S, top, 1), 1), 1)
    if name == "CF + MMR":
        return np.array([mmr(top[u], np.linspace(1, 0, 50), k=k, lam=.7) for u in range(n_users)])
    recs = top[:, :k].copy()
    if name == "CF + exploración":
        recs[:, -2:] = g.integers(0, n_items, size=(n_users, 2))      # 2 huecos de exploración uniforme
    return recs

def simulate_feedback_loop(name, rounds, init_frac=0.2, seed=SEED):
    g = np.random.default_rng(seed)
    C0 = X.copy().astype(np.float32); C0.data[g.random(C0.nnz) > init_frac] = 0; C0.eliminate_zeros()
    C, hist, first_exp = C0.tolil(), [], None
    for t in range(rounds):
        recs = recommend_round(name, C.tocsr(), g)
        e = np.bincount(recs.ravel(), minlength=n_items).astype(float)
        first_exp = e if first_exp is None else first_exp
        clicks = g.random(recs.shape) < P_TRUE[np.arange(n_users)[:, None], recs]
        for u, j in zip(*np.nonzero(clicks)):
            C[u, recs[u, j]] += 1
        hist.append({"ronda": t + 1, "cobertura": (e > 0).mean(), "Gini exposición": gini(e),
                     "cuota top-1%": np.sort(e)[::-1][: max(1, n_items // 100)].sum() / e.sum(),
                     "clics/usuario": clicks.sum() / n_users})
    return pd.DataFrame(hist), first_exp, e

ROUNDS = 15 if FAST_DEV_RUN else 40
loop = {name: simulate_feedback_loop(name, ROUNDS) for name in ["Popularidad", "CF (PureSVD)", "CF + MMR", "CF + exploración"]}
''')

nb.code(r'''
fig, ax = plt.subplots(2, 2, figsize=(12, 7))
colors = dict(zip(loop, ["#7f7f7f", "#4c78a8", "#f58518", "#54a24b"]))
for name, (h, e0, eT) in loop.items():
    c = colors[name]
    ax[0, 0].plot(h["ronda"], h["cobertura"], "o-", ms=3, c=c, label=name)
    ax[0, 1].plot(h["ronda"], h["Gini exposición"], "o-", ms=3, c=c, label=name)
    ax[1, 1].plot(h["ronda"], h["clics/usuario"].cumsum(), "o-", ms=3, c=c, label=name)
    if name in ("CF (PureSVD)", "CF + exploración"):
        for e, ls, tag in [(e0, ":", "ronda 1"), (eT, "-", f"ronda {ROUNDS}")]:
            ax[1, 0].plot(np.linspace(0, 1, n_items), np.cumsum(np.sort(e)) / e.sum(), ls=ls, c=c, label=f"{name} · {tag}")
ax[1, 0].plot([0, 1], [0, 1], "k--", lw=.8, label="igualdad perfecta")
ax[0, 0].set_title("Cobertura del catálogo en cada ronda"); ax[0, 1].set_title("Gini de la exposición en cada ronda")
ax[1, 0].set_title("Curvas de Lorenz de la exposición"); ax[1, 0].set_xlabel("fracción de ítems (de menos a más expuestos)")
ax[1, 1].set_title("Clics acumulados por usuario (utilidad)")
for a in ax.ravel():
    a.legend(fontsize=7)
for a in [ax[0, 0], ax[0, 1], ax[1, 1]]:
    a.set_xlabel("ronda")
plt.suptitle("Feedback loop: la exposición se concentra con el tiempo (salvo con exploración)", weight="bold")
plt.tight_layout(); plt.show()
pd.DataFrame({n: {"cobertura ronda 1": h.cobertura.iat[0], f"cobertura ronda {ROUNDS}": h.cobertura.iat[-1],
                  "Gini ronda 1": h["Gini exposición"].iat[0], f"Gini ronda {ROUNDS}": h["Gini exposición"].iat[-1],
                  "clics totales/usuario": h["clics/usuario"].sum()} for n, (h, _, _) in loop.items()}).T.round(3)
''')

nb.md("""
**Cómo leerlo.** La popularidad muestra lo mismo a todos desde la primera ronda (cobertura mínima, Gini ≈ 1). El CF empieza personalizando, pero al reentrenarse con su propio feedback la **cobertura cae ronda a ronda**: los ítems que mostró reciben clics, parecen mejores y se muestran más; los que nunca mostró se quedan sin datos (*rich get richer*). Fíjate en que **MMR no lo arregla**: diversifica *géneros dentro de cada lista*, no *qué parte del catálogo* se expone — diversidad intra-lista y diversidad agregada son cosas distintas. La exploración mantiene la cobertura estable y genera **datos menos sesgados** sobre ítems que el modelo nunca habría mostrado, a cambio de algunos clics a corto plazo. Si compensa a largo plazo (retención, salud del catálogo, proveedores) solo se responde con experimentos de larga duración (módulo 15).

## 8 · Fairness de exposición (proveedores y usuarios)

### 📐 Exposición y mérito (Singh & Joachims, KDD 2018)
La atención cae con la posición; con el modelo DCG, la exposición de la posición $k$ es $v_k = 1/\\log_2(1+k)$. Para un grupo de ítems $G$ (p. ej., productoras independientes):
$$\\operatorname{Exp}(G) = \\frac{1}{\\lvert G \\rvert}\\sum_{i \\in G} \\frac{1}{\\lvert U \\rvert}\\sum_u v_{\\operatorname{pos}_u(i)}, \\qquad \\operatorname{Merit}(G) = \\frac{1}{\\lvert G \\rvert}\\sum_{i \\in G} \\bar r_i$$
(ambas son **medias por ítem** del grupo, como en el paper; $v=0$ si el ítem no aparece en la lista).
- **Paridad demográfica**: $\\operatorname{Exp}(G_0) \\approx \\operatorname{Exp}(G_1)$ (rara vez deseable: ignora la relevancia).
- **Trato dispar** (*disparate treatment*): la exposición debe ser **proporcional al mérito**: $\\dfrac{\\operatorname{Exp}(G_0)}{\\operatorname{Merit}(G_0)} \\approx \\dfrac{\\operatorname{Exp}(G_1)}{\\operatorname{Merit}(G_1)}$.

En el ratio de trato dispar el factor $1/\\lvert G\\rvert$ se cancela, así que basta con comparar **cuotas** de exposición y de mérito: es lo que calcula `exposure_report` (exposición y mérito sumados por grupo y normalizados).

Como proxy de "proveedor" usamos **cabeza** (top-10 % por popularidad: grandes estudios) frente a **cola** (independientes). Comparamos tres re-rankers: baseline, **cuota por prefijo** (estilo FA*IR, Zehlike et al. 2017: en cada prefijo de longitud $k$, al menos $\\lfloor p\\,k \\rfloor$ ítems del grupo protegido) y **amortizado** (Biega et al., SIGIR 2018: la equidad se mide acumulada entre muchos rankings; damos un bonus al grupo con déficit acumulado de exposición respecto a su mérito).
""")

nb.code(r'''
V_POS = 1 / np.log2(np.arange(2, K + 2))
HEAD = np.zeros(n_items, bool); HEAD[np.argsort(-pop)[: int(.1 * n_items)]] = True    # "grandes estudios"

def exposure_report(lists):
    exp = {"cabeza": 0.0, "cola": 0.0}; merit = {"cabeza": 0.0, "cola": 0.0}
    for u, L in lists.items():
        ids, rel = CANDS[u]
        for grp, m in [("cabeza", HEAD[ids]), ("cola", ~HEAD[ids])]:
            merit[grp] += rel[m].sum()
        for k, i in enumerate(L[:K]):
            exp["cabeza" if HEAD[i] else "cola"] += V_POS[k]
    te, tm = sum(exp.values()), sum(merit.values())
    return {f"exp {g}": exp[g] / te for g in exp} | {f"mérito {g}": merit[g] / tm for g in merit} | \
           {"ratio trato dispar (cola/cabeza)": (exp["cola"] / merit["cola"]) / (exp["cabeza"] / merit["cabeza"])}

def prefix_quota_rerank(ids, rel, p_min=.4, k=K):
    order = list(np.argsort(-rel)); tail = [j for j in order if not HEAD[ids[j]]]; out = []
    for t in range(1, k + 1):
        need = int(np.floor(p_min * t)) - sum(not HEAD[ids[j]] for j in out)
        pool = [j for j in tail if j not in out] if need > 0 else []
        out.append(pool[0] if pool else next(j for j in order if j not in out))
    return list(ids[out])

def amortized_rerank(users, beta=2.0):
    acc_exp, acc_mer, out = np.zeros(2), np.zeros(2), {}
    for u in users:
        ids, rel = CANDS[u]
        grp = (~HEAD[ids]).astype(int)                       # 1 = cola
        acc_mer += [rel[grp == 0].sum(), rel[grp == 1].sum()]
        ratio = (acc_exp + 1e-9) / (acc_mer + 1e-9)
        deficit = np.clip(ratio.max() - ratio, 0, None) / (ratio.max() + 1e-9)   # quién va por detrás
        L = list(ids[np.argsort(-(rel + beta * deficit[grp]))][:K])
        for k, i in enumerate(L):
            acc_exp[int(not HEAD[i])] += V_POS[k]
        out[u] = L
    return out
''')

nb.code(r'''
fair_lists = {"Baseline": baseline,
              "Cuota por prefijo (p=0,4)": {u: prefix_quota_rerank(*CANDS[u]) for u in eval_users},
              "Amortizado (β=2)": amortized_rerank(eval_users)}
fr = pd.DataFrame({n: {**exposure_report(L), "NDCG@10": evaluate_lists(L)["NDCG@10"]} for n, L in fair_lists.items()}).T
fig, ax = plt.subplots(1, 2, figsize=(12, 3.6))
x = np.arange(len(fr))
ax[0].bar(x - .2, fr["exp cola"], .4, label="cuota de EXPOSICIÓN de la cola")
ax[0].bar(x + .2, fr["mérito cola"], .4, label="cuota de MÉRITO (relevancia) de la cola")
ax[0].set_xticks(x, fr.index, fontsize=8); ax[0].legend(fontsize=8); ax[0].set_title("Exposición vs mérito del grupo 'cola'")
ax[1].bar(fr.index, fr["NDCG@10"], color="#bab0ac"); ax[1].set_title("Coste en precisión"); ax[1].tick_params(axis="x", labelsize=8)
plt.tight_layout(); plt.show(); fr.round(3)
''')

nb.code(r'''
# Fairness del lado del USUARIO: ¿reciben la misma calidad los usuarios poco activos? (Li et al., WWW 2021)
act = pd.Series({u: len(hist_by_user[u]) for u in eval_users})
quart = pd.qcut(act, 4, labels=["Q1 (poco activos)", "Q2", "Q3", "Q4 (muy activos)"])
uf = pd.DataFrame({"actividad": quart,
                   "CF": [ndcg_at_k(baseline[u], truth[u]) for u in act.index],
                   "Calibrado λ=0,6": [ndcg_at_k(cal_lists[u], truth[u]) for u in act.index]}).groupby("actividad", observed=False).mean()
ax = uf.plot.bar(rot=0, figsize=(7, 3.2)); ax.set_ylabel("NDCG@10"); ax.set_title("Calidad por grupo de actividad del usuario")
plt.tight_layout(); plt.show(); uf.round(4)
''')

nb.md("""
> 👀 **Qué debes observar:** (proveedores) en el baseline la barra de **exposición** de la cola queda por debajo de su barra de **mérito**: la cola recibe menos atención de la que «merece» por relevancia. La cuota por prefijo cierra el hueco a la fuerza; el amortizado lo cierra **acumulado en el tiempo** con menos coste de NDCG. (usuarios) si la calidad cae mucho en Q1 (usuarios poco activos), tienes un problema de equidad entre usuarios que ninguna métrica media te habría mostrado: por eso se evalúa por segmentos (secreto 5 del módulo 02).
""")

# --------------------------------------------------------------- 9. Pareto
nb.md("""
## 9 · Multi-objetivo y frente de Pareto

Tenemos varios objetivos (relevancia, diversidad, calibración, novedad) que compiten. Un re-ranker *greedy* con **escalarización lineal**:
$$\\operatorname{score}_t(i) = \\operatorname{rel}(i) + w_{div}\\,\\big(1 - \\max_{j \\in S}\\operatorname{sim}(i,j)\\big) + w_{nov}\\,\\operatorname{nov}(i) - w_{cal}\\,\\mathrm{KL}\\big(p \\Vert \\tilde q(S \\cup \\{i\\})\\big)$$
Barremos una rejilla de pesos y nos quedamos con las configuraciones **no dominadas**: una configuración $a$ domina a $b$ si es al menos igual de buena en todos los objetivos y estrictamente mejor en alguno. El conjunto no dominado es el **frente de Pareto**.

⚠️ La escalarización lineal solo encuentra la parte **convexa** del frente. El método **ε-restricción** ("maximiza NDCG sujeto a ILD ≥ ε y KL ≤ δ") encuentra cualquier punto y, además, es como habla negocio ("no perder más de un 2 % de NDCG"). Lin et al. (RecSys 2019, Alibaba) proponen PE-LTR para entrenar directamente modelos Pareto-eficientes.
""")
nb.code(COMBINED)

nb.code(r'''
users_p = eval_users[: (150 if FAST_DEV_RUN else 1000)]
grid = list(itertools.product([0, .15, .3, .6], [0, .5, 1, 2], [0, .2, .4]))
par = []
for w_div, w_cal, w_nov in grid:
    lists = {u: combined_rerank(u, *CANDS[u], w_div=w_div, w_cal=w_cal, w_nov=w_nov) for u in users_p}
    par.append({"w_div": w_div, "w_cal": w_cal, "w_nov": w_nov, **evaluate_lists(lists)})
par = pd.DataFrame(par)
objs = np.c_[par["NDCG@10"], par["ILD@10"], -par["KL calibración"]]
par["pareto_3d"] = pareto_mask(objs)
par["pareto_2d"] = pareto_mask(objs[:, :2])
print(f"{len(par)} configuraciones · {par.pareto_3d.sum()} en el frente 3D (NDCG, ILD, −KL) · {par.pareto_2d.sum()} en el 2D")
''')

nb.code(r'''
fig, ax = plt.subplots(1, 2, figsize=(12.5, 4.3))
sc = ax[0].scatter(par["ILD@10"], par["NDCG@10"], c=par["KL calibración"], cmap="viridis_r", s=28)
f2 = par[par.pareto_2d].sort_values("ILD@10")
ax[0].plot(f2["ILD@10"], f2["NDCG@10"], "r-o", ms=5, label="frente de Pareto (NDCG, ILD)")
ax[0].scatter(res_base["ILD@10"], res_base["NDCG@10"], marker="*", s=200, c="k", label="baseline")
plt.colorbar(sc, ax=ax[0], label="KL (miscalibración)"); ax[0].set_xlabel("ILD@10"); ax[0].set_ylabel("NDCG@10"); ax[0].legend(fontsize=8)
ax[0].set_title("Rejilla de pesos: cada punto es una configuración")
f3 = par[par.pareto_3d]
ax[1].scatter(par["KL calibración"], par["NDCG@10"], c="lightgray", s=20, label="dominadas")
ax[1].scatter(f3["KL calibración"], f3["NDCG@10"], c=f3["ILD@10"], cmap="plasma", s=45, label="Pareto 3D (color = ILD)")
ax[1].invert_xaxis(); ax[1].set_xlabel("KL (→ mejor calibrado)"); ax[1].set_ylabel("NDCG@10"); ax[1].legend(fontsize=8)
ax[1].set_title("Frente 3D proyectado en (KL, NDCG)")
plt.tight_layout(); plt.show()

base_p = evaluate_lists({u: baseline[u] for u in users_p})
ok = par[(par["ILD@10"] >= 1.15 * base_p["ILD@10"]) & (par["KL calibración"] <= .7 * base_p["KL calibración"])]
best = ok.sort_values("NDCG@10", ascending=False).head(1)
print("ε-restricción → max NDCG s.a. ILD ≥ +15 % y KL ≤ −30 % respecto al baseline:"); best.round(4)
''')

nb.md("""
> 👀 **Qué debes observar:** los puntos grises (dominados) son configuraciones que **nunca** elegirías: siempre hay otra mejor en todo. El frente es la «carta» de opciones razonables, y elegir un punto ya no es una pregunta técnica sino de producto. La celda ε-restricción traduce esa decisión al lenguaje de negocio («máximo NDCG sin perder diversidad ni calibración»): es la forma en que se suelen escribir los requisitos de un lanzamiento.
""")

nb.code(r'''
def hypervolume_2d(points, ref):
    """Área dominada por un frente (maximizar ambas) respecto a un punto de referencia."""
    P = sorted([p for p in points if p[0] > ref[0] and p[1] > ref[1]], key=lambda p: -p[0])
    hv, y_best = 0.0, ref[1]
    for x, y in P:
        if y > y_best:
            hv += (x - ref[0]) * (y - y_best); y_best = y
    return hv

ref = (par["NDCG@10"].min() * .95, par["ILD@10"].min() * .95)
for label, sub in [("solo w_div", par[(par.w_cal == 0) & (par.w_nov == 0)]), ("rejilla completa", par)]:
    pts = list(zip(sub["NDCG@10"], sub["ILD@10"]))
    print(f"Hipervolumen (NDCG, ILD) {label:18}: {hypervolume_2d(pts, ref):.5f}")
''')

# --------------------------------------------------------------- 10. Página
nb.md("""
## 10 · Optimización a nivel de página: la home de Netflix

La home de Netflix no es una lista: es una **página 2D** de filas temáticas ("Porque viste…", "Tendencias", géneros…) y en cada fila varios títulos. Netflix explicó (Alvino & Basilico, 2015, *Learning a Personalized Homepage*) que hay que decidir **qué filas**, **en qué orden** y **qué títulos dentro de cada una**, teniendo en cuenta que el usuario navega de arriba abajo y de izquierda a derecha, que las filas deben ser **diversas** entre sí y que un mismo título no debería repetirse por toda la página. Su conclusión clave: optimizar la página **como un todo**, no cada fila por separado.

### 📐 Modelo
- **Atención**: $A(r, c) = \\gamma^{r} \\cdot \\delta(c)$, con $\\gamma<1$ (las filas de abajo se miran menos) y $\\delta(c) = 1$ en las columnas visibles sin desplazar y decayendo después.
- **Utilidad de página** (con deduplicación): $U(\\text{página}) = \\sum_{(r,c)} A(r,c)\\, \\operatorname{rel}(i_{r,c})\\, \\mathbb{1}[i_{r,c} \\text{ no apareció antes}]$.
- **Greedy por filas**: en cada posición vertical, elegimos la fila candidata con mayor ganancia **marginal** (sus ítems ya mostrados valen 0) y una penalización si es del mismo "tipo" que la anterior.
- ¿Garantías? Si todas las posiciones pesaran igual y no hubiera penalización de tipo, la utilidad deduplicada sería una **función de cobertura ponderada** (monótona y submodular) y el greedy tendría la garantía $(1-1/e)$ de Nemhauser et al. Con atención decreciente por fila y la penalización, el problema pasa a ser de asignación ordenada y esa garantía **no aplica tal cual**: el greedy es la heurística estándar (y suele ser muy buena), no un óptimo certificado.
""")

nb.code(r'''
N_ROWS, N_COLS, VISIBLE = 6, 10, 5
ATT = (0.8 ** np.arange(N_ROWS))[:, None] * np.where(np.arange(N_COLS) < VISIBLE, 1.0, 0.6 ** (np.arange(N_COLS) - VISIBLE + 1))[None, :]
fig, ax = plt.subplots(figsize=(8, 3))
im = ax.imshow(ATT, cmap="magma_r"); plt.colorbar(im, ax=ax, label="probabilidad de examen")
ax.set_xlabel("columna (posición en la fila)"); ax.set_ylabel("fila"); ax.axvline(VISIBLE - .5, c="w", ls="--")
ax.set_title("Modelo de atención de la home (visible sin desplazar a la izquierda de la línea)"); plt.show()
''')

nb.code(r'''
def user_rel_full(u):
    s = cf.user_emb([u])[0] @ cf.item_emb.T
    z = (s - s.mean()) / (s.std() + 1e-9); r = 1 / (1 + np.exp(-(z - 2)))
    r[hist_by_user[u]] = 0; return r

def candidate_rows(u, n=20):
    r = user_rel_full(u); seen = set(hist_by_user[u])
    best = lambda pool: [int(i) for i in sorted(pool, key=lambda i: -r[i]) if i not in seen][:n]
    rows = {("top", "Top para ti"): best(np.argsort(-r)[:200])}
    p = genre_dist_history(u)
    for g in np.argsort(-p)[:3]:
        rows[("genero", f"Porque te gusta {GENRES[g]}")] = best(np.where(G[:, g] > 0)[0])
    last = hist_by_user[u][-1]
    nbrs = np.argsort(-(cf.item_emb @ cf.item_emb[last]))[:300]
    rows[("item", f"Porque viste {movies.title.iat[last][:25]}")] = best(nbrs)
    rows[("pop", "Tendencias")] = [int(i) for i in np.argsort(-pop) if i not in seen][:n]
    low = np.where(pop <= np.median(pop[pop > 0]))[0]
    rows[("joya", "Joyas ocultas")] = best(low)
    return rows, r

def page_independent(rows, r):
    """Filas ordenadas por la relevancia media de su cabecera; cada fila muestra su propio top (sin deduplicar)."""
    ranked = sorted(rows.items(), key=lambda kv: -np.mean([r[i] for i in kv[1][:VISIBLE]]))[:N_ROWS]
    return [(k, items[:N_COLS]) for k, items in ranked]

def page_greedy(rows, r, type_penalty=0.3):
    page, used, prev_type, remaining = [], set(), None, dict(rows)
    for pos in range(min(N_ROWS, len(rows))):
        best, best_v = None, -np.inf
        for key, items in remaining.items():
            fresh = [i for i in items if i not in used][:N_COLS]
            v = sum(ATT[pos, c] * r[i] for c, i in enumerate(fresh))
            v -= type_penalty * ATT[pos, 0] * (key[0] == prev_type)
            if v > best_v:
                best, best_v, best_items = key, v, fresh
        page.append((best, best_items)); used |= set(best_items); prev_type = best[0]; remaining.pop(best)
    return page
''')

nb.code(r'''
def page_metrics(page, r, u):
    seen_items, util, hits, dups = set(), 0.0, 0.0, 0
    for pos, (_, items) in enumerate(page):
        for c, i in enumerate(items):
            if i in seen_items:
                dups += 1; continue
            seen_items.add(i); util += ATT[pos, c] * r[i]; hits += ATT[pos, c] * (i in truth[u])
    top3 = {g for _, items in page[:3] for i in items[:VISIBLE] for g in movies.genre_list.iat[i]}
    return {"utilidad de página": util, "aciertos esperados": hits, "duplicados": dups,
            "títulos distintos": len(seen_items), "géneros en las 3 primeras filas": len(top3)}

users_pg = eval_users[: (150 if FAST_DEV_RUN else 1000)]
pm = {"Filas independientes": [], "Greedy de página": []}
for u in users_pg:
    rows, r = candidate_rows(u)
    pm["Filas independientes"].append(page_metrics(page_independent(rows, r), r, u))
    pm["Greedy de página"].append(page_metrics(page_greedy(rows, r), r, u))
pm_df = pd.DataFrame({k: pd.DataFrame(v).mean() for k, v in pm.items()}).T
fig, ax = plt.subplots(1, 5, figsize=(15, 3))
for a, col in zip(ax, pm_df.columns):
    a.bar(pm_df.index, pm_df[col], color=["#bab0ac", "#4c78a8"]); a.set_title(col, fontsize=9); a.tick_params(axis="x", labelsize=7, rotation=15)
plt.suptitle("Home: filas independientes vs optimización de página"); plt.tight_layout(); plt.show(); pm_df.round(3)
''')

nb.code(r'''
def draw_page(page, title, ax):
    cmap = plt.get_cmap("tab20"); seen_i = set()
    for pos, (key, items) in enumerate(page):
        for c, i in enumerate(items):
            g = GENRES.index(next((x for x in movies.genre_list.iat[i] if x in GENRES), "Drama"))
            ax.add_patch(plt.Rectangle((c, -pos), .92, .8, fc=cmap(g % 20), ec="w"))
            if i in seen_i:
                ax.text(c + .46, -pos + .4, "✕", ha="center", va="center", fontsize=12, weight="bold")
            seen_i.add(i)
        ax.text(-.2, -pos + .4, key[1][:28], ha="right", va="center", fontsize=7.5)
    ax.set_xlim(-5.5, N_COLS); ax.set_ylim(-len(page) + .5, 1); ax.axis("off"); ax.set_title(title, fontsize=10)

u_pg = users_pg[0]; rows, r = candidate_rows(u_pg)
fig, ax = plt.subplots(1, 2, figsize=(15, 3.8))
draw_page(page_independent(rows, r), "Filas independientes (✕ = duplicado)", ax[0])
draw_page(page_greedy(rows, r), "Greedy de página (deduplicada, filas diversas)", ax[1])
plt.suptitle(f"Home de CineMatch para el usuario {u_pg} (color = género principal)"); plt.tight_layout(); plt.show()
''')

nb.md("""
> 👀 **Qué debes observar:** en la página de filas independientes aparecen **✕** (el mismo título repetido en varias filas) y, en las etiquetas de la izquierda, filas seguidas del mismo tipo; la greedy de página elimina duplicados y alterna tipos (el color es el género principal de cada título). En las barras, la utilidad de página deduplicada sube aunque la relevancia media por casilla pueda bajar un poco: es el argumento de Netflix para optimizar la página entera. Cada casilla repetida es una oportunidad de enseñar algo nuevo perdida.
""")

# --------------------------------------------------------------- 11. Reglas
nb.md("""
## 11 · Reglas de negocio: el último kilómetro

En producción, después del modelo siempre hay reglas: **filtros duros** (perfil infantil, disponibilidad por país/licencia, ya visto), **cuotas** (máximo de títulos por género o franquicia), **boosts** (estrenos, contenido propio), **pins** (un hueco reservado para un lanzamiento). Tres principios:
1. **Composición ordenada y auditable**: cada regla es una función pura que registra qué cambió.
2. **Filtros duros antes, preferencias después**: una cuota nunca debe reintroducir algo filtrado.
3. **Loguea antes y después**: guarda las puntuaciones del modelo y la posición final. Si solo logueas la lista final, el siguiente modelo aprenderá las reglas como si fueran preferencias del usuario (y no podrás hacer IPS/OPE, módulo 14).
""")

nb.code(r'''
MATURE = {"Horror", "Thriller", "Crime", "War", "Film-Noir"}
AVAILABLE = (np.arange(n_items) * 2654435761 % 100) >= 8           # ~92 % disponible en el país (determinista)
ORIGINAL = (np.arange(n_items) * 40503 % 100) < 5                  # ~5 % "CineMatch Originals"
MAX_YEAR = np.nanmax(movies.year)

def r_kids(ids, sc, ctx):
    keep = [j for j, i in enumerate(ids) if not ctx.get("kids") or not (set(movies.genre_list.iat[i]) & MATURE)]
    return ids[keep], sc[keep], len(ids) - len(keep)
def r_availability(ids, sc, ctx):
    keep = AVAILABLE[ids]; return ids[keep], sc[keep], int((~keep).sum())
def r_boost_new(ids, sc, ctx):
    new = np.nan_to_num(movies.year.to_numpy()[ids]) >= MAX_YEAR - 2
    return ids, sc + .15 * new, int(new.sum())
def r_genre_quota(ids, sc, ctx, max_per=3):
    order, cnt, out = np.argsort(-sc), collections.Counter(), []
    for j in order:
        g = movies.genre_list.iat[ids[j]][0]
        if cnt[g] < max_per or len(out) >= K:
            out.append(j); cnt[g] += 1
    moved = int(sum(a != b for a, b in zip(out[:K], order[:K])))
    return ids[out], np.linspace(1, 0, len(out)), moved
def r_pin_original(ids, sc, ctx, slot=2):
    orig = [j for j in range(len(ids)) if ORIGINAL[ids[j]]]
    if not orig or orig[0] < K:
        return ids, sc, 0
    order = list(range(len(ids))); j = orig[0]; order.remove(j); order.insert(slot, j)
    return ids[order], np.linspace(1, 0, len(ids)), 1

RULES = [("perfil infantil", r_kids), ("disponibilidad", r_availability), ("boost estrenos", r_boost_new),
         ("cuota ≤3 por género", r_genre_quota), ("pin Original (hueco 3)", r_pin_original)]

def apply_rules(ids, sc, ctx, rules=RULES):
    ids, sc, log = np.asarray(ids), np.asarray(sc, float), []
    for name, fn in rules:
        ids, sc, n = fn(ids, sc, ctx)
        if name in ("boost estrenos",):
            o = np.argsort(-sc); ids, sc = ids[o], sc[o]
        log.append((name, n))
    return list(ids[:K]), log
''')

nb.code(r'''
steps, logs = [], collections.defaultdict(int)
kids_users = set(eval_users[::5])                                   # 20 % de perfiles infantiles
for n_rules in range(len(RULES) + 1):
    lists = {}
    for u in eval_users:
        L, log = apply_rules(*CANDS[u], {"kids": u in kids_users}, RULES[:n_rules])
        lists[u] = L
        if n_rules == len(RULES):
            for name, n in log:
                logs[name] += n
    m = evaluate_lists(lists)
    steps.append({"tras regla": "modelo" if n_rules == 0 else RULES[n_rules - 1][0], **m})
steps = pd.DataFrame(steps).set_index("tras regla")
fig, ax = plt.subplots(1, 2, figsize=(12, 3.4))
ax[0].plot(steps.index, steps["NDCG@10"], "o-"); ax[0].set_title("NDCG@10 al aplicar reglas en cascada"); ax[0].tick_params(axis="x", rotation=25, labelsize=8)
ax[1].plot(steps.index, steps["ILD@10"], "o-", c="#f58518"); ax[1].set_title("ILD@10"); ax[1].tick_params(axis="x", rotation=25, labelsize=8)
plt.tight_layout(); plt.show()
viol = sum(bool(set(movies.genre_list.iat[i]) & MATURE) for u in kids_users for i in apply_rules(*CANDS[u], {"kids": True})[0])
print("Ítems afectados por regla (total):", dict(logs), "· violaciones en perfiles infantiles:", viol)
steps.round(4)
''')

nb.code(r'''
# Resumen: todos los re-rankers del módulo sobre los mismos candidatos
summary = {"Baseline CF": baseline,
           "MMR λ=0,7": {u: mmr(*CANDS[u], lam=.7) for u in eval_users},
           "DPP θ=0,7": {u: dpp_rerank(*CANDS[u], theta=.7) for u in eval_users},
           "Calibrado λ=0,6": cal_lists,
           "Novedad β=0,2": {u: list(CANDS[u][0][np.argsort(-(CANDS[u][1] + .2 * NOV[CANDS[u][0]]))][:K]) for u in eval_users},
           "Combinado (div .3, cal 1, nov .2)": {u: combined_rerank(u, *CANDS[u], w_div=.3, w_cal=1, w_nov=.2) for u in eval_users}}
sm = pd.DataFrame({k: evaluate_lists(v) for k, v in summary.items()}).T
rel_change = ((sm / sm.loc["Baseline CF"] - 1) * 100).drop(index="Baseline CF")
better = rel_change * np.array([-1 if c in ("KL calibración", "Gini exposición") else 1 for c in rel_change.columns])
fig, ax = plt.subplots(figsize=(11, 3.8))
im = ax.imshow(better.T.values, cmap="RdYlGn", vmin=-50, vmax=50, aspect="auto")
ax.set_xticks(range(len(better)), better.index, rotation=15, fontsize=8)
ax.set_yticks(range(better.shape[1]), better.columns, fontsize=8)
for (r, c), v in np.ndenumerate(rel_change.T.values):
    ax.text(c, r, f"{v:+.0f}%", ha="center", va="center", fontsize=7.5, color="white" if abs(better.T.values[r, c]) > 35 else "black")
plt.colorbar(im, label="verde = mejora, rojo = empeora")
ax.set_title("Cambio relativo de cada métrica frente al baseline (texto = cambio real; KL y Gini: bajar es mejorar)")
plt.tight_layout(); plt.show(); sm.round(4)
''')

nb.md("""
> 👀 **Qué debes observar:** el heatmap es la tabla que llevarías a una revisión de lanzamiento: cada fila es una métrica, cada columna un re-ranker, y el color dice si mejora (verde) o empeora (rojo) frente al baseline. No hay columna toda verde: **todo re-ranking compra unas métricas con otras**. Fíjate también en las reglas de negocio: suelen empeorar alguna métrica offline y aun así son innegociables (filtros duros, disponibilidad).
""")

nb.md("""
## 🧰 Librerías de industria (y por qué aquí lo hacemos a mano)
No existe un "scikit-learn del re-ranking": en producción MMR, DPP y calibración se implementan en el propio servidor de ranking (Java/C++/Rust) sobre los candidatos de cada petición, porque son pocas líneas y deben ajustarse a la latencia. Herramientas útiles:
- **Métricas beyond-accuracy**: [RecBole](https://recbole.io/) (ItemCoverage, AveragePopularity, GiniIndex, TailPercentage), [Elliot](https://github.com/sisinflab/elliot) (decenas de métricas de diversidad, novedad y sesgo), [Microsoft Recommenders](https://github.com/recommenders-team/recommenders) (`diversity`, `novelty`, `serendipity`, `catalog_coverage` en `python_evaluation`).
- **DPP**: [DPPy](https://github.com/guilgautier/DPPy) para muestreo exacto/aproximado (útil para investigar; para MAP greedy en tiempo real se usa el algoritmo de Chen et al. implementado a mano, como aquí).
- **Fairness en ranking**: `fairsearchcore` (implementación de referencia de FA\\*IR de sus autores) y las métricas de exposición de Elliot.

🧪 **Ejercicio de verificación:** calcula `diversity`/`novelty` con Microsoft Recommenders sobre las mismas listas y comprueba que coinciden con nuestras funciones (cuidado: su diversidad usa co-ocurrencias o embeddings, no géneros, por defecto).
""")

nb.md("""
## 🏭 En producción

- **YouTube** (Wilhelm et al., CIKM 2018) introdujo una capa de **DPP** entre el ranker y las políticas del feed móvil, con el kernel $L_{ij} = \\alpha q_i q_j \\exp(-D_{ij}/2\\sigma^2)$ cuyos parámetros se ajustaron con experimentos online, y reportó mejoras en métricas de satisfacción de usuario.
- **Hulu / Chen et al.** (NeurIPS 2018) publicaron el **greedy MAP rápido** con Cholesky incremental que usamos aquí; es el algoritmo de referencia para DPP en tiempo real (con ventanas deslizantes para listas largas).
- **Netflix**: Harald Steck (Netflix) propuso las **recomendaciones calibradas** (RecSys 2018), motivadas por usuarios con varios intereses cuyas preferencias minoritarias desaparecían de las listas. Netflix describió además la construcción **personalizada de la página** (Alvino & Basilico, 2015): selección y orden de filas, diversidad entre filas y deduplicación, y la página como unidad de optimización (Gomez-Uribe & Hunt, 2015, describen el sistema completo).
- **Spotify** (Anderson et al., WWW 2020) midió que una mayor **diversidad de consumo** se asocia fuertemente a conversión y retención, que la escucha algorítmica se asocia a **menor** diversidad, y que los usuarios que se diversifican lo hacen vía escucha orgánica.
- **Pinterest** (Silva et al., FAccT 2023) desplegó diversificación de punta a punta (retrieval por *buckets* + re-ranking con **DPP** multi-objetivo) para mejorar la representación de tonos de piel en belleza y moda, con impacto neutro o positivo en utilidad.
- **LinkedIn** (Geyik et al., KDD 2019) desplegó re-ranking con restricciones de **fairness** (representación proporcional por prefijo) en LinkedIn Recruiter.
- **Alibaba** (Lin et al., RecSys 2019) propuso **PE-LTR**, aprendizaje Pareto-eficiente para optimizar a la vez GMV y CTR en e-commerce.

Latencia: MMR y calibración greedy sobre 100–500 candidatos cuestan ~ms en C++/NumPy vectorizado; el DPP rápido también. Lo caro no es el algoritmo: es **elegir el *trade-off*** — eso se decide con A/B tests de larga duración, no offline.

## 🧠 Secretos de la élite

1. **La diversidad offline no es satisfacción.** ILD sube con casi cualquier ruido. Los equipos serios fijan el *trade-off* con A/B tests de semanas y miran retención y "diversidad de consumo" real (lo que el usuario *vio*), como Spotify, no solo lo mostrado.
2. **Calibrar ≠ diversificar.** MMR mete géneros que no te interesan; la calibración devuelve tus proporciones. Para usuarios multi-interés (cuentas compartidas, familias) la calibración suele ser la palanca correcta.
3. **El kernel lo es todo en un DPP.** La similitud debe reflejar la **sustituibilidad percibida** por el usuario (dos episodios de la misma serie son sustitutos; dos dramas cualesquiera no tanto). YouTube aprendió sus parámetros con experimentos online.
4. **Los feedback loops sesgan tu evaluación offline.** Los logs reflejan la política anterior; sin huecos de exploración (o *propensities* logueadas) acabarás evaluando "quién se parece más al modelo viejo" (módulo 14).
5. **Loguea la puntuación del modelo *antes* de las reglas y la posición *después*.** Si solo guardas la lista final, el próximo modelo aprende tus reglas y tus boosts como si fueran gustos.
6. **En la home, las grandes ganancias están en la selección y orden de filas y en la deduplicación**, no en afinar el orden dentro de una fila: la atención cae muy rápido hacia abajo.
7. **Usa ε-restricciones para hablar con negocio** ("como mucho −1 % de NDCG offline, +15 % de ILD") y ajusta los pesos por superficie y segmento: los pesos de Pareto no se transfieren entre productos.
8. **Fairness amortizada > fairness por lista.** Exigir cuotas en *cada* lista es caro en precisión; medir y corregir la exposición **acumulada** entre usuarios y en el tiempo (Biega et al., 2018) consigue lo mismo con menos coste.

## ⚠️ Errores comunes
- Calcular ILD con la misma representación que usa el modelo para puntuar (se "auto-premia"); usa una representación independiente (géneros, embeddings de contenido).
- Calibrar contra el historial **sin recencia**: los gustos de hace 10 años pesan igual que los de ayer.
- Evaluar fairness de exposición sin modelo de posición (un ítem en el puesto 10 no recibe la misma atención que en el 1).
- Aplicar cuotas o boosts **antes** de los filtros duros y reintroducir contenido vetado (perfil infantil).
- Medir la cobertura del catálogo con una muestra pequeña de usuarios (siempre sale baja) y compararla entre experimentos con muestras distintas.
- Declarar "el feedback loop no existe" tras una simulación de 3 rondas: los efectos son acumulativos y lentos.
""")

nb.md("""
## 📝 Autoevaluación

1. ¿Por qué la lista con los $K$ ítems de mayor relevancia individual no maximiza la utilidad de la lista?
<details><summary>Respuesta</summary>Porque los ítems son redundantes: si son muy parecidos, su éxito está correlacionado (si al usuario no le apetece ese tipo de contenido hoy, fallan todos). La utilidad de un conjunto es submodular: cada ítem similar añade menos. Diversificar reduce el riesgo, como una cartera.</details>

2. En un DPP con $L = \\operatorname{Diag}(q)\\, S\\, \\operatorname{Diag}(q)$, ¿qué ocurre con $\\det(L_{\\{i,j\\}})$ si $i$ y $j$ son idénticos? ¿Y si son ortogonales?
<details><summary>Respuesta</summary>$\\det = q_i^2 q_j^2 (1 - S_{ij}^2)$. Idénticos ($S_{ij}=1$): determinante 0 → el DPP nunca los elige juntos. Ortogonales ($S_{ij}=0$): $q_i^2 q_j^2$, el máximo para esas calidades.</details>

3. ¿Qué ventaja computacional aporta el algoritmo de Chen et al. (2018) y por qué funciona?
<details><summary>Respuesta</summary>Reduce el greedy MAP de $O(N K^3)$–$O(NK^4)$ a $O(N K^2)$: mantiene incrementalmente la factorización de Cholesky, de modo que la ganancia marginal de cada candidato ($d_i^2$) se actualiza con un producto escalar por paso en vez de recalcular determinantes.</details>

4. Un usuario ha visto 70 % comedias y 30 % documentales. Su top-10 tiene 10 comedias. Calcula (aprox.) la KL con $\\alpha = 0{,}01$ y explica qué hace el re-ranker de Steck.
<details><summary>Respuesta</summary>$\\tilde q = 0{,}99\\cdot(1, 0) + 0{,}01\\cdot(0{,}7, 0{,}3) = (0{,}997, 0{,}003)$. KL $= 0{,}7\\log(0{,}7/0{,}997) + 0{,}3 \\log(0{,}3/0{,}003) \\approx -0{,}248 + 1{,}382 = 1{,}13$. El re-ranker cambia comedias de baja puntuación por documentales hasta acercar las proporciones a 7/3, sacrificando poca relevancia.</details>

5. ¿Por qué la exploración reduce la concentración de la exposición en la simulación de feedback loop, y qué otro beneficio tiene?
<details><summary>Respuesta</summary>Porque reparte impresiones a ítems que el modelo no habría mostrado, rompiendo el ciclo "mostrado → clicado → más mostrado". Además genera datos menos sesgados por la política, con los que el modelo aprende la calidad real de ítems poco expuestos y con los que se puede hacer evaluación off-policy.</details>

6. Diferencia entre paridad demográfica de exposición y trato dispar (Singh & Joachims).
<details><summary>Respuesta</summary>La paridad exige igual exposición media por ítem en cada grupo, ignorando la relevancia. El trato dispar exige exposición **proporcional al mérito** (relevancia media) de cada grupo: si un grupo es igual de relevante debe recibir la misma exposición relativa.</details>

7. ¿Por qué el greedy de página con deduplicación es preferible a ordenar filas de forma independiente, y cuándo tiene garantía de aproximación?
<details><summary>Respuesta</summary>En la versión simplificada (mismo peso por posición, sin penalización de tipo) la utilidad deduplicada es una función de cobertura ponderada (monótona y submodular), así que el greedy obtiene al menos $(1-1/e)$ del óptimo (Nemhauser et al., 1978). Con atención decreciente por fila la garantía formal no se transfiere directamente, pero el greedy sigue optimizando la función correcta. Las filas independientes ni siquiera optimizan esa función: cuentan varias veces el mismo título.</details>

## 📚 Referencias

**Diversidad**
- Carbonell, J. & Goldstein, J. (1998). *The Use of MMR, Diversity-Based Reranking for Reordering Documents and Producing Summaries*. SIGIR. [doi:10.1145/290941.291025](https://doi.org/10.1145/290941.291025)
- Chen, L., Zhang, G. & Zhou, H. (2018). *Fast Greedy MAP Inference for Determinantal Point Process to Improve Recommendation Diversity*. NeurIPS. [arXiv:1709.05135](https://arxiv.org/abs/1709.05135)
- Wilhelm, M., Ramanathan, A., Bonomo, A., Jain, S., Chi, E. H. & Gillenwater, J. (2018). *Practical Diversified Recommendations on YouTube with Determinantal Point Processes*. CIKM. [doi:10.1145/3269206.3272018](https://doi.org/10.1145/3269206.3272018)
- Kulesza, A. & Taskar, B. (2012). *Determinantal Point Processes for Machine Learning*. [arXiv:1207.6083](https://arxiv.org/abs/1207.6083)
- Kaminskas, M. & Bridge, D. (2016). *Diversity, Serendipity, Novelty, and Coverage: A Survey and Empirical Analysis of Beyond-Accuracy Objectives in Recommender Systems*. ACM TiiS. [doi:10.1145/2926720](https://doi.org/10.1145/2926720)
- Ge, M., Delgado-Battenfeld, C. & Jannach, D. (2010). *Beyond Accuracy: Evaluating Recommender Systems by Coverage and Serendipity*. RecSys.
- Silva, P. et al. (2023). *Representation Online Matters: Practical End-to-End Diversification in Search and Recommender Systems* (Pinterest). FAccT. [arXiv:2305.15534](https://arxiv.org/abs/2305.15534)
- Anderson, A., Maystre, L., Anderson, I., Mehrotra, R. & Lalmas, M. (2020). *Algorithmic Effects on the Diversity of Consumption on Spotify*. WWW. [doi:10.1145/3366423.3380281](https://doi.org/10.1145/3366423.3380281)

**Calibración, popularidad y feedback loops**
- Steck, H. (2018). *Calibrated Recommendations*. RecSys. [doi:10.1145/3240323.3240372](https://doi.org/10.1145/3240323.3240372)
- Abdollahpouri, H., Mansoury, M., Burke, R. & Mobasher, B. (2019). *The Unfairness of Popularity Bias in Recommendation*. [arXiv:1907.13286](https://arxiv.org/abs/1907.13286)
- Chaney, A., Stewart, B. & Engelhardt, B. (2018). *How Algorithmic Confounding in Recommendation Systems Increases Homogeneity and Decreases Utility*. RecSys. [arXiv:1710.11214](https://arxiv.org/abs/1710.11214)
- Mansoury, M., Abdollahpouri, H., Pechenizkiy, M., Mobasher, B. & Burke, R. (2020). *Feedback Loop and Bias Amplification in Recommender Systems*. CIKM. [arXiv:2007.13019](https://arxiv.org/abs/2007.13019)

**Fairness**
- Singh, A. & Joachims, T. (2018). *Fairness of Exposure in Rankings*. KDD. [arXiv:1802.07281](https://arxiv.org/abs/1802.07281)
- Biega, A., Gummadi, K. & Weikum, G. (2018). *Equity of Attention: Amortizing Individual Fairness in Rankings*. SIGIR. [arXiv:1805.01788](https://arxiv.org/abs/1805.01788)
- Zehlike, M. et al. (2017). *FA\\*IR: A Fair Top-k Ranking Algorithm*. CIKM. [arXiv:1706.06368](https://arxiv.org/abs/1706.06368)
- Geyik, S., Ambler, S. & Kenthapadi, K. (2019). *Fairness-Aware Ranking in Search & Recommendation Systems with Application to LinkedIn Talent Search*. KDD. [arXiv:1905.01989](https://arxiv.org/abs/1905.01989)
- Li, Y., Chen, H., Fu, Z., Ge, Y. & Zhang, Y. (2021). *User-oriented Fairness in Recommendation*. WWW. [arXiv:2104.10671](https://arxiv.org/abs/2104.10671)

**Multi-objetivo y página**
- Lin, X. et al. (2019). *A Pareto-Efficient Algorithm for Multiple Objective Optimization in E-Commerce Recommendation*. RecSys. [doi:10.1145/3298689.3347011](https://doi.org/10.1145/3298689.3347011)
- Alvino, C. & Basilico, J. (2015). *Learning a Personalized Homepage*. Netflix TechBlog. [netflixtechblog.com](https://netflixtechblog.com/learning-a-personalized-homepage-aa8ec670359a)
- Gomez-Uribe, C. & Hunt, N. (2015). *The Netflix Recommender System: Algorithms, Business Value, and Innovation*. ACM TMIS. [doi:10.1145/2843948](https://doi.org/10.1145/2843948)
- Nemhauser, G., Wolsey, L. & Fisher, M. (1978). *An analysis of approximations for maximizing submodular set functions*. Mathematical Programming.
""")

nb.save(LESSON)

# ===========================================================================
# PROYECTO
# ===========================================================================
pj = Notebook("Proyecto 13 · Re-ranker de la home de CineMatch", colab_path=PROJECT, gpu=False)

pj.md(f"""
{pj.badge()}

# Proyecto 13 · Re-ranker de la home de CineMatch: relevancia + diversidad + calibración

**Nivel:** 🟠 Avanzado → 🔴 Experto · **Duración:** 4–6 h · **GPU:** no necesaria · **Unidades:** ~0–1.
**Prerrequisitos:** lección 13 (y 01, 02, 08).
""")

pj.md("""
## 🏢 Contexto de negocio
El equipo de producto de **CineMatch** tiene tres quejas sobre la home:
1. *"Me salen 10 películas del mismo tipo"* (falta de **diversidad**).
2. *"Veo con mis hijos dibujos y con mi pareja thrillers, pero solo me recomienda thrillers"* (falta de **calibración**).
3. *"La misma película aparece en tres filas"* y los perfiles infantiles han visto un tráiler de terror (**página** y **reglas**).

El VP pide un re-ranker que arregle esto **sin perder más de un 7 % de NDCG@10 offline** y un análisis de qué pasará con la concentración del catálogo a medio plazo.

## 📦 Dataset
**MovieLens latest-small** (GroupLens). Géneros como espacio de diversidad/calibración. Candidatos: top-100 de un retriever PureSVD + FAISS (módulo 08). Si no hay red, datos sintéticos con la misma forma.

## ✅ Entregables y rúbrica (sobre usuarios de **test**, pesos ajustados en usuarios de **validación**)

| # | Entregable | Criterio |
|---|---|---|
| R1 | Métricas `ild`, `kl_calibration`, `gini` | pasan los tests numéricos |
| R2 | `dpp_greedy_fast` (Cholesky incremental) | coincide con el greedy ingenuo |
| R3 | `rerank_home(u, ids, rel, w)` (diversidad + calibración + novedad) | NDCG@10 ≥ 0,93 × baseline · ILD@10 ≥ 1,10 × baseline · KL ≤ 0,75 × baseline |
| R4 | Barrido de pesos + frente de Pareto + punto elegido por ε-restricción en **validación** | gráfico y tabla |
| R5 | `build_home(u)`: 6 filas × 10 títulos, deduplicada, con reglas (infantil, cuota por género) | 0 duplicados · 0 violaciones en perfiles infantiles · utilidad ≥ filas independientes |
| R6 | Simulación de feedback loop (10 rondas): baseline vs tu re-ranker | gráfico de Gini y cobertura |
""")

pj.code(PIP)
pj.code(SETUP)
pj.md("### Utilidades (módulos 01, 02, 08) y preparación de candidatos")
code_parts(pj, UTILS_DATA)
pj.code(UTILS_EVAL)
pj.code(UTILS_RETR)
pj.code(PREP)
pj.code(r'''
# Usuarios de VALIDACIÓN (para ajustar pesos) disjuntos de los de TEST (eval_users)
rest = sorted(set(truth) - set(eval_users))
val_users = sorted(int(u) for u in np.random.default_rng(1).choice(rest, size=min(len(eval_users), len(rest)), replace=False))
for u in val_users:
    CANDS[u] = candidates(u)
NOV = (lambda v: (v - v.min()) / (v.max() - v.min() + 1e-9))(-np.log2((pop + 1) / (n_users + 1)))

def genre_dist_history(u):
    h = hist_by_user[u]; w = np.linspace(.5, 1., len(h))
    p = (w[:, None] * P_gi[h]).sum(0); return p / p.sum()

def genre_dist_list(ids):
    q = P_gi[list(ids)].sum(0); return q / max(q.sum(), 1e-12)

def check(name, fn):
    try:
        fn(); print(f"✅ {name}")
    except NotImplementedError:
        print(f"⏳ {name}: TODO pendiente")
    except AssertionError as e:
        print(f"❌ {name}: {e}")
print(f"test={len(eval_users)} usuarios · validación={len(val_users)} usuarios")
''')

pj.md("""
## 🛠️ Parte 1 · Métricas (R1)
- `ild(ids)`: media de $1 - \\cos$ (géneros, usa `SIM(ids)`) sobre pares $i<j$.
- `kl_calibration(p, q, alpha=0.01)`: $\\mathrm{KL}(p\\Vert\\tilde q)$ con $\\tilde q = (1-\\alpha)q + \\alpha p$, sumando solo donde $p>0$.
- `gini(x)`: coeficiente de Gini de un vector de exposiciones.
""")
pj.code(r'''
def ild(ids):
    raise NotImplementedError   # TODO

def kl_calibration(p, q, alpha=0.01):
    raise NotImplementedError   # TODO

def gini(x):
    raise NotImplementedError   # TODO

def _t1():
    assert abs(kl_calibration(np.array([.7, .3]), np.array([1., 0.])) - 1.1336) < 1e-3, "KL del ejemplo 70/30"
    assert abs(gini(np.ones(10))) < 1e-9 and gini(np.r_[np.zeros(9), 1]) > .89, "Gini"
    ids = np.where(G[:, GENRES.index("Drama")] > 0)[0][:3]
    assert ild(ids) >= 0 and abs(ild([ids[0], ids[0]])) < 1e-6, "ILD"
check("R1 métricas", _t1)
''')

pj.md("""
## 🛠️ Parte 2 · DPP rápido (R2)
Implementa el greedy MAP de Chen et al. (2018): mantén para cada candidato el vector de Cholesky $\\mathbf{c}_i$ y $d_i^2$; al elegir $j$, $e_i = (L_{ji} - \\langle \\mathbf{c}_j, \\mathbf{c}_i\\rangle)/d_j$, $d_i^2 \\mathrel{-}= e_i^2$. Para cuando $\\max d_i^2 < \\varepsilon$.
""")
pj.code(r'''
def dpp_greedy_fast(L, k, eps=1e-10):
    raise NotImplementedError   # TODO

def dpp_greedy_naive(L, k):
    chosen = []
    for _ in range(k):
        cand = [(np.linalg.slogdet(L[np.ix_(chosen + [i], chosen + [i])]), i) for i in range(len(L)) if i not in chosen]
        (sign, v), i = max(((s, v), i) for (s, v), i in cand if s > 0)
        chosen.append(i)
    return chosen

def _t2():
    g = np.random.default_rng(0); B = g.normal(size=(20, 80)); L = B.T @ B / 20 + 1e-3 * np.eye(80)
    assert dpp_greedy_fast(L, 8) == dpp_greedy_naive(L, 8), "no coincide con el greedy ingenuo"
check("R2 DPP", _t2)
''')

pj.md("""
## 🛠️ Parte 3 · Re-ranker de la home (R3)
`rerank_home(u, ids, rel, w)` con `w = {"div": ..., "cal": ..., "nov": ...}`. Greedy: en cada paso elige el candidato que maximiza
$$\\operatorname{rel}(i) + w_{div}(1-\\max_{j\\in S}\\operatorname{sim}(i,j)) + w_{nov}\\operatorname{nov}(i) - w_{cal}\\,\\mathrm{KL}(p\\Vert \\tilde q(S\\cup\\{i\\})).$$
💡 Vectoriza la KL para todos los candidatos a la vez (una matriz `Q` de tamaño $N \\times |\\mathcal{G}|$).

<details><summary>🪜 Pista</summary>Mantén la suma de distribuciones de género de lo ya elegido, <code>acc</code> (vector de |G|). Para todos los candidatos a la vez: <code>Q = (acc + G_cand) / (len(S) + 1)</code> (cada fila es la distribución de la lista si añades ese candidato), <code>Q̃ = (1 − α)Q + α p</code> y <code>KL = (p * log(p / Q̃)).sum(1)</code> solo sobre géneros con p &gt; 0. La diversidad marginal es <code>1 − max_{j∈S} sim(i, j)</code>, que también puedes mantener incrementalmente con un <code>np.maximum</code> por paso (como en MMR).</details>
""")
pj.code(r'''
def rerank_home(u, ids, rel, w, k=K):
    raise NotImplementedError   # TODO

def evaluate_lists(lists, k=K):
    us = list(lists); exp = np.zeros(n_items)
    for u in us:
        exp[list(lists[u][:k])] += 1
    return {"NDCG@10": np.mean([ndcg_at_k(list(lists[u]), truth[u], k) for u in us]),
            "ILD@10": np.mean([ild(lists[u][:k]) for u in us]),
            "KL": np.mean([kl_calibration(genre_dist_history(u), genre_dist_list(lists[u][:k])) for u in us]),
            "Novedad": np.mean([NOV[list(lists[u][:k])].mean() for u in us]),
            "Cobertura": float((exp > 0).mean()), "Gini": gini(exp)}
''')

pj.md("""
## 🛠️ Parte 4 · Pareto + ε-restricción en validación (R4)
Barre al menos 30 combinaciones de pesos en `val_users`, marca las no dominadas en (NDCG, ILD, −KL) y elige por **ε-restricción**: entre las que cumplen NDCG ≥ 0,93×, ILD ≥ 1,10× y KL ≤ 0,75× el baseline **de validación**, la de mayor NDCG (si ninguna cumple, la de Pareto con mejor compromiso y NDCG ≥ 0,93×). Después evalúa ese punto **una sola vez** en test.
""")
pj.code(r'''
def pareto_mask(P):
    raise NotImplementedError   # TODO (todas las columnas se maximizan)

def choose_weights(grid, users):
    raise NotImplementedError   # TODO: devuelve (DataFrame del barrido, dict de pesos elegidos)
''')

pj.md("""
## 🛠️ Parte 5 · Home completa con reglas (R5)
`build_home(u, kids=False)` devuelve una lista de 6 filas `(titulo_fila, [10 ids])`:
- Filas candidatas: "Top para ti" (tu `rerank_home`), 3 × "Porque te gusta <género>", "Tendencias", "Joyas ocultas".
- **Greedy de página** con el modelo de atención `ATT` y deduplicación.
- **Reglas**: en perfil infantil se eliminan `MATURE`; ninguna fila con más de 4 títulos del mismo género principal.

<details><summary>🪜 Pista</summary>Orden de la lección (§11): primero los <b>filtros duros</b> sobre los candidatos de cada fila (infantil, ya vistos), después el greedy de página con deduplicación y, al rellenar cada fila, la <b>cuota</b> por género (salta el candidato si su género ya tiene 4). Así una cuota nunca reintroduce algo filtrado. Para comprobar R5 escribe dos <code>assert</code>: ningún id repetido en la página y ningún género de <code>MATURE</code> si <code>kids=True</code>.</details>
""")
pj.code(r'''
N_ROWS, N_COLS, VISIBLE = 6, 10, 5
ATT = (0.8 ** np.arange(N_ROWS))[:, None] * np.where(np.arange(N_COLS) < VISIBLE, 1., .6 ** (np.arange(N_COLS) - VISIBLE + 1))[None, :]
MATURE = {"Horror", "Thriller", "Crime", "War", "Film-Noir"}

def build_home(u, kids=False):
    raise NotImplementedError   # TODO

def page_value(page, r):
    seen, util, dups = set(), 0.0, 0
    for pos, (_, items) in enumerate(page):
        for c, i in enumerate(items):
            if i in seen:
                dups += 1
            else:
                seen.add(i); util += ATT[pos, c] * r[i]
    return util, dups
''')

# ------------------------------------------------------------- SOLUCIÓN
pj.md("""
---
# ⛔ SPOILER — intenta resolverlo primero
Solución de referencia completa: redefine las funciones y ejecuta la evaluación final (R1–R6).
""")
pj.code(r'''
# ---------- R1 ----------
def ild(ids):
    ids = list(ids)
    if len(ids) < 2:
        return 0.0
    S = SIM(ids); return float((1 - S)[np.triu_indices(len(ids), 1)].mean())

def kl_calibration(p, q, alpha=0.01):
    qt = (1 - alpha) * q + alpha * p; m = p > 0
    return float(np.sum(p[m] * np.log(p[m] / qt[m])))

def gini(x):
    x = np.sort(np.asarray(x, float)); n = len(x)
    return 0.0 if x.sum() == 0 else float((2 * np.arange(1, n + 1) - n - 1) @ x / (n * x.sum()))

check("R1 métricas", _t1)
''')
pj.code(r'''
# ---------- R2 ----------
def dpp_greedy_fast(L, k, eps=1e-10):
    N = L.shape[0]; c = np.zeros((k, N)); d2 = np.diag(L).astype(float).copy()
    chosen = [int(np.argmax(d2))]
    while len(chosen) < k:
        j, t = chosen[-1], len(chosen) - 1
        e = (L[j] - c[:t, j] @ c[:t]) / np.sqrt(d2[j])
        c[t] = e; d2 = d2 - e ** 2; d2[chosen] = -np.inf
        nxt = int(np.argmax(d2))
        if d2[nxt] < eps:
            break
        chosen.append(nxt)
    return chosen

check("R2 DPP", _t2)
''')
pj.code(r'''
# ---------- R3 ----------
def kl_rows(p, Q, alpha=0.01):
    Qt = (1 - alpha) * Q + alpha * p; m = p > 0
    return (p[m] * np.log(p[m] / Qt[:, m])).sum(1)

def rerank_home(u, ids, rel, w, k=K):
    ids, rel = np.asarray(ids), np.asarray(rel)
    p, S = genre_dist_history(u), SIM(ids)
    chosen, acc = [], np.zeros(len(GENRES)); max_sim = np.zeros(len(ids)); avail = np.ones(len(ids), bool)
    for t in range(min(k, len(ids))):
        score = rel + w.get("nov", 0) * NOV[ids] + (w.get("div", 0) * (1 - max_sim) if t else 0)
        if w.get("cal", 0):
            Q = acc + P_gi[ids]; score = score - w["cal"] * kl_rows(p, Q / Q.sum(1, keepdims=True))
        score[~avail] = -np.inf
        j = int(np.argmax(score)); chosen.append(j); avail[j] = False
        acc += P_gi[ids[j]]; max_sim = np.maximum(max_sim, S[j])
    return list(ids[chosen])

base_test = evaluate_lists({u: list(CANDS[u][0][:K]) for u in eval_users})
pd.Series(base_test, name="baseline (test)").round(4)
''')
pj.code(r'''
# ---------- R4 ----------
def pareto_mask(P):
    keep = np.ones(len(P), bool)
    for i in range(len(P)):
        keep[i] = not (np.all(P >= P[i], 1) & np.any(P > P[i], 1)).any()
    return keep

def choose_weights(grid, users):
    base = evaluate_lists({u: list(CANDS[u][0][:K]) for u in users})
    rows = [{**w, **evaluate_lists({u: rerank_home(u, *CANDS[u], w) for u in users})} for w in grid]
    df = pd.DataFrame(rows)
    df["pareto"] = pareto_mask(np.c_[df["NDCG@10"], df["ILD@10"], -df["KL"]])
    df["gain"] = df["ILD@10"] / base["ILD@10"] - df["KL"] / base["KL"]          # compromiso diversidad + calibración
    keep_ndcg = df["NDCG@10"] >= .93 * base["NDCG@10"]
    ok = df[keep_ndcg & (df["ILD@10"] >= 1.10 * base["ILD@10"]) & (df["KL"] <= .75 * base["KL"])]
    if len(ok):
        pick = ok.sort_values("NDCG@10", ascending=False).iloc[0]
    else:                                                                        # ε-restricción no factible
        pick = df[df.pareto & keep_ndcg].sort_values("gain", ascending=False).iloc[0]
    return df, {k: float(pick[k]) for k in ["div", "cal", "nov"]}, base

grid = [{"div": a, "cal": b, "nov": c} for a, b, c in itertools.product([0, .05, .1, .15, .3], [0, .15, .3, .5, 1], [0, .1])]
sweep, W, base_val = choose_weights(grid, val_users)
fig, ax = plt.subplots(figsize=(7, 4))
s = ax.scatter(sweep["ILD@10"], sweep["NDCG@10"], c=sweep["KL"], cmap="viridis_r", s=25)
f = sweep[sweep.pareto]; ax.scatter(f["ILD@10"], f["NDCG@10"], facecolors="none", edgecolors="r", s=80, label="Pareto 3D")
pk = sweep[(sweep["div"] == W["div"]) & (sweep["cal"] == W["cal"]) & (sweep["nov"] == W["nov"])]
ax.scatter(pk["ILD@10"], pk["NDCG@10"], marker="*", s=250, c="gold", ec="k", label=f"elegido {W}")
ax.scatter(base_val["ILD@10"], base_val["NDCG@10"], marker="X", s=120, c="k", label="baseline")
plt.colorbar(s, label="KL"); ax.set_xlabel("ILD@10"); ax.set_ylabel("NDCG@10"); ax.legend(fontsize=7)
ax.set_title(f"Barrido en VALIDACIÓN ({len(grid)} configuraciones)"); plt.show()

final = evaluate_lists({u: rerank_home(u, *CANDS[u], W) for u in eval_users})
rep = pd.DataFrame({"baseline": base_test, "re-ranker": final}).T
crit = {"NDCG ≥ 0,93×": final["NDCG@10"] >= .93 * base_test["NDCG@10"], "ILD ≥ 1,10×": final["ILD@10"] >= 1.10 * base_test["ILD@10"],
        "KL ≤ 0,75×": final["KL"] <= .75 * base_test["KL"]}
print("R3 (test):", {k: "✅" if v else "❌" for k, v in crit.items()}); rep.round(4)
''')
pj.code(r'''
# ---------- R5 ----------
def user_rel_full(u):
    s = cf.user_emb([u])[0] @ cf.item_emb.T
    z = (s - s.mean()) / (s.std() + 1e-9); r = 1 / (1 + np.exp(-(z - 2))); r[hist_by_user[u]] = 0
    return r

def apply_row_rules(items, kids, max_per_genre=4):
    out, cnt = [], collections.Counter()
    for i in items:
        gs = movies.genre_list.iat[i]
        if kids and set(gs) & MATURE:
            continue
        if cnt[gs[0]] >= max_per_genre:
            continue
        out.append(i); cnt[gs[0]] += 1
    return out

def candidate_rows_home(u, kids=False, n=30):
    r = user_rel_full(u); seen = set(hist_by_user[u])
    top = lambda pool: [int(i) for i in sorted(pool, key=lambda i: -r[i]) if i not in seen][:n]
    ids, rel = CANDS[u] if u in CANDS else candidates(u)
    rows = {("top", "Top para ti"): rerank_home(u, ids, rel, W, k=n)}
    for g in np.argsort(-genre_dist_history(u))[:3]:
        rows[("genero", f"Porque te gusta {GENRES[g]}")] = top(np.where(G[:, g] > 0)[0])
    rows[("pop", "Tendencias")] = [int(i) for i in np.argsort(-pop) if i not in seen][:n]
    rows[("joya", "Joyas ocultas")] = top(np.where(pop <= np.median(pop[pop > 0]))[0])
    return {k: apply_row_rules(v, kids) for k, v in rows.items()}, r

def page_greedy(rows, r, type_penalty=.3):
    page, used, prev, rem = [], set(), None, dict(rows)
    for pos in range(min(N_ROWS, len(rows))):
        scored = []
        for key, items in rem.items():
            fresh = [i for i in items if i not in used][:N_COLS]
            v = sum(ATT[pos, c] * r[i] for c, i in enumerate(fresh)) - type_penalty * ATT[pos, 0] * (key[0] == prev)
            scored.append((v, key, fresh))
        v, key, fresh = max(scored, key=lambda x: x[0])
        page.append((key[1], fresh)); used |= set(fresh); prev = key[0]; rem.pop(key)
    return page

def build_home(u, kids=False):
    rows, r = candidate_rows_home(u, kids)
    return page_greedy(rows, r)

def page_independent(u, kids=False):
    rows, r = candidate_rows_home(u, kids)
    ranked = sorted(rows.items(), key=lambda kv: -np.mean([r[i] for i in kv[1][:VISIBLE]] or [0]))[:N_ROWS]
    return [(k[1], v[:N_COLS]) for k, v in ranked]

users_h = eval_users[:100]; kids_set = set(users_h[::4])
res_h = {"Filas independientes": [], "Greedy de página + reglas": []}; viol = 0
for u in users_h:
    r = user_rel_full(u); kids = u in kids_set
    res_h["Filas independientes"].append(page_value(page_independent(u, kids), r))
    pg = build_home(u, kids); res_h["Greedy de página + reglas"].append(page_value(pg, r))
    viol += kids * sum(bool(set(movies.genre_list.iat[i]) & MATURE) for _, it in pg for i in it)
hdf = pd.DataFrame({k: {"utilidad": np.mean([a for a, _ in v]), "duplicados": np.mean([b for _, b in v])} for k, v in res_h.items()}).T
ok5 = hdf.loc["Greedy de página + reglas", "duplicados"] == 0 and viol == 0 and \
      hdf.loc["Greedy de página + reglas", "utilidad"] >= hdf.loc["Filas independientes", "utilidad"]
print("R5:", "✅" if ok5 else "❌", f"· violaciones infantiles={viol}"); hdf.round(3)
''')
pj.code(r'''
# Visualización de una home
u0 = users_h[0]; page = build_home(u0)
fig, ax = plt.subplots(figsize=(11, 3.6)); cmap = plt.get_cmap("tab20")
for pos, (title, items) in enumerate(page):
    for c, i in enumerate(items):
        g = GENRES.index(next((x for x in movies.genre_list.iat[i] if x in GENRES), "Drama"))
        ax.add_patch(plt.Rectangle((c, -pos), .92, .8, fc=cmap(g % 20), ec="w"))
        ax.text(c + .46, -pos + .4, movies.title.iat[i][:9], ha="center", va="center", fontsize=5.5)
    ax.text(-.2, -pos + .4, title[:30], ha="right", va="center", fontsize=8)
ax.set_xlim(-5.5, N_COLS); ax.set_ylim(-len(page) + .5, 1); ax.axis("off")
ax.set_title(f"Home de CineMatch del usuario {u0} (color = género principal)"); plt.show()
''')
pj.code(r'''
# ---------- R6 · feedback loop: baseline vs re-ranker ----------
def ground_truth(dim=32, base_ctr=.03, temp=1.0):
    Xall = build_interaction_matrix(ratings, n_users, n_items)
    svd = TruncatedSVD(dim, random_state=SEED).fit(Xall)
    S = (Xall @ svd.components_.T) @ svd.components_
    Z = (S - S.mean(1, keepdims=True)) / (S.std(1, keepdims=True) + 1e-9)
    return 1 / (1 + np.exp(-(temp * np.clip(Z, -3, 3) + np.log(base_ctr / (1 - base_ctr)))))

def run_loop(use_reranker, rounds=10, sim_users=None, seed=SEED):
    g = np.random.default_rng(seed); us = np.array(sim_users)
    Xobs = X.copy().tolil(); exposure = np.zeros(n_items); hist = []
    for t in range(rounds):
        Xc = Xobs.tocsr(); svd = TruncatedSVD(32, random_state=SEED).fit(Xc)
        Sc = np.asarray((Xc[us] @ svd.components_.T) @ svd.components_); Sc[Xc[us].nonzero()] = -np.inf
        recs = []
        for row, u in enumerate(us):
            top = np.argpartition(-Sc[row], N_CAND)[:N_CAND]; top = top[np.argsort(-Sc[row, top])]
            sc = Sc[row, top]; rel = (sc - sc.min()) / (sc.max() - sc.min() + 1e-9)
            recs.append(rerank_home(u, top, rel, W) if use_reranker else list(top[:K]))
        recs = np.array(recs); np.add.at(exposure, recs.ravel(), 1)
        clicks = g.random(recs.shape) < P_TRUE[us[:, None], recs]
        for r_, c_ in zip(*np.nonzero(clicks)):
            Xobs[us[r_], recs[r_, c_]] = 1
        hist.append({"ronda": t + 1, "Gini": gini(exposure), "cobertura acumulada": (exposure > 0).mean(), "clics": clicks.sum()})
    return pd.DataFrame(hist)

P_TRUE = ground_truth()
sim_users = eval_users[: (150 if FAST_DEV_RUN else len(eval_users))]
loops = {"Baseline CF": run_loop(False, sim_users=sim_users), "Re-ranker home": run_loop(True, sim_users=sim_users)}
fig, ax = plt.subplots(1, 3, figsize=(13, 3.3))
for name, h in loops.items():
    ax[0].plot(h.ronda, h.Gini, "o-", label=name); ax[1].plot(h.ronda, h["cobertura acumulada"], "o-", label=name)
    ax[2].plot(h.ronda, h.clics.cumsum(), "o-", label=name)
for a, t in zip(ax, ["Gini de exposición", "Cobertura acumulada del catálogo", "Clics acumulados"]):
    a.set_title(t); a.set_xlabel("ronda"); a.legend(fontsize=8)
plt.tight_layout(); plt.show()
''')

pj.md("""
## 🚀 Retos extra (nivel experto)
1. **DPP en la fila "Top para ti"**: sustituye el término de diversidad por un DPP con el kernel de YouTube y busca $(\\alpha, \\sigma)$ en validación. ¿Domina al greedy combinado en el frente de Pareto?
2. **Calibración por embeddings**: en vez de géneros, agrupa los ítems con k-means sobre embeddings de contenido (módulo 03) y calibra sobre esos *clusters*.
3. **Fairness amortizada de proveedores** dentro de la home: garantiza que la exposición acumulada del 90 % menos popular del catálogo sea ≥ 0,8 × su mérito, a lo largo de todos los usuarios.
4. **Pesos personalizados**: aprende $w_{div}$ por segmento de usuario (p. ej., por entropía de su historial). ¿Mejora el frente?
5. **Off-policy**: loguea propensiones del re-ranker (con algo de aleatoriedad) y estima con IPS el CTR de otra configuración de pesos (módulo 14).

## 🤔 Reflexión (producción / MLOps)
- ¿Qué métricas *beyond-accuracy* pondrías como **guardrails** en un A/B test de este re-ranker (módulo 15)? ¿Cuánto tiempo lo dejarías correr y por qué?
- ¿Dónde vive este re-ranker en la arquitectura online (módulo 16)? ¿Qué presupuesto de latencia le das y qué pasa si se excede (fallback)?
- ¿Qué logs necesitas para que el siguiente modelo no aprenda tus reglas como si fueran preferencias?
- Si el negocio cambia los pesos cada semana, ¿cómo versionas y auditas esas decisiones (módulo 17)?
""")

pj.save(PROJECT)
