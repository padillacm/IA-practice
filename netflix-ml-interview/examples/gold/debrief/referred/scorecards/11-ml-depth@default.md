---
instance_id: 11-ml-depth@default
stage: ml-depth
variant: default
level: L5
rubric_version: 1
recommendation: fail
level_observed: none
scores:
  domain_depth: N
  first_principles_reasoning: N
  connection_to_practice: Y
  architecture_depth: no_evidence
  culture_signals: no_evidence
evidence:
  domain_depth:
    - turn_id: 2
      quote: I think it is unbiased. There is also a doubly robust estimator.
  first_principles_reasoning:
    - turn_id: 4
      quote: I do not remember how to derive it.
  connection_to_practice:
    - turn_id: 6
      quote: we run an A/B test with a ramp, watching play-starts and a latency guardrail, and we roll back if the guardrail is breached for an hour
hints: []
---

# Scorecard: 11-ml-depth@default

> Recommendation derived by the simulator's pedagogical rule; Netflix does not use a common scale.
> Recomendación derivada por la regla pedagógica del simulador; Netflix no usa una escala común.

## Summary
Recommendation fail, observed level none. Synthetic scorecard for a debrief gold case (source transcript: mldepth-weak.md).

## Scores and evidence
- domain_depth: N. Names estimators but no deciding condition between methods and no chain of mechanism answers.
- first_principles_reasoning: N. No derivation of variance, no limiting case.
- connection_to_practice: Y. Offline-to-online path, guardrail and rollback trigger.
- architecture_depth: no_evidence. Not asked.
- culture_signals: no_evidence. No disagreement or dropped approach discussed.

## Hints
None.

## Uncovered signal points
None recorded.

## Strengths and gaps
See the scores above.

## Study plan
See study-map.yaml for the weakest competencies.
