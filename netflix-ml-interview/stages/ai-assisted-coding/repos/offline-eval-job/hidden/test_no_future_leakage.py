"""Hidden check: the popularity baseline must not see events at or after the cutoff.

Fails if popularity_counts (or run_eval's use of it) counts clicks with ts >= cutoff_ts, for example
when a trailing window is anchored to max(ts) of all rows instead of the cutoff.
"""
import unittest

from offline_eval import Impression, popularity_counts, run_eval

CUT = 100


def rows():
    return [
        Impression("h1", "rh1", "u1", "old", 0, 10, 1),
        # item "future" is only clicked AFTER the cutoff, many times
        Impression("f1", "rf1", "u2", "future", 0, 150, 1),
        Impression("f2", "rf2", "u3", "future", 0, 160, 1),
        Impression("f3", "rf3", "u4", "future", 0, 170, 1),
        # evaluation request at the cutoff: user clicks "old"
        Impression("e1", "re1", "u5", "future", 0, 100, 0),
        Impression("e2", "re1", "u5", "old", 1, 100, 1),
    ]


class NoFutureLeakageTest(unittest.TestCase):
    def test_counts_ignore_future(self):
        counts = popularity_counts(rows(), CUT)
        self.assertEqual(counts.get("future", 0), 0)
        self.assertEqual(counts["old"], 1)

    def test_baseline_not_inflated_by_future_clicks(self):
        res = run_eval(rows(), CUT, k=1)
        # with history only, "old" is the most popular candidate, so the baseline ranks it first
        self.assertEqual(res["baseline"]["hit_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
