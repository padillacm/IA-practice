import math
import random
import unittest

import solution


def brute(ratings, user, n):
    items = sorted({i for r in ratings.values() for i in r})
    users = sorted(ratings)
    mine = ratings.get(user, {})
    scores = {i: 0.0 for i in items}
    if mine:
        nu = math.sqrt(sum(v * v for v in mine.values()))
        for v in users:
            if v == user:
                continue
            row = ratings[v]
            dot = sum(mine.get(i, 0) * row.get(i, 0) for i in items)
            nv = math.sqrt(sum(x * x for x in row.values()))
            if dot > 0:
                s = dot / (nu * nv)
                for i in items:
                    if i not in mine:
                        scores[i] += s * row.get(i, 0)
    out = sorted((i for i in items if i not in mine and scores[i] > 1e-12), key=lambda i: (-scores[i], i))[:n]
    if len(out) < n:
        pop = {i: sum(1 for r in ratings.values() if i in r) for i in items}
        rest = sorted((i for i in items if i not in mine and i not in out), key=lambda i: (-pop[i], i))
        out += rest[: n - len(out)]
    return out


class TestCF(unittest.TestCase):
    R = {
        "u1": {"a": 5, "b": 3},
        "u2": {"a": 5, "b": 3, "c": 4},
        "u3": {"a": 1, "d": 5},
        "u4": {"x": 2, "y": 5},
    }

    def test_neighbour_item_ranked_first(self):
        # u2 is much closer to u1 than u3 is
        self.assertEqual(solution.recommend(self.R, "u1", 1), ["c"])

    def test_never_recommends_seen_items(self):
        out = solution.recommend(self.R, "u1", 10)
        self.assertFalse({"a", "b"} & set(out))
        self.assertEqual(out[:2], ["c", "d"])

    def test_fallback_fills_with_popularity(self):
        out = solution.recommend(self.R, "u1", 10)
        # c and d have positive scores; x and y (no overlap with u1's neighbours) are filled by popularity then id
        self.assertEqual(out, ["c", "d", "x", "y"])

    def test_cold_start_user(self):
        out = solution.recommend(self.R, "newbie", 3)
        self.assertEqual(out, ["a", "b", "c"])  # a:3 raters, b:2, then ties (c, d, x, y with 1) by id
        self.assertEqual(solution.recommend(self.R, "u5", 0), [])

    def test_user_with_empty_row(self):
        r = dict(self.R, ghost={})
        self.assertEqual(solution.recommend(r, "ghost", 2), ["a", "b"])

    def test_tie_break_by_item_id(self):
        r = {"me": {"a": 1}, "v": {"a": 1, "z": 2, "b": 2}}
        self.assertEqual(solution.recommend(r, "me", 2), ["b", "z"])

    def test_matches_dense_bruteforce(self):
        rng = random.Random(13)
        for _ in range(60):
            users = [f"u{i}" for i in range(rng.randint(2, 8))]
            items = [f"i{i}" for i in range(rng.randint(2, 9))]
            r = {u: {i: float(rng.randint(1, 5)) for i in items if rng.random() < 0.4} for u in users}
            target = rng.choice(users)
            n = rng.randint(1, 6)
            self.assertEqual(solution.recommend(r, target, n), brute(r, target, n), (r, target, n))

    def test_scales_without_dense_matrix(self):
        # 20k users x 20k items would be 400M cells dense; sparse input has ~100k ratings
        rng = random.Random(1)
        r = {f"u{u}": {f"i{rng.randrange(20000)}": 1.0 for _ in range(5)} for u in range(20000)}
        out = solution.recommend(r, "u0", 10)
        self.assertEqual(len(out), 10)


if __name__ == "__main__":
    unittest.main()
