---
variant: oa
roles: [mle, rs, ds]
levels: [L4, L5, L6]
title: OA coding 1 - sparse matrix multiplication from COO triplets
minutes: 35
---
# OA coding 1: sparse matrix multiplication (COO)

Matrices arrive as lists of `(row, col, value)` triplets (coordinate format). The same `(row, col)` may appear several
times: duplicates are **summed**. Implement:

`matmul_coo(a, b)` returning `a @ b` as a list of `(row, col, value)` triplets that is

- sorted by `(row, col)`,
- free of duplicates and of entries whose value is exactly 0,
- computed without building dense matrices (indices can be as large as 10^9).

Then `to_dense(triplets, n_rows, n_cols)` returning a list of lists (used to check small cases; entries out of range
raise `IndexError`).

This is an online assessment: no interviewer help; budget 35 minutes for this problem. Write at least three tests of your own.
