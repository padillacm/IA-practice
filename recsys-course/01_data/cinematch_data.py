"""cinematch_data — pipeline de datos de CineMatch (módulo 01 del curso).

Interfaz estable que reutilizan los módulos posteriores:

    ratings, items = load_movielens("100k")      # o "1m", "latest-small", "25m", "32m"
    users = load_users("100k")                    # demografía (solo 100k y 1m; si no, None)
    inter = to_implicit(ratings, threshold=4.0)   # feedback implícito (rating >= 4)
    inter = filter_k_core(inter, min_user=5, min_item=5)
    train, val, test = temporal_split(inter, val_frac=0.1, test_frac=0.1)
    train, test = leave_one_out_split(inter)      # último ítem de cada usuario a test
    train, test = random_split(inter, test_frac=0.2)
    X, u2i, i2i = to_csr(train)                   # matriz usuario×ítem scipy.sparse
    recs = recommend_popular(train, users=test.user_id.unique(), k=10)
    # recs: dict[user_id -> list[item_id]] ordenado de más a menos recomendado

Convenciones de columnas: user_id (int), item_id (int), rating (float),
timestamp (int, segundos Unix). items: item_id, title, year, genres (str "A|B").

Si la descarga de GroupLens falla (sin red), `load_movielens` genera un dataset
sintético con el mismo esquema (`make_synthetic_movielens`) y avisa.
"""
from __future__ import annotations

import io
import urllib.request
import warnings
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

BASE_URL = "https://files.grouplens.org/datasets/movielens"
SIZES = {
    "100k": "ml-100k",
    "1m": "ml-1m",
    "latest-small": "ml-latest-small",
    "25m": "ml-25m",
    "32m": "ml-32m",
}
GENRES_100K = [
    "unknown", "Action", "Adventure", "Animation", "Children's", "Comedy", "Crime",
    "Documentary", "Drama", "Fantasy", "Film-Noir", "Horror", "Musical", "Mystery",
    "Romance", "Sci-Fi", "Thriller", "War", "Western",
]


# ----------------------------------------------------------------------------
# Descarga y carga
# ----------------------------------------------------------------------------
def download_movielens(size: str = "100k", data_dir: str | Path = "data") -> Path:
    """Descarga y descomprime MovieLens desde GroupLens. Devuelve la carpeta."""
    if size not in SIZES:
        raise ValueError(f"size debe ser uno de {list(SIZES)}")
    name = SIZES[size]
    data_dir = Path(data_dir)
    folder = data_dir / name
    if folder.exists():
        return folder
    data_dir.mkdir(parents=True, exist_ok=True)
    url = f"{BASE_URL}/{name}.zip"
    print(f"Descargando {url} ...")
    with urllib.request.urlopen(url, timeout=60) as resp:
        zipfile.ZipFile(io.BytesIO(resp.read())).extractall(data_dir)
    return folder


def _split_title_year(titles: pd.Series) -> tuple[pd.Series, pd.Series]:
    year = titles.str.extract(r"\((\d{4})\)\s*$")[0].astype("float")
    clean = titles.str.replace(r"\s*\(\d{4}\)\s*$", "", regex=True)
    return clean, year


