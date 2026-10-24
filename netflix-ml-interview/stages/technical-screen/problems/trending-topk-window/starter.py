class TrendingTracker:
    def __init__(self, window):
        raise NotImplementedError

    def record(self, ts, title):
        raise NotImplementedError

    def top_k(self, now, k):
        raise NotImplementedError
