---
variant: ml-coding
roles: [mle, rs]
levels: [L4, L5, L6]
title: Sparse matrix multiplication
minutes: 40
---
# Sparse matrix multiplication

Sparse matrices are stored as row dictionaries: `{row: {col: value}}`; absent entries are 0 and stored values are
non-zero. Implement:

1. `sparse_matmul(a, b)`: product `a @ b` in the same format. Result entries that cancel to exactly 0 must be omitted,
   and rows with no entries must be omitted. Do not materialize dense matrices. Time should depend on the number of
   non-zeros, not on the matrix dimensions.
2. `sparse_transpose(a)`: transpose in the same format.
3. `sparse_gram(a)`: `a @ a.T` (item-item or user-user co-occurrence, depending on orientation), reusing the
   previous functions.

Mention what you would do for shapes that do not conform (the inner dimension is implicit in the keys). Write your own
tests with a dense reference implementation.
