"""Hidden check: an entry is expired at exactly t + ttl (valid for t <= now < t + ttl).

Fails if the expiry comparison becomes `now > expires_at`, or if TTL is evaluated against a
different clock than the injected one.
"""
import unittest

from feature_service import TTLCache


class TTLBoundaryTest(unittest.TestCase):
    def test_expired_at_exact_boundary(self):
        now = [0.0]
        cache = TTLCache(max_size=4, ttl=10, clock=lambda: now[0])
        cache.put("k", "v")
        now[0] = 9.999
        self.assertEqual(cache.get("k"), "v")
        now[0] = 10.0
        self.assertIsNone(cache.get("k"))

    def test_per_entry_ttl_boundary(self):
        now = [100.0]
        cache = TTLCache(max_size=4, ttl=60, clock=lambda: now[0])
        cache.put("k", "v", ttl=5)
        now[0] = 105.0
        self.assertIsNone(cache.get("k"))


if __name__ == "__main__":
    unittest.main()
