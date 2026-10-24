# Follow-ups: homepage row deduplication

Progressive; ask only as time allows. Signals in brackets.

1. **Per-row n.** `n` becomes a list (visible slots differ per row: a carousel on TV shows 6, on mobile 3). How does the
   code change? [clean generalization, does not copy-paste]
2. **Exempt rows.** Some rows (for example "Continue Watching" or a pinned billboard) must never lose items and must not
   hide titles from other rows. Add `exempt=set_of_row_indexes`. Which titles do exempt rows contribute to `visible`?
   Ask the candidate to state the product decision before coding. [requirements clarification]
3. **Scale.** 200 rows x 75 titles per row is trivial; now dedupe 50 million profile pages per hour. Where does the work
   run (per request vs precomputed)? Is the algorithm O(total items)? What if candidate generators are slow and rows
   arrive out of order (concurrency: rows produced by parallel threads/services)? Discuss a deterministic merge order
   and why dedup should be applied after row ranking, not inside each generator.
4. **Quality, not only correctness.** Dropping a title from a row can leave it short. Fallback: backfill from the row's
   candidate pool instead of shrinking. What changes in the algorithm? [lazy iterators over the pool]
5. **Concurrency.** Two threads dedup different users' pages with a shared cache of "seen titles". What is shared state
   here, and why should it be per-request?
