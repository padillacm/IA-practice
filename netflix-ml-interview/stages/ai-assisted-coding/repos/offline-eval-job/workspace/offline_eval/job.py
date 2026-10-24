"""Offline evaluation: logged ranking vs popularity baseline on a time-based holdout.

run_eval(rows, cutoff_ts, k) -> {"requests", "logged": {"ndcg", "hit_rate"}, "baseline": {...}}
Metrics are macro-averaged over evaluation requests. A request counts only if it has at least one click.
"""
from .baseline import popularity_counts, popularity_ranking
from .data import dedupe_impressions, group_slates, split_by_time
from .metrics import hit_rate_at_k, ndcg_at_k


def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def run_eval(rows, cutoff_ts, k=10):
    rows = dedupe_impressions(rows)
    history, evaluation = split_by_time(rows, cutoff_ts)
    counts = popularity_counts(history, cutoff_ts)
    logged_ndcg, logged_hit, base_ndcg, base_hit = [], [], [], []
    for slate in group_slates(evaluation).values():
        if not any(r.clicked for r in slate):
            continue
        rel_by_item = {r.item_id: 1 if r.clicked else 0 for r in slate}
        logged = [rel_by_item[r.item_id] for r in slate]
        ranked = popularity_ranking(counts, [r.item_id for r in slate])
        base = [rel_by_item[i] for i in ranked]
        all_rel = list(rel_by_item.values())
        logged_ndcg.append(ndcg_at_k(logged, k, ideal=all_rel))
        logged_hit.append(hit_rate_at_k(logged, k))
        base_ndcg.append(ndcg_at_k(base, k, ideal=all_rel))
        base_hit.append(hit_rate_at_k(base, k))
    return {
        "requests": len(logged_ndcg),
        "logged": {"ndcg": _mean(logged_ndcg), "hit_rate": _mean(logged_hit)},
        "baseline": {"ndcg": _mean(base_ndcg), "hit_rate": _mean(base_hit)},
    }
