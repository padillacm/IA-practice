# Follow-ups: OA sparse matmul (COO)

Online assessments have no live follow-up; use these in the debrief or when the simulator reviews the solution.

1. **Scale.** The cost is the sum, over entries of `a`, of the row length of `b` at the matching index. Describe the input
   that makes it quadratic and how you would bound it. At 10^10 non-zeros, how do you partition (by the inner index
   `k`, as a join followed by a reduce on `(i, j)`) and run the pieces in parallel?
2. **Concurrency.** Row-parallel workers with threads share read-only structures; where is the contention, and why do
   per-worker accumulators avoid locks?
3. **Floating point.** Exact `!= 0` after float accumulation; use a tolerance or integers?
4. **Formats.** COO to CSR conversion cost; when is it worth converting first?
