"""Popularity baseline built ONLY from history before the evaluation cutoff."""
from collections import Counter


def popularity_counts(rows, cutoff_ts):
    """Click counts per item using rows strictly before cutoff_ts."""
    counts = Counter()
    for r in rows:
        if r.ts < cutoff_ts and r.clicked:
            counts[r.item_id] += 1
    return counts


def popularity_ranking(counts, candidates):
    """Order candidate item ids by popularity (desc); ties broken by item id for determinism."""
    return sorted(candidates, key=lambda i: (-counts.get(i, 0), i))
