"""Online feature lookup in front of a slow backend store.

Backend protocol:
    fetch(feature_set, entity_id) -> dict | None      (None = unknown entity)

Behaviour:
  * Results are cached per (feature_set, entity_id).
  * Unknown entities (backend returns None) are NOT cached.
  * Callers get a copy, so mutating a result never corrupts the cache.
"""


def make_key(feature_set, entity_id):
    return (feature_set, entity_id)


class FeatureService:
    def __init__(self, backend, cache):
        self._backend = backend
        self._cache = cache
        self.hits = 0
        self.misses = 0

    def get_features(self, entity_id, feature_set):
        key = make_key(feature_set, entity_id)
        cached = self._cache.get(key)
        if cached is not None:
            self.hits += 1
            return dict(cached)
        self.misses += 1
        value = self._backend.fetch(feature_set, entity_id)
        if value is None:
            return None
        self._cache.put(key, dict(value))
        return dict(value)