def _read_folder(size: str, folder: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    if size == "100k":
        ratings = pd.read_csv(folder / "u.data", sep="\t",
                              names=["user_id", "item_id", "rating", "timestamp"])
        cols = ["item_id", "title", "release_date", "video_release_date", "url"] + GENRES_100K
        raw = pd.read_csv(folder / "u.item", sep="|", names=cols, encoding="latin-1")
        flags = raw[GENRES_100K].values.astype(bool)
        genres = ["|".join(g for g, f in zip(GENRES_100K, row) if f) or "unknown" for row in flags]
        items = pd.DataFrame({"item_id": raw["item_id"], "title": raw["title"].fillna(""),
                              "genres": genres})
    elif size == "1m":
        ratings = pd.read_csv(folder / "ratings.dat", sep="::", engine="python",
                              names=["user_id", "item_id", "rating", "timestamp"])
        items = pd.read_csv(folder / "movies.dat", sep="::", engine="python",
                            names=["item_id", "title", "genres"], encoding="latin-1")
    else:
        ratings = pd.read_csv(folder / "ratings.csv").rename(
            columns={"userId": "user_id", "movieId": "item_id"})
        items = pd.read_csv(folder / "movies.csv").rename(columns={"movieId": "item_id"})
    items["title"], items["year"] = _split_title_year(items["title"].astype(str))
    return ratings, items[["item_id", "title", "year", "genres"]]


def load_movielens(size: str = "100k", data_dir: str | Path = "data",
                   synthetic_fallback: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (ratings, items) con el esquema estándar de CineMatch.

    ratings: user_id, item_id, rating (float32), timestamp (int64), ordenado por tiempo.
    items:   item_id, title, year, genres ("Action|Comedy").
    """
    try:
        folder = download_movielens(size, data_dir)
        ratings, items = _read_folder(size, folder)
    except Exception as e:  # sin red, URL caída, etc.
        if not synthetic_fallback:
            raise
        warnings.warn(f"No se pudo descargar MovieLens-{size} ({e!r}). "
                      "Usando datos SINTÉTICOS con el mismo esquema.")
        ratings, items = make_synthetic_movielens()
    ratings = ratings.astype({"user_id": "int64", "item_id": "int64",
                              "rating": "float32", "timestamp": "int64"})
    ratings = ratings.sort_values(["timestamp", "user_id", "item_id"], kind="stable")
    return ratings.reset_index(drop=True), items.reset_index(drop=True)


def load_users(size: str = "100k", data_dir: str | Path = "data") -> pd.DataFrame | None:
    """Demografía de usuarios (user_id, age, gender, occupation). Solo 100k y 1m."""
    try:
        folder = download_movielens(size, data_dir)
    except Exception:
        return None
    if size == "100k":
        return pd.read_csv(folder / "u.user", sep="|",
                           names=["user_id", "age", "gender", "occupation", "zip"])
    if size == "1m":
        return pd.read_csv(folder / "users.dat", sep="::", engine="python",
                           names=["user_id", "gender", "age", "occupation", "zip"])
    return None


def make_synthetic_movielens(n_users: int = 943, n_items: int = 1682,
                             n_ratings: int = 100_000, seed: int = 42
                             ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Dataset sintético con forma de MovieLens: long tail, actividad sesgada,
    gustos latentes por género y deriva temporal (los ítems nuevos van llegando)."""
    rng = np.random.default_rng(seed)
    genres = GENRES_100K[1:]
    t0, t1 = 874_724_710, 893_286_638  # mismo rango temporal que ML-100K
    # Ítems: género principal, popularidad intrínseca (Zipf) y fecha de llegada
    item_genre = rng.integers(0, len(genres), n_items)
    item_pop = 1.0 / np.arange(1, n_items + 1) ** 1.1
    rng.shuffle(item_pop)
    item_arrival = t0 + (t1 - t0) * np.where(rng.random(n_items) < 0.5, 0.0,
                                             rng.uniform(0, 0.95, n_items))  # catálogo inicial + estrenos
    # Usuarios: actividad log-normal, afinidad por géneros y fecha de alta
    activity = rng.lognormal(0, 1.0, n_users)
    activity = np.maximum(20, activity / activity.sum() * n_ratings).astype(int)
    taste = rng.dirichlet(np.full(len(genres), 0.3), n_users)
    user_start = t0 + (t1 - t0) * rng.uniform(0, 0.9, n_users)
    item_quality = rng.normal(0, 0.45, n_items)   # unas películas son mejores que otras
    user_bias = rng.normal(0, 0.35, n_users)      # hay usuarios generosos y exigentes
    rows = []
    for u in range(n_users):
        start = user_start[u]
        end = min(t1, start + rng.uniform(1, 120) * 86_400)
        avail = item_arrival <= end
        n = int(min(activity[u], avail.sum() // 2))
        ts = np.sort(rng.uniform(start, end, n))
        age_days = np.maximum(0, end - item_arrival) / 86_400
        hype = np.where(item_arrival > t0, 1 + 30 * np.exp(-age_days / 30), 1.0)  # los estrenos tienen su momento
        w = item_pop * hype * (0.15 + taste[u][item_genre]) * avail
        chosen = rng.choice(n_items, size=n, replace=False, p=w / w.sum())
        ts = np.maximum(ts, item_arrival[chosen] + 3600)
        aff = taste[u][item_genre[chosen]] * len(genres)
        r = np.clip(np.round(3.2 + 0.6 * np.log1p(aff) + item_quality[chosen] + user_bias[u]
                             + rng.normal(0, 0.7, n)), 1, 5)
        rows.append(pd.DataFrame({"user_id": u + 1, "item_id": chosen + 1,
                                  "rating": r, "timestamp": ts.astype(np.int64)}))
    ratings = pd.concat(rows, ignore_index=True)
    second = rng.integers(0, len(genres), n_items)
    items = pd.DataFrame({
        "item_id": np.arange(1, n_items + 1),
        "title": [f"Película sintética {i}" for i in range(1, n_items + 1)],
        "year": (1930 + 66 * rng.beta(4, 1.5, n_items)).round(),
        "genres": [genres[a] if a == b else f"{genres[a]}|{genres[b]}"
                   for a, b in zip(item_genre, second)],
    })
    return ratings, items


# ----------------------------------------------------------------------------
# Limpieza y señales
# ----------------------------------------------------------------------------
def to_implicit(ratings: pd.DataFrame, threshold: float = 4.0) -> pd.DataFrame:
    """Convierte ratings explícitos en interacciones implícitas positivas
    (rating >= threshold). Mantiene la columna rating por si se quiere ponderar."""
    out = ratings[ratings["rating"] >= threshold].copy()
    return out.reset_index(drop=True)


def dedup_interactions(df: pd.DataFrame, keep: str = "last") -> pd.DataFrame:
    """Elimina pares (usuario, ítem) duplicados quedándose con el primero/último en el tiempo."""
    return (df.sort_values("timestamp", kind="stable")
              .drop_duplicates(["user_id", "item_id"], keep=keep)
              .reset_index(drop=True))


def filter_k_core(df: pd.DataFrame, min_user: int = 5, min_item: int = 5,
                  max_iter: int = 100) -> pd.DataFrame:
    """k-core iterativo: repite hasta que todo usuario tenga >= min_user
    interacciones y todo ítem >= min_item (filtrar uno puede romper el otro)."""
    for _ in range(max_iter):
        n0 = len(df)
        ic = df["item_id"].map(df["item_id"].value_counts())
        df = df[ic >= min_item]
        uc = df["user_id"].map(df["user_id"].value_counts())
        df = df[uc >= min_user]
        if len(df) == n0:
            break
    return df.reset_index(drop=True)


# ----------------------------------------------------------------------------
# Splits
# ----------------------------------------------------------------------------
def _drop_cold(train: pd.DataFrame, other: pd.DataFrame, users: bool, items: bool) -> pd.DataFrame:
    if users:
        other = other[other["user_id"].isin(train["user_id"].unique())]
    if items:
        other = other[other["item_id"].isin(train["item_id"].unique())]
    return other.reset_index(drop=True)


def random_split(df: pd.DataFrame, test_frac: float = 0.2, seed: int = 42,
                 drop_cold: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split aleatorio de interacciones (¡filtra el futuro al train! solo como contraejemplo)."""
    mask = np.random.default_rng(seed).random(len(df)) < test_frac
    train, test = df[~mask].reset_index(drop=True), df[mask]
    return train, _drop_cold(train, test, drop_cold, drop_cold)


def leave_one_out_split(df: pd.DataFrame, n_test: int = 1, min_train: int = 1
                        ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Las últimas n_test interacciones (en el tiempo) de cada usuario van a test.
    Ojo: no hay un corte temporal global → el train de un usuario puede contener
    interacciones posteriores al test de otro (leakage temporal entre usuarios)."""
    df = df.sort_values(["user_id", "timestamp"], kind="stable")
    rank_from_end = df.groupby("user_id").cumcount(ascending=False)
    n_user = df.groupby("user_id")["item_id"].transform("size")
    is_test = (rank_from_end < n_test) & (n_user >= n_test + min_train)
    return df[~is_test].reset_index(drop=True), df[is_test].reset_index(drop=True)


def temporal_split(df: pd.DataFrame, val_frac: float = 0.1, test_frac: float = 0.1,
                   drop_cold_users: bool = True, drop_cold_items: bool = True
                   ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split temporal GLOBAL: train = pasado, val = siguiente val_frac del tiempo
    (por cuantiles de eventos), test = último test_frac. Es lo más parecido a
    producción: entrenas con todo lo anterior a T y sirves después de T.
    Devuelve (train, val, test); val puede estar vacío si val_frac == 0."""
    ts = df["timestamp"]
    t_test = ts.quantile(1 - test_frac)
    t_val = ts.quantile(1 - test_frac - val_frac) if val_frac > 0 else t_test
    train = df[ts < t_val].reset_index(drop=True)
    val = df[(ts >= t_val) & (ts < t_test)]
    test = df[ts >= t_test]
    val = _drop_cold(train, val, drop_cold_users, drop_cold_items)
    # Para test, "conocido" = visto en train o val (en producción reentrenas antes de servir)
    seen = pd.concat([train, val])
    test = _drop_cold(seen, test, drop_cold_users, drop_cold_items)
    return train, val, test


# ----------------------------------------------------------------------------
# Matrices dispersas
# ----------------------------------------------------------------------------
def build_mappings(df: pd.DataFrame) -> tuple[dict, dict]:
    """Mapeos id original -> índice contiguo 0..n-1 (usuarios e ítems)."""
    users = np.sort(df["user_id"].unique())
    items = np.sort(df["item_id"].unique())
    return ({u: i for i, u in enumerate(users)}, {it: j for j, it in enumerate(items)})


def to_csr(df: pd.DataFrame, user2idx: dict | None = None, item2idx: dict | None = None,
           value_col: str | None = None) -> tuple[sp.csr_matrix, dict, dict]:
    """Matriz usuario×ítem CSR. value_col=None → 1.0 por interacción (implícito).
    Las filas/ítems fuera del mapeo se descartan. Devuelve (X, user2idx, item2idx)."""
    if user2idx is None or item2idx is None:
        user2idx, item2idx = build_mappings(df)
    r = df["user_id"].map(user2idx)
    c = df["item_id"].map(item2idx)
    ok = r.notna() & c.notna()
    vals = np.ones(ok.sum(), dtype=np.float32) if value_col is None \
        else df.loc[ok, value_col].to_numpy(np.float32)
    X = sp.csr_matrix((vals, (r[ok].astype(int), c[ok].astype(int))),
                      shape=(len(user2idx), len(item2idx)))
    X.sum_duplicates()
    return X, user2idx, item2idx


# ----------------------------------------------------------------------------
# Baselines
# ----------------------------------------------------------------------------
def _seen_by_user(train: pd.DataFrame) -> dict:
    return train.groupby("user_id")["item_id"].agg(set).to_dict()


def _topk_excluding(ranked: np.ndarray, seen: set, k: int) -> list:
    out = []
    for it in ranked:
        if it not in seen:
            out.append(int(it))
            if len(out) == k:
                break
    return out


def popularity_ranking(train: pd.DataFrame, window_days: float | None = None,
                       half_life_days: float | None = None) -> np.ndarray:
    """Ítems ordenados por popularidad. window_days: solo cuenta los últimos N días.
    half_life_days: pondera cada evento por 0.5**(edad/half_life) (recencia suave)."""
    df = train
    t_max = df["timestamp"].max()
    if window_days is not None:
        df = df[df["timestamp"] >= t_max - window_days * 86_400]
    if half_life_days is not None:
        age = (t_max - df["timestamp"]) / 86_400
        w = 0.5 ** (age / half_life_days)
        scores = w.groupby(df["item_id"]).sum()
    else:
        scores = df["item_id"].value_counts()
    return scores.sort_values(ascending=False, kind="stable").index.to_numpy()


def recommend_popular(train: pd.DataFrame, users, k: int = 10, exclude_seen: bool = True,
                      window_days: float | None = None,
                      half_life_days: float | None = None) -> dict:
    """Top-K más populares (opcionalmente recientes) para cada usuario de `users`."""
    ranked = popularity_ranking(train, window_days, half_life_days)
    seen = _seen_by_user(train) if exclude_seen else {}
    return {u: _topk_excluding(ranked, seen.get(u, set()), k) for u in users}


def recommend_popular_by_segment(train: pd.DataFrame, users, segment_of: dict, k: int = 10,
                                 exclude_seen: bool = True, min_segment_events: int = 50) -> dict:
    """Popularidad dentro del segmento del usuario (p. ej. edad, país, género favorito).
    `segment_of`: dict user_id -> segmento. Segmentos con pocos eventos → popularidad global."""
    seg = train["user_id"].map(segment_of)
    global_rank = popularity_ranking(train)
    ranks = {}
    for s, g in train.groupby(seg):
        if len(g) >= min_segment_events:
            r = g["item_id"].value_counts().index.to_numpy()
            # completar con el ranking global para no quedarnos cortos
            ranks[s] = np.concatenate([r, global_rank[~np.isin(global_rank, r)]])
    seen = _seen_by_user(train) if exclude_seen else {}
    return {u: _topk_excluding(ranks.get(segment_of.get(u), global_rank), seen.get(u, set()), k)
            for u in users}


def recommend_random(train: pd.DataFrame, users, k: int = 10, seed: int = 42,
                     exclude_seen: bool = True) -> dict:
    """Recomendador aleatorio: el suelo absoluto de cualquier comparación."""
    rng = np.random.default_rng(seed)
    items = train["item_id"].unique()
    seen = _seen_by_user(train) if exclude_seen else {}
    return {u: _topk_excluding(rng.permutation(items), seen.get(u, set()), k) for u in users}


# ----------------------------------------------------------------------------
# Persistencia
# ----------------------------------------------------------------------------
def save_splits(out_dir: str | Path, **frames: pd.DataFrame) -> Path:
    """Guarda cada DataFrame como parquet: save_splits("data/cinematch", train=..., test=...)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, f in frames.items():
        f.to_parquet(out_dir / f"{name}.parquet", index=False)
    return out_dir


def load_splits(out_dir: str | Path, names=("train", "val", "test", "items")) -> dict:
    out_dir = Path(out_dir)
    return {n: pd.read_parquet(out_dir / f"{n}.parquet") for n in names
            if (out_dir / f"{n}.parquet").exists()}


# ----------------------------------------------------------------------------
# Pipeline completo de CineMatch (una llamada)
# ----------------------------------------------------------------------------
def prepare_cinematch(size: str = "100k", threshold: float | None = 4.0, min_user: int = 5,
                      min_item: int = 5, val_frac: float = 0.1, test_frac: float = 0.1,
                      data_dir: str | Path = "data", out_dir: str | Path | None = None) -> dict:
    """Pipeline estándar del curso:
    carga → dedup → implícito (rating >= threshold; None = no filtrar) → split temporal
    global → k-core SOLO sobre train (no miramos el futuro para filtrar) → val/test
    restringidos a usuarios e ítems conocidos en train.

    Devuelve {"train", "val", "test", "items", "ratings"} (DataFrames) y, si
    out_dir no es None, los guarda en parquet."""
    ratings, items = load_movielens(size, data_dir)
    inter = dedup_interactions(ratings)
    if threshold is not None:
        inter = to_implicit(inter, threshold)
    train, val, test = temporal_split(inter, val_frac, test_frac,
                                      drop_cold_users=False, drop_cold_items=False)
    train = filter_k_core(train, min_user, min_item)
    val = _drop_cold(train, val, True, True)
    test = _drop_cold(train, test, True, True)
    out = {"train": train, "val": val, "test": test, "items": items, "ratings": ratings}
    if out_dir is not None:
        save_splits(out_dir, train=train, val=val, test=test, items=items)
    return out
