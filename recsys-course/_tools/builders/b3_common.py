"""Fragmentos compartidos por los builders del Bloque III (módulos 06, 07, 08).

Solo contiene *strings* con código/markdown que se insertan en los notebooks,
para que cada notebook sea autocontenido en Colab.
"""

def header(nb, numero: str, titulo: str, nivel: str, duracion: str, gpu: str,
           unidades: str, prereq: str, tipo: str = "Lección") -> None:
    nb.md(f"""
{nb.badge()}

# Módulo {numero} · {titulo}
### {tipo} — Curso «Sistemas de Recomendación: de cero a nivel Netflix»

| | |
|---|---|
| **Nivel** | {nivel} |
| **Duración estimada** | {duracion} |
| **GPU recomendada** | {gpu} |
| **Unidades de Colab estimadas** | {unidades} |
| **Prerrequisitos** | {prereq} |

> En Colab: *Entorno de ejecución → Cambiar tipo de entorno → GPU*. Todo el notebook
> funciona también en CPU con `FAST_DEV_RUN = True` (más lento, mismos conceptos).
""")


# ---------------------------------------------------------------------------
# Utilidades MovieLens + split temporal + métricas (resumen de módulos 01 y 02)
# ---------------------------------------------------------------------------
ML_UTILS_MD = """
### 🧰 Utilidades mínimas (vienen de los módulos 01 y 02)

Para que este notebook sea **autocontenido en Colab** repetimos aquí, en versión
compacta, tres piezas que ya construiste antes:

1. `load_movielens(size)` — descarga MovieLens desde GroupLens (módulo 01). Si no hay
   red, genera un **MovieLens sintético** con el mismo esquema para que nada se bloquee.
2. `temporal_split(...)` — split **temporal global** (módulo 01): entrenamos con el
   pasado y evaluamos con el futuro, como en producción.
3. `recall_at_k`, `ndcg_at_k` — métricas de ranking de top-K (módulo 02).
"""

ML_UTILS_CODE = r'''
# === Utilidades mínimas (módulos 01 y 02) ===================================
import os, io, zipfile, urllib.request
import numpy as np
import pandas as pd

ML_URLS = {
    "1m": "https://files.grouplens.org/datasets/movielens/ml-1m.zip",
    "25m": "https://files.grouplens.org/datasets/movielens/ml-25m.zip",
}

def _synthetic_movielens(n_users=1500, n_items=900, seed=42):
    """MovieLens 'de juguete' con el mismo esquema que ML-1M (fallback sin red)."""
    rng = np.random.default_rng(seed)
    genres = ["Action", "Comedy", "Drama", "Thriller", "Romance", "Sci-Fi",
              "Horror", "Animation", "Documentary", "Children's"]
    G = len(genres)
    item_g = rng.dirichlet(np.ones(G) * 0.3, n_items)            # mezcla de géneros
    user_g = rng.dirichlet(np.ones(G) * 0.5, n_users)            # gustos
    pop = np.minimum(rng.zipf(1.4, n_items), 300).astype(float)  # cola larga
    activity = np.clip(rng.zipf(1.6, n_users) * 20, 20, 600).astype(int)
    rows, t0 = [], 956_703_932                                    # ~abril 2000
    for u in range(n_users):
        aff = item_g @ user_g[u]
        p = pop * (aff + 0.02) ** 2
        p /= p.sum()
        n = min(activity[u], n_items // 2)
        items = rng.choice(n_items, size=n, replace=False, p=p)
        score = 4 * (aff[items] / aff.max()) + rng.normal(0, 0.8, n)
        r = np.clip(np.round(1 + score), 1, 5).astype(int)
        start = t0 + rng.integers(0, 2 * 365 * 86400)
        ts = np.sort(start + rng.integers(0, 365 * 86400, n))
        rows.append(pd.DataFrame({"user_id": u + 1, "item_id": items + 1,
                                  "rating": r, "timestamp": ts}))
    ratings = pd.concat(rows, ignore_index=True)
    gnames = ["|".join([genres[g] for g in np.where(item_g[i] > 0.25)[0]] or
                       [genres[int(item_g[i].argmax())]]) for i in range(n_items)]
    years = rng.integers(1930, 2001, n_items)
    movies = pd.DataFrame({"item_id": np.arange(1, n_items + 1),
                           "title": [f"Película sintética {i+1} ({y})" for i, y in enumerate(years)],
                           "genres": gnames})
    users = pd.DataFrame({"user_id": np.arange(1, n_users + 1),
                          "gender": rng.choice(["M", "F"], n_users),
                          "age": rng.choice([1, 18, 25, 35, 45, 50, 56], n_users),
                          "occupation": rng.integers(0, 21, n_users),
                          "zip": [f"{z:05d}" for z in rng.integers(0, 99999, n_users)]})
    return ratings, movies, users

def load_movielens(size: str = "1m", data_dir: str = "data"):
    """Devuelve (ratings, movies, users) con columnas user_id, item_id, rating, timestamp."""
    os.makedirs(data_dir, exist_ok=True)
    try:
        zpath = os.path.join(data_dir, f"ml-{size}.zip")
        if not os.path.exists(zpath):
            print(f"Descargando MovieLens-{size} de GroupLens…")
            urllib.request.urlretrieve(ML_URLS[size], zpath)
        with zipfile.ZipFile(zpath) as z:
            if size == "1m":
                rd = lambda f, cols: pd.read_csv(io.BytesIO(z.read(f"ml-1m/{f}")), sep="::",
                                                 engine="python", names=cols, encoding="latin-1")
                ratings = rd("ratings.dat", ["user_id", "item_id", "rating", "timestamp"])
                movies = rd("movies.dat", ["item_id", "title", "genres"])
                users = rd("users.dat", ["user_id", "gender", "age", "occupation", "zip"])
            else:
                ratings = pd.read_csv(z.open("ml-25m/ratings.csv")).rename(
                    columns={"userId": "user_id", "movieId": "item_id"})
                movies = pd.read_csv(z.open("ml-25m/movies.csv")).rename(columns={"movieId": "item_id"})
                users = None
        print(f"MovieLens-{size} real: {len(ratings):,} ratings")
    except Exception as e:  # sin red / URL caída → fallback sintético
        print(f"⚠️ No se pudo descargar MovieLens ({type(e).__name__}). Uso datos SINTÉTICOS.")
        ratings, movies, users = _synthetic_movielens()
    return ratings, movies, users

def temporal_split(df: pd.DataFrame, val_frac=0.1, test_frac=0.1, ts_col="timestamp"):
    """Split temporal GLOBAL: [pasado | validación | futuro] por cuantiles de tiempo."""
    t_val, t_test = df[ts_col].quantile([1 - val_frac - test_frac, 1 - test_frac])
    train = df[df[ts_col] < t_val]
    val = df[(df[ts_col] >= t_val) & (df[ts_col] < t_test)]
    test = df[df[ts_col] >= t_test]
    return train, val, test

def recall_at_k(topk: np.ndarray, truth: list, k: int) -> float:
    """topk: [U, >=k] ids recomendados; truth: lista de sets con los relevantes."""
    vals = [len(set(row[:k]) & t) / len(t) for row, t in zip(topk, truth) if len(t) > 0]
    return float(np.mean(vals)) if vals else 0.0

def ndcg_at_k(topk: np.ndarray, truth: list, k: int) -> float:
    """NDCG@k con relevancia binaria (módulo 02)."""
    disc = 1.0 / np.log2(np.arange(2, k + 2))
    vals = []
    for row, t in zip(topk, truth):
        if not t:
            continue
        gains = np.array([1.0 if i in t else 0.0 for i in row[:k]])
        idcg = disc[: min(len(t), k)].sum()
        vals.append((gains * disc[: len(gains)]).sum() / idcg)
    return float(np.mean(vals)) if vals else 0.0
'''

