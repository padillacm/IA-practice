import random
import unittest

import solution


def naive_near(xs, k, t):
    for i in range(len(xs)):
        for j in range(i + 1, min(len(xs), i + k + 1)):
            if abs(xs[i] - xs[j]) <= t:
                return True
    return False


class TestPart1(unittest.TestCase):
    def test_basic(self):
        self.assertFalse(solution.has_duplicate([]))
        self.assertFalse(solution.has_duplicate([1, 2, 3]))
        self.assertTrue(solution.has_duplicate([1, 2, 1]))
        self.assertTrue(solution.has_duplicate(["a", "a"]))


class TestPart2(unittest.TestCase):
    def test_distance(self):
        self.assertTrue(solution.has_duplicate_within([1, 2, 3, 1], 3))
        self.assertFalse(solution.has_duplicate_within([1, 2, 3, 1], 2))
        self.assertTrue(solution.has_duplicate_within([1, 0, 1, 1], 1))

    def test_k_zero_and_empty(self):
        self.assertFalse(solution.has_duplicate_within([1, 1], 0))
        self.assertFalse(solution.has_duplicate_within([], 5))

    def test_later_pair_after_far_pair(self):
        # first pair of 7s is too far apart, but the second pair is close
        self.assertTrue(solution.has_duplicate_within([7, 1, 2, 3, 7, 7], 1))
        self.assertFalse(solution.has_duplicate_within([7, 1, 2, 3, 7], 2))


class TestPart3(unittest.TestCase):
    def test_examples(self):
        self.assertTrue(solution.has_near_duplicate([10, 100, 12], 2, 2))
        self.assertFalse(solution.has_near_duplicate([10, 100, 12], 1, 2))
        self.assertFalse(solution.has_near_duplicate([10, 20, 30], 2, 5))
        self.assertTrue(solution.has_near_duplicate([5, 5], 1, 0))

    def test_adjacent_buckets(self):
        # t=3 -> bucket width 4; 3 and 6 land in buckets 0 and 1 and differ by 3
        self.assertTrue(solution.has_near_duplicate([3, 6], 1, 3))
        self.assertFalse(solution.has_near_duplicate([3, 7], 1, 3))

    def test_negative_values_and_edge_cases(self):
        self.assertTrue(solution.has_near_duplicate([-1, 1], 1, 2))
        self.assertFalse(solution.has_near_duplicate([-3, 1], 1, 3))
        self.assertFalse(solution.has_near_duplicate([], 3, 3))
        self.assertFalse(solution.has_near_duplicate([1], 3, 3))
        self.assertFalse(solution.has_near_duplicate([1, 1], 0, 3))

    def test_window_eviction(self):
        self.assertFalse(solution.has_near_duplicate([1, 50, 90, 1], 2, 0))
        self.assertTrue(solution.has_near_duplicate([1, 50, 90, 1], 3, 0))

    def test_matches_naive(self):
        rng = random.Random(3)
        for _ in range(500):
            xs = [rng.randint(-20, 60) for _ in range(rng.randint(0, 12))]
            k, t = rng.randint(0, 5), rng.randint(0, 6)
            self.assertEqual(solution.has_near_duplicate(xs, k, t), naive_near(xs, k, t), (xs, k, t))

    def test_large_input_is_fast(self):
        xs = list(range(0, 2_000_000, 10))  # no near duplicates for t < 10
        self.assertFalse(solution.has_near_duplicate(xs, 1000, 5))


if __name__ == "__main__":
    unittest.main()
