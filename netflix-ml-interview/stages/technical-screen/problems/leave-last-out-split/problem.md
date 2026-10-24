---
variant: ml-framing-coding
roles: [rs]
levels: [L4, L5, L6]
title: Leave-last-out evaluation split for recommenders
minutes: 25
---
# Leave-last-out evaluation split

Interactions are `(user, item, ts)` tuples in arbitrary order. Implement a time-aware split for offline evaluation:

1. `leave_last_out(interactions, min_history=3)` returns `(train, test)`:
   - For each user with at least `min_history` interactions, the interaction with the **largest `ts`** (ties: the one that
     appears last in the input) goes to `test`, a dict `user -> item`; all their other interactions are in `train`.
   - Users with fewer than `min_history` interactions contribute everything to `train` and nothing to `test`.
   - `train` is a list that keeps the input order. No leakage: no test interaction may appear in `train`.
2. `hit_rate_at_k(recommendations, test, k)`: `recommendations` maps user -> ranked list of items; returns the fraction of
   test users whose held-out item is in the first `k` recommendations (a user with no recommendations is a miss;
   0.0 if `test` is empty).
3. `unseen_only(recommendations, train)`: remove from each user's list the items the user already has in `train`, keeping
   order. Explain why evaluation lists should do this.

Write your own tests. State what the split assumes about the world and what a random split would do instead.
