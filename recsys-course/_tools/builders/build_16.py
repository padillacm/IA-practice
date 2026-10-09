"""Builder del módulo 16 · Producción y serving (lección + proyecto).

Ejecutar desde la raíz del repo:  python recsys-course/_tools/builders/build_16.py
"""
import os
import sys

sys.path.insert(0, "recsys-course/_tools")
from nbbuild import Notebook  # noqa: E402

MOD = "recsys-course/16_production_serving"
os.makedirs(MOD, exist_ok=True)

# ---------------------------------------------------------------------------
# Celdas compartidas entre lección y proyecto
# ---------------------------------------------------------------------------
DATA_CELL = r'''
import os, io, zipfile, urllib.request, time, json, math, random, warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from IPython.display import display

warnings.filterwarnings("ignore")
seed = 42
random.seed(seed); np.random.seed(seed)
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.3})

DATA_DIR, ART_DIR = "data", "artifacts"
os.makedirs(DATA_DIR, exist_ok=True); os.makedirs(ART_DIR, exist_ok=True)
ML100K_URL = "https://files.grouplens.org/datasets/movielens/ml-100k.zip"
GENRES = ["unknown", "Action", "Adventure", "Animation", "Children", "Comedy", "Crime",
          "Documentary", "Drama", "Fantasy", "Film-Noir", "Horror", "Musical", "Mystery",
          "Romance", "Sci-Fi", "Thriller", "War", "Western"]


def synthetic_movielens(n_users=943, n_items=1682, n_ratings=100_000, seed=42):
    """Fallback sin red: imita el esquema de ML-100K (gustos por género + popularidad Zipf)."""
    rng = np.random.default_rng(seed)
    item_genres = (rng.random((n_items, len(GENRES))) < 0.12).astype(int)
    item_genres[np.arange(n_items), rng.integers(1, len(GENRES), n_items)] = 1
    user_taste = rng.dirichlet(np.ones(len(GENRES)) * 0.3, n_users)
    pop = 1.0 / np.arange(1, n_items + 1) ** 0.9
    pop = pop[rng.permutation(n_items)]
    rows, t0 = [], 874_724_710  # sept-1997, como ML-100K
    per_user = rng.multinomial(n_ratings, rng.dirichlet(np.ones(n_users)))
    for u in range(n_users):
        k = max(per_user[u], 20)
        p = pop * (item_genres @ user_taste[u] + 0.02)
        p /= p.sum()
        items = rng.choice(n_items, size=min(k, n_items // 2), replace=False, p=p)
        aff = item_genres[items] @ user_taste[u]
        r = np.clip(np.round(2.5 + 6 * aff + rng.normal(0, 0.8, len(items))), 1, 5)
        ts = t0 + np.sort(rng.integers(0, 215 * 86400, len(items)))
        rows.append(pd.DataFrame({"user_id": u + 1, "item_id": items + 1, "rating": r.astype(int), "ts": ts}))
    ratings = pd.concat(rows, ignore_index=True)
    items_df = pd.DataFrame(item_genres, columns=GENRES)
    items_df.insert(0, "title", [f"Película sintética {i + 1}" for i in range(n_items)])
    items_df.insert(0, "item_id", np.arange(1, n_items + 1))
    return ratings, items_df, "Sintético (esquema ML-100K)"


def load_ml100k():
    try:
        path = os.path.join(DATA_DIR, "ml-100k.zip")
        if not os.path.exists(path):
            urllib.request.urlretrieve(ML100K_URL, path)
        with zipfile.ZipFile(path) as z:
            ratings = pd.read_csv(z.open("ml-100k/u.data"), sep="\t",
                                  names=["user_id", "item_id", "rating", "ts"])
            raw = pd.read_csv(z.open("ml-100k/u.item"), sep="|", encoding="latin-1", header=None)
        items_df = raw[[0, 1] + list(range(5, 24))].copy()
        items_df.columns = ["item_id", "title"] + GENRES
        return ratings, items_df, "MovieLens-100K"
    except Exception as e:  # sin red / URL caída → nunca bloqueamos el notebook
        print("⚠️ No se pudo descargar ML-100K, uso datos sintéticos:", repr(e)[:120])
        return synthetic_movielens()


ratings, items_df, DATASET = load_ml100k()
ratings = ratings.sort_values("ts").reset_index(drop=True)
print(DATASET, ratings.shape, "usuarios:", ratings.user_id.nunique(), "ítems:", ratings.item_id.nunique())
'''

PIPE_CELL = r'''
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds

N_USERS, N_ITEMS = int(ratings.user_id.max()) + 1, int(items_df.item_id.max()) + 1
GENRE_MAT = np.zeros((N_ITEMS, len(GENRES)), dtype=np.float32)
GENRE_MAT[items_df.item_id.values] = items_df[GENRES].values

# Split temporal global: 70 % (embeddings) · 10 % (etiquetas del ranker) · 20 % (test)
t_a, t_b = ratings.ts.quantile([0.7, 0.8]).values
train_a = ratings[ratings.ts < t_a]
train_b = ratings[(ratings.ts >= t_a) & (ratings.ts < t_b)]
test = ratings[ratings.ts >= t_b]


def item_embeddings(df, dim=64):
    """PureSVD sobre la matriz implícita (Cremonesi et al. 2010): baseline de retrieval fuerte y barato."""
    m = csr_matrix((np.ones(len(df), dtype=np.float32), (df.user_id, df.item_id)), shape=(N_USERS, N_ITEMS))
    _, s, vt = svds(m, k=dim, random_state=seed)
    emb = (vt.T * np.sqrt(s)).astype(np.float32)
    emb /= np.linalg.norm(emb, axis=1, keepdims=True) + 1e-8
    return emb


def user_vector(hist_items, emb, max_len=50):
    """'Torre de usuario' sin parámetros: media de los embeddings de su historial reciente (cf. YouTube DNN 2016)."""
    if len(hist_items) == 0:
        return None
    v = emb[np.asarray(hist_items[-max_len:])].mean(0)
    return (v / (np.linalg.norm(v) + 1e-8)).astype(np.float32)


ITEM_EMB = item_embeddings(train_a)
hist_a = train_a.groupby("user_id").item_id.apply(list).to_dict()
print("Embeddings de ítem:", ITEM_EMB.shape, "| usuarios con historial:", len(hist_a))
'''


