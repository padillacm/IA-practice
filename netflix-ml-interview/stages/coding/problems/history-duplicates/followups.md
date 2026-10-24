# Follow-ups: duplicates in viewing history

1. **Memory.** Part 1 with a history of 10 billion events that does not fit in memory: sort-based (external) approach vs
   hash partitioning by title id; a Bloom filter as a pre-filter and what false positives cost. [scale]
2. **Streaming.** Records arrive one by one; implement `DuplicateDetector.add(x)` with O(1) amortized time for part 2.
   Why is a fixed-size window a deque plus a counter, and what breaks if records arrive out of order?
3. **Scale and parallel workers.** Part 3 over 300M members: partition by member id (no cross-member comparisons), run in
   parallel workers, and discuss skew for members with huge histories. What changes if the same title is replayed across
   devices that report to different shards (concurrency in ingestion)?
4. **Why bucketing is correct.** Ask for the argument: with width t+1, two values in the same bucket are within t, and
   only adjacent buckets can hold a match. Why do we need to keep at most one value per bucket inside the window?
5. **Product.** Duplicates may be legitimate (rewatching). How would the detector change if the question were "was this
   a double-logged event" vs "is this a rewatch"? [judgment]
