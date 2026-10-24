import unittest

from feature_service import FeatureService, TTLCache
from tests.fakes import FakeBackend, FakeClock

DATA = {
    "user": {"u1": {"age_bucket": 3}, "u2": {"age_bucket": 5}},
    "title": {"t1": {"genre": "drama"}},
}


class FeatureServiceTest(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.backend = FakeBackend(DATA)
        self.cache = TTLCache(max_size=100, ttl=60, clock=self.clock)
        self.svc = FeatureService(self.backend, self.cache)

    def test_miss_then_hit(self):
        self.assertEqual(self.svc.get_features("u1", "user"), {"age_bucket": 3})
        self.assertEqual(self.svc.get_features("u1", "user"), {"age_bucket": 3})
        self.assertEqual(len(self.backend.fetch_calls), 1)
        self.assertEqual((self.svc.hits, self.svc.misses), (1, 1))

    def test_refetch_after_ttl(self):
        self.svc.get_features("u1", "user")
        self.clock.advance(61)
        self.svc.get_features("u1", "user")
        self.assertEqual(len(self.backend.fetch_calls), 2)

    def test_unknown_entity_not_cached(self):
        self.assertIsNone(self.svc.get_features("zz", "user"))
        self.assertIsNone(self.svc.get_features("zz", "user"))
        self.assertEqual(len(self.backend.fetch_calls), 2)

    def test_result_is_a_copy(self):
        first = self.svc.get_features("u1", "user")
        first["age_bucket"] = 99
        self.assertEqual(self.svc.get_features("u1", "user"), {"age_bucket": 3})

    def test_distinct_feature_sets_do_not_share_entries(self):
        backend = FakeBackend({"user": {"x": {"v": 1}}, "title": {"x": {"v": 2}}})
        svc = FeatureService(backend, TTLCache(10, 60, clock=self.clock))
        self.assertEqual(svc.get_features("x", "user"), {"v": 1})
        self.assertEqual(svc.get_features("x", "title"), {"v": 2})


if __name__ == "__main__":
    unittest.main()
