"""Celdas compartidas por build_18.py, build_19.py y build_20.py (autor A7).

Cada notebook es autocontenido: estas cadenas se copian TAL CUAL dentro de celdas de código.
Reutiliza las piezas canónicas del curso (no las reescribe):
- corpus, métricas y BM25 del módulo 00  -> poliglota_utils.py
- embedders con fallback TF-IDF+SVD       -> _a5_common.CODE_EMBEDDER_TOOLS (módulo 12)
- bootstrap / test pareado                -> _a6_src15.STATS_SRC (poliglota_eval.py, módulo 15)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from poliglota_utils import SRC_METRICS, SRC_BM25, src_corpus_cells  # noqa: E402,F401
from _a5_common import CODE_EMBEDDER_TOOLS  # noqa: E402,F401
from _a6_src15 import STATS_SRC  # noqa: E402,F401

CODE_PIP = r'''
!pip install -q faiss-cpu qdrant-client fastapi httpx sentence-transformers scikit-learn matplotlib pandas
'''

CODE_SETUP = r'''
import os, sys, time, math, random, json, hashlib, unicodedata, warnings
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

SEED = 42
random.seed(SEED); np.random.seed(SEED)
FAST_DEV_RUN = True       # True: tamaños diminutos (CPU en minutos). False en Colab con GPU para modelos reales y más datos.
N_THREADS = int(os.environ.get("N_THREADS", "1" if FAST_DEV_RUN else "4"))
os.environ.setdefault("OMP_NUM_THREADS", str(N_THREADS))
try:
    import torch
    torch.manual_seed(SEED); torch.set_num_threads(N_THREADS)
    device = "cuda" if torch.cuda.is_available() else "cpu"
except ImportError:
    torch, device = None, "cpu"
AZUL, NARANJA, VERDE, GRIS, ROJO = "#1F6FEB", "#F28E2B", "#2CA02C", "#6B7280", "#D62728"
plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": .25})
print(f"device={device} · FAST_DEV_RUN={FAST_DEV_RUN} · threads={N_THREADS}")
'''

CODE_LOAD = r'''
corpus = carga_corpus(fast_dev=FAST_DEV_RUN)
docs, queries, qrels = corpus["docs"], corpus["queries"], corpus["qrels"]
doc_ids = [d["id"] for d in docs]; doc_texts = [d["text"] for d in docs]
doc_lang = np.array([d["lang"] for d in docs])
qids = [q["qid"] for q in queries]; q_texts = [q["text"] for q in queries]; q_lang = np.array([q["lang"] for q in queries])
print(f"fuente={corpus['source']} · {len(docs)} docs · {len(queries)} queries · idiomas={sorted(set(doc_lang))}")
'''

CODE_HELPERS = r'''
def run_desde_scores(S, k: int = 10, ids=None) -> dict:
    """Matriz de scores (n_queries x n_docs) -> run {qid: [doc_ids top-k]} con el desempate canónico."""
    ids = doc_ids if ids is None else ids
    return {qid: rank_from_scores(S[i], ids, k) for i, qid in enumerate(qids)}

def ndcg_por_query(run: dict, k: int = 10) -> np.ndarray:
    """nDCG@k de cada query (orden de `qids`); unidad de remuestreo para bootstrap."""
    return np.array([ndcg_at_k(run.get(q, []), qrels[q], k) for q in qids])

def l2n(X):
    X = np.asarray(X, dtype=np.float32)
    return X / np.maximum(np.linalg.norm(X, axis=1, keepdims=True), 1e-9)

BM25_IDX = BM25().fit([tokenize_simple(t) for t in doc_texts], doc_ids)
S_BM25 = np.array([BM25_IDX.scores(tokenize_simple(q)) for q in q_texts])
print("BM25 (baseline del módulo 00):", {m: round(v, 3) for m, v in evaluate(run_desde_scores(S_BM25), qrels).items() if m in ("ndcg", "recall", "mrr")})
'''

CODE_VERSIONES = r'''
# Dos versiones del embedder de Políglota: v1 (la que está en producción) y v2 (la candidata).
# Con hub: v1 = multilingual-e5-small (384 d), v2 = multilingual-e5-base (768 d).
# Sin hub: dos fallbacks TF-IDF+SVD DISTINTOS (otro analizador y otra dimensión) -> espacios incompatibles, como en la vida real.
USAR_MODELOS_REALES = True
V1_REAL, V2_REAL = "multilingual-e5-small", "multilingual-e5-base"

def carga_versiones(textos_ajuste) -> dict:
    vers = {}
    if USAR_MODELOS_REALES:
        for nombre, clave in (("v1", V1_REAL), ("v2", V2_REAL)):
            e = cargar_embedder(clave)          # None si no hay hub
            if e is None:
                break
            vers[nombre] = e
    if len(vers) < 2:
        print("⚠️  Sin modelos reales: v1/v2 = fallbacks TF-IDF+SVD (NO son modelos neuronales; las cifras no representan a e5).")
        vers = {"v1": Embedder("v1 · char 3-4 + SVD 48d (fallback)", {}, fallback=HashSVDEmbedder(dim=48, ngram=(3, 4)).fit(textos_ajuste)),
                "v2": Embedder("v2 · char 2-5 + SVD 128d (fallback)", {}, fallback=HashSVDEmbedder(dim=128, ngram=(2, 5)).fit(textos_ajuste))}
    return vers

VERS = carga_versiones(doc_texts)
EMB = {}
for v, e in VERS.items():
    t0 = time.perf_counter()
    D, Qv = e.encode_docs(doc_texts), e.encode_queries(q_texts)
    EMB[v] = {"D": D, "Q": Qv, "seg": time.perf_counter() - t0}
    print(f"{v}: {e.clave} · dim={D.shape[1]} · nDCG@10={evaluate(run_desde_scores(Qv @ D.T), qrels)['ndcg']:.3f} · {EMB[v]['seg']:.1f}s")
'''

# ─────────────── Servicio Políglota (solución del proyecto 18; reutilizado en el 20) ───────────────
CODE_CACHE = r'''
from collections import OrderedDict

def normaliza_query(texto: str) -> str:
    """Normalización ANTES de la clave de caché: NFC + minúsculas + espacios colapsados (sube el hit rate)."""
    return " ".join(unicodedata.normalize("NFC", texto).lower().split())

def clave_cache(version: str, texto: str) -> str:
    """La versión del modelo VA EN LA CLAVE: si no, tras migrar servirías vectores v1 contra un índice v2."""
    return hashlib.sha1(f"{version}\x00{normaliza_query(texto)}".encode("utf-8")).hexdigest()

class LRUCache:
    """Caché LRU O(1) con OrderedDict y contadores de aciertos/fallos."""
    def __init__(self, capacidad: int):
        self.cap, self.d, self.hits, self.misses = capacidad, OrderedDict(), 0, 0
    def get(self, k):
        if k in self.d:
            self.d.move_to_end(k); self.hits += 1
            return self.d[k]
        self.misses += 1
        return None
    def put(self, k, v):
        self.d[k] = v; self.d.move_to_end(k)
        if len(self.d) > self.cap:
            self.d.popitem(last=False)          # expulsa el menos usado recientemente
    @property
    def hit_rate(self) -> float:
        n = self.hits + self.misses
        return self.hits / n if n else 0.0
'''

CODE_SERVICE = r'''
import faiss
faiss.omp_set_num_threads(1)

class ServicioPoliglota:
    """Búsqueda versionada: caché de embeddings de query + índice denso por versión (FAISS IndexFlatIP) + BM25,
    filtro por idioma, fusión RRF, alias 'prod' -> versión y versiones 'adaptador' (queries nuevas -> índice viejo)."""
    def __init__(self, docs, bm25, cache_cap: int = 2048, rrf_k: int = 60, profundidad: int = 50):
        self.ids = [d["id"] for d in docs]; self.lang = np.array([d["lang"] for d in docs])
        self.bm25, self.cache, self.rrf_k, self.prof = bm25, LRUCache(cache_cap), rrf_k, profundidad
        self.versiones, self.alias, self.lat_ms = {}, {}, []

    def registrar_version(self, nombre, embedder, D):
        idx = faiss.IndexFlatIP(D.shape[1]); idx.add(l2n(D))
        self.versiones[nombre] = {"emb": embedder, "idx": idx, "W": None, "base": nombre}

    def registrar_adaptador(self, nombre, embedder, W, sobre: str):
        """Queries con `embedder` (versión nueva) proyectadas con W al espacio del índice `sobre` (versión vieja)."""
        self.versiones[nombre] = {"emb": embedder, "idx": self.versiones[sobre]["idx"], "W": W, "base": sobre}

    def embebe_query(self, texto, nombre):
        k = clave_cache(nombre, texto)
        v = self.cache.get(k)
        if v is None:
            cfg = self.versiones[nombre]
            v = cfg["emb"].encode_queries([texto])
            if cfg["W"] is not None:
                v = l2n(v @ cfg["W"])
            self.cache.put(k, v)
        return v

    def _rangos_densos(self, texto, nombre, cand):
        idx = self.versiones[nombre]["idx"]; q = self.embebe_query(texto, nombre)
        params = faiss.SearchParameters(sel=faiss.IDSelectorBatch(cand.astype("int64"))) if cand is not None else None
        _, I = idx.search(q, min(self.prof, idx.ntotal), params=params)
        return [i for i in I[0] if i >= 0]

    def _rangos_bm25(self, texto, cand):
        s = self.bm25.scores(tokenize_simple(texto))
        if cand is not None:
            m = np.full(len(s), -np.inf); m[cand] = s[cand]; s = m
        orden = np.lexsort((np.arange(len(s)), -s))[: self.prof]
        return [i for i in orden if np.isfinite(s[i]) and s[i] > 0]

    def buscar(self, texto, k: int = 10, lang=None, modo: str = "hibrido", version: str = "prod"):
        t0 = time.perf_counter()
        nombre = self.alias.get(version, version)
        cand = np.flatnonzero(self.lang == lang) if lang else None
        listas = []
        if modo in ("denso", "hibrido"):
            listas.append(self._rangos_densos(texto, nombre, cand))
        if modo in ("bm25", "hibrido"):
            listas.append(self._rangos_bm25(texto, cand))
        score = {}
        for lst in listas:                       # RRF: sum 1/(k + rango), rango desde 1
            for r, i in enumerate(lst):
                score[i] = score.get(i, 0.0) + 1.0 / (self.rrf_k + r + 1)
        top = sorted(score, key=lambda i: (-score[i], i))[:k]
        self.lat_ms.append((time.perf_counter() - t0) * 1e3)
        return [(self.ids[i], round(score[i], 5)) for i in top]

    def metricas(self) -> dict:
        lat = np.array(self.lat_ms) if self.lat_ms else np.zeros(1)
        return {"n": len(self.lat_ms), "p50_ms": float(np.percentile(lat, 50)), "p99_ms": float(np.percentile(lat, 99)),
                "hit_rate": self.cache.hit_rate, "versiones": sorted(self.versiones), "alias": dict(self.alias)}
'''

CODE_ADAPTER = r'''
def ajusta_adaptador(A, B, lam: float = 0.1, metodo: str = "ridge"):
    """Aprende W (d_src x d_dst) con A @ W ≈ B a partir de PARES (mismo texto embebido con ambas versiones).
    ridge: W = (AᵀA + λI)⁻¹ AᵀB.  procrustes: W semi-ortogonal = U Vᵀ con U Σ Vᵀ = SVD(AᵀB) (conserva ángulos)."""
    A, B = np.asarray(A, np.float64), np.asarray(B, np.float64)
    if metodo == "ridge":
        return np.linalg.solve(A.T @ A + lam * np.eye(A.shape[1]), A.T @ B).astype(np.float32)
    U, _, Vt = np.linalg.svd(A.T @ B, full_matrices=False)
    return (U @ Vt).astype(np.float32)
'''

CODE_FASTAPI = r'''
# (Opcional) El mismo servicio detrás de una API HTTP con FastAPI. En Colab puedes servirlo con uvicorn + túnel;
# aquí lo probamos en proceso con TestClient (requiere httpx). Si falta alguna librería, la celda solo avisa.
try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from pydantic import BaseModel

    class Peticion(BaseModel):
        q: str
        k: int = 10
        lang: str | None = None
        modo: str = "hibrido"
        version: str = "prod"

    def crea_app(servicio) -> "FastAPI":
        app = FastAPI(title="Políglota Search")
        @app.get("/health")
        def health():
            return {"ok": True, "prod": servicio.alias.get("prod")}
        @app.post("/search")
        def search(p: Peticion):
            res = servicio.buscar(p.q, k=p.k, lang=p.lang, modo=p.modo, version=p.version)
            return {"version": servicio.alias.get(p.version, p.version), "results": [{"id": i, "score": s} for i, s in res]}
        @app.get("/metrics")
        def metrics():
            return servicio.metricas()
        return app
    FASTAPI_OK = True
except Exception as e:  # noqa: BLE001
    FASTAPI_OK = False
    print(f"⚠️ FastAPI/httpx no disponibles ({type(e).__name__}); celda opcional omitida.")
'''


def hint(n1: str, n2: str) -> str:
    return f"""
<details><summary>🪜 Pista 1 (la idea)</summary>

{n1}
</details>

<details><summary>🪜 Pista 2 (casi la API)</summary>

{n2}
</details>
"""


CODE_CORRE = r'''
def corre(f):
    """Ejecuta un chequeo sin romper 'ejecutar todo' si el TODO está pendiente."""
    try:
        r = f()
        print(r if r is not None else "✅ OK")
        return True
    except NotImplementedError as e:
        print(f"⏳ pendiente: {e}")
    except AssertionError as e:
        print(f"❌ falló: {e}")
    except Exception as e:  # noqa: BLE001
        print(f"❌ {type(e).__name__}: {e}")
    return False
'''
