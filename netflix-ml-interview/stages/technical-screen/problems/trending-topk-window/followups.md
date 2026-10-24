# Follow-ups: trending titles in a window

1. **Cost of `top_k`.** Counting is O(1) per event but `top_k` is O(m log k) over active titles. When k is small and the
   catalog large, maintain a heap with lazy deletion or bucketed counts. What do you give up?
2. **Scale.** 2M plays per second worldwide. Keep tumbling one-minute buckets of counts per region, merge the last N
   buckets for the window, and merge regional top-k lists (approximate: Space-Saving / Count-Min sketch). What error
   does merging local top-k introduce?
3. **Concurrency.** Many ingest threads call `record` while serving threads call `top_k`. Compare a single lock, striped
   locks per title, per-thread buffers merged periodically, and publishing an immutable snapshot every second.
4. **Late data and replays.** Events arrive up to a minute late and Kafka replays duplicates. Event-time vs
   processing-time windows; deduplicate by play id.
5. **Product quality.** Raw counts favor already-popular titles. How would you rank "trending" (velocity vs baseline,
   z-score of the last hour against the last week)?
