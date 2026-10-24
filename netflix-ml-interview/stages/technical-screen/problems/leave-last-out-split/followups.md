# Follow-ups: leave-last-out split

1. **Global temporal split.** Leave-last-out lets the model train on interactions that happened after another user's test
   event. Compare it with a global time cutoff; which is closer to deployment and what leakage remains?
2. **Candidate sampling.** Ranking the held-out item against 99 sampled negatives vs the full catalog changes metric values
   and sometimes model order. Explain the bias and when full ranking is feasible.
3. **Scale.** 300M users, 40B interactions. The split is a keyed reduction by user (find the max ts per user): shuffle by
   user id, run it in parallel across partitions, and avoid collecting a user's rows to the driver. Skew from heavy users?
4. **Concurrency / reproducibility.** The split job runs daily while data is appended. Fix an as-of snapshot and a
   deterministic tie-break so two concurrent runs produce identical splits.
5. **Repeat consumption.** Streaming members rewatch. Does removing already-seen items from recommendations
   (`unseen_only`) match the product? How do you evaluate both?
6. **Cold start.** The held-out item may never appear in train. Report hit rate split by whether the item is in train.
