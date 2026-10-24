---
instance_id: 01-coding@practical
stage: coding
variant: practical
level: L5
rubric_version: 1
recommendation: fail
level_observed: none
scores:
  problem_solving: N
  code_quality_correctness: Y
  testing_verification: N
  complexity_optimality: Y
  production_followups: N
  culture_signals: N
evidence:
  problem_solving:
    - {turn_id: 2, quote: "Is the window exclusive on the left?"}
    - {turn_id: 4, quote: "This rebuilds the live list each time, so it is O(n times live size). It could be improved with a deque."}
  code_quality_correctness:
    - {turn_id: 6, quote: "if any(b[0] < a[0] for a, b in zip(events, events[1:])):"}
    - {turn_id: 6, quote: "while live[0][0] <= ts - window:"}
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
    - {turn_id: 10, quote: "I did not test those."}
hints: [{id: h1, level: nudge, competency: testing_verification}]
---

# Scorecard: 01-coding@practical

> Recommendation derived by the simulator's pedagogical rule; Netflix does not use a common scale.
> Recomendación derivada por la regla pedagógica del simulador; Netflix no usa una escala común.

## Summary
**Recommendation: fail. Observed level: none.**

The candidate ended with a correct O(n) deque-plus-counts solution. It passed the full hidden suite on the second run, and the candidate stated its time and space complexity without being asked. Two core competencies fall below the L5 bar, so the result is fail:
- **Problem solving:** the candidate asked only one clarifying question. Ties and input validation were never raised. They coded the slow version and only moved to the deque after the hidden suite reported a timeout.
- **Testing and verification:** they wrote only two tests, and only after a nudge. Ties, the window boundary, invalid inputs and a brute-force oracle were all left out. They said the solution was done without having checked it.

The scale follow-up got no concrete design step.

No level is observed. Even the L4 testing bar (at least three tests when asked) was not met. The session closed normally (`phase: closed`), with no uncovered signal points recorded.

## Scores and evidence

### problem_solving (core): N
- T2: "Is the window exclusive on the left?"
- T4: "This rebuilds the live list each time, so it is O(n times live size). It could be improved with a deque."

What was met:
- The candidate stated the baseline and its cost.
- They named the deque idea right after the first version.

What was missing:
- **Ambiguities not resolved before coding.** The only question was about the left boundary. The interviewer offered the tie semantics without being asked. Whether the input must be sorted and how to validate it was never raised, and the first submission missed the sorted check.
- **Intended technique only after the timeout.** The deque solution was implemented only after the hidden suite reported the timeout. The bar is met only partially.

**Model Yes answer:** Before coding, ask:
- Do equal timestamps all count as inside the window?
- Is the left edge exclusive?
- Should unsorted input or `window <= 0` raise?
- What should empty input return?

Then state the baseline: "Rebuild the window per event, O(n·w)." Then go straight to a deque of live events plus a title-to-count map, so each event is pushed and popped once, and write that version first.

### code_quality_correctness (core): Y
- T6: "if any(b[0] < a[0] for a, b in zip(events, events[1:])):"
- T6: "while live[0][0] <= ts - window:"

The second run passed the full hidden suite, which the L5 bar allows ("first or second run"). The code handles each edge case explicitly:
- the window check and the sorted check both raise `ValueError`;
- the exclusive left boundary is the `<=` eviction condition;
- empty input returns `[]`.

`max_distinct` reuses `distinct_counts`. Two small weaknesses: the `ValueError`s carry no messages, and all the logic sits in one function. These don't change the score.

### testing_verification (core): N (cap Y from nudge h1)
- T8: "These pass. I think the solution is fine."
- T10: "I did not write a brute force check."

The candidate wrote no tests unprompted. After the nudge (h1) they wrote two asserts: the statement example and empty input. Then they declared the solution done. When the interviewer asked about ties, the boundary and invalid inputs, the candidate admitted none were tested and argued correctness without checking it. There was no randomized oracle comparison. This also falls short of the L4 bar of at least three tests. It is not Strong No, because some tests were written when asked.

