---
variant: practical
roles: [mle, rs, ds]
levels: [L4, L5, L6]
title: Sliding window of distinct titles
minutes: 35
---
# Sliding window of distinct titles

A playback log is a list of `(timestamp_seconds, title_id)` events sorted by timestamp (ties possible).

Implement `distinct_counts(events, window)`: for every event `i` return the number of distinct titles among the events
`j <= i` (by index) with `timestamp_j > timestamp_i - window`, i.e. the window `(t_i - window, t_i]`.

- `window > 0`; raise `ValueError` if `events` is not sorted by timestamp or `window <= 0`.
- Return a list with one count per event, in input order.
- Single pass; O(n) time apart from hashing.

Example: `events = [(0,"a"), (1,"b"), (2,"a"), (10,"c")], window = 3` -> `[1, 2, 2, 1]`.

Also implement `max_distinct(events, window)` returning the maximum of that list (0 for no events).

Write your own tests (include equal timestamps and empty input).
