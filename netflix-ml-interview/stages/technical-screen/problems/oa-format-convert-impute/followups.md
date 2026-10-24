# Follow-ups: OA format conversion and imputation

1. **Leakage.** Fill values computed on all records, including the test split, leak information. Where in a
   pipeline do you fit the imputer, and how do you persist the fill values for serving (training/serving skew)?
2. **Scale.** 2 billion records: one pass for column statistics (sum, count, per-value counts) computed in parallel
   across partitions and merged, then a second pass to write. What is the memory of the categorical counts for a
   high-cardinality column, and what do you do about it (top-k sketch, "other")?
3. **Concurrency.** Threads converting different chunks need the same fill values: compute once, share read-only.
4. **Missingness is informative.** Add an indicator column when imputing; when does mean imputation distort the
   distribution, and what would a median or model-based imputer change?
5. **Schema drift.** A new key appears mid-stream or a numeric column starts carrying strings; fail fast, coerce or quarantine?
