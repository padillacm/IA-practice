---
variant: ml-coding
roles: [mle]
levels: [L4, L5, L6]
title: Trending titles in a sliding time window
minutes: 40
---
# Trending titles in a sliding time window

Implement `TrendingTracker(window)` over a stream of play events:

- `record(ts, title)`: a play of `title` at integer second `ts`. Calls arrive with non-decreasing `ts`; raise
  `ValueError` if `ts` goes backwards.
- `top_k(now, k)`: the `k` titles with the most plays in the window `(now - window, now]`, as a list of
  `(title, count)` sorted by count descending, then title ascending. `now` is non-decreasing across calls and at least the
  last recorded `ts`. Fewer than `k` items are returned if fewer titles are active.
- Memory must be bounded by the events inside the window, not by the whole history.

`window > 0`, `k > 0`. Write your own tests, including events that sit exactly on the window boundary.
