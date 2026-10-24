import heapq
from collections import Counter, deque


class TrendingTracker:
    def __init__(self, window):
        if window <= 0:
            raise ValueError("window must be positive")
        self.window = window
        self.events = deque()
        self.counts = Counter()
        self.last = None

    def record(self, ts, title):
        if self.last is not None and ts < self.last:
            raise ValueError("timestamps must be non-decreasing")
        self.last = ts
        self.events.append((ts, title))
        self.counts[title] += 1

    def _expire(self, now):
        while self.events and self.events[0][0] <= now - self.window:
            _, title = self.events.popleft()
            self.counts[title] -= 1
            if self.counts[title] == 0:
                del self.counts[title]

    def top_k(self, now, k):
        self._expire(now)
        return heapq.nsmallest(k, self.counts.items(), key=lambda kv: (-kv[1], kv[0]))