**Model Yes answer:** Before saying "done", write tests for:
- empty input returns `[]`;
- all-equal timestamps, e.g. `[(5,'a'),(5,'b'),(5,'a')]` gives `[1,2,2]`;
- an exact-boundary case, e.g. `[(0,'a'),(3,'b')]` with `window=3` gives `[1,1]`;
- `window=0` and unsorted input each raise `ValueError`.

Then add a loop of a few hundred random sorted logs that compares the output with an O(n²) brute force recomputing each window from scratch. If a case fails, fix it by reading the failing input.

### complexity_optimality (non-core): Y
- T6: "Time is O(n) amortized, space O(live events)."
- T4: "This rebuilds the live list each time, so it is O(n times live size)."

The candidate stated time and space for the final solution unprompted, and the final solution is O(n). They named the inefficiency of the first version. They did not name a remaining inefficiency in the final one, such as the extra list copy from `events[1:]` in the sorted check. Getting to the expected complexity took the timeout result, but the stated analysis meets the bar.

### production_followups (non-core): N
- T12: "Hmm, I have not thought much about it. We could use Kafka maybe."

Scale only came up when the interviewer asked. The answer names a technology but gives no design step and no concrete production concern.

**Model Yes answer:** "With many partitions, events are only sorted within a partition. I would key the stream by user or profile, so each window lives on one consumer. I would merge partitions with a watermark that allows bounded lateness, and keep the deque and count map as per-key state with snapshots for recovery. If we only need approximate counts at very high volume, a per-window HyperLogLog can replace the exact map."

### culture_signals (non-core): N
- T6: "I forgot the sorted check."
- T10: "I did not test those."

The candidate showed **candor**: they admitted the missed check and the missing tests plainly, without getting defensive. That meets the L4 bar.

At L5 the session gave no sign of **judgment** or **curiosity**. The candidate declared the solution "fine" without verification and argued correctness from belief ("I believe, so it should work"). They asked no question back on the real-time follow-up. The session gave no clear chance to disagree with a worse proposal, so the score rests on the judgment shown.

**Model Yes answer:** "Before I call it done, let me check ties and the boundary against a brute force. I'm not confident from reading the code alone." On the follow-up: "Do we need exact counts, or is approximate acceptable? That changes whether per-key exact state is worth it."

## Hints
- **h1** (nudge, T5) on testing_verification: the reminder to write their own tests. Cap applied: Y. The final score is N, below the cap.

## Uncovered signal points
None recorded. The final interviewer meta shows `phase: closed` with no uncovered points, so this was a normal close.

## Strengths and gaps
**Strengths**
- Reached a correct O(n) amortized deque-plus-counts solution and passed the full hidden suite on the second run.
- Stated the cost of the first version and the complexity of the final one without being asked.
- Said plainly what they missed (the sorted check, the untested cases).

**Gaps**
- Did not clarify every ambiguity before coding (ties, validation of unsorted input).
- Testing was the weakest area: tests came only after a nudge, there were only two, no boundary, tie or invalid-input cases, and no brute-force oracle.
- Declared the solution done without verifying it.
- No concrete design for the multi-partition, real-time follow-up.

## Study plan
1. **Testing and verification (core gap):** practise writing tests before declaring done, plus a randomized oracle comparison. Map entry `coding.testing_verification`: practice stage `coding`, resource "Write tests before declaring done, plus a randomized oracle comparison". For more brute-force and randomized comparison drills, see `technical-screen.verification_testing`.
2. **Problem solving (core gap):** list every ambiguity (ties, boundaries, validation, empty input) and state the brute-force baseline before writing code. Map entry `coding.problem_solving`: practice stage `coding`, resource "Practice clarifying questions and stating the brute-force baseline before coding".
3. **Production follow-ups:** study partition keys, state snapshots and the offline versus online split for streaming windows. Map entry `coding.production_followups`: course `recsys-course/16_production_serving/`, practice stage `coding`.
