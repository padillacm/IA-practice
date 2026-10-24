import random
import unittest

import solution


def to_dense(m, rows, cols):
    return [[m.get(i, {}).get(j, 0) for j in range(cols)] for i in range(rows)]


def dense_mul(x, y):
    return [[sum(x[i][k] * y[k][j] for k in range(len(y))) for j in range(len(y[0]))] for i in range(len(x))]


def rand_sparse(rng, rows, cols, density):
    return {i: {j: rng.randint(-3, 3) or 1 for j in range(cols) if rng.random() < density} for i in range(rows)}


def clean(m):
    return {i: r for i, r in m.items() if r}


class TestSparse(unittest.TestCase):
    def test_small(self):
        a = {0: {0: 1, 2: 2}, 1: {1: 3}}
        b = {0: {1: 4}, 1: {0: 5}, 2: {1: 1, 2: 2}}
        self.assertEqual(solution.sparse_matmul(a, b), {0: {1: 6, 2: 4}, 1: {0: 15}})

    def test_cancellation_is_dropped(self):
        a = {0: {0: 1, 1: 1}}
        b = {0: {0: 2}, 1: {0: -2}}
        self.assertEqual(solution.sparse_matmul(a, b), {})

    def test_empty_and_missing_rows(self):
        self.assertEqual(solution.sparse_matmul({}, {0: {0: 1}}), {})
        self.assertEqual(solution.sparse_matmul({0: {5: 1}}, {0: {0: 1}}), {})

    def test_transpose(self):
        a = {0: {1: 2, 3: 4}, 2: {1: 5}}
        self.assertEqual(solution.sparse_transpose(a), {1: {0: 2, 2: 5}, 3: {0: 4}})
        self.assertEqual(solution.sparse_transpose(solution.sparse_transpose(a)), a)

    def test_gram_is_symmetric(self):
        a = {0: {0: 1, 1: 1}, 1: {1: 1, 2: 1}, 2: {0: 1}}
        g = solution.sparse_gram(a)
        self.assertEqual(g, {0: {0: 2, 1: 1, 2: 1}, 1: {0: 1, 1: 2}, 2: {0: 1, 2: 1}})

    def test_matches_dense(self):
        rng = random.Random(21)
        for _ in range(100):
            n, m, p = rng.randint(1, 6), rng.randint(1, 6), rng.randint(1, 6)
            a, b = rand_sparse(rng, n, m, 0.4), rand_sparse(rng, m, p, 0.4)
            got = solution.sparse_matmul(clean(a), clean(b))
            self.assertEqual(to_dense(got, n, p), dense_mul(to_dense(a, n, m), to_dense(b, m, p)))
            for row in got.values():
                self.assertTrue(row and all(v != 0 for v in row.values()))

    def test_huge_dimensions_cost_depends_on_nnz(self):
        a = {10**9: {10**9 + 7: 2}}
        b = {10**9 + 7: {5 * 10**9: 3}}
        self.assertEqual(solution.sparse_matmul(a, b), {10**9: {5 * 10**9: 6}})

    def test_inputs_not_mutated(self):
        a = {0: {0: 1}}
        b = {0: {0: 1}}
        solution.sparse_matmul(a, b)
        solution.sparse_transpose(a)
        self.assertEqual(a, {0: {0: 1}})


if __name__ == "__main__":
    unittest.main()
