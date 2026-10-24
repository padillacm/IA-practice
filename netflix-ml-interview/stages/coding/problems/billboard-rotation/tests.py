import unittest

import solution


def take(b, n):
    return [b.get() for _ in range(n)]


class TestBillboard(unittest.TestCase):
    def test_empty(self):
        self.assertIsNone(solution.Billboard().get())

    def test_order_and_cycle(self):
        b = solution.Billboard()
        for m, s in [("a", 1), ("b", 3), ("c", 2)]:
            b.add(m, s)
        self.assertEqual(take(b, 6), ["b", "c", "a", "b", "c", "a"])

    def test_ties_by_id(self):
        b = solution.Billboard()
        for m in ["z", "m", "a"]:
            b.add(m, 5)
        self.assertEqual(take(b, 3), ["a", "m", "z"])

    def test_update_pending_changes_current_cycle(self):
        b = solution.Billboard()
        for m, s in [("a", 3), ("b", 2), ("c", 1)]:
            b.add(m, s)
        self.assertEqual(b.get(), "a")
        b.update("c", 10)
        self.assertEqual(take(b, 2), ["c", "b"])

    def test_update_served_applies_next_cycle(self):
        b = solution.Billboard()
        for m, s in [("a", 3), ("b", 2), ("c", 1)]:
            b.add(m, s)
        self.assertEqual(b.get(), "a")
        b.update("a", 0)  # already served: no effect now
        self.assertEqual(take(b, 2), ["b", "c"])
        self.assertEqual(take(b, 3), ["b", "c", "a"])

    def test_each_movie_once_per_cycle_with_repeated_updates(self):
        b = solution.Billboard()
        for m, s in [("a", 3), ("b", 2)]:
            b.add(m, s)
        b.update("a", 1)
        b.update("a", 3)  # back to the old score: stale heap entries must not duplicate it
        self.assertEqual(take(b, 4), ["a", "b", "a", "b"])

    def test_add_midcycle_is_eligible(self):
        b = solution.Billboard()
        b.add("a", 2)
        b.add("b", 1)
        self.assertEqual(b.get(), "a")
        b.add("c", 9)
        self.assertEqual(take(b, 2), ["c", "b"])
        self.assertEqual(b.get(), "c")

    def test_remove(self):
        b = solution.Billboard()
        for m, s in [("a", 3), ("b", 2), ("c", 1)]:
            b.add(m, s)
        b.remove("b")
        self.assertEqual(take(b, 4), ["a", "c", "a", "c"])
        b.remove("a")
        b.remove("c")
        self.assertIsNone(b.get())

    def test_unknown_movie_raises(self):
        b = solution.Billboard()
        with self.assertRaises(KeyError):
            b.update("x", 1)
        with self.assertRaises(KeyError):
            b.remove("x")

    def test_remove_then_readd(self):
        b = solution.Billboard()
        b.add("a", 1)
        b.add("b", 2)
        b.remove("b")
        b.add("b", 5)
        self.assertEqual(take(b, 2), ["b", "a"])

    def test_many_operations_are_fast(self):
        b = solution.Billboard()
        for i in range(50_000):
            b.add(i, i % 977)
        seen = set()
        for _ in range(50_000):
            seen.add(b.get())
        self.assertEqual(len(seen), 50_000)


if __name__ == "__main__":
    unittest.main()
