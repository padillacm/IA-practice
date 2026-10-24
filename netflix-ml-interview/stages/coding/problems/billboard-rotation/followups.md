# Follow-ups: billboard rotation

1. **Data structure choice.** Why does this need two ordered collections (pending and served), in the original framing
   two tree maps? What does a heap with lazy deletion give up compared with a balanced tree (for example "peek the next
   three movies" or rank queries)?
2. **Concurrency.** Many request threads call `get()` while a feature job calls `update()`. Make the class thread-safe.
   Where is the critical section? Compare one coarse lock, a reader-writer lock and a copy-on-write snapshot for a
   cycle. What guarantee must hold under concurrent calls (a movie never returned twice in a cycle)?
3. **Per-member state at scale.** The billboard is personalized: 200M members each have their own cycle position. Where
   does cycle state live (client, session store, stateless via a deterministic seeded permutation)? How would you shard
   it, and what happens on a failover (a repeated movie is acceptable, a crash is not)?
4. **Parallel scoring updates.** Scores are refreshed by a batch job every hour for 100k movies: apply as a bulk swap
   vs incremental `update` calls. What changes in complexity and in the semantics of "the current cycle"?
5. **Fairness / exploration.** Strict descending order means low-score movies are shown last in every cycle. How would
   you add exploration (for example weighted sampling without replacement) while keeping each-once-per-cycle?
