"""Builder del módulo 03 · Recomendación basada en contenido.

Ejecutar desde la raíz del repo:  python recsys-course/_tools/builders/build_03.py
"""
import sys
from pathlib import Path

sys.path.insert(0, "recsys-course/_tools")
sys.path.insert(0, "recsys-course/_tools/builders")
from nbbuild import Notebook  # noqa: E402
from bloque2_common import add_utils  # noqa: E402

MOD = "recsys-course/03_content_based"
Path(MOD).mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Celdas de código compartidas por lección y proyecto
# ---------------------------------------------------------------------------
METADATA_CODE = r'''
# Metadatos de películas: sinopsis + URL de póster, con cadena de fallbacks
import csv, json, subprocess

M3L_COMMIT = "b11f814041f316684457e43a38cc2a9fd3e9d4eb"  # commit fijado → reproducible
M3L_BASE = f"https://raw.githubusercontent.com/giuspillo/M3L_10M_20M/{M3L_COMMIT}/1_download_raw"


def _from_m3l(d: Path) -> pd.DataFrame:
    """M³L (Spillo et al., 2026): sinopsis TMDB + URL de póster, indexadas por movieId de MovieLens."""
    files = {"REPRO_plot_text.tsv": "download_text", "REPRO_poster_links.tsv": "download_posters"}
    for f, sub in files.items():
        if not (d / f).exists():
            urllib.request.urlretrieve(f"{M3L_BASE}/{sub}/{f}", d / f)
    plots = pd.read_csv(d / "REPRO_plot_text.tsv", sep="\t", quoting=csv.QUOTE_NONE)
    posters = pd.read_csv(d / "REPRO_poster_links.tsv", sep="\t")
    plots = plots.rename(columns={"movie_id": "item_id", "plot": "overview"})
    posters = posters.rename(columns={"movie_id": "item_id", "poster_link": "poster_url"})
    return plots.merge(posters, on="item_id", how="outer")


def _from_kaggle(d: Path) -> pd.DataFrame:
    """Fallback: Kaggle «The Movies Dataset» (requiere ~/.kaggle/kaggle.json)."""
    subprocess.run(["kaggle", "datasets", "download", "-d", "rounakbanik/the-movies-dataset",
                    "-f", "movies_metadata.csv", "-p", str(d), "--unzip"], check=True)
    subprocess.run(["kaggle", "datasets", "download", "-d", "rounakbanik/the-movies-dataset",
                    "-f", "links.csv", "-p", str(d), "--unzip"], check=True)
    meta = pd.read_csv(d / "movies_metadata.csv", low_memory=False)
    meta["tmdbId"] = pd.to_numeric(meta["id"], errors="coerce")
    links = pd.read_csv(d / "links.csv").rename(columns={"movieId": "item_id"})
    out = links.merge(meta[["tmdbId", "overview", "poster_path"]], on="tmdbId", how="left")
    out["poster_url"] = "https://image.tmdb.org/t/p/original" + out["poster_path"].astype(str)
    out.loc[out.poster_path.isna(), "poster_url"] = np.nan
    return out[["item_id", "overview", "poster_url"]]


def load_movie_metadata(movies: pd.DataFrame, data_dir: Path = DATA_DIR) -> pd.DataFrame:
    d = Path(data_dir) / "metadata"
    d.mkdir(parents=True, exist_ok=True)
    meta, source = None, "solo título+géneros (fallback sintético)"
    for name, fn in [("M³L / TMDB (GitHub)", _from_m3l), ("Kaggle The Movies Dataset", _from_kaggle)]:
        try:
            meta, source = fn(d), name
            break
        except Exception as e:
            print(f"⚠️ {name} no disponible: {e.__class__.__name__}")
    out = movies.copy()
    if meta is not None:
        out = out.merge(meta.drop_duplicates("item_id"), on="item_id", how="left")
    for c in ("overview", "poster_url"):
        if c not in out:
            out[c] = np.nan
    out["overview"] = out["overview"].fillna("")
    # Texto del ítem = título + géneros + sinopsis (lo que verá el encoder)
    out["text"] = (out["title"] + ". Genres: " + out["genres"].apply(", ".join) + ". " + out["overview"]).str.strip()
    print(f"Fuente de metadatos: {source} · sinopsis {np.mean(out.overview.str.len() > 0):.1%} · "
          f"pósters {out.poster_url.notna().mean():.1%}")
    return out
'''

CONTENT_FNS = r'''
# Recomendador basado en contenido: perfil de usuario = media ponderada de vectores de ítem
from sklearn.preprocessing import normalize


def user_weights(R: sp.csr_matrix, scheme: str = "centered") -> sp.csr_matrix:
    """Pesos w_ui del perfil. 'binary': 1 · 'liked': rating≥4 · 'centered': r_ui − media_u (Rocchio)."""
    W = R.copy().astype(np.float32).tocsr()
    if scheme == "binary":
        W.data[:] = 1.0
    elif scheme == "liked":
        W.data = (W.data >= 4).astype(np.float32)
    elif scheme == "centered":
        counts = np.diff(W.indptr)
        means = np.asarray(W.sum(1)).ravel() / np.maximum(counts, 1)
        W.data -= np.repeat(means, counts)
    return W


def content_score_fn(W: sp.csr_matrix, F):
    """score(u, i) = <perfil_u, x_i> con perfil_u = Σ_j w_uj x_j  (F: n_items × d, filas L2-normalizadas)."""
    def score(ub):
        S = (W[ub] @ F) @ F.T
        return S.toarray() if sp.issparse(S) else np.asarray(S)
    return score


def zrow(S: np.ndarray) -> np.ndarray:
    """Estandariza cada fila (para mezclar puntuaciones de escalas distintas)."""
    return (S - S.mean(1, keepdims=True)) / (S.std(1, keepdims=True) + 1e-9)
'''

EMBED_CODE = r'''
# Embeddings densos de texto con sentence-transformers (fallback: LSA = TF-IDF + SVD truncada)
from sklearn.decomposition import TruncatedSVD

TEXT_MODELS = {  # nombre corto → (modelo en HF Hub, prefijo recomendado por sus autores)
    "bge-small": ("BAAI/bge-small-en-v1.5", ""),
    "e5-base": ("intfloat/e5-base-v2", "query: "),   # E5 exige prefijo; 'query: ' para tareas simétricas
    "gte-base": ("thenlper/gte-base", ""),
}


def embed_texts(texts, model_key: str, cache_dir: Path = DATA_DIR / "emb") -> np.ndarray:
    cache_dir.mkdir(parents=True, exist_ok=True)
    f = cache_dir / f"{model_key}.npy"
    if f.exists():
        return np.load(f)
    name, prefix = TEXT_MODELS[model_key]
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(name, device=device)
        E = model.encode([prefix + t for t in texts], batch_size=128, normalize_embeddings=True,
                         show_progress_bar=True, convert_to_numpy=True)
    except Exception as e:
        print(f"⚠️ No se pudo cargar {name} ({e.__class__.__name__}); uso LSA como fallback.")
        from sklearn.feature_extraction.text import TfidfVectorizer
        T = TfidfVectorizer(stop_words="english", min_df=2, sublinear_tf=True).fit_transform(texts)
        E = normalize(TruncatedSVD(256, random_state=seed).fit_transform(T))
        f = cache_dir / "lsa_fallback.npy"   # nunca cacheamos el fallback con el nombre del modelo
    E = E.astype(np.float32)
    np.save(f, E)
    return E
'''

POSTER_CODE = r'''
# Descarga paralela de pósters (TMDB sirve tamaños w92…w780; w185 basta para CLIP a 224 px)
from concurrent.futures import ThreadPoolExecutor
from PIL import Image


def download_posters(df: pd.DataFrame, out_dir: Path = DATA_DIR / "posters", size: str = "w185",
                     workers: int = 16) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)

    def fetch(item_id, url):
        path = out_dir / f"{item_id}.jpg"
        if path.exists() and path.stat().st_size > 0:
            return item_id, path
        try:
            req = urllib.request.Request(url.replace("/original/", f"/{size}/"),
                                         headers={"User-Agent": "Mozilla/5.0 (CineMatch course)"})
            path.write_bytes(urllib.request.urlopen(req, timeout=20).read())
            Image.open(path).verify()
            return item_id, path
        except Exception:
            path.unlink(missing_ok=True)
            return item_id, None

    rows = df.dropna(subset=["poster_url"])
    with ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(lambda r: fetch(r[0], r[1]), zip(rows.item_id, rows.poster_url)))
    return {i: p for i, p in res if p is not None}
'''

CLIP_CODE = r'''
# CLIP (open_clip): imágenes y textos en el MISMO espacio vectorial
CLIP_ARCH, CLIP_WEIGHTS = "ViT-B-32", "laion2b_s34b_b79k"


def load_clip():
    import open_clip
    model, _, preprocess = open_clip.create_model_and_transforms(CLIP_ARCH, pretrained=CLIP_WEIGHTS)
    return model.to(device).eval(), preprocess, open_clip.get_tokenizer(CLIP_ARCH)


@torch.no_grad()
def clip_encode_images(paths, model, preprocess, batch: int = 128) -> np.ndarray:
    out = []
    for s in range(0, len(paths), batch):
        ims = torch.stack([preprocess(Image.open(p).convert("RGB")) for p in paths[s : s + batch]])
        out.append(model.encode_image(ims.to(device)).float().cpu().numpy())
    return normalize(np.vstack(out)).astype(np.float32)


@torch.no_grad()
def clip_encode_texts(texts, model, tokenizer) -> np.ndarray:
    emb = model.encode_text(tokenizer(texts).to(device)).float().cpu().numpy()
    return normalize(emb).astype(np.float32)
'''

# ---------------------------------------------------------------------------
# LECCIÓN
# ---------------------------------------------------------------------------
LESSON = f"{MOD}/03_content_based.ipynb"
nb = Notebook("Módulo 03 · Recomendación basada en contenido", colab_path=LESSON, gpu=True)

