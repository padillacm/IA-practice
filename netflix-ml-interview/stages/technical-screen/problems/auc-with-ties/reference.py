def roc_auc(labels, scores):
    if len(labels) != len(scores):
        raise ValueError("length mismatch")
    n_pos = sum(1 for y in labels if y == 1)
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        raise ValueError("need both classes")
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    ranks = [0.0] * len(scores)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1  # 1-based average rank
        for t in range(i, j + 1):
            ranks[order[t]] = avg
        i = j + 1
    rank_sum = sum(r for r, y in zip(ranks, labels) if y == 1)
    return (rank_sum - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


def auc_by_group(groups, labels, scores):
    by = {}
    for g, y, s in zip(groups, labels, scores):
        by.setdefault(g, ([], []))
        by[g][0].append(y)
        by[g][1].append(s)
    out = {}
    for g, (ys, ss) in by.items():
        if 0 < sum(ys) < len(ys):
            out[g] = roc_auc(ys, ss)
    return out


def macro_auc(groups, labels, scores):
    per = auc_by_group(groups, labels, scores)
    return sum(per.values()) / len(per) if per else 0.0
