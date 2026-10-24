---
instance_id: 05-coding@practical
stage: coding
variant: practical
level: L5
rubric_version: 1
recommendation: pass
level_observed: L5
scores:
  problem_solving: Y
  code_quality_correctness: Y
  testing_verification: SY
  complexity_optimality: Y
  production_followups: Y
  culture_signals: Y
evidence:
  problem_solving:
    - turn_id: 2
      quote: "The brute force is: for each i, scan back while the timestamp is in the window"
    - turn_id: 2
      quote: both ends of the window only move forward
  code_quality_correctness:
    - turn_id: 4
      quote: "def _validate(events, window):"
    - turn_id: 6
      quote: The condition must be <=.
  testing_verification:
    - turn_id: 6
      quote: I will write boundary tests, ties, empty input, the validation errors and a randomized comparison against a brute force oracle.
    - turn_id: 6
      quote: so a boundary bug like mine shows up as a failing random case
  complexity_optimality:
    - turn_id: 4
      quote: each event is appended once and popped at most once, so O(n) time and O(w) space
    - turn_id: 4
      quote: in the worst case all events share a timestamp and the deque holds everything
  production_followups:
    - turn_id: 10
      quote: I would partition by member id so each member's stream is handled by one worker
    - turn_id: 10
      quote: add a watermark
  culture_signals:
    - turn_id: 8
      quote: I would not ship it as the implementation, though.
    - turn_id: 8
      quote: If you tell me the inputs are bounded by a few thousand, I agree the simple version is the better trade
hints: []
---

# Scorecard: 05-coding@practical

> Recommendation derived by the simulator's pedagogical rule; Netflix does not use a common scale.
> Recomendación derivada por la regla pedagógica del simulador; Netflix no usa una escala común.

## Summary
Recommendation pass, observed level L5. Synthetic scorecard for a debrief gold case (source transcript: coding-strong.md).

## Scores and evidence
- problem_solving: Y. Resolves boundary, ties, hashability and validation timing before coding, states the brute-force cost, reaches deque plus count dict without a hint.
- code_quality_correctness: Y. Small functions, empty/ties/boundary handled; first run had one boundary failure, fixed on the second run (within the L5 bar: first or second run).
- testing_verification: SY. Unprompted tests including boundaries and a randomized brute-force oracle; fixed the failure by reading its output. Reaches beyond the bar by explaining why the oracle is independent (SY plausible, Y acceptable).
- complexity_optimality: Y. States time and space unprompted, expected O(n), names a remaining inefficiency.
- production_followups: Y. Raises partitioning, lateness and state/checkpoint strategy and an offline-vs-online reference. Prompted by the interviewer's question, but the design steps are concrete (L5 asks to raise scale unprompted; Y at the lower edge).
- culture_signals: Y. Disagrees with a worse proposal with a technical reason, proposes a measurement, accepts the point when it holds.

## Hints
None.

## Uncovered signal points
None recorded.

## Strengths and gaps
See the scores above.

## Study plan
See study-map.yaml for the weakest competencies.
