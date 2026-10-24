import math
import unittest

import solution


class TestMetrics(unittest.TestCase):
    def test_precision(self):
        self.assertAlmostEqual(solution.precision_at_k(["a", "b", "c"], {"a", "c"}, 2), 0.5)
        self.assertAlmostEqual(solution.precision_at_k(["a"], {"a"}, 4), 0.25)  # short list divides by k
        self.assertAlmostEqual(solution.precision_at_k([], {"a"}, 3), 0.0)

    def test_recall(self):
        self.assertAlmostEqual(solution.recall_at_k(["a", "b", "c"], {"a", "c", "z"}, 3), 2 / 3)
        self.assertEqual(solution.recall_at_k(["a"], set(), 3), 0.0)

    def test_ndcg_perfect_and_zero(self):
        gains = {"a": 3, "b": 2, "c": 1}
        self.assertAlmostEqual(solution.ndcg_at_k(["a", "b", "c"], gains, 3), 1.0)
        self.assertEqual(solution.ndcg_at_k(["x", "y"], gains, 3), 0.0)
        self.assertEqual(solution.ndcg_at_k(["a"], {}, 3), 0.0)

    def test_ndcg_hand_computed(self):
        gains = {"a": 3, "b": 2, "c": 1}
        dcg = 2 / math.log2(2) + 3 / math.log2(3) + 0
        idcg = 3 / math.log2(2) + 2 / math.log2(3) + 1 / math.log2(4)
        self.assertAlmostEqual(solution.ndcg_at_k(["b", "a", "x"], gains, 3), dcg / idcg)

    def test_ndcg_cutoff_uses_top_k_ideal(self):
        gains = {"a": 3, "b": 2, "c": 1}
        # ideal@1 is just "a"; ranking [b] gets 2 / 3
        self.assertAlmostEqual(solution.ndcg_at_k(["b", "a"], gains, 1), 2 / 3)

    def test_ideal_considers_items_not_retrieved(self):
        gains = {"a": 1, "hidden": 1}
        self.assertAlmostEqual(solution.ndcg_at_k(["a"], gains, 2), 1.0 / (1.0 + 1 / math.log2(3)))

    def test_invalid_k(self):
        for f, arg in [(solution.precision_at_k, {"a"}), (solution.recall_at_k, {"a"}), (solution.ndcg_at_k, {"a": 1})]:
            with self.assertRaises(ValueError):
                f(["a"], arg, 0)

    def test_mean_metric(self):
        reqs = [(["a", "b"], {"a"}), (["b", "a"], {"a"})]
        self.assertAlmostEqual(solution.mean_metric(solution.precision_at_k, reqs, k=1), 0.5)
        self.assertEqual(solution.mean_metric(solution.precision_at_k, [], k=1), 0.0)


if __name__ == "__main__":
    unittest.main()
