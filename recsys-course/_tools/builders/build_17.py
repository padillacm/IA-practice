"""Builder del módulo 17 · MLOps y monitoreo (lección + proyecto).

Ejecutar desde la raíz del repo:  python recsys-course/_tools/builders/build_17.py
"""
import os
import sys

sys.path.insert(0, "recsys-course/_tools")
from nbbuild import Notebook  # noqa: E402

MOD = "recsys-course/17_mlops_monitoring"
os.makedirs(MOD, exist_ok=True)

PIP = r'''
!pip install -q mlflow prefect evidently pandera scikit-learn scipy pyarrow
'''

DATA_CELL = r'''
import os, io, re, zipfile, urllib.request, time, json, math, random, warnings, logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from IPython.display import display, HTML

warnings.filterwarnings("ignore")
logging.getLogger("mlflow").setLevel(logging.ERROR)
seed = 42
random.seed(seed); np.random.seed(seed)
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.3})

# SCALE = "small" → MovieLens latest-small (100K valoraciones, 1996–2018, CPU, minutos)
# SCALE = "full"  → MovieLens-25M (25M valoraciones, 1995–2019; ~2 GB RAM, ~15–25 min en CPU de Colab)
SCALE = "small"
DATA_DIR = "data"; os.makedirs(DATA_DIR, exist_ok=True)
URLS = {"small": ("https://files.grouplens.org/datasets/movielens/ml-latest-small.zip", "ml-latest-small"),
        "full": ("https://files.grouplens.org/datasets/movielens/ml-25m.zip", "ml-25m")}


def synthetic_drift(n_items=3000, years=range(1998, 2018), users_per_year=260, d=16, seed=42):
    """Fallback sin red. Catálogo que crece cada año, gustos que se desplazan (taste drift) y preferencia por novedades."""
    rng = np.random.default_rng(seed)
    item_f = rng.normal(0, 1, (n_items, d)) / np.sqrt(d)
    release = np.sort(rng.integers(1980, max(years) + 1, n_items))
    quality = rng.normal(0, 1, n_items)
    G = rng.normal(0, 1, (d, 18)); main_genre = (item_f @ G).argmax(1)
    gnames = ["Action", "Adventure", "Animation", "Children", "Comedy", "Crime", "Documentary", "Drama", "Fantasy",
              "Film-Noir", "Horror", "Musical", "Mystery", "Romance", "Sci-Fi", "Thriller", "War", "Western"]
    trend = rng.normal(0, 1, d); trend /= np.linalg.norm(trend)
    rows, uid = [], 0
    for y in years:
        frac = (y - min(years)) / (max(years) - min(years))
        avail = np.where(release <= y)[0]
        for _ in range(users_per_year):
            uid += 1
            u = rng.normal(0, 1, d) + 2.5 * frac * trend
            logit = 3 * item_f[avail] @ u + 0.8 * quality[avail] - 0.12 * (y - release[avail])
            p = np.exp(logit - logit.max()); p /= p.sum()
            n = int(rng.integers(15, 80))
            its = rng.choice(avail, size=min(n, len(avail)), replace=False, p=p)
            aff = item_f[its] @ u
            r = np.clip(np.round((3.2 + 1.5 * aff + 0.3 * quality[its] + rng.normal(0, 0.6, len(its))) * 2) / 2, 0.5, 5)
            t0 = pd.Timestamp(f"{y}-01-01").timestamp()
            ts = t0 + np.sort(rng.uniform(0, 364 * 86400, len(its)))
            rows.append(pd.DataFrame({"user_id": uid, "item_id": its + 1, "rating": r, "ts": ts.astype(int)}))
    ratings = pd.concat(rows, ignore_index=True)
    movies = pd.DataFrame({"item_id": np.arange(1, n_items + 1), "title": [f"Título {i}" for i in range(1, n_items + 1)],
                           "genres": [gnames[g] for g in main_genre], "release_year": release})
    return ratings, movies, "Sintético con drift"


def load_movielens(scale=SCALE):
    url, folder = URLS[scale]
    try:
        path = os.path.join(DATA_DIR, folder + ".zip")
        if not os.path.exists(path):
            urllib.request.urlretrieve(url, path)
        with zipfile.ZipFile(path) as z:
            r = pd.read_csv(z.open(f"{folder}/ratings.csv"))
            m = pd.read_csv(z.open(f"{folder}/movies.csv"))
        r.columns = ["user_id", "item_id", "rating", "ts"]
        m.columns = ["item_id", "title", "genres"]
        m["release_year"] = pd.to_numeric(m.title.str.extract(r"\((\d{4})\)\s*$")[0], errors="coerce")
        return r, m, folder
    except Exception as e:
        print("⚠️ Sin red o URL caída → datos sintéticos con drift:", repr(e)[:120])
        return synthetic_drift()


ratings, movies, DATASET = load_movielens()
ratings["year"] = pd.to_datetime(ratings.ts, unit="s").dt.year
movies["main_genre"] = movies.genres.str.split("|").str[0]
movies["release_year"] = movies.release_year.fillna(movies.release_year.median())
ratings = ratings.merge(movies[["item_id", "main_genre", "release_year"]], on="item_id", how="left")
ratings["item_age"] = (ratings.year - ratings.release_year).clip(lower=0)
ratings = ratings.sort_values("ts").reset_index(drop=True)
print(DATASET, ratings.shape, "| años:", ratings.year.min(), "→", ratings.year.max())
'''

MODEL_CELL = r'''
from scipy.sparse import csr_matrix


def train_als(df, dim=48, reg=20.0, iters=12, init=None, min_count=3, seed=seed):
    """ALS sin ponderar sobre la matriz implícita binaria (equivale a un SVD regularizado; Hu et al. 2008 añade pesos).

    `init` = modelo previo → *warm start*: los ítems conocidos arrancan con sus factores anteriores.
    Devuelve un dict serializable (es lo que registraremos en MLflow).
    """
    rng = np.random.default_rng(seed)
    cnt = df.item_id.value_counts()
    items = np.sort(cnt[cnt >= min_count].index.to_numpy())
    imap = pd.Series(np.arange(len(items)), index=items)
    d = df[df.item_id.isin(items)].drop_duplicates(["user_id", "item_id"])
    users, uidx = np.unique(d.user_id.to_numpy(), return_inverse=True)
    R = csr_matrix((np.ones(len(d), np.float32), (uidx, imap[d.item_id].to_numpy())), shape=(len(users), len(items)))
    Y = rng.normal(0, 0.01, (len(items), dim)).astype(np.float32)
    if init is not None:
        known = np.isin(items, init["items"])
        prev = pd.Series(np.arange(len(init["items"])), index=init["items"])
        Y[known] = init["Y"][prev[items[known]].to_numpy()]
    I = reg * np.eye(dim, dtype=np.float32)
    for _ in range(iters):
        X = (R @ Y) @ np.linalg.inv(Y.T @ Y + I)
        Y = (R.T @ X) @ np.linalg.inv(X.T @ X + I)
    Y = Y.astype(np.float32)
    pop = cnt.reindex(items).to_numpy().astype(np.float32)
    return {"items": items, "Y": Y, "G": np.linalg.inv(Y.T @ Y + I).astype(np.float32), "pop": pop,
            "trained_until": int(df.ts.max()), "n_train": int(len(d)), "dim": dim, "reg": reg}


def user_vectors(model, hists):
    """Fold-in: x_u = (YᵀY + λI)⁻¹ Y_Hᵀ 1 para cada historial (también sirve para usuarios nunca vistos)."""
    imap = pd.Series(np.arange(len(model["items"])), index=model["items"])
    rows, cols = [], []
    for r, h in enumerate(hists):
        idx = imap.reindex(h).dropna().astype(int).to_numpy()
        rows += [r] * len(idx); cols += list(idx)
    H = csr_matrix((np.ones(len(rows), np.float32), (rows, cols)), shape=(len(hists), len(model["items"])))
    return (H @ model["Y"]) @ model["G"], H


def recommend_batch(model, hists, k=10):
    X, H = user_vectors(model, hists)
    S = X @ model["Y"].T
    S += 1e-6 * np.log1p(model["pop"])[None]          # desempate por popularidad (usuarios sin ítems conocidos)
    S[H.nonzero()] = -np.inf                           # no recomendar lo ya visto
    top = np.argpartition(-S, k, axis=1)[:, :k]
    top = np.take_along_axis(top, np.argsort(-np.take_along_axis(S, top, 1), 1), 1)
    return model["items"][top], np.take_along_axis(S, top, 1)


def popularity_model(df, window_days=365):
    recent = df[df.ts >= df.ts.max() - window_days * 86400]
    cnt = recent.item_id.value_counts()
    return {"items": cnt.index.to_numpy(), "pop": cnt.to_numpy().astype(np.float32), "trained_until": int(df.ts.max())}


def recommend_pop(model, hists, k=10):
    out = []
    for h in hists:
        s = set(h); out.append([i for i in model["items"][: k + len(h)] if i not in s][:k])
    return np.array(out)


def ndcg_at_k(recs, targets, k=10):
    disc = 1 / np.log2(np.arange(2, k + 2))
    vals = []
    for r, t in zip(recs, targets):
        g = np.isin(r[:k], list(t)).astype(float)
        ideal = disc[: min(k, len(t))].sum()
        vals.append((g * disc).sum() / ideal if ideal else 0.0)
    return float(np.mean(vals))


def eval_sets_by_year(df, min_inter=10, max_users=1500):
    """Para cada año: usuarios activos ese año con ≥ min_inter interacciones. Primera mitad (temporal) = historial
    que se pliega en el modelo (fold-in); segunda mitad = objetivo. Simula 'servir al usuario durante el año'."""
    out = {}
    rng = np.random.default_rng(seed)
    for y, g in df.groupby("year"):
        g = g.sort_values("ts"); cnt = g.user_id.value_counts()
        us = cnt[cnt >= min_inter].index.to_numpy()
        if len(us) > max_users:
            us = rng.choice(us, max_users, replace=False)
        hists, tgts = [], []
        for u, gu in g[g.user_id.isin(us)].groupby("user_id"):
            it = gu.item_id.to_numpy(); h = len(it) // 2
            tg = set(it[h:]) - set(it[:h])
            if tg:
                hists.append(list(it[:h])); tgts.append(tg)
        if len(hists) >= 15:
            out[int(y)] = (hists, tgts)
    return out


EVAL = eval_sets_by_year(ratings)
print("Años evaluables:", list(EVAL)[:3], "…", list(EVAL)[-3:], "| usuarios/año (mediana):",
      int(np.median([len(v[0]) for v in EVAL.values()])))
'''


