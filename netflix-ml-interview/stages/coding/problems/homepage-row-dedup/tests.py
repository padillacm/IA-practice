import copy
import unittest

import solution


class TestDedupRows(unittest.TestCase):
    def test_statement_example(self):
        rows = [["a", "b", "c", "a"], ["b", "d", "e", "c"], ["c", "f", "g"]]
        self.assertEqual(solution.dedup_rows(rows, 2),
                         [["a", "b", "c"], ["d", "e", "c"], ["c", "f", "g"]])

    def test_does_not_mutate_input(self):
        rows = [["a", "a"], ["a", "b"]]
        snapshot = copy.deepcopy(rows)
        solution.dedup_rows(rows, 1)
        self.assertEqual(rows, snapshot)

    def test_n_zero_is_within_row_only(self):
        rows = [["a", "b", "a"], ["a", "a", "b"]]
        self.assertEqual(solution.dedup_rows(rows, 0), [["a", "b"], ["a", "b"]])

    def test_large_n_is_global_dedup_of_everything(self):
        rows = [["a", "b"], ["b", "c"], ["a", "c", "d"]]
        self.assertEqual(solution.dedup_rows(rows, 100), [["a", "b"], ["c"], ["d"]])

    def test_shift_makes_items_visible(self):
        # "x" is dropped from the visible area of row 1, so "y" and "z" move up and claim visible slots
        rows = [["x"], ["x", "y", "z", "w"], ["z", "q"]]
        self.assertEqual(solution.dedup_rows(rows, 2), [["x"], ["y", "z", "w"], ["q"]])

    def test_offscreen_item_does_not_block_later_visible(self):
        rows = [["a", "b", "c"], ["c", "d"]]
        self.assertEqual(solution.dedup_rows(rows, 2), [["a", "b", "c"], ["c", "d"]])

    def test_empty_inputs(self):
        self.assertEqual(solution.dedup_rows([], 3), [])
        self.assertEqual(solution.dedup_rows([[], ["a"]], 3), [[], ["a"]])

    def test_matches_naive_on_random_pages(self):
        import random
        rng = random.Random(7)
        for _ in range(200):
            n = rng.randint(0, 4)
            rows = [[rng.choice("abcdefgh") for _ in range(rng.randint(0, 8))] for _ in range(rng.randint(0, 5))]
            self.assertEqual(solution.dedup_rows(rows, n), self._naive(rows, n))

    @staticmethod
    def _naive(rows, n):
        visible, out = [], []
        for row in rows:
            kept = []
            for t in row:
                if t in kept:
                    continue
                if len(kept) < n and t in visible:
                    continue
                if len(kept) < n:
                    visible.append(t)
                kept.append(t)
            out.append(kept)
        return out


if __name__ == "__main__":
    unittest.main()
