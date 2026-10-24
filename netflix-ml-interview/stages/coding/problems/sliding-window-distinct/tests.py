import random
import unittest

import solution


def naive(events, window):
    out = []
    for i, (t, _) in enumerate(events):
        out.append(len({x for (s, x) in events[:i + 1] if s > t - window}))
    return out


class TestWindow(unittest.TestCase):
    def test_example(self):
        ev = [(0, "a"), (1, "b"), (2, "a"), (10, "c")]
        self.assertEqual(solution.distinct_counts(ev, 3), [1, 2, 2, 1])
        self.assertEqual(solution.max_distinct(ev, 3), 2)

    def test_boundary_is_exclusive_on_the_left(self):
        ev = [(0, "a"), (3, "b")]
        self.assertEqual(solution.distinct_counts(ev, 3), [1, 1])  # a is at t - window: excluded
        self.assertEqual(solution.distinct_counts(ev, 4), [1, 2])

    def test_equal_timestamps(self):
        ev = [(5, "a"), (5, "b"), (5, "a"), (5, "c")]
        self.assertEqual(solution.distinct_counts(ev, 1), [1, 2, 2, 3])

    def test_empty(self):
        self.assertEqual(solution.distinct_counts([], 5), [])
        self.assertEqual(solution.max_distinct([], 5), 0)

    def test_validation(self):
        with self.assertRaises(ValueError):
            solution.distinct_counts([(2, "a"), (1, "b")], 5)
        with self.assertRaises(ValueError):
            solution.distinct_counts([(1, "a")], 0)

    def test_repeated_title_keeps_count_until_all_expire(self):
        ev = [(0, "a"), (2, "a"), (4, "b"), (6, "c")]
        self.assertEqual(solution.distinct_counts(ev, 3), [1, 1, 2, 2])

    def test_matches_naive(self):
        rng = random.Random(5)
        for _ in range(200):
            ts = sorted(rng.randint(0, 40) for _ in range(rng.randint(0, 25)))
            ev = [(t, rng.choice("abcdef")) for t in ts]
            w = rng.randint(1, 15)
            self.assertEqual(solution.distinct_counts(ev, w), naive(ev, w))

    def test_large_input(self):
        ev = [(i, i % 1000) for i in range(300_000)]
        out = solution.distinct_counts(ev, 500)
        self.assertEqual(out[-1], 500)


if __name__ == "__main__":
    unittest.main()