def lesson() -> None:
    path = f"{MOD}/17_mlops_monitoring.ipynb"
    nb = Notebook("Módulo 17 · MLOps y monitoreo", colab_path=path)
    M, C = nb.md, nb.code

    M(f"""
    {nb.badge()}

    # Módulo 17 · MLOps para recomendadores: tracking, orquestación, monitoreo y reentreno

    **Nivel:** 🔴 Experto · **Duración:** 5–6 h · **GPU:** no necesaria · **Unidades Colab:** 1–3 (CPU; `SCALE="full"` con ML-25M ≈ 3–5)

    **Prerrequisitos:** 02 (evaluación), 05 (factorización/ALS), 13 (feedback loops), 15 (A/B testing), 16 (serving).

    > Un recomendador no se «termina»: el catálogo cambia cada semana, los gustos cambian cada año y el propio sistema
    > cambia los datos con los que se reentrena. En este módulo construimos el **bucle de entrenamiento continuo** que
    > mantiene vivo el servicio del módulo 16, y medimos —con datos reales de 20 años de MovieLens— cuánto se degrada un
    > modelo que no se reentrena.
    """)

    M(r"""
    ## 🎯 Objetivos de aprendizaje

    1. **Registrar** experimentos y modelos en **MLflow** y gestionar despliegues con *aliases* `champion`/`challenger`.
    2. **Orquestar** un pipeline de entrenamiento continuo con **Prefect** (y saber traducirlo a Airflow, Kubeflow o Metaflow).
    3. **Validar** lotes de datos con **Pandera** (y conocer Great Expectations) antes de que contaminen el modelo.
    4. **Medir** data drift, prediction drift, *catalog drift* y **embedding drift** con **Evidently** y con implementaciones propias.
    5. **Cuantificar** la degradación de NDCG en el tiempo y **comparar** estrategias de reentreno (estático, programado, ventana deslizante, warm-start, por trigger).
    6. **Diseñar** alertas sobre métricas de negocio y simular **feedback loops**.
    7. **Ejecutar** despliegues seguros: *shadow*, *canary* con guardrails y *rollback* automático.
    8. **Describir** un sistema CI/CD/CT para recsys y los tests que lo protegen.
    """)

    M(r"""
    ## 💡 1. Intuición: los modelos se pudren

    En ML clásico (riesgo de crédito, fraude) el mundo cambia despacio. En recomendación cambian tres cosas a la vez:

    1. **El catálogo** (*catalog drift*): cada semana entran títulos que el modelo **no puede recomendar** porque no tienen embedding.
    2. **Los gustos** (*concept drift*): lo que la gente quiere ver en 2018 no es lo de 2003.
    3. **El propio sistema** (*feedback loop*): el modelo decide qué se muestra ⇒ decide qué datos tendrás para reentrenar.

    Por eso los equipos de recsys reentrenan con frecuencia (diaria o más). Monolith (ByteDance, 2022) lleva la idea al
    extremo con **entrenamiento online**: los parámetros se actualizan en minutos.

    El ciclo de **CT (Continuous Training)** —nivel 1–2 de madurez MLOps en la guía de Google Cloud— es:

    ```
    datos nuevos → validar → (¿drift? ¿toca por calendario?) → entrenar → evaluar vs champion → registrar
          ↑                                                                                  ↓
     monitoreo ← servir (canary → 100 %) ← promover alias champion ←──────────────── ¿mejor? ┘
    ```
    """)

    C(PIP)
    C(DATA_CELL)

    C(r'''
    def box(ax, xy, w, h, text, color):
        ax.add_patch(mpatches.FancyBboxPatch(xy, w, h, boxstyle="round,pad=0.03", fc=color, ec="k"))
        ax.text(xy[0] + w / 2, xy[1] + h / 2, text, ha="center", va="center", fontsize=9)


    fig, ax = plt.subplots(figsize=(13, 5)); ax.set_xlim(0, 13); ax.set_ylim(0, 5.2); ax.axis("off")
    steps = [("Ingesta\n(eventos, Kafka→lake)", "#d6eaf8"), ("Validación\n(Pandera / GX)", "#d1f2eb"),
             ("Monitor de drift\n(Evidently)", "#fdebd0"), ("Entrenar\n(warm-start / full)", "#fadbd8"),
             ("Evaluar vs\nchampion", "#e8daef"), ("Registrar\n(MLflow)", "#fcf3cf")]
    for i, (t, c) in enumerate(steps):
        box(ax, (0.2 + 2.13 * i, 3.3), 1.8, 1.1, t, c)
        if i:
            ax.annotate("", xy=(0.2 + 2.13 * i, 3.85), xytext=(2.0 + 2.13 * (i - 1), 3.85), arrowprops=dict(arrowstyle="->", lw=1.5))
    low = [("Monitoreo\n(negocio + sistema)", "#d6eaf8"), ("Servir 100 %", "#d5f5e3"), ("Canary 1→5→25 %\n+ guardrails", "#fdebd0"),
           ("Shadow\n(sin impacto)", "#ebedef"), ("alias\nchallenger", "#fcf3cf")]
    for i, (t, c) in enumerate(low):
        box(ax, (0.2 + 2.13 * i, 0.5), 1.8, 1.1, t, c)
        if i:
            ax.annotate("", xy=(2.0 + 2.13 * (i - 1), 1.05), xytext=(0.2 + 2.13 * i, 1.05), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.annotate("", xy=(9.4, 1.6), xytext=(11.75, 3.3), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.annotate("", xy=(1.1, 3.3), xytext=(1.1, 1.6), arrowprops=dict(arrowstyle="->", lw=1.5, color="#c0392b"))
    ax.text(1.25, 2.4, "trigger (drift,\ncalendario, KPI)", color="#c0392b", fontsize=8)
    ax.annotate("", xy=(5.4, 1.6), xytext=(5.4, 1.6), arrowprops=dict(arrowstyle="->"))
    ax.text(4.3, 2.0, "rollback = mover el alias\nchampion a la versión anterior", fontsize=8, color="#7d3c98")
    ax.set_title("Bucle de Continuous Training (CT) para CineMatch", fontsize=12); plt.show()
    ''')

    M(r"""
    ## 2. Los datos: 20+ años de MovieLens como «producción»

    Usamos **MovieLens latest-small** (o **ML-25M** con `SCALE="full"`) porque abarca de 1996 a 2018: cada año será un
    «periodo de producción». Antes de modelar, miremos el drift a simple vista.
    """)

    C(r'''
    by_year = ratings.groupby("year").agg(interacciones=("item_id", "size"), usuarios=("user_id", "nunique"),
                                         edad_media_item=("item_age", "mean"), rating_medio=("rating", "mean"))
    first_seen = ratings.groupby("item_id").year.min()
    by_year["items_nuevos"] = first_seen.value_counts().reindex(by_year.index).fillna(0)
    genre_share = pd.crosstab(ratings.year, ratings.main_genre, normalize="index")
    top_g = genre_share.mean().sort_values(ascending=False).index[:6]

    fig, ax = plt.subplots(1, 3, figsize=(16, 4))
    by_year.interacciones.plot.bar(ax=ax[0], color="#5dade2"); ax[0].set_title("Interacciones por año"); ax[0].tick_params(axis="x", labelsize=7)
    genre_share[top_g].plot(ax=ax[1], marker="o", ms=3); ax[1].set_title("Cuota del género principal (drift de gustos)")
    ax[1].legend(fontsize=7)
    ax2 = ax[2]; ax2.plot(by_year.index, by_year.edad_media_item, "o-", color="#e67e22", label="edad media del ítem visto")
    ax2.set_ylabel("años"); ax3 = ax2.twinx(); ax3.bar(by_year.index, by_year.items_nuevos, alpha=0.3, label="ítems nuevos")
    ax2.set_title("Catálogo: edad de lo consumido e ítems nuevos"); ax2.legend(loc="upper left", fontsize=8)
    plt.tight_layout(); plt.show()
    ''')

    M(r"""
    ## 📐 3. Teoría: tipos de drift y cómo medirlos

    Sea $P_t(X, Y)$ la distribución conjunta de features $X$ y etiqueta $Y$ en el periodo $t$:

    - **Data (covariate) drift:** cambia $P(X)$; p. ej. más usuarios móviles, otra mezcla de géneros.
    - **Concept drift:** cambia $P(Y\mid X)$; la misma película gusta menos a ese perfil.
    - **Prediction drift:** cambia la distribución de las salidas del modelo $P(\hat{y})$ — barata de medir, sin etiquetas.
    - **Catalog drift** (específico de recsys): fracción de interacciones sobre ítems **fuera del vocabulario** del modelo,
      $\text{OOV}_t = \frac{|\{(u,i)\in D_t : i \notin \mathcal{I}_{\text{modelo}}\}|}{|D_t|}$.
    - **Embedding drift:** cambio en la distribución de vectores (de usuarios o de ítems consumidos).

    Medidas habituales:

    $$\text{PSI} = \sum_{b} (p_b - q_b)\,\ln\frac{p_b}{q_b},\qquad
      \text{JS}(p\Vert q) = \tfrac12 \text{KL}(p\Vert m) + \tfrac12 \text{KL}(q\Vert m),\ m=\tfrac{p+q}{2}$$

    con $p_b, q_b$ las proporciones de referencia y actuales en el bin $b$ (regla práctica PSI: < 0,1 estable, 0,1–0,25
    moderado, > 0,25 grande). Para numéricas: test **KS** o distancia de **Wasserstein**; para categóricas: **chi²** o JS.
    Para embeddings, el método por **clasificador de dominio** entrena un clasificador que distinga referencia vs actual:
    si su ROC-AUC ≈ 0,5 no hay drift; Evidently lo recomienda como método por defecto (umbral 0,55).

    ⚠️ **Con muchos datos todo es «significativo».** Un test KS con $10^6$ filas rechaza por diferencias irrelevantes:
    usa tamaños de efecto (PSI, Wasserstein normalizada) y umbrales calibrados con históricos, no p-valores a pelo.
    """)

    C(r'''
    def psi(ref, cur, bins=10):
        edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
        p = np.histogram(np.clip(ref, edges[0], edges[-1]), edges)[0] / len(ref) + 1e-4
        q = np.histogram(np.clip(cur, edges[0], edges[-1]), edges)[0] / len(cur) + 1e-4
        return float(np.sum((p - q) * np.log(p / q)))


    def js_div(ref_cat, cur_cat):
        cats = sorted(set(ref_cat) | set(cur_cat))
        p = pd.Series(ref_cat).value_counts(normalize=True).reindex(cats).fillna(0).to_numpy() + 1e-9
        q = pd.Series(cur_cat).value_counts(normalize=True).reindex(cats).fillna(0).to_numpy() + 1e-9
        m = (p + q) / 2
        return float(0.5 * np.sum(p * np.log(p / m)) + 0.5 * np.sum(q * np.log(q / m)))


    def oov_rate(model, df):
        return float((~df.item_id.isin(model["items"])).mean())


    # Mini-ejemplo de papel: dos distribuciones de géneros
    print("JS(igual) =", round(js_div(["Drama"] * 50 + ["Comedy"] * 50, ["Drama"] * 50 + ["Comedy"] * 50), 4),
          "| JS(cambio) =", round(js_div(["Drama"] * 80 + ["Comedy"] * 20, ["Drama"] * 30 + ["Comedy"] * 50 + ["Sci-Fi"] * 20), 4))
    ''')

    M(r"""
    ## 4. El modelo y el protocolo de evaluación temporal

    Modelo: **ALS implícito** (variante sin pesos, rápida y escalable con matrices dispersas) — el módulo 05 lo explica a
    fondo. La clave para producción es el **fold-in**: el vector de un usuario se calcula al vuelo a partir de su historial,
    $x_u = (Y^\top Y + \lambda I)^{-1} Y_{H_u}^\top \mathbf{1}$, así que el modelo sirve a usuarios que no existían al entrenar.
    Lo que **no** puede hacer es recomendar ítems que no estaban en su entrenamiento.

    Protocolo: para cada año $t$ tomamos los usuarios activos; la primera mitad (temporal) de su actividad es el historial
    y la segunda, el objetivo. Un modelo «entrenado hasta el año $s$» se evalúa en todos los años $t > s$.
    """)

    C(MODEL_CELL)

    M(r"""
    ## 5. Tracking y registry con MLflow

    MLflow tiene cuatro piezas: **Tracking** (runs con params, métricas, artefactos), **Models** (formato + *flavors*;
    `pyfunc` para lógica propia), **Model Registry** (versiones de un modelo con nombre) y, desde la 2.8, **aliases**:
    punteros mutables a versiones (`models:/cinematch-retrieval@champion`). Los *stages* (Staging/Production) están
    obsoletos en favor de aliases y tags.

    Patrón **champion/challenger**: el servicio carga siempre `@champion`; el pipeline registra cada candidato como
    `@challenger`; si supera al champion en evaluación offline (y luego en canary), se mueve el alias. **Rollback = volver
    a apuntar el alias a la versión anterior** (segundos, sin redeploy si el servicio recarga el alias).

    Usamos un backend SQLite local. En equipo: servidor MLflow + Postgres + almacenamiento S3/MinIO (ver `reference_stack/`).
    """)

    C(r'''
    import mlflow
    from mlflow.tracking import MlflowClient

    mlflow.set_tracking_uri("sqlite:///mlflow.db")
    mlflow.set_experiment("cinematch-ct")
    client = MlflowClient()
    MODEL_NAME = "cinematch-retrieval"


    class ALSRecommender(mlflow.pyfunc.PythonModel):
        """Envoltorio pyfunc: entrada = DataFrame con columna 'history' (lista de item_id); salida = top-10."""

        def load_context(self, context):
            z = np.load(context.artifacts["model"], allow_pickle=False)
            self.m = {k: z[k] for k in z.files}

        def predict(self, context, model_input, params=None):
            recs, _ = recommend_batch(self.m, list(model_input["history"]), k=10)
            return pd.DataFrame({"recs": [list(map(int, r)) for r in recs]})


    def log_and_register(model, run_name, params, metrics, alias=None):
        np.savez("model.npz", **{k: model[k] for k in ("items", "Y", "G", "pop", "trained_until")})
        with mlflow.start_run(run_name=run_name) as run:
            mlflow.log_params(params); mlflow.log_metrics(metrics)
            kw = dict(python_model=ALSRecommender(), artifacts={"model": "model.npz"}, registered_model_name=MODEL_NAME)
            try:
                mlflow.pyfunc.log_model(name="model", **kw)            # MLflow ≥ 3
            except TypeError:
                mlflow.pyfunc.log_model(artifact_path="model", **kw)   # MLflow 2.x
        v = max(int(x.version) for x in client.search_model_versions(f"name='{MODEL_NAME}'"))
        if alias:
            client.set_registered_model_alias(MODEL_NAME, alias, v)
        return v
    ''')

    C(r'''
    years = sorted(EVAL)
    T0 = years[max(1, len(years) // 4)]                       # primer año "en producción"
    train0 = ratings[ratings.year < T0]
    hp_runs = []
    for dim in [16, 32, 64]:
        for reg in [5.0, 20.0]:
            m = train_als(train0[train0.year < T0 - 1], dim=dim, reg=reg)      # validación = año T0-1
            nd = ndcg_at_k(recommend_batch(m, EVAL[T0 - 1][0])[0], EVAL[T0 - 1][1]) if T0 - 1 in EVAL else 0.0
            with mlflow.start_run(run_name=f"hp-dim{dim}-reg{reg}"):
                mlflow.log_params({"dim": dim, "reg": reg, "train_until_year": T0 - 2}); mlflow.log_metric("ndcg10_val", nd)
            hp_runs.append({"dim": dim, "reg": reg, "ndcg10_val": nd})
    hp = pd.DataFrame(hp_runs).sort_values("ndcg10_val", ascending=False); display(hp)
    BEST = hp.iloc[0][["dim", "reg"]].to_dict(); BEST["dim"] = int(BEST["dim"])

    m0 = train_als(train0, **BEST)
    v0 = log_and_register(m0, f"champion-{T0}", {**BEST, "train_until_year": T0 - 1},
                          {"ndcg10_val": float(hp.iloc[0].ndcg10_val)}, alias="champion")
    champion = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}@champion")
    print("Versión champion:", v0, "→", champion.predict(pd.DataFrame({"history": [EVAL[T0][0][0]]})).recs[0])
    display(mlflow.search_runs(experiment_names=["cinematch-ct"])[["tags.mlflow.runName", "params.dim", "params.reg", "metrics.ndcg10_val"]].head(8))
    ''')

    M(r"""
    ## 6. Validación de datos: Pandera (y Great Expectations)

    Un lote corrupto (IDs nulos, ratings fuera de rango, timestamps en el futuro, duplicados por reintentos del productor
    de Kafka) puede degradar el modelo **más** que cualquier drift. La validación va **antes** de entrenar y bloquea el
    pipeline. **Pandera** define esquemas como código (ideal para tests y CI); **Great Expectations** añade *data docs*,
    *checkpoints* y perfiles, a costa de más configuración (su API cambió mucho en la versión 1.x).
    """)

    C(r'''
    try:
        import pandera.pandas as pa      # pandera ≥ 0.24
    except ImportError:
        import pandera as pa
    from pandera import Check

    NOW = int(ratings.ts.max()) + 86400
    interactions_schema = pa.DataFrameSchema(
        {
            "user_id": pa.Column(int, Check.ge(1), nullable=False),
            "item_id": pa.Column(int, Check.ge(1), nullable=False),
            "rating": pa.Column(float, Check.isin(list(np.arange(0.5, 5.01, 0.5))), nullable=False),
            "ts": pa.Column(int, [Check.gt(788_918_400), Check.le(NOW)]),  # > 1995-01-01 y no en el futuro
        },
        checks=[Check(lambda d: d.duplicated(["user_id", "item_id", "ts"]).mean() < 0.01, error="duplicados > 1 %"),
                Check(lambda d: len(d) > 50, error="lote demasiado pequeño")],
        coerce=True, strict=False,
    )


    def validate_batch(df):
        try:
            interactions_schema.validate(df, lazy=True); return True, None
        except pa.errors.SchemaErrors as e:
            return False, e.failure_cases[["column", "check", "failure_case"]].drop_duplicates(["column", "check"])


    good = ratings[ratings.year == T0][["user_id", "item_id", "rating", "ts"]]
    bad = good.copy()
    bad.loc[bad.sample(frac=0.02, random_state=seed).index, "rating"] = 10.0          # bug de escala en el cliente
    bad.loc[bad.sample(frac=0.01, random_state=1).index, "ts"] = NOW + 10**7           # reloj del dispositivo mal
    bad = pd.concat([bad, bad.head(len(bad) // 20)])                                 # reintentos duplicados
    for name, df in [("lote correcto", good), ("lote corrupto", bad)]:
        ok, fails = validate_batch(df)
        print(f"{name}: {'✅ válido' if ok else '❌ rechazado'}")
        if not ok:
            display(fails)
    ''')

    M(r"""
    ## 7. 🧪 El experimento central: ¿cuánto se degrada un modelo sin reentreno?

    Comparamos cinco estrategias, todas arrancando con el mismo modelo entrenado hasta $T_0$:

    | Estrategia | Qué hace | Coste |
    |---|---|---|
    | **Estático** | nunca reentrena | 0 |
    | **Programado (anual, histórico completo)** | reentrena cada año con todo el pasado | alto |
    | **Ventana deslizante (3 años)** | reentrena cada año solo con los 3 últimos años | medio |
    | **Warm-start incremental** | cada año, 3 iteraciones de ALS sobre el último año partiendo de los factores previos | bajo |
    | **Por trigger (drift)** | reentrena (ventana) solo si el OOV o el JS de géneros del último año superan en +5 pp / +0,01 la *línea base* medida en el primer periodo tras desplegar | variable |
    | Popularidad del último año | baseline sin personalización, recalculada cada año | mínimo |
    """)

    C(r'''
    def evaluate(model, t):
        h, tg = EVAL[t]
        recs = recommend_pop(model, h) if "Y" not in model else recommend_batch(model, h)[0]
        return ndcg_at_k(recs, tg)


    def monitor(model, df_recent):
        """Métricas de monitoreo del último periodo observado frente al modelo/referencia actuales."""
        ref = ratings[(ratings.ts <= model["trained_until"]) & (ratings.ts > model["trained_until"] - 365 * 86400)]
        return {"oov": oov_rate(model, df_recent), "js_genre": js_div(ref.main_genre, df_recent.main_genre),
                "psi_item_age": psi(ref.item_age.to_numpy(), df_recent.item_age.to_numpy())}


    D_OOV, D_JS = 0.05, 0.01      # umbrales RELATIVOS a la línea base del modelo desplegado


    def drift_alarm(mon, base, d_oov=D_OOV, d_js=D_JS):
        """Compara con la deriva 'normal' observada en el primer periodo tras desplegar (no con cero)."""
        return mon["oov"] > base["oov"] + d_oov or mon["js_genre"] > base["js_genre"] + d_js


    def simulate(strategy, years_eval, window=3):
        model = train_als(ratings[ratings.year < years_eval[0]], **BEST)
        log, base = [], None
        for t in years_eval:
            past, last = ratings[ratings.year < t], ratings[ratings.year == t - 1]
            retrained = False
            if t != years_eval[0]:
                mon = monitor(model, last)
                if strategy == "Programado (anual, completo)":
                    model, retrained = train_als(past, **BEST), True
                elif strategy == "Ventana deslizante (3 años)":
                    model, retrained = train_als(past[past.year >= t - window], **BEST), True
                elif strategy == "Warm-start incremental":
                    model, retrained = train_als(past[past.year >= t - 1], init=model, iters=3, min_count=2, **BEST), True
                elif strategy == "Por trigger (drift)":
                    if base is None:
                        base = mon                              # primer periodo tras desplegar = línea base
                    elif drift_alarm(mon, base):
                        model, retrained, base = train_als(past[past.year >= t - window], **BEST), True, None
                elif strategy == "Popularidad último año":
                    model, retrained = popularity_model(past), True
            if strategy == "Popularidad último año" and t == years_eval[0]:
                model = popularity_model(past)
            cur = ratings[ratings.year == t]
            log.append({"strategy": strategy, "year": t, "ndcg10": evaluate(model, t), "retrained": retrained,
                        **({"oov": oov_rate(model, cur)} if "Y" in model else {"oov": np.nan})})
        return log


    STRATS = ["Estático", "Programado (anual, completo)", "Ventana deslizante (3 años)", "Warm-start incremental",
              "Por trigger (drift)", "Popularidad último año"]
    years_eval = [y for y in years if y >= T0]
    t0 = time.time()
    sim = pd.DataFrame([row for s in STRATS for row in simulate(s, years_eval)])
    print(f"Simulación: {len(years_eval)} años × {len(STRATS)} estrategias en {time.time() - t0:.0f}s")
    display(sim.groupby("strategy").agg(ndcg10_medio=("ndcg10", "mean"), reentrenos=("retrained", "sum")).sort_values("ndcg10_medio"))
    ''')

    C(r'''
    colors = dict(zip(STRATS, ["#7f8c8d", "#2471a3", "#28b463", "#e67e22", "#c0392b", "#af7ac5"]))
    fig, ax = plt.subplots(1, 2, figsize=(16, 4.8), gridspec_kw={"width_ratios": [2.2, 1]})
    for s, g in sim.groupby("strategy"):
        sm = g.ndcg10.rolling(2, min_periods=1).mean()
        ax[0].plot(g.year, sm, "-", color=colors[s], label=s, lw=2 if s in ("Estático", "Por trigger (drift)") else 1.3)
        rt = g[g.retrained & (s == "Por trigger (drift)")]
        ax[0].scatter(rt.year, sm[rt.index], color=colors[s], marker="v", s=60, zorder=4)
    ax[0].set_xlabel("año de producción"); ax[0].set_ylabel("NDCG@10 (media móvil 2 años)")
    ax[0].set_title("Degradación de NDCG@10 en el tiempo con y sin reentreno (▼ = reentreno por trigger)")
    ax[0].legend(fontsize=8)
    agg = sim.groupby("strategy").agg(nd=("ndcg10", "mean"), rt=("retrained", "sum"))
    for s, r in agg.iterrows():
        ax[1].scatter(r.rt, r.nd, s=120, color=colors[s]); ax[1].annotate(s, (r.rt, r.nd), fontsize=7, xytext=(4, 4), textcoords="offset points")
    ax[1].set_xlabel("nº de reentrenos (coste)"); ax[1].set_ylabel("NDCG@10 medio"); ax[1].set_title("Calidad vs coste")
    plt.tight_layout(); plt.show()
    ''')

    M(r"""
    🧪 **Qué deberías ver** (con los datos reales y con el fallback sintético): el modelo **estático** cae año tras año —
    sobre todo porque una fracción creciente de lo que la gente ve no existe en su vocabulario (OOV). Compáralo con la
    **popularidad del último año**: un modelo personalizado pero rancio puede acabar acercándose (o cayendo por debajo) de
    un baseline trivial pero *fresco* — compruébalo con tus datos y tu escala. Reentrenar recupera la calidad; la **ventana
    deslizante** suele igualar o superar al histórico completo (lo antiguo ya no describe los gustos actuales) siendo más
    barata, y el **trigger** consigue casi lo mismo con menos reentrenos. El **warm-start** es el más barato, pero acumula
    sesgo: en producción se combina con reentrenos completos periódicos.

    ⚠️ Con `SCALE="small"` hay pocos usuarios por año y las curvas son ruidosas (por eso la media móvil). Con ML-25M las
    conclusiones se ven nítidas.
    """)

    C(r'''
    # Monitoreo del modelo ESTÁTICO año a año: ¿qué métricas sin etiquetas anticipan la caída de NDCG?
    static = train_als(ratings[ratings.year < T0], **BEST)
    mon_rows = []
    for t in years_eval:
        cur = ratings[ratings.year == t]
        h, _ = EVAL[t]
        _, top_scores = recommend_batch(static, h[:300], k=1)
        mon_rows.append({"year": t, **monitor(static, cur), "score_top1": float(np.median(top_scores))})
    mon = pd.DataFrame(mon_rows).merge(sim[sim.strategy == "Estático"][["year", "ndcg10"]], on="year")

    fig, ax = plt.subplots(1, 3, figsize=(16, 4))
    ax[0].plot(mon.year, mon.oov, "o-", label="OOV (catalog drift)"); ax[0].plot(mon.year, mon.js_genre * 10, "s-", label="JS géneros ×10")
    ax[0].plot(mon.year, mon.psi_item_age, "^-", label="PSI edad del ítem"); ax[0].legend(fontsize=8)
    ax[0].set_title("Drift del modelo estático (sin etiquetas)")
    ax[1].plot(mon.year, mon.score_top1, "o-", color="#8e44ad"); ax[1].set_title("Prediction drift: score top-1 mediano")
    ax[2].scatter(mon.oov, mon.ndcg10, c=mon.year, cmap="viridis"); ax[2].set_xlabel("OOV"); ax[2].set_ylabel("NDCG@10")
    ax[2].set_title(f"OOV vs NDCG (corr = {mon[['oov', 'ndcg10']].corr().iloc[0, 1]:.2f})")
    plt.tight_layout(); plt.show()
    ''')

    M(r"""
    ## 8. Monitoreo con Evidently

    **Evidently** (open source) genera *Reports* (y *Test Suites*) comparando un dataset de **referencia** con uno
    **actual**: detecta drift por columna eligiendo el test según tipo y tamaño (KS/chi² para muestras pequeñas,
    Wasserstein/JS para grandes), y también métricas de calidad y de ranking. En producción se ejecuta en un job
    programado y se publica en su UI o se exportan las métricas a Prometheus/Grafana.

    Construimos una tabla de monitoreo por interacción (lo que registraría el servicio): rating, edad del ítem, popularidad
    del ítem en el entrenamiento (0 si es nuevo), género principal y actividad del usuario.
    """)

    C(r'''
    def monitoring_table(df, model):
        pop = pd.Series(model["pop"], index=model["items"])
        act = df.user_id.map(df.user_id.value_counts())
        return pd.DataFrame({"rating": df.rating.astype(float), "item_age": df.item_age.astype(float),
                             "log_item_pop": np.log1p(df.item_id.map(pop).fillna(0)).astype(float),
                             "main_genre": df.main_genre.astype(str), "user_activity": act.astype(float)}).reset_index(drop=True)


    ref_df = monitoring_table(ratings[ratings.year == T0 - 1], static)
    cur_year = years_eval[-1]
    cur_df = monitoring_table(ratings[ratings.year == cur_year], static)


    def evidently_drift(ref, cur, html_path=None):
        """Devuelve {columna: (drift?, valor, método)} con la API nueva (≥0.7) o la legacy (0.4.x)."""
        out = {}
        try:
            from evidently import Report
            from evidently.presets import DataDriftPreset
            snap = Report([DataDriftPreset()]).run(current_data=cur, reference_data=ref)
            for m in snap.dict()["metrics"]:
                name = m["metric_name"]
                if name.startswith("ValueDrift"):
                    col = re.search(r"column=([^,]+)", name).group(1)
                    thr = float(re.search(r"threshold=([\d.]+)", name).group(1))
                    v = float(m["value"])
                    out[col] = ((v < thr) if "p_value" in name else (v >= thr), v, name.split("method=")[1].split(",")[0])
        except ImportError:
            from evidently.report import Report
            from evidently.metric_preset import DataDriftPreset
            snap = Report(metrics=[DataDriftPreset()]); snap.run(reference_data=ref, current_data=cur)
            res = snap.as_dict()["metrics"][1]["result"]["drift_by_columns"]
            out = {c: (r["drift_detected"], r["drift_score"], r["stattest_name"]) for c, r in res.items()}
        if html_path:
            snap.save_html(html_path)
        return out


    drift = evidently_drift(ref_df, cur_df, html_path="evidently_report.html")
    display(pd.DataFrame(drift, index=["drift", "valor", "método"]).T)
    print("Informe HTML guardado en evidently_report.html (ábrelo desde el panel de archivos de Colab)")
    ''')

    C(r'''
    # Share de columnas con drift año a año (modelo estático, referencia = último año de entrenamiento)
    share = []
    for t in years_eval:
        d = evidently_drift(ref_df, monitoring_table(ratings[ratings.year == t], static))
        share.append({"year": t, **{c: float(v[0]) for c, v in d.items()}})
    share = pd.DataFrame(share).set_index("year")
    fig, ax = plt.subplots(figsize=(12, 3.2))
    im = ax.imshow(share.T.values, aspect="auto", cmap="Reds", vmin=0, vmax=1)
    ax.set_yticks(range(share.shape[1])); ax.set_yticklabels(share.columns)
    ax.set_xticks(range(len(share))); ax.set_xticklabels(share.index, rotation=90, fontsize=7)
    ax.set_title("Evidently: columnas con drift detectado por año (rojo = drift)"); ax.grid(False); plt.show()
    ''')

    M(r"""
    ### 8.1 Embedding drift

    Las features tabulares no cuentan toda la historia: los **vectores de usuario** (fold-in) resumen gustos. Medimos su
    drift con dos métodos: **clasificador de dominio** (ROC-AUC de una regresión logística que distingue referencia vs
    actual; 0,5 = sin drift) y **MMD** con kernel RBF (*Maximum Mean Discrepancy*, Gretton et al. 2012).
    """)

    C(r'''
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score
    from sklearn.decomposition import PCA


    def domain_classifier_auc(A, B):
        X = np.vstack([A, B]); y = np.r_[np.zeros(len(A)), np.ones(len(B))]
        return float(cross_val_score(LogisticRegression(max_iter=500), X, y, cv=3, scoring="roc_auc").mean())


    def mmd_rbf(A, B, gamma=None):
        X = np.vstack([A, B]); gamma = gamma or 1.0 / (np.median(np.sum((X[:200, None] - X[None, :200]) ** 2, -1)) + 1e-9)
        k = lambda P, Q: np.exp(-gamma * np.sum((P[:, None] - Q[None]) ** 2, -1))
        return float(k(A, A).mean() + k(B, B).mean() - 2 * k(A, B).mean())


    ref_year = max(y for y in years if y < T0)
    U_ref = user_vectors(static, EVAL[ref_year][0][:300])[0]
    emb_rows = []
    for t in years_eval:
        U = user_vectors(static, EVAL[t][0][:300])[0]
        emb_rows.append({"year": t, "auc_dominio": domain_classifier_auc(U_ref, U), "mmd": mmd_rbf(U_ref[:200], U[:200])})
    emb = pd.DataFrame(emb_rows)

    fig, ax = plt.subplots(1, 2, figsize=(14, 4))
    ax[0].plot(emb.year, emb.auc_dominio, "o-", label="AUC clasificador de dominio"); ax[0].axhline(0.55, ls="--", color="r", label="umbral 0,55")
    ax2 = ax[0].twinx(); ax2.plot(emb.year, emb.mmd, "s--", color="#e67e22", label="MMD"); ax[0].legend(loc="upper left", fontsize=8)
    ax[0].set_title("Embedding drift de los vectores de usuario")
    U_last = user_vectors(static, EVAL[years_eval[-1]][0][:300])[0]
    Z = PCA(2, random_state=seed).fit_transform(np.vstack([U_ref, U_last]))
    ax[1].scatter(*Z[: len(U_ref)].T, s=8, alpha=0.5, label=f"referencia {ref_year}")
    ax[1].scatter(*Z[len(U_ref):].T, s=8, alpha=0.5, label=f"actual {years_eval[-1]}")
    ax[1].set_title("PCA de vectores de usuario: referencia vs actual"); ax[1].legend()
    plt.tight_layout(); plt.show()
    ''')

    M(r"""
    ## 9. Métricas de negocio y alertas

    Las métricas de modelo (NDCG offline, drift) son **proxies**. Lo que importa son métricas de producto: *play rate*
    de la home, horas vistas, % de sesiones con al menos un play, retención. Diseño típico de alertas en tres capas:

    1. **Sistema** (Prometheus, módulo 16): latencia p99, errores, tasa de fallback.
    2. **Datos/modelo** (Evidently): drift, OOV, frescura de features, volumen de eventos.
    3. **Negocio**: KPIs con estacionalidad ⇒ **no** uses umbrales fijos; compara con el mismo día de la semana o con una
       predicción (z-score sobre residuos), y alerta solo si persiste ($N$ de $M$ ventanas).

    Simulamos 120 días de *play rate* con estacionalidad semanal y un incidente silencioso el día 80 (las features de
    ítem dejan de actualizarse y la calidad cae un 8 %).
    """)

    C(r'''
    rng = np.random.default_rng(seed)
    days = np.arange(120)
    base = 0.31 + 0.025 * np.sin(2 * np.pi * days / 7) + 0.0002 * days
    play = base * np.where(days >= 80, 0.92, 1.0) + rng.normal(0, 0.004, len(days))
    s = pd.Series(play)
    # Detector 1: umbral fijo
    alert_fixed = s < 0.29
    # Detector 2: z-score frente a las 4 semanas previas del MISMO día de la semana + persistencia 2 de 3 días
    ref_mean = sum(s.shift(7 * k) for k in range(1, 5)) / 4
    ref_std = pd.concat([s.shift(7 * k) for k in range(1, 5)], axis=1).std(axis=1) + 0.003
    z = (s - ref_mean) / ref_std
    alert_z = (z < -3).astype(int).rolling(3).sum() >= 2

    fig, ax = plt.subplots(2, 1, figsize=(13, 5.5), sharex=True)
    ax[0].plot(days, play, label="play rate diario"); ax[0].axhline(0.29, ls="--", color="gray", label="umbral fijo")
    ax[0].axvline(80, color="r", alpha=0.4, label="incidente (día 80)")
    ax[0].scatter(days[alert_fixed], play[alert_fixed], color="gray", marker="x", label="alerta umbral fijo")
    ax[0].scatter(days[alert_z], play[alert_z], color="r", marker="v", s=50, label="alerta z-score estacional")
    ax[0].legend(fontsize=8, ncol=3); ax[0].set_title("Alertas sobre una métrica de negocio con estacionalidad")
    ax[1].plot(days, z, color="#8e44ad"); ax[1].axhline(-3, ls="--", color="r"); ax[1].set_ylabel("z (mismo día semana)")
    ax[1].set_xlabel("día"); plt.tight_layout(); plt.show()
    first = days[alert_z.to_numpy()]
    print("Falsos positivos umbral fijo (antes del día 80):", int(alert_fixed[:80].sum()),
          "| primera alerta z-score: día", int(first[first >= 80][0]) if (first >= 80).any() else None,
          "| falsos positivos z:", int((first < 80).sum()))
    ''')

    M(r"""
    ## 10. Feedback loops

    El recomendador decide qué se muestra; los usuarios solo pueden hacer clic en lo mostrado; el siguiente modelo se
    entrena con esos clics. Resultado: **rich-get-richer**, homogeneización y menor utilidad a largo plazo (Chaney, Stewart
    & Engelhardt, RecSys 2018). Simulamos 40 rondas de reentreno con preferencias reales fijas y comparamos una política
    *greedy* con una que reserva un 10 % de slots a exploración (ε-greedy) — lo que verás formalizado en el módulo 14.
    """)

    C(r'''
    def feedback_loop(eps, rounds=40, n_u=400, n_i=300, k=10, seed=seed):
        r_ = np.random.default_rng(seed)
        U, V = r_.normal(0, 1, (n_u, 8)), r_.normal(0, 1, (n_i, 8))
        true_ctr = 1 / (1 + np.exp(-(U @ V.T / 2 - 2.5)))            # preferencias reales (desconocidas)
        clicks, imps = np.ones(n_i), np.full(n_i, 20.0)              # prior: todos los ítems iguales
        exposure, gini, util = np.zeros(n_i), [], []
        for _ in range(rounds):
            est = clicks / imps                                      # "modelo" = CTR estimado de lo logueado
            rec = np.tile(np.argsort(-est)[:k], (n_u, 1))
            explore = r_.random((n_u, k)) < eps
            rec[explore] = r_.integers(0, n_i, explore.sum())
            c = r_.random((n_u, k)) < np.take_along_axis(true_ctr, rec, 1)
            np.add.at(imps, rec.ravel(), 1); np.add.at(clicks, rec.ravel(), c.ravel()); np.add.at(exposure, rec.ravel(), 1)
            x = np.sort(exposure); n = len(x)
            gini.append(float((2 * np.arange(1, n + 1) - n - 1) @ x / (n * x.sum())))
            util.append(float(np.take_along_axis(true_ctr, rec, 1).mean()))
        return gini, util


    fig, ax = plt.subplots(1, 2, figsize=(13, 4))
    for eps in [0.0, 0.1, 0.3]:
        g, u = feedback_loop(eps)
        ax[0].plot(g, label=f"ε = {eps}"); ax[1].plot(pd.Series(u).rolling(3, min_periods=1).mean(), label=f"ε = {eps}")
    ax[0].set_title("Concentración de exposición (Gini acumulado)"); ax[0].set_xlabel("ronda de reentreno"); ax[0].legend()
    ax[1].set_title("CTR real medio de lo recomendado"); ax[1].set_xlabel("ronda de reentreno"); ax[1].legend()
    plt.tight_layout(); plt.show()
    ''')

    M(r"""
    🧠 Implicación MLOps: si el log de entrenamiento lo genera tu propia política, **guarda la propensión** (probabilidad
    de mostrar cada ítem) junto a cada impresión. Sin ella no podrás hacer *off-policy evaluation* ni corregir el sesgo
    (IPS, módulo 14), y tus evaluaciones offline premiarán al modelo que más se parezca al actual.

    ## 11. Orquestación: Prefect (ejecutable) y sus primos

    | Herramienta | Modelo | Puntos fuertes | Cuándo |
    |---|---|---|---|
    | **Airflow** | DAGs declarados en Python, scheduler central | estándar de facto en data eng, cientos de operadores | el equipo de datos ya lo usa |
    | **Prefect** | flows/tasks = funciones Python decoradas | DX excelente, flujos dinámicos, ejecutable local | equipos ML pequeños/medios, este notebook |
    | **Kubeflow Pipelines** | componentes en contenedores sobre Kubernetes | aislamiento, GPUs, escala | plataforma ML sobre K8s |
    | **Metaflow** (creado en Netflix, open source 2019) | `FlowSpec` con `@step`, versionado automático de artefactos | del portátil a AWS Batch/K8s con un decorador (`@resources`, `@batch`) | científicos de datos que no quieren pelear con infra |

    En `reference_stack/` tienes el mismo pipeline como **DAG de Airflow**, **flow de Metaflow** y **pipeline de Kubeflow**.
    Aquí lo ejecutamos con **Prefect** (arranca un servidor temporal local la primera vez; tarda ~20–30 s).
    """)

    C(r'''
    from prefect import flow, task
    try:                                   # Prefect 3: sin caché de inputs (DataFrames grandes no se hashean bien)
        from prefect.cache_policies import NO_CACHE
        TASK_KW = {"cache_policy": NO_CACHE}
    except ImportError:
        TASK_KW = {}

    PROMOTION_MARGIN = 0.0   # el challenger debe ser ≥ champion en el año de validación


    @task(retries=2, retry_delay_seconds=2, **TASK_KW)
    def ingest(year: int) -> pd.DataFrame:
        return ratings[ratings.year == year]


    @task(**TASK_KW)
    def validate(batch: pd.DataFrame) -> bool:
        ok, fails = validate_batch(batch[["user_id", "item_id", "rating", "ts"]])
        if not ok:
            print("Lote rechazado:\n", fails)
        return ok


    @task(**TASK_KW)
    def check_drift(model: dict, batch: pd.DataFrame) -> dict:
        return monitor(model, batch)


    @task(**TASK_KW)
    def train(until_year: int, window: int = 3) -> dict:
        past = ratings[(ratings.year < until_year) & (ratings.year >= until_year - window)]
        return train_als(past, **BEST)


    @task(**TASK_KW)
    def evaluate_on(model: dict, year: int) -> float:
        return evaluate(model, year)


    @flow(name="cinematch-continuous-training", log_prints=True)
    def ct_flow(year: int, d_oov: float = D_OOV, d_js: float = D_JS) -> dict:
        """Se ejecuta al inicio de `year`. Usa el año anterior como 'datos nuevos' y como validación.
        La línea base de drift de cada versión se guarda como TAG de la versión en el registry."""
        champ_info = client.get_model_version_by_alias(MODEL_NAME, "champion")
        champ = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}@champion").unwrap_python_model().m
        batch = ingest(year - 1)
        if not validate(batch):
            return {"year": year, "action": "bloqueado_por_validacion", "champion": champ_info.version}
        d = check_drift(champ, batch)
        if "baseline_oov" not in champ_info.tags:            # primer periodo tras desplegar → registrar línea base
            client.set_model_version_tag(MODEL_NAME, champ_info.version, "baseline_oov", str(d["oov"]))
            client.set_model_version_tag(MODEL_NAME, champ_info.version, "baseline_js", str(d["js_genre"]))
            print(f"{year}: línea base registrada para v{champ_info.version}: {d}")
            return {"year": year, "action": "sin_cambios", "champion": champ_info.version, **d}
        base = {"oov": float(champ_info.tags["baseline_oov"]), "js_genre": float(champ_info.tags["baseline_js"])}
        if not drift_alarm(d, base, d_oov, d_js):
            print(f"{year}: sin drift relevante {d} → no reentreno")
            return {"year": year, "action": "sin_cambios", "champion": champ_info.version, **d}
        challenger = train(year - 1)                       # entrena con datos hasta year-2 …
        nd_ch, nd_cp = evaluate_on(challenger, year - 1), evaluate_on(champ, year - 1)   # … valida en year-1
        challenger = train(year)                           # y reentrena incluyendo year-1 para servir
        v = log_and_register(challenger, f"challenger-{year}", {**BEST, "window": 3, "train_until_year": year - 1},
                             {"ndcg10_val_challenger": nd_ch, "ndcg10_val_champion": nd_cp, **d}, alias="challenger")
        if nd_ch >= nd_cp + PROMOTION_MARGIN:
            client.set_registered_model_alias(MODEL_NAME, "champion", v)
            action = "promovido"
        else:
            action = "rechazado"
        print(f"{year}: drift {d} · challenger {nd_ch:.4f} vs champion {nd_cp:.4f} → {action} (v{v})")
        return {"year": year, "action": action, "champion": client.get_model_version_by_alias(MODEL_NAME, "champion").version, **d}
    ''')

    C(r'''
    # Ejecutamos el flow una vez por "año de producción" (en producción: un cron semanal/diario o un evento de drift)
    client.set_registered_model_alias(MODEL_NAME, "champion", v0)
    try:
        ct_log = [ct_flow(y) for y in years_eval[1:]]
    except Exception as e:      # p. ej. si el servidor temporal de Prefect no arranca en tu entorno
        print("⚠️ Prefect falló, ejecuto las funciones sin orquestador:", repr(e)[:200])
        ct_log = [ct_flow.fn(y) for y in years_eval[1:]]
    ct = pd.DataFrame(ct_log); display(ct[["year", "action", "champion", "oov", "js_genre"]])
    ''')

    C(r'''
    # Registry tras la simulación: versiones, aliases y un rollback de un clic
    versions = sorted(client.search_model_versions(f"name='{MODEL_NAME}'"), key=lambda x: int(x.version))
    aliases = client.get_registered_model(MODEL_NAME).aliases
    print("Versiones:", [x.version for x in versions], "| aliases:", aliases)
    champ_v = int(client.get_model_version_by_alias(MODEL_NAME, "champion").version)
    prev = [int(x.version) for x in versions if int(x.version) < champ_v]
    if prev:
        client.set_registered_model_alias(MODEL_NAME, "champion", prev[-1])   # 🔙 ROLLBACK
        print(f"Rollback: champion v{champ_v} → v{prev[-1]}")
        client.set_registered_model_alias(MODEL_NAME, "champion", champ_v)    # y vuelta atrás
    timeline = ct.assign(champion=ct.champion.astype(int))
    fig, ax = plt.subplots(figsize=(11, 3))
    ax.step(timeline.year, timeline.champion, where="post", color="#2471a3")
    for _, r in timeline.iterrows():
        ax.scatter(r.year, r.champion, color={"promovido": "g", "rechazado": "r", "sin_cambios": "gray"}.get(r.action, "k"), zorder=3)
    ax.set_xlabel("año"); ax.set_ylabel("versión champion"); ax.set_title("Línea temporal del alias champion (verde = promoción, rojo = challenger rechazado)")
    plt.show()
    ''')

    M(r"""
    ## 12. Despliegue seguro: shadow, canary y rollback

    - **Shadow (dark launch):** el challenger recibe una copia del tráfico, calcula su respuesta y se **loguea** pero no se
      muestra. Detecta errores, latencia y diferencias de distribución sin riesgo. No mide impacto en usuarios.
    - **Canary:** un % pequeño y creciente de usuarios ve el challenger (1 → 5 → 25 → 50 → 100 %). En cada escalón se
      comprueban **guardrails** (latencia, errores, *play rate*); si empeoran de forma significativa → **rollback automático**.
    - **A/B test completo** (módulo 15): la decisión de producto con potencia estadística. Canary ≠ A/B: el canary protege,
      el A/B decide.
    - **Interleaving** (Netflix, 2017) para comparar rankers con muchísimos menos usuarios.

    Simulamos un canary con un challenger **malo** (CTR real 4,7 % vs 5,0 %) y otro **bueno** (5,2 %).
    """)

    C(r'''
    from scipy.stats import norm


    def canary(ctr_ch, ctr_cp=0.050, steps=(0.01, 0.05, 0.25, 0.5, 1.0), req_per_step=400_000, alpha=0.05, seed=seed):
        r_ = np.random.default_rng(seed); hist = []
        for st in steps:
            n_ch = int(req_per_step * st); n_cp = req_per_step - n_ch if st < 1 else req_per_step // 2
            c_ch, c_cp = r_.binomial(n_ch, ctr_ch), r_.binomial(n_cp, ctr_cp)
            p1, p0 = c_ch / n_ch, c_cp / n_cp
            se = np.sqrt(p1 * (1 - p1) / n_ch + p0 * (1 - p0) / n_cp)
            diff, lo, hi = p1 - p0, p1 - p0 - norm.ppf(1 - alpha) * se, p1 - p0 + norm.ppf(1 - alpha) * se
            hist.append({"tráfico": st, "diff": diff, "lo": lo, "hi": hi})
            if hi < 0:                                     # significativamente peor (unilateral) → rollback
                hist[-1]["acción"] = "ROLLBACK"; break
            hist[-1]["acción"] = "avanzar"
        return pd.DataFrame(hist)


    fig, ax = plt.subplots(1, 2, figsize=(13, 4))
    for j, (lab, c) in enumerate([("challenger malo (4,7 %)", 0.047), ("challenger bueno (5,2 %)", 0.052)]):
        h = canary(c); x = np.arange(len(h))
        ax[j].errorbar(x, h["diff"], yerr=[h["diff"] - h.lo, h.hi - h["diff"]], fmt="o", capsize=4)
        ax[j].axhline(0, color="k", ls="--"); ax[j].set_xticks(x); ax[j].set_xticklabels([f"{int(100 * t)} %" for t in h["tráfico"]])
        ax[j].set_title(f"{lab}: {h['acción'].iloc[-1]}"); ax[j].set_xlabel("escalón de tráfico"); ax[j].set_ylabel("CTR challenger − champion")
    plt.tight_layout(); plt.show()
    ''')

    M(r"""
    ## 13. CI/CD/CT para recomendadores

    | Capa | Qué se prueba | Ejemplos (recsys) |
    |---|---|---|
    | **CI (código)** | unit tests, lint, tipos | feature builder, métricas, serialización |
    | **CI (datos)** | esquemas y expectativas | Pandera en una muestra del día; volumen ±30 % vs semana anterior |
    | **CI (modelo)** | tests de comportamiento | NDCG ≥ baseline de popularidad; no recomienda vistos; no recomienda ítems bloqueados; determinismo |
    | **CD** | empaquetado y despliegue | imagen Docker, paridad ONNX, latencia p99 en *smoke test*, shadow |
    | **CT** | pipeline de reentreno | trigger por calendario/drift, evaluación vs champion, promoción de alias |

    *The ML Test Score* (Breck et al., 2017) ofrece una rúbrica de 28 tests (datos, modelo, infraestructura, monitoreo).
    El workflow de GitHub Actions de referencia está en `reference_stack/ci/github-actions-ct.yml`. Estos son tests de
    modelo ejecutables:
    """)

    C(r'''
    champ = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}@champion").unwrap_python_model().m
    yt = years_eval[-1]; h, tg = EVAL[yt]


    def test_beats_popularity():
        assert ndcg_at_k(recommend_batch(champ, h)[0], tg) >= 0.8 * ndcg_at_k(recommend_pop(popularity_model(ratings[ratings.year < yt]), h), tg)


    def test_no_seen_items():
        recs = recommend_batch(champ, h[:200])[0]
        assert all(not (set(r) & set(hh)) for r, hh in zip(recs, h[:200]))


    def test_deterministic():
        assert (recommend_batch(champ, h[:50])[0] == recommend_batch(champ, h[:50])[0]).all()


    def test_cold_user_gets_k_items():
        assert recommend_batch(champ, [[]], k=10)[0].shape == (1, 10)


    def test_latency_budget():
        t = time.perf_counter(); recommend_batch(champ, h[:100]); assert (time.perf_counter() - t) / 100 < 0.05


    for t in [test_beats_popularity, test_no_seen_items, test_deterministic, test_cold_user_gets_k_items, test_latency_budget]:
        try:
            t(); print("✅", t.__name__)
        except AssertionError:
            print("❌", t.__name__)
    ''')

    M(r"""
    ## 🏭 En producción

    - **Netflix** creó y liberó **Metaflow** (2019) para que los científicos de datos lleven pipelines del portátil a
      producción; su orquestador interno **Maestro** también es open source (2024). Su sistema de experimentación (A/B +
      interleaving) es el árbitro final de cualquier cambio de modelo.
    - **Uber Michelangelo** (2017) estandarizó el ciclo completo: gestión de datos, entrenamiento, evaluación, despliegue,
      predicción y **monitoreo de predicciones** frente a resultados observados.
    - **ByteDance Monolith** (2022): entrenamiento **online** con sincronización de parámetros al serving en minutos y la
      observación de que se puede sacrificar algo de fiabilidad a cambio de aprendizaje en tiempo real.
    - **Booking.com** (Bernardi et al., KDD 2019, *150 Successful Machine Learning Models*): mejoras offline no se
      correlacionan necesariamente con mejoras de negocio; todo pasa por experimentos controlados y se monitoriza la
      distribución de las predicciones como señal temprana sin etiquetas.
    - **Shankar et al. (2022)**, entrevistas a 18 ML engineers: el éxito en producción depende de *velocity*, *validation*
      y *versioning*; la mayoría de equipos reentrena con cadencia fija y valida con datos recientes.
    - **Spotify** (2021, *The Rise (and Lessons Learned) of ML Models to Personalize Content on Home*): lecciones de llevar
      modelos de la home a producción, incluida la importancia de herramientas de evaluación y monitoreo comunes.

    ## 🧠 Secretos de la élite

    1. **El primer baseline a batir en producción es «el mismo modelo, reentrenado».** Muchas «mejoras» de arquitectura desaparecen cuando el champion se reentrena con la misma frescura.
    2. **Monitoriza el OOV / cobertura de catálogo**: en recsys es el predictor sin etiquetas más fiable de la caída de calidad (lo has visto en §7).
    3. **Un p-valor de drift con millones de filas no significa nada**; usa tamaños de efecto con umbrales calibrados en históricos y alertas con persistencia.
    4. **Warm-start sí, pero con reentreno completo periódico**: el warm-start arrastra sesgos y factores de ítems muertos; combínalo con un *full retrain* semanal/mensual.
    5. **Guarda propensiones y la versión del modelo en cada impresión.** Sin eso no hay OPE, ni análisis de feedback loops, ni depuración de incidentes.
    6. **La ventana de entrenamiento es un hiperparámetro** (y suele ganar a «todo el histórico»); tunéala con el protocolo temporal, nunca con split aleatorio.
    7. **Promociona con alias, no con redeploys**: un rollback que requiere build de imagen no es un rollback, es un incidente largo.
    8. **Alerta sobre métricas de negocio con estacionalidad modelada** (mismo día de la semana, festivos), o tu on-call aprenderá a ignorar las alertas.

    ## ⚠️ Errores comunes

    - Evaluar el challenger con un split aleatorio o con datos del futuro respecto al champion.
    - Comparar challenger y champion en conjuntos de evaluación distintos (cambia el denominador → conclusiones falsas).
    - Reentrenar sobre datos sin validar (un lote duplicado por reintentos sesga la popularidad).
    - Disparar reentrenos por cada alerta de drift sin evaluar si el drift afecta a la métrica (*alert fatigue* y coste).
    - No versionar datos de entrenamiento (sin *snapshot* no puedes reproducir ni auditar un modelo).
    - Olvidar que el reentreno cambia los embeddings: índice ANN, cachés y modelos downstream deben actualizarse **juntos**.

    ## 📝 Autoevaluación

    1. ¿Por qué un modelo estático puede acabar perdiendo frente a un baseline de popularidad reciente?
    <details><summary>Respuesta</summary>Porque una fracción creciente de interacciones ocurre sobre ítems que no existían cuando se entrenó (OOV) y los gustos se desplazan; la popularidad reciente, aunque no personaliza, es fresca y captura los estrenos.</details>

    2. Diferencia entre data drift, concept drift y prediction drift. ¿Cuál puedes medir sin etiquetas?
    <details><summary>Respuesta</summary>Data drift: cambia P(X). Concept drift: cambia P(Y|X). Prediction drift: cambia P(ŷ). Data y prediction drift se miden sin etiquetas; el concept drift necesita etiquetas (o proxies retrasados).</details>

    3. ¿Qué ventaja tienen los aliases de MLflow frente a desplegar una nueva imagen para cada modelo?
    <details><summary>Respuesta</summary>Desacoplan el código de servicio del modelo: el servicio carga `@champion`; promover o hacer rollback es mover un puntero (segundos, auditable), sin build ni redeploy.</details>

    4. ¿Por qué un test KS con 10⁶ filas no es buen trigger de reentreno?
    <details><summary>Respuesta</summary>Con muestras enormes cualquier diferencia minúscula es estadísticamente significativa; dispararía reentrenos constantes. Hay que usar tamaños de efecto (PSI, Wasserstein) con umbrales calibrados y relacionados con impacto en la métrica.</details>

    5. ¿Qué es un feedback loop en recsys y qué dato debes loguear para poder corregirlo?
    <details><summary>Respuesta</summary>El modelo determina la exposición y por tanto los datos con los que se reentrena, reforzando sus propias decisiones (popularidad, homogeneización). Hay que loguear la propensión de cada impresión (y la versión del modelo) para IPS/OPE.</details>

    6. Shadow vs canary: ¿qué detecta cada uno?
    <details><summary>Respuesta</summary>Shadow detecta errores, latencia y diferencias de salida sin impacto en usuarios, pero no mide efecto en comportamiento. Canary expone a un % real de usuarios y mide guardrails de negocio con rollback automático.</details>

    7. Propón una política de reentreno para CineMatch y justifícala.
    <details><summary>Respuesta</summary>Ejemplo: warm-start diario con los eventos del día (frescura e ítems nuevos), reentreno completo semanal con ventana deslizante tuneada, trigger extra si OOV > umbral o caída de play rate persistente; cada candidato pasa validación de datos, evaluación vs champion en el mismo split temporal, shadow y canary con guardrails.</details>

    ## 📚 Referencias

    - Sculley, D. et al. (2015). *Hidden Technical Debt in Machine Learning Systems*. NeurIPS.
    - Breck, E., Cai, S., Nielsen, E., Salib, M., Sculley, D. (2017). *The ML Test Score: A Rubric for ML Production Readiness and Technical Debt Reduction*. IEEE Big Data.
    - Shankar, S., Garcia, R., Hellerstein, J. M., Parameswaran, A. (2022). *Operationalizing Machine Learning: An Interview Study*. arXiv:2209.09125
    - Bernardi, L., Mavridis, T., Estevez, P. (2019). *150 Successful Machine Learning Models: 6 Lessons Learned at Booking.com*. KDD.
    - Chaney, A., Stewart, B., Engelhardt, B. (2018). *How Algorithmic Confounding in Recommendation Systems Increases Homogeneity and Decreases Utility*. RecSys. arXiv:1710.11214
    - Gama, J. et al. (2014). *A Survey on Concept Drift Adaptation*. ACM Computing Surveys.
    - Rabanser, S., Günnemann, S., Lipton, Z. (2019). *Failing Loudly: An Empirical Study of Methods for Detecting Dataset Shift*. NeurIPS. arXiv:1810.11953
    - Gretton, A. et al. (2012). *A Kernel Two-Sample Test*. JMLR (MMD).
    - Liu, Z. et al. (2022). *Monolith: Real Time Recommendation System With Collisionless Embedding Table*. arXiv:2209.07663
    - Hu, Y., Koren, Y., Volinsky, C. (2008). *Collaborative Filtering for Implicit Feedback Datasets*. ICDM.
    - Google Cloud. *MLOps: Continuous delivery and automation pipelines in machine learning*. https://cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning
    - Evidently AI (2023). *Shift happens: we compared 5 methods to detect drift in ML embeddings*. https://www.evidentlyai.com/blog/embedding-drift-detection
    - Netflix Tech Blog (2019). *Open-Sourcing Metaflow, a Human-Centric Framework for Data Science*.
    - Del Balso, M. & Hermann, J. (2017). *Meet Michelangelo: Uber's Machine Learning Platform*. https://www.uber.com/blog/michelangelo-machine-learning-platform/
    - Harper, F. M. & Konstan, J. A. (2015). *The MovieLens Datasets: History and Context*. ACM TiiS.

    **Herramientas:** MLflow (https://mlflow.org) · Prefect (https://docs.prefect.io) · Evidently (https://docs.evidentlyai.com) · Pandera · Great Expectations · Apache Airflow · Kubeflow Pipelines · Metaflow (https://metaflow.org) · Prometheus + Grafana.

    ➡️ **Siguiente:** el proyecto (pipeline CT completo con MLflow + Prefect + Evidently) y el capstone (módulo 18).
    """)

    nb.save(path)


