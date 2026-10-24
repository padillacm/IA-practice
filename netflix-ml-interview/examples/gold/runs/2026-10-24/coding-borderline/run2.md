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
    - {turn_id: 4, quote: "This rebuilds the live list each time, so it is O(n times live size)."}
    - {turn_id: 4, quote: "It could be improved with a deque."}
  code_quality_correctness:
    - {turn_id: 6, quote: "if any(b[0] < a[0] for a, b in zip(events, events[1:])):"}
    - {turn_id: 6, quote: "while live[0][0] <= ts - window:"}
    - {turn_id: 4, quote: "return max(distinct_counts(events, window)) if events else 0"}
  testing_verification:
    - {turn_id: 8, quote: "assert distinct_counts([], 3) == []"}
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
**Recommendation: fail. Observed level: none.** This was a normal close: the final interviewer meta is `phase: closed` and lists no uncovered signal points. The transcript header says `05-coding@practical`, but this scorecard uses the instance id from the config, `01-coding@practical`.

The candidate first wrote a brute-force solution and gave its cost. After the hidden-suite feedback, they moved to the intended approach: a deque with a counts dictionary. The second version passed the full hidden suite, and the candidate stated its O(n) amortized time and its space use without being asked.

Two of the three core competencies are below the L5 bar, so the rule gives fail:
- **problem_solving:** the candidate resolved only part of the ambiguity before coding.
- **testing_verification:** after a nudge, they wrote only two tests. These did not cover ties, the window boundary or invalid inputs, and there was no brute-force oracle.

The answer to the production follow-up had no concrete design step. The L4 testing bar (at least three tests including a boundary case) is also not met, so no level is observed.

## Scores and evidence

### problem_solving: N (core)
- T2: "Is the window exclusive on the left?"
- T4: "This rebuilds the live list each time, so it is O(n times live size)."
- T4: "It could be improved with a deque."

The candidate asked one clarifying question and stated the brute-force cost. They did not ask about equal timestamps or what to do with unsorted input; the interviewer explained the ties. The deque idea came up in T4, but it was only built after the hidden suite reported a timeout and the missing sorted check. That is partial against the L5 bar.

**Model Yes answer (L5):** Before coding, ask whether equal timestamps fall in each other's window, whether the left edge is exclusive, and whether the sortedness check is part of the contract. State the baseline: rescanning the window for each event costs O(n·w). Then go straight to the intended structure: a deque of live events plus a dictionary from title to count. Pop from the left while `t_old <= t_i - window`, and report `len(counts)` for each event.

### code_quality_correctness: Y (core)
- T6: "if any(b[0] < a[0] for a, b in zip(events, events[1:])):"
- T6: "while live[0][0] <= ts - window:"
- T4: "return max(distinct_counts(events, window)) if events else 0"

The second run passed the full hidden suite, which the L5 bar allows. The code handles the cases the bar asks for:
- invalid input: unsorted events and `window <= 0`
- empty input: in `max_distinct`
- the boundary: through `<=`
- ties

Weak points: everything sits in one function, and the `ValueError` is raised without a message. This is a borderline Yes.

### testing_verification: N (core; nudge cap Y)
- T8: "assert distinct_counts([], 3) == []"
- T8: "These pass. I think the solution is fine."
- T10: "I did not write a brute force check."

The candidate wrote tests only after being reminded (hint h1). There were just two: the statement example and empty input. In T10 they said they had not tested equal timestamps, the boundary or invalid inputs, and had no oracle. They also said the solution was fine before checking those cases. This misses the L5 bar, and with only two tests it misses the L4 bar of three tests as well.

**Model Yes answer (L5):** Before saying "done", and without being asked, write these tests:
- `[]` gives `[]`
- `[(5,'a'),(5,'b'),(5,'a')]` with window 1 gives `[1,2,2]` (ties)
- `[(0,'a'),(3,'b')]` with window 3 gives `[1,1]` (exact boundary is excluded)
- `pytest.raises(ValueError)` for unsorted input and for `window=0`
- a randomized loop that compares against an O(n²) brute force that recounts the window for each index

If any case fails, fix it by reading the mismatch.

### complexity_optimality: Y
- T6: "Time is O(n) amortized, space O(live events)."
- T4: "This rebuilds the live list each time, so it is O(n times live size)."

The candidate stated time and space without being asked, and the final solution reaches the expected O(n). They named the inefficiency of the first version and fixed it once the hidden suite showed the timeout.

### production_followups: N
- T12: "Hmm, I have not thought much about it. We could use Kafka maybe."

The candidate only named a tool when prompted. They gave no concrete design step and named no specific concern such as volume or ordering.

**Model Yes answer (L5):** Partition the stream by `title_id` or `account_id` so each consumer keeps its own deque and counts. Note that events from different partitions arrive out of order, so you need a watermark or an allowed-lateness buffer before evicting from the window. Do exact counts online per partition, and use offline batch recomputation for global or late-corrected numbers. Mention HyperLogLog if global distinct counts become too large to keep exactly.

### culture_signals: N
- T6: "I forgot the sorted check."
- T10: "I did not test those."

The candidate was plainly honest about their mistakes and gaps without getting defensive (memo value: candor). That meets the L4 behavior. They did not disagree with any proposal or suggest a measurement to settle a question. They also declared the solution "fine" without checking it, which shows weak judgment.

**Model Yes answer (L5):** When pressed on edge cases, say "I'm not sure the boundary is right; let me prove it with a brute-force comparison" instead of "it should work". Push back with a technical reason when a proposal is worse, and accept the interviewer's point when the measurement supports it.

## Hints
- **h1** (nudge), competency `testing_verification`: caps it at Y. The score given, N, is within the cap.

## Uncovered signal points
None. This was a normal close and the final meta lists no uncovered points.

## Strengths and gaps
**Strengths:**
- Reached the intended deque and counts solution, and the second run passed the full hidden suite.
- Stated complexity accurately without being asked, and named the inefficiency of the first version.
- Was honest about what was missing.

**Gaps:**
- Did not resolve the ambiguities (ties, sortedness) before coding.
- Tests were thin, written only after a reminder, with no brute-force oracle. The solution was called "fine" without verification.
- No concrete design for distributed or streaming ingestion.

## Study plan
1. **testing_verification (core):** write tests before declaring done, and add a randomized comparison against a brute-force oracle. Practice the `coding` stage again (resource: "Write tests before declaring done, plus a randomized oracle comparison").
2. **problem_solving (core):** ask clarifying questions about ties and sortedness, and state the brute-force baseline before coding. Practice the `coding` stage again (resource: "Practice clarifying questions and stating the brute-force baseline before coding").
3. **production_followups:** study `recsys-course/16_production_serving/` (partition keys, snapshots, offline vs online split) and practice the `coding` follow-ups again.
