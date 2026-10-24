def sparse_matmul(a, b):
    out = {}
    for i, row in a.items():
        acc = {}
        for k, v in row.items():
            brow = b.get(k)
            if not brow:
                continue
            for j, w in brow.items():
                acc[j] = acc.get(j, 0) + v * w
        acc = {j: x for j, x in acc.items() if x != 0}
        if acc:
            out[i] = acc
    return out


def sparse_transpose(a):
    out = {}
    for i, row in a.items():
        for j, v in row.items():
            out.setdefault(j, {})[i] = v
    return out


def sparse_gram(a):
    return sparse_matmul(a, sparse_transpose(a))
