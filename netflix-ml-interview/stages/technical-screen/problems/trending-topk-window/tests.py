import random
import unittest

import solution


class TestTrending(unittest.TestCase):
    def test_basic(self):
        t = solution.TrendingTracker(10)
        for ts, title in [(1, "a"), (2, "b"), (3, "a"), (4, "c"), (5, "b"), (6, "a")]:
            t.record(ts, title)
        self.assertEqual(t.top_k(6, 2), [("a", 3), ("b", 2)])
        self.assertEqual(t.top_k(6, 10), [("a", 3), ("b", 2), ("c", 1)])

    def test_tie_by_title(self):
        t = solution.TrendingTracker(10)
        t.record(1, "z")
        t.record(2, "m")
        self.assertEqual(t.top_k(2, 2), [("m", 1), ("z", 1)])

    def test_boundary_exclusive_left(self):
        t = solution.TrendingTracker(5)
        t.record(0, "old")
        t.record(5, "new")
        self.assertEqual(t.top_k(5, 5), [("new", 1)])  # window is (0, 5]

    def test_expiry_over_time(self):
        t = solution.TrendingTracker(3)
        t.record(1, "a")
        t.record(2, "a")
        t.record(3, "b")
        self.assertEqual(t.top_k(3, 2), [("a", 2), ("b", 1)])
        self.assertEqual(t.top_k(4, 2), [("a", 1), ("b", 1)])
        self.assertEqual(t.top_k(6, 2), [])

    def test_empty_and_validation(self):
        t = solution.TrendingTracker(3)
        self.assertEqual(t.top_k(0, 3), [])
        t.record(5, "a")
        with self.assertRaises(ValueError):
            t.record(4, "b")

    def test_matches_naive(self):
        rng = random.Random(17)
        t = solution.TrendingTracker(7)
        log, now = [], 0
        for _ in range(600):
            now += rng.randint(0, 3)
            title = rng.choice("abcdefg")
            t.record(now, title)
            log.append((now, title))
            if rng.random() < 0.3:
                k = rng.randint(1, 5)
                counts = {}
                for ts, x in log:
                    if ts > now - 7:
                        counts[x] = counts.get(x, 0) + 1
                exp = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:k]
                self.assertEqual(t.top_k(now, k), exp)

    def test_memory_bounded(self):
        t = solution.TrendingTracker(10)
        for ts in range(200_000):
            t.record(ts, ts % 5)
            if ts % 1000 == 0:
                t.top_k(ts, 3)
        t.top_k(200_000, 3)
        self.assertEqual(sum(c for _, c in t.top_k(200_000, 5)), 9)  # plays at 199991..199999


if __name__ == "__main__":
    unittest.main()
