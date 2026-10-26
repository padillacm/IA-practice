# ── Métricas de retrieval canónicas de Políglota (módulo 00) ──────────────────
import math

import numpy as np


def _dedup(ranked_ids):
    """Quita duplicados conservando la primera aparición (un doc repetido NO puntúa dos veces)."""
    seen, out = set(), []
    for d in ranked_ids:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out


def dcg_at_k(ranked_ids, rels: dict, k: int = 10) -> float:
    """DCG con ganancia lineal (como trec_eval / pytrec_eval, que usa BEIR/MTEB) y descuento 1/log2(rango+1)."""
    ranked = _dedup(ranked_ids)[:k]
    return sum(rels.get(d, 0) / math.log2(i + 2) for i, d in enumerate(ranked) if rels.get(d, 0) > 0)


def ndcg_at_k(ranked_ids, rels: dict, k: int = 10) -> float:
    """nDCG@k. rels: doc_id -> relevancia (>0 relevante). Sin relevantes -> 0.0 (evaluate() las excluye)."""
    ideal = sorted((r for r in rels.values() if r > 0), reverse=True)[:k]
    idcg = sum(r / math.log2(i + 2) for i, r in enumerate(ideal))
    return 0.0 if idcg == 0 else dcg_at_k(ranked_ids, rels, k) / idcg


def recall_at_k(ranked_ids, rels: dict, k: int = 10) -> float:
    """Fracción de los documentos relevantes que aparecen en el top-k."""
    relevant = {d for d, r in rels.items() if r > 0}
    if not relevant:
        return 0.0
    return len(relevant & set(_dedup(ranked_ids)[:k])) / len(relevant)


def mrr_at_k(ranked_ids, rels: dict, k: int = 10) -> float:
    """1/rango del primer relevante dentro del top-k (0 si no hay ninguno)."""
    for i, d in enumerate(_dedup(ranked_ids)[:k]):
        if rels.get(d, 0) > 0:
            return 1.0 / (i + 1)
    return 0.0


def rank_from_scores(scores, doc_ids, k: int | None = None):
    """Ordena por score desc. Empates -> orden original del corpus (determinista). Los empates son una fuente
    silenciosa de varianza: con scores iguales, el orden de entrada decidiría el resultado."""
    scores = np.asarray(scores, dtype=float)
    order = np.lexsort((np.arange(len(scores)), -scores))
    order = order[:k] if k else order
    return [doc_ids[i] for i in order]


def evaluate(run: dict, qrels: dict, k: int = 10) -> dict:
    """run: {qid: [doc_id ordenados]}. Promedia solo sobre queries con algún relevante (convención trec_eval)."""
    n, tot = 0, {"ndcg": 0.0, "recall": 0.0, "mrr": 0.0}
    for qid, rels in qrels.items():
        if not any(r > 0 for r in rels.values()):
            continue
        ranked = run.get(qid, [])
        tot["ndcg"] += ndcg_at_k(ranked, rels, k)
        tot["recall"] += recall_at_k(ranked, rels, k)
        tot["mrr"] += mrr_at_k(ranked, rels, k)
        n += 1
    out = {m: (v / n if n else 0.0) for m, v in tot.items()}
    out.update(n_queries=n, n_skipped=len(qrels) - n)
    return out
