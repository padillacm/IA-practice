import unittest

import solution


class TestSampler(unittest.TestCase):
    def test_boundaries(self):
        s = solution.WeightedKeySampler({"a": 1, "b": 3})
        self.assertEqual(s.pick(0.0), "a")
        self.assertEqual(s.pick(0.24), "a")
        self.assertEqual(s.pick(0.25), "b")
        self.assertEqual(s.pick(0.999999), "b")

    def test_zero_weight_never_picked(self):
        s = solution.WeightedKeySampler({"a": 0, "b": 2, "c": 0, "d": 2})
        picks = {s.pick(i / 1000) for i in range(1000)}
        self.assertEqual(picks, {"b", "d"})
        self.assertEqual(s.pick(0.0), "b")

    def test_proportions_on_a_uniform_grid(self):
        weights = {"a": 1, "b": 2, "c": 3, "d": 4}
        s = solution.WeightedKeySampler(weights)
        counts = {k: 0 for k in weights}
        for i in range(10_000):
            counts[s.pick(i / 10_000)] += 1
        self.assertEqual(counts, {"a": 1000, "b": 2000, "c": 3000, "d": 4000})

    def test_update_changes_distribution(self):
        s = solution.WeightedKeySampler({"a": 1, "b": 1})
        s.update("a", 0)
        self.assertEqual({s.pick(i / 100) for i in range(100)}, {"b"})
        s.update("a", 3)
        self.assertEqual(s.pick(0.5), "a")
        self.assertEqual(s.pick(0.9), "b")

    def test_single_key(self):
        s = solution.WeightedKeySampler({"only": 0.5})
        self.assertEqual(s.pick(0.0), "only")
        self.assertEqual(s.pick(0.9999999), "only")

    def test_validation(self):
        with self.assertRaises(ValueError):
            solution.WeightedKeySampler({"a": -1, "b": 2})
        with self.assertRaises(ValueError):
            solution.WeightedKeySampler({"a": 0})
        with self.assertRaises(ValueError):
            solution.WeightedKeySampler({})
        s = solution.WeightedKeySampler({"a": 1, "b": 0})
        with self.assertRaises(KeyError):
            s.update("zzz", 1)
        with self.assertRaises(ValueError):
            s.update("a", 0)  # would make the total 0
        with self.assertRaises(ValueError):
            s.update("b", -1)

    def test_matches_linear_scan(self):
        import random
        rng = random.Random(11)
        weights = {i: rng.randint(0, 9) for i in range(40)}
        weights[0] = 5
        s = solution.WeightedKeySampler(weights)
        for step in range(400):
            if step % 3 == 0:
                k = rng.randrange(40)
                new = rng.randint(0, 9)
                if sum(weights.values()) - weights[k] + new > 0:
                    weights[k] = new
                    s.update(k, new)
            u = rng.random()
            total, target, acc, expected = sum(weights.values()), None, 0, None
            target = u * total
            for k, w in weights.items():
                acc += w
                if acc > target:
                    expected = k
                    break
            self.assertEqual(s.pick(u), expected)

    def test_scale(self):
        n = 100_000
        s = solution.WeightedKeySampler({i: 1 for i in range(n)})
        for i in range(n):
            s.update(i, 2)
            s.pick(0.5)
        self.assertEqual(s.pick(0.5), n // 2)


if __name__ == "__main__":
    unittest.main()
