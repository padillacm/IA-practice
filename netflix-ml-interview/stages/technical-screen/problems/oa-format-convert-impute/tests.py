import copy
import unittest

import solution


class TestConvert(unittest.TestCase):
    def test_numeric_mean_and_categorical_mode(self):
        recs = [{"age": 10, "plan": "basic"}, {"age": None, "plan": "premium"}, {"plan": "basic"}, {"age": 20, "plan": ""}]
        out = solution.to_columns(recs)
        self.assertEqual(list(out), ["age", "plan"])
        self.assertEqual(out["age"], [10, 15.0, 15.0, 20])
        self.assertEqual(out["plan"], ["basic", "premium", "basic", "basic"])

    def test_mode_tie_is_smallest_string(self):
        out = solution.to_columns([{"c": "b"}, {"c": "a"}, {"c": None}])
        self.assertEqual(out["c"], ["b", "a", "a"])

    def test_all_missing_column_dropped(self):
        out = solution.to_columns([{"x": None, "y": 1}, {"x": "", "y": 2}])
        self.assertEqual(out, {"y": [1, 2]})

    def test_bool_is_categorical(self):
        out = solution.to_columns([{"f": True}, {"f": True}, {"f": False}, {}])
        self.assertEqual(out["f"], [True, True, False, True])

    def test_mixed_types_are_categorical(self):
        out = solution.to_columns([{"v": 1}, {"v": "a"}, {"v": 1}, {}])
        self.assertEqual(out["v"], [1, "a", 1, 1])

    def test_zero_is_not_missing(self):
        out = solution.to_columns([{"n": 0}, {"n": 4}, {"n": None}])
        self.assertEqual(out["n"], [0, 4, 2.0])

    def test_empty_and_no_mutation(self):
        self.assertEqual(solution.to_columns([]), {})
        recs = [{"a": None}, {"a": 1}]
        snap = copy.deepcopy(recs)
        solution.to_columns(recs)
        solution.impute_summary(recs)
        self.assertEqual(recs, snap)

    def test_summary(self):
        recs = [{"age": 10, "plan": "basic"}, {"age": None, "plan": "basic"}, {"age": 20, "plan": "basic"}]
        self.assertEqual(solution.impute_summary(recs), {"age": 15.0})
        self.assertEqual(solution.impute_summary([{"a": 1}, {"b": 2}]), {"a": 1.0, "b": 2.0})


if __name__ == "__main__":
    unittest.main()
