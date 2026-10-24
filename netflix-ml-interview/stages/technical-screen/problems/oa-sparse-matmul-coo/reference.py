from collections import defaultdict


def _rows(m):
    rows = defaultdict(lambda: defaultdict(float))
    for i, j, v in m:
        rows[i][j] += v
    return rows


def matmul_coo(a, b):
    ra, rb = _rows(a), _rows(b)
    out = []
    for i in sorted(ra):
        acc = defaultdict(float)
        for k, v in ra[i].items():
            for j, w in rb.get(k, {}).items():
                acc[j] += v * w
        out.extend((i, j, x) for j, x in sorted(acc.items()) if x != 0)
    return out


def to_dense(triplets, n_rows, n_cols):
    dense = [[0] * n_cols for _ in range(n_rows)]
    for i, j, v in triplets:
        if not (0 <= i < n_rows and 0 <= j < n_cols):
            raise IndexError((i, j))
        dense[i][j] += v
    return dense
