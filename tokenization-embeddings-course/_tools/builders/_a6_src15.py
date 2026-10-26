"""Fuentes de código del módulo 15 (métricas canónicas, estadística, retrievers de referencia).

Se incrustan en celdas de la lección/proyecto Y se vuelcan a `15_evaluacion_retrieval/poliglota_eval.py`
(módulo canónico de evaluación del curso). Convenciones idénticas a trec_eval / ranx / pytrec_eval.
"""

METRICS_SRC = r'''
import math
import numpy as np

def _dedup(ranked_ids):
    """Conserva la primera aparición: un doc repetido NO puntúa dos veces."""
    seen, out = set(), []
    for d in ranked_ids:
        if d not in seen:
            seen.add(d); out.append(d)
    return out

def _gain(r: float, exp_gain: bool) -> float:
    return (2.0 ** r - 1.0) if exp_gain else float(r)

def dcg_at_k(ranked_ids, rels: dict, k: int = 10, exp_gain: bool = False) -> float:
    """DCG@k = sum_i gain(rel_i) / log2(i+1), i = 1..k. rels: doc_id -> relevancia (>0 relevante; ausente = 0)."""
    return sum(_gain(rels.get(d, 0), exp_gain) / math.log2(i + 2)
               for i, d in enumerate(_dedup(ranked_ids)[:k]) if rels.get(d, 0) > 0)

def ndcg_at_k(ranked_ids, rels: dict, k: int = 10, exp_gain: bool = False) -> float:
    """nDCG@k = DCG@k / IDCG@k. IDCG usa los mejores k de TODOS los juzgados. Sin relevantes -> 0.0 (convención)."""
    ideal = sorted((r for r in rels.values() if r > 0), reverse=True)[:k]
    idcg = sum(_gain(r, exp_gain) / math.log2(i + 2) for i, r in enumerate(ideal))
    return 0.0 if idcg == 0 else dcg_at_k(ranked_ids, rels, k, exp_gain) / idcg

def recall_at_k(ranked_ids, rels: dict, k: int = 10) -> float:
    """|relevantes en top-k| / |relevantes|. Sin relevantes -> 0.0."""
    relevant = {d for d, r in rels.items() if r > 0}
    return len(relevant & set(_dedup(ranked_ids)[:k])) / len(relevant) if relevant else 0.0

def mrr_at_k(ranked_ids, rels: dict, k: int = 10) -> float:
    """1/rango del primer relevante dentro del top-k; 0 si no hay ninguno."""
    for i, d in enumerate(_dedup(ranked_ids)[:k]):
        if rels.get(d, 0) > 0:
            return 1.0 / (i + 1)
    return 0.0

def precision_at_k(ranked_ids, rels: dict, k: int = 10) -> float:
    """Divide SIEMPRE por k (como trec_eval), aunque la lista sea más corta."""
    return sum(rels.get(d, 0) > 0 for d in _dedup(ranked_ids)[:k]) / k

def rank_from_scores(scores, doc_ids, k=None):
    """Orden por score desc; empates -> orden del corpus (determinista). Sin esto, 'argsort' decide por ti."""
    scores = np.asarray(scores, dtype=float)
    order = np.lexsort((np.arange(len(scores)), -scores))
    return [doc_ids[i] for i in (order[:k] if k else order)]

METRICS = {"ndcg": ndcg_at_k, "recall": recall_at_k, "mrr": mrr_at_k, "precision": precision_at_k}

def evaluate_per_query(run: dict, qrels: dict, k: int = 10, metrics=("ndcg", "recall", "mrr")) -> dict:
    """run: {qid: [doc_id ordenados]}. Devuelve {"qids": [...], metric: np.ndarray}. Excluye queries sin relevantes
    (convención trec_eval); una query sin ranking en `run` puntúa 0 (NO se descarta: sería hacer trampa)."""
    qids = [q for q, rels in qrels.items() if any(r > 0 for r in rels.values())]
    out = {"qids": qids}
    for m in metrics:
        out[m] = np.array([METRICS[m](run.get(q, []), qrels[q], k) for q in qids])
    return out

def evaluate(run: dict, qrels: dict, k: int = 10) -> dict:
    per = evaluate_per_query(run, qrels, k)
    return {f"{m}@{k}": float(per[m].mean()) for m in ("ndcg", "recall", "mrr")} | {"n_queries": len(per["qids"])}
'''.strip("\n")

