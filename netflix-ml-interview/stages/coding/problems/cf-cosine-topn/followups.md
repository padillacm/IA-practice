# Follow-ups: CF with cosine on a sparse matrix

1. **Complexity.** State the cost of your solution in terms of the target's ratings, the length of the item posting
   lists and the number of neighbours. Which items (blockbusters rated by millions) dominate it, and how do you cap the
   posting lists (sample, drop top-popularity items, IDF weighting)?
2. **Item-based variant.** Precompute item-item similarities offline and serve with a lookup of the member's recent
   items. Compare memory, freshness and cold-start for new users and new titles.
3. **Scale and parallel computation.** 200M members x 20k titles. Shard the similarity computation (MinHash/LSH or
   blocked sparse matmul across parallel workers), keep top-k neighbours per user, and refresh daily. What is served online?
   How do you handle a worker failing in the middle of a block?
4. **Concurrency.** Ratings are updated while recommendations are served. Immutable snapshots vs locking the index;
   what staleness is acceptable?
5. **Normalization.** Mean-centering, implicit feedback (watch ratio), shrinkage for small overlaps. Why is raw cosine
   on positive ratings biased toward popular items, and how would you detect it offline?
6. **Evaluation.** How would you evaluate this offline without leakage (time-based split) and what online check would
   you want before shipping (interleaving then A/B)?
