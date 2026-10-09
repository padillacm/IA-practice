"""Celdas comunes del Bloque IV (módulos 09, 10, 11).

Las utilidades replican, en versión mínima, lo construido en 01_data y
02_evaluation para que cada notebook sea autocontenido en Colab.
"""

UTILS_MD = r"""
## 🧰 Utilidades mínimas (vienen de los módulos 01 y 02)

Para que este notebook sea **autocontenido en Colab**, copiamos aquí una versión reducida de las utilidades que construimos en
`01_data` (carga de MovieLens, secuencias, *splits*) y `02_evaluation` (HR@K y NDCG@K con *full ranking*).

- Si la descarga falla (sin red, *firewall*…), se generan **datos sintéticos con estructura secuencial** para que el notebook nunca se bloquee. Los números con datos sintéticos **no** son comparables con los papers.
- Convención de IDs: los ítems se re-indexan a `1..n_items` y **el 0 es el *padding***.
"""

UTILS_LOAD = r"""
# ==== Utilidades (versión mínima de 01_data) ====
import os, io, zipfile, urllib.request

ML1M_URL = "https://files.grouplens.org/datasets/movielens/ml-1m.zip"

def make_synthetic_ml(n_users=1500, n_items=700, n_genres=12, seed=42):
    '''Datos de juguete con señal secuencial: "siguiente capítulo", deriva de género y popularidad.'''
    rng = np.random.default_rng(seed)
    genre = rng.integers(0, n_genres, n_items)
    by_genre = [np.where(genre == g)[0] for g in range(n_genres)]
    pop = np.minimum(rng.zipf(1.4, n_items), 60).astype(float); pop /= pop.sum()
    rows = []
    for u in range(1, n_users + 1):
        g = int(rng.integers(n_genres)); it = int(rng.choice(by_genre[g])); t = 978_300_000 + int(rng.integers(0, 10**7))
        for _ in range(int(rng.integers(20, 160))):
            rows.append((u, it + 1, int(rng.integers(3, 6)), t))
            t += int(rng.integers(30, 3 * 86400)); r = rng.random()
            if r < 0.45:   it = (it + int(rng.integers(1, 4))) % n_items          # secuela / siguiente capítulo
            elif r < 0.8:  it = int(rng.choice(by_genre[g]))                       # mismo género
            else:          g = int(rng.integers(n_genres)); it = int(rng.choice(n_items, p=pop))
    ratings = pd.DataFrame(rows, columns=["user", "item", "rating", "ts"]).drop_duplicates(["user", "item"])
    names = ["Action", "Comedy", "Drama", "Horror", "Sci-Fi", "Romance", "Thriller",
             "Animation", "Documentary", "Crime", "Musical", "War"]
    movies = pd.DataFrame({"item": np.arange(1, n_items + 1),
                           "title": [f"Película sintética {i} (2000)" for i in range(1, n_items + 1)],
                           "genres": [names[g % len(names)] for g in genre]})
    return ratings, movies

def load_movielens_1m(data_dir="data"):
    '''Devuelve (ratings[user,item,rating,ts], movies[item,title,genres]).'''
    os.makedirs(data_dir, exist_ok=True)
    zpath = os.path.join(data_dir, "ml-1m.zip")
    try:
        if not os.path.exists(zpath):
            urllib.request.urlretrieve(ML1M_URL, zpath)
        with zipfile.ZipFile(zpath) as z:
            ratings = pd.read_csv(z.open("ml-1m/ratings.dat"), sep="::", engine="python",
                                  names=["user", "item", "rating", "ts"])
            movies = pd.read_csv(z.open("ml-1m/movies.dat"), sep="::", engine="python",
                                 names=["item", "title", "genres"], encoding="latin-1")
        return ratings, movies
    except Exception as e:
        if os.path.exists(zpath):
            os.remove(zpath)
        print(f"⚠️ No se pudo descargar MovieLens-1M ({type(e).__name__}). Uso datos SINTÉTICOS.")
        return make_synthetic_ml()
"""

