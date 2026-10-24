# Follow-ups: ranking metrics

1. **Edge semantics.** Empty relevant set: should recall be 0, undefined or excluded from the mean? What do
   you do in an offline evaluation report, and why does the choice move the average?
2. **Exponential gain.** Use `2**gain - 1` instead of linear gain. When does the choice change model rankings?
3. **Ties and duplicates.** The model returns duplicate ids or tied scores. How do ties make the metric
   non-deterministic, and how do you break them reproducibly?
4. **Scale.** 200M requests/day for daily evaluation: compute per request in a map step and aggregate (sum,
   count) in the reduce step; why is averaging averages across shards wrong when shard sizes differ? Vectorize the computation
   with numpy arrays and parallel workers; what is the memory bound per worker?
5. **Concurrency and streaming.** Metrics are updated live from impressions. Keep sums and counts in
   thread-safe or atomic counters; discuss lost updates and delayed labels (a click arrives minutes after the impression).
6. **Metric choice.** NDCG vs MAP vs MRR for a homepage with 2D layout (rows and columns) and position
   bias: what does the metric assume that the product violates? [judgment]
