---
variant: practical
roles: [mle, rs, ds]
levels: [L4, L5, L6]
title: Duplicates in viewing history
minutes: 35
---
# Duplicates in viewing history

A member's viewing history is a list of records. Implement three functions, each building on the previous one.

1. `has_duplicate(title_ids)`: True if any title id appears more than once.
2. `has_duplicate_within(title_ids, k)`: True if two equal ids appear at positions `i != j` with `|i - j| <= k`
   (the same title replayed within `k` consecutive records). `k >= 0`; `k = 0` is always False.
3. `has_near_duplicate(start_times, k, t)`: `start_times` are integer playback start times (seconds) of consecutive
   records of the same title, possibly noisy because of client clock skew. Return True if there are `i != j` with
   `|i - j| <= k` and `|start_times[i] - start_times[j]| <= t`. `t >= 0`.

Part 3 should be better than comparing every pair; explain the idea of **bucketing** you use and its complexity.

Write your own tests as you go.