# ---------------------------------------------------------------------------
# Helper para dibujar arquitecturas con matplotlib
# ---------------------------------------------------------------------------
DRAW_CODE = r'''
# === Helper para dibujar arquitecturas (cajas + flechas) con matplotlib ======
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

PALETTE = {"in": "#dbe9f6", "emb": "#c6e2c3", "inter": "#fde2b8", "mlp": "#f6c9c9",
           "out": "#e1d5f0", "gate": "#fff3a8", "grey": "#eeeeee"}

def _edge_point(box, other):
    x, y, w, h = box[:4]
    cx, cy = x + w / 2, y + h / 2
    ox, oy = other[0] + other[2] / 2, other[1] + other[3] / 2
    dx, dy = ox - cx, oy - cy
    if dx == 0 and dy == 0:
        return cx, cy
    t = min((w / 2) / abs(dx) if dx else np.inf, (h / 2) / abs(dy) if dy else np.inf)
    return cx + t * dx, cy + t * dy

def draw_blocks(ax, boxes: dict, arrows: list, title: str = "", xlim=(0, 10), ylim=(0, 10)):
    """boxes = {clave: (x, y, w, h, texto, color)}; arrows = [(origen, destino[, etiqueta])]."""
    for key, (x, y, w, h, txt, col) in boxes.items():
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.15",
                                    fc=PALETTE.get(col, col), ec="#333333", lw=1.2, zorder=2))
        ax.text(x + w / 2, y + h / 2, txt, ha="center", va="center", fontsize=9, zorder=3)
    for a in arrows:
        s, d = boxes[a[0]], boxes[a[1]]
        p1, p2 = _edge_point(s, d), _edge_point(d, s)
        ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=12,
                                     color="#444444", lw=1.1, zorder=1))
        if len(a) > 2:
            ax.text((p1[0] + p2[0]) / 2 + 0.1, (p1[1] + p2[1]) / 2, a[2], fontsize=8, color="#444")
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.axis("off")
    if title:
        ax.set_title(title, fontsize=11, weight="bold")
'''

SETUP_CODE = r'''
import random, time, math, warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
import torch.nn.functional as F

warnings.filterwarnings("ignore")
seed = 42
random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
device = "cuda" if torch.cuda.is_available() else "cpu"
print("device:", device, "| torch", torch.__version__)
if device == "cuda":
    print(torch.cuda.get_device_name(0))
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.3})
'''