nb.md(f"""
{nb.badge()}

# Módulo 03 · Recomendación basada en contenido
### De TF-IDF a embeddings de texto (BGE/E5/GTE) y CLIP para pósters

| | |
|---|---|
| **Nivel** | 🟢 Básico → 🟡 Intermedio |
| **Duración estimada** | 3–4 h |
| **GPU recomendada** | T4 (embeddings + CLIP). Funciona en CPU, más lento |
| **Unidades de Colab** | ≈ 1–2 (T4) con `FAST_DEV_RUN=False` |
| **Prerrequisitos** | [00_intro](../00_intro), [01_data](../01_data), [02_evaluation](../02_evaluation) |

> Bloque II — Métodos clásicos. Es el primer módulo donde construimos recomendadores
> **personalizados**. Empezamos por el más intuitivo: «si te gustó *Alien*, te gustará
> otra película *parecida a Alien*».
""")

nb.md("""
## 🎯 Objetivos de aprendizaje

Al terminar este módulo serás capaz de:

1. **Explicar** qué es un recomendador basado en contenido, qué problema resuelve (cold start de ítems) y cuándo **no** usarlo (sobre-especialización, ignora la calidad).
2. **Construir** perfiles de ítem con TF-IDF y BM25 **desde cero** y verificarlos contra scikit-learn.
3. **Construir** perfiles de usuario (Rocchio / media ponderada centrada) y **evaluarlos** con NDCG@10, Recall@10 y coverage en un split temporal.
4. **Generar** embeddings semánticos con modelos modernos (BGE, E5, GTE) y **comparar** su calidad con TF-IDF.
5. **Usar** CLIP (open_clip) para representar **pósters** y hacer búsqueda multimodal texto→imagen.
6. **Diseñar** un híbrido simple (fusión de modalidades + prior de popularidad) y **medir** su efecto.
7. **Cuantificar** la ventaja del contenido en **cold start de ítems** frente a no tener nada.
""")

