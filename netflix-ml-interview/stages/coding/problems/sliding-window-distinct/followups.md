# Follow-ups: sliding window of distinct titles

1. **Unsorted / late events.** Events arrive up to 30 s late. What changes (watermark, buffer, drop or correct)? Does the
   deque still work? [event-time thinking]
2. **Scale.** 1M events/s across 50M members. Partition by member id, keep one small window per member in a keyed state
   store; discuss state size, TTL for idle members and checkpointing in a stream processor. What do you do about a hot
   member (bot with 100k events per window)?
3. **Approximate distinct counts.** When exact per-window sets are too big, use HyperLogLog. Why is HLL awkward for
   expiring items (sliding HLL, or tumbling sub-windows merged)? What is the error?
4. **Concurrency.** The log is consumed by several threads, each handling a partition of members. Which structures are
   shared? Where could two threads touch the same member (rebalancing) and how do you avoid it?
5. **Batch vs streaming parity.** The same feature is computed offline in SQL over historical data. List three
   semantic differences that cause training/serving skew (window boundary inclusion, late data, time zone/event time).
6. **Variant.** "Max distinct in any window of length w" without per-event output; "k most frequent titles in the
   window" (heap with lazy deletion).
