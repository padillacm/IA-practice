---
instance_id: 01-coding@practical
stage: coding
variant: practical
level: L5
rubric_version: 1
recommendation: fail
level_observed: none
scores:
  problem_solving: Y
  code_quality_correctness: Y
  testing_verification: N
  complexity_optimality: Y
  production_followups: N
  culture_signals: N
evidence:
  problem_solving:
    - {turn_id: 2, quote: "Is the window exclusive on the left?"}
    - {turn_id: 4, quote: "This rebuilds the live list each time, so it is O(n times live size)."}
    - {turn_id: 4, quote: "It could be improved with a deque."}
  code_quality_correctness:
    - {turn_id: 6, quote: "if any(b[0] < a[0] for a, b in zip(events, events[1:])):"}
    - {turn_id: 6, quote: "I will add it and replace the list with a deque, popping from the left while the oldest timestamp is out of the window, with a counts dictionary for the distinct titles."}
  testing_verification:
    - {turn_id: 8, quote: "These pass. I think the solution is fine."}
    - {turn_id: 10, quote: "I did not write a brute force check."}
  complexity_optimality:
    - {turn_id: 6, quote: "Time is O(n) amortized, space O(live events)."}
    - {turn_id: 4, quote: "This rebuilds the live list each time, so it is O(n times live size)."}
  production_followups:
    - {turn_id: 12, quote: "Hmm, I have not thought much about it. We could use Kafka maybe."}
  culture_signals:
    - {turn_id: 6, quote: "I forgot the sorted check."}
    - {turn_id: 10, quote: "The boundary is handled by the <= and ties are inside the window, I believe, so it should work."}
hints: [{id: h1, level: nudge, competency: testing_verification}]
---

# Scorecard: 01-coding@practical

> Recommendation derived by the simulator's pedagogical rule; Netflix does not use a common scale.
> Recomendación derivada por la regla pedagógica del simulador; Netflix no usa una escala común.

## Summary
**Recommendation: fail. Observed level: none.**

The session ended normally. The last interviewer meta says `phase: closed` and lists no uncovered points. The transcript header says `05-coding@practical` but the config says `01-coding@practical`, so this scorecard uses the config id.

The candidate solved the main problem. They asked about the left boundary of the window, gave the cost of the brute force and named the deque before any hint. After one round of hidden-suite feedback, the deque plus counts-dictionary solution passed the full suite on the second run, and the candidate stated its O(n) amortized time and its space without being asked.

Testing was the weak point. Even after a nudge, the candidate wrote only two asserts (the statement example and empty input). They did not test ties, the window boundary or invalid input, wrote no brute-force oracle, and said the solution was "fine" before verifying it. Their answer on the production follow-up had no design content. On culture, they were candid about their mistakes, but they declared the work done without evidence and showed no L5-level judgment.

Under the fixed rule, one core competency is N and two non-core competencies are N, so the result is `fail`. On level: testing does not reach even the L4 bar (at least three tests when asked), so no level has every core competency at Y or better, and `level_observed` is `none`.

## Scores and evidence

### problem_solving (core): Y
- T2: "Is the window exclusive on the left?"
- T4: "This rebuilds the live list each time, so it is O(n times live size)."
- T4: "It could be improved with a deque."

The candidate asked a clarifying question about the boundary before coding. The interviewer's answer also settled ties. The candidate stated the cost of the baseline and named the intended structure (a deque) before any hint was recorded, then implemented it with a counts dictionary. This is a borderline Y. Only one question was asked, and the efficient version was implemented only after the timeout feedback. Still, the technique was named without a hint, so the bar is met.

### code_quality_correctness (core): Y
- T6: "if any(b[0] < a[0] for a, b in zip(events, events[1:])):"
- T6: "I will add it and replace the list with a deque, popping from the left while the oldest timestamp is out of the window, with a counts dictionary for the distinct titles."

The second version passes the full hidden suite (second run, which the L5 bar allows). It validates sorted order and `window`. It handles empty input: the loop does not run, and `max_distinct` has an empty guard. It handles the half-open boundary with `<=` and does not change the input. Weaker points: `ValueError` is raised with no message, and the logic sits in one function rather than small helpers. These keep the score at Y, not SY.

### testing_verification (core): N (hint cap: Y)
- T8: "These pass. I think the solution is fine."
- T10: "I did not write a brute force check."