STATS_SRC = r'''
def bootstrap_ci(values, n_boot: int = 2000, alpha: float = 0.05, seed: int = 42):
    """IC percentil de la media remuestreando QUERIES (la unidad de muestreo es la query, no el par query-doc)."""
    v = np.asarray(values, dtype=float)
    idx = np.random.default_rng(seed).integers(0, len(v), size=(n_boot, len(v)))
    means = v[idx].mean(axis=1)
    return float(v.mean()), float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2))

def paired_bootstrap(a, b, n_boot: int = 10000, alpha: float = 0.05, seed: int = 42) -> dict:
    """Test pareado A vs B sobre las MISMAS queries. IC percentil de la diferencia media y p-valor bilateral
    por 'shift' (se centra la diferencia en 0 bajo H0 y se cuenta cuántas veces el remuestreo supera lo observado)."""
    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(n_boot, len(d)))
    means = d[idx].mean(axis=1)
    null = (d - d.mean())[idx].mean(axis=1)
    p = (np.sum(np.abs(null) >= abs(d.mean())) + 1) / (n_boot + 1)
    return {"diff": float(d.mean()), "ci_low": float(np.quantile(means, alpha / 2)),
            "ci_high": float(np.quantile(means, 1 - alpha / 2)), "p_value": float(p)}

def paired_permutation(a, b, n_perm: int = 10000, seed: int = 42) -> float:
    """Test de aleatorización pareado (sign-flip): bajo H0 el signo de cada diferencia por query es intercambiable."""
    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    signs = np.random.default_rng(seed).choice([-1.0, 1.0], size=(n_perm, len(d)))
    stat = np.abs((signs * d).mean(axis=1))
    return float((np.sum(stat >= abs(d.mean()) - 1e-12) + 1) / (n_perm + 1))

def holm(pvalues: dict, alpha: float = 0.05) -> dict:
    """Corrección de Holm-Bonferroni para comparaciones múltiples. Devuelve {nombre: (p_ajustado, rechaza_H0)}."""
    items = sorted(pvalues.items(), key=lambda kv: kv[1])
    m, out, running = len(items), {}, 0.0
    for i, (name, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[name] = (running, running < alpha)
    return out
'''.strip("\n")

RETRIEVERS_SRC = r'''
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.decomposition import TruncatedSVD

def tok_simple(text: str) -> list[str]:
    """Token léxico: minúsculas + regex de palabras (snake_case queda como UN solo token; lo veremos fallar en código)."""
    return re.findall(r"\w+", text.lower())

def tok_code(text: str) -> list[str]:
    """Igual, pero parte snake_case y camelCase (set_ttl -> set, ttl). Es tokenización con criterio de dominio."""
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text).replace("_", " ")
    return re.findall(r"[^\W_]+", text.lower())

class BM25:
    """BM25 (Robertson/Lucene idf) con matriz dispersa. k1=1.2, b=0.75."""
    def __init__(self, tokenizer=tok_simple, k1=1.2, b=0.75):
        self.tok, self.k1, self.b = tokenizer, k1, b
    def fit(self, texts, ids):
        self.ids = list(ids)
        self.cv = CountVectorizer(tokenizer=self.tok, lowercase=False, token_pattern=None)
        X = self.cv.fit_transform(texts).tocsr().astype(float)
        self.N = X.shape[0]; self.dl = np.asarray(X.sum(1)).ravel(); self.avg = self.dl.mean()
        df = np.asarray((X > 0).sum(0)).ravel()
        self.idf = np.log(1 + (self.N - df + 0.5) / (df + 0.5))
        self.X = X.tocsc()
        return self
    def scores(self, query: str) -> np.ndarray:
        s = np.zeros(self.N)
        for j in set(self.cv.transform([query]).indices):
            col = self.X[:, j].toarray().ravel()
            s += self.idf[j] * col * (self.k1 + 1) / (col + self.k1 * (1 - self.b + self.b * self.dl / self.avg))
        return s

class LSI:
    """Retriever 'denso' sin descargas: TF-IDF sublineal + SVD truncada (LSA) + coseno. Hace de embedder de CPU."""
    def __init__(self, dim=48, seed=42):
        self.dim, self.seed = dim, seed
    def fit(self, texts, ids):
        self.ids = list(ids)
        self.tf = TfidfVectorizer(sublinear_tf=True)
        T = self.tf.fit_transform(texts)
        self.svd = TruncatedSVD(min(self.dim, T.shape[1] - 1), random_state=self.seed)
        self.Z = self._norm(self.svd.fit_transform(T))
        return self
    @staticmethod
    def _norm(Z): return Z / (np.linalg.norm(Z, axis=1, keepdims=True) + 1e-9)
    def scores(self, query: str) -> np.ndarray:
        return self.Z @ self._norm(self.svd.transform(self.tf.transform([query])))[0]

def rrf_scores(score_lists, k: int = 60) -> np.ndarray:
    """Reciprocal Rank Fusion: sum 1/(k + rango). Ignora la escala de cada score (ventaja y límite)."""
    out = np.zeros(len(score_lists[0]))
    for s in score_lists:
        order = np.lexsort((np.arange(len(s)), -np.asarray(s)))
        out[order] += 1.0 / (k + np.arange(len(s)) + 1)
    return out

def build_run(scorer, queries, doc_ids, topn: int = 100) -> dict:
    """scorer(texto_query) -> vector de scores alineado con doc_ids. Devuelve run {qid: [doc_ids top-n]}."""
    return {q["qid"]: rank_from_scores(scorer(q["text"]), doc_ids, topn) for q in queries}
'''.strip("\n")

# Módulo .py canónico que se escribe junto al notebook (para que otros módulos puedan hacer wget)
EVAL_MODULE_HEADER = '''"""poliglota_eval.py · Evaluación canónica de retrieval del curso «Tokenización y Embeddings» (módulo 15).

Convenciones idénticas a trec_eval / ranx: queries sin relevantes se excluyen; query sin ranking = 0; nDCG con ganancia
lineal por defecto (exp_gain=True -> 2^rel - 1); duplicados cuentan una vez; empates -> orden del corpus.
Generado por tokenization-embeddings-course/_tools/builders/build_15.py (NO editar a mano).
"""
'''
