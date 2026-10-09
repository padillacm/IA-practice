"""Builder del módulo 18 · Capstone CineMatch + guía de élite (lección + proyecto).

Ejecutar desde la raíz del repo:  python recsys-course/_tools/builders/build_18.py
Reutiliza las celdas de datos del módulo 16 (mismo esquema MovieLens) para no divergir.
"""
import os
import sys

sys.path.insert(0, "recsys-course/_tools")
sys.path.insert(0, "recsys-course/_tools/builders")
from nbbuild import Notebook  # noqa: E402
from build_16 import DATA_CELL, SCALE_CELL  # noqa: E402

MOD = "recsys-course/18_capstone"
os.makedirs(MOD, exist_ok=True)

# ---------------------------------------------------------------------------
# Celdas compartidas: split, fuentes de candidatos, features, ranker, MMR
# ---------------------------------------------------------------------------
CORE_CELL = r'''
import faiss, lightgbm as lgb
import scipy.sparse as sp
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds

N_USERS, N_ITEMS = int(ratings.user_id.max()) + 1, int(items_df.item_id.max()) + 1
GENRE_MAT = np.zeros((N_ITEMS, len(GENRES)), dtype=np.float32)
GENRE_MAT[items_df.item_id.values] = items_df[GENRES].values
GNORM = np.linalg.norm(GENRE_MAT, axis=1) + 1e-8
TITLES = dict(zip(items_df.item_id, items_df.title))

# Split temporal GLOBAL (módulo 01): 70 % entrenar fuentes · 10 % etiquetas del ranker · 20 % test
t_a, t_b = ratings.ts.quantile([0.7, 0.8]).values
train_a, train_b, test = ratings[ratings.ts < t_a], ratings[(ratings.ts >= t_a) & (ratings.ts < t_b)], ratings[ratings.ts >= t_b]
hist_a = train_a.groupby("user_id").item_id.apply(list).to_dict()
hist_b = ratings[ratings.ts < t_b].groupby("user_id").item_id.apply(list).to_dict()
lab_b = train_b.groupby("user_id").item_id.apply(set).to_dict()
test_pos = test.groupby("user_id").item_id.apply(set).to_dict()


def binary_matrix(df):
    d = df.drop_duplicates(["user_id", "item_id"])
    return csr_matrix((np.ones(len(d), np.float32), (d.user_id, d.item_id)), shape=(N_USERS, N_ITEMS))


def topk_cosine_cooc(X, k=200, block=1024):
    """Item-kNN coseno DISPERSO: guarda solo los k vecinos más similares de cada ítem.

    Una matriz densa N×N no escala: con ml-latest-small los movieId llegan a ~193.000 (≈150 GB en float32) y con
    ~10⁴ ítems reales ya son cientos de MB que además se copian a MLflow. Calculamos XᵀX por bloques de filas
    (siempre disperso) y truncamos a top-k por fila → memoria O(N·k). Es lo que hace cualquier item-kNN en producción."""
    n = np.sqrt(np.asarray(X.sum(0)).ravel()).astype(np.float32) + 1e-8
    XT = X.T.tocsr()
    active = np.where(np.diff(XT.indptr) > 0)[0]
    R, C, V = [], [], []
    for s0 in range(0, len(active), block):
        rows = active[s0:s0 + block]
        B = (XT[rows] @ X).tocsr()                          # bloque × N_ITEMS, disperso
        for r, i in enumerate(rows):
            a, b = B.indptr[r], B.indptr[r + 1]
            c, v = B.indices[a:b], B.data[a:b] / (n[i] * n[B.indices[a:b]])
            keep = c != i
            c, v = c[keep], v[keep]
            if len(v) > k:
                sel = np.argpartition(-v, k)[:k]; c, v = c[sel], v[sel]
            R.append(np.full(len(c), i)); C.append(c); V.append(v)
    R, C, V = (np.concatenate(x) if x else np.array([]) for x in (R, C, V))
    return csr_matrix((V.astype(np.float32), (R, C)), shape=X.shape[1:] * 2)


def cooc_scores(cooc, hist, seen, k):
    """Suma de similitudes de los últimos 50 ítems → top-k ítems con score > 0 (no vistos, sin el padding 0)."""
    cs = np.asarray(cooc[hist[-50:]].sum(0)).ravel()
    cs[list(seen)] = 0; cs[0] = 0
    nz = np.flatnonzero(cs > 0)
    top = nz[np.argsort(-cs[nz])[:k]]
    return top, cs


class Sources:
    """Generación de candidatos multi-fuente (módulos 04, 05, 08): embeddings+FAISS, co-ocurrencia y popularidad reciente."""

    def __init__(self, df, dim=64, item_emb=None):
        X = binary_matrix(df)
        if item_emb is None:                                    # PureSVD (Cremonesi 2010) si no nos dan two-tower
            _, s, vt = svds(X, k=dim, random_state=seed)
            item_emb = (vt.T * np.sqrt(s)).astype(np.float32)
        self.emb = item_emb / (np.linalg.norm(item_emb, axis=1, keepdims=True) + 1e-8)
        self.index = faiss.IndexHNSWFlat(self.emb.shape[1], 32, faiss.METRIC_INNER_PRODUCT)
        self.index.hnsw.efSearch = 128
        self.index.add(self.emb)
        self.cooc = topk_cosine_cooc(X)                        # item-kNN coseno top-200 (Linden et al. 2003), disperso
        recent = df[df.ts >= df.ts.max() - 30 * 86400]
        self.pop = recent.item_id.value_counts().index.to_numpy()

    def ann(self, hist, k):
        v = self.emb[hist[-50:]].mean(0, keepdims=True)
        v /= np.linalg.norm(v) + 1e-8
        s, i = self.index.search(v.astype(np.float32), k + len(hist))
        return i[0], s[0]

    def candidates(self, hist, k=100):
        """Devuelve {item: dict de features de fuente}. Unión de las tres fuentes (deduplicada)."""
        seen, out = set(hist), {}
        ids, sc = self.ann(hist, k)
        for r, (i, s) in enumerate([(i, s) for i, s in zip(ids, sc) if i not in seen and i > 0][:k]):
            out.setdefault(int(i), {})["ann_score"], out[int(i)]["ann_rank"] = float(s), r
        top, cs = cooc_scores(self.cooc, hist, seen, k)
        for r, i in enumerate(top):
            out.setdefault(int(i), {})["cooc_score"], out[int(i)]["cooc_rank"] = float(cs[i]), r
        for r, i in enumerate([i for i in self.pop if i not in seen][: k // 2]):
            out.setdefault(int(i), {})["pop_rank"] = r
        return out


SRC_FEATS = ["ann_score", "ann_rank", "cooc_score", "cooc_rank", "pop_rank"]
SRC_DEFAULT = {"ann_score": -1.0, "ann_rank": 999, "cooc_score": 0.0, "cooc_rank": 999, "pop_rank": 999}
'''

FEAT_CELL = r'''
def item_stats_asof(t_cut):
    d = ratings[ratings.ts < t_cut]
    g = d.groupby("item_id")
    st = pd.DataFrame({"pop_cum": g.size(), "rating_mean": g.rating.mean(), "first_ts": g.ts.min(),
                       "pop_30d": d[d.ts >= t_cut - 30 * 86400].item_id.value_counts()})
    st = st.reindex(range(N_ITEMS))
    st["item_age_days"] = ((t_cut - st.first_ts) / 86400).fillna(-1)
    return st.fillna({"pop_cum": 0, "rating_mean": 3.0, "pop_30d": 0}).drop(columns="first_ts")


def user_stats_asof(t_cut):
    d = ratings[ratings.ts < t_cut]; g = d.groupby("user_id")
    prof = pd.DataFrame({"user_n": g.size().astype(float), "user_mean": g.rating.mean(),
                         "user_days_since_last": (t_cut - g.ts.max()) / 86400})
    gen = pd.DataFrame(GENRE_MAT[d.item_id.values], index=d.user_id.values).groupby(level=0).mean()
    gen = gen.div(np.linalg.norm(gen.values, axis=1) + 1e-8, axis=0)
    return prof, gen


RANK_FEATS = SRC_FEATS + ["n_sources", "pop_cum", "pop_30d", "rating_mean", "item_age_days",
                          "genre_affinity", "user_n", "user_mean", "user_days_since_last"]


def build_frame(src, hist, users, t_cut, k=100, labels=None):
    """Candidatos + features POINT-IN-TIME (todo calculado con datos < t_cut)."""
    ist = item_stats_asof(t_cut); prof, gen = user_stats_asof(t_cut)
    rows = []
    for u in users:
        if u not in hist or u not in prof.index:
            continue
        cands = src.candidates(hist[u], k)
        ids = np.fromiter(cands, dtype=int)
        f = pd.DataFrame([{**SRC_DEFAULT, **cands[i]} for i in ids])
        f["n_sources"] = [len(cands[i]) // 2 + ("pop_rank" in cands[i]) for i in ids]
        f["user_id"], f["item_id"] = u, ids
        f["genre_affinity"] = GENRE_MAT[ids] @ gen.loc[u].values / GNORM[ids]
        for c in ["user_n", "user_mean", "user_days_since_last"]:
            f[c] = prof.loc[u, c]
        rows.append(f)
    out = pd.concat(rows, ignore_index=True).join(ist, on="item_id")
    if labels is not None:
        out["label"] = [int(i in labels.get(u, ())) for u, i in zip(out.user_id, out.item_id)]
    return out


def train_lambdamart(frame, n_estimators=200):
    """LambdaMART regularizado (pocas hojas, hojas grandes): con pocos miles de usuarios etiquetados sobreajusta enseguida.
    Agrupa por `qid` (usuario × ventana) si existe; si no, por usuario."""
    key = "qid" if "qid" in frame else "user_id"
    f = frame[frame.groupby(key).label.transform("max") > 0].sort_values(key)
    m = lgb.LGBMRanker(objective="lambdarank", n_estimators=n_estimators, learning_rate=0.05, num_leaves=15,
                       min_child_samples=100, subsample=0.8, subsample_freq=1, colsample_bytree=0.8, verbose=-1, random_state=seed, n_jobs=LGB_THREADS)
    m.fit(f[RANK_FEATS], f.label, group=f.groupby(key, sort=False).size().values)
    return m


def multi_window_frames(make_src, quantiles=(0.5, 0.6, 0.7, 0.8), k=100):
    """Más ejemplos para el ranker SIN romper el protocolo temporal: para cada ventana [q_i, q_{i+1}) las fuentes y
    features se construyen solo con datos < q_i y las etiquetas son lo visto en la ventana. `make_src(df)` → fuentes."""
    frames = []
    for lo_q, hi_q in zip(quantiles[:-1], quantiles[1:]):
        lo, hi = ratings.ts.quantile([lo_q, hi_q]).values
        past, win = ratings[ratings.ts < lo], ratings[(ratings.ts >= lo) & (ratings.ts < hi)]
        hist = past.groupby("user_id").item_id.apply(list).to_dict()
        lab = win.groupby("user_id").item_id.apply(set).to_dict()
        fr = build_frame(make_src(past), hist, [u for u in lab if u in hist], lo, k, labels=lab)
        fr["qid"] = fr.user_id.astype(str) + f"@{lo_q}"
        frames.append(fr)
    return pd.concat(frames, ignore_index=True)


def ndcg_at_k(ranked, relevant, k=10):
    dcg = sum(1.0 / np.log2(r + 2) for r, i in enumerate(ranked[:k]) if i in relevant)
    idcg = sum(1.0 / np.log2(r + 2) for r in range(min(k, len(relevant))))
    return dcg / idcg if idcg else 0.0


def mmr(items, scores, emb, k=10, lam=0.7):
    """Maximal Marginal Relevance (Carbonell & Goldstein 1998; módulo 13): λ·relevancia − (1−λ)·máx similitud."""
    items = list(items)
    rel = (scores - scores.min()) / (np.ptp(scores) + 1e-9)
    chosen, cand = [], list(range(len(items)))
    E = emb[np.asarray(items)]
    while cand and len(chosen) < k:
        if chosen:
            sim = (E[cand] @ E[chosen].T).max(1)
        else:
            sim = np.zeros(len(cand))
        best = cand[int(np.argmax(lam * rel[cand] - (1 - lam) * sim))]
        chosen.append(best); cand.remove(best)
    return [items[c] for c in chosen]


def ild(items, emb):
    """Intra-list diversity: 1 − similitud coseno media entre pares."""
    E = emb[np.asarray(items)]; S = E @ E.T; n = len(items)
    return float(1 - (S.sum() - np.trace(S)) / (n * (n - 1)))
'''


