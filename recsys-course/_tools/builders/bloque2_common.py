"""Celdas compartidas por los builders del Bloque II (módulos 03, 04 y 05).

Contiene el código de la celda «🧰 Utilidades del curso»: carga de MovieLens 1M,
split temporal global, codificación a matriz dispersa y métricas top-K
(NDCG@K, Recall@K, coverage). Son versiones mínimas de lo construido en
01_data y 02_evaluation, para que cada notebook sea autocontenido en Colab.
"""

UTILS_MD = """
## 🧰 Utilidades del curso

Para que este notebook sea **autocontenido en Colab**, las tres celdas siguientes
contienen versiones mínimas de las utilidades que construimos en
[01_data](../01_data) (carga de MovieLens + **split temporal global**) y
[02_evaluation](../02_evaluation) (**NDCG@K, Recall@K, coverage**). Son las mismas
definiciones; si ya tienes tu propia librería de los módulos 01/02, puedes
importarla en su lugar.

Convenciones que usaremos en todo el Bloque II:

| Concepto | Convención |
|---|---|
| Columnas | `user_id`, `item_id`, `rating`, `timestamp` (IDs originales de MovieLens) |
| Índices internos | `uidx`, `iidx` contiguos `0..n-1`, definidos **solo con train** |
| Split | temporal **global**: el 80 % más antiguo de las interacciones → train, el 20 % más reciente → test |
| Implícito | positivo = `rating ≥ 4` (protocolo de Liang et al. 2018 / Steck 2019) |
| Evaluación | *full ranking* sobre todo el catálogo, excluyendo lo ya visto en train |
"""

UTILS_DATA = r'''
# 🧰 Utilidades del curso (1/3) — carga de datos. Mismas funciones que en 01_data.
import io, os, zipfile, urllib.request
from pathlib import Path
import numpy as np
import pandas as pd
import scipy.sparse as sp

DATA_DIR = Path(os.environ.get("RECSYS_DATA", "data"))
ML1M_URL = "https://files.grouplens.org/datasets/movielens/ml-1m.zip"
# Espejo público en GitHub (mismo contenido, en CSV) por si GroupLens no responde
ML1M_MIRROR = "https://raw.githubusercontent.com/khanhnamle1994/movielens/master"


def load_movielens_1m(data_dir: Path = DATA_DIR):
    """Devuelve (ratings, movies, users) de MovieLens 1M, cacheados en parquet."""
    d = Path(data_dir) / "ml-1m"
    d.mkdir(parents=True, exist_ok=True)
    cache = {n: d / f"{n}.parquet" for n in ("ratings", "movies", "users")}
    if all(p.exists() for p in cache.values()):
        return tuple(pd.read_parquet(p) for p in cache.values())
    try:
        with urllib.request.urlopen(ML1M_URL, timeout=60) as r:
            zipfile.ZipFile(io.BytesIO(r.read())).extractall(d.parent)
        rd = lambda f, cols: pd.read_csv(d / f, sep="::", engine="python", names=cols, encoding="latin-1")
        ratings = rd("ratings.dat", ["user_id", "item_id", "rating", "timestamp"])
        movies = rd("movies.dat", ["item_id", "title", "genres"])
        users = rd("users.dat", ["user_id", "gender", "age", "occupation", "zip"])
    except Exception as e:  # fallback: espejo en GitHub
        print(f"GroupLens no disponible ({e.__class__.__name__}); usando espejo de GitHub…")
        rd = lambda f: pd.read_csv(f"{ML1M_MIRROR}/{f}", sep="\t", index_col=0, encoding="latin-1")
        ratings = rd("ratings.csv").rename(columns={"movie_id": "item_id"})[["user_id", "item_id", "rating", "timestamp"]]
        movies = rd("movies.csv").rename(columns={"movie_id": "item_id"})[["item_id", "title", "genres"]]
        users = rd("users.csv").rename(columns={"zipcode": "zip"})[["user_id", "gender", "age", "occupation", "zip"]]
    movies["genres"] = movies["genres"].str.split("|")
    movies["year"] = movies["title"].str.extract(r"\((\d{4})\)\s*$").astype(float)
    for n, df in zip(cache, (ratings, movies, users)):
        df.to_parquet(cache[n], index=False)
    return ratings, movies, users

'''

