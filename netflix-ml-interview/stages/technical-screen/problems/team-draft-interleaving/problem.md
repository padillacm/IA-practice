---
variant: ml-coding
roles: [mle]
levels: [L4, L5, L6]
title: Team-draft interleaving of two rankers
minutes: 40
---
# Team-draft interleaving of two rankers

To compare two rankers A and B cheaply, show each member one **interleaved** list and credit clicks to the ranker that
contributed the clicked item (team-draft interleaving).

Implement:

1. `team_draft(ranking_a, ranking_b, coins, k)` returning `(interleaved, attribution)`.
   - `ranking_a`, `ranking_b`: lists of item ids, best first.
   - `coins`: a list of 0/1 values, one per **round** (use `coins[round]`); 0 means A picks first in that round, 1 means B
     picks first. If there are more rounds than coins, raise `ValueError`.
   - In a round, the first team appends its highest-ranked item not already in `interleaved`, then the second team does the
     same. A team with no remaining item skips its pick.
   - Stop when `interleaved` has `k` items or both rankings are exhausted. `attribution` maps item -> `"A"` or `"B"`.
2. `score_clicks(clicked, attribution)` returning `{"A": n_a, "B": n_b}`: the number of clicked items attributed to each
   team (ignore clicked items that were not shown).
3. `winner(clicks_by_impression)`: given a list of `{"A": n, "B": n}` dicts (one per impression), return `"A"`, `"B"` or
   `"tie"` by the number of impressions each won (an impression with equal credit is a tie and counts for nobody).

Write your own tests. Why does the coin toss happen each round, and what bias would a fixed "A always first" cause?
