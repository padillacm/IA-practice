import math


def hit_rate_at_k(relevances, k):
    """1.0 if any of the first k items is relevant (relevance > 0), else 0.0."""
    return 1.0 if any(r > 0 for r in relevances[:k]) else 0.0


def dcg_at_k(relevances, k):
    return sum((2 ** r - 1) / math.log2(i + 2) for i, r in enumerate(relevances[:k]))


def ndcg_at_k(relevances, k, ideal=None):
    """NDCG@k of a ranked relevance list.

    `ideal` is the list of ALL relevances available for the request (ideal ranking is its descending
    sort); defaults to `relevances` itself. Returns 0.0 when there is nothing relevant.
    """
    best = dcg_at_k(sorted(ideal if ideal is not None else relevances, reverse=True), k)
    if best == 0:
        return 0.0
    return dcg_at_k(relevances, k) / best
