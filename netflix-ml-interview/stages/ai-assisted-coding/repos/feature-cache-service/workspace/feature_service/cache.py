"""Bounded LRU cache with per-entry time-to-live.

Contract:
  * An entry stored at time t with ttl T is valid for t <= now < t + T.
    At exactly now == t + T it is expired.
  * Capacity is `max_size`; inserting beyond it evicts the least recently used entry.
    Both `get` hits and `put` count as a use.
  * The clock is injectable (a zero-argument callable returning seconds) so tests are deterministic.
"""
from collections import OrderedDict
import time


class TTLCache:
    def __init__(self, max_size, ttl, clock=time.monotonic):
        if max_size < 1:
            raise ValueError("max_size must be >= 1")
        if ttl <= 0:
            raise ValueError("ttl must be > 0")
        self.max_size = max_size
        self.ttl = ttl
        self._clock = clock
        self._data = OrderedDict()  # key -> (value, expires_at)

    def _expired(self, expires_at, now):
        return now >= expires_at

    def get(self, key, default=None):
        item = self._data.get(key)
        if item is None:
            return default
        value, expires_at = item
        if self._expired(expires_at, self._clock()):
            del self._data[key]
            return default
        self._data.move_to_end(key)
        return value

    def put(self, key, value, ttl=None):
        ttl = self.ttl if ttl is None else ttl
        if ttl <= 0:
            raise ValueError("ttl must be > 0")
        self._data[key] = (value, self._clock() + ttl)
        self._data.move_to_end(key)
        while len(self._data) > self.max_size:
            self._data.popitem(last=False)

    def invalidate(self, key):
        self._data.pop(key, None)

    def __len__(self):
        return len(self._data)
