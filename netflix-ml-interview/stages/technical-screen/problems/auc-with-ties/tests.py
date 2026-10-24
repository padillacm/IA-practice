import random
import unittest

import solution


def naive(labels, scores):
    pos = [s for y, s in zip(labels, scores) if y == 1]
    neg = [s for y, s in zip(labels, scores) if y == 0]
    total = sum(1.0 if p > n else 0.5 if p == n else 0.0 for p in pos for n in neg)
    return total / (len(pos) * len(neg))


class TestAUC(unittest.TestCase):
    def test_perfect_and_inverted(self):
        self.assertAlmostEqual(solution.roc_auc([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9]), 1.0)
        self.assertAlmostEqual(solution.roc_auc([1, 1, 0, 0], [0.1, 0.2, 0.8, 0.9]), 0.0)

    def test_classic_example(self):
        self.assertAlmostEqual(solution.roc_auc([0, 0, 1, 1], [0.1, 0.4, 0.35, 0.8]), 0.75)

    def test_all_tied_is_half(self):
        self.assertAlmostEqual(solution.roc_auc([0, 1, 0, 1], [0.5] * 4), 0.5)

    def test_partial_ties(self):
        self.assertAlmostEqual(solution.roc_auc([0, 1, 1], [0.5, 0.5, 0.9]), 0.75)

    def test_validation(self):
        with self.assertRaises(ValueError):
            solution.roc_auc([1, 1], [0.1, 0.2])
        with self.assertRaises(ValueError):
            solution.roc_auc([0, 1], [0.1])

    def test_matches_naive(self):
        rng = random.Random(10)
        for _ in range(300):
            n = rng.randint(2, 30)
            labels = [rng.randint(0, 1) for _ in range(n)]
            if sum(labels) in (0, n):
                labels[0], labels[1] = 0, 1
            scores = [rng.randint(0, 5) / 5 for _ in range(n)]
            self.assertAlmostEqual(solution.roc_auc(labels, scores), naive(labels, scores))

    def test_groups(self):
        g = ["a", "a", "b", "b", "c", "c"]
        y = [0, 1, 0, 1, 1, 1]  # c has one class only
        s = [0.1, 0.9, 0.9, 0.1, 0.3, 0.4]
        self.assertEqual(solution.auc_by_group(g, y, s), {"a": 1.0, "b": 0.0})
        self.assertAlmostEqual(solution.macro_auc(g, y, s), 0.5)
        self.assertEqual(solution.macro_auc(["x", "x"], [1, 1], [0.1, 0.2]), 0.0)

    def test_n_log_n(self):
        rng = random.Random(0)
        n = 200_000
        labels = [rng.randint(0, 1) for _ in range(n)]
        scores = [rng.random() for _ in range(n)]
        auc = solution.roc_auc(labels, scores)
        self.assertTrue(0.49 < auc < 0.51)


if __name__ == "__main__":
    unittest.main()
