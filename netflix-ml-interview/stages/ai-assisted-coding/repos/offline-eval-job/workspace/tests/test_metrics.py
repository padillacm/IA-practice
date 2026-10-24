import math
import unittest

from offline_eval import hit_rate_at_k, ndcg_at_k


class MetricsTest(unittest.TestCase):
    def test_hit_rate(self):
        self.assertEqual(hit_rate_at_k([0, 0, 1], 3), 1.0)
        self.assertEqual(hit_rate_at_k([0, 0, 1], 2), 0.0)

    def test_ndcg_perfect(self):
        self.assertAlmostEqual(ndcg_at_k([1, 0, 0], 3), 1.0)

    def test_ndcg_position_discount(self):
        self.assertAlmostEqual(ndcg_at_k([0, 1, 0], 3), 1 / math.log2(3))

    def test_ndcg_no_relevant(self):
        self.assertEqual(ndcg_at_k([0, 0], 2), 0.0)

    def test_ndcg_uses_ideal_from_full_set(self):
        # relevant item outside the top-k still counts in the ideal ranking
        self.assertAlmostEqual(ndcg_at_k([0, 1], 1, ideal=[0, 1]), 0.0)


if __name__ == "__main__":
    unittest.main()
