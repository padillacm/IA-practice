import unittest

import solution


class TestSplit(unittest.TestCase):
    def test_basic(self):
        data = [("u1", "a", 3), ("u1", "b", 1), ("u1", "c", 2), ("u2", "a", 1), ("u2", "b", 2)]
        train, test = solution.leave_last_out(data, min_history=3)
        self.assertEqual(test, {"u1": "a"})
        self.assertEqual(train, [("u1", "b", 1), ("u1", "c", 2), ("u2", "a", 1), ("u2", "b", 2)])

    def test_ties_use_latest_input_position(self):
        data = [("u", "a", 5), ("u", "b", 5), ("u", "c", 1)]
        train, test = solution.leave_last_out(data, 3)
        self.assertEqual(test, {"u": "b"})
        self.assertEqual(train, [("u", "a", 5), ("u", "c", 1)])

    def test_min_history_boundary_and_no_leakage(self):
        data = [("u", "a", 1), ("u", "b", 2)]
        self.assertEqual(solution.leave_last_out(data, 2), ([("u", "a", 1)], {"u": "b"}))
        self.assertEqual(solution.leave_last_out(data, 3), (data, {}))
        train, test = solution.leave_last_out([("u", "a", 1), ("u", "a", 2), ("u", "a", 3)], 3)
        self.assertEqual(len(train), 2)  # the repeated item is a separate interaction; only one row held out
        self.assertEqual(test, {"u": "a"})

    def test_does_not_mutate(self):
        data = [("u", "a", 2), ("u", "b", 1), ("u", "c", 3)]
        copy = list(data)
        solution.leave_last_out(data, 3)
        self.assertEqual(data, copy)

    def test_hit_rate(self):
        test = {"u1": "a", "u2": "b", "u3": "c"}
        recs = {"u1": ["x", "a"], "u2": ["b"], }
        self.assertAlmostEqual(solution.hit_rate_at_k(recs, test, 1), 1 / 3)
        self.assertAlmostEqual(solution.hit_rate_at_k(recs, test, 2), 2 / 3)
        self.assertEqual(solution.hit_rate_at_k(recs, {}, 2), 0.0)

    def test_unseen_only(self):
        train = [("u1", "a", 1), ("u1", "b", 2)]
        recs = {"u1": ["a", "c", "b", "d"], "u2": ["a"]}
        self.assertEqual(solution.unseen_only(recs, train), {"u1": ["c", "d"], "u2": ["a"]})

    def test_scale(self):
        data = [(u, i, i) for u in range(2000) for i in range(50)]
        train, test = solution.leave_last_out(data, 3)
        self.assertEqual(len(test), 2000)
        self.assertEqual(len(train), 2000 * 49)


if __name__ == "__main__":
    unittest.main()
