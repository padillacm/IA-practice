import unittest

from offline_eval import popularity_counts, popularity_ranking, run_eval
from tests.helpers import imp


def rows():
    return [
        # history (ts < 100): item "b" is clicked twice, "a" once
        imp("h1", "rh1", "u1", "b", 0, 10, 1),
        imp("h2", "rh2", "u2", "b", 0, 20, 1),
        imp("h3", "rh3", "u3", "a", 0, 30, 1),
        # evaluation request: logged order a, b, c; user clicked b
        imp("e1", "re1", "u4", "a", 0, 100, 0),
        imp("e2", "re1", "u4", "b", 1, 100, 1),
        imp("e3", "re1", "u4", "c", 2, 100, 0),
    ]


class JobTest(unittest.TestCase):
    def test_popularity_counts_use_history_only(self):
        counts = popularity_counts(rows(), 100)
        self.assertEqual(counts["b"], 2)
        self.assertEqual(counts["a"], 1)

    def test_popularity_ranking_ties_by_id(self):
        self.assertEqual(popularity_ranking({"a": 1, "b": 1}, ["b", "a", "c"]), ["a", "b", "c"])

    def test_baseline_beats_logged_when_clicked_item_is_popular(self):
        res = run_eval(rows(), 100, k=1)
        self.assertEqual(res["requests"], 1)
        self.assertEqual(res["logged"]["hit_rate"], 0.0)
        self.assertEqual(res["baseline"]["hit_rate"], 1.0)

    def test_duplicates_do_not_change_result(self):
        res_a = run_eval(rows(), 100, k=2)
        res_b = run_eval(rows() + rows()[3:], 100, k=2)
        self.assertEqual(res_a, res_b)

    def test_requests_without_clicks_are_skipped(self):
        only_no_click = [imp("e1", "r1", "u", "a", 0, 100, 0)]
        self.assertEqual(run_eval(only_no_click, 100)["requests"], 0)


if __name__ == "__main__":
    unittest.main()
