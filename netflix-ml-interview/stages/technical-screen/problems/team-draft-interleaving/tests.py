import unittest

import solution


class TestTeamDraft(unittest.TestCase):
    def test_a_first_always(self):
        out, attr = solution.team_draft(["x", "y", "z"], ["y", "w", "x"], [0, 0, 0], 4)
        # round 0: A->x, B->y; round 1: A->z (y taken), B->w
        self.assertEqual(out, ["x", "y", "z", "w"])
        self.assertEqual(attr, {"x": "A", "y": "B", "z": "A", "w": "B"})

    def test_b_first(self):
        out, attr = solution.team_draft(["x", "y"], ["x", "w"], [1, 1], 4)
        # round 0: B->x, A: x taken -> y; round 1: B->w, A exhausted
        self.assertEqual(out, ["x", "y", "w"])
        self.assertEqual(attr, {"x": "B", "y": "A", "w": "B"})

    def test_k_cuts_mid_round(self):
        out, attr = solution.team_draft(["a", "b"], ["c", "d"], [0, 1], 3)
        self.assertEqual(out, ["a", "c", "d"])
        self.assertEqual(attr["d"], "B")

    def test_exhausted_rankings_end_early(self):
        out, _ = solution.team_draft(["a"], ["a"], [0, 0], 10)
        self.assertEqual(out, ["a"])

    def test_not_enough_coins(self):
        with self.assertRaises(ValueError):
            solution.team_draft(["a", "b", "c"], ["d", "e", "f"], [0], 6)

    def test_no_duplicates_and_attribution_complete(self):
        import random
        rng = random.Random(1)
        for _ in range(100):
            a = rng.sample("abcdefgh", rng.randint(0, 8))
            b = rng.sample("abcdefgh", rng.randint(0, 8))
            coins = [rng.randint(0, 1) for _ in range(20)]
            out, attr = solution.team_draft(a, b, coins, rng.randint(1, 10))
            self.assertEqual(len(out), len(set(out)))
            self.assertEqual(set(out), set(attr))
            self.assertTrue(set(out) <= set(a) | set(b))

    def test_score_clicks(self):
        attr = {"x": "A", "y": "B", "z": "A"}
        self.assertEqual(solution.score_clicks(["x", "z", "q"], attr), {"A": 2, "B": 0})
        self.assertEqual(solution.score_clicks([], attr), {"A": 0, "B": 0})

    def test_winner(self):
        self.assertEqual(solution.winner([{"A": 2, "B": 0}, {"A": 0, "B": 1}, {"A": 1, "B": 0}]), "A")
        self.assertEqual(solution.winner([{"A": 1, "B": 1}]), "tie")
        self.assertEqual(solution.winner([{"A": 0, "B": 3}, {"A": 1, "B": 1}]), "B")
        self.assertEqual(solution.winner([]), "tie")


if __name__ == "__main__":
    unittest.main()
