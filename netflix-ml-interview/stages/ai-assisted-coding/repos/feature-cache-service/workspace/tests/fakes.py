class FakeClock:
    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class FakeBackend:
    """In-memory backend: data[feature_set][entity_id] -> dict. Counts calls."""

    def __init__(self, data):
        self.data = data
        self.fetch_calls = []
        self.fetch_many_calls = []

    def fetch(self, feature_set, entity_id):
        self.fetch_calls.append((feature_set, entity_id))
        return self.data.get(feature_set, {}).get(entity_id)

    def fetch_many(self, feature_set, entity_ids):
        self.fetch_many_calls.append((feature_set, list(entity_ids)))
        table = self.data.get(feature_set, {})
        return {e: table[e] for e in entity_ids if e in table}