def lesson() -> None:
    path = f"{MOD}/16_production_serving.ipynb"
    nb = Notebook("Módulo 16 · Producción y serving", colab_path=path)
    M, C = nb.md, nb.code

    M(f"""
    {nb.badge()}

    # Módulo 16 · Recomendadores en producción: arquitectura, feature stores y serving

    **Nivel:** 🔴 Experto · **Duración:** 5–6 h · **GPU:** no imprescindible (CPU basta; una T4 acelera la parte de ONNX/TorchScript) · **Unidades Colab estimadas:** 2–4

    **Prerrequisitos:** 02 (evaluación), 05 (factorización), 06 (ranking CTR), 08 (two-tower + ANN), 13 (re-ranking). Ayuda haber visto 15 (A/B).

    > Hasta ahora has entrenado modelos en un notebook. En este módulo los convertimos en un **servicio** que responde en
    > decenas de milisegundos, con features frescas y coherentes con las de entrenamiento, y que aguanta carga.
    > Es el salto de *data scientist* a *ML platform engineer*.
    """)

    M(r"""
    ## 🎯 Objetivos de aprendizaje

    Al terminar serás capaz de:

    1. **Dibujar y justificar** la arquitectura offline / nearline / online de Netflix y decidir qué cómputo va en cada capa.
    2. **Repartir un presupuesto de latencia** (p99) entre las etapas de un serving multi-etapa y razonar sobre la cola de latencia (*tail at scale*).
    3. **Demostrar** con código el *data leakage* que produce un join ingenuo de features y **corregirlo** con *point-in-time joins* (a mano y con **Feast**).
    4. **Implementar** un microservicio de recomendación (FastAPI + FAISS + LightGBM + caché Redis + fallback de cold start) y medir su latencia por etapa.
    5. **Exportar** un ranker a **TorchScript** y **ONNX**, verificar paridad numérica y comparar latencias por tamaño de batch.
    6. **Detectar** *training-serving skew* con un chequeo de paridad de features.
    7. **Hacer un test de carga** y leer curvas de throughput / p99 para dimensionar réplicas.
    8. **Comparar** Triton, BentoML, Ray Serve y TorchServe, y explicar por qué TorchRec / NVIDIA Merlin existen (sharding de tablas de embeddings).
    """)

    # ------------------------------------------------------------------ Intuición
    M(r"""
    ## 💡 1. Intuición: el modelo es la parte pequeña

    En *Hidden Technical Debt in Machine Learning Systems* (Sculley et al., NeurIPS 2015) hay una figura famosa: una
    cajita negra diminuta («ML code») rodeada de cajas enormes — recogida de datos, extracción de features, verificación,
    serving, monitoreo, gestión de recursos… En recomendación esto se exagera, porque:

    - **Cada petición es personalizada**: no puedes cachear «la respuesta» para todos como en una web estática.
    - **El catálogo es grande** (de 10⁴ a 10⁹ ítems): no puedes puntuar todos los ítems con un modelo pesado en 100 ms.
    - **El contexto cambia en segundos**: acabas de ver un capítulo de *Dark*; si la home no lo refleja al volver, la experiencia es mala.

    Netflix lo resolvió (Amatriain & Basilico, 2013) separando el cómputo según **cuándo** puede hacerse:

    | Capa | Cuándo se ejecuta | Latencia tolerada | Datos | Ejemplo en CineMatch |
    |---|---|---|---|---|
    | **Offline** | por lotes (horas/días) | horas | todo el histórico | entrenar embeddings, ranker, precomputar candidatos |
    | **Nearline** | en respuesta a eventos (segundos/minutos) | segundos | eventos recientes | actualizar el vector del usuario tras un *play* |
    | **Online** | en la petición del usuario | ~10–200 ms | contexto de la petición + features cacheadas | retrieval ANN + ranking + re-ranking |

    💡 **Analogía con lo que ya sabes de MLOps:** offline = tu pipeline de entrenamiento en Airflow; online = tu endpoint
    de inferencia; *nearline* es la pieza que casi nadie tiene en un proyecto de ML clásico: un **consumidor de eventos**
    (Kafka) que recalcula estado del usuario sin esperar al siguiente batch y sin ralentizar la petición.
    """)

    C(r'''
    !pip install -q fastapi uvicorn faiss-cpu lightgbm fakeredis redis requests httpx onnx onnxruntime onnxscript pyarrow
    ''')

    C(DATA_CELL)

    C(r'''
    def box(ax, xy, w, h, text, color, fs=9):
        ax.add_patch(mpatches.FancyBboxPatch(xy, w, h, boxstyle="round,pad=0.02", fc=color, ec="k", lw=1))
        ax.text(xy[0] + w / 2, xy[1] + h / 2, text, ha="center", va="center", fontsize=fs)


    def arrow(ax, a, b, text="", color="k"):
        ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="->", lw=1.4, color=color))
        if text:
            ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 0.12, text, fontsize=7.5, ha="center", color=color)


    fig, ax = plt.subplots(figsize=(13, 6.5)); ax.set_xlim(0, 13); ax.set_ylim(0, 7); ax.axis("off")
    for y, name, c in [(5.2, "OFFLINE (batch · horas)", "#dbe9f6"), (2.9, "NEARLINE (eventos · segundos)", "#fdebd0"),
                       (0.4, "ONLINE (petición · ms)", "#d5f5e3")]:
        ax.add_patch(mpatches.Rectangle((0.1, y - 0.2), 12.8, 1.9, fc=c, ec="none", alpha=0.6))
        ax.text(0.2, y + 1.5, name, fontsize=10, weight="bold")
    box(ax, (0.4, 5.3), 2.2, 0.9, "Data lake\n(Hive/Iceberg, S3)", "white")
    box(ax, (3.2, 5.3), 2.4, 0.9, "Entrenamiento\n(Spark, GPUs)", "white")
    box(ax, (6.2, 5.3), 2.4, 0.9, "Batch scoring /\ncandidatos precomputados", "white")
    box(ax, (9.3, 5.3), 2.6, 0.9, "Registry de modelos\n+ feature store offline", "white")
    box(ax, (0.4, 3.0), 2.2, 0.9, "Bus de eventos\n(Kafka / Hermes)", "white")
    box(ax, (3.2, 3.0), 2.4, 0.9, "Consumidor nearline\n(Flink / Manhattan)", "white")
    box(ax, (6.2, 3.0), 2.4, 0.9, "Estado del usuario\n(vector, recientes)", "white")
    box(ax, (9.3, 3.0), 2.6, 0.9, "Online store / caché\n(Redis, EVCache, Cassandra)", "white")
    box(ax, (0.4, 0.6), 2.2, 0.9, "App cliente\n(TV, móvil, web)", "white")
    box(ax, (3.2, 0.6), 2.4, 0.9, "API de recomendación\n(FastAPI / gRPC)", "white")
    box(ax, (6.2, 0.6), 2.4, 0.9, "Retrieval ANN →\nranking → re-ranking", "white")
    box(ax, (9.3, 0.6), 2.6, 0.9, "Respuesta (filas\nde la home)", "white")
    arrow(ax, (2.6, 5.75), (3.2, 5.75)); arrow(ax, (5.6, 5.75), (6.2, 5.75)); arrow(ax, (8.6, 5.75), (9.3, 5.75))
    arrow(ax, (2.6, 3.45), (3.2, 3.45)); arrow(ax, (5.6, 3.45), (6.2, 3.45)); arrow(ax, (8.6, 3.45), (9.3, 3.45))
    arrow(ax, (2.6, 1.05), (3.2, 1.05)); arrow(ax, (5.6, 1.05), (6.2, 1.05)); arrow(ax, (8.6, 1.05), (9.3, 1.05))
    arrow(ax, (1.5, 1.5), (1.5, 3.0), "eventos (play, pausa)", "#c0392b")
    arrow(ax, (1.5, 3.9), (1.5, 5.3), "logs → data lake", "#c0392b")
    arrow(ax, (10.6, 5.3), (10.6, 3.9), "modelos + features", "#2471a3")
    arrow(ax, (9.3, 3.2), (8.0, 1.5), "features frescas", "#2471a3")
    ax.set_title("Arquitectura offline / nearline / online (inspirada en Netflix, Amatriain & Basilico 2013)", fontsize=12)
    plt.show()
    ''')

    M(r"""
    El diagrama tiene tres «bucles» con relojes distintos. La pregunta de diseño que te harán en cualquier entrevista
    (y que verás en el módulo 18) es: **¿qué puede ser obsoleto y cuánto?** Los factores de ítem de una factorización
    pueden recalcularse cada día sin drama; el «seguir viendo» no puede tener ni un minuto de retraso.

    ### El funnel multi-etapa y el presupuesto de latencia

    Ya conoces la cascada retrieval → ranking → re-ranking (módulos 00, 06, 08, 13). En producción cada etapa tiene un
    **presupuesto de tiempo** y un **tamaño de entrada**: el coste total es aproximadamente

    $$\text{coste} \approx \sum_{s} N_s \cdot c_s,$$

    donde $N_s$ es el número de candidatos que entran en la etapa $s$ y $c_s$ el coste de puntuar uno. Como $c_s$ crece
    por órdenes de magnitud (producto escalar → GBDT → transformer), $N_s$ debe decrecer por órdenes de magnitud.
    """)

    C(r'''
    stages = [("Catálogo", 1e6, "#bdc3c7"), ("Retrieval (ANN + reglas)", 1e3, "#85c1e9"),
              ("Pre-ranking ligero", 300, "#76d7c4"), ("Ranking pesado", 100, "#f8c471"), ("Re-ranking + negocio", 20, "#f1948a")]
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.8))
    ax = axes[0]; ax.axis("off"); ax.set_xlim(-1.1, 1.1); ax.set_ylim(0, len(stages))
    for i, (name, n, c) in enumerate(stages):
        w = 0.15 + 0.85 * (np.log10(n) / 6)
        y = len(stages) - i - 1
        ax.add_patch(mpatches.FancyBboxPatch((-w, y + 0.1), 2 * w, 0.8, boxstyle="round,pad=0.01", fc=c, ec="k"))
        ax.text(0, y + 0.5, f"{name}\n{int(n):,} ítems".replace(",", "."), ha="center", va="center", fontsize=9)
    ax.set_title("Funnel multi-etapa: cada etapa reduce candidatos ~10×")

    # Presupuesto de latencia (p99) tipo cascada
    budget = [("Red + auth", 8), ("Features usuario\n(online store)", 7), ("Retrieval ANN", 10),
              ("Features ítem\n(batch get)", 8), ("Ranking (GBDT/NN)", 25), ("Re-ranking\ndiversidad", 5),
              ("Serialización", 3), ("Margen", 14)]
    ax = axes[1]; acc = 0
    for i, (name, ms) in enumerate(budget):
        ax.bar(i, ms, bottom=acc, color="#5dade2" if name != "Margen" else "#d5dbdb", ec="k")
        ax.text(i, acc + ms / 2, f"{ms} ms", ha="center", va="center", fontsize=8)
        acc += ms
    ax.axhline(80, color="#c0392b", ls="--"); ax.text(0, 82, "SLO p99 = 80 ms", color="#c0392b")
    ax.set_xticks(range(len(budget))); ax.set_xticklabels([b[0] for b in budget], rotation=35, ha="right", fontsize=8)
    ax.set_ylabel("ms acumulados"); ax.set_title("Presupuesto de latencia (cascada / waterfall) — valores ilustrativos")
    plt.tight_layout(); plt.show()
    ''')

    M(r"""
    ⚠️ Los milisegundos de la cascada son **ilustrativos** (un orden de magnitud razonable para una home), no cifras de
    Netflix. Más abajo mediremos los nuestros con un servicio real y dibujaremos la cascada **medida**.

    ## 📐 2. Teoría: colas de latencia, capacidad y cachés

    **(a) La cola de la latencia manda (*The Tail at Scale*, Dean & Barroso, CACM 2013).** Si una petición hace *fan-out* a
    $n$ servicios independientes (shards del índice, feature stores…) y espera a todos, su latencia es el máximo:

    $$P(T_{\max} \le t) = \prod_{i=1}^{n} P(T_i \le t) = F(t)^n.$$

    Si cada shard cumple $t$ el 99 % de las veces ($F(t)=0{,}99$), con $n=100$ shards solo el $0{,}99^{100}\approx 36{,}6\%$ de
    peticiones cumplen $t$. Por eso se optimiza **p99/p999**, no la media, y se usan *hedged requests* (lanzar una réplica
    de la petición si la primera tarda más que el p95).

    **(b) Ley de Little y colas.** Con tasa de llegada $\lambda$ (peticiones/s) y tiempo en el sistema $W$, el número medio
    de peticiones en vuelo es $L=\lambda W$. En una cola M/M/1 con tasa de servicio $\mu$, $W = 1/(\mu-\lambda)$: la latencia
    **explota** cuando la utilización $\rho=\lambda/\mu \to 1$. Regla práctica: dimensiona para $\rho \lesssim 0{,}6$–$0{,}7$ en el pico.

    **(c) Caché.** Con tasa de acierto $h$, latencia de acierto $\ell_h$ y de fallo $\ell_m$:
    $\mathbb{E}[\ell] = h\,\ell_h + (1-h)\,\ell_m$. Pero el p99 lo dominan los fallos en cuanto $1-h > 1\%$.

    **(d) Point-in-time correctness.** Sea un ejemplo de entrenamiento $(u, i, t, y)$ y una feature $f$ con historial de
    valores $\{(f_k, \tau_k)\}$. El valor correcto es el último **disponible** antes de $t$:

    $$f^{\text{PIT}}(t) = f_{k^*},\quad k^* = \arg\max_k \{\tau_k : \tau_k \le t - \delta\},$$

    con $\delta$ el retraso de publicación del pipeline (si la feature se calcula en un batch nocturno, a las 15:00 aún no
    existe el valor de hoy). Usar $f$ calculada con datos posteriores a $t$ es **leakage** de futuro.
    """)

    C(r'''
    rng = np.random.default_rng(seed)
    lat = rng.lognormal(mean=np.log(5), sigma=0.5, size=(20000, 128))  # ms por shard
    lat[rng.random(lat.shape) < 0.002] *= 20  # 0,2 % de "hipos" (GC, red, vecino ruidoso)
    ns = [1, 2, 4, 8, 16, 32, 64, 128]
    p50 = [np.percentile(lat[:, :n].max(1), 50) for n in ns]
    p99 = [np.percentile(lat[:, :n].max(1), 99) for n in ns]

    # Hedged requests: si un shard tarda > p95, lanzamos una copia y nos quedamos con la primera respuesta
    p95_shard = np.percentile(lat, 95)
    backup = rng.lognormal(np.log(5), 0.5, lat.shape) + p95_shard
    hedged = np.where(lat > p95_shard, np.minimum(lat, backup), lat)
    p99_h = [np.percentile(hedged[:, :n].max(1), 99) for n in ns]

    fig, ax = plt.subplots(1, 2, figsize=(13, 4))
    ax[0].plot(ns, p50, "o-", label="p50"); ax[0].plot(ns, p99, "o-", label="p99")
    ax[0].plot(ns, p99_h, "o--", label="p99 con hedged requests")
    ax[0].set_xscale("log", base=2); ax[0].set_xlabel("nº de shards en el fan-out"); ax[0].set_ylabel("ms")
    ax[0].set_title("Tail at scale: el máximo de n latencias"); ax[0].legend()
    t = np.linspace(0.5, 1, 200)
    for n in [1, 10, 100]:
        ax[1].plot(t, t ** n, label=f"n={n}")
    ax[1].set_xlabel("F(t) por shard"); ax[1].set_ylabel("P(petición completa ≤ t)"); ax[1].legend()
    ax[1].set_title("F(t)^n")
    plt.tight_layout(); plt.show()
    print(f"Con 64 shards: p99 = {p99[6]:.1f} ms → con hedging {p99_h[6]:.1f} ms (coste: ~5 % más peticiones)")
    ''')

    # ------------------------------------------------------------------ Pipeline base
    M(r"""
    ## 3. El modelo que vamos a servir

    Para centrarnos en la ingeniería usamos un pipeline compacto pero realista (los módulos 05–08 lo hacen mejor):

    - **Retrieval:** embeddings de ítem con *PureSVD* (Cremonesi et al., RecSys 2010) e índice **FAISS**. El vector de usuario es
      la **media de los embeddings de sus últimos 50 ítems** — una torre de usuario sin parámetros que permite actualizar al
      usuario *nearline* sin reentrenar (la misma idea que el *averaging* de YouTube DNN, Covington et al. 2016).
    - **Ranking:** LightGBM binario sobre ~100 candidatos con features de usuario, de ítem y de cruce.
    - **Split temporal global** 70/10/20: embeddings con el 70 %, etiquetas del ranker en el 10 % siguiente, test en el 20 % final.
    """)

    C(PIPE_CELL)

    C(r'''
    import faiss

    index_flat = faiss.IndexFlatIP(ITEM_EMB.shape[1])     # exacto (producto interno = coseno, vectores normalizados)
    index_flat.add(ITEM_EMB)
    index_hnsw = faiss.IndexHNSWFlat(ITEM_EMB.shape[1], 32, faiss.METRIC_INNER_PRODUCT)
    index_hnsw.hnsw.efSearch = 64
    index_hnsw.add(ITEM_EMB)


    def retrieve(hist, k=100, index=index_flat):
        v = user_vector(hist, ITEM_EMB)
        if v is None:
            return np.array([], dtype=int), np.array([])
        scores, ids = index.search(v[None], k + len(hist))
        seen = set(hist)
        keep = [(i, s) for i, s in zip(ids[0], scores[0]) if i not in seen and i > 0][:k]
        return np.array([i for i, _ in keep]), np.array([s for _, s in keep])


    # Recall@100 del retrieval sobre el test (¿está lo que verá después entre los 100 candidatos?)
    test_pos = test.groupby("user_id").item_id.apply(set).to_dict()
    users_eval = [u for u in test_pos if u in hist_a][:300]
    for name, idx in [("Flat", index_flat), ("HNSW", index_hnsw)]:
        t0 = time.perf_counter()
        rec = np.mean([len(set(retrieve(hist_a[u], 100, idx)[0]) & test_pos[u]) / len(test_pos[u]) for u in users_eval])
        print(f"{name:5s} Recall@100 = {rec:.3f} | {1e3 * (time.perf_counter() - t0) / len(users_eval):.2f} ms/usuario")
    ''')

    M(r"""
    ## 4. Feature store y *point-in-time correctness*

    ### 4.1 El bug más caro de la industria, en 20 líneas

    El ranker necesita features como «popularidad del ítem» o «nota media del ítem». La forma ingenua de construir el
    dataset de entrenamiento es calcular esas features **sobre todo el histórico** y hacer un `merge` por `item_id`.
    Problema: para un ejemplo del lunes, la popularidad incluye las vistas del martes… incluidas **las de la propia etiqueta**.

    El ranker aprende «popularidad alta ⇒ clic», el AUC offline sale espectacular, y en producción (donde la feature solo
    puede contener el pasado) el modelo se desinfla. Vamos a medirlo.
    """)

    C(r'''
    # Snapshots diarios de features de ítem. Un batch nocturno calcula las stats del día d y las PUBLICA al inicio de d+1.
    ev = ratings[["item_id", "rating", "ts"]].copy()
    ev["day"] = ev.ts // 86400
    daily = ev.groupby(["item_id", "day"]).agg(n=("rating", "size"), s=("rating", "sum")).reset_index().sort_values(["item_id", "day"])
    daily["pop_cum"] = daily.groupby("item_id").n.cumsum()
    daily["rating_mean_cum"] = daily.groupby("item_id").s.cumsum() / daily.pop_cum
    daily["event_timestamp"] = pd.to_datetime((daily.day + 1) * 86400, unit="s", utc=True)  # disponible al día siguiente
    item_stats = daily[["item_id", "event_timestamp", "pop_cum", "rating_mean_cum"]].reset_index(drop=True)
    item_stats.to_parquet(f"{DATA_DIR}/item_stats.parquet")


    def make_examples(df_pos, n_neg=4, seed=seed):
        """Positivos = interacciones reales; negativos = ítems aleatorios en el mismo instante."""
        r = np.random.default_rng(seed)
        pos = df_pos[["user_id", "item_id", "ts"]].assign(label=1)
        neg = pos.loc[pos.index.repeat(n_neg)].copy()
        neg["item_id"] = r.integers(1, N_ITEMS, len(neg)); neg["label"] = 0
        out = pd.concat([pos, neg], ignore_index=True)
        out["event_timestamp"] = pd.to_datetime(out.ts, unit="s", utc=True)
        return out.sort_values("event_timestamp").reset_index(drop=True)


    def naive_join(ex):
        full = ev.groupby("item_id").agg(pop_cum=("rating", "size"), rating_mean_cum=("rating", "mean")).reset_index()
        return ex.merge(full, on="item_id", how="left").fillna({"pop_cum": 0, "rating_mean_cum": 3.0})


    def pit_join(ex, stats=item_stats):
        """Point-in-time join: último snapshot con event_timestamp <= instante del ejemplo (merge_asof)."""
        out = pd.merge_asof(ex.sort_values("event_timestamp"), stats.sort_values("event_timestamp"),
                            on="event_timestamp", by="item_id", direction="backward")
        return out.fillna({"pop_cum": 0, "rating_mean_cum": 3.0})


    ex_train, ex_val = make_examples(train_a.sample(frac=0.5, random_state=seed)), make_examples(train_b)
    print(pit_join(ex_val).head(3)[["user_id", "item_id", "event_timestamp", "pop_cum", "label"]])
    ''')

    C(r'''
    import lightgbm as lgb
    from sklearn.metrics import roc_auc_score

    FEATS_PIT = ["pop_cum", "rating_mean_cum"]
    params = dict(objective="binary", learning_rate=0.05, num_leaves=31, n_estimators=200, verbose=-1, random_state=seed)
    res = {}
    for name, joiner in [("Join ingenuo (leakage)", naive_join), ("Point-in-time", pit_join)]:
        tr, va_off = joiner(ex_train), joiner(ex_val)          # 'offline': el val se construye igual que el train
        va_prod = pit_join(ex_val)                              # 'producción': solo existe el pasado
        m = lgb.LGBMClassifier(**params).fit(tr[FEATS_PIT], tr.label)
        res[name] = (roc_auc_score(va_off.label, m.predict_proba(va_off[FEATS_PIT])[:, 1]),
                     roc_auc_score(va_prod.label, m.predict_proba(va_prod[FEATS_PIT])[:, 1]))

    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(2)
    for j, (lab, c) in enumerate([("AUC offline (lo que reportas)", "#5dade2"), ("AUC en producción (lo que pasa)", "#e67e22")]):
        ax.bar(x + 0.38 * j, [res[k][j] for k in res], 0.38, label=lab, color=c)
    for i, k in enumerate(res):
        ax.text(i + 0.19, max(res[k]) + 0.01, f"gap = {res[k][0] - res[k][1]:+.3f}", ha="center")
    ax.set_xticks(x + 0.19); ax.set_xticklabels(list(res)); ax.set_ylim(0.5, 1.0); ax.set_ylabel("AUC")
    ax.set_title("Leakage temporal: el join ingenuo infla la métrica offline"); ax.legend(loc="lower right")
    plt.show()
    print({k: tuple(round(v, 3) for v in vals) for k, vals in res.items()})
    ''')

    M(r"""
    🧪 **Lee el gráfico:** con el join ingenuo, la AUC offline es claramente superior a la que obtienes con las features que
    existirían en producción. Con el *point-in-time join* la métrica offline **predice** la de producción (gap ≈ 0). Este es el
    motivo número uno por el que existen los feature stores: Netflix construyó un sistema de *time travel* de features
    («DeLorean») precisamente para regenerar features tal y como eran en el pasado (Sadekar & Jiang, *Time Travel based Feature
    Generation*, SysML 2018), y Uber lo integró en Michelangelo (Del Balso & Hermann, 2017).

    ### 4.2 Lo mismo con Feast

    **Feast** es el feature store open source más usado. Conceptos:

    - **Entity**: la clave (`item_id`, `user_id`).
    - **Data source / offline store**: tablas históricas con `event_timestamp` (parquet, BigQuery, Snowflake, Spark…).
    - **FeatureView**: grupo de features + entidad + fuente + `ttl` (cuánto vale un valor antes de considerarse caducado).
    - `get_historical_features(entity_df)` → **point-in-time join** para entrenamiento.
    - `materialize` → copia el último valor de cada entidad al **online store** (SQLite en local; Redis/DynamoDB/Bigtable en producción).
    - `get_online_features(entity_rows)` → lectura de baja latencia en serving. **Mismas definiciones** para ambos caminos ⇒ menos skew.
    """)

    C(r'''
    # Feast puede tardar ~1 min en instalarse. Si falla en tu versión de Colab, el resto del notebook sigue funcionando.
    !pip install -q feast
    ''')

    C(r'''
    import pathlib, textwrap
    from datetime import timedelta

    REPO = pathlib.Path("feature_repo"); REPO.mkdir(exist_ok=True)
    (REPO / "feature_store.yaml").write_text(textwrap.dedent(f"""
        project: cinematch
        registry: {os.path.abspath(DATA_DIR)}/registry.db
        provider: local
        online_store:
          type: sqlite
          path: {os.path.abspath(DATA_DIR)}/online_store.db
        offline_store:
          type: file
        entity_key_serialization_version: 3
    """))
    try:
        from feast import Entity, FeatureStore, FeatureView, Field, FileSource
        from feast.types import Float32, Int64
        from feast.value_type import ValueType

        item = Entity(name="item", join_keys=["item_id"], value_type=ValueType.INT64)
        item_src = FileSource(path=os.path.abspath(f"{DATA_DIR}/item_stats.parquet"), timestamp_field="event_timestamp")
        item_stats_fv = FeatureView(name="item_stats", entities=[item], ttl=timedelta(days=3650),
                                    schema=[Field(name="pop_cum", dtype=Int64), Field(name="rating_mean_cum", dtype=Float32)],
                                    source=item_src, online=True)
        fs = FeatureStore(repo_path=str(REPO))
        fs.apply([item, item_stats_fv])
        FEAST_OK = True
    except Exception as e:
        FEAST_OK = False
        print("⚠️ Feast no disponible en este entorno:", repr(e)[:200])
    print("FEAST_OK =", FEAST_OK)
    ''')

    C(r'''
    if FEAST_OK:
        # Mismo ítem consultado en tres instantes: Feast devuelve el valor vigente en cada uno (PIT)
        top_item = int(ratings.item_id.value_counts().index[0])
        when = pd.to_datetime([ratings.ts.quantile(q) for q in (0.1, 0.5, 0.9)], unit="s", utc=True)
        entity_df = pd.DataFrame({"item_id": [top_item] * 3, "event_timestamp": when})
        hist = fs.get_historical_features(entity_df=entity_df,
                                          features=["item_stats:pop_cum", "item_stats:rating_mean_cum"]).to_df()
        display(hist.sort_values("event_timestamp"))

        # Comprobación: Feast == nuestro merge_asof en el set de validación
        sample = ex_val.sample(2000, random_state=seed)[["item_id", "event_timestamp"]].reset_index(drop=True)
        f_df = fs.get_historical_features(entity_df=sample, features=["item_stats:pop_cum"]).to_df()
        ours = pit_join(sample.assign(user_id=0, ts=0, label=0))
        cmp = f_df.merge(ours[["item_id", "event_timestamp", "pop_cum"]], on=["item_id", "event_timestamp"], suffixes=("_feast", "_ours"))
        agree = (cmp.pop_cum_feast.fillna(0).astype(float) == cmp.pop_cum_ours.astype(float)).mean()
        print(f"Coincidencia Feast vs merge_asof: {agree:.1%}")

        # Materializamos al online store (SQLite) y leemos como lo haría el servicio
        fs.materialize(start_date=item_stats.event_timestamp.min().to_pydatetime() - timedelta(days=1),
                       end_date=item_stats.event_timestamp.max().to_pydatetime() + timedelta(days=1))
        online = fs.get_online_features(features=["item_stats:pop_cum", "item_stats:rating_mean_cum"],
                                        entity_rows=[{"item_id": top_item}, {"item_id": 2}]).to_dict()
        print("Online store:", online)
    ''')

    C(r'''
    # Diagrama del PIT join: tres consultas, snapshots diarios y el retraso de publicación δ
    snaps = item_stats[item_stats.item_id == int(ratings.item_id.value_counts().index[0])].iloc[::7].head(12)
    fig, ax = plt.subplots(figsize=(12, 3.2))
    ax.step(snaps.event_timestamp, snaps.pop_cum, where="post", color="#2471a3", label="valor publicado de pop_cum")
    ax.scatter(snaps.event_timestamp, snaps.pop_cum, color="#2471a3", zorder=3)
    q = snaps.event_timestamp.iloc[[2, 6, 10]] + pd.Timedelta(hours=60)
    for t in q:
        v = snaps[snaps.event_timestamp <= t].pop_cum.iloc[-1]
        ax.axvline(t, color="#c0392b", ls="--", alpha=0.7)
        ax.annotate(f"ejemplo en t\n→ usa {v}", (t, v), xytext=(10, -35), textcoords="offset points", fontsize=8,
                    color="#c0392b", arrowprops=dict(arrowstyle="->", color="#c0392b"))
    ax.set_title("Point-in-time join: cada ejemplo ve el último valor publicado ANTES de su instante")
    ax.set_ylabel("pop_cum"); ax.legend(loc="upper left"); plt.tight_layout(); plt.show()
    ''')

    # ------------------------------------------------------------------ Ranker
    M(r"""
    ## 5. Entrenar el ranker con features correctas

    Ahora construimos el dataset del ranker **como lo verá producción**: para cada usuario generamos 100 candidatos con el
    retrieval (historial hasta $t_a$) y etiquetamos con lo que vio en $[t_a, t_b)$. Features:

    | Feature | Tipo | Fuente en serving |
    |---|---|---|
    | `retr_score` | cruce | calculada en la petición (ANN) |
    | `retr_rank` | cruce | idem |
    | `pop_cum`, `rating_mean_cum` | ítem | online store (batch diario) |
    | `genre_affinity` | cruce | perfil de géneros del usuario (online store) · géneros del ítem |
    | `user_n`, `user_mean` | usuario | online store |
    """)

    C(r'''
    RANK_FEATS = ["retr_score", "retr_rank", "pop_cum", "rating_mean_cum", "genre_affinity", "user_n", "user_mean"]


    def user_profile(df):
        g = df.groupby("user_id")
        prof = pd.DataFrame({"user_n": g.size(), "user_mean": g.rating.mean()})
        gen = pd.DataFrame(GENRE_MAT[df.item_id.values], index=df.user_id.values).groupby(level=0).mean()
        gen = gen.div(np.linalg.norm(gen.values, axis=1) + 1e-8, axis=0)
        return prof, gen


    def item_feats_asof(t_cut):
        snap = item_stats[item_stats.event_timestamp <= pd.Timestamp(t_cut, unit="s", tz="UTC")]
        last = snap.groupby("item_id").tail(1).set_index("item_id")[["pop_cum", "rating_mean_cum"]]
        return last.reindex(range(N_ITEMS)).fillna({"pop_cum": 0, "rating_mean_cum": 3.0})


    def build_candidates(hist, users, t_cut, k=100, labels=None):
        prof, gen = user_profile(ratings[ratings.ts < t_cut])
        itf = item_feats_asof(t_cut)
        rows = []
        for u in users:
            ids, sc = retrieve(hist[u], k)
            if len(ids) == 0:
                continue
            aff = GENRE_MAT[ids] @ gen.loc[u].values / (np.linalg.norm(GENRE_MAT[ids], axis=1) + 1e-8)
            d = pd.DataFrame({"user_id": u, "item_id": ids, "retr_score": sc, "retr_rank": np.arange(len(ids)),
                              "genre_affinity": aff, "user_n": prof.loc[u, "user_n"], "user_mean": prof.loc[u, "user_mean"]})
            rows.append(d)
        out = pd.concat(rows, ignore_index=True).join(itf, on="item_id")
        if labels is not None:
            out["label"] = [int(i in labels.get(u, ())) for u, i in zip(out.user_id, out.item_id)]
        return out


    lab_b = train_b.groupby("user_id").item_id.apply(set).to_dict()
    users_b = [u for u in lab_b if u in hist_a]
    cand_tr = build_candidates(hist_a, users_b, t_a, labels=lab_b)
    grp = cand_tr.groupby("user_id").label.transform("max") > 0
    cand_tr = cand_tr[grp]                      # solo usuarios con algún positivo entre los candidatos
    ranker = lgb.LGBMClassifier(**params).fit(cand_tr[RANK_FEATS], cand_tr.label)
    print("Ejemplos ranker:", cand_tr.shape, "| tasa de positivos:", round(cand_tr.label.mean(), 4))
    ''')

    C(r'''
    def ndcg_at_k(ranked, relevant, k=10):
        gains = [1.0 / np.log2(r + 2) for r, i in enumerate(ranked[:k]) if i in relevant]
        ideal = sum(1.0 / np.log2(r + 2) for r in range(min(k, len(relevant))))
        return sum(gains) / ideal if ideal else 0.0


    hist_b = ratings[ratings.ts < t_b].groupby("user_id").item_id.apply(list).to_dict()
    users_t = [u for u in test_pos if u in hist_b][:400]
    cand_te = build_candidates(hist_b, users_t, t_b)
    cand_te["p"] = ranker.predict_proba(cand_te[RANK_FEATS])[:, 1]
    m_retr, m_rank = [], []
    for u, g in cand_te.groupby("user_id"):
        m_retr.append(ndcg_at_k(list(g.sort_values("retr_rank").item_id), test_pos[u]))
        m_rank.append(ndcg_at_k(list(g.sort_values("p", ascending=False).item_id), test_pos[u]))
    print(f"NDCG@10 solo retrieval = {np.mean(m_retr):.4f} | retrieval + ranker = {np.mean(m_rank):.4f}")
    imp = pd.Series(ranker.booster_.feature_importance("gain"), index=RANK_FEATS).sort_values()
    imp.plot.barh(figsize=(7, 3), title="Importancia (gain) de las features del ranker", color="#48c9b0"); plt.show()
    ''')

    # ------------------------------------------------------------------ Nearline
    M(r"""
    ## 6. Eventos y nearline: Kafka / Redpanda

    En producción, cada *play*, pausa o valoración se publica en un **topic** de Kafka (o Redpanda, compatible con la API de
    Kafka y sin JVM). Varios consumidores leen el mismo stream con propósitos distintos: uno escribe al data lake (para
    reentrenar), otro actualiza features nearline (Flink, Kafka Streams, un worker Python), otro alimenta el monitoreo.

    Conceptos que debes dominar: **partición** (unidad de paralelismo y de orden; particiona por `user_id` para conservar
    el orden de los eventos de cada usuario), **consumer group** (reparto de particiones entre réplicas), **offset**
    (posición; *commit* tras procesar ⇒ semántica *at-least-once*, así que tus actualizaciones deben ser **idempotentes**),
    **retención** (permite *replay* para reconstruir features).

    En Colab no tenemos Docker, así que simulamos el bus con una cola en memoria y un consumidor en un hilo. El código de
    producción equivalente (con `confluent-kafka`) está en `reference_stack/nearline/consumer.py`.

    🧪 **Experimento:** ¿cuánto vale la frescura? Comparamos predecir el siguiente ítem del usuario con su vector
    **congelado** en el último batch ($t_b$) vs **actualizado nearline** tras cada evento.
    """)

    C(r'''
    import queue, threading
    import fakeredis

    r = fakeredis.FakeRedis(decode_responses=True)
    for u, h in hist_b.items():                       # estado inicial = último batch
        r.rpush(f"hist:{u}", *h[-50:])

    bus: "queue.Queue[dict]" = queue.Queue()
    lags = []


    def nearline_consumer(stop):
        while not stop.is_set() or not bus.empty():
            try:
                e = bus.get(timeout=0.05)
            except queue.Empty:
                continue
            key = f"hist:{e['user_id']}"
            r.rpush(key, e["item_id"]); r.ltrim(key, -50, -1)   # idempotencia aproximada: lista acotada
            lags.append(time.perf_counter() - e["sent_at"])
            bus.task_done()


    stream = test[test.user_id.isin(users_t[:150])].sort_values("ts")
    stop = threading.Event(); th = threading.Thread(target=nearline_consumer, args=(stop,), daemon=True); th.start()
    hits_frozen, hits_fresh = [], []
    for _, e in stream.iterrows():
        u, i = int(e.user_id), int(e.item_id)
        bus.join()                                     # el consumidor ya procesó los eventos anteriores
        fresh_hist = [int(x) for x in r.lrange(f"hist:{u}", 0, -1)]
        hits_frozen.append(i in set(retrieve(hist_b.get(u, []), 50)[0]))
        hits_fresh.append(i in set(retrieve(fresh_hist, 50)[0]))
        bus.put({"user_id": u, "item_id": i, "sent_at": time.perf_counter()})
    stop.set(); th.join()
    print(f"HitRate@50 siguiente ítem — congelado: {np.mean(hits_frozen):.3f} | nearline: {np.mean(hits_fresh):.3f}")
    print(f"Lag del consumidor p50={1e3*np.median(lags):.2f} ms p99={1e3*np.percentile(lags, 99):.2f} ms")
    ''')

    C(r'''
    w = 300
    roll = lambda x: pd.Series(np.asarray(x, float)).rolling(w, min_periods=50).mean()
    fig, ax = plt.subplots(figsize=(11, 3.8))
    ax.plot(roll(hits_frozen), label="vector congelado en el último batch")
    ax.plot(roll(hits_fresh), label="vector actualizado nearline")
    ax.set_xlabel("eventos del stream de test (orden temporal)"); ax.set_ylabel(f"HitRate@50 (media móvil {w})")
    ax.set_title("El valor de la frescura: cuanto más se aleja el batch, más gana el nearline"); ax.legend(); plt.show()
    ''')

    # ------------------------------------------------------------------ Cache
    M(r"""
    ## 7. Caché con Redis: cuándo ayuda y cuándo engaña

    Patrones típicos en recsys:

    - **Cache-aside de la respuesta completa** (`recs:{user}` con TTL): muy eficaz en la home porque los usuarios recargan.
      Riesgo: servir recomendaciones viejas tras un evento → **invalida** la clave cuando llega un evento del usuario (nearline).
    - **Caché de features** (vector de usuario, features de ítem): el *online store* ya es una caché.
    - **Precomputación offline** (candidatos por usuario en batch): Netflix lo describía como una forma de mover cómputo fuera del camino crítico.

    En Colab usamos **fakeredis** (misma API que `redis-py`). Si tienes un Redis real, cambia a `redis.Redis(host=..., port=6379)`.
    """)

    C(r'''
    def simulate_cache(ttl_s, n_req=30000, n_users=N_USERS - 1, zipf_a=1.2, qps=200, invalidate_p=0.0):
        """Tráfico Zipf (pocos usuarios muy activos). Devuelve hit rate y latencia media simulada."""
        rng = np.random.default_rng(seed)
        users = np.minimum(rng.zipf(zipf_a, n_req), n_users)
        expiry, hits = {}, 0
        for k, u in enumerate(users):
            now = k / qps
            if expiry.get(u, -1) > now:
                hits += 1
            else:
                expiry[u] = now + ttl_s
            if rng.random() < invalidate_p:        # un evento del usuario invalida su clave
                expiry.pop(u, None)
        h = hits / n_req
        return h, h * 1.0 + (1 - h) * 35.0         # 1 ms acierto vs 35 ms pipeline completo


    ttls = [0, 5, 15, 30, 60, 120, 300, 600]
    fig, ax = plt.subplots(1, 2, figsize=(13, 4))
    for inv in [0.0, 0.05, 0.2]:
        out = [simulate_cache(t, invalidate_p=inv) for t in ttls]
        ax[0].plot(ttls, [o[0] for o in out], "o-", label=f"invalidación por evento p={inv}")
        ax[1].plot(ttls, [o[1] for o in out], "o-", label=f"p={inv}")
    ax[0].set_xlabel("TTL (s)"); ax[0].set_ylabel("hit rate"); ax[0].set_title("Hit rate vs TTL (tráfico Zipf)"); ax[0].legend()
    ax[1].set_xlabel("TTL (s)"); ax[1].set_ylabel("latencia media (ms)"); ax[1].set_title("Latencia media esperada"); ax[1].legend()
    plt.tight_layout(); plt.show()
    ''')

    # ------------------------------------------------------------------ FastAPI
    M(r"""
    ## 8. El microservicio: FastAPI + FAISS + LightGBM + Redis

    Guardamos los artefactos (índice, embeddings, ranker, features) como lo haría el pipeline offline, escribimos la app en
    un fichero y la lanzamos con **uvicorn en segundo plano**. La app:

    1. lee el historial del usuario (online store) → vector de usuario;
    2. **retrieval** FAISS (100 candidatos);
    3. *batch get* de features de ítem → **ranker** LightGBM;
    4. **re-ranking** de diversidad simple (máx. 3 por género principal);
    5. **fallback** de cold start (popularidad) si el usuario no existe;
    6. caché de la respuesta con TTL e **invalidación** al recibir un evento (`POST /event`);
    7. devuelve los tiempos de cada etapa (para dibujar la cascada **medida**) y expone `/metrics` en formato Prometheus.
    """)

    C(r'''
    # --- "Pipeline offline": publicar artefactos ---
    faiss.write_index(index_hnsw, f"{ART_DIR}/items.faiss")
    np.save(f"{ART_DIR}/item_emb.npy", ITEM_EMB)
    np.save(f"{ART_DIR}/genre_mat.npy", GENRE_MAT)
    ranker.booster_.save_model(f"{ART_DIR}/ranker.txt")
    item_feats_asof(t_b).to_parquet(f"{ART_DIR}/item_feats.parquet")
    prof_b, gen_b = user_profile(ratings[ratings.ts < t_b])
    prof_b.to_parquet(f"{ART_DIR}/user_prof.parquet"); gen_b.columns = [str(c) for c in gen_b.columns]
    gen_b.to_parquet(f"{ART_DIR}/user_genre.parquet")
    json.dump({str(u): h[-50:] for u, h in hist_b.items()}, open(f"{ART_DIR}/user_hist.json", "w"))
    popular = ratings[ratings.ts < t_b].item_id.value_counts().index[:200].tolist()
    json.dump({"popular": popular, "rank_feats": RANK_FEATS, "model_version": "ranker-v1"}, open(f"{ART_DIR}/meta.json", "w"))
    print(sorted(os.listdir(ART_DIR)))
    ''')

    C(r'''
    %%writefile cinematch_api.py
    """Servicio de recomendación CineMatch (versión Colab). Ver reference_stack/ para la versión con Redis/Feast reales."""
    import json, os, time
    import faiss, fakeredis, lightgbm as lgb, numpy as np, pandas as pd
    from fastapi import FastAPI, Response
    from pydantic import BaseModel

    ART = os.environ.get("ART_DIR", "artifacts")
    INDEX = faiss.read_index(f"{ART}/items.faiss"); INDEX.hnsw.efSearch = 64
    EMB = np.load(f"{ART}/item_emb.npy"); GENRE = np.load(f"{ART}/genre_mat.npy")
    RANKER = lgb.Booster(model_file=f"{ART}/ranker.txt")
    ITEM_F = pd.read_parquet(f"{ART}/item_feats.parquet")
    POP, RMEAN = ITEM_F.pop_cum.to_numpy(), ITEM_F.rating_mean_cum.to_numpy()
    PROF = pd.read_parquet(f"{ART}/user_prof.parquet"); UGEN = pd.read_parquet(f"{ART}/user_genre.parquet")
    META = json.load(open(f"{ART}/meta.json"))
    try:  # Redis real si existe REDIS_HOST, si no fakeredis (misma API)
        import redis
        R = redis.Redis(host=os.environ["REDIS_HOST"], decode_responses=True); R.ping()
    except Exception:
        R = fakeredis.FakeRedis(decode_responses=True)
    for u, h in json.load(open(f"{ART}/user_hist.json")).items():
        R.rpush(f"hist:{u}", *h)
    TTL = int(os.environ.get("CACHE_TTL", "60"))
    METRICS = {"requests_total": 0, "cache_hits_total": 0, "fallback_total": 0, "latency_ms_sum": 0.0}
    app = FastAPI(title="CineMatch Recommender")


    class Event(BaseModel):
        user_id: int
        item_id: int
        event_type: str = "play"


    def diversify(items, k, max_per_genre=3):
        out, count = [], {}
        for i in items:
            g = int(np.argmax(GENRE[i][1:])) + 1
            if count.get(g, 0) < max_per_genre:
                out.append(int(i)); count[g] = count.get(g, 0) + 1
            if len(out) == k:
                break
        return out


    @app.get("/health")
    def health():
        return {"status": "ok", "model_version": META["model_version"]}


    @app.get("/recommend/{user_id}")
    def recommend(user_id: int, k: int = 10, use_cache: bool = True):
        t0 = time.perf_counter(); tm = {}
        METRICS["requests_total"] += 1
        key = f"recs:{user_id}:{k}"
        if use_cache and (hit := R.get(key)):
            METRICS["cache_hits_total"] += 1
            return {**json.loads(hit), "cache": True, "timings_ms": {"total": 1e3 * (time.perf_counter() - t0)}}
        hist = [int(x) for x in R.lrange(f"hist:{user_id}", 0, -1)]; tm["features_usuario"] = time.perf_counter()
        if not hist or user_id not in PROF.index:            # cold start → popularidad
            METRICS["fallback_total"] += 1
            items = [i for i in META["popular"] if i not in set(hist)][:k]
            return {"user_id": user_id, "items": items, "strategy": "popularity_fallback", "cache": False}
        v = EMB[hist].mean(0); v = (v / (np.linalg.norm(v) + 1e-8)).astype("float32")
        sc, ids = INDEX.search(v[None], 100 + len(hist)); tm["retrieval"] = time.perf_counter()
        seen = set(hist); mask = [(i not in seen) and i > 0 for i in ids[0]]
        ids, sc = ids[0][mask][:100], sc[0][mask][:100]
        g = UGEN.loc[user_id].to_numpy()
        aff = GENRE[ids] @ g / (np.linalg.norm(GENRE[ids], axis=1) + 1e-8)
        X = np.column_stack([sc, np.arange(len(ids)), POP[ids], RMEAN[ids], aff,
                             np.full(len(ids), PROF.loc[user_id, "user_n"]), np.full(len(ids), PROF.loc[user_id, "user_mean"])])
        tm["features_item"] = time.perf_counter()
        p = RANKER.predict(X); order = ids[np.argsort(-p)]; tm["ranking"] = time.perf_counter()
        items = diversify(order, k); tm["reranking"] = time.perf_counter()
        resp = {"user_id": user_id, "items": items, "strategy": "two_stage", "model_version": META["model_version"]}
        R.setex(key, TTL, json.dumps(resp))
        prev, timings = t0, {}
        for name, t in tm.items():
            timings[name] = 1e3 * (t - prev); prev = t
        timings["total"] = 1e3 * (time.perf_counter() - t0)
        METRICS["latency_ms_sum"] += timings["total"]
        return {**resp, "cache": False, "timings_ms": timings}


    @app.post("/event")
    def event(e: Event):
        """Ingesta nearline simplificada: actualiza historial e invalida la caché del usuario."""
        R.rpush(f"hist:{e.user_id}", e.item_id); R.ltrim(f"hist:{e.user_id}", -50, -1)
        for key in R.scan_iter(f"recs:{e.user_id}:*"):
            R.delete(key)
        return {"ok": True}


    @app.get("/metrics")
    def metrics():
        body = "\n".join(f"cinematch_{k} {v}" for k, v in METRICS.items()) + "\n"
        return Response(body, media_type="text/plain")
    ''')

    C(r'''
    import subprocess, sys, requests

    def start_api(port=8000, extra_env=None):
        env = {**os.environ, "ART_DIR": ART_DIR, **(extra_env or {})}
        proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "cinematch_api:app", "--port", str(port),
                                 "--log-level", "warning"], env=env)
        for _ in range(120):
            try:
                if requests.get(f"http://127.0.0.1:{port}/health", timeout=0.5).ok:
                    return proc
            except requests.exceptions.RequestException:
                time.sleep(0.5)
        proc.kill(); raise RuntimeError("La API no arrancó")


    API = "http://127.0.0.1:8000"
    api_proc = start_api()
    print(requests.get(f"{API}/health").json())
    u0 = users_t[0]
    print(json.dumps(requests.get(f"{API}/recommend/{u0}", params={"use_cache": False}).json(), indent=1)[:600])
    print("Usuario nuevo:", requests.get(f"{API}/recommend/999999").json())
    ''')

    C(r'''
    # Cascada de latencia MEDIDA (sin caché) sobre 300 peticiones
    rows = []
    for u in users_t[:300]:
        rows.append(requests.get(f"{API}/recommend/{u}", params={"use_cache": False}).json()["timings_ms"])
    tdf = pd.DataFrame(rows)
    stages_m = ["features_usuario", "retrieval", "features_item", "ranking", "reranking"]
    p50s, p99s = tdf[stages_m].median(), tdf[stages_m].quantile(0.99)
    fig, ax = plt.subplots(1, 2, figsize=(13, 4))
    acc = 0
    for i, s in enumerate(stages_m):
        ax[0].bar(i, p50s[s], bottom=acc, color="#5dade2", ec="k"); ax[0].text(i, acc + p50s[s] / 2, f"{p50s[s]:.2f}", ha="center", fontsize=8)
        acc += p50s[s]
    ax[0].set_xticks(range(len(stages_m))); ax[0].set_xticklabels(stages_m, rotation=25)
    ax[0].set_ylabel("ms (p50 acumulado)"); ax[0].set_title("Cascada medida dentro del servicio (p50)")
    ax[1].hist(tdf.total, bins=40, color="#af7ac5"); ax[1].axvline(tdf.total.quantile(0.99), color="r", ls="--", label="p99")
    ax[1].set_xlabel("latencia interna total (ms)"); ax[1].set_title("Distribución de latencia"); ax[1].legend()
    plt.tight_layout(); plt.show()
    display(pd.DataFrame({"p50": p50s, "p99": p99s}).round(3))
    ''')

    M(r"""
    🧪 Fíjate en dos cosas: (1) en CPU y con 100 candidatos, el **ranker** y el **retrieval** dominan; en un sistema real
    las lecturas de features por red suelen ser la etapa más cara y con peor cola. (2) La latencia que ve el cliente
    incluye red, serialización JSON y la cola del servidor: mídela **siempre** desde fuera, como en el test de carga.

    ### Invalidación de caché por evento (nearline en el servicio)
    """)

    C(r'''
    a = requests.get(f"{API}/recommend/{u0}").json(); b = requests.get(f"{API}/recommend/{u0}").json()
    print("1ª petición cache:", a["cache"], "| 2ª petición cache:", b["cache"])
    requests.post(f"{API}/event", json={"user_id": u0, "item_id": int(a["items"][0])})
    c = requests.get(f"{API}/recommend/{u0}").json()
    print("Tras evento → cache:", c["cache"], "| ¿cambió la lista?", c["items"] != a["items"])
    print(requests.get(f"{API}/metrics").text)
    ''')

    # ------------------------------------------------------------------ Load test
    M(r"""
    ## 9. Test de carga

    **Locust** es el estándar en Python (usuarios virtuales definidos como clases). Abajo escribimos un `locustfile.py`
    (puedes lanzarlo con `RUN_LOCUST = True`) y, para que el notebook sea autocontenido, también un mini *load tester*
    con hilos que mide throughput y percentiles a distintas concurrencias.
    """)

    C(r'''
    %%writefile locustfile.py
    import random
    from locust import HttpUser, task, between

    USERS = list(range(1, 900))


    class HomeUser(HttpUser):
        wait_time = between(0.01, 0.05)

        @task(10)
        def home(self):
            self.client.get(f"/recommend/{random.choice(USERS)}", name="/recommend/[user]")

        @task(1)
        def play(self):
            self.client.post("/event", json={"user_id": random.choice(USERS), "item_id": random.randint(1, 1600)})
    ''')

    C(r'''
    from concurrent.futures import ThreadPoolExecutor

    def load_test(concurrency, n=400, cache=False):
        sess = requests.Session()
        def one(u):
            t = time.perf_counter(); sess.get(f"{API}/recommend/{u}", params={"use_cache": cache}); return 1e3 * (time.perf_counter() - t)
        us = np.random.default_rng(seed).choice(users_t, n)
        t0 = time.perf_counter()
        with ThreadPoolExecutor(concurrency) as ex:
            lat = list(ex.map(one, us))
        return {"concurrencia": concurrency, "qps": n / (time.perf_counter() - t0), "p50": np.percentile(lat, 50),
                "p95": np.percentile(lat, 95), "p99": np.percentile(lat, 99)}


    lt = pd.DataFrame([load_test(c) for c in [1, 2, 4, 8, 16]])
    lt_cache = pd.DataFrame([load_test(c, cache=True) for c in [1, 2, 4, 8, 16]])
    fig, ax = plt.subplots(1, 2, figsize=(13, 4))
    ax[0].plot(lt.concurrencia, lt.qps, "o-", label="sin caché"); ax[0].plot(lt_cache.concurrencia, lt_cache.qps, "o-", label="con caché")
    ax[0].set_xlabel("usuarios concurrentes"); ax[0].set_ylabel("peticiones/s"); ax[0].set_title("Throughput"); ax[0].legend()
    for col in ["p50", "p95", "p99"]:
        ax[1].plot(lt.qps, lt[col], "o-", label=col)
    ax[1].axhline(80, color="r", ls="--", label="SLO 80 ms"); ax[1].set_xlabel("QPS alcanzados"); ax[1].set_ylabel("ms (cliente)")
    ax[1].set_title("Latencia vs carga (sin caché): el 'codo' marca la capacidad de 1 réplica"); ax[1].legend()
    plt.tight_layout(); plt.show(); display(lt.round(1))

    RUN_LOCUST = False
    if RUN_LOCUST:
        !pip install -q locust
        !locust -f locustfile.py --headless -u 20 -r 5 -t 20s --host http://127.0.0.1:8000 --csv locust_out
        display(pd.read_csv("locust_out_stats.csv"))
    ''')

    M(r"""
    📐 **Dimensionado:** si una réplica sostiene ~$Q_1$ QPS cumpliendo el SLO y el pico esperado es $Q$, necesitas
    $\lceil Q / (\rho\, Q_1) \rceil$ réplicas con $\rho\approx0{,}6$ de utilización objetivo, más redundancia por zona. ⚠️ uvicorn
    con 1 worker y GIL: en producción usa varios workers (`--workers`), o mueve la inferencia pesada a un servidor de modelos
    (Triton) y deja FastAPI como orquestador asíncrono.

    ## 10. Exportar el ranker: TorchScript y ONNX

    Los GBDT se sirven bien en CPU (LightGBM nativo, Treelite, o el backend **FIL** de Triton en GPU). Los rankers neuronales
    (DCN-v2, DIN, MMoE — módulos 06–07) se exportan para desacoplar el *runtime* de inferencia del código de entrenamiento:

    - **TorchScript** (`torch.jit.trace/script`): grafo serializado ejecutable sin Python (libtorch, TorchServe, Triton backend PyTorch). En mantenimiento: PyTorch recomienda `torch.export` para flujos nuevos.
    - **ONNX** (`torch.onnx.export`): formato abierto ejecutado por **ONNX Runtime** (CPU/GPU, TensorRT EP) o Triton.
    - Siempre: **test de paridad numérica** (salidas iguales hasta ~1e-5) y benchmark por tamaño de batch.
    """)

    C(r'''
    import torch, torch.nn as nn
    torch.manual_seed(seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"

    Xtr = cand_tr[RANK_FEATS].to_numpy(np.float32); ytr = cand_tr.label.to_numpy(np.float32)
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-6


    class MLPRanker(nn.Module):
        def __init__(self, d, mu, sd):
            super().__init__()
            self.register_buffer("mu", torch.tensor(mu)); self.register_buffer("sd", torch.tensor(sd))
            self.net = nn.Sequential(nn.Linear(d, 128), nn.ReLU(), nn.Linear(128, 64), nn.ReLU(), nn.Linear(64, 1))

        def forward(self, x):                 # la normalización viaja DENTRO del modelo → menos skew
            return torch.sigmoid(self.net((x - self.mu) / self.sd)).squeeze(-1)


    mlp = MLPRanker(len(RANK_FEATS), mu, sd)
    opt = torch.optim.Adam(mlp.parameters(), 1e-3); lossf = nn.BCELoss()
    Xt, yt = torch.tensor(Xtr), torch.tensor(ytr)
    for epoch in range(5):
        perm = torch.randperm(len(Xt))
        for b in range(0, len(Xt), 1024):
            idx = perm[b:b + 1024]; opt.zero_grad(); l = lossf(mlp(Xt[idx]), yt[idx]); l.backward(); opt.step()
    mlp.eval()
    print("AUC MLP (test candidatos):", round(roc_auc_score(
        [int(i in test_pos[u]) for u, i in zip(cand_te.user_id, cand_te.item_id)],
        mlp(torch.tensor(cand_te[RANK_FEATS].to_numpy(np.float32))).detach().numpy()), 4))
    ''')

    C(r'''
    import onnxruntime as ort

    example = torch.tensor(cand_te[RANK_FEATS].to_numpy(np.float32)[:100])
    ts_model = torch.jit.trace(mlp, example); ts_model.save(f"{ART_DIR}/ranker_ts.pt")
    onnx_path = f"{ART_DIR}/ranker.onnx"
    export_kw = dict(input_names=["x"], output_names=["p"], dynamic_axes={"x": {0: "batch"}, "p": {0: "batch"}}, opset_version=17)
    try:
        torch.onnx.export(mlp, (example,), onnx_path, dynamo=False, **export_kw)   # exportador clásico (TorchScript)
    except TypeError:
        torch.onnx.export(mlp, (example,), onnx_path, **export_kw)                # versiones antiguas sin 'dynamo'
    sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])

    with torch.no_grad():
        ref = mlp(example).numpy(); out_ts = ts_model(example).numpy()
    out_onnx = sess.run(None, {"x": example.numpy()})[0]
    print(f"Paridad: |eager-TS|max={np.abs(ref - out_ts).max():.2e} · |eager-ONNX|max={np.abs(ref - out_onnx).max():.2e}")
    assert np.allclose(ref, out_onnx, atol=1e-5), "¡Fallo de paridad ONNX!"

    torch.set_num_threads(2)
    bench = []
    for bs in [1, 16, 100, 500, 2000]:
        xb = torch.randn(bs, len(RANK_FEATS)); xn = xb.numpy()
        for name, fn in [("PyTorch eager", lambda: mlp(xb)), ("TorchScript", lambda: ts_model(xb)),
                         ("ONNX Runtime", lambda: sess.run(None, {"x": xn}))]:
            with torch.no_grad():
                for _ in range(5): fn()
                t = time.perf_counter(); [fn() for _ in range(50)]
            bench.append({"batch": bs, "runtime": name, "ms": 1e3 * (time.perf_counter() - t) / 50})
    bench = pd.DataFrame(bench)
    fig, ax = plt.subplots(figsize=(8, 4))
    for name, g in bench.groupby("runtime"):
        ax.plot(g.batch, g.ms, "o-", label=name)
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel("tamaño de batch (candidatos)"); ax.set_ylabel("ms por llamada")
    ax.set_title("Latencia de inferencia del ranker por runtime (CPU)"); ax.legend(); plt.show()
    ''')

    M(r"""
    ## 11. Servidores de modelos: Triton, BentoML, Ray Serve, TorchServe

    | | **NVIDIA Triton** | **BentoML** | **Ray Serve** | **TorchServe** |
    |---|---|---|---|---|
    | Qué es | servidor de inferencia multi-framework (C++) | framework Python para empaquetar y servir | librería de serving sobre Ray | servidor oficial de PyTorch |
    | Backends | TensorRT, ONNX RT, PyTorch, TF, Python, **FIL** (XGBoost/LightGBM) | cualquiera (Python) | cualquiera (Python) | PyTorch |
    | Fuerte en | **dynamic batching**, múltiples instancias por GPU, *ensembles*, GPU | DX, contenedores reproducibles, *adaptive batching* | **composición** de modelos (grafos de deployments), autoescalado | integración PyTorch |
    | Cuándo | ranker neuronal en GPU con mucho QPS | equipo pequeño, time-to-market | pipelines multi-modelo (retrieval+ranking+LLM) en Python | legado PyTorch |

    ⚠️ **Estado (2025):** el repositorio de TorchServe indica que el proyecto está en **mantenimiento limitado** y no planea
    nuevas funcionalidades; para proyectos nuevos valora Triton, Ray Serve, BentoML o vLLM (para LLMs). Comprueba el estado
    actual antes de elegir.

    **Dynamic batching** (Triton/BentoML/Ray): el servidor espera unos microsegundos para juntar peticiones y aprovechar la
    GPU; en recsys cada petición ya es un «batch» de ~100–1000 candidatos, así que el beneficio está en juntar **peticiones de
    usuarios distintos**. Ejemplo de `config.pbtxt` de Triton para nuestro ranker ONNX (también en `reference_stack/triton/`):

    ```protobuf
    name: "ranker"
    backend: "onnxruntime"
    max_batch_size: 4096
    input  [{ name: "x", data_type: TYPE_FP32, dims: [7] }]
    output [{ name: "p", data_type: TYPE_FP32, dims: [] }]
    dynamic_batching { max_queue_delay_microseconds: 500 }
    instance_group [{ kind: KIND_GPU, count: 2 }]
    ```

    Y el mismo pipeline como grafo en **Ray Serve** (cada etapa escala de forma independiente):

    ```python
    from ray import serve

    @serve.deployment(num_replicas=2)
    class Retriever:
        def __init__(self): self.index = load_faiss()
        async def __call__(self, user_vec): return self.index.search(user_vec, 100)

    @serve.deployment(ray_actor_options={"num_gpus": 0.5})
    class Ranker:
        def __init__(self): self.model = load_onnx()
        async def __call__(self, feats): return self.model.run(feats)

    @serve.deployment
    class Recommender:
        def __init__(self, retriever, ranker): self.retriever, self.ranker = retriever, ranker
        async def __call__(self, request):
            cands = await self.retriever.remote(...); return await self.ranker.remote(...)

    app = Recommender.bind(Retriever.bind(), Ranker.bind())
    ```

    ## 12. Entrenar a escala: TorchRec, NVIDIA Merlin y el sharding de embeddings

    En CTR/ranking industrial, el 99 % de los parámetros están en **tablas de embeddings** de IDs (usuarios, ítems,
    creadores, hashes de cruces). Cuenta rápida: $10^9$ IDs × 128 dims × 4 bytes = **512 GB** solo de pesos (más el estado
    del optimizador: Adagrad ×2, Adam ×3). No cabe en una GPU ⇒ hay que **partir (shard)** las tablas:

    - **Table-wise**: cada tabla entera en una GPU (simple; desequilibrado si una tabla es enorme).
    - **Row-wise**: filas repartidas (por hash/rango) entre GPUs; requiere comunicación *all-to-all*.
    - **Column-wise**: dimensiones repartidas; equilibra tablas muy anchas.
    - **Data-parallel**: tablas pequeñas replicadas.

    **TorchRec** (Meta, PyTorch) implementa `EmbeddingBagCollection`, kernels FBGEMM y un **planner** que elige la
    estrategia por tabla según memoria y coste; es la base de DLRM (Naumov et al. 2019). **NVIDIA Merlin** agrupa NVTabular
    (ETL en GPU), Merlin Models, **HugeCTR** (entrenamiento con embeddings distribuidos y modelo paralelo) y el *Hierarchical
    Parameter Server* para inferencia (caché de embeddings en GPU → CPU → SSD). TikTok/ByteDance describe en **Monolith**
    (Liu et al. 2022) tablas *collisionless* con expiración de IDs y entrenamiento online. ⚠️ Comprueba la actividad de los
    repos de Merlin antes de adoptarlos: el ecosistema se mueve rápido.

    🧪 Simulemos por qué el sharding **por rango** es peligroso con IDs populares (los IDs bajos suelen ser los antiguos y populares):
    """)

    C(r'''
    rng = np.random.default_rng(seed)
    n_ids, n_shards = 1_000_000, 8
    access = np.minimum(rng.zipf(1.1, 2_000_000), n_ids) - 1          # IDs populares = IDs bajos
    load_range = np.bincount(access // (n_ids // n_shards), minlength=n_shards)
    load_hash = np.bincount((access * 2654435761) % 2**32 % n_shards, minlength=n_shards)

    fig, ax = plt.subplots(1, 2, figsize=(13, 4))
    ax[0].bar(np.arange(n_shards) - 0.2, load_range / load_range.mean(), 0.4, label="row-wise por rango")
    ax[0].bar(np.arange(n_shards) + 0.2, load_hash / load_hash.mean(), 0.4, label="row-wise por hash")
    ax[0].axhline(1, color="k", ls="--"); ax[0].set_yscale("log"); ax[0].set_xlabel("shard (GPU)")
    ax[0].set_ylabel("carga / carga media"); ax[0].set_title("Desequilibrio de lookups (tráfico Zipf)"); ax[0].legend()
    cfg = {"fp32": 4, "fp16": 2, "int8": 1}
    n_rows = [1e7, 1e8, 1e9]
    for j, (dt, b) in enumerate(cfg.items()):
        ax[1].bar(np.arange(3) + 0.27 * j, [n * 128 * b / 1e9 for n in n_rows], 0.27, label=f"pesos {dt}")
    ax[1].bar(np.arange(3) + 0.81, [n * 128 * 4 * 2 / 1e9 for n in n_rows], 0.27, label="fp32 + Adagrad")
    ax[1].axhline(80, color="r", ls="--", label="1× GPU de 80 GB"); ax[1].set_yscale("log")
    ax[1].set_xticks(np.arange(3) + 0.4); ax[1].set_xticklabels(["10M IDs", "100M IDs", "1B IDs"])
    ax[1].set_ylabel("GB (dim=128)"); ax[1].set_title("Memoria de una tabla de embeddings"); ax[1].legend(fontsize=8)
    plt.tight_layout(); plt.show()
    print("Máx/medio rango:", round(load_range.max() / load_range.mean(), 2), "| hash:", round(load_hash.max() / load_hash.mean(), 3))
    ''')

    # ------------------------------------------------------------------ Skew
    M(r"""
    ## 13. Training-serving skew

    *Skew* = el modelo ve en serving una distribución de features distinta de la de entrenamiento **por culpa del sistema**,
    no del mundo (eso sería *drift*, módulo 17). Fuentes típicas (Google, *Rules of ML*, reglas #29–#37):

    1. **Dos implementaciones** de la misma feature (SQL/Spark offline vs Java/Python online).
    2. **Valores por defecto distintos** para nulos (0 vs media global vs `NaN` que LightGBM trata aparte).
    3. **Frescura distinta**: offline usas la feature del día, online la de hace 3 días porque el job falló.
    4. **Unidades / zonas horarias / tokenización** diferentes.

    La regla de oro: **registrar (log) las features tal y como se sirvieron** y entrenar con esos logs (*log-and-wait*), o al
    menos compararlas con la recomputación offline. Simulemos un bug clásico: el servicio online rellena `rating_mean_cum`
    faltante con **0** en vez de 3,0 y calcula `user_mean` redondeando a entero.
    """)

    C(r'''
    X_off = cand_te[RANK_FEATS].copy()
    X_on = X_off.copy()
    X_on.loc[X_on.pop_cum == 0, "rating_mean_cum"] = 0.0          # bug 1: default distinto para nulos
    X_on["user_mean"] = X_on.user_mean.round()                      # bug 2: implementación distinta
    p_off, p_on = ranker.predict_proba(X_off)[:, 1], ranker.predict_proba(X_on)[:, 1]

    # Chequeo de paridad de features: % de filas donde difieren (lo que haría un job diario sobre los logs)
    parity = ((X_off - X_on).abs() > 1e-6).mean().sort_values(ascending=False)
    nd_on = []
    for u, g in cand_te.assign(p_on=p_on).groupby("user_id"):
        nd_on.append(ndcg_at_k(list(g.sort_values("p_on", ascending=False).item_id), test_pos[u]))
    fig, ax = plt.subplots(1, 2, figsize=(13, 4))
    ax[0].barh(parity.index, parity.values, color="#ec7063"); ax[0].set_xlabel("% filas con mismatch")
    ax[0].set_title("Chequeo de paridad offline vs online")
    ax[1].hist(p_on - p_off, bins=60, color="#5499c7"); ax[1].set_xlabel("p_online − p_offline")
    ax[1].set_title(f"Skew en predicciones · NDCG@10 {np.mean(m_rank):.4f} → {np.mean(nd_on):.4f}")
    plt.tight_layout(); plt.show()
    ''')

    M(r"""
    ## 14. Cold start en producción

    En producción el cold start no es un problema de modelado sino una **cadena de fallbacks** con SLO:

    | Situación | Estrategia | Dónde vive |
    |---|---|---|
    | Usuario anónimo / nuevo | popularidad por país/dispositivo/hora; onboarding («elige 3 títulos»); bandit (módulo 14) | online |
    | Usuario con 1–5 eventos | vector = media de esos ítems (nearline) — ¡ya lo hace nuestro servicio! | nearline |
    | Ítem nuevo sin interacciones | **torre de contenido**: proyectar metadatos al espacio de embeddings y **añadirlo al índice ANN sin reentrenar** | offline/nearline |
    | Ítem nuevo con pocas vistas | *boost* de exploración / slots reservados con guardrails | re-ranking |

    Implementamos la torre de contenido mínima: una regresión ridge de géneros → embedding SVD. Un estreno entra al índice
    FAISS al instante (Netflix describe que su foundation model también necesita manejar títulos nuevos vía metadatos).
    """)

    C(r'''
    from sklearn.linear_model import Ridge

    known = np.where(np.linalg.norm(ITEM_EMB, axis=1) > 0.5)[0]
    tr_i, te_i = known[: int(0.8 * len(known))], known[int(0.8 * len(known)):]
    content_tower = Ridge(alpha=1.0).fit(GENRE_MAT[tr_i], ITEM_EMB[tr_i])
    pred = content_tower.predict(GENRE_MAT[te_i]).astype(np.float32)
    pred /= np.linalg.norm(pred, axis=1, keepdims=True) + 1e-8
    cos_true = (pred * ITEM_EMB[te_i]).sum(1)
    cos_rand = (pred * ITEM_EMB[np.random.default_rng(seed).permutation(te_i)]).sum(1)

    # "Estreno": añadimos un ítem nuevo al índice (id nuevo) sin reentrenar nada
    new_vec = pred[:1]; new_id = index_flat.ntotal
    index_flat.add(new_vec)
    fan = [u for u in users_eval if ITEM_EMB[hist_a[u]].mean(0) @ new_vec[0] > 0][:50]
    shown = np.mean([new_id in retrieve(hist_a[u], 100, index_flat)[0] for u in fan])
    print(f"El estreno aparece en el top-100 del {shown:.0%} de 50 usuarios afines (sin reentrenar)")

    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.hist(cos_true, bins=40, alpha=0.7, label="coseno(predicho, real)")
    ax.hist(cos_rand, bins=40, alpha=0.7, label="coseno(predicho, ítem aleatorio)")
    ax.set_xlabel("similitud coseno"); ax.set_title("Torre de contenido para ítems nuevos (géneros → embedding)"); ax.legend()
    plt.show()
    ''')

    C(r'''
    api_proc.terminate()   # apagamos el servicio
    ''')

    # ------------------------------------------------------------------ Producción
    M(r"""
    ## 🏭 En producción

    - **Netflix.** El post de 2013 (Amatriain & Basilico) define offline/nearline/online: offline para entrenar y precomputar,
      nearline para reaccionar a eventos (p. ej. tras un *play*) con resultados en caché (EVCache, Cassandra, MySQL), online para
      responder con el contexto de la petición; y advierte que cada capa tiene sus fallos: online necesita **fallbacks** si un
      cómputo no llega a tiempo. Su *time travel* de features («DeLorean», SysML 2018) materializa el *point-in-time*.
      En 2025 describen un **foundation model** de recomendación (transformer sobre secuencias de interacciones) cuyos
      **embeddings** se publican en un *embedding store* para que muchos modelos *downstream* los consuman — la misma
      separación offline/online, ahora con un modelo grande.
    - **Uber Michelangelo** (2017): plataforma end-to-end; su feature store compartido (online en Cassandra, offline en Hive) y
      la regla de «mismas features en entrenamiento y serving» son el antecedente directo de Feast (Feast nació en Gojek con Google Cloud, 2019).
    - **Instagram Explore** (Meta, 2023): pipeline de cuatro etapas (retrieval → first-stage ranking → second-stage ranking →
      reranking final) con *two-tower* en retrieval y **caching/precomputación** para poder usar modelos más pesados en las etapas finales.
    - **X/Twitter** (open source 2023, *the-algorithm*): el servicio Home Mixer obtiene ~1500 candidatos de varias fuentes,
      los puntúa con un ranker neuronal (~48M parámetros) y aplica heurísticas y filtros; todo el grafo es público y es un
      gran material de estudio.
    - **ByteDance Monolith** (2022): entrenamiento online con tablas de embeddings sin colisiones y sincronización de
      parámetros al serving en minutos; muestra el trade-off fiabilidad vs tiempo real.
    - **YouTube** (Covington et al. 2016): candidate generation + ranking, y la observación de que la *frescura* («example age»
      como feature) importa mucho porque el contenido nuevo es lo que más se consume.

    ## 🧠 Secretos de la élite

    1. **Loguea las features servidas, no las recalcules.** Entrenar sobre *served features logs* elimina por construcción la mayor fuente de skew (Rules of ML #29). Cuesta almacenamiento; ahorra trimestres de depuración.
    2. **El AUC offline sospechosamente alto es un bug hasta que se demuestre lo contrario.** El 90 % de las veces es un join sin *point-in-time* o una feature calculada con la etiqueta.
    3. **Optimiza p99 del fan-out, no la media de cada servicio** (Dean & Barroso 2013). *Hedged requests* y timeouts por etapa con degradación elegante (devolver candidatos sin re-ranking antes que un error).
    4. **El fallback es una feature de producto.** Ten siempre una respuesta barata precomputada (popularidad por segmento) para cuando el ranker no llegue: un 503 en la home cuesta más que una lista algo peor.
    5. **Invalida caché por evento, no solo por TTL.** El usuario que acaba de ver algo y lo vuelve a ver recomendado pierde la confianza en el sistema.
    6. **Particiona Kafka por `user_id`** para conservar el orden por usuario y haz los consumidores **idempotentes** (at-least-once ⇒ duplicados).
    7. **La normalización y el preprocesado viajan dentro del artefacto del modelo** (buffers en el `nn.Module`, pipeline en ONNX): cada transformación que vive fuera es una oportunidad de skew.
    8. **En tablas de embeddings, hashea antes de shardear** y vigila las *hot rows*: los IDs populares saturan un shard (por rango) y dominan la cola de latencia.

    ## ⚠️ Errores comunes

    - Medir la latencia **dentro** del handler y olvidar red, serialización, colas y GC.
    - Evaluar con un split aleatorio y features calculadas sobre todo el dataset (doble leakage).
    - Cachear la respuesta sin incluir en la clave lo que la cambia (`k`, país, perfil, versión del modelo).
    - Cargar el modelo **en cada petición** o no hacer *warm-up* (la primera petición tras desplegar tarda 10×).
    - Un solo worker síncrono con inferencia pesada: el GIL convierte tu API en una cola M/M/1 con $\rho \to 1$.
    - No versionar juntos modelo + índice ANN + features: un índice construido con embeddings v2 consultado con un vector de usuario v1 devuelve basura **sin errores**.
    - Olvidar el *ttl* de las FeatureViews: valores muy viejos se sirven como si fueran actuales.

    ## 📝 Autoevaluación

    1. ¿Qué cómputo pondrías en nearline y no en online, y por qué?
    <details><summary>Respuesta</summary>Lo que depende de eventos recientes pero es demasiado caro para la petición o no necesita el contexto de la misma: recalcular el vector/historial del usuario tras un play, invalidar caché, recomputar candidatos del usuario. Se hace asíncrono (consumidor de eventos) y deja el resultado en el online store, reduciendo latencia online sin perder frescura.</details>

    2. Un servicio hace fan-out a 50 shards; cada uno cumple 20 ms el 99 % de las veces. ¿Qué fracción de peticiones cumple 20 ms?
    <details><summary>Respuesta</summary>$0{,}99^{50}\approx 0{,}605$: solo ~60 %. Por eso se optimiza la cola de cada shard, se usan hedged requests o se reduce el fan-out.</details>

    3. Explica con un ejemplo concreto por qué un join ingenuo de `popularidad_item` produce leakage.
    <details><summary>Respuesta</summary>Si la popularidad se calcula con todo el histórico, para un ejemplo del día d incluye interacciones de días posteriores, entre ellas la de la propia etiqueta positiva. El modelo aprende una correlación imposible en serving, la métrica offline se infla y cae en producción. El PIT join usa el último valor publicado antes de t.</details>

    4. ¿Qué hace `materialize` en Feast y por qué no se lee el offline store en serving?
    <details><summary>Respuesta</summary>Copia el valor más reciente de cada entidad (dentro del ttl) del offline store al online store (SQLite/Redis/DynamoDB), que permite lecturas clave-valor en milisegundos. El offline store (parquet/warehouse) está optimizado para escaneos masivos, no para lecturas puntuales de baja latencia.</details>

    5. ¿Diferencia entre training-serving skew y data drift?
    <details><summary>Respuesta</summary>Skew: discrepancia causada por el sistema (dos implementaciones, defaults, frescura) entre features de entrenamiento y de serving en el mismo momento. Drift: el mundo cambia (gustos, catálogo) y la distribución de datos reales se mueve con el tiempo. El skew se arregla con ingeniería; el drift con monitoreo y reentreno.</details>

    6. ¿Cuándo elegirías Triton frente a FastAPI con ONNX Runtime embebido?
    <details><summary>Respuesta</summary>Cuando hay GPU y mucho QPS (dynamic batching entre peticiones, varias instancias por GPU, TensorRT), varios modelos/frameworks a servir o ensembles. Para un GBDT en CPU con QPS moderado, ONNX Runtime/LightGBM embebido en FastAPI es más simple.</details>

    7. Una tabla de 500M IDs × 64 dims en fp32 con Adam: ¿cuánta memoria? ¿Qué harías?
    <details><summary>Respuesta</summary>Pesos: 500e6·64·4 B = 128 GB; Adam añade 2 momentos ⇒ ~384 GB. Sharding row-wise por hash entre varias GPUs (TorchRec/HugeCTR), optimizador más ligero (row-wise Adagrad), fp16/int8 en inferencia, hashing/poda de IDs raros o caché jerárquica.</details>

    ## 📚 Referencias

    **Arquitectura y blogs de ingeniería**
    - Amatriain, X. & Basilico, J. (2013). *System Architectures for Personalization and Recommendation*. Netflix Tech Blog. https://netflixtechblog.com/system-architectures-for-personalization-and-recommendation-e081aa94b5d8
    - Netflix Tech Blog (2025). *Foundation Model for Personalized Recommendation*. https://netflixtechblog.com/foundation-model-for-personalized-recommendation-1a0bd8e02d39
    - Sadekar, K. & Jiang, H. (2018). *Time Travel based Feature Generation*. SysML 2018 (Netflix, DeLorean).
    - Del Balso, M. & Hermann, J. (2017). *Meet Michelangelo: Uber's Machine Learning Platform*. https://www.uber.com/blog/michelangelo-machine-learning-platform/
    - Meta Engineering (2023). *Scaling the Instagram Explore recommendations system*. https://engineering.fb.com/2023/08/09/ml-applications/scaling-instagram-explore-recommendations-system/
    - Twitter/X Engineering (2023). *Twitter's Recommendation Algorithm*. https://blog.x.com/engineering/en_us/topics/open-source/2023/twitter-recommendation-algorithm
    - Yan, E. (2021). *System Design for Recommendations and Search*. https://eugeneyan.com/writing/system-design-for-discovery/
    - Huyen, C. (2022). *Real-time machine learning: challenges and solutions*. https://huyenchip.com/2022/01/02/real-time-machine-learning-challenges-and-solutions.html
    - Google. *Rules of Machine Learning* (Zinkevich). https://developers.google.com/machine-learning/guides/rules-of-ml

    **Papers**
    - Sculley, D. et al. (2015). *Hidden Technical Debt in Machine Learning Systems*. NeurIPS.
    - Dean, J. & Barroso, L. A. (2013). *The Tail at Scale*. Communications of the ACM 56(2).
    - Covington, P., Adams, J., Sargin, E. (2016). *Deep Neural Networks for YouTube Recommendations*. RecSys.
    - Cremonesi, P., Koren, Y., Turrin, R. (2010). *Performance of Recommender Algorithms on Top-N Recommendation Tasks*. RecSys.
    - Naumov, M. et al. (2019). *Deep Learning Recommendation Model for Personalization and Recommendation Systems* (DLRM). arXiv:1906.00091
    - Ivchenko, D. et al. (2022). *TorchRec: a PyTorch Domain Library for Recommendation Systems*. RecSys.
    - Wang, Z. et al. (2022). *Merlin HugeCTR: GPU-accelerated Recommender System Training and Inference*. RecSys. arXiv:2210.08803
    - Liu, Z. et al. (2022). *Monolith: Real Time Recommendation System With Collisionless Embedding Table*. arXiv:2209.07663
    - Johnson, J., Douze, M., Jégou, H. (2017). *Billion-scale similarity search with GPUs* (FAISS). arXiv:1702.08734

    **Herramientas:** Feast (https://docs.feast.dev) · FastAPI · FAISS · LightGBM · Redis · Apache Kafka / Redpanda · Locust (https://locust.io) · ONNX Runtime · NVIDIA Triton Inference Server · BentoML · Ray Serve · TorchRec · NVIDIA Merlin.

    ➡️ **Siguiente:** el proyecto de este módulo (desplegar CineMatch como microservicio) y luego el módulo 17, donde ese servicio se monitoriza y se reentrena solo.
    """)

    nb.save(path)



