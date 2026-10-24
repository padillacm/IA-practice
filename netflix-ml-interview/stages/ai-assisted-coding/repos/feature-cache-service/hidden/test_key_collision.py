"""Hidden check: the cache key must include the feature set.

Fails if the key is built from entity_id alone (e.g. make_key returns str(entity_id)),
because the second lookup would return the first feature set's cached values.
"""
import unittest

from feature_service import FeatureService, TTLCache


class _Backend:
    def fetch(self, feature_set, entity_id):
        return {"source": feature_set, "id": entity_id}

    def fetch_many(self, feature_set, entity_ids):
        return {e: {"source": feature_set, "id": e} for e in entity_ids}


class KeyCollisionTest(unittest.TestCase):
    def test_same_entity_different_feature_sets(self):
        svc = FeatureService(_Backend(), TTLCache(10, 60, clock=lambda: 0.0))
        a = svc.get_features("42", "user")
        b = svc.get_features("42", "title")
        self.assertEqual(a["source"], "user")
        self.assertEqual(b["source"], "title")

    def test_separator_collision(self):
        svc = FeatureService(_Backend(), TTLCache(10, 60, clock=lambda: 0.0))
        a = svc.get_features("b:c", "a")
        b = svc.get_features("c", "a:b")
        self.assertEqual((a["source"], a["id"]), ("a", "b:c"))
        self.assertEqual((b["source"], b["id"]), ("a:b", "c"))


if __name__ == "__main__":
    unittest.main()
