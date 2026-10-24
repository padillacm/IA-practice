import math


def _check(k):
    if k <= 0:
        raise ValueError("k must be positive")


def precision_at_k(ranked, relevant, k):
    _check(k)
    return sum(1 for x in ranked[:k] if x in relevant) / k


def recall_at_k(ranked, relevant, k):
    _check(k)
    if not relevant:
        return 0.0
    return sum(1 for x in ranked[:k] if x in relevant) / len(relevant)


def _dcg(gs):
    return sum(g / math.log2(i + 2) for i, g in enumerate(gs))


def ndcg_at_k(ranked, gains, k):
    _check(k)
    ideal = _dcg(sorted(gains.values(), reverse=True)[:k])
    if ideal == 0:
        return 0.0
    return _dcg([gains.get(x, 0) for x in ranked[:k]]) / ideal


def mean_metric(metric, requests, **kwargs):
    if not requests:
        return 0.0
    return sum(metric(*r, **kwargs) for r in requests) / len(requests)
