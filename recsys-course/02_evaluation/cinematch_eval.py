"""cinematch_eval — evaluador offline de CineMatch (módulo 02 del curso).

Métricas implementadas desde cero y verificadas contra `ranx`.

Formato de entrada (convención de todo el curso):
    recs : dict[user_id -> list[item_id]]  ordenada (posición 0 = la mejor)
    test : pd.DataFrame con columnas user_id, item_id (+ opcional una columna de
           relevancia graduada, p. ej. "rating", vía rel_col)

Uso:
    from cinematch_eval import evaluate, evaluate_per_user, bootstrap_ci
    res = evaluate(recs, test, k=10)                       # dict métrica -> media
    res = evaluate(recs, test, k=10, train=train, items=items)  # + beyond-accuracy
    per_user = evaluate_per_user(recs, test, k=10)          # DataFrame (para tests)

Convenciones (¡importan al comparar con papers!):
  * Se promedia sobre TODOS los usuarios de `test`; un usuario sin recomendaciones
    cuenta como 0 (no se le "olvida").
  * precision@k divide por k aunque la lista sea más corta.
  * AP@k divide por |relevantes| (convención de ranx/trec_eval);
    con ap_denominator="min" divide por min(k, |relevantes|).
  * NDCG usa ganancia lineal rel/log2(pos+1) (ranx "ndcg"); con exp_gain=True usa
    2^rel - 1 (ranx "ndcg_burges"). Con relevancia binaria ambas coinciden.
  * Evaluación full-ranking (contra todo el catálogo). Nada de sampled metrics.
"""
from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd

DEFAULT_METRICS = ("precision", "recall", "hit_rate", "mrr", "map", "ndcg")


# ----------------------------------------------------------------------------
# Métricas por usuario (una lista recomendada vs un conjunto relevante)
# ----------------------------------------------------------------------------
def precision_at_k(rec: list, rel: set, k: int) -> float:
    return sum(1 for i in rec[:k] if i in rel) / k


def recall_at_k(rec: list, rel: set, k: int) -> float:
    if not rel:
        return 0.0
    return sum(1 for i in rec[:k] if i in rel) / len(rel)


def hit_rate_at_k(rec: list, rel: set, k: int) -> float:
    return float(any(i in rel for i in rec[:k]))


def mrr_at_k(rec: list, rel: set, k: int) -> float:
    for pos, i in enumerate(rec[:k], start=1):
        if i in rel:
            return 1.0 / pos
    return 0.0


def average_precision_at_k(rec: list, rel: set, k: int, denominator: str = "rel") -> float:
    if not rel:
        return 0.0
    hits, s = 0, 0.0
    for pos, i in enumerate(rec[:k], start=1):
        if i in rel:
            hits += 1
            s += hits / pos
    denom = len(rel) if denominator == "rel" else min(k, len(rel))
    return s / denom


def ndcg_at_k(rec: list, rel, k: int, exp_gain: bool = False) -> float:
    """rel: set (binaria) o dict item -> relevancia graduada."""
    gains = rel if isinstance(rel, dict) else {i: 1.0 for i in rel}
    if not gains:
        return 0.0
    g = (lambda x: 2.0 ** x - 1.0) if exp_gain else (lambda x: float(x))
    dcg = sum(g(gains.get(i, 0.0)) / np.log2(pos + 1) for pos, i in enumerate(rec[:k], start=1))
    ideal = sorted(gains.values(), reverse=True)[:k]
    idcg = sum(g(x) / np.log2(pos + 1) for pos, x in enumerate(ideal, start=1))
    return dcg / idcg if idcg > 0 else 0.0


_METRIC_FNS = {
    "precision": precision_at_k,
    "recall": recall_at_k,
    "hit_rate": hit_rate_at_k,
    "mrr": mrr_at_k,
    "map": average_precision_at_k,
    "ndcg": ndcg_at_k,
}


# ----------------------------------------------------------------------------
# Métricas de predicción de rating (explícito)
# ----------------------------------------------------------------------------
def rmse(y_true, y_pred) -> float:
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def mae(y_true, y_pred) -> float:
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    return float(np.mean(np.abs(y_true - y_pred)))


