def leave_last_out(interactions, min_history=3):
    by_user = {}
    for idx, (u, _, ts) in enumerate(interactions):
        by_user.setdefault(u, []).append((ts, idx))
    held_idx = {}
    for u, rows in by_user.items():
        if len(rows) >= min_history:
            held_idx[u] = max(rows)[1]  # largest ts, ties -> latest input position
    held = set(held_idx.values())
    train = [r for i, r in enumerate(interactions) if i not in held]
    test = {u: interactions[i][1] for u, i in held_idx.items()}
    return train, test


def hit_rate_at_k(recommendations, test, k):
    if not test:
        return 0.0
    hits = sum(1 for u, item in test.items() if item in recommendations.get(u, [])[:k])
    return hits / len(test)


def unseen_only(recommendations, train):
    seen = {}
    for u, item, _ in train:
        seen.setdefault(u, set()).add(item)
    return {u: [i for i in items if i not in seen.get(u, ())] for u, items in recommendations.items()}