nb.md("""
## ⚙️ Setup

Instalamos lo que Colab no trae: `open_clip_torch` (CLIP) y `umap-learn`.
`sentence-transformers`, `torch`, `scikit-learn` y `matplotlib` ya vienen en Colab.
""")
nb.code("""
!pip install -q open_clip_torch sentence-transformers umap-learn pyarrow
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

# FAST_DEV_RUN=True → modelos pequeños y subconjunto de pósters (minutos en CPU)
FAST_DEV_RUN = True
N_POSTERS = 400 if FAST_DEV_RUN else 4000
TEXT_MODEL_KEYS = ["bge-small"] if FAST_DEV_RUN else ["bge-small", "e5-base", "gte-base"]
print("device:", device, "| FAST_DEV_RUN:", FAST_DEV_RUN)
''')

add_utils(nb)

# ---------------- Intuición ----------------
nb.md("""
## 💡 1. Intuición: recomendar por parecido

Imagina el videoclub de tu barrio. Le dices al dependiente: *«me encantaron Alien y Blade
Runner»*. Sin saber nada de otros clientes, te da *Terminator*: **ciencia ficción oscura de los
80**. Eso es un recomendador **basado en contenido** (*content-based filtering*):

1. Describimos cada ítem con **features** (género, sinopsis, reparto, póster…) → un vector $\\mathbf{x}_i$.
2. Describimos al usuario con un **perfil** en el *mismo espacio*: la media de los vectores de lo que le gustó.
3. Recomendamos los ítems cuyo vector se parece más al perfil (similitud coseno).

**Analogía con lo que ya sabes**: es un *buscador* (retrieval) donde la «consulta» es tu
historial. O, si lo prefieres, un **kNN en el espacio de features** — nada de aprender de
otros usuarios. Esa es su gran virtud y su gran defecto:

| ✅ Ventajas | ❌ Inconvenientes |
|---|---|
| Recomienda ítems **nuevos** sin una sola interacción (cold start de ítems) | No sabe de **calidad**: una mala película de robots se parece mucho a una buena |
| **Explicable** («porque viste películas de ciencia ficción con IA») | **Sobre-especialización**: te encierra en lo que ya conoces (poca serendipia) |
| No necesita otros usuarios (privacidad, catálogos pequeños) | Las features deben existir y ser buenas (*garbage in, garbage out*) |
| Escala trivialmente (1 vector por ítem) | No resuelve el cold start de **usuarios** (sin historial no hay perfil) |
""")
nb.code(r'''
# Diagrama: el pipeline de un recomendador basado en contenido
fig, ax = plt.subplots(figsize=(12, 4.2)); ax.axis("off"); ax.set_xlim(0, 12); ax.set_ylim(0, 4.2)
def box(x, y, w, h, txt, c):
    ax.add_patch(mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08", fc=c, ec="k", lw=1.2))
    ax.text(x + w / 2, y + h / 2, txt, ha="center", va="center", fontsize=9.5)
def arrow(x1, y1, x2, y2, t=""):
    ax.annotate("", (x2, y2), (x1, y1), arrowprops=dict(arrowstyle="->", lw=1.6))
    if t: ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.18, t, ha="center", fontsize=8.5, style="italic")
box(0.1, 2.6, 2.2, 1.2, "Metadatos\nsinopsis · géneros\npóster · año", "#fde2c8")
box(3.2, 2.6, 2.3, 1.2, "Vectores de ítem $x_i$\nTF-IDF · BM25\nBGE/E5 · CLIP", "#cfe8ff")
box(0.1, 0.3, 2.2, 1.2, "Historial del usuario\n(ratings en train)", "#e2f0d9")
box(3.2, 0.3, 2.3, 1.2, "Perfil $p_u=\\sum_j w_{uj}\\,x_j$\n(Rocchio)", "#e2f0d9")
box(6.6, 1.45, 2.3, 1.2, "Scoring\n$s(u,i)=\\cos(p_u, x_i)$", "#f4d7f4")
box(9.8, 1.45, 2.0, 1.2, "Top-K\n(excluye vistos)", "#fff2a8")
arrow(2.35, 3.2, 3.15, 3.2, "encoder"); arrow(2.35, 0.9, 3.15, 0.9, "pesos $w_{uj}$")
arrow(4.35, 2.55, 4.35, 1.55, ""); arrow(5.55, 3.2, 6.6, 2.35); arrow(5.55, 0.9, 6.6, 1.75)
arrow(8.95, 2.05, 9.75, 2.05)
ax.set_title("Recomendación basada en contenido: ítems → vectores → perfil → similitud", fontsize=12)
plt.show()
''')

nb.md("""
### 🧪 Ejemplo en papel: 6 películas, 1 usuario

Antes de tocar MovieLens, hagamos el cálculo a mano con 6 «sinopsis» de juguete. Así verás
cada número antes de verlo a escala.
""")
nb.code(r'''
toy_docs = {
    "Alien":        "space alien crew ship horror",
    "Blade Runner": "future android detective city noir",
    "Terminator":   "future android killer war",
    "Toy Story":    "toys friendship kids adventure",
    "Shrek":        "ogre princess kids adventure comedy",
    "Love Actually":"love christmas london comedy",
}
titles = list(toy_docs)
vocab = sorted({w for d in toy_docs.values() for w in d.split()})
tf = np.array([[d.split().count(w) for w in vocab] for d in toy_docs.values()], dtype=float)  # 6 × |V|
df_ = (tf > 0).sum(0)                              # nº de docs que contienen cada término
idf = np.log((1 + len(titles)) / (1 + df_)) + 1    # idf «suavizado» (el de scikit-learn)
X_toy = tf * idf
X_toy /= np.linalg.norm(X_toy, axis=1, keepdims=True)
S_toy = X_toy @ X_toy.T                            # coseno = producto escalar de vectores unitarios
print("Vocabulario:", len(vocab), "términos; idf de 'future' =", idf[vocab.index("future")].round(3),
      "| idf de 'ogre' =", idf[vocab.index("ogre")].round(3))
''')
nb.code(r'''
fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
im = axes[0].imshow(S_toy, cmap="viridis", vmin=0, vmax=1)
axes[0].set_xticks(range(6), titles, rotation=40, ha="right"); axes[0].set_yticks(range(6), titles)
for i in range(6):
    for j in range(6):
        axes[0].text(j, i, f"{S_toy[i, j]:.2f}", ha="center", va="center", color="w" if S_toy[i, j] < .6 else "k", fontsize=8)
axes[0].set_title("Similitud coseno TF-IDF entre películas"); axes[0].grid(False)
plt.colorbar(im, ax=axes[0], fraction=0.046)

# Usuario: le encantó Alien (5★) y Blade Runner (4★), odió Love Actually (1★). Media = 3.33
r = {"Alien": 5, "Blade Runner": 4, "Love Actually": 1}
mu = np.mean(list(r.values()))
profile = sum((v - mu) * X_toy[titles.index(t)] for t, v in r.items())   # Rocchio centrado
scores = X_toy @ profile
cands = [t for t in titles if t not in r]
axes[1].barh(cands, [scores[titles.index(t)] for t in cands], color=["#d62728", "#1f77b4", "#1f77b4"])
axes[1].axvline(0, color="k", lw=0.8); axes[1].set_xlabel("score = ⟨perfil, x_i⟩")
axes[1].set_title("Scores para candidatos no vistos (perfil centrado)")
plt.tight_layout(); plt.show()
''')
nb.md("""
Observa dos cosas:

- *Terminator* sale primero porque comparte «future android» con *Blade Runner*.
- *Shrek* puntúa **negativo**: comparte «comedy» con *Love Actually*, que el usuario odió. Al
  **centrar** los ratings ($r_{ui}-\\bar r_u$), lo que no te gustó **resta**. Con pesos binarios
  («todo lo que he visto suma») eso se perdería.
""")

# ---------------- Teoría ----------------
nb.md(r"""
## 📐 2. Teoría formal

### 2.1 TF-IDF
Para un término $t$ y un documento (sinopsis) $d$:

$$\text{tfidf}(t,d) = \underbrace{\text{tf}(t,d)}_{\text{frecuencia en } d}\cdot \underbrace{\left(\ln\frac{1+N}{1+\text{df}(t)} + 1\right)}_{\text{idf: rareza en el corpus}}$$

- $N$: nº de documentos; $\text{df}(t)$: nº de documentos que contienen $t$.
- Con `sublinear_tf=True` se usa $1+\ln \text{tf}$ (que «android» aparezca 10 veces no es 10× más informativo).
- Cada vector se normaliza a norma L2 = 1, así que **coseno = producto escalar**.

### 2.2 BM25 (Robertson & Zaragoza, 2009)
BM25 es el TF-IDF «bien hecho» de los buscadores (Lucene/Elasticsearch lo usan por defecto):

$$\text{BM25}(q,d)=\sum_{t\in q}\text{idf}(t)\cdot\frac{\text{tf}(t,d)\,(k_1+1)}{\text{tf}(t,d)+k_1\left(1-b+b\,\frac{|d|}{\overline{|d|}}\right)}$$

- $k_1\in[1.2, 2]$: **saturación** del tf (a partir de cierto punto, repetir un término no suma).
- $b\in[0,1]$: **normalización por longitud** (sinopsis largas no ganan por tener más palabras).
- $\text{idf}(t)=\ln\left(1+\frac{N-\text{df}(t)+0.5}{\text{df}(t)+0.5}\right)$.

### 2.3 Perfil de usuario (Rocchio) y scoring
Con $I_u$ los ítems valorados por $u$ en train y $\mathbf{x}_j$ los vectores de ítem:

$$\mathbf{p}_u=\sum_{j\in I_u} w_{uj}\,\mathbf{x}_j,\qquad w_{uj}=r_{uj}-\bar r_u,\qquad s(u,i)=\langle \mathbf{p}_u,\mathbf{x}_i\rangle$$

No hace falta dividir por $\sum|w_{uj}|$: el ranking **de cada usuario** es invariante a escalar su perfil.
En forma matricial (lo que implementaremos): $\mathbf{S} = (\mathbf{W}\mathbf{F})\,\mathbf{F}^\top$ con
$\mathbf{W}\in\mathbb{R}^{|U|\times|I|}$ disperso y $\mathbf{F}\in\mathbb{R}^{|I|\times d}$.

### 2.4 Embeddings densos (*bi-encoders*)
Un modelo tipo BGE/E5/GTE es un Transformer $f_\theta$ entrenado con **aprendizaje contrastivo**
(InfoNCE) sobre millones de pares (pregunta, respuesta), (título, cuerpo)…:

$$\mathcal{L}=-\log\frac{\exp(\cos(f_\theta(a),f_\theta(b^+))/\tau)}{\sum_{b\in\mathcal{B}}\exp(\cos(f_\theta(a),f_\theta(b))/\tau)}$$

Es *exactamente* el mismo truco de *in-batch negatives* que veremos en el two-tower (módulo 08).
Ventaja frente a TF-IDF: «android» y «robot» quedan cerca aunque no compartan palabra.

### 2.5 CLIP (Radford et al., 2021)
Dos encoders (imagen y texto) entrenados con la misma InfoNCE sobre pares (imagen, pie de foto).
Resultado: **un espacio compartido** donde el póster de *Alien* está cerca del texto «a sci-fi horror
movie». Nos permite (a) similitud póster↔póster, (b) búsqueda texto→póster, (c) una modalidad
extra para el híbrido.

### 2.6 Fusión (híbridos simples)
- **Early fusion**: concatenar vectores normalizados con pesos $\sqrt{\alpha_m}$ → el coseno resultante es $\sum_m \alpha_m\cos_m$.
- **Late fusion**: mezclar puntuaciones estandarizadas, p. ej. $s=z(s_{\text{contenido}})+\beta\,z(\log \text{pop}_i)$.
""")

# ---------------- Datos ----------------
nb.md("""
## 📦 3. Datos: MovieLens 1M + sinopsis y pósters

- **Interacciones**: MovieLens 1M (6 040 usuarios, 3 706 películas valoradas, 1 M ratings, 2000–2003).
- **Metadatos**: MovieLens solo trae título y géneros. Para sinopsis y pósters usamos
  **M³L** (Spillo et al., 2026, *Binge Watch*, [arXiv:2602.15505](https://arxiv.org/abs/2602.15505);
  [GitHub](https://github.com/giuspillo/M3L_10M_20M)), que publica la sinopsis de TMDB y la URL del
  póster para cada `movieId` de MovieLens. Los IDs de MovieLens son estables entre versiones, así
  que sirven para ML-1M (≈ 97 % de cobertura).
- **Fallbacks**: (1) Kaggle *The Movies Dataset* (`rounakbanik/the-movies-dataset`, requiere
  `~/.kaggle/kaggle.json`: en Kaggle → *Settings → Create New Token* y súbelo a Colab);
  (2) si nada responde, texto = título + géneros, para que el notebook nunca se bloquee.

⚠️ Licencia: datos derivados de MovieLens → **solo investigación/educación**, sin uso comercial.
""")
nb.code(METADATA_CODE)
nb.code(r'''
ratings, movies, users = load_movielens_1m()
movies = load_movie_metadata(movies)
print(ratings.shape, movies.shape)
movies[["item_id", "title", "genres", "overview"]].head(4)
''')
nb.code(r'''
# EDA de metadatos: longitud de sinopsis y distribución de géneros
fig, axes = plt.subplots(1, 2, figsize=(13, 4))
lens = movies.overview.str.split().str.len()
axes[0].hist(lens[lens > 0], bins=40, color="#4c72b0")
axes[0].set_title("Longitud de la sinopsis (palabras)"); axes[0].set_xlabel("palabras"); axes[0].set_ylabel("películas")
g = movies.explode("genres").genres.value_counts()
axes[1].barh(g.index[::-1], g.values[::-1], color="#55a868")
axes[1].set_title("Películas por género (multi-etiqueta)"); axes[1].set_xlabel("nº de películas")
plt.tight_layout(); plt.show()
''')

nb.md("""
### Split temporal y matrices

Usamos el split temporal global de las utilidades. El codificador se ajusta **solo con train**.
La matriz `R` guarda el rating (para el perfil centrado); `X` es binaria (para excluir vistos).
Los vectores de ítem se indexan con `movies`, así que necesitamos mapear `enc.items` → filas.
""")
nb.code(r'''
train, test = temporal_split(ratings, test_frac=0.2)
enc = Encoder(train)
tr, te = enc.transform(train), enc.transform(test)
X = enc.csr(tr)                         # binaria: «visto» (para excluir de las recomendaciones)
R = enc.csr(tr, tr.rating.values)       # ratings explícitos (para los pesos del perfil)
rel = test_relevance(te)                # relevantes = rating ≥ 4 en test
row_of = pd.Series(np.arange(len(movies)), index=movies.item_id)
idx = row_of.loc[enc.items].values      # fila de `movies` para cada iidx
print(f"train {len(tr):,} · test {len(te):,} · usuarios evaluados {len(rel):,} · ítems {enc.n_items:,}")
print("Corte temporal:", pd.to_datetime(train.timestamp.max(), unit="s"))

pop = np.asarray(X.sum(0)).ravel().astype(np.float32)
results = {"Popularidad": evaluate_topk(lambda ub: np.tile(pop, (len(ub), 1)), X, rel)}
results["Popularidad"]
''')
nb.md("""
⚠️ Fíjate en el baseline de popularidad: en un split temporal **honesto** es durísimo de batir
(los usuarios activos tras el corte ven sobre todo lo popular del momento). Ahora sabremos si el
contenido aporta algo.
""")

# ---------------- TF-IDF desde cero ----------------
nb.md("""
## 🔨 4. Implementación desde cero: TF-IDF y BM25

Tokenizamos con `CountVectorizer` (eso no es lo interesante) y calculamos **nosotros** idf,
tf sublineal y normalización. Después comprobamos que coincide con `TfidfVectorizer`.
""")
nb.code(r'''
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.preprocessing import normalize


def tfidf_from_scratch(counts: sp.csr_matrix, sublinear: bool = True) -> sp.csr_matrix:
    N = counts.shape[0]
    dfreq = np.bincount(counts.indices, minlength=counts.shape[1])     # docs que contienen t
    idf = np.log((1 + N) / (1 + dfreq)) + 1
    T = counts.astype(np.float64).tocsr(copy=True)
    if sublinear:
        T.data = 1 + np.log(T.data)
    T = T @ sp.diags(idf)
    return normalize(T)                                                # L2 por fila


cv = CountVectorizer(stop_words="english", min_df=2)
C_all = cv.fit_transform(movies.text)
T_ours = tfidf_from_scratch(C_all)
T_skl = TfidfVectorizer(stop_words="english", min_df=2, sublinear_tf=True).fit_transform(movies.text)
print("vocabulario:", C_all.shape[1], "| máx. diferencia vs scikit-learn:", abs(T_ours - T_skl).max())
''')
nb.code(r'''
def bm25_matrix(counts: sp.csr_matrix, k1: float = 1.5, b: float = 0.75) -> sp.csr_matrix:
    """Pesos BM25 por (doc, término): idf · tf(k1+1) / (tf + k1(1-b+b|d|/avg|d|))."""
    C = counts.astype(np.float64).tocsr(copy=True)
    N = C.shape[0]
    dfreq = np.bincount(C.indices, minlength=C.shape[1])
    idf = np.log(1 + (N - dfreq + 0.5) / (dfreq + 0.5))
    dl = np.asarray(C.sum(1)).ravel()
    denom_doc = k1 * (1 - b + b * dl / dl.mean())                       # depende solo del doc
    rows = np.repeat(np.arange(N), np.diff(C.indptr))
    C.data = C.data * (k1 + 1) / (C.data + denom_doc[rows]) * idf[C.indices]
    return C


B_all = bm25_matrix(C_all)
Q_all = (C_all > 0).astype(np.float64)        # la «consulta» es el conjunto de términos del ítem


def more_like_this(item_id: int, F, k: int = 6, sim_fn=None):
    i = row_of[item_id]
    s = sim_fn(i) if sim_fn else np.asarray((F[i] @ F.T).todense() if sp.issparse(F) else F[i] @ F.T).ravel()
    s[i] = -np.inf
    top = np.argsort(-s)[:k]
    return movies.title.values[top].tolist()


bm25_sim = lambda i: np.asarray((Q_all[i] @ B_all.T).todense()).ravel()
for mid in [1, 260, 593]:   # Toy Story, Star Wars, The Silence of the Lambs
    print(f"\n🎬 {movies.title[row_of[mid]]}")
    print("  TF-IDF:", more_like_this(mid, T_ours, 5))
    print("  BM25  :", more_like_this(mid, None, 5, sim_fn=bm25_sim))
''')
nb.md("""
💡 TF-IDF y BM25 encuentran **secuelas y franquicias** (comparten nombres propios: Woody, Buzz,
Luke, Vader…). Es lo que mejor sabe hacer el *matching léxico*. Pero no sabe que «robot» y
«android» son lo mismo: para eso están los embeddings.

### 4.1 Perfiles de usuario y evaluación

Evaluamos tres representaciones (géneros one-hot, TF-IDF, BM25 normalizado) × tres esquemas de
pesos del perfil.
""")
nb.code(CONTENT_FNS)
nb.code(r'''
from sklearn.preprocessing import MultiLabelBinarizer

G_all = normalize(MultiLabelBinarizer(sparse_output=True).fit_transform(movies.genres).astype(np.float32))
feats = {"Géneros": G_all[idx], "TF-IDF": T_ours[idx].astype(np.float32), "BM25": normalize(B_all[idx]).astype(np.float32)}
grid = {}
for fname, F in feats.items():
    for scheme in ["binary", "liked", "centered"]:
        grid[(fname, scheme)] = evaluate_topk(content_score_fn(user_weights(R, scheme), F), X, rel)["NDCG@10"]
grid_df = pd.Series(grid).unstack()
grid_df.round(4)
''')
nb.code(r'''
ax = grid_df.plot.bar(figsize=(9, 4), rot=0, color=["#8da0cb", "#66c2a5", "#fc8d62"])
ax.axhline(results["Popularidad"]["NDCG@10"], color="k", ls="--", label="Popularidad")
ax.set_ylabel("NDCG@10"); ax.set_title("Contenido puro: representación × esquema de pesos del perfil")
ax.legend(title="pesos"); plt.tight_layout(); plt.show()
for fname, F in feats.items():
    results[f"{fname} (centrado)"] = evaluate_topk(content_score_fn(user_weights(R, "centered"), F), X, rel)
''')
nb.md("""
🧪 **Lectura honesta del resultado**: el contenido puro queda **muy por debajo** de la popularidad
en ítems *warm*. No es un bug: el perfil de contenido no sabe qué películas son *buenas* ni qué se
está viendo *ahora*; solo sabe qué se *parece* a tu historial. El perfil **centrado** gana a los
otros esquemas (lo que odiaste resta) y además dispara la **coverage**.

Por eso en la industria el contenido casi nunca va solo: se usa como **feature** del ranker,
como **fuente de candidatos** para ítems nuevos, o mezclado con señales colaborativas.
""")

# ---------------- Embeddings densos ----------------
nb.md("""
## 🏭 5. Librerías de industria: embeddings de texto (sentence-transformers)

Modelos *bi-encoder* modernos y abiertos (todos en el [MTEB leaderboard](https://huggingface.co/spaces/mteb/leaderboard)):

| Modelo | Parámetros | Dim | Nota |
|---|---|---|---|
| `BAAI/bge-small-en-v1.5` | 33 M | 384 | rapidísimo, excelente calidad/coste |
| `intfloat/e5-base-v2` | 110 M | 768 | **requiere prefijo** `query: ` / `passage: ` |
| `thenlper/gte-base` | 110 M | 768 | sin prefijos |
| `intfloat/multilingual-e5-base` | 278 M | 768 | si tus sinopsis están en español |
| `Alibaba-NLP/gte-modernbert-base`, `Qwen/Qwen3-Embedding-0.6B` | 149 M / 0.6 B | 768 / 1024 | generación 2025; pruébalos con `FAST_DEV_RUN=False` |

Para similitud **ítem↔ítem** (tarea simétrica) los autores de E5 recomiendan el prefijo `query: `
en ambos lados. Normalizamos los embeddings (`normalize_embeddings=True`) para que coseno = producto escalar.
""")
nb.code(EMBED_CODE)
nb.code(r'''
emb = {}
for key in TEXT_MODEL_KEYS:
    t0 = time.time()
    emb[key] = embed_texts(movies.text.tolist(), key)
    print(f"{key}: {emb[key].shape} en {time.time() - t0:.1f}s")
for key, E in emb.items():
    results[f"{key} (centrado)"] = evaluate_topk(content_score_fn(user_weights(R, "centered"), E[idx]), X, rel)
for mid in [1, 260, 2571]:   # Toy Story, Star Wars, The Matrix
    print(f"🎬 {movies.title[row_of[mid]]} →", more_like_this(mid, emb[TEXT_MODEL_KEYS[0]], 5))
''')
nb.md("""
### 5.1 El problema de la anisotropía (y el truco de centrar)

Los embeddings de Transformers ocupan un **cono estrecho** del espacio: casi todos los pares
tienen coseno alto. Eso aplana las diferencias. Un truco barato y eficaz (Su et al., 2021,
*Whitening Sentence Representations*) es **restar la media** y re-normalizar (o blanquear del todo).
""")
nb.code(r'''
E0 = emb[TEXT_MODEL_KEYS[0]]
E_c = normalize(E0 - E0.mean(0))
rng = np.random.default_rng(seed)
pairs = rng.integers(0, len(E0), size=(20000, 2))
fig, ax = plt.subplots(figsize=(9, 3.8))
for name, M_, c in [("TF-IDF", T_ours, "#8da0cb"), (f"{TEXT_MODEL_KEYS[0]} crudo", E0, "#fc8d62"), (f"{TEXT_MODEL_KEYS[0]} centrado", E_c, "#66c2a5")]:
    a, b = M_[pairs[:, 0]], M_[pairs[:, 1]]
    sims = np.asarray(a.multiply(b).sum(1)).ravel() if sp.issparse(M_) else (a * b).sum(1)
    ax.hist(sims, bins=80, alpha=0.6, label=name, color=c, density=True)
ax.set_xlabel("coseno entre pares aleatorios de películas"); ax.set_ylabel("densidad")
ax.set_title("Distribución de similitudes: los embeddings densos son anisótropos"); ax.legend(); plt.show()
results[f"{TEXT_MODEL_KEYS[0]} centrado-media"] = evaluate_topk(content_score_fn(user_weights(R, "centered"), E_c[idx]), X, rel)
''')
nb.md("""
### 5.2 Visualizar el espacio semántico

Proyectamos los embeddings a 2D con UMAP (fallback: t-SNE) y coloreamos por el género **más
específico** de cada película (el menos frecuente de su lista), para que *Animation* o *Horror*
no queden tapados por *Drama*.
""")
nb.code(r'''
gfreq = movies.explode("genres").genres.value_counts()
movies["main_genre"] = movies.genres.apply(lambda gs: min(gs, key=lambda g: gfreq[g]))
top_g = movies.main_genre.value_counts().index[:9]
lab = movies.main_genre.where(movies.main_genre.isin(top_g), "Otros")
try:
    import umap
    Z = umap.UMAP(n_neighbors=20, min_dist=0.1, metric="cosine", random_state=seed).fit_transform(E_c)
    method = "UMAP"
except Exception:
    from sklearn.manifold import TSNE
    Z = TSNE(n_components=2, init="pca", random_state=seed).fit_transform(E_c); method = "t-SNE"
fig, ax = plt.subplots(figsize=(10, 7))
cmap = plt.get_cmap("tab10")
for k, g in enumerate(list(top_g) + ["Otros"]):
    m = (lab == g).values
    ax.scatter(Z[m, 0], Z[m, 1], s=5, alpha=0.6, color="lightgrey" if g == "Otros" else cmap(k), label=g)
for mid in [1, 260, 2571, 593, 1721, 2355]:
    i = row_of[mid]; ax.annotate(movies.title[i][:22], Z[i], fontsize=8, weight="bold")
ax.legend(markerscale=4, fontsize=8, ncol=2); ax.set_title(f"Espacio de sinopsis ({TEXT_MODEL_KEYS[0]}, {method})")
ax.set_xticks([]); ax.set_yticks([]); plt.show()
''')

# ---------------- CLIP ----------------
nb.md("""
## 🖼️ 6. Multimodal: pósters con CLIP (open_clip)

Netflix ha contado que el **artwork** es lo primero que decide si alguien pulsa un título
(*Artwork Personalization at Netflix*, 2017). Aquí lo usamos como **feature de contenido**:
el póster codifica tono, época, público objetivo (animación infantil vs. thriller oscuro).

Usamos `ViT-B-32` con pesos `laion2b_s34b_b79k` (OpenCLIP entrenado en LAION-2B): buen equilibrio
calidad/velocidad en una T4. Alternativas: `ViT-L-14` (más calidad) o SigLIP (`ViT-B-16-SigLIP`, `webli`).
""")
nb.code(POSTER_CODE)
nb.code(CLIP_CODE)
nb.code(r'''
# Descargamos los N_POSTERS pósters de las películas más populares de train
order = np.argsort(-pop)
pop_ids = enc.items[order[:N_POSTERS]]
t0 = time.time()
poster_paths = download_posters(movies[movies.item_id.isin(pop_ids)])
print(f"{len(poster_paths)} pósters descargados en {time.time() - t0:.0f}s")
HAVE_POSTERS = len(poster_paths) >= 50
clip_model = None
if HAVE_POSTERS:
    try:
        clip_model, clip_pre, clip_tok = load_clip()
    except Exception as e:
        print("⚠️ No se pudo cargar CLIP:", e.__class__.__name__); HAVE_POSTERS = False
if HAVE_POSTERS:
    poster_ids = np.array(sorted(poster_paths))
    P_img = clip_encode_images([poster_paths[i] for i in poster_ids], clip_model, clip_pre)
    print("embeddings de póster:", P_img.shape)
else:
    print("⚠️ Sin pósters (sin red a image.tmdb.org): se omiten las celdas de imagen.")
''')
nb.code(r'''
def show_posters(ids, scores=None, title=""):
    fig, axes = plt.subplots(1, len(ids), figsize=(2.1 * len(ids), 3.4))
    for k, (ax, i) in enumerate(zip(np.atleast_1d(axes), ids)):
        ax.imshow(Image.open(poster_paths[i])); ax.axis("off")
        t = movies.title[row_of[i]][:20] + (f"\n{scores[k]:.2f}" if scores is not None else "")
        ax.set_title(t, fontsize=7.5)
    fig.suptitle(title, fontsize=11); plt.tight_layout(); plt.show()


if HAVE_POSTERS:
    pid_pos = pd.Series(np.arange(len(poster_ids)), index=poster_ids)
    for q in [1, 2571, 1258]:   # Toy Story, The Matrix, The Shining
        if q in pid_pos:
            s = P_img @ P_img[pid_pos[q]]
            top = np.argsort(-s)[:6]
            show_posters(poster_ids[top], s[top], f"Póster consulta (izq.) y sus vecinos CLIP")
''')
nb.code(r'''
# Búsqueda cross-modal: TEXTO → PÓSTER (lo que permite un buscador «muéstrame algo así»)
if HAVE_POSTERS:
    queries = ["a poster of an animated movie for kids", "a dark horror movie poster", "a romantic comedy poster with a couple"]
    Tq = clip_encode_texts(queries, clip_model, clip_tok)
    for q, tv in zip(queries, Tq):
        s = P_img @ tv; top = np.argsort(-s)[:6]
        show_posters(poster_ids[top], s[top], f"«{q}»")
''')
nb.md("""
💡 Fíjate en que los vecinos por póster capturan **estilo visual** (animación, tonos oscuros,
caras en primer plano), no trama. Es una señal **complementaria** a la sinopsis: perfecta para
un híbrido… y también un riesgo (dos pósters azules de épocas distintas pueden parecer «iguales»).
""")

# ---------------- Híbrido ----------------
nb.md("""
## 🧪 7. Experimentos: híbridos simples

### 7.1 Early fusion de modalidades + late fusion con popularidad

Construimos el vector de ítem como concatenación ponderada de géneros, texto y póster (los ítems
sin póster reciben el póster «medio»). Luego mezclamos la puntuación de contenido con el prior de
popularidad: $s=z(s_{\\text{cont}})+\\beta\\,z(\\log(1+\\text{pop}))$.

Para elegir pesos **no miramos el test**: hacemos un split temporal *dentro* de train (validación).
""")
nb.code(r'''
def fused_item_matrix(w_genre=0.4, w_text=0.6, w_img=0.0) -> np.ndarray:
    """Vector por película (filas de `movies`) = concat ponderada de modalidades L2-normalizadas."""
    blocks = [np.sqrt(w_genre) * G_all.toarray(), np.sqrt(w_text) * E_c]
    if w_img > 0 and HAVE_POSTERS:
        I = np.tile(normalize(P_img.mean(0, keepdims=True)), (len(movies), 1))
        I[row_of.loc[poster_ids].values] = P_img
        blocks.append(np.sqrt(w_img) * I)
    return normalize(np.hstack(blocks)).astype(np.float32)


# Validación temporal dentro de train
tr_in, val = temporal_split(train, test_frac=0.1)
enc_v = Encoder(tr_in); a_, b_ = enc_v.transform(tr_in), enc_v.transform(val)
Xv, Rv, relv = enc_v.csr(a_), enc_v.csr(a_, a_.rating.values), test_relevance(b_)
idx_v = row_of.loc[enc_v.items].values
pop_v = np.log1p(np.asarray(Xv.sum(0)).ravel()); pop_v = (pop_v - pop_v.mean()) / pop_v.std()
Wv = user_weights(Rv, "centered")
''')
nb.code(r'''
w_imgs = [0.0, 0.2] if HAVE_POSTERS else [0.0]
betas = [0, 1, 2, 4, 8]
hyb = {}
for wg in [0.2, 0.5]:
    for wi in w_imgs:
        Fv = fused_item_matrix(wg, 1 - wg - wi, wi)[idx_v]
        f = content_score_fn(Wv, Fv)
        for beta in betas:
            hyb[(f"g={wg},img={wi}", beta)] = evaluate_topk(lambda ub: zrow(f(ub)) + beta * pop_v, Xv, relv)["NDCG@10"]
hyb_df = pd.Series(hyb).unstack()
fig, ax = plt.subplots(figsize=(8, 3.2))
im = ax.imshow(hyb_df.values, cmap="magma", aspect="auto")
ax.set_xticks(range(len(betas)), [f"β={b}" for b in betas]); ax.set_yticks(range(len(hyb_df)), hyb_df.index)
for i in range(hyb_df.shape[0]):
    for j in range(hyb_df.shape[1]):
        ax.text(j, i, f"{hyb_df.values[i, j]:.3f}", ha="center", va="center", color="w", fontsize=8)
ax.set_title("NDCG@10 en VALIDACIÓN: pesos de modalidad × peso de popularidad β"); ax.grid(False)
plt.colorbar(im); plt.show()
best_cfg, best_beta = hyb_df.stack().idxmax()
print("Mejor configuración en validación:", best_cfg, "β =", best_beta)
''')
nb.code(r'''
# Re-entrenamos con TODO train y evaluamos UNA vez en test
wg_b = float(best_cfg.split(",")[0].split("=")[1]); wi_b = float(best_cfg.split("=")[-1])
F_best = fused_item_matrix(wg_b, 1 - wg_b - wi_b, wi_b)[idx]
f_best = content_score_fn(user_weights(R, "centered"), F_best)
pop_z = np.log1p(pop); pop_z = (pop_z - pop_z.mean()) / pop_z.std()
results["Híbrido contenido+pop"] = evaluate_topk(lambda ub: zrow(f_best(ub)) + best_beta * pop_z, X, rel)
res_df = pd.DataFrame(results).T.drop(columns="n_users").sort_values("NDCG@10")
fig, axes = plt.subplots(1, 2, figsize=(13, 4.2))
res_df["NDCG@10"].plot.barh(ax=axes[0], color="#4c72b0"); axes[0].set_title("NDCG@10 (test temporal)")
res_df["Coverage"].plot.barh(ax=axes[1], color="#dd8452"); axes[1].set_title("Coverage del catálogo")
plt.tight_layout(); plt.show()
res_df.round(4)
''')
nb.md("""
El híbrido queda **al nivel de la popularidad**: en ítems *warm* el contenido apenas añade señal.
Bajando β ganas coverage y diversidad a costa de NDCG (mira el heatmap de validación): es el
compromiso típico entre precisión y descubrimiento que retomaremos en el módulo 13. En la próxima sesión (04) verás que la señal colaborativa (lo que hacen
*otros* usuarios) supera a ambos en ítems con historial.

### 7.2 Donde el contenido brilla: **cold start de ítems**

Simulamos «estrenos»: escogemos el 15 % de las películas (con ≥ 20 ratings) y **borramos todas sus
interacciones de train**. Para un modelo colaborativo esos ítems no existen. Para el contenido
basta con su sinopsis/póster. Medimos el ranking **entre los ítems fríos** para cada usuario.
""")
nb.code(r'''
rng = np.random.default_rng(seed)
cnt = ratings.item_id.value_counts()
eligible = cnt[cnt >= 20].index.values
cold = np.sort(rng.choice(eligible, size=int(0.15 * len(eligible)), replace=False))
tr_w = train[~train.item_id.isin(cold)]
enc_w = Encoder(tr_w); tw = enc_w.transform(tr_w)
W_w = user_weights(enc_w.csr(tw, tw.rating.values), "centered")
cpos = pd.Series(np.arange(len(cold)), index=cold)
liked_cold = ratings[ratings.item_id.isin(cold) & ratings.user_id.isin(enc_w.users) & (ratings.rating >= 4)]
rel_cold = {u: g.values for u, g in liked_cold.assign(u=enc_w.u2i.loc[liked_cold.user_id].values,
                                                     c=cpos.loc[liked_cold.item_id].values).groupby("u")["c"]}
no_seen = sp.csr_matrix((enc_w.n_users, len(cold)))   # nadie ha «visto» los fríos en train
warm_rows, cold_rows = row_of.loc[enc_w.items].values, row_of.loc[cold].values


def cold_eval(Fm):
    Fw, Fc = Fm[warm_rows], Fm[cold_rows]
    return evaluate_topk(lambda ub: np.asarray((W_w[ub] @ Fw) @ Fc.T.toarray() if sp.issparse(Fc) else (W_w[ub] @ Fw) @ Fc.T), no_seen, rel_cold)


cold_res = {"Aleatorio": evaluate_topk(lambda ub: rng.random((len(ub), len(cold))), no_seen, rel_cold),
            "Géneros": cold_eval(G_all), "TF-IDF": cold_eval(T_ours),
            f"{TEXT_MODEL_KEYS[0]}": cold_eval(E_c), "Fusión (mejor val.)": cold_eval(fused_item_matrix(wg_b, 1 - wg_b - wi_b, wi_b))}
cold_df = pd.DataFrame(cold_res).T
ax = cold_df["NDCG@10"].plot.bar(figsize=(8, 3.6), rot=15, color=["grey"] + ["#55a868"] * (len(cold_df) - 1))
ax.set_ylabel("NDCG@10 entre ítems fríos"); ax.set_title(f"Cold start de {len(cold)} «estrenos» ({len(rel_cold):,} usuarios)")
plt.tight_layout(); plt.show()
cold_df.round(4)
''')
nb.md("""
🧪 Aquí el contenido **multiplica** al azar (que es lo único que tendría un modelo colaborativo
puro). Esta es la razón de ser del contenido en producción: **dar visibilidad a lo nuevo** hasta
que acumule interacciones (y entonces el colaborativo toma el relevo).
""")

# ---------------- Producción ----------------
nb.md("""
## 🏭 8. En producción

- **Netflix** etiqueta su catálogo con taggers humanos entrenados (tono, tipo de final, etc.) y
  genera miles de «altgenres» a partir de esas etiquetas (Madrigal, *How Netflix Reverse-Engineered
  Hollywood*, The Atlantic, 2014). Los metadatos alimentan filas explicables («Thrillers oscuros») y
  son features de los rankers. El **artwork** se personaliza con bandits (*Artwork Personalization
  at Netflix*, 2017) — lo veremos en el módulo 14.
- **Spotify** usó CNNs sobre el **audio** para recomendar canciones sin escuchas (cold start):
  la red predice los factores latentes colaborativos a partir del espectrograma (Dieleman, 2014;
  van den Oord et al., NeurIPS 2013, *Deep content-based music recommendation*).
- **Pinterest** entrena un embedding visual unificado para búsqueda visual y recomendación
  (Zhai et al., KDD 2019, *Learning a Unified Embedding for Visual Search at Pinterest*).
- **Amazon**: los atributos de producto y el texto son la base del cold start de catálogo; el
  colaborativo ítem-a-ítem toma el relevo cuando hay datos (Smith & Linden, 2017, *Two Decades of
  Recommender Systems at Amazon.com*).

**Patrón de serving típico**: los embeddings de ítem se calculan *offline* (batch nocturno o al dar
de alta el ítem), se indexan en un ANN (FAISS/ScaNN, módulo 08) y el perfil de usuario se calcula
*online* como media de los últimos N ítems → latencia de milisegundos. El encoder Transformer
**nunca** está en el camino crítico de cada petición; solo al indexar ítems nuevos.
""")
nb.md("""
## 🧠 9. Secretos de la élite

1. **Parecido semántico ≠ gusto compartido.** Dos películas con sinopsis casi idénticas pueden tener
   públicos opuestos (un *thriller* de culto y su *remake* fallido). Los equipos top **alinean** el
   espacio de contenido con el colaborativo: entrenan un mapeo contenido → factores latentes CF (el
   truco de Spotify/van den Oord 2013; DropoutNet, Volkovs et al., NeurIPS 2017) o hacen *fine-tuning*
   contrastivo del encoder con pares co-consumidos. Lo implementarás como reto en el proyecto.
2. **El MTEB no es tu métrica.** Un modelo top en el leaderboard puede perder contra `bge-small` en
   *tu* tarea. Elige encoder con **tu** métrica offline (NDCG en split temporal, cold-start), no por ranking público.
3. **Prefijos y normalización importan.** Olvidar `query: `/`passage: ` en E5 o no normalizar los
   embeddings degrada la calidad sin dar ningún error. Y **centrar** (restar la media) corrige la
   anisotropía casi gratis (Su et al., 2021).
4. **Las features «aburridas» ganan.** El año y los géneros suelen pesar más que la sinopsis para
   predecir co-consumo: el público de una película se parece al de otras **de su época**. Pruébalo en
   el proyecto añadiendo una penalización por diferencia de año.
5. **El contenido puro casi nunca va solo a producción.** Se usa como fuente de candidatos para ítems
   fríos, como feature del ranker o como *fallback*. Medido honestamente (split temporal), pierde
   contra popularidad en ítems con historial — si tu experimento dice lo contrario, busca una fuga.
6. **Perfil centrado o con negativos.** Sumar todo lo visto (pesos binarios) convierte el perfil en
   «la media del catálogo». Restar lo que no gustó y ponderar por recencia mejora mucho.
7. **Cachea embeddings con versión del modelo.** Cambiar de encoder invalida todo el índice ANN; en
   producción se versiona `(modelo, versión, hash del texto)` y se re-indexa en *blue/green*.
""")
nb.md("""
## ⚠️ 10. Errores comunes

- **Fuga por metadatos**: usar campos que contienen el futuro (p. ej. nº de votos o rating medio de
  TMDB de 2017 para predecir ratings del 2000). Úsalos solo si estarían disponibles en el momento de recomendar.
- Ajustar el TF-IDF o el vocabulario **con el test**: aquí es inofensivo (los textos no son
  interacciones), pero ajustar *pesos del híbrido* con el test sí es fuga → usa validación.
- Comparar coseno entre embeddings **no normalizados** o de modelos distintos.
- Evaluar cold start con ítems que sí estaban en train (no es cold start).
- Olvidar excluir los ítems ya vistos al recomendar (infla o hunde métricas según el caso).
- Creer que más dimensiones = mejor: con 3 700 ítems, 384 dimensiones bien centradas sobran.
""")
nb.md("""
## ✅ 11. Autoevaluación

1. ¿Por qué el perfil centrado ($r_{ui}-\\bar r_u$) suele funcionar mejor que el binario?
<details><summary>Respuesta</summary>Porque los ítems por debajo de la media del usuario restan, de modo que el perfil apunta hacia lo que le gusta y se aleja de lo que no. Con pesos binarios todo suma y el perfil tiende al «centro» del catálogo.</details>

2. ¿Qué dos problemas de TF-IDF resuelve BM25?
<details><summary>Respuesta</summary>La saturación de la frecuencia del término (parámetro $k_1$) y la normalización por longitud de documento (parámetro $b$).</details>

3. ¿Qué es la anisotropía de los embeddings y cómo se mitiga?
<details><summary>Respuesta</summary>Los vectores se concentran en un cono estrecho y casi todos los cosenos son altos. Se mitiga restando la media (centrado) y re-normalizando, o con whitening.</details>

4. ¿Por qué el contenido pierde contra popularidad en el split temporal pero gana en cold start?
<details><summary>Respuesta</summary>En ítems warm, la popularidad reciente captura calidad y tendencia, que el contenido ignora. En ítems fríos no hay popularidad ni señal colaborativa, y el contenido es la única información disponible.</details>

5. ¿Qué ventaja tiene CLIP frente a un CNN de clasificación de ImageNet para pósters?
<details><summary>Respuesta</summary>Comparte espacio con el texto: permite búsqueda texto→imagen y fusionar con sinopsis de forma natural, y sus features capturan conceptos (género, tono) aprendidos de pies de foto, no solo 1000 clases.</details>

6. ¿Por qué no se debe elegir el peso β del híbrido mirando el test?
<details><summary>Respuesta</summary>Porque entonces el test deja de ser una estimación insesgada del rendimiento futuro (es tuning sobre el test → sobreestimación). Se ajusta en validación y se mide una sola vez en test.</details>

7. ¿Resuelve el contenido el cold start de usuarios?
<details><summary>Respuesta</summary>No directamente: sin historial no hay perfil. Se usan preguntas de onboarding, datos demográficos/contextuales o popularidad hasta tener unas pocas interacciones.</details>
""")
nb.md("""
## 📚 12. Referencias

**Papers**
- Lops, de Gemmis & Semeraro (2011). *Content-based Recommender Systems: State of the Art and Trends*. Recommender Systems Handbook, Springer.
- Robertson & Zaragoza (2009). *The Probabilistic Relevance Framework: BM25 and Beyond*. Foundations and Trends in IR.
- Reimers & Gurevych (2019). *Sentence-BERT*. EMNLP. [arXiv:1908.10084](https://arxiv.org/abs/1908.10084)
- Wang et al. (2022). *Text Embeddings by Weakly-Supervised Contrastive Pre-training* (E5). [arXiv:2212.03533](https://arxiv.org/abs/2212.03533)
- Xiao et al. (2023). *C-Pack: Packaged Resources To Advance General Chinese Embedding* (BGE). [arXiv:2309.07597](https://arxiv.org/abs/2309.07597)
- Li et al. (2023). *Towards General Text Embeddings with Multi-stage Contrastive Learning* (GTE). [arXiv:2308.03281](https://arxiv.org/abs/2308.03281)
- Radford et al. (2021). *Learning Transferable Visual Models From Natural Language Supervision* (CLIP). [arXiv:2103.00020](https://arxiv.org/abs/2103.00020)
- Cherti et al. (2023). *Reproducible scaling laws for contrastive language-image learning* (OpenCLIP/LAION). [arXiv:2212.07143](https://arxiv.org/abs/2212.07143)
- Su et al. (2021). *Whitening Sentence Representations for Better Semantics and Faster Retrieval*. [arXiv:2103.15316](https://arxiv.org/abs/2103.15316)
- van den Oord, Dieleman & Schrauwen (2013). *Deep content-based music recommendation*. NeurIPS.
- Volkovs, Yu & Poutanen (2017). *DropoutNet: Addressing Cold Start in Recommender Systems*. NeurIPS.
- Zhai et al. (2019). *Learning a Unified Embedding for Visual Search at Pinterest*. KDD. [arXiv:1908.01707](https://arxiv.org/abs/1908.01707)
- Spillo et al. (2026). *Binge Watch: Reproducible Multimodal Benchmarks Datasets for Large-Scale Movie Recommendation on MovieLens-10M and 20M*. [arXiv:2602.15505](https://arxiv.org/abs/2602.15505)
- Harper & Konstan (2015). *The MovieLens Datasets: History and Context*. ACM TiiS.

**Blogs y artículos de industria**
- Netflix Tech Blog (2017). *Artwork Personalization at Netflix*. https://netflixtechblog.com/artwork-personalization-c589f074ad76
- Madrigal (2014). *How Netflix Reverse-Engineered Hollywood*. The Atlantic.
- Dieleman (2014). *Recommending music on Spotify with deep learning*. https://sander.ai/2014/08/05/spotify-cnns.html
- Smith & Linden (2017). *Two Decades of Recommender Systems at Amazon.com*. IEEE Internet Computing.

**Librerías**: [sentence-transformers](https://www.sbert.net) · [open_clip](https://github.com/mlfoundations/open_clip) · [MTEB](https://github.com/embeddings-benchmark/mteb) · [umap-learn](https://umap-learn.readthedocs.io)
""")
nb.save(LESSON)

# ---------------------------------------------------------------------------
# PROYECTO
# ---------------------------------------------------------------------------
PROJ = f"{MOD}/03_proyecto_more_like_this.ipynb"
pj = Notebook("Proyecto 03 · «Más como esta» en CineMatch", colab_path=PROJ, gpu=True)
pj.md(f"""
{pj.badge()}

# Proyecto 03 · «Más como esta» para CineMatch
| | |
|---|---|
| **Nivel** | 🟡 Intermedio |
| **Duración** | 3–5 h |
| **GPU** | T4 recomendada (embeddings + CLIP); ≈ 1–2 unidades |
| **Prerrequisitos** | Lección 03 |

## 🏢 Contexto de negocio

Eres ML engineer en **CineMatch**. Producto quiere lanzar la fila **«Más como esta»** en la ficha
de cada película (lo que ves al pulsar un título). Requisitos:

- Debe funcionar **el día del estreno** (sin interacciones): el equipo de contenidos sube sinopsis y póster.
- Debe parecerse a lo que *de verdad* ve la gente que vio la película (los PMs lo comprobarán con datos de co-consumo).
- Latencia: los vecinos se precalculan offline; solo hace falta un *lookup*.

## 📦 Dataset
MovieLens 1M + sinopsis y pósters TMDB vía M³L (mismo loader que la lección, con fallbacks).

## 📋 Entregables y rúbrica

| # | Entregable | Criterio |
|---|---|---|
| 1 | `item_vectors()` que fusiona géneros + texto (+ póster opcional) | Código limpio y documentado |
| 2 | `more_like_this(item_id, k)` | Devuelve títulos coherentes para 5 películas de prueba |
| 3 | **CoWatch-HR@10** (proporción de los 10 vecinos de contenido que están entre los 50 vecinos colaborativos) | **≥ 0,25** (géneros solos ≈ 0,20; reto experto: ≥ 0,35) |
| 4 | **Cold start**: NDCG@10 entre «estrenos» simulados (perfil centrado) | **≥ 2× el aleatorio** (reto: ≥ 3×) |
| 5 | Grid de pósters de 3 consultas + 1 párrafo de análisis de errores | Cualitativo |

Los pesos se eligen en **validación** (ítems de ajuste), y se reportan en ítems de test.
""")
pj.code("""
!pip install -q open_clip_torch sentence-transformers pyarrow
""")
pj.code(r'''
import os, random, time, warnings
import numpy as np, pandas as pd, matplotlib.pyplot as plt, torch
warnings.filterwarnings("ignore")
seed = 42; random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
device = "cuda" if torch.cuda.is_available() else "cpu"
FAST_DEV_RUN = True
N_POSTERS = 400 if FAST_DEV_RUN else 4000
TEXT_MODEL_KEYS = ["bge-small"] if FAST_DEV_RUN else ["bge-small", "e5-base", "gte-base"]
''')
add_utils(pj)
pj.md("### Funciones de la lección (metadatos, embeddings, pósters, CLIP)")
pj.code(METADATA_CODE)
pj.code(EMBED_CODE)
pj.code(POSTER_CODE)
pj.code(CLIP_CODE)
pj.code(r'''
ratings, movies, users = load_movielens_1m()
movies = load_movie_metadata(movies)
train, test = temporal_split(ratings)
row_of = pd.Series(np.arange(len(movies)), index=movies.item_id)
''')
pj.md("""
## Paso 1 · La «verdad» de co-consumo (proporcionada)

Para cada película con ≥ 30 *likes* en train calculamos sus 50 vecinos por **coseno colaborativo**
sobre likes (rating ≥ 4). Esa es la referencia con la que los PMs juzgarán la fila. Dividimos esas
películas en **ajuste** (para elegir pesos) y **test** (para reportar).
""")
pj.code(r'''
likes = train[train.rating >= 4]
enc = Encoder(likes); L = enc.csr(enc.transform(likes))
cnt = np.asarray(L.sum(0)).ravel()
Gm = (L.T @ L).toarray().astype(np.float32); nrm = np.sqrt(np.diag(Gm))
Scf = Gm / np.outer(nrm, nrm).clip(1e-9); np.fill_diagonal(Scf, -1); Scf[:, cnt < 30] = -1
query_iidx = np.where(cnt >= 30)[0]
truth = np.argsort(-Scf[query_iidx], 1)[:, :50]
rng = np.random.default_rng(seed)
is_tune = rng.random(len(query_iidx)) < 0.5
rows_enc = row_of.loc[enc.items].values          # fila de `movies` para cada iidx de `enc`
print(f"{len(query_iidx)} películas consulta · {is_tune.sum()} ajuste / {(~is_tune).sum()} test")
''')
pj.md("""
## Paso 2 · Métrica CoWatch-HR@10  ✏️ TODO

Implementa `cowatch_hr(F, mask)` : para cada película consulta (filtrada por `mask`), busca sus 10
vecinos más similares según `F[rows_enc]` (excluyéndose a sí misma y a las películas con `cnt < 30`)
y calcula la fracción que cae dentro de `truth`. Devuelve la media.

💡 Pista: `S = Fq @ F.T`, pon `-inf` en la diagonal y en las columnas no elegibles, `np.argsort(-S, 1)[:, :10]`, `np.isin`.
""")
pj.code(r'''
def cowatch_hr(F_items: np.ndarray, mask: np.ndarray, k: int = 10) -> float:
    """F_items: matriz (n_items_enc × d) L2-normalizada, alineada con enc.items."""
    # TODO: implementa la métrica
    raise NotImplementedError
''')
pj.md("""
## Paso 3 · Representaciones  ✏️ TODO

1. `G`: géneros one-hot normalizados (filas de `movies`).
2. `T`: TF-IDF de `movies.text` (`sublinear_tf=True`, `stop_words="english"`).
3. `E`: embeddings densos con `embed_texts(movies.text.tolist(), "bge-small")`, **centrados** y re-normalizados.
4. (Opcional) `P`: pósters CLIP para las `N_POSTERS` más populares; el resto recibe el póster medio.

Mide `cowatch_hr` en las películas de **ajuste** para cada una.
""")
pj.code(r'''
from sklearn.preprocessing import normalize, MultiLabelBinarizer
from sklearn.feature_extraction.text import TfidfVectorizer
# TODO: construye G, T, E (y opcionalmente P) y mide cowatch_hr(F[rows_enc], is_tune) para cada una
G = T = E = P = None
''')
pj.md("""
## Paso 4 · Fusión + año  ✏️ TODO

Implementa `item_vectors(w_genre, w_text, w_img)` (early fusion con $\\sqrt{w}$) y un
`more_like_this(item_id, k, gamma)` que reste `gamma · |año_i − año_j| / 10` a la similitud.
Haz un grid sobre `w_genre ∈ {0.2,…,0.8}`, `gamma ∈ {0, 0.05, 0.1, 0.2}` en **ajuste**.
""")
pj.code(r'''
def item_vectors(w_genre: float, w_text: float, w_img: float = 0.0) -> np.ndarray:
    # TODO
    raise NotImplementedError


def cowatch_hr_year(F_items, mask, gamma, k=10) -> float:
    # TODO: como cowatch_hr pero con penalización por diferencia de año
    raise NotImplementedError
''')
pj.md("""
## Paso 5 · Cold start  ✏️ TODO

Reutiliza el protocolo de la lección (15 % de películas con ≥ 20 ratings como «estrenos», borradas
de train; perfil centrado; ranking entre ítems fríos). Compara: aleatorio, géneros, texto, tu fusión.
""")
pj.code(r'''
# TODO: protocolo de cold start y tabla de resultados
''')
pj.md("""
## Paso 6 · Informe  ✏️ TODO
Tabla final en el conjunto de **test** (CoWatch-HR@10 + cold start), grid de pósters de 3 consultas y
un párrafo: ¿en qué falla tu «Más como esta»? (secuelas, remakes, películas infantiles vs adultas…).
""")
pj.md("""
---
# ⛔ SPOILER — intenta resolverlo primero

A partir de aquí está la **solución de referencia** completa.
""")
pj.code(r'''
def _hr_from_sim(S, q, k, truth_rows):
    S[np.arange(len(q)), q] = -np.inf
    S[:, cnt < 30] = -np.inf
    top = np.argsort(-S, 1)[:, :k]
    return float(np.mean([np.isin(t, g).mean() for t, g in zip(top, truth_rows)]))


def cowatch_hr(F_items, mask, k=10):
    q = query_iidx[mask]
    return _hr_from_sim(np.asarray(F_items[q] @ F_items.T, dtype=np.float32), q, k, truth[mask])


years = movies.year.fillna(movies.year.median()).values


def cowatch_hr_year(F_items, mask, gamma, k=10):
    q = query_iidx[mask]
    y = years[rows_enc]
    S = np.asarray(F_items[q] @ F_items.T, dtype=np.float32) - gamma * np.abs(y[q][:, None] - y[None, :]) / 10
    return _hr_from_sim(S, q, k, truth[mask])
''')
pj.code(r'''
G = normalize(MultiLabelBinarizer().fit_transform(movies.genres).astype(np.float32))
T = TfidfVectorizer(stop_words="english", min_df=2, sublinear_tf=True).fit_transform(movies.text)
T = T.astype(np.float32).toarray()
E_raw = embed_texts(movies.text.tolist(), TEXT_MODEL_KEYS[0])
E = normalize(E_raw - E_raw.mean(0)).astype(np.float32)

# Pósters (opcional): si no hay red a TMDB, P queda en None
pop_like = cnt.copy()
top_ids = enc.items[np.argsort(-pop_like)[:N_POSTERS]]
paths = download_posters(movies[movies.item_id.isin(top_ids)])
P = None
if len(paths) >= 50:
    try:
        cm, cpre, _ = load_clip()
        pids = np.array(sorted(paths))
        Pimg = clip_encode_images([paths[i] for i in pids], cm, cpre)
        P = np.tile(normalize(Pimg.mean(0, keepdims=True)), (len(movies), 1))
        P[row_of.loc[pids].values] = Pimg
    except Exception as e:
        print("CLIP no disponible:", e.__class__.__name__)
single = {"Géneros": G, "TF-IDF": T, TEXT_MODEL_KEYS[0]: E} | ({"Póster CLIP": P} if P is not None else {})
print({k: round(cowatch_hr(v[rows_enc], is_tune), 4) for k, v in single.items()})
''')
pj.code(r'''
def item_vectors(w_genre, w_text, w_img=0.0):
    blocks = [np.sqrt(w_genre) * G, np.sqrt(w_text) * E]
    if w_img > 0 and P is not None:
        blocks.append(np.sqrt(w_img) * P)
    return normalize(np.hstack(blocks)).astype(np.float32)


grid = {}
for wg in [0.2, 0.4, 0.6, 0.8]:
    for wi in ([0.0, 0.15] if P is not None else [0.0]):
        F = item_vectors(wg, 1 - wg - wi, wi)[rows_enc]
        for gamma in [0.0, 0.05, 0.1, 0.2]:
            grid[(wg, wi, gamma)] = cowatch_hr_year(F, is_tune, gamma)
best = max(grid, key=grid.get)
print("Mejor (w_genre, w_img, gamma) en ajuste:", best, "→", round(grid[best], 4))
gdf = pd.Series(grid).rename_axis(["w_genre", "w_img", "gamma"]).reset_index(name="hr")
fig, ax = plt.subplots(figsize=(7, 3.5))
for (wg, wi), g in gdf.groupby(["w_genre", "w_img"]):
    ax.plot(g.gamma, g.hr, marker="o", label=f"w_genre={wg}, w_img={wi}")
ax.set_xlabel("γ (penalización por año)"); ax.set_ylabel("CoWatch-HR@10 (ajuste)"); ax.legend(fontsize=7)
ax.set_title("Efecto de la fusión y del año"); plt.show()
''')
pj.code(r'''
wg, wi, gamma = best
F_best_all = item_vectors(wg, 1 - wg - wi, wi)


def more_like_this(item_id: int, k: int = 10, gamma: float = gamma):
    i = row_of[item_id]
    s = F_best_all @ F_best_all[i] - gamma * np.abs(years - years[i]) / 10
    s[i] = -np.inf
    top = np.argsort(-s)[:k]
    return movies.iloc[top][["item_id", "title"]].assign(score=s[top].round(3))


final = {k: cowatch_hr(v[rows_enc], ~is_tune) for k, v in single.items()}
final["Fusión + año (CineMatch)"] = cowatch_hr_year(F_best_all[rows_enc], ~is_tune, gamma)
final["Aleatorio"] = float(np.mean([np.isin(rng.choice(np.where(cnt >= 30)[0], 10, replace=False), g).mean() for g in truth[~is_tune]]))
print(pd.Series(final).sort_values().round(4))
for mid in [1, 260, 1196]:
    print("\n🎬", movies.title[row_of[mid]]); print(more_like_this(mid, 5).to_string(index=False))
''')
pj.code(r'''
# Cold start (mismo protocolo que la lección)
import scipy.sparse as sp
cnt_all = ratings.item_id.value_counts()
eligible = cnt_all[cnt_all >= 20].index.values
cold = np.sort(np.random.default_rng(seed).choice(eligible, size=int(0.15 * len(eligible)), replace=False))
tr_w = train[~train.item_id.isin(cold)]
enc_w = Encoder(tr_w); tw = enc_w.transform(tr_w)
Rw = enc_w.csr(tw, tw.rating.values).tocsr()
cts = np.diff(Rw.indptr); Rw.data -= np.repeat(np.asarray(Rw.sum(1)).ravel() / np.maximum(cts, 1), cts)
cpos = pd.Series(np.arange(len(cold)), index=cold)
lc = ratings[ratings.item_id.isin(cold) & ratings.user_id.isin(enc_w.users) & (ratings.rating >= 4)]
rel_cold = {u: g.values for u, g in lc.assign(u=enc_w.u2i.loc[lc.user_id].values, c=cpos.loc[lc.item_id].values).groupby("u")["c"]}
no_seen = sp.csr_matrix((enc_w.n_users, len(cold)))
wr, cr = row_of.loc[enc_w.items].values, row_of.loc[cold].values
cold_eval = lambda F: evaluate_topk(lambda ub: (Rw[ub] @ F[wr]) @ F[cr].T, no_seen, rel_cold)["NDCG@10"]
cold_res = {"Aleatorio": evaluate_topk(lambda ub: rng.random((len(ub), len(cold))), no_seen, rel_cold)["NDCG@10"],
            "Géneros": cold_eval(G), TEXT_MODEL_KEYS[0]: cold_eval(E), "Fusión CineMatch": cold_eval(F_best_all)}
print(pd.Series(cold_res).round(4)); print("ratio vs aleatorio:", round(cold_res["Fusión CineMatch"] / cold_res["Aleatorio"], 2))
''')
pj.code(r'''
# Grid cualitativo de pósters
from PIL import Image
if P is not None:
    for mid in [1, 2571, 1258]:
        if mid not in paths: continue
        recs = [r for r in more_like_this(mid, 30).item_id if r in paths][:5]
        fig, axes = plt.subplots(1, 6, figsize=(12, 3.2))
        for ax, i in zip(axes, [mid] + recs):
            ax.imshow(Image.open(paths[i])); ax.axis("off"); ax.set_title(movies.title[row_of[i]][:18], fontsize=7)
        plt.suptitle("Consulta (izq.) → «Más como esta»"); plt.show()
else:
    print("Sin pósters disponibles: omito el grid.")
''')
pj.md("""
**Análisis de errores (solución de referencia)**: la fusión acierta franquicias y subgéneros, pero
(1) mezcla películas infantiles con adultas que comparten género *Animation*; (2) los remakes salen
arriba aunque su público sea otro; (3) el año ayuda mucho porque los públicos de MovieLens están
muy cohortizados por época; (4) **la mejor fusión para co-consumo (mucho peso en géneros) no es la
mejor para cold start (donde gana el texto)**: objetivos distintos piden pesos distintos, así que en
producción se mantienen dos configuraciones (fila «Más como esta» vs. candidatos de estrenos). La señal
colaborativa (módulo 04) corrige casi todo esto en ítems warm.

## 🚀 Retos extra (nivel experto)

1. **Alinear contenido con CF**: entrena una regresión (ridge o MLP en PyTorch) que prediga el
   vector colaborativo de un ítem (fila de `Scf` reducida con SVD) desde `[G, E, P]`. Úsala para el
   cold start y compárala con la fusión (idea de van den Oord 2013 / DropoutNet).
2. **Fine-tuning contrastivo** de `bge-small` con pares (ítem, vecino colaborativo) usando
   `MultipleNegativesRankingLoss` de sentence-transformers. ¿Sube CoWatch-HR sin romper el cold start?
3. **Sinopsis en español** con `intfloat/multilingual-e5-base` traduciendo un subconjunto con un LLM.
4. **Índice ANN**: indexa `F_best_all` en FAISS y mide la latencia de `more_like_this` (anticipo del módulo 08).

## 🤔 Reflexión (producción / MLOps)

- ¿Cómo versionarías los embeddings para que un cambio de encoder no rompa la fila en producción?
- ¿Qué monitorizarías tras el lanzamiento (CTR de la fila, cobertura de estrenos, drift del encoder)?
- ¿Cuándo «graduarías» un estreno del contenido al colaborativo? ¿Con cuántas interacciones?
""")
pj.save(PROJ)

# ---------------------------------------------------------------------------
# README
# ---------------------------------------------------------------------------
Path(f"{MOD}/README.md").write_text("""# 03 · Recomendación basada en contenido

🟢→🟡 · 3–4 h (lección) + 3–5 h (proyecto) · GPU T4 recomendada (≈ 1–2 unidades de Colab)

Primer recomendador **personalizado** del curso: describimos cada película por su contenido
(géneros, sinopsis, póster) y recomendamos lo que se parece a tu historial.

## Contenido
| Notebook | Qué hay dentro |
|---|---|
| [`03_content_based.ipynb`](03_content_based.ipynb) | TF-IDF y BM25 desde cero · perfiles de usuario (Rocchio centrado) · embeddings BGE/E5/GTE con sentence-transformers · anisotropía y centrado · UMAP del espacio semántico · CLIP (open_clip) para pósters y búsqueda texto→imagen · híbrido contenido+popularidad · cold start de ítems |
| [`03_proyecto_more_like_this.ipynb`](03_proyecto_more_like_this.ipynb) | Fila «Más como esta» de CineMatch: fusión géneros+texto+póster+año evaluada con co-consumo (CoWatch-HR@10) y cold start |

## Objetivos
- Construir y evaluar recomendadores de contenido con métricas top-K en split temporal.
- Usar encoders de texto modernos y CLIP; entender cuándo el contenido gana (cold start) y cuándo pierde (ítems warm).
- Diseñar híbridos simples sin fuga de información (pesos en validación).

## Datasets
- **MovieLens 1M** (GroupLens; espejo en GitHub como fallback).
- **Sinopsis + pósters TMDB** vía [M³L](https://github.com/giuspillo/M3L_10M_20M) (Spillo et al., 2026), commit fijado; fallback: Kaggle *The Movies Dataset* (`rounakbanik/the-movies-dataset`) o solo título+géneros.
- Uso solo educativo/investigación (licencia MovieLens).

## Lecturas clave
- Lops et al. (2011), *Content-based Recommender Systems: State of the Art and Trends*.
- Robertson & Zaragoza (2009), *BM25 and Beyond*.
- Radford et al. (2021), *CLIP*; Wang et al. (2022), *E5*; Xiao et al. (2023), *BGE*.
- van den Oord et al. (2013), *Deep content-based music recommendation*; Volkovs et al. (2017), *DropoutNet*.

## Conexión con CineMatch
Este módulo produce la fila «Más como esta» y la fuente de candidatos para **estrenos**. En 04/05
añadimos la señal colaborativa; en 08 indexaremos estos embeddings en FAISS.

Los notebooks se generan con `python recsys-course/_tools/builders/build_03.py`.
""", encoding="utf-8")
print("README OK")
