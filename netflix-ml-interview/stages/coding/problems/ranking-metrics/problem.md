---
variant: practical
roles: [mle, rs, ds]
levels: [L4, L5, L6]
title: Ranking metrics P@K, recall@K and NDCG@K
minutes: 30
---
# Ranking metrics: P@K, Recall@K, NDCG@K

Implement offline ranking metrics for one request (one member's ranked list):

- `precision_at_k(ranked, relevant, k)`: `ranked` is a list of item ids (best first, no duplicates), `relevant` a set of
  relevant ids. Precision is hits in the top `k` divided by `k` (even if `ranked` is shorter than `k`).
- `recall_at_k(ranked, relevant, k)`: hits in the top `k` divided by `len(relevant)`; 0.0 if `relevant` is empty.
- `ndcg_at_k(ranked, gains, k)`: `gains` is a dict `item -> non-negative gain` (missing items have gain 0).
  `DCG@k = sum(gain_i / log2(i + 2))` for the 0-based position `i < k`; `IDCG@k` is the DCG of the ideal ordering of
  all gains in `gains`. Return `DCG / IDCG`, or 0.0 if `IDCG == 0`.
- `mean_metric(metric, requests, **kwargs)`: average of `metric(*request, **kwargs)` over `requests` (a list of argument
  tuples); 0.0 for an empty list.

`k <= 0` raises `ValueError`. Write your own tests, including hand-computed cases.