UTILS_SPLIT = r'''
# 🧰 Utilidades del curso (2/3) — split temporal y codificación. Mismas funciones que en 01_data.
def temporal_split(df: pd.DataFrame, test_frac: float = 0.2, ts_col: str = "timestamp"):
    """Split temporal GLOBAL: todo lo anterior al corte → train; lo posterior → test.
    El test se filtra a usuarios e ítems vistos en train (warm-start)."""
    cutoff = df[ts_col].quantile(1 - test_frac)
    train, test = df[df[ts_col] <= cutoff], df[df[ts_col] > cutoff]
    test = test[test.user_id.isin(train.user_id) & test.item_id.isin(train.item_id)]
    return train.reset_index(drop=True), test.reset_index(drop=True)


class Encoder:
    """Mapea IDs originales ↔ índices contiguos (ajustado SOLO con train)."""
    def __init__(self, train: pd.DataFrame):
        self.users = np.sort(train.user_id.unique())
        self.items = np.sort(train.item_id.unique())
        self.u2i = pd.Series(np.arange(len(self.users)), index=self.users)
        self.i2i = pd.Series(np.arange(len(self.items)), index=self.items)
        self.n_users, self.n_items = len(self.users), len(self.items)

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df[df.user_id.isin(self.u2i.index) & df.item_id.isin(self.i2i.index)].copy()
        df["uidx"] = self.u2i.loc[df.user_id].values
        df["iidx"] = self.i2i.loc[df.item_id].values
        return df

    def csr(self, df: pd.DataFrame, values=None) -> sp.csr_matrix:
        """Matriz usuario×ítem dispersa (binaria por defecto)."""
        v = np.ones(len(df), dtype=np.float32) if values is None else np.asarray(values, dtype=np.float32)
        return sp.csr_matrix((v, (df.uidx.values, df.iidx.values)), shape=(self.n_users, self.n_items))
'''

UTILS_METRICS = r'''
# 🧰 Utilidades del curso (3/3) — métricas top-K. Mismas definiciones que en 02_evaluation.
from typing import Callable, Dict


def test_relevance(test_enc: pd.DataFrame, min_rating: float = 4.0) -> Dict[int, np.ndarray]:
    """uidx → array de iidx relevantes en test (rating ≥ min_rating)."""
    rel = test_enc[test_enc.rating >= min_rating]
    return {u: g.values for u, g in rel.groupby("uidx")["iidx"]}


def topk_from_scores(scores: np.ndarray, seen: sp.csr_matrix, k: int) -> np.ndarray:
    """Top-K por fila excluyendo ítems ya vistos (scores: batch×n_items, seen: batch×n_items)."""
    scores = np.array(scores, dtype=np.float32, copy=True)
    r, c = seen.nonzero()
    scores[r, c] = -np.inf
    part = np.argpartition(-scores, k, axis=1)[:, :k]
    order = np.take_along_axis(scores, part, 1).argsort(axis=1)[:, ::-1]
    return np.take_along_axis(part, order, 1)


def ndcg_recall_at_k(recs: np.ndarray, relevant: list, k: int):
    """NDCG@K y Recall@K (binarios) para cada usuario."""
    discounts = 1.0 / np.log2(np.arange(2, k + 2))
    ndcg, recall = np.zeros(len(recs)), np.zeros(len(recs))
    for n, (rec, rel) in enumerate(zip(recs, relevant)):
        hits = np.isin(rec[:k], rel)
        idcg = discounts[: min(len(rel), k)].sum()
        ndcg[n] = (hits * discounts).sum() / idcg
        recall[n] = hits.sum() / len(rel)
    return ndcg, recall


def evaluate_topk(score_fn: Callable[[np.ndarray], np.ndarray], train_csr: sp.csr_matrix,
                  relevance: Dict[int, np.ndarray], k: int = 10, batch: int = 512) -> Dict[str, float]:
    """Evalúa un modelo dado por score_fn(uidx_batch) -> scores densos (batch×n_items)."""
    users = np.array(sorted(relevance))
    all_recs = []
    for s in range(0, len(users), batch):
        ub = users[s : s + batch]
        all_recs.append(topk_from_scores(score_fn(ub), train_csr[ub], k))
    recs = np.vstack(all_recs)
    ndcg, rec = ndcg_recall_at_k(recs, [relevance[u] for u in users], k)
    return {f"NDCG@{k}": ndcg.mean(), f"Recall@{k}": rec.mean(),
            "Coverage": len(np.unique(recs)) / train_csr.shape[1], "n_users": len(users)}
'''

PIP_NOTE = "Si alguna librería falla al instalar, el notebook sigue: cada sección tiene *fallback*."


def add_utils(nb) -> None:
    """Añade las tres celdas de utilidades a un Notebook de nbbuild."""
    nb.md(UTILS_MD)
    nb.code(UTILS_DATA)
    nb.code(UTILS_SPLIT)
    nb.code(UTILS_METRICS)