SCALE_CELL = r'''
# SCALE = "small" → MovieLens-100K (minutos en CPU) · "full" → MovieLens-1M (más realista; sigue cabiendo en CPU)
SCALE = "small"
ML1M_URL = "https://files.grouplens.org/datasets/movielens/ml-1m.zip"


def load_ml1m():
    path = os.path.join(DATA_DIR, "ml-1m.zip")
    if not os.path.exists(path):
        urllib.request.urlretrieve(ML1M_URL, path)
    with zipfile.ZipFile(path) as z:
        r = pd.read_csv(z.open("ml-1m/ratings.dat"), sep="::", engine="python", names=["user_id", "item_id", "rating", "ts"])
        mv = pd.read_csv(z.open("ml-1m/movies.dat"), sep="::", engine="python", names=["item_id", "title", "genres"],
                         encoding="latin-1")
    g = mv.genres.str.replace("Children's", "Children").str.get_dummies("|")
    items = pd.concat([mv[["item_id", "title"]], g.reindex(columns=GENRES, fill_value=0)], axis=1)
    return r, items, "MovieLens-1M"


if SCALE == "full":
    try:
        ratings, items_df, DATASET = load_ml1m()
        ratings = ratings.sort_values("ts").reset_index(drop=True)
    except Exception as e:
        print("⚠️ ML-1M no disponible, sigo con", DATASET, repr(e)[:100])
print(DATASET, ratings.shape)
'''