def lesson() -> None:
    path = f"{MOD}/18_capstone.ipynb"
    nb = Notebook("Módulo 18 · Capstone CineMatch y guía de élite", colab_path=path)
    M, C = nb.md, nb.code

    M(f"""
    {nb.badge()}

    # Módulo 18 · Capstone: CineMatch de punta a punta + lo que solo sabe la élite

    **Nivel:** 🔴 Experto · **Duración:** 6–8 h (lección) + 15–25 h (proyecto capstone) · **GPU:** opcional (T4 para el two-tower del proyecto) · **Unidades Colab:** 2–10

    **Prerrequisitos:** todo el curso (00–17). Este módulo no introduce técnicas nuevas: las **integra**, enseña a
    **defenderlas** en una entrevista de *system design* y te deja un mapa para seguir creciendo.

    ## 🎯 Objetivos de aprendizaje

    1. **Integrar** en un solo sistema datos → retrieval multi-fuente → ranking → re-ranking → serving → monitoreo → reentreno.
    2. **Diagnosticar** un sistema multi-etapa midiendo la métrica correcta en cada etapa (recall del funnel, NDCG del ranker, diversidad tras re-ranking, latencia por etapa).
    3. **Aplicar** ≥ 30 lecciones concretas de practicantes de élite y saber de qué paper/blog sale cada una.
    4. **Resolver** entrevistas de system design de recsys con un marco de 10 pasos y cálculos *back-of-the-envelope* (home de Netflix, feed de YouTube/TikTok, People You May Know).
    5. **Planificar** tu lectura de ~40 papers canónicos por etapa y tu ruta de carrera en ML de recomendación.

    ## Índice
    1. El mapa: CineMatch y los 18 módulos
    2. *Walking skeleton* end-to-end ejecutable (la columna vertebral del proyecto)
    3. 🧠 Lo que solo sabe la élite (compendio)
    4. Guía de entrevistas de *system design* (marco + 3 casos resueltos con diagramas)
    5. Mapa de lectura: ~40 papers canónicos por etapa
    6. Conferencias, blogs y comunidades
    7. Ruta de carrera
    8. Autoevaluación y referencias
    """)

    M(r"""
    ## 💡 1. El mapa: cómo encaja todo

    CineMatch es el producto que has ido construyendo. Cada caja del diagrama es un módulo del curso; las flechas son
    contratos (datos, artefactos, APIs). La pregunta de este capstone es: **¿funciona el sistema completo, y sabes
    explicar por qué cada pieza está ahí?**
    """)

    C(r'''
    !pip install -q faiss-cpu lightgbm fastapi uvicorn requests pyarrow
    ''')
    C(DATA_CELL)
    C(SCALE_CELL)

    C(r'''
    def draw(boxes, edges, title, figsize=(14, 6.5), xlim=(0, 14), ylim=(0, 7)):
        """boxes: {clave: (x, y, w, h, texto, color)} · edges: [(a, b, etiqueta)]"""
        fig, ax = plt.subplots(figsize=figsize); ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.axis("off")
        for k, (x, y, w, h, t, c) in boxes.items():
            ax.add_patch(mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03", fc=c, ec="k", lw=1))
            ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=8.5)
        for a, b, lab in edges:
            xa, ya, wa, ha, *_ = boxes[a]; xb, yb, wb, hb, *_ = boxes[b]
            pa, pb = (xa + wa / 2, ya + ha / 2), (xb + wb / 2, yb + hb / 2)
            # salir/entrar por el borde más cercano
            if abs(pa[0] - pb[0]) > abs(pa[1] - pb[1]):
                pa = (xa + wa, pa[1]) if pb[0] > pa[0] else (xa, pa[1]); pb = (xb, pb[1]) if pb[0] > pa[0] else (xb + wb, pb[1])
            else:
                pa = (pa[0], ya + ha) if pb[1] > pa[1] else (pa[0], ya); pb = (pb[0], yb) if pb[1] > pa[1] else (pb[0], yb + hb)
            ax.annotate("", xy=pb, xytext=pa, arrowprops=dict(arrowstyle="->", lw=1.2, color="#34495e"))
            if lab:
                ax.text((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2 + 0.1, lab, fontsize=7, ha="center", color="#7d3c98")
        ax.set_title(title, fontsize=12); plt.show()


    B, G, O, R, P, Y = "#d6eaf8", "#d5f5e3", "#fdebd0", "#fadbd8", "#e8daef", "#fcf3cf"
    draw({
        "ev": (0.2, 5.6, 2.2, 0.9, "Eventos (Kafka)\nmód. 16", B), "lake": (0.2, 4.2, 2.2, 0.9, "Data lake + splits\nmód. 01", B),
        "fs": (0.2, 2.8, 2.2, 0.9, "Feature store PIT\n(Feast) mód. 16", B), "val": (0.2, 1.4, 2.2, 0.9, "Validación datos\nmód. 17", B),
        "ret": (3.2, 5.0, 2.6, 1.3, "Retrieval multi-fuente\nCF (04-05) · two-tower (08)\nsecuencial (09) · grafo (10)\ngenerativo (11)", G),
        "rank": (6.4, 5.0, 2.4, 1.3, "Ranking\nCTR/LTR (06-07)\nmulti-tarea MMoE", O),
        "rr": (9.4, 5.0, 2.3, 1.3, "Re-ranking\ndiversidad/calibración\n(13) · bandits (14)", R),
        "api": (12.2, 5.0, 1.6, 1.3, "API\nFastAPI\n(16)", P),
        "agent": (12.2, 2.9, 1.6, 1.3, "Agente\nconversacional\nLLM (12)", P),
        "eval": (3.2, 2.6, 2.6, 1.2, "Evaluación offline\n(02) + OPE (14)", Y),
        "ab": (6.4, 2.6, 2.4, 1.2, "A/B + interleaving\n(15)", Y),
        "mon": (9.4, 2.6, 2.3, 1.2, "Monitoreo + drift\n(17)", Y),
        "ct": (6.4, 0.6, 2.4, 1.1, "Reentreno CT\nMLflow + Prefect (17)", Y),
        "llm": (3.2, 0.6, 2.6, 1.1, "LLM: metadatos, cold\nstart, LLM-judge (12)", G),
    }, [("ev", "lake", ""), ("lake", "fs", ""), ("fs", "val", ""), ("lake", "ret", "entrena"), ("ret", "rank", "~1000→100"),
        ("rank", "rr", "100→20"), ("rr", "api", "10"), ("api", "agent", "tools"), ("api", "mon", "logs"), ("mon", "ct", "trigger"),
        ("ct", "ret", ""), ("eval", "ab", "candidatos"), ("ab", "rr", ""), ("llm", "ret", "")],
        "CineMatch: arquitectura final y módulos del curso que la componen")
    ''')

    M(r"""
    ## 2. *Walking skeleton*: el sistema completo en miniatura

    Un *walking skeleton* (término de Alistair Cockburn) es la versión mínima que recorre **todas** las capas de punta a
    punta. Es lo primero que construye un equipo sénior: después cada pieza se mejora sin romper el contrato con las
    demás. Aquí cada etapa usa una implementación sencilla pero correcta; el proyecto la sustituye por la versión fuerte.

    | Etapa | Aquí | En el proyecto | Módulo |
    |---|---|---|---|
    | Datos | split temporal global 70/10/20 | ídem + validación Pandera | 01, 17 |
    | Retrieval | PureSVD + FAISS HNSW · item-kNN co-ocurrencia · popularidad 30 días | **two-tower** PyTorch (logQ) + las mismas | 04, 05, 08 |
    | Ranking | LambdaMART (LightGBM) con features *point-in-time*, entrenado en 3 ventanas temporales | ídem + ablación de features | 06, 07, 16 |
    | Re-ranking | MMR (diversidad) | MMR + cuota de novedad | 13 |
    | Serving | función en proceso con perfil de latencia | **FastAPI** + caché + fallback + test de carga | 16 |
    | MLOps | chequeo de drift train→test | **MLflow** champion/challenger + Evidently + decisión de reentreno | 17 |
    | Agente | — | agente con herramientas (Claude API) con fallback sin LLM | 12 |
    """)

    C(CORE_CELL)
    C(FEAT_CELL)

    C(r'''
    t0 = time.time()
    SRC = Sources(train_a)                                   # fuentes entrenadas con datos < t_a
    users_eval = [u for u in test_pos if u in hist_b][:500]
    SRC_B = Sources(ratings[ratings.ts < t_b])               # para servir el test: re-entrenadas hasta t_b
    rec = {"ANN (PureSVD)": [], "Co-ocurrencia": [], "Popularidad 30d": [], "Unión": []}
    sizes = []
    for u in users_eval:
        c = SRC_B.candidates(hist_b[u], 100); tp = test_pos[u]
        rec["ANN (PureSVD)"].append(len({i for i, f in c.items() if "ann_rank" in f} & tp) / len(tp))
        rec["Co-ocurrencia"].append(len({i for i, f in c.items() if "cooc_rank" in f} & tp) / len(tp))
        rec["Popularidad 30d"].append(len({i for i, f in c.items() if "pop_rank" in f} & tp) / len(tp))
        rec["Unión"].append(len(set(c) & tp) / len(tp)); sizes.append(len(c))
    print(f"Fuentes construidas en {time.time() - t0:.1f}s · candidatos medios por usuario: {np.mean(sizes):.0f}")
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.bar(list(rec), [np.mean(v) for v in rec.values()], color=["#5dade2", "#48c9b0", "#f5b041", "#af7ac5"])
    for i, v in enumerate(rec.values()):
        ax.text(i, np.mean(v) + 0.005, f"{np.mean(v):.3f}", ha="center")
    ax.set_ylabel("Recall del conjunto de candidatos"); ax.set_title("Etapa 1 · Recall por fuente de candidatos (≤100 c/u)"); plt.show()
    ''')

    M(r"""
    💡 **Lectura:** ninguna fuente sola cubre lo que el usuario verá; la **unión** sí sube el techo. Este es el motivo de
    que YouTube, X/Twitter o Instagram usen *muchas* fuentes de candidatos: el recall del funnel es el **techo** de todo lo
    que viene después — un ranker perfecto no puede recuperar lo que el retrieval no trajo.
    """)

    C(r'''
    # Ranker entrenado con 3 ventanas temporales [0,5–0,6), [0,6–0,7), [0,7–0,8): más usuarios etiquetados, sin leakage
    fr_tr = multi_window_frames(Sources)
    print("Ejemplos del ranker:", fr_tr.shape, "| grupos (usuario×ventana):", fr_tr.qid.nunique())
    RANKER = train_lambdamart(fr_tr)
    fr_te = build_frame(SRC_B, hist_b, users_eval, t_b)
    fr_te["score"] = RANKER.predict(fr_te[RANK_FEATS])

    res = {"Solo ANN": [], "Solo co-ocurrencia": [], "LambdaMART": [], "LambdaMART + MMR": []}
    div = {"LambdaMART": [], "LambdaMART + MMR": []}
    for u, g in fr_te.groupby("user_id"):
        tp = test_pos[u]
        res["Solo ANN"].append(ndcg_at_k(list(g.sort_values("ann_rank").item_id), tp))
        res["Solo co-ocurrencia"].append(ndcg_at_k(list(g.sort_values("cooc_rank").item_id), tp))
        g = g.sort_values("score", ascending=False)
        top = list(g.item_id[:10]); res["LambdaMART"].append(ndcg_at_k(top, tp)); div["LambdaMART"].append(ild(top, SRC_B.emb))
        rr = mmr(g.item_id.values[:50], g.score.values[:50], SRC_B.emb, k=10, lam=0.8)
        res["LambdaMART + MMR"].append(ndcg_at_k(rr, tp)); div["LambdaMART + MMR"].append(ild(rr, SRC_B.emb))
    summary = pd.DataFrame({"NDCG@10": {k: np.mean(v) for k, v in res.items()}, "ILD@10": {k: np.mean(v) for k, v in div.items()}})
    display(summary.round(4))
    imp = pd.Series(RANKER.booster_.feature_importance("gain"), index=RANK_FEATS).sort_values()
    fig, ax = plt.subplots(1, 2, figsize=(14, 4))
    summary["NDCG@10"].plot.bar(ax=ax[0], color="#5dade2", rot=15); ax[0].set_title("Etapas 2–3 · NDCG@10 en test temporal")
    imp.plot.barh(ax=ax[1], color="#48c9b0"); ax[1].set_title("Importancia (gain) de features del ranker")
    plt.tight_layout(); plt.show()
    ''')

    C(r'''
    # Frontera relevancia-diversidad del re-ranking (módulo 13): barrido de λ en MMR
    lams, pts = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.3], []
    groups = list(fr_te.groupby("user_id"))[:250]
    for lam in lams:
        nd, dv = [], []
        for u, g in groups:
            g = g.sort_values("score", ascending=False)
            rr = mmr(g.item_id.values[:50], g.score.values[:50], SRC_B.emb, k=10, lam=lam)
            nd.append(ndcg_at_k(rr, test_pos[u])); dv.append(ild(rr, SRC_B.emb))
        pts.append((np.mean(dv), np.mean(nd)))
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(*zip(*pts), "o-")
    for lam, (x, y) in zip(lams, pts):
        ax.annotate(f"λ={lam}", (x, y), xytext=(4, 4), textcoords="offset points", fontsize=8)
    ax.set_xlabel("ILD@10 (diversidad)"); ax.set_ylabel("NDCG@10"); ax.set_title("Etapa 4 · Frontera relevancia–diversidad (MMR)")
    plt.show()
    ''')

    C(r'''
    # Etapa 5 · Serving: la función de recomendación completa con perfil de latencia por etapa
    IST_B = item_stats_asof(t_b); PROF_B, GEN_B = user_stats_asof(t_b)
    POPULAR = ratings[ratings.ts < t_b].item_id.value_counts().index[:100].tolist()


    def recommend(u, k=10, lam=0.8):
        tm = {"t0": time.perf_counter()}
        h = hist_b.get(u, [])
        if not h or u not in PROF_B.index:
            return [i for i in POPULAR if i not in set(h)][:k], {"fallback": 0.0}
        cands = SRC_B.candidates(h, 100); tm["retrieval"] = time.perf_counter()
        ids = np.fromiter(cands, dtype=int)
        f = pd.DataFrame([{**SRC_DEFAULT, **cands[i]} for i in ids])
        f["n_sources"] = [len(cands[i]) // 2 + ("pop_rank" in cands[i]) for i in ids]
        f["genre_affinity"] = GENRE_MAT[ids] @ GEN_B.loc[u].values / GNORM[ids]
        for c in ["user_n", "user_mean", "user_days_since_last"]:
            f[c] = PROF_B.loc[u, c]
        f = pd.concat([f, IST_B.loc[ids].reset_index(drop=True)], axis=1); tm["features"] = time.perf_counter()
        s = RANKER.predict(f[RANK_FEATS]); o = np.argsort(-s)[:50]; tm["ranking"] = time.perf_counter()
        out = mmr(ids[o], s[o], SRC_B.emb, k=k, lam=lam); tm["reranking"] = time.perf_counter()
        keys = list(tm); return out, {b: 1e3 * (tm[b] - tm[a]) for a, b in zip(keys, keys[1:])}


    prof = pd.DataFrame([recommend(u)[1] for u in users_eval[:200]])
    fig, ax = plt.subplots(1, 2, figsize=(13, 3.8))
    acc = 0
    for i, c in enumerate(prof.columns):
        v = prof[c].median(); ax[0].bar(i, v, bottom=acc, color="#85c1e9", ec="k"); ax[0].text(i, acc + v / 2, f"{v:.1f}", ha="center", fontsize=8); acc += v
    ax[0].set_xticks(range(prof.shape[1])); ax[0].set_xticklabels(prof.columns); ax[0].set_ylabel("ms (p50 acumulado)")
    ax[0].set_title("Cascada de latencia del skeleton (en proceso, CPU)")
    ax[1].hist(prof.sum(1), bins=30, color="#af7ac5"); ax[1].set_xlabel("ms por petición"); ax[1].set_title("Latencia total")
    plt.tight_layout(); plt.show()
    u0 = users_eval[0]
    print("Historial reciente:", [TITLES.get(i, i) for i in hist_b[u0][-5:]])
    print("Recomendado:", [TITLES.get(i, i) for i in recommend(u0)[0]])
    ''')

    M(r"""
    ⚠️ Observa dónde se va el tiempo: construir el DataFrame de features en pandas por petición es **lento**. En el
    proyecto (y en producción) las features se leen como arrays precomputados (módulo 16) y el ranker recibe una matriz
    NumPy: la latencia baja un orden de magnitud. *Profilea antes de optimizar.*
    """)

    C(r'''
    # Etapa 6 · Monitoreo: ¿cuánto ha derivado el periodo de test respecto al de entrenamiento?
    def psi(ref, cur, bins=10):
        edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
        p = np.histogram(np.clip(ref, edges[0], edges[-1]), edges)[0] / len(ref) + 1e-4
        q = np.histogram(np.clip(cur, edges[0], edges[-1]), edges)[0] / len(cur) + 1e-4
        return float(np.sum((p - q) * np.log(p / q)))


    pop_train = ratings[ratings.ts < t_b].item_id.value_counts()
    checks = {
        "OOV (ítems de test sin historial)": float((~test.item_id.isin(pop_train.index)).mean()),
        "PSI log-popularidad de lo consumido": psi(np.log1p(train_a.item_id.map(pop_train).fillna(0).values),
                                                   np.log1p(test.item_id.map(pop_train).fillna(0).values)),
        "PSI rating": psi(train_a.rating.values.astype(float), test.rating.values.astype(float)),
        "Usuarios de test sin historial (cold start)": float(1 - test.user_id.isin(hist_b.keys()).mean()),
    }
    display(pd.Series(checks).round(4).to_frame("valor"))
    print("Decisión de reentreno (regla del módulo 17):",
          "REENTRENAR" if checks["OOV (ítems de test sin historial)"] > 0.05 or checks["PSI log-popularidad de lo consumido"] > 0.25 else "mantener champion")
    ''')

    M(r"""
    ### 🏭 En producción: el mismo esqueleto, a escala

    - **X/Twitter** (2023, código abierto): fuentes de candidatos in-network y out-of-network (~1500 candidatos), un ranker
      neuronal de ~48M parámetros y una capa de heurísticas/filtros — exactamente el patrón fuentes → ranker → re-ranking.
    - **Instagram Explore** (Meta, 2023): retrieval → first-stage ranking → second-stage ranking → reranking final, con
      two-tower en retrieval y caching/precomputación para permitir modelos más pesados al final.
    - **Netflix** (2013 → 2025): offline/nearline/online; hoy, un foundation model cuyos embeddings consumen los modelos
      downstream vía un *embedding store*.
    - **YouTube** (2016, 2019): candidate generation + ranking; ranking multi-tarea con MMoE y corrección de sesgo de posición.

    ### ⚠️ Errores comunes al integrar
    - Optimizar una etapa con una métrica que no mueve la siguiente (p. ej. recall@1000 cuando el ranker solo ve 100).
    - Entrenar el ranker con candidatos de una versión de retrieval y servirlo con otra (cambia la distribución de entrada).
    - Features calculadas «a mano» en el notebook y reimplementadas en la API (skew): usa un único módulo (lo hace el proyecto).
    - Re-ranking que destruye la relevancia sin medirla: siempre la frontera NDCG–diversidad, nunca un λ a ojo.
    - Medir latencia solo del modelo: la cola la ponen las lecturas de features y la red.
    """)

    # ------------------------------------------------------------------ Elite compendium
    M(r"""
    ## 🧠 3. Lo que solo sabe la élite (compendio)

    Lecciones concretas, cada una con su fuente. Agrupadas por etapa. Si en una entrevista o en un *design review* puedes
    citar y explicar diez de estas, estás en el percentil alto.

    ### Evaluación (lo que separa resultados reales de espejismos)
    1. **Las métricas muestreadas mienten.** Evaluar contra 100 negativos aleatorios puede **invertir** el orden de modelos frente al ranking completo; evalúa con *full ranking* o corrige el estimador. — Krichene & Rendle, *On Sampled Metrics for Item Recommendation*, KDD 2020.
    2. **Muchos modelos neuronales no superan baselines bien ajustados.** De 18 algoritmos de top-conferencias solo 7 eran reproducibles con esfuerzo razonable y 6 de esos 7 fueron superados por métodos simples (kNN, heurísticas) bien tuneados. — Ferrari Dacrema, Cremonesi & Jannach, RecSys 2019 (arXiv:1907.06902).
    3. **El producto escalar le gana al MLP como función de similitud** si ambos se tunean bien; un MLP necesita mucha capacidad para aproximar un dot product y además impide el ANN. — Rendle, Krichene, Zhang & Anderson, *Neural Collaborative Filtering vs. Matrix Factorization Revisited*, RecSys 2020.
    4. **iALS bien regularizado sigue siendo competitivo** con el estado del arte en benchmarks clásicos. — Rendle et al., *Revisiting the Performance of iALS on Item Recommendation Benchmarks*, RecSys 2022.
    5. **EASE (modelo lineal con solución cerrada) es un baseline obligatorio**: segundos de cómputo, resultados de primer nivel en catálogos medianos. — Steck, *Embarrassingly Shallow Autoencoders*, WWW 2019.
    6. **El split aleatorio filtra el futuro.** Con splits no temporales, información posterior entra en el entrenamiento y cambia el ranking de modelos; usa un corte temporal global. — Ji, Sun, Zhang & Li, *A Critical Study on Data Leakage in Recommender System Offline Evaluation*, ACM TOIS 2023.
    7. **SASRec con la pérdida adecuada iguala o supera a BERT4Rec**; muchas «mejoras» venían de la loss (softmax completo vs BCE con un negativo), no de la arquitectura. — Klenitskiy & Vasilev, RecSys 2023; Petrov & Macdonald, *A Systematic Review and Replicability Study of BERT4Rec*, RecSys 2022.
    8. **Los negativos muestreados vuelven al modelo sobreconfiado**; gBCE corrige la calibración de SASRec. — Petrov & Macdonald, *gSASRec*, RecSys 2023.
    9. **Usa GAUC (AUC por usuario ponderado)** cuando el sistema solo ordena dentro de cada usuario; el AUC global mezcla usuarios y no refleja la tarea. — Zhou et al., *Deep Interest Network*, KDD 2018.

    ### Datos y features
    10. **Point-in-time o nada**: features calculadas con datos posteriores al ejemplo inflan la métrica offline; Netflix construyó *time travel* de features (DeLorean) para evitarlo. — Sadekar & Jiang, SysML 2018.
    11. **Loguea las features servidas** y entrena con ellas: elimina la fuente principal de *training-serving skew*. — Google, *Rules of Machine Learning*, regla #29.
    12. **La frescura de los datos es una feature y un hiperparámetro**: en Facebook, pasar de reentrenar semanal a diario mejoró la calidad de forma medible; las features históricas fueron las más importantes. — He et al., *Practical Lessons from Predicting Clicks on Ads at Facebook*, ADKDD 2014.
    13. **«Example age» elimina el sesgo hacia el pasado**: YouTube añade la edad del ejemplo de entrenamiento como feature (y la pone a 0 en serving) para que el modelo aprenda la preferencia por lo fresco. — Covington, Adams & Sargin, RecSys 2016.
    14. **Predice el siguiente consumo, no uno aleatorio retenido**: el consumo es asimétrico (los episodios van en orden); YouTube entrena con el contexto *anterior* al ítem objetivo. — Covington et al., RecSys 2016.
    15. **El sesgo de selección del ranker** (solo ve lo que se mostró/retrajo) se ataca modelando el espacio completo, p. ej. ESMM para CVR. — Ma et al., *Entire Space Multi-Task Model*, SIGIR 2018.

    ### Retrieval
    16. **Corrige el sesgo de muestreo de los negativos in-batch** con la corrección logQ: los ítems populares aparecen más como negativos y se penalizan de más. — Yi et al., *Sampling-Bias-Corrected Neural Modeling for Large Corpus Item Recommendations*, RecSys 2019.
    17. **Mezcla negativos in-batch con negativos uniformes del corpus** (mixed negative sampling) para no ignorar el long tail. — Yang et al., WWW 2020 (companion).
    18. **El recall del funnel es el techo**; usa múltiples fuentes de candidatos y mide el recall de la unión, no solo de cada fuente (lo has visto en §2). Ejemplos públicos: el *Home Mixer* de X mezcla fuentes in-network y out-of-network (2023).
    19. **Las random walks escalan sorprendentemente bien**: Pixie de Pinterest sirve recomendaciones en tiempo real con paseos aleatorios sobre un grafo de miles de millones de nodos en memoria. — Eksombatchai et al., WWW 2018.
    20. **Los embeddings de sesión con el ítem reservado como contexto global** y negativos del mismo mercado mejoran la búsqueda de Airbnb. — Grbovic & Cheng, *Real-time Personalization using Embeddings for Search Ranking at Airbnb*, KDD 2018.

    ### Ranking y objetivos
    21. **Calibra si vas a combinar scores** (fusión multi-objetivo, subastas, umbrales): un ranker puede ordenar bien y estar descalibrado; mide *normalized entropy*/log-loss además del AUC. — He et al., ADKDD 2014.
    22. **Multi-tarea con expertos para evitar transferencia negativa**: MMoE en YouTube (Zhao et al., RecSys 2019) y PLE contra el «efecto balancín» (Tang et al., RecSys 2020).
    23. **Separa el sesgo de posición del modelo de relevancia**: torre superficial de posición en YouTube (2019) o PAL (Guo et al., RecSys 2019); sin ello el modelo aprende «estar arriba ⇒ clic».
    24. **Optimiza satisfacción a largo plazo, no clics**: Netflix describe la recompensa *proxy* de satisfacción a largo plazo y el problema de la recompensa retrasada. — Netflix Tech Blog, *Recommending for Long-Term Member Satisfaction at Netflix*, 2024.

    ### Re-ranking, exploración y experimentación
    25. **La diversidad se modela, no se impone con reglas**: YouTube usó DPP sobre las listas de la home. — Wilhelm et al., *Practical Diversified Recommendations on YouTube with Determinantal Point Processes*, CIKM 2018.
    26. **Calibra la lista a los gustos del usuario** (si ve 70 % drama y 30 % comedia, que la lista lo refleje). — Steck, *Calibrated Recommendations*, RecSys 2018.
    27. **Guarda la propensión de cada impresión**: sin ella no hay off-policy evaluation fiable (IPS/SNIPS/DR) ni corrección de feedback loops. — Saito et al., *Open Bandit Dataset and Pipeline*, NeurIPS D&B 2021; Chen et al., *Top-K Off-Policy Correction for a REINFORCE Recommender System*, WSDM 2019.
    28. **Personalizar la *presentación* también es recomendación**: Netflix elige el artwork de cada título por usuario con bandits contextuales. — Netflix Tech Blog, *Artwork Personalization at Netflix*, 2017.
    29. **Interleaving para comparar rankers con muchísimos menos usuarios** que un A/B; Netflix lo usa como primera criba antes del A/B. — Netflix Tech Blog, *Innovating Faster on Personalization Algorithms at Netflix Using Interleaving*, 2017.
    30. **CUPED reduce la varianza de los A/B** usando la métrica pre-experimento como covariable. — Deng, Xu, Kohavi & Walker, WSDM 2013.
    31. **Las mejoras offline no garantizan mejoras de negocio**; Booking reporta que no encontró correlación entre ganancias offline y online en sus modelos. — Bernardi et al., *150 Successful Machine Learning Models*, KDD 2019.
    32. **Los feedback loops homogeneizan** a los usuarios y reducen la utilidad; simular el bucle antes de lanzar es barato. — Chaney, Stewart & Engelhardt, RecSys 2018.

    ### Escala, sistemas y estado del arte
    33. **Optimiza la cola (p99) del fan-out**, no la media; *hedged requests* y timeouts por etapa. — Dean & Barroso, *The Tail at Scale*, CACM 2013.
    34. **Las tablas de embeddings son el modelo**: el sharding (table/row/column-wise) y la comunicación all-to-all dominan el coste de entrenar DLRMs. — Naumov et al., DLRM, 2019; TorchRec (RecSys 2022).
    35. **Hashing sin colisiones + expiración de IDs + entrenamiento online** es lo que permite reaccionar en minutos. — Liu et al., *Monolith* (ByteDance), 2022.
    36. **Las leyes de escala llegan a recsys** cuando el problema se reformula como generación secuencial: HSTU escala con el cómputo hasta billones de parámetros. — Zhai et al., *Actions Speak Louder than Words*, ICML 2024; Netflix (2025, blog; 2026, arXiv:2605.23312) reporta mejoras al escalar su *backbone* de 2 M a 1.000 M de parámetros, con algunas tareas acercándose a un techo.
    37. **Los *semantic IDs* comparten estadística entre ítems similares** y ayudan en cold start frente a IDs atómicos. — Rajput et al., *TIGER*, NeurIPS 2023; Singh et al., *Better Generalization with Semantic IDs*, RecSys 2024.
    38. **Los LLMs como rankers zero-shot tienen sesgo de posición** y les cuesta usar el orden del historial; mitigarlo (bootstrapping, prompts con recencia) es parte del diseño. — Hou et al., *Large Language Models are Zero-Shot Rankers for Recommender Systems*, ECIR 2024.
    """)

    # ------------------------------------------------------------------ System design
    M(r"""
    ## 4. Guía de entrevistas de *system design* de recsys

    ### El marco de 10 pasos (≈45 minutos)

    | # | Paso | Qué decir | Tiempo |
    |---|---|---|---|
    | 1 | **Clarificar** | superficie, usuarios, objetivo de negocio, restricciones (latencia, privacidad, legal) | 3' |
    | 2 | **Métricas** | north star online + guardrails + métricas offline proxy (y por qué correlacionan) | 4' |
    | 3 | **Escala** | DAU, QPS pico, tamaño de catálogo, almacenamiento de embeddings (*back-of-the-envelope*) | 3' |
    | 4 | **Datos y etiquetas** | señales implícitas/explícitas, definición de positivo, negativos, sesgos, logging de propensiones | 5' |
    | 5 | **Arquitectura** | funnel multi-etapa con tamaños y presupuestos de latencia; offline/nearline/online | 7' |
    | 6 | **Retrieval** | varias fuentes (two-tower, grafo, co-ocurrencia, frescura, seguidos), ANN | 5' |
    | 7 | **Ranking** | features, modelo multi-tarea, calibración, fusión de objetivos | 6' |
    | 8 | **Re-ranking y políticas** | diversidad, frescura, negocio, integridad, exploración | 3' |
    | 9 | **Evaluación y experimentos** | offline temporal, OPE, interleaving, A/B, efectos a largo plazo | 4' |
    | 10 | **Operación** | cold start, monitoreo, reentreno, fallos y degradación elegante | 5' |

    ⚠️ Los números de escala de los casos son **supuestos razonables para la entrevista**, no cifras oficiales de las
    empresas (salvo donde se cita). Lo que se evalúa es el razonamiento, no acertar el dato.
    """)

    C(r'''
    def envelope(name, dau, sessions_per_day, reqs_per_session, peak_factor, catalog, dim, users_total):
        qps = dau * sessions_per_day * reqs_per_session / 86400
        return {"caso": name, "QPS medio": round(qps), "QPS pico": round(qps * peak_factor),
                "emb. ítems (GB, fp16)": round(catalog * dim * 2 / 1e9, 2), "emb. usuarios (GB, fp16)": round(users_total * dim * 2 / 1e9, 1)}


    env = pd.DataFrame([
        envelope("Home de Netflix", dau=100e6, sessions_per_day=2, reqs_per_session=3, peak_factor=3, catalog=2e4, dim=256, users_total=300e6),
        envelope("Feed short-video", dau=1e9, sessions_per_day=8, reqs_per_session=10, peak_factor=2, catalog=1e10, dim=128, users_total=2e9),
        envelope("People You May Know", dau=1e9, sessions_per_day=1, reqs_per_session=1, peak_factor=2, catalog=3e9, dim=128, users_total=3e9),
    ]).set_index("caso")
    display(env)
    ''')

    M(r"""
    ### Caso 1 · La home de Netflix

    **Clarificar.** Página 2D: filas (temáticas) × columnas (títulos) en TV, móvil y web; perfiles por cuenta; catálogo
    pequeño (~10⁴ títulos) pero de alto coste de producción. Objetivo: **satisfacción y retención** a largo plazo
    (Netflix 2024), no clics. Recomendaciones muy influyentes: Gomez-Uribe & Hunt (2015) estiman que ~80 % de las horas
    vistas vienen de recomendaciones.

    **Métricas.** North star: retención / horas «de calidad»; online: *take rate* por fila y posición, % sesiones con
    play, tiempo hasta el play; guardrails: diversidad, cobertura del catálogo, latencia; offline: NDCG/recall por fila,
    métricas de página.

    **Arquitectura.**
    - *Candidatos por fila*: «Seguir viendo» (estado nearline), «Porque viste X» (similitud de ítems), géneros
      personalizados, Top 10 del país, tendencias, estrenos.
    - *Ranking dentro de cada fila* + **ranking de filas** (*page-level*: la página entera es el objeto a optimizar,
      con restricciones de diversidad entre filas y deduplicación de títulos).
    - *Presentación*: artwork por usuario (bandits) y evidencia (sinopsis, etiquetas).
    - Catálogo pequeño ⇒ se puede **precomputar mucho offline** (por perfil) y ajustar nearline/online con el contexto
      (dispositivo, hora, lo que acaba de ver). Embeddings de un **foundation model** consumidos por modelos downstream (2025).

    **Trampas a mencionar:** sesgo de posición 2D (filas superiores y columnas izquierdas), evaluación de página vs
    ítem, cold start de estrenos (metadatos + exploración), perfiles compartidos, efectos de novedad en A/B.
    """)

    C(r'''
    draw({
        "ctx": (0.2, 3.0, 1.9, 1.0, "Petición\n(perfil, device,\nhora, país)", P),
        "cw": (2.7, 5.4, 2.3, 0.8, "Seguir viendo\n(estado nearline)", G),
        "byw": (2.7, 4.4, 2.3, 0.8, "Porque viste X\n(item-item)", G),
        "gen": (2.7, 3.4, 2.3, 0.8, "Géneros personalizados\n(two-tower / FM emb.)", G),
        "top": (2.7, 2.4, 2.3, 0.8, "Top 10 país /\ntendencias", G),
        "new": (2.7, 1.4, 2.3, 0.8, "Estrenos\n(contenido + exploración)", G),
        "rin": (5.7, 3.4, 2.3, 1.4, "Ranking dentro\nde cada fila\n(multi-tarea)", O),
        "rows": (8.6, 3.4, 2.4, 1.4, "Ranking de filas\npage-level + dedup\n+ diversidad", R),
        "art": (11.6, 3.4, 2.2, 1.4, "Artwork y\nevidencia\n(bandits)", R),
        "off": (5.7, 0.6, 5.3, 1.1, "Offline: foundation model → embedding store · precómputo por perfil · entrenamiento diario", B),
        "log": (11.6, 0.6, 2.2, 1.1, "Logs + propensiones\n→ A/B, interleaving", Y),
    }, [("ctx", "cw", ""), ("ctx", "byw", ""), ("ctx", "gen", ""), ("ctx", "top", ""), ("ctx", "new", ""),
        ("cw", "rin", ""), ("byw", "rin", ""), ("gen", "rin", ""), ("top", "rin", ""), ("new", "rin", ""),
        ("rin", "rows", "filas candidatas"), ("rows", "art", "página"), ("art", "log", "impresiones"), ("off", "rin", "features/emb.")],
        "Caso 1 · Home de Netflix: candidatos por fila → ranking en fila → ranking de página → presentación")
    ''')

    M(r"""
    ### Caso 2 · Feed de YouTube / TikTok (vídeo corto)

    **Clarificar.** Feed infinito vertical; señal por vídeo muy densa (watch time, completado, replay, like, share,
    skip rápido); catálogo enorme y **muy fresco** (millones de subidas al día); latencia estricta y QPS altísimo.

    **Métricas.** North star: tiempo de visionado satisfecho / retención diaria; online: watch time por sesión, tasa de
    completado, skips < 3 s, likes/shares, encuestas de satisfacción; guardrails: integridad, diversidad de creadores,
    distribución a creadores nuevos.

    **Arquitectura.**
    - *Retrieval* (miles): two-tower con logQ, grafo de co-engagement, seguidos, *trending*, **pool de exploración** de
      vídeos nuevos (garantiza impresiones iniciales y aprende rápido), secuencial sobre los últimos N vídeos.
    - *Pre-ranking* ligero (two-tower o GBDT pequeño) → *ranking* pesado **multi-tarea** (MMoE/PLE) que predice
      P(completar), E[watch time], P(like), P(skip)… y una **fórmula de fusión** con pesos tuneados por A/B.
    - *Re-ranking*: diversidad de creador/tema, frescura, reglas de integridad.
    - **Entrenamiento online/streaming** (Monolith): el modelo se actualiza en minutos porque los intereses en vídeo
      corto cambian dentro de la sesión. Features en tiempo real (últimos vídeos vistos en la sesión).

    **Trampas:** sesgo de duración (vídeos largos acumulan más watch time ⇒ normaliza por duración), *clickbait*,
    feedback loops y concentración en pocos creadores, cold start de vídeos nuevos, coste de GPU del ranker.
    """)

    C(r'''
    draw({
        "req": (0.2, 3.0, 1.8, 1.0, "Petición\n+ sesión en\ntiempo real", P),
        "tt": (2.6, 5.4, 2.3, 0.8, "Two-tower + ANN\n(logQ)", G), "gr": (2.6, 4.4, 2.3, 0.8, "Grafo co-engagement", G),
        "fol": (2.6, 3.4, 2.3, 0.8, "Seguidos / creadores", G), "seq": (2.6, 2.4, 2.3, 0.8, "Secuencial (últimos N)", G),
        "exp": (2.6, 1.4, 2.3, 0.8, "Pool exploración\n(vídeos nuevos)", G),
        "pre": (5.5, 3.3, 1.9, 1.4, "Pre-ranking\nligero\n~10⁴→10³", O),
        "rk": (8.0, 3.3, 2.2, 1.4, "Ranker multi-tarea\n(MMoE/PLE) +\nfusión de objetivos", O),
        "rr": (10.8, 3.3, 1.6, 1.4, "Re-rank\ndiversidad\nintegridad", R), "out": (12.8, 3.3, 1.0, 1.4, "Feed", P),
        "stream": (5.5, 0.5, 5.0, 1.1, "Kafka → entrenamiento online (Monolith) → sync de parámetros en minutos", B),
        "fs": (10.8, 0.5, 3.0, 1.1, "Features tiempo real\n(Flink + online store)", B),
    }, [("req", "tt", ""), ("req", "gr", ""), ("req", "fol", ""), ("req", "seq", ""), ("req", "exp", ""),
        ("tt", "pre", ""), ("gr", "pre", ""), ("fol", "pre", ""), ("seq", "pre", ""), ("exp", "pre", ""),
        ("pre", "rk", "~500"), ("rk", "rr", "~50"), ("rr", "out", "10"), ("out", "stream", "eventos"), ("stream", "rk", "params"), ("fs", "rk", "")],
        "Caso 2 · Feed de vídeo corto: muchas fuentes, cascada de rankers y entrenamiento en streaming", xlim=(0, 14))
    ''')

    M(r"""
    ### Caso 3 · People You May Know (PYMK)

    **Clarificar.** Recomendar **personas** (no ítems) en una red social; la acción tiene dos lados (enviar y **aceptar**
    la solicitud); objetivo: crecimiento de la red con conexiones de calidad (que generen interacción), sin abuso ni
    incomodidad (privacidad: no revelar contactos sensibles).

    **Métricas.** Online: solicitudes enviadas **y aceptadas** por impresión, conexiones activas a 30 días; guardrails:
    tasa de reportes/ignorar, privacidad; offline: recall@K de conexiones futuras (split temporal sobre el grafo).

    **Arquitectura.**
    - *Candidatos*: **amigos de amigos** (2 saltos) — con grado medio 200 son ~40 000 por usuario ⇒ hay que podar
      (top por vecinos comunes, *random walks with restart*, muestreo); contactos importados, misma escuela/empresa,
      embeddings de grafo (node2vec / GNN, módulo 10).
    - *Features*: vecinos comunes, Adamic-Adar, Jaccard, interacción reciente, similitud de perfil, geografía,
      asimetrías de grado.
    - *Ranking*: P(enviar) × P(aceptar | enviado) — dos modelos o multi-tarea; *supervised random walks*
      (Backstrom & Leskovec, WSDM 2011) como referencia clásica.
    - Precómputo **offline** (batch diario de candidatos 2-hop sobre el grafo) + ajuste **online** (eventos recientes:
      nueva conexión ⇒ nuevos candidatos nearline).

    **Trampas:** usuarios nuevos sin grafo (onboarding con contactos), *hubs* (celebridades) que dominan los 2-hop,
    fugas de privacidad (inferir relaciones ocultas), feedback loop de densificación, spam.
    """)

    C(r'''
    draw({
        "u": (0.2, 3.0, 1.8, 1.0, "Usuario u", P),
        "fof": (2.6, 5.2, 2.6, 0.9, "Amigos de amigos (2-hop)\npodado por vecinos comunes", G),
        "rw": (2.6, 4.0, 2.6, 0.9, "Random walk with restart\n(PPR)", G),
        "ct": (2.6, 2.8, 2.6, 0.9, "Contactos importados /\nescuela / empresa", G),
        "emb": (2.6, 1.6, 2.6, 0.9, "Embeddings de grafo\n(node2vec / GNN)", G),
        "feat": (5.9, 3.0, 2.3, 1.4, "Features de par\nvecinos comunes,\nAdamic-Adar, perfil", O),
        "rk": (8.8, 3.0, 2.4, 1.4, "P(enviar) ×\nP(aceptar | enviar)\nmulti-tarea", O),
        "pol": (11.8, 3.0, 2.0, 1.4, "Políticas: privacidad,\nanti-spam, hubs,\ndiversidad", R),
        "batch": (2.6, 0.2, 5.6, 0.9, "Batch diario sobre el grafo (Spark/GraphX) → candidatos precomputados", B),
        "near": (8.8, 0.2, 5.0, 0.9, "Nearline: nueva conexión ⇒ recalcular 2-hop del usuario", B),
    }, [("u", "fof", ""), ("u", "rw", ""), ("u", "ct", ""), ("u", "emb", ""), ("fof", "feat", ""), ("rw", "feat", ""),
        ("ct", "feat", ""), ("emb", "feat", ""), ("feat", "rk", ""), ("rk", "pol", ""), ("batch", "feat", ""), ("near", "rk", "")],
        "Caso 3 · People You May Know: candidatos de grafo, ranking de doble lado y políticas")
    ''')

    C(r'''
    # Back-of-the-envelope de PYMK: ¿por qué hay que podar el 2-hop?
    deg = np.array([50, 100, 200, 500])
    fof_naive = deg ** 2                      # cota superior (sin solapamiento)
    rng = np.random.default_rng(seed)
    fig, ax = plt.subplots(1, 2, figsize=(13, 3.8))
    ax[0].bar([str(d) for d in deg], fof_naive, color="#f5b041"); ax[0].set_yscale("log")
    ax[0].set_xlabel("grado medio"); ax[0].set_ylabel("candidatos 2-hop (cota)"); ax[0].set_title("Explosión del 2-hop")
    # Distribución de grados heavy-tailed: los hubs dominan
    degrees = np.minimum(rng.pareto(1.5, 100_000) * 50 + 1, 5000)
    share = np.sort(degrees)[::-1].cumsum() / degrees.sum()
    ax[1].plot(np.arange(1, len(share) + 1) / len(share), share); ax[1].set_xscale("log")
    ax[1].set_xlabel("fracción de usuarios (más conectados primero)"); ax[1].set_ylabel("fracción de aristas")
    ax[1].set_title("Hubs: pocos nodos concentran muchas aristas"); plt.tight_layout(); plt.show()
    ''')

    # ------------------------------------------------------------------ Reading map
    M(r"""
    ## 5. Mapa de lectura: ~40 papers canónicos, en orden

    Lee en este orden: cada bloque presupone el anterior. ⭐ = imprescindible.

    | # | Etapa | Paper | Año | Dónde |
    |---|---|---|---|---|
    | 1 | Fundamentos | ⭐ Linden, Smith, York — *Amazon.com Recommendations: Item-to-Item Collaborative Filtering* | 2003 | IEEE Internet Computing |
    | 2 | Fundamentos | ⭐ Koren, Bell, Volinsky — *Matrix Factorization Techniques for Recommender Systems* | 2009 | IEEE Computer |
    | 3 | Fundamentos | ⭐ Hu, Koren, Volinsky — *Collaborative Filtering for Implicit Feedback Datasets* | 2008 | ICDM |
    | 4 | Fundamentos | Rendle et al. — *BPR: Bayesian Personalized Ranking from Implicit Feedback* | 2009 | UAI · arXiv:1205.2618 |
    | 5 | Fundamentos | Koren — *Collaborative Filtering with Temporal Dynamics* (timeSVD++) | 2009 | KDD |
    | 6 | Fundamentos | ⭐ Gomez-Uribe & Hunt — *The Netflix Recommender System: Algorithms, Business Value, and Innovation* | 2015 | ACM TMIS |
    | 7 | Evaluación | ⭐ Krichene & Rendle — *On Sampled Metrics for Item Recommendation* | 2020 | KDD |
    | 8 | Evaluación | ⭐ Ferrari Dacrema et al. — *Are We Really Making Much Progress?* | 2019 | RecSys · arXiv:1907.06902 |
    | 9 | Evaluación | Rendle et al. — *Neural Collaborative Filtering vs. Matrix Factorization Revisited* | 2020 | RecSys · arXiv:2005.09683 |
    | 10 | Lineales | ⭐ Steck — *Embarrassingly Shallow Autoencoders for Sparse Data* (EASE) | 2019 | WWW · arXiv:1905.03375 |
    | 11 | Lineales | Ning & Karypis — *SLIM: Sparse Linear Methods for Top-N Recommender Systems* | 2011 | ICDM |
    | 12 | Ranking | ⭐ He et al. — *Practical Lessons from Predicting Clicks on Ads at Facebook* | 2014 | ADKDD |
    | 13 | Ranking | Rendle — *Factorization Machines* | 2010 | ICDM |
    | 14 | Ranking | ⭐ Cheng et al. — *Wide & Deep Learning for Recommender Systems* | 2016 | DLRS · arXiv:1606.07792 |
    | 15 | Ranking | Wang et al. — *DCN V2: Improved Deep & Cross Network* | 2021 | WWW · arXiv:2008.13535 |
    | 16 | Ranking | Zhou et al. — *Deep Interest Network for Click-Through Rate Prediction* | 2018 | KDD · arXiv:1706.06978 |
    | 17 | LTR | Burges — *From RankNet to LambdaRank to LambdaMART: An Overview* | 2010 | MSR-TR-2010-82 |
    | 18 | LTR | Joachims, Swaminathan, Schnabel — *Unbiased Learning-to-Rank with Biased Feedback* | 2017 | WSDM · arXiv:1608.04468 |
    | 19 | Multi-tarea | ⭐ Zhao et al. — *Recommending What Video to Watch Next: A Multitask Ranking System* | 2019 | RecSys |
    | 20 | Multi-tarea | Ma et al. — *Modeling Task Relationships in Multi-task Learning with Multi-gate MoE* | 2018 | KDD |
    | 21 | Multi-tarea | Tang et al. — *Progressive Layered Extraction (PLE)* | 2020 | RecSys |
    | 22 | Retrieval | ⭐ Covington, Adams, Sargin — *Deep Neural Networks for YouTube Recommendations* | 2016 | RecSys |
    | 23 | Retrieval | ⭐ Yi et al. — *Sampling-Bias-Corrected Neural Modeling for Large Corpus Item Recommendations* | 2019 | RecSys |
    | 24 | Retrieval | Johnson, Douze, Jégou — *Billion-scale similarity search with GPUs* (FAISS) | 2017 | arXiv:1702.08734 |
    | 25 | Retrieval | Malkov & Yashunin — *Efficient and robust ANN search using HNSW graphs* | 2016 | arXiv:1603.09320 |
    | 26 | Retrieval | Grbovic & Cheng — *Real-time Personalization using Embeddings for Search Ranking at Airbnb* | 2018 | KDD |
    | 27 | Secuencial | Hidasi et al. — *Session-based Recommendations with Recurrent Neural Networks* (GRU4Rec) | 2016 | ICLR · arXiv:1511.06939 |
    | 28 | Secuencial | ⭐ Kang & McAuley — *Self-Attentive Sequential Recommendation* (SASRec) | 2018 | ICDM · arXiv:1808.09781 |
    | 29 | Secuencial | Sun et al. — *BERT4Rec* | 2019 | CIKM · arXiv:1904.06690 |
    | 30 | Secuencial | Petrov & Macdonald — *gSASRec: Reducing Overconfidence in Sequential Recommendation* | 2023 | RecSys · arXiv:2308.07192 |
    | 31 | Grafos | ⭐ Ying et al. — *Graph Convolutional Neural Networks for Web-Scale Recommender Systems* (PinSage) | 2018 | KDD · arXiv:1806.01973 |
    | 32 | Grafos | He et al. — *LightGCN* | 2020 | SIGIR · arXiv:2002.02126 |
    | 33 | Más allá de la precisión | Steck — *Calibrated Recommendations* | 2018 | RecSys |
    | 34 | Más allá de la precisión | Wilhelm et al. — *Practical Diversified Recommendations on YouTube with DPPs* | 2018 | CIKM |
    | 35 | Bandits / OPE | ⭐ Li, Chu, Langford, Schapire — *A Contextual-Bandit Approach to Personalized News Article Recommendation* (LinUCB) | 2010 | WWW · arXiv:1003.0146 |
    | 36 | Bandits / OPE | Chen et al. — *Top-K Off-Policy Correction for a REINFORCE Recommender System* | 2019 | WSDM · arXiv:1812.02353 |
    | 37 | Experimentación | Deng et al. — *Improving the Sensitivity of Online Controlled Experiments by Utilizing Pre-Experiment Data* (CUPED) | 2013 | WSDM |
    | 38 | Sistemas | ⭐ Sculley et al. — *Hidden Technical Debt in Machine Learning Systems* | 2015 | NeurIPS |
    | 39 | Sistemas | Naumov et al. — *Deep Learning Recommendation Model (DLRM)* | 2019 | arXiv:1906.00091 |
    | 40 | Sistemas | Liu et al. — *Monolith: Real Time Recommendation System With Collisionless Embedding Table* | 2022 | arXiv:2209.07663 |
    | 41 | Generativos | ⭐ Rajput et al. — *Recommender Systems with Generative Retrieval* (TIGER) | 2023 | NeurIPS · arXiv:2305.05065 |
    | 42 | Generativos | ⭐ Zhai et al. — *Actions Speak Louder than Words: Trillion-Parameter Sequential Transducers* (HSTU) | 2024 | ICML · arXiv:2402.17152 |
    | 43 | Generativos | Deng et al. — *OneRec: Unifying Retrieve and Rank with Generative Recommender* (Kuaishou) | 2025 | arXiv:2502.18965 |
    | 44 | LLMs | Geng et al. — *Recommendation as Language Processing (P5)* | 2022 | RecSys · arXiv:2203.13366 |
    | 45 | LLMs | Hou et al. — *Large Language Models are Zero-Shot Rankers for Recommender Systems* | 2024 | ECIR · arXiv:2305.08845 |
    """)

    C(r'''
    papers = pd.DataFrame([
        ("Fundamentos", 2003), ("Fundamentos", 2009), ("Fundamentos", 2008), ("Fundamentos", 2009), ("Fundamentos", 2009), ("Fundamentos", 2015),
        ("Evaluación", 2020), ("Evaluación", 2019), ("Evaluación", 2020), ("Lineales", 2019), ("Lineales", 2011),
        ("Ranking", 2014), ("Ranking", 2010), ("Ranking", 2016), ("Ranking", 2021), ("Ranking", 2018), ("LTR", 2010), ("LTR", 2017),
        ("Multi-tarea", 2019), ("Multi-tarea", 2018), ("Multi-tarea", 2020), ("Retrieval", 2016), ("Retrieval", 2019), ("Retrieval", 2017),
        ("Retrieval", 2016), ("Retrieval", 2018), ("Secuencial", 2016), ("Secuencial", 2018), ("Secuencial", 2019), ("Secuencial", 2023),
        ("Grafos", 2018), ("Grafos", 2020), ("Beyond accuracy", 2018), ("Beyond accuracy", 2018), ("Bandits/OPE", 2010), ("Bandits/OPE", 2019),
        ("Experimentación", 2013), ("Sistemas", 2015), ("Sistemas", 2019), ("Sistemas", 2022), ("Generativos", 2023), ("Generativos", 2024),
        ("Generativos", 2025), ("LLMs", 2022), ("LLMs", 2024)], columns=["etapa", "año"])
    order = list(dict.fromkeys(papers.etapa))
    fig, ax = plt.subplots(figsize=(12, 4.5))
    for j, e in enumerate(order):
        yrs = papers[papers.etapa == e].año.values
        ax.scatter(yrs + np.random.default_rng(j).uniform(-0.25, 0.25, len(yrs)), [j] * len(yrs), s=70, alpha=0.8)
    ax.set_yticks(range(len(order))); ax.set_yticklabels(order); ax.set_xlabel("año")
    ax.set_title(f"Mapa de lectura: {len(papers)} papers canónicos por etapa y año"); plt.show()
    ''')

    M(r"""
    ## 6. Conferencias, blogs y comunidades

    **Conferencias** (lee los *proceedings* y mira las charlas industriales):
    - **ACM RecSys** — la conferencia de recomendación (track industrial, workshops como ORSUM, CARS, REVEAL, LargeRecSys, y el RecSys Challenge).
    - **KDD** (ADS track), **WWW / TheWebConf**, **SIGIR**, **WSDM**, **CIKM**, **ECIR**; **NeurIPS / ICML / ICLR** para escalado y modelos generativos.

    **Blogs de ingeniería** (los que más contenido de recsys publican):
    - Netflix Tech Blog (netflixtechblog.com) y Netflix Research (research.netflix.com).
    - Meta Engineering (engineering.fb.com) y Meta AI blog; Google Research blog; YouTube / Google DeepMind papers.
    - Pinterest Engineering (medium.com/pinterest-engineering), Spotify Engineering (engineering.atspotify.com) y Spotify Research.
    - Uber Engineering (uber.com/blog/engineering), Airbnb Tech Blog, LinkedIn Engineering, DoorDash Engineering, Instacart Tech, Etsy Code as Craft, Zalando Engineering.
    - X/Twitter Engineering (y el repo público *the-algorithm*), ByteDance/TikTok y Kuaishou (papers en arXiv).

    **Personas y newsletters**: Eugene Yan (eugeneyan.com — *system design for recsys and search*, *patterns for personalization*),
    Chip Huyen (huyenchip.com — ML en tiempo real), Xavier Amatriain, Harald Steck, Steffen Rendle, Julian McAuley
    (libro *Personalized Machine Learning*, 2022).

    **Libros**: Ricci, Rokach & Shapira (eds.), *Recommender Systems Handbook* (3.ª ed., 2022); Aggarwal, *Recommender
    Systems: The Textbook* (2016); Falk, *Practical Recommender Systems* (2019); Bischof & Yee, *Building Recommendation
    Systems in Python and JAX* (O'Reilly, 2023); Huyen, *Designing Machine Learning Systems* (O'Reilly, 2022).

    **Código para leer**: Microsoft Recommenders, RecBole, TorchRec, NVIDIA Merlin, Transformers4Rec, `implicit`, ranx, Open Bandit Pipeline, *the-algorithm* de X.
    """)

    M(r"""
    ## 7. Ruta de carrera en ML de recomendación
    """)

    C(r'''
    levels = [("ML Engineer\n(generalista)", "Entrena y despliega modelos;\nbaselines; métricas offline"),
              ("Recsys MLE", "Retrieval + ranking; features PIT;\nA/B tests; dueño de una superficie"),
              ("Senior", "Diseña el funnel completo;\nfusión de objetivos; OPE;\nlidera experimentos"),
              ("Staff / Principal", "Plataforma (feature store, serving,\nCT) para muchas superficies;\nestrategia multi-año; foundation models"),
              ("Research Scientist\n(rama paralela)", "Nuevos modelos (generativos,\nscaling); publica en RecSys/KDD")]
    fig, ax = plt.subplots(figsize=(14, 3.6)); ax.axis("off"); ax.set_xlim(0, 14); ax.set_ylim(0, 3.6)
    cols = ["#d6eaf8", "#d5f5e3", "#fdebd0", "#fadbd8", "#e8daef"]
    for i, ((t, d), c) in enumerate(zip(levels, cols)):
        x = 0.2 + i * 2.8
        ax.add_patch(mpatches.FancyBboxPatch((x, 1.8), 2.4, 1.2, boxstyle="round,pad=0.03", fc=c, ec="k"))
        ax.text(x + 1.2, 2.4, t, ha="center", va="center", fontsize=9, weight="bold")
        ax.text(x + 1.2, 0.9, d, ha="center", va="center", fontsize=7.5)
        if i < 3:
            ax.annotate("", xy=(x + 2.8, 2.4), xytext=(x + 2.4, 2.4), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.set_title("Ruta de carrera: del ML generalista a staff de plataformas de recomendación", fontsize=11); plt.show()
    ''')

    M(r"""
    | Nivel | Te evalúan por | Demuéstralo con |
    |---|---|---|
    | MLE → Recsys MLE | rigor de evaluación (splits temporales, full ranking), baselines fuertes, código de producción | proyectos 02, 04, 05 y 16 de este curso en tu GitHub |
    | Recsys MLE → Senior | diseño end-to-end, A/B bien diseñados, impacto medido en negocio | el capstone + un *write-up* de decisiones (métricas, trade-offs, resultados) |
    | Senior → Staff | plataformas reutilizables, influencia en varios equipos, visión técnica | diseño de feature store/CT para varias superficies; charla o blog técnico |
    | Research | novedad + rigor + reproducibilidad | paper en workshop de RecSys; reproducción honesta de un paper |

    **Cómo preparar las entrevistas:** (1) dos casos de *system design* en voz alta por semana con el marco de §4; (2) una
    *deep dive* de un proyecto propio con números (qué métrica, cuánto, por qué); (3) ML fundamentals (calibración, sesgos,
    métricas de ranking, *negative sampling*); (4) coding (pandas/NumPy, implementar NDCG o un two-tower en PyTorch en 30').

    ## 📝 Autoevaluación

    1. ¿Por qué el recall de la unión de fuentes es la primera métrica a mirar en un sistema multi-etapa?
    <details><summary>Respuesta</summary>Porque es el techo de todo el pipeline: el ranker y el re-ranker solo reordenan lo que el retrieval trae; si un ítem relevante no está en los candidatos, ninguna mejora posterior lo recupera.</details>

    2. En una entrevista te piden «diseña el feed de TikTok». ¿Cuáles son tus 3 primeras preguntas?
    <details><summary>Respuesta</summary>Objetivo y métricas (¿watch time satisfecho, retención, encuestas?), escala y latencia (DAU, QPS, SLO), y qué señales/superficies hay (feed For You vs Following, señales implícitas disponibles, restricciones de integridad y privacidad).</details>

    3. ¿Por qué Netflix optimiza a nivel de página y no solo de ítem?
    <details><summary>Respuesta</summary>Porque el usuario ve una página 2D: la utilidad depende del conjunto (duplicados, diversidad entre filas, posición 2D). Ordenar ítems independientemente produce páginas redundantes; el objeto de decisión es la página.</details>

    4. Explica por qué las métricas muestreadas pueden engañar.
    <details><summary>Respuesta</summary>Con pocos negativos aleatorios (p. ej. 100) casi cualquier modelo pone al positivo arriba; las métricas muestreadas no son consistentes con las de ranking completo y pueden invertir la comparación entre modelos (Krichene & Rendle 2020).</details>

    5. En PYMK, ¿por qué no basta con P(enviar solicitud)?
    <details><summary>Respuesta</summary>Porque el valor está en conexiones aceptadas y de calidad; optimizar solo envíos fomenta spam y solicitudes no deseadas. Se modela P(enviar)·P(aceptar|enviar) y guardrails de reportes/ignorados.</details>

    6. ¿Qué tres cosas guardarías en cada impresión logueada y por qué?
    <details><summary>Respuesta</summary>Las features servidas (contra el skew), la propensión/probabilidad de mostrar el ítem (para OPE e IPS) y la versión del modelo/política (para atribuir efectos, depurar y hacer rollbacks).</details>

    7. Tu modelo nuevo gana +4 % NDCG offline y pierde en el A/B. Da tres hipótesis.
    <details><summary>Respuesta</summary>(a) Métrica offline no alineada con el objetivo (clic vs satisfacción); (b) leakage o split no temporal que infló el offline; (c) training-serving skew o features no disponibles igual en serving; también: efectos de novedad, sesgo de exposición del log de evaluación.</details>

    ## 📚 Referencias

    Todas las referencias del compendio (§3) y del mapa de lectura (§5) son citas completas (autor, año, título, venue
    e identificador arXiv cuando existe). Fuentes adicionales citadas en este módulo:

    - Netflix Tech Blog (2025). *Foundation Model for Personalized Recommendation*. https://netflixtechblog.com/foundation-model-for-personalized-recommendation-1a0bd8e02d39
    - Netflix Tech Blog (2013). *System Architectures for Personalization and Recommendation*. https://netflixtechblog.com/system-architectures-for-personalization-and-recommendation-e081aa94b5d8
    - Twitter/X Engineering (2023). *Twitter's Recommendation Algorithm*. https://blog.x.com/engineering/en_us/topics/open-source/2023/twitter-recommendation-algorithm
    - Meta Engineering (2023). *Scaling the Instagram Explore recommendations system*. https://engineering.fb.com/2023/08/09/ml-applications/scaling-instagram-explore-recommendations-system/
    - Eksombatchai, C. et al. (2018). *Pixie: A System for Recommending 3+ Billion Items to 200+ Million Users in Real-Time*. WWW. arXiv:1711.07601
    - Backstrom, L. & Leskovec, J. (2011). *Supervised Random Walks: Predicting and Recommending Links in Social Networks*. WSDM. arXiv:1011.4071
    - Singh, A. et al. (2024). *Better Generalization with Semantic IDs: A Case Study in Ranking for Recommendations*. RecSys. arXiv:2306.08121
    - Yan, E. *System Design for Recommendations and Search*. https://eugeneyan.com/writing/system-design-for-discovery/
    - Carbonell, J. & Goldstein, J. (1998). *The Use of MMR, Diversity-Based Reranking for Reordering Documents and Producing Summaries*. SIGIR.
    - Harper, F. M. & Konstan, J. A. (2015). *The MovieLens Datasets: History and Context*. ACM TiiS. https://doi.org/10.1145/2827872

    **Enlaces de las fuentes del compendio (§3)** — para leer el original de cada «secreto»:
    - Krichene & Rendle (2020), sampled metrics: https://doi.org/10.1145/3394486.3403226 · Ferrari Dacrema et al. (2019): https://arxiv.org/abs/1907.06902
    - Rendle et al. (2020), NCF vs MF: https://arxiv.org/abs/2005.09683 · Rendle et al. (2022), iALS revisitado: https://arxiv.org/abs/2110.14037 · Steck (2019), EASE: https://arxiv.org/abs/1905.03375
    - Ji et al. (2023), leakage en evaluación offline: https://arxiv.org/abs/2010.11060 · Klenitskiy & Vasilev (2023), SASRec vs BERT4Rec: https://arxiv.org/abs/2309.07602
    - Petrov & Macdonald (2022), replicabilidad de BERT4Rec: https://arxiv.org/abs/2207.07483 · gSASRec (2023): https://arxiv.org/abs/2308.07192 · DIN/GAUC (2018): https://arxiv.org/abs/1706.06978
    - He et al. (2014), Facebook ads: https://doi.org/10.1145/2648584.2648589 · ESMM (2018): https://arxiv.org/abs/1804.07931 · Covington et al. (2016): https://doi.org/10.1145/2959100.2959190
    - Yi et al. (2019), logQ: https://doi.org/10.1145/3298689.3346996 · Yang et al. (2020), mixed negative sampling: https://doi.org/10.1145/3366424.3386195 · Pixie (2018): https://arxiv.org/abs/1711.07601
    - Grbovic & Cheng (2018), Airbnb: https://doi.org/10.1145/3219819.3219885 · MMoE en YouTube (2019): https://doi.org/10.1145/3298689.3346997 · PLE (2020): https://doi.org/10.1145/3383313.3412236 · PAL (2019): https://doi.org/10.1145/3298689.3347033
    - Wilhelm et al. (2018), DPP YouTube: https://doi.org/10.1145/3269206.3272018 · Steck (2018), calibración: https://doi.org/10.1145/3240323.3240372
    - Open Bandit Dataset (2021): https://arxiv.org/abs/2008.07146 · Top-K off-policy correction (2019): https://arxiv.org/abs/1812.02353
    - Netflix, artwork (2017): https://netflixtechblog.com/artwork-personalization-c589f074ad76 · interleaving (2017): https://netflixtechblog.com/using-interleaving-in-online-experiments-to-accelerate-algorithm-innovation-at-netflix-a04ee392ec55
    - CUPED (2013): https://doi.org/10.1145/2433396.2433413 · Bernardi et al. (2019), Booking: https://doi.org/10.1145/3292500.3330744 · Chaney et al. (2018): https://arxiv.org/abs/1710.11214
    - The Tail at Scale (2013): https://doi.org/10.1145/2408776.2408794 · DLRM: https://arxiv.org/abs/1906.00091 · Monolith: https://arxiv.org/abs/2209.07663
    - HSTU (2024): https://arxiv.org/abs/2402.17152 · TIGER (2023): https://arxiv.org/abs/2305.05065 · LLM rankers zero-shot (Hou et al.): https://arxiv.org/abs/2305.08845
    - Netflix (2026), generative recommender de 1B de parámetros: https://arxiv.org/abs/2605.23312 · DeLorean (SysML 2018): https://web.archive.org/web/20180413124347/http://www.sysml.cc/doc/108.pdf

    ➡️ **Ahora:** el proyecto capstone (`18_proyecto_capstone_cinematch.ipynb`). Es largo: planifícalo como un sprint.
    """)

    nb.save(path)


