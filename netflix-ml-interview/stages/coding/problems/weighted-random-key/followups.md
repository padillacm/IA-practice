# Follow-ups: weighted random key

1. **Static fast path.** With no updates, prefix sums plus `bisect` give O(log n) picks and O(n) build. Where is the
   crossover with a Fenwick tree if updates are 1% of operations?
2. **Alias method.** O(1) sampling with O(n) build (Walker/Vose). When is it worth it, and why does it not support
   cheap updates? [tradeoff]
3. **Without replacement.** Sample k distinct titles proportional to weight (Efraimidis-Spirakis keys `u ** (1 / w)`,
   or repeated draws with zeroing). Complexity?
4. **Concurrency and scale.** 50 request threads call `pick` while a weights refresher calls `update` for 1M keys.
   Options: lock, versioned immutable snapshot swapped atomically, per-shard samplers merged by shard weight. What do you
   choose and why does the snapshot approach make `pick` lock-free? How would you run this across many parallel servers
   while keeping the sampled distribution unbiased?
5. **Testing randomness.** How do the injected `u`, a uniform grid and a chi-square test on a seeded generator each help?
   What flakiness would an unseeded statistical test introduce in CI?
6. **Numerical issues.** Float weights spanning 1e-9 to 1e9; accumulated Fenwick error after millions of updates.
   Mitigations (periodic rebuild, integer weights).
