import math
from collections import defaultdict


def recommend(ratings, user, n):
    if n <= 0:
        return []
    mine = ratings.get(user) or {}
    seen = set(mine)
    scores = defaultdict(float)
    if mine:
        item_users = defaultdict(list)
        for u, row in ratings.items():
            for item in row:
                item_users[item].append(u)
        dots = defaultdict(float)
        for item, r in mine.items():
            for v in item_users[item]:
                if v != user:
                    dots[v] += r * ratings[v][item]
        norm_u = math.sqrt(sum(r * r for r in mine.values()))
        sims = {}
        for v, d in dots.items():
            norm_v = math.sqrt(sum(r * r for r in ratings[v].values()))
            if d > 0 and norm_v > 0:
                sims[v] = d / (norm_u * norm_v)
        for v, s in sims.items():
            for item, r in ratings[v].items():
                if item not in seen:
                    scores[item] += s * r
    ranked = sorted((i for i, s in scores.items() if s > 0), key=lambda i: (-scores[i], i))[:n]
    if len(ranked) < n:
        counts = defaultdict(int)
        for row in ratings.values():
            for item in row:
                counts[item] += 1
        have = set(ranked)
        pop = sorted((i for i in counts if i not in seen and i not in have), key=lambda i: (-counts[i], i))
        ranked += pop[: n - len(ranked)]
    return ranked