SERVING_MODULE = r'''
%%writefile cinematch_serving.py
"""CineMatch · motor de recomendación de serving (capstone). Lo usan la API y el notebook (paridad por construcción)."""
import json, os, time
import faiss, lightgbm as lgb, numpy as np, pandas as pd
import scipy.sparse as sp


class Recommender:
    def __init__(self, art="artifacts"):
        self.meta = json.load(open(f"{art}/meta.json"))
        self.feats, self.default = self.meta["rank_feats"], self.meta["src_default"]
        self.genre = np.load(f"{art}/genre_mat.npy"); self.gnorm = np.linalg.norm(self.genre, axis=1) + 1e-8
        self.svd = np.load(f"{art}/svd_emb.npy"); self.svd_index = faiss.read_index(f"{art}/svd.faiss")
        self.svd_index.hnsw.efSearch = 128
        self.cooc = sp.load_npz(f"{art}/cooc.npz").tocsr(); self.pop = np.load(f"{art}/pop_recent.npy")   # top-k disperso
        self.tt_user = None
        if os.path.exists(f"{art}/tt_user.pt"):
            import torch
            self.torch = torch; torch.set_num_threads(1)
            self.tt_user = torch.jit.load(f"{art}/tt_user.pt").eval()
            self.tt_emb = np.load(f"{art}/tt_item_emb.npy"); self.tt_index = faiss.read_index(f"{art}/tt.faiss")
            self.tt_index.hnsw.efSearch = 128
        ist = pd.read_parquet(f"{art}/item_stats.parquet")
        self.ist = {c: ist[c].to_numpy(float) for c in ist.columns}
        prof = pd.read_parquet(f"{art}/user_prof.parquet")
        self.prof = {int(u): r for u, r in zip(prof.index, prof.to_numpy(float))}; self.prof_cols = list(prof.columns)
        ugen = pd.read_parquet(f"{art}/user_genre.parquet")
        self.ugen = {int(u): r for u, r in zip(ugen.index, ugen.to_numpy())}
        self.ranker = lgb.Booster(model_file=f"{art}/ranker.txt")
        self.popular = self.meta["popular"]

    def _ann(self, index, v, hist, k, prefix, out):
        s, i = index.search(v.astype(np.float32), k + len(hist)); seen = set(hist)
        for r, (it, sc) in enumerate([(a, b) for a, b in zip(i[0], s[0]) if a not in seen and a > 0][:k]):
            out.setdefault(int(it), {})[f"{prefix}_score"], out[int(it)][f"{prefix}_rank"] = float(sc), r

    def tt_vector(self, hist):
        h = hist[-50:]; x = self.torch.tensor([h + [0] * (50 - len(h))])
        with self.torch.no_grad():
            return self.tt_user(x).numpy()

    def candidates(self, hist, k=100):
        out, seen = {}, set(hist)
        v = self.svd[hist[-50:]].mean(0, keepdims=True); v /= np.linalg.norm(v) + 1e-8
        self._ann(self.svd_index, v, hist, k, "ann", out)
        cs = np.asarray(self.cooc[hist[-50:]].sum(0)).ravel(); cs[list(seen)] = 0; cs[0] = 0   # misma lógica que
        nz = np.flatnonzero(cs > 0); top = nz[np.argsort(-cs[nz])[:k]]                          # cooc_scores (paridad)
        for r, i in enumerate(top):
            out.setdefault(int(i), {})["cooc_score"], out[int(i)]["cooc_rank"] = float(cs[i]), r
        for r, i in enumerate([i for i in self.pop if i not in seen][: k // 2]):
            out.setdefault(int(i), {})["pop_rank"] = r
        if self.tt_user is not None:
            self._ann(self.tt_index, self.tt_vector(hist), hist, k, "tt", out)
        return out

    def features(self, u, cands):
        ids = np.fromiter(cands, dtype=int); cols = {}
        for f in self.default:
            cols[f] = np.array([cands[i].get(f, self.default[f]) for i in ids], dtype=float)
        cols["n_sources"] = np.array([len(cands[i]) // 2 + ("pop_rank" in cands[i]) for i in ids], dtype=float)
        cols["genre_affinity"] = self.genre[ids] @ self.ugen[u] / self.gnorm[ids]
        for j, c in enumerate(self.prof_cols):
            cols[c] = np.full(len(ids), self.prof[u][j])
        for c, arr in self.ist.items():
            cols[c] = arr[ids]
        return ids, np.column_stack([cols[f] for f in self.feats])

    def recommend(self, u, hist, k=10, lam=0.8):
        t = [time.perf_counter()]
        if not hist or u not in self.prof:
            return [i for i in self.popular if i not in set(hist)][:k], {"strategy": "popularity_fallback"}
        cands = self.candidates(hist); t.append(time.perf_counter())
        ids, X = self.features(u, cands); t.append(time.perf_counter())
        s = self.ranker.predict(X, num_threads=1); o = np.argsort(-s)[:50]; t.append(time.perf_counter())
        items = self.mmr(ids[o], s[o], k, lam); t.append(time.perf_counter())
        names = ["retrieval", "features", "ranking", "reranking"]
        return items, {"strategy": "multi_stage", **{n: 1e3 * (b - a) for n, a, b in zip(names, t, t[1:])}}

    def mmr(self, items, scores, k, lam):
        rel = (scores - scores.min()) / (np.ptp(scores) + 1e-9); E = self.svd[items]
        chosen, cand = [], list(range(len(items)))
        while cand and len(chosen) < k:
            sim = (E[cand] @ E[chosen].T).max(1) if chosen else np.zeros(len(cand))
            best = cand[int(np.argmax(lam * rel[cand] - (1 - lam) * sim))]
            chosen.append(best); cand.remove(best)
        return [int(items[c]) for c in chosen]
'''

