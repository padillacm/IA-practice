# Follow-ups: sparse matrix multiplication

1. **Complexity.** Cost is sum over non-zeros `a[i,k]` of the number of non-zeros in row `k` of `b`. What input makes it
   explode (one dense row/column), and what would you do about it (sampling, thresholding, blocking)?
2. **Formats.** Why CSR/CSC beat dict-of-dicts in memory and speed; what does scipy.sparse do for you, and when would
   you still write this by hand?
3. **Scale and parallel execution.** Gram matrix of 100M x 1M interactions: partition rows of `a` across workers
   (each needs all of `b`, or the needed rows of `b` via a join on k), then combine. In Spark/MapReduce terms this is a
   join on the inner index followed by a reduce on `(i, j)`. Discuss skew on popular titles and the shuffle size.
4. **Concurrency.** Row-parallel multiplication with threads: Python's GIL, process pools vs a native library; what is
   shared (read-only inputs) and what is not (per-row accumulators)?
5. **Approximation.** For co-watch similarity only the top-k neighbours per row are kept. How do you keep the output
   sparse during the multiplication rather than after?
6. **Numerical.** Floating point cancellation: exact `!= 0` vs a tolerance; effects on the output sparsity.
