import unittest

from feature_service.cache import TTLCache
from tests.fakes import FakeClock


class TTLCacheTest(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.cache = TTLCache(max_size=2, ttl=10, clock=self.clock)

    def test_put_get(self):
        self.cache.put("a", 1)
        self.assertEqual(self.cache.get("a"), 1)

    def test_missing_returns_default(self):
        self.assertIsNone(self.cache.get("nope"))
        self.assertEqual(self.cache.get("nope", 7), 7)

    def test_expires_after_ttl(self):
        self.cache.put("a", 1)
        self.clock.advance(11)
        self.assertIsNone(self.cache.get("a"))
        self.assertEqual(len(self.cache), 0)

    def test_valid_before_ttl(self):
        self.cache.put("a", 1)
        self.clock.advance(9)
        self.assertEqual(self.cache.get("a"), 1)

    def test_lru_eviction(self):
        self.cache.put("a", 1)
        self.cache.put("b", 2)
        self.cache.get("a")
        self.cache.put("c", 3)
        self.assertIsNone(self.cache.get("b"))
        self.assertEqual(self.cache.get("a"), 1)
        self.assertEqual(self.cache.get("c"), 3)

    def test_overwrite_refreshes_ttl(self):
        self.cache.put("a", 1)
        self.clock.advance(8)
        self.cache.put("a", 2)
        self.clock.advance(8)
        self.assertEqual(self.cache.get("a"), 2)

    def test_per_entry_ttl(self):
        self.cache.put("a", 1, ttl=3)
        self.clock.advance(4)
        self.assertIsNone(self.cache.get("a"))

    def test_invalidate(self):
        self.cache.put("a", 1)
        self.cache.invalidate("a")
        self.assertIsNone(self.cache.get("a"))

    def test_bad_args(self):
        with self.assertRaises(ValueError):
            TTLCache(max_size=0, ttl=1)
        with self.assertRaises(ValueError):
            TTLCache(max_size=1, ttl=0)


if __name__ == "__main__":
    unittest.main()
