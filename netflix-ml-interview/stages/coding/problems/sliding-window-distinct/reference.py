from collections import Counter, deque


def distinct_counts(events, window):
    if window <= 0:
        raise ValueError("window must be positive")
    out = []
    live = deque()
    counts = Counter()
    prev = None
    for ts, title in events:
        if prev is not None and ts < prev:
            raise ValueError("events must be sorted by timestamp")
        prev = ts
        live.append((ts, title))
        counts[title] += 1
        while live[0][0] <= ts - window:
            _, old = live.popleft()
            counts[old] -= 1
            if counts[old] == 0:
                del counts[old]
        out.append(len(counts))
    return out


def max_distinct(events, window):
    counts = distinct_counts(events, window)
    return max(counts) if counts else 0
