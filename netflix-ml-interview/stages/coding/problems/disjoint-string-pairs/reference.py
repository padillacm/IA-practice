from collections import Counter


def _mask(w):
    m = 0
    for ch in w:
        m |= 1 << (ord(ch) - 97)
    return m


def count_disjoint_pairs(words):
    counts = Counter(_mask(w) for w in words)
    masks = list(counts)
    total = 0
    for i, a in enumerate(masks):
        if a == 0:  # empty-set mask is disjoint with every word, including other empty ones
            n = counts[a]
            total += n * (n - 1) // 2 + n * (len(words) - n)
            continue
        for b in masks[i + 1:]:
            if b != 0 and a & b == 0:
                total += counts[a] * counts[b]
    return total


def max_disjoint_product(words):
    best_len = {}
    for w in words:
        m = _mask(w)
        best_len[m] = max(best_len.get(m, 0), len(w))
    items = list(best_len.items())
    best = 0
    for i, (a, la) in enumerate(items):
        for b, lb in items[i + 1:]:
            if a & b == 0:
                best = max(best, la * lb)
    # two words with the same non-empty mask are never disjoint; empty strings give product 0
    return best