API_MODULE = r'''
%%writefile capstone_api.py
"""API de CineMatch (capstone): FastAPI sobre el motor `Recommender`."""
import json, os, threading, time
import fakeredis
from fastapi import FastAPI, Response
from pydantic import BaseModel
from cinematch_serving import Recommender

ART = os.environ.get("ART_DIR", "artifacts")
REC = Recommender(ART)
R = fakeredis.FakeRedis(decode_responses=True)
for u, h in json.load(open(f"{ART}/user_hist.json")).items():
    R.rpush(f"hist:{u}", *h)
TTL = int(os.environ.get("CACHE_TTL", "60"))
LOCK = threading.Lock()
M = {"requests_total": 0, "cache_hits_total": 0, "fallback_total": 0, "latency_ms_sum": 0.0}
app = FastAPI(title="CineMatch capstone", version=REC.meta["model_version"])


class Event(BaseModel):
    user_id: int
    item_id: int


@app.get("/health")
def health():
    return {"status": "ok", "model_version": REC.meta["model_version"]}


@app.get("/recommend/{user_id}")
def recommend(user_id: int, k: int = 10, use_cache: bool = True):
    t0 = time.perf_counter()
    with LOCK:
        M["requests_total"] += 1
    if use_cache and (hit := R.get(f"recs:{user_id}:{k}")):
        with LOCK:
            M["cache_hits_total"] += 1
        return {**json.loads(hit), "cache": True}
    hist = [int(x) for x in R.lrange(f"hist:{user_id}", 0, -1)]   # completo: excluir vistos
    items, info = REC.recommend(user_id, hist, k)
    if info["strategy"] == "popularity_fallback":
        with LOCK:
            M["fallback_total"] += 1
    resp = {"user_id": user_id, "items": items, "model_version": REC.meta["model_version"], **info}
    R.setex(f"recs:{user_id}:{k}", TTL, json.dumps(resp))
    with LOCK:
        M["latency_ms_sum"] += 1e3 * (time.perf_counter() - t0)
    return {**resp, "cache": False}


@app.post("/event")
def event(e: Event):
    R.rpush(f"hist:{e.user_id}", e.item_id); R.ltrim(f"hist:{e.user_id}", -1000, -1)
    for key in R.scan_iter(f"recs:{e.user_id}:*"):
        R.delete(key)
    return {"ok": True}


@app.get("/metrics")
def metrics():
    return Response("".join(f"cinematch_{k} {v}\n" for k, v in M.items()), media_type="text/plain")
'''


