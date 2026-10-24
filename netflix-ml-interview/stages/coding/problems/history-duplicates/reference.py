def has_duplicate(title_ids):
    return len(set(title_ids)) != len(title_ids)


def has_duplicate_within(title_ids, k):
    last = {}
    for i, x in enumerate(title_ids):
        if x in last and i - last[x] <= k:
            return True
        last[x] = i
    return False


def has_near_duplicate(start_times, k, t):
    """Sliding window of the last k records, bucketed by value // (t + 1)."""
    if k <= 0 or t < 0:
        return False
    width = t + 1
    buckets = {}  # bucket id -> value (at most one value per bucket inside the window)
    for i, x in enumerate(start_times):
        b = x // width
        if b in buckets:
            return True
        if b - 1 in buckets and x - buckets[b - 1] <= t:
            return True
        if b + 1 in buckets and buckets[b + 1] - x <= t:
            return True
        buckets[b] = x
        if i >= k:
            del buckets[start_times[i - k] // width]
    return False