UTILS_CELL = r'''
try:
    import pandera.pandas as pa
except ImportError:
    import pandera as pa
from pandera import Check
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score


def js_div(ref_cat, cur_cat):
    cats = sorted(set(ref_cat) | set(cur_cat))
    p = pd.Series(ref_cat).value_counts(normalize=True).reindex(cats).fillna(0).to_numpy() + 1e-9
    q = pd.Series(cur_cat).value_counts(normalize=True).reindex(cats).fillna(0).to_numpy() + 1e-9
    m = (p + q) / 2
    return float(0.5 * np.sum(p * np.log(p / m)) + 0.5 * np.sum(q * np.log(q / m)))


def oov_rate(model, df):
    return float((~df.item_id.isin(model["items"])).mean())


def monitoring_table(df, model):
    pop = pd.Series(model["pop"], index=model["items"])
    act = df.user_id.map(df.user_id.value_counts())
    return pd.DataFrame({"rating": df.rating.astype(float), "item_age": df.item_age.astype(float),
                         "log_item_pop": np.log1p(df.item_id.map(pop).fillna(0)).astype(float),
                         "main_genre": df.main_genre.astype(str), "user_activity": act.astype(float)}).reset_index(drop=True)


def evidently_drift(ref, cur, html_path=None):
    """{columna: (drift?, valor, método)} con Evidently ≥0.7 (o API legacy 0.4.x)."""
    out = {}
    try:
        from evidently import Report
        from evidently.presets import DataDriftPreset
        snap = Report([DataDriftPreset()]).run(current_data=cur, reference_data=ref)
        for m in snap.dict()["metrics"]:
            name = m["metric_name"]
            if name.startswith("ValueDrift"):
                col = re.search(r"column=([^,]+)", name).group(1)
                thr = float(re.search(r"threshold=([\d.]+)", name).group(1)); v = float(m["value"])
                out[col] = ((v < thr) if "p_value" in name else (v >= thr), v, name.split("method=")[1].split(",")[0])
    except ImportError:
        from evidently.report import Report
        from evidently.metric_preset import DataDriftPreset
        snap = Report(metrics=[DataDriftPreset()]); snap.run(reference_data=ref, current_data=cur)
        res = snap.as_dict()["metrics"][1]["result"]["drift_by_columns"]
        out = {c: (r["drift_detected"], r["drift_score"], r["stattest_name"]) for c, r in res.items()}
    if html_path:
        snap.save_html(html_path)
    return out


def domain_classifier_auc(A, B):
    X = np.vstack([A, B]); y = np.r_[np.zeros(len(A)), np.ones(len(B))]
    return float(cross_val_score(LogisticRegression(max_iter=500), X, y, cv=3, scoring="roc_auc").mean())


def evaluate(model, t):
    h, tg = EVAL[t]
    return ndcg_at_k(recommend_batch(model, h)[0], tg)


years = sorted(EVAL)
T0 = years[max(1, len(years) // 4)]
YEARS_PROD = [y for y in years if y >= T0]
HP = {"dim": 32, "reg": 20.0}
print("Años de producción simulados:", YEARS_PROD[0], "→", YEARS_PROD[-1])
'''