The candidate wrote tests only after the nudge (h1), and only two of them. They covered the example and empty input, but not ties, the window boundary or invalid input. They declared the solution done without an oracle comparison. When asked about the missing cases, they reasoned about them instead of testing them. This does not reach the L5 bar, or the L4 bar of three tests. It is not SN because tests were written when asked.

**What a Yes-level answer would have looked like:** Before saying "done", and without being prompted, write:
- a test where equal timestamps share a window, e.g. `[(0,'a'),(0,'b'),(0,'a')]` with `window=1` gives `[1,2,2]`;
- an exact-boundary test, e.g. `[(0,'a'),(3,'b')]` with `window=3` gives `[1,1]`, because the event at t=0 drops out;
- `pytest.raises(ValueError)` for unsorted input and for `window=0`;
- a brute-force oracle (rescan all `j <= i` with `t_j > t_i - window`), compared with `distinct_counts` on a few hundred random small logs, and any mismatch fixed from the failing input.

### complexity_optimality (non-core): Y
- T6: "Time is O(n) amortized, space O(live events)."
- T4: "This rebuilds the live list each time, so it is O(n times live size)."

The candidate gave time and space complexity without being asked and reached the expected O(n) amortized solution. For the first version, they also named its inefficiency and how to fix it.

### production_followups (non-core): N
- T12: "Hmm, I have not thought much about it. We could use Kafka maybe."

The candidate named a tool but gave no concrete design step. There was no partition key, no handling of out-of-order events across partitions, and no state or snapshot strategy. They raised nothing about scale before the question was asked.

**What a Yes-level answer would have looked like:** Partition the stream by `title_id` or by user/session. For each partition, keep the deque and counts as state. Handle cross-partition skew with a watermark: buffer events up to an allowed lateness, then process them in timestamp order. Checkpoint the window state so it survives a restart. If needed, compute global distinct counts in a separate merge step, or approximately with HyperLogLog sketches per window.

### culture_signals (non-core): N
- T6: "I forgot the sorted check."
- T10: "The boundary is handled by the <= and ties are inside the window, I believe, so it should work."

The candidate showed **candor**: they admitted the missing sorted check plainly and without defensiveness, which meets the L4 behavior. On **judgment**, they declared the solution fine based on two tests and relied on "I believe, so it should work" instead of checking. On **curiosity**, they did not engage with the streaming extension. No L5 behavior was shown, such as defending a technical position with a reason or proposing a measurement to settle a question.

**What a Yes-level answer would have looked like:** When the interviewer asks about ties and boundaries, say "I'm not sure; let me prove it". Then add the boundary tests and an oracle comparison, report the result, and change the code if a case fails. In the follow-up, propose a concrete design and name the trade-off. For example: "partition by title, and accept approximate global counts to avoid a shuffle", and say how you would measure the error.

## Hints
- **h1** (nudge, testing_verification, T5): the interviewer reminded the candidate to write their own tests. This caps testing_verification at **Y**. The final score is N, which is below the cap.

## Uncovered signal points
None recorded. The session ended normally (the last interviewer meta has `phase: closed` and no `uncovered_signal_points`).

## Strengths and gaps
**Strengths**
- Gave the brute-force cost and named the deque technique before any hint.
- Turned the hidden-suite failures into a correct O(n) fix on the second run, including the sorted-input check.
- Stated time and space complexity without being asked.
- Admitted mistakes plainly.

**Gaps**
- Testing was thin even after a nudge: no ties, boundary or invalid-input tests, no brute-force oracle, and the solution was declared done too early.
- Gave no concrete design for the real-time, multi-partition extension.
- Asked few clarifying questions before coding. Ties and unsorted input were handled only after the interviewer's answer or the hidden suite caught them.

## Study plan
1. **Testing and verification (core gap):** before saying "done", always write boundary tests (empty input, ties, the exact window edge, invalid input) and a randomized comparison against a brute-force oracle. Study-map entry `coding.testing_verification`: practice stage `coding`; resource "Write tests before declaring done, plus a randomized oracle comparison".
2. **Production follow-ups:** practise turning "real time, many partitions" into a partition key, a state or checkpoint strategy, and handling of late or out-of-order events. Study-map entry `coding.production_followups`: course `recsys-course/16_production_serving/`; practice stage `coding`; resource "Scale and concurrency follow-ups: partition keys, snapshots, offline vs online split".
3. **Judgment and culture signals:** replace "I believe it should work" with a quick check, and be ready to defend a position with a measurement. Study-map entry `coding.culture_signals`: practice stage `culture`; resource "Netflix culture memo: jobs.netflix.com/culture".