def project() -> None:
    path = f"{MOD}/16_proyecto_cinematch_microservicio.ipynb"
    nb = Notebook("Proyecto 16 · CineMatch como microservicio", colab_path=path)
    M, C = nb.md, nb.code

    M(f"""
    {nb.badge()}

    # Proyecto 16 · Desplegar CineMatch como microservicio de recomendación

    **Nivel:** 🔴 Experto · **Duración:** 4–6 h · **GPU:** no necesaria · **Unidades Colab:** 1–3 (CPU)

    ## 🏢 Contexto de negocio

    Eres *ML platform engineer* en **CineMatch**. El equipo de producto lanza la nueva home el mes que viene y el modelo
    de los módulos anteriores vive todavía en un notebook. Tu misión: convertirlo en un **servicio** que cumpla el contrato
    acordado con el equipo de backend:

    - `GET /recommend/{{user_id}}?k=10` → 10 títulos, **p99 ≤ 80 ms** medido desde el cliente con 8 usuarios concurrentes (sin caché), 1 réplica.
    - **Nunca** un error para usuarios nuevos: *fallback* de popularidad.
    - `POST /event` actualiza el historial del usuario (nearline) e **invalida** su caché.
    - `GET /metrics` en formato Prometheus para que SRE monte alertas (lo usarás en el módulo 17).
    - Features **point-in-time correctas** en entrenamiento y **paridad 100 %** entre las features que ve el modelo en entrenamiento y en serving.

    ## 📦 Dataset

    **MovieLens-100K** (GroupLens, https://grouplens.org/datasets/movielens/) — 100 000 valoraciones de 943 usuarios sobre
    1 682 películas (1997–98) con géneros. Con `SCALE = "full"` usarás **MovieLens-1M** (1M valoraciones, 6 040 usuarios).
    Si no hay red, el notebook genera datos sintéticos con el mismo esquema (no te quedas bloqueado).

    ## ✅ Entregables y rúbrica (100 puntos)

    | # | Entregable | Criterio objetivo | Puntos |
    |---|---|---|---|
    | E1 | `pit_item_features` | test automático: ninguna feature con `event_timestamp` > instante del ejemplo; gap AUC offline/producción < 0,01 | 20 |
    | E2 | Ranker LambdaMART (`LGBMRanker`) | NDCG@10 en test temporal ≥ **1,10 ×** el NDCG@10 del retrieval solo | 20 |
    | E3 | Servicio FastAPI | `/health`, `/recommend`, `/event`, `/metrics`; fallback para usuarios nuevos; invalidación de caché comprobada | 25 |
    | E4 | Test de carga | p99 ≤ 80 ms con concurrencia 8 sin caché (CPU de Colab) | 15 |
    | E5 | Paridad de features | features **logueadas por el servicio** == features del builder offline en ≥ 99,9 % de las celdas | 10 |
    | E6 | Decisiones | 5–10 líneas: qué iría a Triton/Redis/Feast/Kafka en `reference_stack/` y por qué | 10 |

    > La solución de referencia está al final. Las celdas de comprobación capturan `NotImplementedError` para que puedas
    > ejecutar el notebook de arriba a abajo mientras trabajas.
    """)

    C(r'''
    !pip install -q fastapi uvicorn faiss-cpu lightgbm fakeredis redis requests pyarrow
    ''')
    C(DATA_CELL)
    C(SCALE_CELL)
    C(PIPE_CELL)
    C(r'''
    import faiss, lightgbm as lgb, requests, subprocess, sys
    from sklearn.metrics import roc_auc_score
    from concurrent.futures import ThreadPoolExecutor

    INDEX = faiss.IndexHNSWFlat(ITEM_EMB.shape[1], 32, faiss.METRIC_INNER_PRODUCT)
    INDEX.hnsw.efSearch = 64
    INDEX.add(ITEM_EMB)


    def retrieve(hist, k=100):
        v = user_vector(hist, ITEM_EMB)
        if v is None:
            return np.array([], dtype=int), np.array([], dtype=np.float32)
        s, ids = INDEX.search(v[None], k + len(hist))
        seen = set(hist)
        mask = np.array([(i not in seen) and i > 0 for i in ids[0]])
        return ids[0][mask][:k], s[0][mask][:k]


    def ndcg_at_k(ranked, relevant, k=10):
        dcg = sum(1.0 / np.log2(r + 2) for r, i in enumerate(ranked[:k]) if i in relevant)
        idcg = sum(1.0 / np.log2(r + 2) for r in range(min(k, len(relevant))))
        return dcg / idcg if idcg else 0.0


    # Snapshots diarios de features de ítem, publicados al día siguiente (batch nocturno)
    ev = ratings[["item_id", "rating", "ts"]].assign(day=lambda d: d.ts // 86400)
    daily = ev.groupby(["item_id", "day"]).agg(n=("rating", "size"), s=("rating", "sum")).reset_index().sort_values(["item_id", "day"])
    daily["pop_cum"] = daily.groupby("item_id").n.cumsum()
    daily["rating_mean_cum"] = daily.groupby("item_id").s.cumsum() / daily.pop_cum
    daily["event_timestamp"] = pd.to_datetime((daily.day + 1) * 86400, unit="s", utc=True)
    ITEM_STATS = daily[["item_id", "event_timestamp", "pop_cum", "rating_mean_cum"]].reset_index(drop=True)
    RANK_FEATS = ["retr_score", "retr_rank", "pop_cum", "rating_mean_cum", "genre_affinity", "user_n", "user_mean"]
    print("Snapshots de ítem:", ITEM_STATS.shape)
    ''')

    M(r"""
    ## Paso 1 · Features *point-in-time* (E1)

    Implementa `pit_item_features(examples, item_stats)`: para cada fila de `examples` (`item_id`, `event_timestamp`)
    añade `pop_cum` y `rating_mean_cum` del **último snapshot con `event_timestamp` ≤ instante del ejemplo**. Valores por
    defecto si no hay snapshot: `pop_cum = 0`, `rating_mean_cum = 3.0`. Añade también la columna `feature_ts` con el
    timestamp del snapshot usado (para el test).

    💡 Pista: `pd.merge_asof(..., on="event_timestamp", by="item_id", direction="backward")`, ambos DataFrames ordenados por la clave temporal.
    """)

    C(r'''
    def pit_item_features(examples: pd.DataFrame, item_stats: pd.DataFrame) -> pd.DataFrame:
        # TODO: point-in-time join + defaults + columna feature_ts
        raise NotImplementedError


    def make_examples(df_pos, n_neg=4, seed=seed):
        r_ = np.random.default_rng(seed)
        pos = df_pos[["user_id", "item_id", "ts"]].assign(label=1)
        neg = pos.loc[pos.index.repeat(n_neg)].copy()
        neg["item_id"] = r_.integers(1, N_ITEMS, len(neg)); neg["label"] = 0
        out = pd.concat([pos, neg], ignore_index=True)
        out["event_timestamp"] = pd.to_datetime(out.ts, unit="s", utc=True)
        return out.sort_values("event_timestamp").reset_index(drop=True)


    def check_E1():
        ex = make_examples(train_b)
        f = pit_item_features(ex, ITEM_STATS)
        ok_ts = (f.feature_ts.isna() | (f.feature_ts <= f.event_timestamp)).all()
        tr = pit_item_features(make_examples(train_a.sample(frac=0.5, random_state=seed)), ITEM_STATS)
        m = lgb.LGBMClassifier(n_estimators=150, verbose=-1, random_state=seed).fit(tr[["pop_cum", "rating_mean_cum"]], tr.label)
        auc = roc_auc_score(f.label, m.predict_proba(f[["pop_cum", "rating_mean_cum"]])[:, 1])
        print(f"E1 · sin features del futuro: {ok_ts} · AUC val (PIT) = {auc:.3f}")
        return ok_ts


    try:
        check_E1()
    except NotImplementedError:
        print("⏳ E1 pendiente")
    ''')

    M(r"""
    ## Paso 2 · Candidatos y ranker LambdaMART (E2)

    1. `build_candidates(hist, users, t_cut, labels=None)` → DataFrame con `user_id, item_id` y las columnas de `RANK_FEATS`
       usando **solo información anterior a `t_cut`** (perfil del usuario, géneros, features de ítem as-of `t_cut`).
    2. Entrena un `lgb.LGBMRanker(objective="lambdarank")` agrupando por usuario (`group=`) con etiquetas de `train_b`.
    3. Evalúa NDCG@10 en `test` (historial hasta `t_b`) frente al orden del retrieval.

    💡 Pista: `affinity = GENRE_MAT[ids] @ perfil_generos_usuario / ‖GENRE_MAT[ids]‖`; el perfil es la media normalizada de los géneros vistos.
    """)

    C(r'''
    def build_candidates(hist: dict, users: list, t_cut: float, k: int = 100, labels: dict | None = None) -> pd.DataFrame:
        # TODO: retrieval top-k + features (RANK_FEATS) as-of t_cut (+ columna label si labels no es None)
        raise NotImplementedError


    def train_ranker(cands: pd.DataFrame):
        # TODO: LGBMRanker lambdarank con group por usuario (ordena por user_id antes)
        raise NotImplementedError


    def check_E2(ranker, build=None):
        build = build or build_candidates
        hist_b = ratings[ratings.ts < t_b].groupby("user_id").item_id.apply(list).to_dict()
        test_pos = test.groupby("user_id").item_id.apply(set).to_dict()
        users = [u for u in test_pos if u in hist_b][:500]
        c = build(hist_b, users, t_b)
        c["score"] = ranker.predict(c[RANK_FEATS])
        nd_r = np.mean([ndcg_at_k(list(g.sort_values("retr_rank").item_id), test_pos[u]) for u, g in c.groupby("user_id")])
        nd_m = np.mean([ndcg_at_k(list(g.sort_values("score", ascending=False).item_id), test_pos[u]) for u, g in c.groupby("user_id")])
        print(f"E2 · NDCG@10 retrieval={nd_r:.4f} ranker={nd_m:.4f} ratio={nd_m / max(nd_r, 1e-9):.2f} (objetivo ≥ 1,10)")
        return nd_m / max(nd_r, 1e-9)


    try:
        lab_b = train_b.groupby("user_id").item_id.apply(set).to_dict()
        cands = build_candidates(hist_a, [u for u in lab_b if u in hist_a], t_a, labels=lab_b)
        check_E2(train_ranker(cands))
    except NotImplementedError:
        print("⏳ E2 pendiente")
    ''')

    M(r"""
    ## Paso 3 · El servicio (E3)

    Completa la plantilla. Requisitos: carga de artefactos al arrancar (no por petición), caché con TTL e invalidación en
    `/event`, fallback de popularidad, `/metrics` en texto Prometheus, y **log de features servidas** (un JSON por línea
    en `logs/served_features.jsonl` con `user_id`, `item_id` y las 7 features) cuando `LOG_FEATURES=1`.
    """)

    C(r'''
    %%writefile service_template.py
    import json, os, time
    import numpy as np
    from fastapi import FastAPI, Response

    app = FastAPI(title="CineMatch (plantilla)")
    # TODO: cargar artefactos (índice FAISS, embeddings, ranker, features de usuario/ítem, historiales, popularidad)


    @app.get("/health")
    def health():
        return {"status": "ok"}


    @app.get("/recommend/{user_id}")
    def recommend(user_id: int, k: int = 10, use_cache: bool = True):
        # TODO: caché → historial → retrieval → features → ranker → diversidad → log de features → respuesta
        raise NotImplementedError


    @app.post("/event")
    def event(payload: dict):
        # TODO: actualizar historial + invalidar caché
        raise NotImplementedError


    @app.get("/metrics")
    def metrics():
        # TODO: contadores en formato Prometheus
        return Response("", media_type="text/plain")
    ''')

    M(r"""
    ## Paso 4 · Test de carga (E4) y paso 5 · Paridad de features (E5)

    - `load_test(url, users, concurrency, n)` → dict con `qps`, `p50`, `p95`, `p99` medidos **desde el cliente**.
    - `parity_check(log_path)` → fracción de celdas (fila × feature) en las que el log del servicio coincide con
      `build_candidates` recalculado offline para los mismos `(user_id, item_id)` (tolerancia 1e-5).
    """)

    C(r'''
    def load_test(url: str, users: list, concurrency: int, n: int = 400, cache: bool = False) -> dict:
        # TODO
        raise NotImplementedError


    def parity_check(log_path: str) -> float:
        # TODO
        raise NotImplementedError
    ''')

    M(r"""
    ## Paso 6 · Decisiones de arquitectura (E6)

    ✍️ Escribe aquí (markdown) qué piezas del servicio moverías a `reference_stack/` en producción real (Redis, Feast con
    online store Redis, Redpanda/Kafka para `/event`, Triton para un ranker neuronal, Prometheus/Grafana) y qué SLO/alertas definirías.

    ---

    # ⛔ SPOILER — intenta resolverlo primero

    A partir de aquí está la **solución de referencia** completa y ejecutable.
    """)

    C(r'''
    def pit_item_features(examples: pd.DataFrame, item_stats: pd.DataFrame) -> pd.DataFrame:
        st = item_stats.rename(columns={"event_timestamp": "feature_ts"}).sort_values("feature_ts")
        ex = examples.sort_values("event_timestamp")
        out = pd.merge_asof(ex, st, left_on="event_timestamp", right_on="feature_ts", by="item_id", direction="backward")
        return out.fillna({"pop_cum": 0, "rating_mean_cum": 3.0})


    check_E1()
    ''')

    C(r'''
    def user_profile(df):
        g = df.groupby("user_id")
        prof = pd.DataFrame({"user_n": g.size().astype(float), "user_mean": g.rating.mean()})
        gen = pd.DataFrame(GENRE_MAT[df.item_id.values], index=df.user_id.values).groupby(level=0).mean()
        gen = gen.div(np.linalg.norm(gen.values, axis=1) + 1e-8, axis=0)
        return prof, gen


    def item_feats_asof(t_cut):
        snap = ITEM_STATS[ITEM_STATS.event_timestamp <= pd.Timestamp(t_cut, unit="s", tz="UTC")]
        last = snap.groupby("item_id").tail(1).set_index("item_id")[["pop_cum", "rating_mean_cum"]]
        return last.reindex(range(N_ITEMS)).fillna({"pop_cum": 0, "rating_mean_cum": 3.0}).astype(float)


    def features_for(u, ids, sc, prof, gen, itf):
        """ÚNICA implementación de las features: la usan el builder offline y (copiada al artefacto) el servicio."""
        aff = GENRE_MAT[ids] @ gen.loc[u].values / (np.linalg.norm(GENRE_MAT[ids], axis=1) + 1e-8)
        return pd.DataFrame({"user_id": u, "item_id": ids, "retr_score": sc.astype(float), "retr_rank": np.arange(len(ids), dtype=float),
                             "pop_cum": itf.pop_cum.values[ids], "rating_mean_cum": itf.rating_mean_cum.values[ids],
                             "genre_affinity": aff.astype(float), "user_n": prof.loc[u, "user_n"], "user_mean": prof.loc[u, "user_mean"]})


    def build_candidates(hist, users, t_cut, k=100, labels=None):
        prof, gen = user_profile(ratings[ratings.ts < t_cut]); itf = item_feats_asof(t_cut)
        rows = []
        for u in users:
            ids, sc = retrieve(hist[u], k)
            if len(ids):
                rows.append(features_for(u, ids, sc, prof, gen, itf))
        out = pd.concat(rows, ignore_index=True)
        if labels is not None:
            out["label"] = [int(i in labels.get(u, ())) for u, i in zip(out.user_id, out.item_id)]
        return out


    def train_ranker(cands):
        c = cands[cands.groupby("user_id").label.transform("max") > 0].sort_values("user_id")
        rk = lgb.LGBMRanker(objective="lambdarank", n_estimators=300, learning_rate=0.05, num_leaves=31,
                            min_child_samples=20, verbose=-1, random_state=seed)
        rk.fit(c[RANK_FEATS], c.label, group=c.groupby("user_id").size().values)
        return rk


    lab_b = train_b.groupby("user_id").item_id.apply(set).to_dict()
    cands = build_candidates(hist_a, [u for u in lab_b if u in hist_a], t_a, labels=lab_b)
    RANKER = train_ranker(cands)
    ratio = check_E2(RANKER)
    ''')

    C(r'''
    # Publicar artefactos as-of t_b (lo que haría el pipeline offline cada noche)
    hist_b = ratings[ratings.ts < t_b].groupby("user_id").item_id.apply(list).to_dict()
    prof_b, gen_b = user_profile(ratings[ratings.ts < t_b]); itf_b = item_feats_asof(t_b)
    faiss.write_index(INDEX, f"{ART_DIR}/items.faiss")
    np.save(f"{ART_DIR}/item_emb.npy", ITEM_EMB); np.save(f"{ART_DIR}/genre_mat.npy", GENRE_MAT)
    RANKER.booster_.save_model(f"{ART_DIR}/ranker.txt")
    itf_b.to_parquet(f"{ART_DIR}/item_feats.parquet"); prof_b.to_parquet(f"{ART_DIR}/user_prof.parquet")
    gen_b.columns = [str(c) for c in gen_b.columns]; gen_b.to_parquet(f"{ART_DIR}/user_genre.parquet")
    json.dump({str(u): h[-50:] for u, h in hist_b.items()}, open(f"{ART_DIR}/user_hist.json", "w"))
    json.dump({"popular": ratings[ratings.ts < t_b].item_id.value_counts().index[:200].tolist(),
               "rank_feats": RANK_FEATS, "model_version": "ranker-lambdamart-v1"}, open(f"{ART_DIR}/meta.json", "w"))
    ''')

    C(r'''
    %%writefile cinematch_service.py
    """CineMatch · servicio de recomendación (solución de referencia del proyecto 16)."""
    import json, os, threading, time
    import faiss, fakeredis, lightgbm as lgb, numpy as np, pandas as pd
    from fastapi import FastAPI, Response
    from pydantic import BaseModel

    ART = os.environ.get("ART_DIR", "artifacts"); LOG = os.environ.get("LOG_FEATURES", "0") == "1"
    INDEX = faiss.read_index(f"{ART}/items.faiss"); INDEX.hnsw.efSearch = 64
    EMB, GENRE = np.load(f"{ART}/item_emb.npy"), np.load(f"{ART}/genre_mat.npy")
    GNORM = np.linalg.norm(GENRE, axis=1) + 1e-8
    RANKER = lgb.Booster(model_file=f"{ART}/ranker.txt")
    ITF = pd.read_parquet(f"{ART}/item_feats.parquet"); POP, RMEAN = ITF.pop_cum.to_numpy(), ITF.rating_mean_cum.to_numpy()
    PROF = pd.read_parquet(f"{ART}/user_prof.parquet"); UGEN = pd.read_parquet(f"{ART}/user_genre.parquet")
    PROF_D = {int(u): (float(r.user_n), float(r.user_mean)) for u, r in PROF.iterrows()}
    UGEN_D = {int(u): row for u, row in zip(UGEN.index, UGEN.to_numpy())}
    META = json.load(open(f"{ART}/meta.json")); FEATS = META["rank_feats"]
    try:
        import redis
        R = redis.Redis(host=os.environ["REDIS_HOST"], decode_responses=True); R.ping()
    except Exception:
        R = fakeredis.FakeRedis(decode_responses=True)
    for u, h in json.load(open(f"{ART}/user_hist.json")).items():
        R.delete(f"hist:{u}"); R.rpush(f"hist:{u}", *h)
    TTL = int(os.environ.get("CACHE_TTL", "60"))
    BUCKETS = [5, 10, 20, 40, 80, 160, float("inf")]
    M = {"requests_total": 0, "cache_hits_total": 0, "fallback_total": 0, "errors_total": 0}
    HIST = [0] * len(BUCKETS); LAT_SUM = [0.0]; LOCK = threading.Lock()
    os.makedirs("logs", exist_ok=True); LOG_F = open("logs/served_features.jsonl", "a") if LOG else None
    app = FastAPI(title="CineMatch Recommender", version=META["model_version"])


    class Event(BaseModel):
        user_id: int
        item_id: int
        event_type: str = "play"


    def observe(ms):
        with LOCK:
            LAT_SUM[0] += ms
            for j, b in enumerate(BUCKETS):
                if ms <= b:
                    HIST[j] += 1


    def diversify(items, k, max_per_genre=3):
        out, cnt = [], {}
        for i in items:
            g = int(np.argmax(GENRE[i][1:])) + 1
            if cnt.get(g, 0) < max_per_genre:
                out.append(int(i)); cnt[g] = cnt.get(g, 0) + 1
            if len(out) == k:
                break
        return out


    @app.get("/health")
    def health():
        return {"status": "ok", "model_version": META["model_version"]}


    @app.get("/recommend/{user_id}")
    def recommend(user_id: int, k: int = 10, use_cache: bool = True):
        t0 = time.perf_counter(); M["requests_total"] += 1
        key = f"recs:{user_id}:{k}"
        if use_cache and (hit := R.get(key)):
            M["cache_hits_total"] += 1; observe(1e3 * (time.perf_counter() - t0))
            return {**json.loads(hit), "cache": True}
        hist = [int(x) for x in R.lrange(f"hist:{user_id}", 0, -1)]
        if not hist or user_id not in PROF_D:
            M["fallback_total"] += 1
            seen = set(hist); items = [i for i in META["popular"] if i not in seen][:k]
            observe(1e3 * (time.perf_counter() - t0))
            return {"user_id": user_id, "items": items, "strategy": "popularity_fallback", "cache": False}
        v = EMB[hist[-50:]].mean(0); v = (v / (np.linalg.norm(v) + 1e-8)).astype("float32")
        sc, ids = INDEX.search(v[None], 100 + len(hist))
        seen = set(hist); mask = np.array([(i not in seen) and i > 0 for i in ids[0]])
        ids, sc = ids[0][mask][:100], sc[0][mask][:100]
        n_u, mean_u = PROF_D[user_id]
        aff = GENRE[ids] @ UGEN_D[user_id] / GNORM[ids]
        X = np.column_stack([sc.astype(float), np.arange(len(ids), dtype=float), POP[ids], RMEAN[ids], aff,
                             np.full(len(ids), n_u), np.full(len(ids), mean_u)])
        order = ids[np.argsort(-RANKER.predict(X))]
        items = diversify(order, k)
        if LOG_F:
            for i, row in zip(ids, X):
                LOG_F.write(json.dumps({"user_id": user_id, "item_id": int(i), **dict(zip(FEATS, map(float, row)))}) + "\n")
            LOG_F.flush()
        resp = {"user_id": user_id, "items": items, "strategy": "two_stage", "model_version": META["model_version"]}
        R.setex(key, TTL, json.dumps(resp))
        observe(1e3 * (time.perf_counter() - t0))
        return {**resp, "cache": False}


    @app.post("/event")
    def event(e: Event):
        R.rpush(f"hist:{e.user_id}", e.item_id); R.ltrim(f"hist:{e.user_id}", -50, -1)
        for key in R.scan_iter(f"recs:{e.user_id}:*"):
            R.delete(key)
        return {"ok": True}


    @app.get("/metrics")
    def metrics():
        lines = [f"# TYPE cinematch_{k} counter\ncinematch_{k} {v}" for k, v in M.items()]
        lines.append("# TYPE cinematch_latency_ms histogram")
        for b, c in zip(BUCKETS, HIST):
            lines.append(f'cinematch_latency_ms_bucket{{le="{"+Inf" if b == float("inf") else b}"}} {c}')
        lines += [f"cinematch_latency_ms_sum {LAT_SUM[0]}", f"cinematch_latency_ms_count {HIST[-1]}"]
        return Response("\n".join(lines) + "\n", media_type="text/plain")
    ''')

    C(r'''
    def start_service(port=8001, log_features=True):
        if os.path.exists("logs/served_features.jsonl"):
            os.remove("logs/served_features.jsonl")
        env = {**os.environ, "ART_DIR": ART_DIR, "LOG_FEATURES": "1" if log_features else "0"}
        p = subprocess.Popen([sys.executable, "-m", "uvicorn", "cinematch_service:app", "--port", str(port), "--log-level", "warning"], env=env)
        for _ in range(120):
            try:
                if requests.get(f"http://127.0.0.1:{port}/health", timeout=0.5).ok:
                    return p
            except requests.exceptions.RequestException:
                time.sleep(0.5)
        p.kill(); raise RuntimeError("no arranca")


    URL = "http://127.0.0.1:8001"
    svc = start_service()
    test_pos = test.groupby("user_id").item_id.apply(set).to_dict()
    users_t = [u for u in test_pos if u in hist_b]
    u0 = users_t[0]
    a = requests.get(f"{URL}/recommend/{u0}").json(); b = requests.get(f"{URL}/recommend/{u0}").json()
    requests.post(f"{URL}/event", json={"user_id": u0, "item_id": a["items"][0]})
    c = requests.get(f"{URL}/recommend/{u0}").json()
    new = requests.get(f"{URL}/recommend/123456789").json()
    E3 = {"cache_2a": b["cache"], "invalidada_tras_evento": not c["cache"], "item_visto_excluido": a["items"][0] not in c["items"],
          "fallback_usuario_nuevo": new["strategy"] == "popularity_fallback" and len(new["items"]) == 10,
          "metrics_ok": "cinematch_requests_total" in requests.get(f"{URL}/metrics").text}
    print("E3:", E3, "→", "✅" if all(E3.values()) else "❌")
    ''')

    C(r'''
    def load_test(url, users, concurrency, n=400, cache=False):
        sess = requests.Session()
        def one(u):
            t = time.perf_counter(); r_ = sess.get(f"{url}/recommend/{u}", params={"use_cache": cache}); r_.raise_for_status()
            return 1e3 * (time.perf_counter() - t)
        us = np.random.default_rng(seed).choice(users, n); t0 = time.perf_counter()
        with ThreadPoolExecutor(concurrency) as ex:
            lat = np.array(list(ex.map(one, us)))
        return {"concurrencia": concurrency, "qps": n / (time.perf_counter() - t0),
                **{f"p{q}": np.percentile(lat, q) for q in (50, 95, 99)}}


    for _ in range(30):                       # warm-up
        requests.get(f"{URL}/recommend/{users_t[_]}", params={"use_cache": False})
    lt = pd.DataFrame([load_test(URL, users_t, c) for c in [1, 2, 4, 8, 16]])
    display(lt.round(1))
    p99_8 = float(lt.loc[lt.concurrencia == 8, "p99"].iloc[0])
    print(f"E4 · p99 con 8 concurrentes = {p99_8:.1f} ms → {'✅' if p99_8 <= 80 else '❌ (optimiza o añade workers)'}")
    fig, ax = plt.subplots(figsize=(8, 4))
    for col in ["p50", "p95", "p99"]:
        ax.plot(lt.concurrencia, lt[col], "o-", label=col)
    ax.axhline(80, ls="--", color="r", label="SLO"); ax.set_xlabel("concurrencia"); ax.set_ylabel("ms")
    ax.set_title("Proyecto 16 · latencia desde el cliente"); ax.legend(); plt.show()
    ''')

    C(r'''
    def parity_check(log_path="logs/served_features.jsonl"):
        logs = pd.read_json(log_path, lines=True).drop_duplicates(["user_id", "item_id"], keep="first")
        logs = logs[logs.user_id != u0]                      # u0 recibió un evento nearline: su historial cambió
        users = logs.user_id.unique()[:200]
        logs = logs[logs.user_id.isin(users)]
        prof, gen = user_profile(ratings[ratings.ts < t_b]); itf = item_feats_asof(t_b)
        off = []
        for u, g in logs.groupby("user_id"):
            ids, sc = retrieve(hist_b[u], 100)                 # historial del batch (sin eventos nearline)
            off.append(features_for(u, ids, sc, prof, gen, itf))
        off = pd.concat(off)
        j = logs.merge(off, on=["user_id", "item_id"], suffixes=("_srv", "_off"))
        match = np.mean([np.isclose(j[f + "_srv"], j[f + "_off"], atol=1e-5).mean() for f in RANK_FEATS])
        print(f"E5 · filas comparadas: {len(j)} · paridad = {match:.4%}")
        return match


    parity = parity_check()
    svc.terminate()
    ''')

    M(r"""
    ⚠️ Nota sobre E5: excluimos de la comparación al usuario `u0` al que le enviamos un evento (su historial cambió *nearline*,
    así que sus features legítimamente difieren del batch). En producción, el *log de features servidas* es precisamente lo
    que permite entrenar con la verdad de serving en vez de recalcularla.

    **E6 (ejemplo de respuesta):** Redis gestionado para historial y caché (TTL 60 s + invalidación por evento); `/event`
    publica en Redpanda (topic `cinematch.events`, particionado por `user_id`) y un consumidor nearline actualiza Redis;
    features de usuario/ítem en Feast con online store Redis materializado cada hora; el ranker neuronal (si sustituye a
    LightGBM) en Triton con *dynamic batching*; Prometheus raspa `/metrics`, alerta si p99 > 80 ms durante 5 min o si
    `fallback_total/requests_total` > 5 %. Ver `reference_stack/`.

    ## 🚀 Retos extra (nivel experto)

    1. Levanta el `reference_stack/docker-compose.yml` en tu máquina (Redis + Redpanda + Prometheus + Grafana) y apunta el servicio a Redis real con `REDIS_HOST`.
    2. Sustituye el ranker LightGBM por un MLP exportado a ONNX (lección §10) y sírvelo con Triton (`reference_stack/triton/`); compara p99.
    3. Implementa *hedged requests* en el cliente del load test y mide el efecto en p99.
    4. Haz el endpoint asíncrono y mueve la inferencia a un `ThreadPoolExecutor` / `run_in_threadpool`; compara con `--workers 4`.
    5. Sustituye las features de ítem por Feast (`get_online_features`) y mide cuánto añade a la latencia.
    6. Añade un *circuit breaker*: si el ranker supera 30 ms, devuelve el orden del retrieval (degradación elegante) y cuéntalo en `/metrics`.

    ## 🤔 Reflexión (conecta con MLOps)

    - ¿Qué versionarías juntos para que un rollback sea atómico (modelo, índice, features, `meta.json`)?
    - ¿Qué alertas pondrías sobre `/metrics` y cuáles requieren datos de negocio (CTR, play rate) que el servicio no ve?
    - Si mañana el batch nocturno de features falla, ¿qué ve el modelo? ¿Cómo lo detectas antes que el usuario?
    - ¿Cómo harías *shadow traffic* para probar un ranker nuevo con tráfico real sin afectar a nadie? (Módulo 17.)
    """)

    nb.save(path)


if __name__ == "__main__":
    lesson()
    project()