def project() -> None:
    path = f"{MOD}/17_proyecto_pipeline_ct.ipynb"
    nb = Notebook("Proyecto 17 · Pipeline de entrenamiento continuo", colab_path=path)
    M, C = nb.md, nb.code

    M(f"""
    {nb.badge()}

    # Proyecto 17 · Pipeline de entrenamiento continuo con MLflow + Prefect + Evidently

    **Nivel:** 🔴 Experto · **Duración:** 4–6 h · **GPU:** no necesaria · **Unidades Colab:** 1–2 (CPU)

    ## 🏢 Contexto de negocio

    El servicio de CineMatch del proyecto 16 está en producción. Tres meses después, el *play rate* de la home ha caído un
    4 % y nadie sabe por qué: el modelo se entrenó una vez y nunca más. La VP de producto te pide un **sistema de
    entrenamiento continuo** que (a) bloquee datos corruptos, (b) detecte drift, (c) reentrene solo cuando haga falta —el
    cómputo cuesta—, (d) promueva modelos solo si son mejores y (e) permita **rollback en segundos**.

    Simularás ~15–20 años de producción con MovieLens (cada año = un periodo).

    ## 📦 Dataset

    **MovieLens latest-small** (GroupLens, 100 836 valoraciones, 610 usuarios, 9 742 películas, 1996–2018) —
    https://files.grouplens.org/datasets/movielens/ml-latest-small.zip. Con `SCALE = "full"`: **ML-25M** (25M valoraciones,
    1995–2019). Fallback sintético con drift si no hay red.

    ## ✅ Entregables y rúbrica (100 puntos)

    | # | Entregable | Criterio objetivo | Puntos |
    |---|---|---|---|
    | E1 | Esquema Pandera `SCHEMA` | acepta **todos** los lotes anuales reales y rechaza los 3 lotes corruptos de prueba | 15 |
    | E2 | `drift_report(model, batch, ref_batch)` | devuelve `oov`, `js_genre`, `evidently_share`, `emb_auc`; gráfico por año para el modelo estático | 20 |
    | E3 | Flow de Prefect `ct_pipeline(year)` | tareas ingest → validate → drift → (train → evaluate → register → promote); cada candidato queda registrado en MLflow con métricas; alias `champion`/`challenger` | 25 |
    | E4 | Simulación de políticas | NDCG@10 medio de la política **por trigger** ≥ **0,95 ×** el de reentreno anual con ventana, usando **≤ 70 %** de sus reentrenos; gráfico NDCG vs año (estático / anual / trigger) | 25 |
    | E5 | Simulacro de incidente | un challenger defectuoso es **rechazado** por la puerta de calidad; un rollback manual del alias se completa y el modelo servido cambia | 15 |
    """)

    C(PIP)
    C(DATA_CELL)
    C(MODEL_CELL)
    C(UTILS_CELL)

    M(r"""
    ## Paso 1 · Validación de datos (E1)

    Define `SCHEMA` (Pandera) para lotes con columnas `user_id, item_id, rating, ts`. Debe rechazar: ratings fuera de
    {0,5, 1, …, 5}, timestamps futuros o anteriores a 1995, IDs nulos/no positivos y **> 1 % de duplicados**
    `(user_id, item_id, ts)`.
    """)

    C(r'''
    NOW = int(ratings.ts.max()) + 86400
    SCHEMA = None   # TODO: pa.DataFrameSchema({...}, checks=[...], coerce=True)


    def corrupt_batches(df):
        b1 = df.copy(); b1.loc[b1.sample(frac=0.02, random_state=1).index, "rating"] = 10.0
        b2 = df.copy(); b2.loc[b2.sample(frac=0.01, random_state=2).index, "ts"] = NOW + 10**7
        b3 = pd.concat([df, df.head(max(len(df) // 10, 5))])
        return {"rating_x2": b1, "ts_futuro": b2, "duplicados": b3}


    def check_E1(schema):
        cols = ["user_id", "item_id", "rating", "ts"]
        ok_real = all(_valid(schema, ratings[ratings.year == y][cols]) for y in YEARS_PROD)
        bad = corrupt_batches(ratings[ratings.year == YEARS_PROD[0]][cols])
        rejected = {k: not _valid(schema, v) for k, v in bad.items()}
        print(f"E1 · acepta lotes reales: {ok_real} · rechaza corruptos: {rejected}")
        return ok_real and all(rejected.values())


    def _valid(schema, df):
        try:
            schema.validate(df, lazy=True); return True
        except pa.errors.SchemaErrors:
            return False


    if SCHEMA is None:
        print("⏳ E1 pendiente")
    else:
        check_E1(SCHEMA)
    ''')

    M(r"""
    ## Paso 2 · Informe de drift (E2)

    `drift_report(model, batch, ref_batch)` → dict con:
    - `oov`: fracción de interacciones de `batch` sobre ítems fuera del vocabulario del modelo;
    - `js_genre`: Jensen-Shannon entre la distribución de `main_genre` de `ref_batch` y `batch`;
    - `evidently_share`: fracción de columnas de `monitoring_table` con drift según Evidently;
    - `emb_auc`: AUC de un clasificador de dominio sobre vectores de usuario (fold-in) de `ref_batch` vs `batch`.
    """)

    C(r'''
    def drift_report(model: dict, batch: pd.DataFrame, ref_batch: pd.DataFrame) -> dict:
        # TODO
        raise NotImplementedError


    try:
        static = train_als(ratings[ratings.year < T0], **HP)
        print(drift_report(static, ratings[ratings.year == YEARS_PROD[-1]], ratings[ratings.year == T0 - 1]))
    except NotImplementedError:
        print("⏳ E2 pendiente")
    ''')

    M(r"""
    ## Paso 3 · Flow de Prefect con MLflow (E3)

    Implementa las tareas y el flow. Reglas:
    - El servicio carga `models:/cinematch-ct@champion`.
    - En el año `year`, el «último lote» es `year-1`. Si no pasa la validación → no se hace nada (y se registra el motivo).
    - La **línea base** de drift de cada versión es el informe del primer periodo tras desplegarla; guárdala como *tags*
      de la versión en MLflow (`baseline_oov`, `baseline_js`, …) y no reentrenes ese periodo.
    - Si `should_retrain(report, baseline)` → entrenar challenger con ventana de `WINDOW` años hasta `year-2`, evaluar challenger
      y champion en `year-1` (mismo conjunto), registrar el challenger (reentrenado hasta `year-1`) con alias `challenger`
      y promover a `champion` solo si `ndcg_challenger ≥ ndcg_champion`.
    """)

    C(r'''
    WINDOW = 3
    MODEL_NAME = "cinematch-ct"


    def should_retrain(report: dict, baseline: dict) -> bool:
        # TODO: tu política de trigger: umbrales RELATIVOS a la línea base (oov, js_genre, evidently_share, emb_auc)
        raise NotImplementedError


    def ct_pipeline(year: int) -> dict:
        # TODO: flow de Prefect (decorado con @flow) que orqueste las tareas
        raise NotImplementedError
    ''')

    M(r"""
    ## Paso 4 · Simulación de políticas (E4) y paso 5 · simulacro de incidente (E5)

    - `simulate(policy)` para `policy ∈ {"estatico", "anual", "trigger"}` → DataFrame `year, ndcg10, retrained`.
    - Simulacro: registra un challenger **defectuoso** (factores aleatorios) y demuestra que tu puerta de calidad lo
      rechaza; después haz un rollback manual del alias y comprueba que el modelo cargado por `@champion` cambia.

    ---

    # ⛔ SPOILER — intenta resolverlo primero

    Solución de referencia completa a continuación.
    """)

    C(r'''
    SCHEMA = pa.DataFrameSchema(
        {
            "user_id": pa.Column(int, Check.ge(1), nullable=False),
            "item_id": pa.Column(int, Check.ge(1), nullable=False),
            "rating": pa.Column(float, Check.isin(list(np.arange(0.5, 5.01, 0.5))), nullable=False),
            "ts": pa.Column(int, [Check.gt(788_918_400), Check.le(NOW)], nullable=False),
        },
        checks=[Check(lambda d: d.duplicated(["user_id", "item_id", "ts"]).mean() <= 0.01, error="duplicados > 1 %")],
        coerce=True,
    )
    E1 = check_E1(SCHEMA)
    ''')

    C(r'''
    def drift_report(model, batch, ref_batch, max_users=300):
        mt_ref, mt_cur = monitoring_table(ref_batch, model), monitoring_table(batch, model)
        ev = evidently_drift(mt_ref, mt_cur)
        hist = lambda df: [list(g.sort_values("ts").item_id) for _, g in df.groupby("user_id")][:max_users]
        U_ref, U_cur = user_vectors(model, hist(ref_batch))[0], user_vectors(model, hist(batch))[0]
        return {"oov": oov_rate(model, batch), "js_genre": js_div(ref_batch.main_genre, batch.main_genre),
                "evidently_share": float(np.mean([v[0] for v in ev.values()])),
                "emb_auc": domain_classifier_auc(U_ref, U_cur) if min(len(U_ref), len(U_cur)) >= 10 else 0.5}


    static = train_als(ratings[ratings.year < T0], **HP)
    ref_b = ratings[ratings.year == T0 - 1]
    rep = pd.DataFrame([{"year": y, **drift_report(static, ratings[ratings.year == y], ref_b)} for y in YEARS_PROD])
    rep["ndcg10"] = [evaluate(static, y) for y in YEARS_PROD]
    fig, ax = plt.subplots(1, 2, figsize=(14, 4))
    for c in ["oov", "js_genre", "evidently_share", "emb_auc"]:
        ax[0].plot(rep.year, rep[c], "o-", ms=3, label=c)
    ax[0].legend(); ax[0].set_title("E2 · Drift del modelo estático por año")
    ax[1].plot(rep.year, rep.ndcg10, "o-", color="k"); ax[1].set_title("NDCG@10 del modelo estático"); plt.tight_layout(); plt.show()
    display(rep.round(3))
    ''')

    C(r'''
    import mlflow
    from mlflow.tracking import MlflowClient
    from prefect import flow, task
    try:
        from prefect.cache_policies import NO_CACHE
        TK = {"cache_policy": NO_CACHE}
    except ImportError:
        TK = {}

    mlflow.set_tracking_uri("sqlite:///mlflow_ct.db"); mlflow.set_experiment("cinematch-ct")
    client = MlflowClient()


    class ALSPyfunc(mlflow.pyfunc.PythonModel):
        def load_context(self, context):
            z = np.load(context.artifacts["model"]); self.m = {k: z[k] for k in z.files}

        def predict(self, context, model_input, params=None):
            return pd.DataFrame({"recs": [list(map(int, r)) for r in recommend_batch(self.m, list(model_input["history"]))[0]]})


    def register(model, run_name, params, metrics):
        np.savez("model_ct.npz", **{k: model[k] for k in ("items", "Y", "G", "pop")})
        np.save("model_ct_meta.npy", np.array([model["trained_until"]]))
        with mlflow.start_run(run_name=run_name):
            mlflow.log_params(params); mlflow.log_metrics(metrics)
            kw = dict(python_model=ALSPyfunc(), artifacts={"model": "model_ct.npz"}, registered_model_name=MODEL_NAME)
            try:
                mlflow.pyfunc.log_model(name="model", **kw)
            except TypeError:
                mlflow.pyfunc.log_model(artifact_path="model", **kw)
        v = max(int(x.version) for x in client.search_model_versions(f"name='{MODEL_NAME}'"))
        client.set_model_version_tag(MODEL_NAME, str(v), "trained_until", str(model["trained_until"]))
        return v


    def load_champion():
        info = client.get_model_version_by_alias(MODEL_NAME, "champion")
        m = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}@champion").unwrap_python_model().m
        m["trained_until"] = int(info.tags.get("trained_until", 0))
        return m, int(info.version)


    def should_retrain(report, baseline):
        """Deriva 'anormal' = peor que la observada en el primer periodo tras desplegar + margen."""
        return (report["oov"] > baseline["oov"] + 0.05 or report["js_genre"] > baseline["js_genre"] + 0.01
                or report["emb_auc"] > max(baseline["emb_auc"] + 0.10, 0.70))


    @task(**TK)
    def t_ingest(year):
        return ratings[ratings.year == year]


    @task(**TK)
    def t_validate(batch):
        return _valid(SCHEMA, batch[["user_id", "item_id", "rating", "ts"]])


    @task(**TK)
    def t_drift(model, batch):
        ref = ratings[(ratings.ts <= model["trained_until"]) & (ratings.ts > model["trained_until"] - 365 * 86400)]
        return drift_report(model, batch, ref)


    @task(**TK)
    def t_train(until_year):
        return train_als(ratings[(ratings.year < until_year) & (ratings.year >= until_year - WINDOW)], **HP)


    @task(**TK)
    def t_eval(model, year):
        return evaluate(model, year)


    @flow(name="cinematch-ct-pipeline", log_prints=True)
    def ct_pipeline(year: int, force: bool = False, bad_challenger: bool = False) -> dict:
        champ, v_champ = load_champion()
        batch = t_ingest(year - 1)
        if not t_validate(batch):
            return {"year": year, "action": "bloqueado_validacion", "champion": v_champ}
        rep_ = t_drift(champ, batch)
        tags = client.get_model_version(MODEL_NAME, str(v_champ)).tags
        if "baseline_oov" not in tags and not force:          # primer periodo tras desplegar → línea base
            for k in ("oov", "js_genre", "emb_auc"):
                client.set_model_version_tag(MODEL_NAME, str(v_champ), f"baseline_{k}", str(rep_[k]))
            return {"year": year, "action": "linea_base", "champion": v_champ, **rep_}
        baseline = {k: float(tags.get(f"baseline_{k}", rep_[k])) for k in ("oov", "js_genre", "emb_auc")}
        if not (force or should_retrain(rep_, baseline)):
            return {"year": year, "action": "sin_reentreno", "champion": v_champ, **rep_}
        cand = t_train(year - 1)
        if bad_challenger:                                   # simulacro: bug que corrompe los factores
            cand["Y"] = np.random.default_rng(0).normal(0, 1, cand["Y"].shape).astype(np.float32)
        nd_ch, nd_cp = t_eval(cand, year - 1), t_eval(champ, year - 1)
        serve = cand if bad_challenger else t_train(year)
        v = register(serve, f"challenger-{year}", {**HP, "window": WINDOW, "year": year},
                     {"ndcg_val_challenger": nd_ch, "ndcg_val_champion": nd_cp, **rep_})
        client.set_registered_model_alias(MODEL_NAME, "challenger", v)
        promoted = nd_ch >= nd_cp
        if promoted:
            client.set_registered_model_alias(MODEL_NAME, "champion", v)
        print(f"{year}: challenger v{v} {nd_ch:.4f} vs champion v{v_champ} {nd_cp:.4f} → {'PROMOVIDO' if promoted else 'RECHAZADO'}")
        return {"year": year, "action": "promovido" if promoted else "rechazado", "champion": v if promoted else v_champ,
                "challenger": v, **rep_}
    ''')

    C(r'''
    # Estado inicial: champion entrenado hasta T0-1
    v_init = register(train_als(ratings[ratings.year < T0], **HP), f"init-{T0}", {**HP, "year": T0}, {})
    client.set_registered_model_alias(MODEL_NAME, "champion", v_init)


    def run_flow(**kw):
        try:
            return ct_pipeline(**kw)
        except Exception as e:     # Prefect sin servidor temporal → misma lógica sin orquestador
            print("⚠️ Prefect no disponible:", repr(e)[:150]); return ct_pipeline.fn(**kw)


    flow_log = []
    for y in YEARS_PROD[1:]:
        out = run_flow(year=y)
        champ, _ = load_champion()
        out["ndcg10"] = evaluate(champ, y)                   # lo que el champion consigue sirviendo el año y
        flow_log.append(out)
    trig = pd.DataFrame(flow_log)
    display(trig[["year", "action", "champion", "oov", "js_genre", "emb_auc", "ndcg10"]].round(3))
    E3 = trig.action.isin(["promovido", "rechazado"]).any() and len(client.search_model_versions(f"name='{MODEL_NAME}'")) > 1
    print("E3 ·", "✅" if E3 else "❌", "| aliases:", client.get_registered_model(MODEL_NAME).aliases)
    ''')

    C(r'''
    def simulate(policy):
        model = train_als(ratings[ratings.year < T0], **HP); rows = []
        for y in YEARS_PROD:
            re = False
            if y != YEARS_PROD[0] and policy == "anual":
                model, re = train_als(ratings[(ratings.year < y) & (ratings.year >= y - WINDOW)], **HP), True
            rows.append({"policy": policy, "year": y, "ndcg10": evaluate(model, y), "retrained": re})
        return pd.DataFrame(rows)


    res = pd.concat([simulate("estatico"), simulate("anual"),
                     pd.DataFrame({"policy": "trigger", "year": [YEARS_PROD[0]] + list(trig.year),
                                   "ndcg10": [evaluate(train_als(ratings[ratings.year < T0], **HP), YEARS_PROD[0])] + list(trig.ndcg10),
                                   "retrained": [False] + list(trig.action.isin(["promovido", "rechazado"]))})])
    summary = res.groupby("policy").agg(ndcg10=("ndcg10", "mean"), reentrenos=("retrained", "sum"))
    display(summary)
    ratio_q = summary.loc["trigger", "ndcg10"] / summary.loc["anual", "ndcg10"]
    ratio_c = summary.loc["trigger", "reentrenos"] / max(summary.loc["anual", "reentrenos"], 1)
    print(f"E4 · calidad trigger/anual = {ratio_q:.3f} (≥ 0,95) · reentrenos trigger/anual = {ratio_c:.2f} (≤ 0,70) →",
          "✅" if ratio_q >= 0.95 and ratio_c <= 0.70 else "⚠️ ajusta umbrales de should_retrain")
    fig, ax = plt.subplots(figsize=(11, 4))
    for p, g in res.groupby("policy"):
        ax.plot(g.year, g.ndcg10.rolling(2, min_periods=1).mean(), "o-", ms=3, label=p)
        rr = g[g.retrained & (p == "trigger")]
        ax.scatter(rr.year, g.ndcg10.rolling(2, min_periods=1).mean()[g.retrained & (p == "trigger")], marker="v", s=60, color="r", zorder=4)
    ax.set_title("E4 · NDCG@10 en el tiempo: estático vs anual vs trigger (▼ reentreno)"); ax.set_xlabel("año"); ax.legend(); plt.show()
    ''')

    C(r'''
    # E5 · Simulacro de incidente
    champ_before = client.get_model_version_by_alias(MODEL_NAME, "champion").version
    drill = run_flow(year=YEARS_PROD[-1], force=True, bad_challenger=True)
    rejected = drill["action"] == "rechazado" and client.get_model_version_by_alias(MODEL_NAME, "champion").version == champ_before

    # Rollback manual: volvemos a la versión anterior del champion y comprobamos que el modelo servido cambia
    versions = sorted(int(v.version) for v in client.search_model_versions(f"name='{MODEL_NAME}'"))
    prev = [v for v in versions if v < int(champ_before) and v != drill["challenger"]]
    t = time.perf_counter()
    client.set_registered_model_alias(MODEL_NAME, "champion", prev[-1] if prev else versions[0])
    m_after, v_after = load_champion()
    rb_ms = 1e3 * (time.perf_counter() - t)
    E5 = rejected and str(v_after) != str(champ_before)
    print(f"E5 · challenger defectuoso rechazado: {rejected} · rollback v{champ_before} → v{v_after} en {rb_ms:.0f} ms →", "✅" if E5 else "❌")
    client.set_registered_model_alias(MODEL_NAME, "champion", champ_before)      # restauramos
    ''')

    M(r"""
    ## 🚀 Retos extra

    1. Sustituye el ALS por el two-tower del módulo 08 con *warm start* desde el checkpoint del champion.
    2. Añade un **shadow deploy**: en el flow, antes de promover, sirve el challenger en paralelo al servicio del proyecto 16 y compara distribuciones de score (prediction drift entre modelos).
    3. Exporta las métricas del flow a Prometheus (*pushgateway*) y crea la alerta «OOV > 15 % durante 2 periodos» en `reference_stack/prometheus/alerts.yml`.
    4. Despliega el flow con `prefect deploy` y un *schedule* cron, o tradúcelo a Airflow (`reference_stack/airflow/`) / Metaflow.
    5. Calibra los umbrales de `should_retrain` con una búsqueda en rejilla optimizando `NDCG − λ·reentrenos` (¡en años de validación, no de test!).
    6. Implementa **reentreno incremental diario + completo semanal** con datos de ML-25M a nivel de semana.

    ## 🤔 Reflexión

    - ¿Qué parte de tu política depende de etiquetas (y por tanto llega tarde) y cuál no?
    - Si el challenger gana offline pero pierde en canary, ¿qué hipótesis investigarías primero?
    - ¿Cómo evitarías que el feedback loop haga que cada nuevo modelo «gane» al anterior solo porque se entrena con datos generados por él?
    - ¿Qué versionarías junto al modelo para poder reproducir exactamente el champion de hace 6 meses?
    """)

    nb.save(path)


if __name__ == "__main__":
    lesson()
    project()
