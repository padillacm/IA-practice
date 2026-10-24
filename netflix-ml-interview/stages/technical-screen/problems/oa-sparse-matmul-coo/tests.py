import random
import unittest

import solution


class TestCOO(unittest.TestCase):
    def test_small(self):
        a = [(0, 0, 1), (0, 2, 2), (1, 1, 3)]
        b = [(0, 1, 4), (1, 0, 5), (2, 1, 1), (2, 2, 2)]
        self.assertEqual(solution.matmul_coo(a, b), [(0, 1, 6), (0, 2, 4), (1, 0, 15)])

    def test_duplicates_are_summed(self):
        a = [(0, 0, 1), (0, 0, 2)]
        b = [(0, 0, 1), (0, 0, 1)]
        self.assertEqual(solution.matmul_coo(a, b), [(0, 0, 6)])

    def test_zero_results_are_dropped(self):
        a = [(0, 0, 1), (0, 1, 1)]
        b = [(0, 0, 2), (1, 0, -2)]
        self.assertEqual(solution.matmul_coo(a, b), [])

    def test_empty(self):
        self.assertEqual(solution.matmul_coo([], [(0, 0, 1)]), [])
        self.assertEqual(solution.matmul_coo([(0, 0, 1)], []), [])

    def test_huge_indices(self):
        a = [(10**9, 5 * 10**8, 2)]
        b = [(5 * 10**8, 10**9 - 1, 3)]
        self.assertEqual(solution.matmul_coo(a, b), [(10**9, 10**9 - 1, 6)])

    def test_to_dense(self):
        self.assertEqual(solution.to_dense([(0, 1, 2), (0, 1, 3), (1, 0, 1)], 2, 2), [[0, 5], [1, 0]])
        with self.assertRaises(IndexError):
            solution.to_dense([(2, 0, 1)], 2, 2)

    def test_matches_dense(self):
        rng = random.Random(33)
        for _ in range(100):
            n, m, p = rng.randint(1, 5), rng.randint(1, 5), rng.randint(1, 5)
            a = [(rng.randrange(n), rng.randrange(m), rng.randint(-2, 3)) for _ in range(rng.randint(0, 10))]
            b = [(rng.randrange(m), rng.randrange(p), rng.randint(-2, 3)) for _ in range(rng.randint(0, 10))]
            got = solution.matmul_coo(a, b)
            da, db = solution.to_dense(a, n, m), solution.to_dense(b, m, p)
            exp = [[sum(da[i][k] * db[k][j] for k in range(m)) for j in range(p)] for i in range(n)]
            self.assertEqual(solution.to_dense(got, n, p), exp)
            self.assertEqual(got, sorted(got))
            self.assertEqual(len({(i, j) for i, j, _ in got}), len(got))
            self.assertTrue(all(v != 0 for _, _, v in got))


if __name__ == "__main__":
    unittest.main()