def auc_score(labels, scores) -> float:
    """AUC = P(score positivo > score negativo), empates cuentan 0.5 (Mann-Whitney)."""
    labels, scores = np.asarray(labels).astype(bool), np.asarray(scores, float)
    n_pos, n_neg = labels.sum(), (~labels).sum()
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    ranks = pd.Series(scores).rank(method="average").to_numpy()
    return float((ranks[labels].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def gauc(df: pd.DataFrame, user_col: str = "user_id", label_col: str = "label",
         score_col: str = "score") -> float:
    """Group AUC (Alibaba): AUC por usuario ponderada por nº de impresiones.
    Usuarios con solo positivos o solo negativos se ignoran."""
    num, den = 0.0, 0
    for _, g in df.groupby(user_col):
        a = auc_score(g[label_col].to_numpy(), g[score_col].to_numpy())
        if not np.isnan(a):
            num += a * len(g)
            den += len(g)
    return num / den if den else float("nan")


# ----------------------------------------------------------------------------
# Agregación
# ----------------------------------------------------------------------------
def _relevance(test: pd.DataFrame, rel_col: str | None) -> dict:
    if rel_col is None:
        return test.groupby("user_id")["item_id"].agg(set).to_dict()
    return {u: dict(zip(g["item_id"], g[rel_col])) for u, g in test.groupby("user_id")}


def evaluate_per_user(recs: dict, test: pd.DataFrame, k: int = 10,
                      metrics=DEFAULT_METRICS, rel_col: str | None = None,
                      exp_gain: bool = False, ap_denominator: str = "rel") -> pd.DataFrame:
    """DataFrame (índice user_id) con una columna por métrica, p. ej. 'ndcg@10'.
    rel_col: columna de relevancia graduada (solo afecta a NDCG; el resto usa
    como relevantes los ítems con rel > 0)."""
    rel = _relevance(test, rel_col)
    rows = {}
    for u, r in rel.items():
        rec = list(recs.get(u, []))
        rel_set = {i for i, v in r.items() if v > 0} if isinstance(r, dict) else r
        row = {}
        for m in metrics:
            if m == "ndcg":
                row[f"ndcg@{k}"] = ndcg_at_k(rec, r, k, exp_gain)
            elif m == "map":
                row[f"map@{k}"] = average_precision_at_k(rec, rel_set, k, ap_denominator)
            else:
                row[f"{m}@{k}"] = _METRIC_FNS[m](rec, rel_set, k)
        rows[u] = row
    out = pd.DataFrame.from_dict(rows, orient="index")
    out.index.name = "user_id"
    return out


# ----------------------------------------------------------------------------
# Beyond-accuracy
# ----------------------------------------------------------------------------
def catalog_coverage(recs: dict, catalog, k: int = 10) -> float:
    """Fracción del catálogo que aparece en al menos una lista top-k."""
    shown = {i for rec in recs.values() for i in rec[:k]}
    catalog = set(catalog)
    return len(shown & catalog) / len(catalog)


def gini_index(recs: dict, catalog, k: int = 10) -> float:
    """Gini de la exposición de ítems (0 = exposición uniforme, 1 = todo a un ítem)."""
    cnt = Counter(i for rec in recs.values() for i in rec[:k])
    x = np.sort(np.array([cnt.get(i, 0) for i in set(catalog)], float))
    n = len(x)
    if x.sum() == 0:
        return 0.0
    return float((2 * np.arange(1, n + 1) - n - 1) @ x / (n * x.sum()))


def novelty(recs: dict, train: pd.DataFrame, k: int = 10) -> float:
    """Autoinformación media -log2 p(i), p(i) = fracción de usuarios de train que vieron i.
    Más alta = recomiendas cosas menos conocidas."""
    n_users = train["user_id"].nunique()
    p = train.groupby("item_id")["user_id"].nunique() / n_users
    vals = [-np.log2(p.get(i, 1.0 / n_users)) for rec in recs.values() for i in rec[:k]]
    return float(np.mean(vals)) if vals else 0.0


def _genre_matrix(items: pd.DataFrame) -> pd.DataFrame:
    return items.set_index("item_id")["genres"].str.get_dummies(sep="|").astype(float)


def intra_list_diversity(recs: dict, items: pd.DataFrame, k: int = 10) -> float:
    """ILD: media de (1 - coseno) entre pares de ítems de cada lista (vectores de género)."""
    G = _genre_matrix(items)
    G = G.div(np.linalg.norm(G.values, axis=1).clip(1e-12), axis=0)
    vals = []
    for rec in recs.values():
        rec = [i for i in rec[:k] if i in G.index]
        if len(rec) < 2:
            continue
        V = G.loc[rec].values
        S = V @ V.T
        n = len(rec)
        vals.append(1 - (S.sum() - np.trace(S)) / (n * (n - 1)))
    return float(np.mean(vals)) if vals else 0.0


def miscalibration_kl(recs: dict, train: pd.DataFrame, items: pd.DataFrame,
                      k: int = 10, alpha: float = 0.01) -> float:
    """Miscalibración de Steck (2018): KL(p || q~) entre la distribución de géneros
    del historial (p) y la de la lista recomendada (q), q~ = (1-a) q + a p."""
    G = _genre_matrix(items)
    G = G.div(G.sum(axis=1).clip(1e-12), axis=0)  # cada película reparte 1 entre sus géneros
    hist = train.groupby("user_id")["item_id"].agg(list).to_dict()
    vals = []
    for u, rec in recs.items():
        h = [i for i in hist.get(u, []) if i in G.index]
        rec = [i for i in rec[:k] if i in G.index]
        if not h or not rec:
            continue
        p = G.loc[h].values.mean(0)
        q = (1 - alpha) * G.loc[rec].values.mean(0) + alpha * p
        m = p > 0
        vals.append(float(np.sum(p[m] * np.log(p[m] / q[m]))))
    return float(np.mean(vals)) if vals else 0.0


def evaluate(recs: dict, test: pd.DataFrame, k: int = 10, metrics=DEFAULT_METRICS,
             rel_col: str | None = None, train: pd.DataFrame | None = None,
             items: pd.DataFrame | None = None, **kw) -> dict:
    """Media de cada métrica sobre los usuarios de test. Si se pasan `train`
    (y opcionalmente `items` con columna genres) añade métricas beyond-accuracy."""
    res = evaluate_per_user(recs, test, k, metrics, rel_col, **kw).mean().to_dict()
    test_recs = {u: recs.get(u, []) for u in test["user_id"].unique()}
    if train is not None:
        catalog = train["item_id"].unique()
        res[f"coverage@{k}"] = catalog_coverage(test_recs, catalog, k)
        res[f"gini@{k}"] = gini_index(test_recs, catalog, k)
        res[f"novelty@{k}"] = novelty(test_recs, train, k)
        if items is not None:
            res[f"ild@{k}"] = intra_list_diversity(test_recs, items, k)
            res[f"miscal_kl@{k}"] = miscalibration_kl(test_recs, train, items, k)
    return {m: float(v) for m, v in res.items()}


# ----------------------------------------------------------------------------
# Incertidumbre y significancia
# ----------------------------------------------------------------------------
def bootstrap_ci(values, n_boot: int = 2000, alpha: float = 0.05, seed: int = 42
                 ) -> tuple[float, float, float]:
    """(media, límite inferior, límite superior) por bootstrap percentil sobre usuarios."""
    v = np.asarray(values, float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(v), (n_boot, len(v)))
    means = v[idx].mean(1)
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return float(v.mean()), float(lo), float(hi)


def paired_bootstrap_test(a, b, n_boot: int = 10_000, seed: int = 42) -> dict:
    """Test pareado (mismos usuarios) de H0: media(a - b) = 0.
    Devuelve diferencia media, IC 95 % y p-valor bilateral."""
    d = np.asarray(a, float) - np.asarray(b, float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), (n_boot, len(d)))
    boot = d[idx].mean(1)
    centered = boot - d.mean()  # distribución bajo H0
    p = float(np.mean(np.abs(centered) >= abs(d.mean())))
    lo, hi = np.quantile(boot, [0.025, 0.975])
    return {"diff": float(d.mean()), "ci_low": float(lo), "ci_high": float(hi), "p_value": p}


# ----------------------------------------------------------------------------
# Puente con ranx (verificación)
# ----------------------------------------------------------------------------
def to_ranx(recs: dict, test: pd.DataFrame, rel_col: str | None = None):
    """Convierte (recs, test) a (Qrels, Run) de ranx. El score es decreciente con
    la posición para que ranx reproduzca exactamente nuestro orden."""
    from ranx import Qrels, Run
    rel = _relevance(test, rel_col)
    qrels = {str(u): ({str(i): int(v) for i, v in r.items()} if isinstance(r, dict)
                      else {str(i): 1 for i in r}) for u, r in rel.items()}
    run = {}
    for u in rel:
        rec = list(recs.get(u, []))
        # ranx no admite consultas vacías: un ítem centinela inexistente con score 0
        run[str(u)] = {str(i): float(len(rec) - p) for p, i in enumerate(rec)} or {"__none__": 0.0}
    return Qrels(qrels), Run(run)