UTILS_SEQ = r"""
# ==== Secuencias y split leave-one-out (01_data) ====
def build_sequences(ratings, min_len=5):
    '''Ordena por tiempo y devuelve (seqs: list[list[int]], item2idx, idx2item). 0 = padding.'''
    df = ratings.sort_values(["user", "ts"], kind="mergesort")      # estable: respeta el orden del fichero en empates
    cnt = df.groupby("user")["item"].transform("size")
    df = df[cnt >= min_len]
    items = np.sort(df["item"].unique())
    item2idx = {it: i + 1 for i, it in enumerate(items)}
    idx2item = np.concatenate([[0], items])
    df = df.assign(iidx=df["item"].map(item2idx))
    seqs = df.groupby("user", sort=True)["iidx"].apply(list).tolist()
    return seqs, item2idx, idx2item

def leave_one_out(seqs):
    '''train = s[:-2]; valid: (s[:-2] -> s[-2]); test: (s[:-1] -> s[-1]).'''
    train = [s[:-2] for s in seqs]
    valid = ([s[:-2] for s in seqs], [s[-2] for s in seqs])
    test = ([s[:-1] for s in seqs], [s[-1] for s in seqs])
    return train, valid, test

def pad_left(seqs, maxlen):
    '''Trunca a los últimos `maxlen` y rellena con 0 por la izquierda -> LongTensor [B, maxlen].'''
    out = np.zeros((len(seqs), maxlen), dtype=np.int64)
    for i, s in enumerate(seqs):
        s = s[-maxlen:]
        if len(s):
            out[i, -len(s):] = s
    return torch.from_numpy(out)
"""

UTILS_EVAL = r"""
# ==== Métricas HR@K / NDCG@K con full ranking (02_evaluation) ====
@torch.no_grad()
def evaluate_next_item(score_fn, histories, targets, ks=(10,), batch_size=512, mask_history=True):
    '''score_fn(list[list[int]]) -> Tensor [B, n_items+1] con puntuaciones de TODOS los ítems.
    Ranking completo (sin negativos muestreados, ver Krichene & Rendle 2020). Una sola relevante => HR = Recall.'''
    ranks = []
    for b in range(0, len(histories), batch_size):
        H, T = histories[b:b + batch_size], torch.as_tensor(targets[b:b + batch_size])
        s = score_fn(H).float().cpu()
        tgt = s.gather(1, T[:, None]).clone()
        s[:, 0] = -float("inf")                                # padding
        if mask_history:                                       # no recomendar lo ya visto
            for i, h in enumerate(H):
                s[i, h[0] if isinstance(h, tuple) else h] = -float("inf")   # h puede ser (items, timestamps)
        s.scatter_(1, T[:, None], tgt)                         # el objetivo nunca se enmascara
        ranks.append((s > tgt).sum(1))                         # posición 0-based (empates optimistas)
    ranks = torch.cat(ranks).numpy()
    out = {}
    for k in ks:
        hit = ranks < k
        out[f"HR@{k}"] = float(hit.mean())
        out[f"NDCG@{k}"] = float((hit / np.log2(ranks + 2)).mean())
    return out
"""

# --- Utilidades para recomendación top-K no secuencial (módulo 10) ---
UTILS_TOPK = r"""
# ==== Split temporal por usuario y Recall/NDCG@K multi-relevante (01 y 02) ====
import scipy.sparse as sp

def temporal_user_split(df, test_frac=0.2):
    '''Para cada usuario, el último `test_frac` de sus interacciones (por tiempo) va a test.'''
    df = df.sort_values(["u", "ts"], kind="mergesort")
    rank = df.groupby("u").cumcount()
    n = df.groupby("u")["i"].transform("size")
    is_test = rank >= np.ceil(n * (1 - test_frac))
    return df[~is_test].reset_index(drop=True), df[is_test].reset_index(drop=True)

def to_csr(df, n_users, n_items):
    return sp.csr_matrix((np.ones(len(df), dtype=np.float32), (df.u.values, df.i.values)), shape=(n_users, n_items))

@torch.no_grad()
def evaluate_topk(score_fn, train_csr, test_csr, k=20, batch_size=1024):
    '''score_fn(user_ids LongTensor) -> Tensor [B, n_items]. Enmascara train. Devuelve Recall@K y NDCG@K medios.'''
    users = np.where(np.asarray((test_csr > 0).sum(1)).ravel() > 0)[0]
    rec, ndcg = [], []
    disc = 1.0 / np.log2(np.arange(2, k + 2))
    for b in range(0, len(users), batch_size):
        u = users[b:b + batch_size]
        s = score_fn(torch.as_tensor(u)).float().cpu().numpy()
        s[train_csr[u].nonzero()] = -np.inf                     # no recomendar lo visto en train
        top = np.argpartition(-s, k, axis=1)[:, :k]
        top = np.take_along_axis(top, np.argsort(-np.take_along_axis(s, top, 1), 1), 1)
        te = test_csr[u].toarray() > 0
        hits = np.take_along_axis(te, top, 1)
        n_rel = te.sum(1)
        rec.append(hits.sum(1) / n_rel)
        idcg = np.array([disc[:min(int(r), k)].sum() for r in n_rel])
        ndcg.append((hits * disc).sum(1) / idcg)
    return {f"Recall@{k}": float(np.concatenate(rec).mean()), f"NDCG@{k}": float(np.concatenate(ndcg).mean())}
"""
