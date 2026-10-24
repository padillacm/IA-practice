---
instance_id: 05-coding@practical
session_id: gold-coding-strong
stage: coding
variant: practical
phase: vo1
role: mle
level: L5
lang: en
domain: recsys
time_scale: 1.0
budget_minutes: 60
---

### T1 · interviewer · t=00m

Hi, I am Arjun Mehta, a Senior Software Engineer. Here is the problem.

A playback log is a list of `(timestamp_seconds, title_id)` events sorted by timestamp (ties possible). Implement `distinct_counts(events, window)`: for every event `i` return the number of distinct titles among the events `j <= i` (by index) with `timestamp_j > timestamp_i - window`, i.e. the window `(t_i - window, t_i]`. `window > 0`; raise `ValueError` if `events` is not sorted or `window <= 0`. Return one count per event in input order. Single pass, O(n) time apart from hashing. Example: `events = [(0,"a"), (1,"b"), (2,"a"), (10,"c")], window = 3` gives `[1, 2, 2, 1]`. Also implement `max_distinct(events, window)`. Write your own tests (include equal timestamps and empty input).

<meta>
problem_id: sliding-window-distinct
phase: intro
</meta>

### T2 · candidate · t=02m

Let me confirm a few things. Is the window (t_i - window, t_i], exclusive on the left, so with window 3 an event at time 0 has expired at time 3? And events with equal timestamps are all inside each other's window, correct? Titles are hashable? Should the sorted check be a full pass before computing, or may I validate while iterating? The brute force is: for each i, scan back while the timestamp is in the window and put the titles in a set, which is O(n times window size) and O(n^2) in the worst case when all events share a timestamp. Since the input is sorted by time, both ends of the window only move forward, so I can keep a deque of the live events plus a dictionary of counts per title and get O(n) amortized.

### T3 · interviewer · t=04m

Yes to all: exclusive on the left, ties are mutually inside, titles are hashable. Validate up front, then compute.

<meta>
problem_id: sliding-window-distinct
phase: main
</meta>

### T4 · candidate · t=09m

Here is the code.

```python
from collections import deque

def _validate(events, window):
    if window <= 0:
        raise ValueError("window must be positive")
    for a, b in zip(events, events[1:]):
        if b[0] < a[0]:
            raise ValueError("events must be sorted by timestamp")

def distinct_counts(events, window):
    _validate(events, window)
    live, counts, out = deque(), {}, []
    for ts, title in events:
        live.append((ts, title))
        counts[title] = counts.get(title, 0) + 1
        while live[0][0] < ts - window:
            _, old = live.popleft()
            counts[old] -= 1
            if counts[old] == 0:
                del counts[old]
        out.append(len(counts))
    return out

def max_distinct(events, window):
    return max(distinct_counts(events, window), default=0)
```

Complexity: each event is appended once and popped at most once, so O(n) time and O(w) space where w is the maximum number of live events; the dictionary operations are O(1) average. One remaining inefficiency: in the worst case all events share a timestamp and the deque holds everything, so space is O(n).

### T5 · interviewer · t=11m

I ran it against my hidden suite: 11 passed, 1 failed. Failing case: events [(0,'a'),(3,'b')], window 3, expected [1, 1], got [1, 2].

<meta>
problem_id: sliding-window-distinct
phase: main
</meta>

### T6 · candidate · t=15m

Reading that failure: at ts=3 the event at 0 should be out, because the window is (0, 3] and 0 is not greater than 0. My loop pops only when the old timestamp is strictly less than ts - window, so an event exactly at the boundary stays. The condition must be <=. Fixing it: `while live[0][0] <= ts - window:`. Now the tests I should have written first. I will write boundary tests, ties, empty input, the validation errors and a randomized comparison against a brute force oracle.

```python
import random

def brute(events, window):
    return [len({t for ts2, t in events[:i+1] if ts2 > ts - window}) for i, (ts, _) in enumerate(events)]

def test_all():
    assert distinct_counts([], 3) == []
    assert distinct_counts([(0,'a'),(1,'b'),(2,'a'),(10,'c')], 3) == [1,2,2,1]
    assert distinct_counts([(0,'a'),(3,'b')], 3) == [1,1]      # boundary
    assert distinct_counts([(5,'a'),(5,'b'),(5,'a')], 1) == [1,2,2]  # ties
    assert max_distinct([], 2) == 0
    for bad in [([(2,'a'),(1,'b')], 3), ([(0,'a')], 0)]:
        try:
            distinct_counts(*bad); assert False
        except ValueError:
            pass
    for _ in range(500):
        ts = sorted(random.randint(0, 30) for _ in range(random.randint(0, 25)))
        ev = [(t, random.choice('abcd')) for t in ts]
        w = random.randint(1, 8)
        assert distinct_counts(ev, w) == brute(ev, w)
```

The oracle is O(n^2) but independent of the deque logic, so a boundary bug like mine shows up as a failing random case.

### T7 · interviewer · t=18m

All green on my side now. One thing: for simplicity I would just build `set(title for ts2, title in events[:i+1] if ts2 > ts - window)` for each event. n is a few thousand in the logs I know. Wouldn't that be fine and easier to read?

<meta>
problem_id: sliding-window-distinct
phase: main
culture_probe: {value: candor}
</meta>

### T8 · candidate · t=22m

For a few thousand events it works and I use it as my oracle. I would not ship it as the implementation, though. It scans the whole prefix for every event, so it is O(n^2) and for a day of playback events for one member, say 100,000 events, that is about 10^10 steps. My reason is the cost at the size where this runs, not style, and I can settle it with a measurement: time both on 10^4, 10^5 and 10^6 random events and see where the brute force crosses a second. If you tell me the inputs are bounded by a few thousand, I agree the simple version is the better trade, and I would keep the fast one only behind a size threshold.

### T9 · interviewer · t=25m

Production follow-up: events now arrive in real time from many partitions, slightly out of order. How would you extend this?

<meta>
problem_id: sliding-window-distinct
phase: main
</meta>

### T10 · candidate · t=31m

I would partition by member id so each member's stream is handled by one worker and ordering within a member is preserved, keep the deque and counts as per-member state, and add a watermark: events later than the allowed lateness (say 30 seconds) are sent to a late-event side output and reconciled in a batch job instead of mutating windows already emitted. State is bounded by the window length, and I would checkpoint it periodically so a restart replays from the checkpoint. Offline versus online: the batch version of this function is the reference for validating the stream results.

### T11 · interviewer · t=34m

Good. That is our time.

<meta>
problem_id: sliding-window-distinct
phase: closed
</meta>
