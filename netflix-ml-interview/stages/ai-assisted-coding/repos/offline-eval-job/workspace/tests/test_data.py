import unittest

from offline_eval import dedupe_impressions, split_by_time
from tests.helpers import imp


class DataTest(unittest.TestCase):
    def test_dedupe_by_impression_id_keeps_first(self):
        rows = [imp("i1", "r1", "u", "a", 0, 1, 0), imp("i1", "r1", "u", "a", 0, 1, 1)]
        self.assertEqual(len(dedupe_impressions(rows)), 1)
        self.assertEqual(dedupe_impressions(rows)[0].clicked, 0)

    def test_repeat_exposure_in_different_requests_is_kept(self):
        rows = [imp("i1", "r1", "u", "a", 0, 1), imp("i2", "r2", "u", "a", 0, 5)]
        self.assertEqual(len(dedupe_impressions(rows)), 2)

    def test_split_boundary(self):
        rows = [imp("i1", "r1", "u", "a", 0, 9), imp("i2", "r2", "u", "a", 0, 10)]
        hist, ev = split_by_time(rows, 10)
        self.assertEqual([r.impression_id for r in hist], ["i1"])
        self.assertEqual([r.impression_id for r in ev], ["i2"])


if __name__ == "__main__":
    unittest.main()
