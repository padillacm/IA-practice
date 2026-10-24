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
  testing_verification: N
  complexity_optimality: Y
  production_followups: N
  culture_signals: no_evidence
evidence:
  problem_solving:
    - turn_id: 2
      quote: Is the window exclusive on the left?
    - turn_id: 4
      quote: It could be improved with a deque.
  code_quality_correctness:
    - turn_id: 6
      quote: I forgot the sorted check.
    - turn_id: 6
      quote: "while live[0][0] <= ts - window:"
  testing_verification:
    - turn_id: 8
      quote: These pass. I think the solution is fine.
    - turn_id: 10
      quote: I did not write a brute force check.
  complexity_optimality:
    - turn_id: 6
      quote: Time is O(n) amortized, space O(live events).
  production_followups:
    - turn_id: 12
      quote: Hmm, I have not thought much about it. We could use Kafka maybe.
hints:
  - id: h1
    level: nudge
    competency: testing_verification
---

# Scorecard: 05-coding@practical

> Recommendation derived by the simulator's pedagogical rule; Netflix does not use a common scale.
> Recomendación derivada por la regla pedagógica del simulador; Netflix no usa una escala común.

## Summary
Recommendation pass, observed level L5. Synthetic scorecard for a debrief gold case (source transcript: coding-borderline.md).

## Scores and evidence
- problem_solving: Y. Asks the boundary question and states the baseline cost but skips ties and validation; reaches the deque only after the suite feedback. Lower edge of Y.
- code_quality_correctness: Y. Final solution passes the full suite on the second run, handles empty/ties/boundary; first version lacked validation and was not optimal. Y (N tolerated).
- testing_verification: N. Two example tests only, no boundary, ties or oracle even after a nudge (h1). Capped at Y by the nudge, scored N on content.
- complexity_optimality: Y. Reaches the expected O(n) with a stated complexity (though only after feedback, and no remaining inefficiency named). Y at the lower edge.
- production_followups: N. No concrete design step: N (non-core).
- culture_signals: no_evidence. No disagreement or challenge occurred in the round; no evidence of defending or changing a position: no_evidence.

## Hints
- h1 (nudge) on testing_verification

## Uncovered signal points
None recorded.

## Strengths and gaps
See the scores above.

## Study plan
See study-map.yaml for the weakest competencies.
