"""Logged impressions.

One row per item shown in a slate. The logging pipeline is at-least-once, so the same impression
(same impression_id) can appear more than once; repeated exposure of an item to a user in different
requests is legitimate and must be kept.
"""
from collections import namedtuple

Impression = namedtuple("Impression", "impression_id request_id user_id item_id position ts clicked")


def dedupe_impressions(rows):
    """Drop repeated deliveries of the same impression_id, keeping the first one seen."""
    seen = set()
    out = []
    for r in rows:
        if r.impression_id in seen:
            continue
        seen.add(r.impression_id)
        out.append(r)
    return out


def split_by_time(rows, cutoff_ts):
    """Return (history, evaluation): history has ts < cutoff_ts, evaluation has ts >= cutoff_ts."""
    history = [r for r in rows if r.ts < cutoff_ts]
    evaluation = [r for r in rows if r.ts >= cutoff_ts]
    return history, evaluation


def group_slates(rows):
    """Group rows by request_id; each slate is ordered by position."""
    slates = {}
    for r in rows:
        slates.setdefault(r.request_id, []).append(r)
    return {k: sorted(v, key=lambda r: r.position) for k, v in slates.items()}
