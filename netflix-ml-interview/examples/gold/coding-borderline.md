---
instance_id: 05-coding@practical
session_id: gold-coding-borderline
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

### T2 · candidate · t=03m

So for each event I count the distinct titles in the window. I will keep a list of the live events and a set. Titles are strings. Is the window exclusive on the left?

### T3 · interviewer · t=05m

Yes, exclusive on the left. Equal timestamps are all inside each other's window.

<meta>
problem_id: sliding-window-distinct
phase: main
</meta>

### T4 · candidate · t=12m

```python
def distinct_counts(events, window):
    if window <= 0:
        raise ValueError
    out = []
    live = []
    for ts, title in events:
        live.append((ts, title))
        live = [(t, x) for t, x in live if t > ts - window]
        out.append(len({x for t, x in live}))
    return out

def max_distinct(events, window):
    return max(distinct_counts(events, window)) if events else 0
```
This rebuilds the live list each time, so it is O(n times live size). It could be improved with a deque.

### T5 · interviewer · t=14m

Hidden suite: 10 passed, 2 failed. The unsorted-input case does not raise, and the 200,000-event case times out. What is your next step? Remember you have to write your own tests.

<meta>
problem_id: sliding-window-distinct
phase: main
hint: {id: h1, level: nudge, competency: testing_verification}
</meta>

### T6 · candidate · t=20m

I forgot the sorted check. I will add it and replace the list with a deque, popping from the left while the oldest timestamp is out of the window, with a counts dictionary for the distinct titles.

```python
from collections import deque

def distinct_counts(events, window):
    if window <= 0:
        raise ValueError
    if any(b[0] < a[0] for a, b in zip(events, events[1:])):
        raise ValueError
    live, counts, out = deque(), {}, []
    for ts, title in events:
        live.append((ts, title))
        counts[title] = counts.get(title, 0) + 1
        while live[0][0] <= ts - window:
            _, old = live.popleft()
            counts[old] -= 1
            if not counts[old]:
                del counts[old]
        out.append(len(counts))
    return out
```
Time is O(n) amortized, space O(live events).

### T7 · interviewer · t=22m

All hidden tests pass now. Show me your own tests.

<meta>
problem_id: sliding-window-distinct
phase: main
</meta>

### T8 · candidate · t=26m

```python
assert distinct_counts([(0,'a'),(1,'b'),(2,'a'),(10,'c')], 3) == [1,2,2,1]
assert distinct_counts([], 3) == []
```
These pass. I think the solution is fine.

### T9 · interviewer · t=28m

What about equal timestamps, the window boundary, or the invalid inputs?

<meta>
problem_id: sliding-window-distinct
phase: main
</meta>

### T10 · candidate · t=32m

I did not test those. The boundary is handled by the <= and ties are inside the window, I believe, so it should work. I did not write a brute force check.

### T11 · interviewer · t=34m

Last question: events now arrive in real time from many partitions. Any thoughts?

<meta>
problem_id: sliding-window-distinct
phase: main
</meta>

### T12 · candidate · t=38m

Hmm, I have not thought much about it. We could use Kafka maybe.

### T13 · interviewer · t=40m

Thank you, that is our time.

<meta>
problem_id: sliding-window-distinct
phase: closed
</meta>