def project() -> None:
    path = f"{MOD}/18_proyecto_capstone_cinematch.ipynb"
    nb = Notebook("Proyecto 18 · Capstone CineMatch end-to-end", colab_path=path, gpu=True)
    M, C = nb.md, nb.code

    M(f"""
    {nb.badge()}

    # Proyecto 18 · Capstone: CineMatch end-to-end

    **Nivel:** 🔴 Experto · **Duración:** 15–25 h (planifícalo como un sprint de 1–2 semanas) · **GPU:** T4 recomendada
    para el two-tower con `SCALE="full"` (en CPU funciona con `FAST_DEV_RUN=True`) · **Unidades Colab:** 3–10

    ## 🏢 Contexto de negocio

    Eres el/la **tech lead de recomendación de CineMatch**. El comité de dirección aprobará el lanzamiento de la nueva
    home si presentas un sistema **completo, medido y operable**: retrieval multi-fuente con un two-tower propio,
    ranker, re-ranking de diversidad, una API con SLO, trazabilidad en MLflow, un informe de drift con decisión de
    reentreno y —como extra— un asistente conversacional. Tu entregable final es este notebook ejecutado + un
    *design doc* de una página.

    ## 📦 Dataset

    **MovieLens-1M** (`SCALE="full"`, recomendado para la entrega: 1 000 209 valoraciones, 6 040 usuarios, 3 706 películas)
    o **MovieLens-100K** (`SCALE="small"`, para iterar). GroupLens: https://grouplens.org/datasets/movielens/ ·
    Fallback sintético si no hay red.

    ## ✅ Rúbrica exigente (100 puntos + 10 de bonus)

    Los umbrales son **relativos a baselines medidos en el mismo split temporal**, para que sean justos con cualquier escala.

    | # | Entregable | Criterio objetivo | Puntos |
    |---|---|---|---|
    | E1 | Datos | split temporal global; esquema Pandera válido; test de no-leakage (todas las features usan datos < corte) | 10 |
    | E2 | Retrieval | two-tower PyTorch con in-batch negatives + **corrección logQ**; Recall@100 del two-tower ≥ **0,6 ×** PureSVD (con `FAST_DEV_RUN=False` debería acercarse o superarlo) y la **unión** con two-tower ≥ **1,05 ×** la unión sin él (aporta candidatos *nuevos*) | 15 |
    | E3 | Ranking | LambdaMART: NDCG@10 ≥ **1,10 ×** la mejor fuente sola; **ablación** de 3 grupos de features | 15 |
    | E4 | Re-ranking | frontera MMR completa y λ elegido con ILD@10 **≥ +3 %** relativo y una ganancia relativa de diversidad **≥** la pérdida relativa de NDCG@10 (con embeddings L2-normalizados el ILD base ya es alto, ~0,7: un +10 % suele ser inalcanzable sin destrozar NDCG) | 10 |
    | E5 | Serving | FastAPI con `/health`, `/recommend`, `/event`, `/metrics`; fallback; **p99 ≤ 100 ms con 4 concurrentes** (1 worker uvicorn en la CPU de Colab; reporta también 8 y explica el codo por el GIL); **paridad** offline/serving ≥ 99,9 % | 15 |
    | E6 | MLOps | MLflow: runs de retrieval y ranking con métricas, modelo registrado con alias `champion`; informe de drift (OOV + Evidently o PSI) y **decisión de reentreno justificada** con el NDCG «stale vs fresh» | 15 |
    | E7 | Informe | *scorecard* automático (abajo) + *design doc* (≤ 1 página: métricas, arquitectura, trade-offs, riesgos, siguientes pasos) | 10 |
    | ⭐ | Bonus | agente conversacional con ≥ 3 herramientas sobre el motor (LLM con tool use) y fallback sin LLM | +10 |

    **Cómo trabajar:** completa los `TODO` de cada etapa (las celdas de chequeo capturan `NotImplementedError`), y
    consulta la solución de referencia solo al final. Si una etapa te bloquea, puedes usar la función de la solución y
    seguir: el capstone premia el sistema completo.
    """)

    C(r'''
    !pip install -q faiss-cpu lightgbm fastapi uvicorn fakeredis requests pyarrow mlflow pandera evidently
    ''')
    C(DATA_CELL)
    C(SCALE_CELL.replace('SCALE = "small"', 'SCALE = "small"     # ⇦ pon "full" (ML-1M) para la entrega'))
    C(r'''
    import torch, torch.nn as nn, torch.nn.functional as F
    torch.manual_seed(seed)
    torch.set_num_threads(int(os.environ.get("TORCH_THREADS", os.cpu_count() or 2)))
    device = "cuda" if torch.cuda.is_available() else "cpu"
    FAST_DEV_RUN = True          # False para la entrega (más épocas y usuarios de evaluación)
    N_EVAL_USERS = 400 if FAST_DEV_RUN else 3000
    print("device:", device, "| FAST_DEV_RUN:", FAST_DEV_RUN)
    ''')
    C(CORE_CELL)
    C(FEAT_CELL)

    M(r"""
    ## Etapa 1 · Datos (E1)

    `CORE_CELL` ya hizo el split temporal 70/10/20. Tu tarea: (a) esquema Pandera para `ratings`; (b) `assert_no_leakage(frame, t_cut)`
    que compruebe que las features de ítem de un frame construido con `build_frame(..., t_cut)` coinciden con las calculadas
    **solo** con datos anteriores a `t_cut` (p. ej. `pop_cum` == conteo de interacciones previas).
    """)

    C(r'''
    def ratings_schema():
        # TODO: pa.DataFrameSchema con user_id/item_id ≥ 1, rating ∈ {1..5}, ts > 0 y sin duplicados (user, item)
        raise NotImplementedError


    def assert_no_leakage(frame, t_cut):
        # TODO
        raise NotImplementedError


    try:
        ratings_schema().validate(ratings[["user_id", "item_id", "rating", "ts"]]); print("E1 · esquema OK")
    except NotImplementedError:
        print("⏳ E1 pendiente")
    ''')

    M(r"""
    ## Etapa 2 · Retrieval two-tower (E2)

    Implementa `TwoTower`: torre de usuario = `EmbeddingBag` (media) sobre los últimos 50 ítems del historial → MLP →
    normalización L2; torre de ítem = embedding de ID + géneros → MLP → L2. Entrena con **softmax in-batch** a
    temperatura τ y **corrección logQ** (resta $\log q_j$ al logit del ítem $j$, con $q_j$ su frecuencia de muestreo;
    Yi et al. 2019). Ejemplos: para cada usuario de `train_a`, posiciones $j$ de su secuencia temporal → (historial
    previo, ítem $j$). Exporta la torre de usuario con TorchScript (la usará el servicio).
    """)

    C(r'''
    class TwoTower(nn.Module):
        def __init__(self, n_items, genre_mat, dim=64):
            super().__init__()
            # TODO: embeddings, EmbeddingBag(mode="mean", padding_idx=0), MLPs
            raise NotImplementedError

        def user(self, hist):            # hist: LongTensor (B, 50) con padding 0
            raise NotImplementedError

        def item(self, ids):
            raise NotImplementedError


    def train_two_tower(df, epochs=3, dim=64, tau=0.05, batch=512, logq=True):
        # TODO: ejemplos (historial previo → siguiente ítem), bucle de entrenamiento, devuelve (modelo, emb_items normalizados)
        raise NotImplementedError
    ''')

    M(r"""
    ## Etapas 3–4 · Ranking, ablación y re-ranking (E3, E4)

    Reutiliza `build_frame` + `train_lambdamart` (y `multi_window_frames` para tener más usuarios etiquetados sin romper
    el protocolo temporal). Añade las features del two-tower (`tt_score`, `tt_rank`). Ablación: (A) solo fuentes,
    (B) + ítem, (C) + usuario/cruce. Re-ranking: barre λ ∈ {1,0; 0,9; …; 0,5} y elige el **mayor** λ que cumpla E4 (ILD ≥ +3 % y ganancia de diversidad ≥ pérdida de NDCG).

    ## Etapa 5 · Serving (E5)

    El motor de serving (`cinematch_serving.Recommender`) y la API (`capstone_api.py`) se escriben en ficheros. Completa
    `export_artifacts()` (todo lo que el motor necesita, as-of `t_b`) y el test de carga.

    ## Etapa 6 · MLOps (E6) y Etapa 7 · Informe (E7)

    Registra en MLflow, genera el informe de drift y la decisión, y rellena el *scorecard*. La solución completa sigue.

    ---

    # ⛔ SPOILER — intenta resolverlo primero

    Solución de referencia completa y ejecutable de arriba a abajo.
    """)

    C(r'''
    try:
        import pandera.pandas as pa
    except ImportError:
        import pandera as pa
    from pandera import Check


    def ratings_schema():
        return pa.DataFrameSchema(
            {"user_id": pa.Column(int, Check.ge(1)), "item_id": pa.Column(int, Check.ge(1)),
             "rating": pa.Column(float, Check.isin([1.0, 2.0, 3.0, 4.0, 5.0])), "ts": pa.Column(int, Check.gt(0))},
            checks=[Check(lambda d: not d.duplicated(["user_id", "item_id"]).any(), error="duplicados (user,item)")], coerce=True)


    def assert_no_leakage(frame, t_cut):
        true_pop = ratings[ratings.ts < t_cut].item_id.value_counts()
        got = frame.drop_duplicates("item_id").set_index("item_id").pop_cum
        ok = np.allclose(got.values, true_pop.reindex(got.index).fillna(0).values)
        assert ok, "¡pop_cum usa datos posteriores al corte!"
        return ok


    E = {}
    ratings_schema().validate(ratings[["user_id", "item_id", "rating", "ts"]])
    E["E1"] = True
    print("E1 · esquema válido · split:", len(train_a), len(train_b), len(test))
    ''')

    C(r'''
    class TwoTower(nn.Module):
        def __init__(self, n_items, genre_mat, dim=64):
            super().__init__()
            self.register_buffer("genre", torch.tensor(genre_mat))
            self.item_emb = nn.Embedding(n_items, dim, padding_idx=0)
            self.hist_emb = nn.EmbeddingBag(n_items, dim, mode="mean", padding_idx=0)
            g = genre_mat.shape[1]
            self.user_mlp = nn.Sequential(nn.Linear(dim, 128), nn.ReLU(), nn.Linear(128, dim))
            self.item_mlp = nn.Sequential(nn.Linear(dim + g, 128), nn.ReLU(), nn.Linear(128, dim))
            nn.init.normal_(self.item_emb.weight, std=0.05); nn.init.normal_(self.hist_emb.weight, std=0.05)

        def user(self, hist):
            return F.normalize(self.user_mlp(self.hist_emb(hist)), dim=-1)

        def item(self, ids):
            return F.normalize(self.item_mlp(torch.cat([self.item_emb(ids), self.genre[ids]], -1)), dim=-1)


    class UserTower(nn.Module):
        """Solo la torre de usuario, para exportar con TorchScript al servicio."""
        def __init__(self, tt):
            super().__init__(); self.hist_emb, self.user_mlp = tt.hist_emb, tt.user_mlp

        def forward(self, hist):
            return F.normalize(self.user_mlp(self.hist_emb(hist)), dim=-1)


    def make_examples(df, max_per_user=40, L=50):
        r_ = np.random.default_rng(seed); H, T = [], []
        for _, g in df.sort_values("ts").groupby("user_id"):
            seq = g.item_id.to_numpy()
            if len(seq) < 3:
                continue
            pos = r_.choice(np.arange(1, len(seq)), min(max_per_user, len(seq) - 1), replace=False)
            for j in pos:
                h = seq[max(0, j - L):j]; H.append(np.pad(h, (0, L - len(h)))); T.append(seq[j])
        return torch.tensor(np.array(H)), torch.tensor(np.array(T))
    ''')

    C(r'''
    def train_two_tower(df, epochs=None, dim=64, tau=0.05, batch=512, logq=True, lr=3e-3):
        epochs = epochs or (4 if FAST_DEV_RUN else 15)
        H, T = make_examples(df)
        q = np.bincount(T.numpy(), minlength=N_ITEMS) / len(T)                  # frecuencia de muestreo del ítem
        logq_t = torch.tensor(np.log(q + 1e-10), dtype=torch.float32, device=device)
        model = TwoTower(N_ITEMS, GENRE_MAT, dim).to(device)
        opt = torch.optim.Adam(model.parameters(), lr=lr); losses = []
        for ep in range(epochs):
            perm = torch.randperm(len(T)); tot = 0.0
            for b in range(0, len(T), batch):
                idx = perm[b:b + batch]; h, t = H[idx].to(device), T[idx].to(device)
                logits = model.user(h) @ model.item(t).T / tau
                if logq:
                    logits = logits - logq_t[t][None, :]                        # corrección logQ (Yi et al. 2019)
                same = (t[:, None] == t[None, :]) & ~torch.eye(len(t), dtype=torch.bool, device=device)
                logits = logits.masked_fill(same, -1e9)                         # "accidental hits" = no son negativos
                loss = F.cross_entropy(logits, torch.arange(len(t), device=device))
                opt.zero_grad(); loss.backward(); opt.step(); tot += loss.item() * len(idx)
            losses.append(tot / len(T))
        model.eval()
        with torch.no_grad():
            item_emb = model.item(torch.arange(N_ITEMS, device=device)).cpu().numpy()
        return model, item_emb, losses


    t0 = time.time()
    TT, TT_EMB, tt_losses = train_two_tower(train_a)
    print(f"Two-tower entrenado en {time.time() - t0:.0f}s · loss final {tt_losses[-1]:.3f}")
    plt.figure(figsize=(6, 3)); plt.plot(tt_losses, "o-"); plt.title("Two-tower: loss in-batch softmax (logQ)"); plt.xlabel("época"); plt.show()
    ''')

    C(r'''
    def make_user_fn(model):
        def fn(hist):
            h = hist[-50:]; x = torch.tensor([h + [0] * (50 - len(h))], device=device)
            with torch.no_grad():
                return model.user(x).cpu().numpy()
        return fn


    class Sources2(Sources):
        """Sources + fuente two-tower (features tt_score / tt_rank)."""
        def __init__(self, df, tt_model=None, tt_emb=None):
            super().__init__(df)
            self.tt_fn = make_user_fn(tt_model) if tt_model is not None else None
            if tt_emb is not None:
                self.tt_emb = tt_emb.astype(np.float32)
                self.tt_index = faiss.IndexHNSWFlat(tt_emb.shape[1], 32, faiss.METRIC_INNER_PRODUCT)
                self.tt_index.hnsw.efSearch = 128; self.tt_index.add(self.tt_emb)

        def candidates(self, hist, k=100):
            out = super().candidates(hist, k)
            if self.tt_fn is not None:
                s, i = self.tt_index.search(self.tt_fn(hist).astype(np.float32), k + len(hist)); seen = set(hist)
                for r, (it, sc) in enumerate([(a, b) for a, b in zip(i[0], s[0]) if a not in seen and a > 0][:k]):
                    out.setdefault(int(it), {})["tt_score"], out[int(it)]["tt_rank"] = float(sc), r
            return out


    SRC_FEATS = SRC_FEATS + ["tt_score", "tt_rank"]
    SRC_DEFAULT = {**SRC_DEFAULT, "tt_score": -1.0, "tt_rank": 999}
    RANK_FEATS = SRC_FEATS + [f for f in RANK_FEATS if f not in SRC_FEATS]
    SRC_A = Sources2(train_a, TT, TT_EMB)
    ''')

    C(r'''
    # Fuentes "frescas" para servir el test: PureSVD/co-ocurrencia re-entrenadas hasta t_b; two-tower afinado hasta t_b
    TT_B, TT_EMB_B, _ = train_two_tower(ratings[ratings.ts < t_b])
    SRC_B = Sources2(ratings[ratings.ts < t_b], TT_B, TT_EMB_B)
    users_eval = [u for u in test_pos if u in hist_b][:N_EVAL_USERS]


    def source_recalls(src, users, hist):
        out = {k: [] for k in ["PureSVD", "Two-tower", "Co-ocurrencia", "Popularidad", "Unión sin TT", "Unión"]}
        for u in users:
            c = src.candidates(hist[u], 100); tp = test_pos[u]; r = lambda s: len(s & tp) / len(tp)
            sets = {k: {i for i, f in c.items() if key in f} for k, key in
                    [("PureSVD", "ann_rank"), ("Two-tower", "tt_rank"), ("Co-ocurrencia", "cooc_rank"), ("Popularidad", "pop_rank")]}
            for k, s in sets.items():
                out[k].append(r(s))
            out["Unión sin TT"].append(r(sets["PureSVD"] | sets["Co-ocurrencia"] | sets["Popularidad"])); out["Unión"].append(r(set(c)))
        return {k: float(np.mean(v)) for k, v in out.items()}


    rec = source_recalls(SRC_B, users_eval, hist_b)
    E["E2"] = rec["Two-tower"] >= 0.6 * rec["PureSVD"] and rec["Unión"] >= 1.05 * rec["Unión sin TT"]
    print({k: round(v, 4) for k, v in rec.items()}, "→ E2", "✅" if E["E2"] else "❌")
    pd.Series(rec).plot.bar(figsize=(9, 3.5), color="#5dade2", rot=15, title="E2 · Recall@100 por fuente (test temporal)"); plt.show()
    ''')

    C(r'''
    # 3 ventanas temporales; en cada una el two-tower y las fuentes se entrenan SOLO con datos anteriores a la ventana
    fr_tr = multi_window_frames(lambda past: Sources2(past, *train_two_tower(past)[:2]))
    assert_no_leakage(fr_tr[fr_tr.qid.str.endswith("@0.7")], t_a)
    print("Ejemplos del ranker:", fr_tr.shape, "| grupos:", fr_tr.qid.nunique())
    fr_te = build_frame(SRC_B, hist_b, users_eval, t_b)
    groups = {"A · solo fuentes": SRC_FEATS + ["n_sources"],
              "B · + ítem": SRC_FEATS + ["n_sources", "pop_cum", "pop_30d", "rating_mean", "item_age_days"],
              "C · + usuario/cruce (todas)": RANK_FEATS}


    def eval_ranker(model, feats, frame):
        frame = frame.assign(score=model.predict(frame[feats]))
        return float(np.mean([ndcg_at_k(list(g.sort_values("score", ascending=False).item_id), test_pos[u])
                              for u, g in frame.groupby("user_id")])), frame


    abl = {}
    for name, feats in groups.items():
        RANK_FEATS_BAK, RANK_FEATS = RANK_FEATS, feats
        m = train_lambdamart(fr_tr); RANK_FEATS = RANK_FEATS_BAK
        abl[name], _ = eval_ranker(m, feats, fr_te)
    RANKER = train_lambdamart(fr_tr)
    nd_rank, fr_te = eval_ranker(RANKER, RANK_FEATS, fr_te)
    best_src = max(float(np.mean([ndcg_at_k(list(g.sort_values(c).item_id), test_pos[u]) for u, g in fr_te.groupby("user_id")]))
                   for c in ["ann_rank", "tt_rank", "cooc_rank"])
    E["E3"] = nd_rank >= 1.10 * best_src and len(abl) == 3
    print(f"E3 · NDCG@10 ranker = {nd_rank:.4f} vs mejor fuente {best_src:.4f} (×{nd_rank / best_src:.2f}) →", "✅" if E["E3"] else "❌")
    display(pd.Series(abl, name="NDCG@10 (ablación)").round(4).to_frame())
    E["E1"] = E["E1"] and True
    ''')

    C(r'''
    lams, rows = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5], []
    G_te = list(fr_te.groupby("user_id"))
    for lam in lams:
        nd, dv = [], []
        for u, g in G_te:
            g = g.sort_values("score", ascending=False)
            rr = mmr(g.item_id.values[:50], g.score.values[:50], SRC_B.emb, k=10, lam=lam)
            nd.append(ndcg_at_k(rr, test_pos[u])); dv.append(ild(rr, SRC_B.emb))
        rows.append({"lambda": lam, "NDCG@10": np.mean(nd), "ILD@10": np.mean(dv)})
    mm = pd.DataFrame(rows); base = mm.iloc[0]
    gain_ild = mm["ILD@10"] / base["ILD@10"] - 1; loss_ndcg = 1 - mm["NDCG@10"] / base["NDCG@10"]
    ok = mm[(gain_ild >= 0.03) & (gain_ild >= loss_ndcg)]                 # no perder más precisión de la que se gana
    LAMBDA = float(ok["lambda"].max()) if len(ok) else 0.8
    E["E4"] = len(ok) > 0
    display(mm.round(4)); print(f"E4 · λ elegido = {LAMBDA} →", "✅" if E["E4"] else "❌ (ninguna λ cumple: prueba otra similitud, p. ej. géneros)")
    fig, ax = plt.subplots(figsize=(6.5, 3.8)); ax.plot(mm["ILD@10"], mm["NDCG@10"], "o-")
    for _, r in mm.iterrows():
        ax.annotate(f"λ={r['lambda']}", (r["ILD@10"], r["NDCG@10"]), fontsize=8, xytext=(3, 3), textcoords="offset points")
    ax.set_xlabel("ILD@10"); ax.set_ylabel("NDCG@10"); ax.set_title("E4 · Frontera MMR"); plt.show()
    ''')

    C(r'''
    def export_artifacts(art=ART_DIR):
        os.makedirs(art, exist_ok=True)
        np.save(f"{art}/genre_mat.npy", GENRE_MAT); np.save(f"{art}/svd_emb.npy", SRC_B.emb)
        faiss.write_index(SRC_B.index, f"{art}/svd.faiss"); sp.save_npz(f"{art}/cooc.npz", SRC_B.cooc)
        np.save(f"{art}/pop_recent.npy", SRC_B.pop); np.save(f"{art}/tt_item_emb.npy", SRC_B.tt_emb)
        faiss.write_index(SRC_B.tt_index, f"{art}/tt.faiss")
        ut = torch.jit.trace(UserTower(TT_B).cpu().eval(), torch.zeros(1, 50, dtype=torch.long)); ut.save(f"{art}/tt_user.pt")
        TT_B.to(device)
        ist = item_stats_asof(t_b); ist.to_parquet(f"{art}/item_stats.parquet")
        prof, gen = user_stats_asof(t_b); prof.to_parquet(f"{art}/user_prof.parquet")
        gen.columns = [str(c) for c in gen.columns]; gen.to_parquet(f"{art}/user_genre.parquet")
        RANKER.booster_.save_model(f"{art}/ranker.txt")
        json.dump({str(u): [int(x) for x in h] for u, h in hist_b.items()}, open(f"{art}/user_hist.json", "w"))
        json.dump({"rank_feats": RANK_FEATS, "src_default": SRC_DEFAULT, "lambda": LAMBDA, "model_version": "capstone-v1",
                   "popular": [int(i) for i in ratings[ratings.ts < t_b].item_id.value_counts().index[:200]]},
                  open(f"{art}/meta.json", "w"))
        return sorted(os.listdir(art))


    print(export_artifacts())
    ''')

    C(SERVING_MODULE)
    C(API_MODULE)

    C(r'''
    import importlib, cinematch_serving
    importlib.reload(cinematch_serving)
    ENGINE = cinematch_serving.Recommender(ART_DIR)

    # Paridad offline/serving: mismas features para los mismos (usuario, ítem)
    par = []
    for u in users_eval[:100]:
        ids, X = ENGINE.features(u, ENGINE.candidates(hist_b[u]))
        off = fr_te[fr_te.user_id == u].set_index("item_id").loc[ids, RANK_FEATS].to_numpy(float)
        par.append(np.isclose(X, off, atol=1e-4).mean())
    parity = float(np.mean(par))
    nd_engine = np.mean([ndcg_at_k(ENGINE.recommend(u, hist_b[u], 10, LAMBDA)[0], test_pos[u]) for u in users_eval[:300]])
    print(f"Paridad de features offline vs motor de serving: {parity:.4%} · NDCG@10 del motor (λ={LAMBDA}) = {nd_engine:.4f}")
    ''')

    C(r'''
    import subprocess, sys, requests
    from concurrent.futures import ThreadPoolExecutor

    import socket
    with socket.socket() as s_:                       # puerto libre: re-ejecutar la celda no choca con un servidor previo
        s_.bind(("127.0.0.1", 0)); PORT = s_.getsockname()[1]
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "capstone_api:app", "--port", str(PORT), "--log-level", "warning"],
                            env={**os.environ, "ART_DIR": ART_DIR})
    URL = f"http://127.0.0.1:{PORT}"
    for _ in range(240):
        try:
            if requests.get(f"{URL}/health", timeout=0.5).ok:
                time.sleep(1); assert proc.poll() is None, f"El servidor en el puerto {PORT} terminó inesperadamente"
                break
        except requests.exceptions.RequestException:
            time.sleep(0.5)
    u0 = users_eval[0]
    a = requests.get(f"{URL}/recommend/{u0}").json(); b = requests.get(f"{URL}/recommend/{u0}").json()
    requests.post(f"{URL}/event", json={"user_id": u0, "item_id": a["items"][0]})
    c = requests.get(f"{URL}/recommend/{u0}").json(); cold = requests.get(f"{URL}/recommend/987654321").json()
    api_ok = b["cache"] and not c["cache"] and cold["strategy"] == "popularity_fallback" and "cinematch_requests_total" in requests.get(f"{URL}/metrics").text


    def load_test(conc, n=300):
        s = requests.Session()
        def one(u):
            t = time.perf_counter(); s.get(f"{URL}/recommend/{u}", params={"use_cache": False}); return 1e3 * (time.perf_counter() - t)
        us = np.random.default_rng(seed).choice(users_eval, n); t0 = time.perf_counter()
        with ThreadPoolExecutor(conc) as ex:
            lat = np.array(list(ex.map(one, us)))
        return {"conc": conc, "qps": n / (time.perf_counter() - t0), "p50": np.percentile(lat, 50), "p99": np.percentile(lat, 99)}


    [requests.get(f"{URL}/recommend/{u}", params={"use_cache": False}) for u in users_eval[:20]]   # warm-up
    lt = pd.DataFrame([load_test(c) for c in [1, 4, 8]]); display(lt.round(1))
    p99_4, p99_8 = float(lt[lt.conc == 4].p99.iloc[0]), float(lt[lt.conc == 8].p99.iloc[0])
    E["E5"] = api_ok and p99_4 <= 100 and parity >= 0.999
    print(f"E5 · API ok={api_ok} · p99@4 = {p99_4:.1f} ms (p99@8 = {p99_8:.1f} ms: 1 worker + GIL ⇒ cola) · paridad = {parity:.4%} →",
          "✅" if E["E5"] else "❌")
    ''')

    C(r'''
    import mlflow
    from mlflow.tracking import MlflowClient
    mlflow.set_tracking_uri("sqlite:///mlflow_capstone.db"); mlflow.set_experiment("cinematch-capstone")
    mc = MlflowClient()


    class CineMatchPyfunc(mlflow.pyfunc.PythonModel):
        def load_context(self, context):
            import sys as _s; _s.path.insert(0, ".")
            from cinematch_serving import Recommender
            self.rec = Recommender(context.artifacts["art"])

        def predict(self, context, model_input, params=None):
            return pd.DataFrame({"items": [self.rec.recommend(int(u), list(h))[0] for u, h in zip(model_input.user_id, model_input.history)]})


    with mlflow.start_run(run_name="retrieval"):
        mlflow.log_params({"tt_dim": 64, "tau": 0.05, "logq": True, "scale": SCALE}); mlflow.log_metrics({f"recall100_{k.replace(' ', '_')}": v for k, v in rec.items()})
    with mlflow.start_run(run_name="ranking+serving") as run:
        mlflow.log_params({"ranker": "LGBMRanker-lambdarank", "mmr_lambda": LAMBDA, "n_feats": len(RANK_FEATS)})
        mlflow.log_metrics({"ndcg10_ranker": nd_rank, "ndcg10_engine": float(nd_engine), "p99_ms_conc4": p99_4, "p99_ms_conc8": p99_8, "parity": parity})
        kw = dict(python_model=CineMatchPyfunc(), artifacts={"art": ART_DIR}, registered_model_name="cinematch-capstone",
                  code_paths=["cinematch_serving.py"])
        try:
            mlflow.pyfunc.log_model(name="model", **kw)
        except TypeError:
            mlflow.pyfunc.log_model(artifact_path="model", **kw)
    v = max(int(x.version) for x in mc.search_model_versions("name='cinematch-capstone'"))
    mc.set_registered_model_alias("cinematch-capstone", "champion", v)
    print("Registrado cinematch-capstone v", v, "con alias champion")
    ''')

    C(r'''
    # Informe de drift + decisión de reentreno basada en evidencia (stale vs fresh)
    def psi(ref, cur, bins=10):
        edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
        p = np.histogram(np.clip(ref, edges[0], edges[-1]), edges)[0] / len(ref) + 1e-4
        q = np.histogram(np.clip(cur, edges[0], edges[-1]), edges)[0] / len(cur) + 1e-4
        return float(np.sum((p - q) * np.log(p / q)))


    pop_a = train_a.item_id.value_counts()
    drift = {"oov_test_vs_train_a": float((~test.item_id.isin(pop_a.index)).mean()),
             "psi_logpop": psi(np.log1p(train_a.item_id.map(pop_a).values), np.log1p(test.item_id.map(pop_a).fillna(0).values)),
             "psi_rating": psi(train_a.rating.values.astype(float), test.rating.values.astype(float))}
    try:
        from evidently import Report
        from evidently.presets import DataDriftPreset
        mk = lambda d: pd.DataFrame({"rating": d.rating.astype(float).values, "log_pop": np.log1p(d.item_id.map(pop_a).fillna(0)).values})
        Report([DataDriftPreset()]).run(current_data=mk(test), reference_data=mk(train_a)).save_html("capstone_drift.html")
        drift["evidently_html"] = "capstone_drift.html"
    except Exception as e:
        print("Evidently no disponible:", repr(e)[:100])
    # ¿Cuánto perdemos sirviendo con fuentes entrenadas hasta t_a (stale) en vez de t_b (fresh)?
    fr_stale = build_frame(SRC_A, hist_b, users_eval[:300], t_b)
    nd_stale, _ = eval_ranker(RANKER, RANK_FEATS, fr_stale)
    nd_fresh, _ = eval_ranker(RANKER, RANK_FEATS, fr_te[fr_te.user_id.isin(users_eval[:300])])
    decision = "REENTRENAR (frescura vale ≥ 3 %)" if nd_fresh >= 1.03 * nd_stale else "mantener calendario actual"
    drift.update({"ndcg_stale": nd_stale, "ndcg_fresh": nd_fresh, "decision": decision})
    with mlflow.start_run(run_name="drift-report"):
        mlflow.log_metrics({k: v for k, v in drift.items() if isinstance(v, float)}); mlflow.set_tag("decision", decision)
    E["E6"] = True
    display(pd.Series(drift).to_frame("valor"))
    ''')

    M(r"""
    ### ⭐ Bonus · Asistente conversacional sobre el motor

    El agente expone el motor como **herramientas** (módulo 12). Si hay `ANTHROPIC_API_KEY` y el paquete `anthropic`,
    usa la Claude API con *tool use* (bucle manual: el modelo pide herramientas, las ejecutamos y le devolvemos los
    resultados); si no, un *fallback* determinista enruta por palabras clave a las mismas herramientas — el notebook nunca
    se bloquea. El modelo se configura con `CINEMATCH_LLM_MODEL`.
    """)

    C(r'''
    GENRE_IDX = {g.lower(): j for j, g in enumerate(GENRES)}


    def tool_recommend_for_user(user_id: int, k: int = 5):
        return [TITLES.get(i, str(i)) for i in ENGINE.recommend(int(user_id), hist_b.get(int(user_id), []), int(k), LAMBDA)[0]]


    def tool_search_by_genre(genre: str, k: int = 5):
        j = GENRE_IDX.get(genre.lower())
        if j is None:
            return {"error": f"género desconocido; usa uno de {GENRES[1:]}"}
        pool = [i for i in ENGINE.popular if GENRE_MAT[i, j] > 0][:k]
        return [TITLES.get(i, str(i)) for i in pool]


    def tool_similar_to(title: str, k: int = 5):
        match = [i for i, t in TITLES.items() if title.lower() in str(t).lower()]
        if not match:
            return {"error": "título no encontrado"}
        v = SRC_B.emb[match[0]][None]; _, ids = SRC_B.index.search(v.astype(np.float32), k + 1)
        return {"base": TITLES[match[0]], "similares": [TITLES.get(int(i), str(i)) for i in ids[0] if i != match[0]][:k]}


    TOOLS = {"recommend_for_user": tool_recommend_for_user, "search_by_genre": tool_search_by_genre, "similar_to": tool_similar_to}
    TOOL_SPECS = [
        {"name": "recommend_for_user", "description": "Recomendaciones personalizadas de CineMatch para un user_id.",
         "input_schema": {"type": "object", "properties": {"user_id": {"type": "integer"}, "k": {"type": "integer"}}, "required": ["user_id"]}},
        {"name": "search_by_genre", "description": f"Títulos populares de un género. Géneros: {', '.join(GENRES[1:])}.",
         "input_schema": {"type": "object", "properties": {"genre": {"type": "string"}, "k": {"type": "integer"}}, "required": ["genre"]}},
        {"name": "similar_to", "description": "Títulos parecidos a uno dado (búsqueda por subcadena del título).",
         "input_schema": {"type": "object", "properties": {"title": {"type": "string"}, "k": {"type": "integer"}}, "required": ["title"]}},
    ]
    ''')

    C(r'''
    import re


    def agent_llm(question, user_id, max_turns=6):
        import anthropic
        client = anthropic.Anthropic()
        model = os.environ.get("CINEMATCH_LLM_MODEL", "claude-opus-5-5")
        system = (f"Eres el asistente de CineMatch. El usuario actual tiene user_id={user_id}. Usa las herramientas para "
                  "basar tus respuestas en el catálogo real; no inventes títulos. Responde en español, breve.")
        messages = [{"role": "user", "content": question}]
        for _ in range(max_turns):
            resp = client.messages.create(model=model, max_tokens=4000, system=system, tools=TOOL_SPECS, messages=messages)
            if resp.stop_reason == "refusal":
                return "No puedo ayudar con esa petición."
            messages.append({"role": "assistant", "content": resp.content})
            if resp.stop_reason != "tool_use":
                return "".join(b.text for b in resp.content if b.type == "text")
            results = []
            for b in resp.content:
                if b.type == "tool_use":
                    try:
                        out, err = TOOLS[b.name](**b.input), False
                    except Exception as e:
                        out, err = {"error": str(e)}, True
                    results.append({"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(out, ensure_ascii=False), "is_error": err})
            messages.append({"role": "user", "content": results})
        return "(límite de turnos alcanzado)"


    def agent_fallback(question, user_id):
        q = question.lower()
        if m := re.search(r"(?:como|parecid[ao]s? a)\s+(.+)", q):
            return tool_similar_to(m.group(1).strip(" ?¿."))
        for g in GENRE_IDX:
            if g in q and g != "unknown":
                return tool_search_by_genre(g)
        return tool_recommend_for_user(user_id)


    USE_LLM = bool(os.environ.get("ANTHROPIC_API_KEY"))
    for q in ["¿Qué me recomiendas para esta noche?", "Quiero algo de Sci-Fi", "Algo parecido a Star Wars"]:
        try:
            ans = agent_llm(q, u0) if USE_LLM else agent_fallback(q, u0)
        except Exception as e:
            print("LLM no disponible, uso fallback:", repr(e)[:80]); ans = agent_fallback(q, u0)
        print(f"🧑 {q}\n🤖 {ans}\n")
    E["bonus"] = True
    ''')

    C(r'''
    # E7 · Scorecard automático
    proc.terminate()
    score = pd.DataFrame([
        ("E1 Datos", E.get("E1", False), 10), ("E2 Retrieval", E.get("E2", False), 15), ("E3 Ranking", E.get("E3", False), 15),
        ("E4 Re-ranking", E.get("E4", False), 10), ("E5 Serving", E.get("E5", False), 15), ("E6 MLOps", E.get("E6", False), 15),
        ("E7 Informe (design doc abajo)", True, 10), ("⭐ Bonus agente", E.get("bonus", False), 10)], columns=["entregable", "cumple", "puntos"])
    score["obtenidos"] = score.cumple * score.puntos
    display(score)
    print(f"TOTAL: {score.obtenidos.sum()} / 100 (+10 bonus)")
    fig, ax = plt.subplots(figsize=(9, 3.5))
    ax.barh(score.entregable, score.puntos, color="#eaecee"); ax.barh(score.entregable, score.obtenidos, color="#58d68d")
    ax.invert_yaxis(); ax.set_title("Scorecard del capstone"); plt.show()
    ''')

    M(r"""
    ### E7 · *Design doc* (plantilla — ≤ 1 página)

    **1. Problema y métricas.** North star: … · online: … · guardrails: … · offline proxy: NDCG@10 en split temporal (justifica la correlación).

    **2. Arquitectura.** Fuentes (PureSVD, two-tower logQ, co-ocurrencia, popularidad) → LambdaMART (N features PIT) → MMR (λ = …) → FastAPI (caché + fallback). Diagrama del módulo 18 §1.

    **3. Resultados.** Tabla: recall por fuente, NDCG por etapa, ILD, p99, paridad. Ablación de features.

    **4. Trade-offs.** Por qué estas fuentes y no otras; λ de MMR; coste de reentrenar el two-tower vs ganancia (stale vs fresh).

    **5. Riesgos.** Feedback loops, cold start de estrenos, skew, sesgo de popularidad, privacidad del asistente.

    **6. Siguientes pasos.** A/B con interleaving como criba (mód. 15), bandits para artwork (14), SASRec como fuente secuencial (09), semantic IDs (11), CT con Prefect (17).

    ## 🚀 Retos extra (nivel staff)

    1. Añade **SASRec** (módulo 09) como quinta fuente y mide su contribución marginal al recall de la unión.
    2. Sustituye LambdaMART por un **ranker multi-tarea** (MMoE: P(ver) y rating esperado) y fusiona objetivos con pesos elegidos por *off-policy evaluation*.
    3. Simula un **A/B con interleaving** entre `capstone-v1` y una variante sin two-tower (módulo 15) usando un simulador de clics calibrado con el test.
    4. Despliega con el `reference_stack/` del módulo 16 (Redis + Redpanda + Prometheus) y conecta el flow de CT del módulo 17.
    5. Sirve el two-tower con **Triton** (ONNX) y compara p99 frente a TorchScript embebido.
    6. Reescribe el agente con **LangGraph** (módulo 12) con memoria de conversación y un nodo de *guardrails* que verifique que todos los títulos mencionados existen en el catálogo.

    ## 🤔 Reflexión final

    - ¿Qué parte de tu sistema aporta más NDCG por milisegundo de latencia? ¿Y por euro de cómputo?
    - Si solo pudieras mantener **dos** fuentes de candidatos, ¿cuáles y por qué (usa la ablación)?
    - ¿Qué métrica online usarías para decidir el λ de MMR, y cómo protegerías el experimento de efectos de novedad?
    - ¿Qué cambiaría en tu diseño si CineMatch tuviera 10⁸ ítems (UGC) en lugar de 10⁴?
    """)

    nb.save(path)


if __name__ == "__main__":
    lesson()
    project()
