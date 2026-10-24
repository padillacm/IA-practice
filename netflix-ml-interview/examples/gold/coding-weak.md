---
instance_id: 05-coding@practical
session_id: gold-coding-weak
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

OK I will write it now.

```python
def distinct_counts(events, window):
    out = []
    for i in range(len(events)):
        s = set()
        for j in range(len(events)):
            if events[j][0] > events[i][0] - window:
                s.add(events[j][1])
        out.append(len(s))
    return out
```

### T3 · interviewer · t=05m

Before we run it: what did you assume about the window, equal timestamps and invalid input? Please also state the complexity.

<meta>
problem_id: sliding-window-distinct
phase: main
hint: {id: h1, level: substantive, competency: problem_solving}
</meta>

### T4 · candidate · t=09m

I assumed it is all events in the window. Complexity is O(n) I think, there are two loops but they are simple.

### T5 · interviewer · t=11m

Hidden suite: 3 passed, 9 failed. Failure output: events [(0,'a'),(1,'b')], window 3 returned [2, 2], expected [1, 2].

<meta>
problem_id: sliding-window-distinct
phase: main
</meta>

### T6 · candidate · t=15m

Maybe I need to subtract the ones that are later? I am not sure. Let me try adding a check j <= i.

```python
            if j <= i and events[j][0] > events[i][0] - window:
```

### T7 · interviewer · t=17m

Hidden suite: 7 passed, 5 failed (missing ValueError cases, empty input for max_distinct, and a timeout on 200,000 events). Do you want to write tests?

<meta>
problem_id: sliding-window-distinct
phase: main
</meta>

### T8 · candidate · t=21m

I think the solution is correct, the remaining ones are edge cases that would not happen in practice. I do not really write tests for these, the interviewer should tell me what the expected output is.

### T9 · interviewer · t=23m

Thank you, that is our time.

<meta>
problem_id: sliding-window-distinct
phase: closed
</meta>
