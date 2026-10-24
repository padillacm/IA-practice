---
instance_id: 08-ml-system-design@design
stage: ml-system-design
variant: design
level: L5
rubric_version: 1
recommendation: fail
level_observed: none
scores:
  problem_framing_requirements: N
  architecture_data_flow: N
  modeling_choices: SN
  scale_reliability_security: N
  online_validation_monitoring: SN
  culture_signals: N
evidence:
  problem_framing_requirements:
    - turn_id: 4
      quote: Accuracy of the click prediction, I think. Scale is big, so we use Spark and a big GPU cluster. Latency should be fast.
  architecture_data_flow:
    - turn_id: 6
      quote: the model gets the user's history from the database, and it returns the top 10 movies
  modeling_choices:
    - turn_id: 6
      quote: we split the logs randomly into train and test sets
    - turn_id: 8
      quote: all the other movies in the catalog are negatives
  scale_reliability_security:
    - turn_id: 10
      quote: We have servers in the cloud so they should not go down.
  online_validation_monitoring:
    - turn_id: 10
      quote: if it is higher than the old one we deploy it
  culture_signals:
    - turn_id: 10
      quote: Honestly, the interviewer's question about the page layout is not something I have seen before.
hints:
  - id: h1
    level: substantive
    competency: modeling_choices
---

# Scorecard: 08-ml-system-design@design

> Recommendation derived by the simulator's pedagogical rule; Netflix does not use a common scale.
> Recomendación derivada por la regla pedagógica del simulador; Netflix no usa una escala común.

## Summary
Recommendation fail, observed level none. Synthetic scorecard for a debrief gold case (source transcript: mlsd-weak.md).

## Scores and evidence
- problem_framing_requirements: N. Optimizes click accuracy (proxy as goal), no numbers, no guardrails, no constraints. Below the bar; N (SN also tolerable).
- architecture_data_flow: N. Single synchronous path, no batch/real-time split, no feature consistency, no cache or fallback.
- modeling_choices: SN. Random split of logs (leakage), unexposed titles as negatives, no model comparison, no bias treatment even after a substantive hint: serious errors, SN.
- scale_reliability_security: N. No target, no degraded mode, no security or cost: N.
- online_validation_monitoring: SN. Deploys on offline accuracy alone, no online test, no monitoring: contradicts the bar, SN (N tolerated by +-1).
- culture_signals: N. Admits not knowing but proposes no way to find out and defends nothing; non-core, N.

## Hints
- h1 (substantive) on modeling_choices

## Uncovered signal points
None recorded.

## Strengths and gaps
See the scores above.

## Study plan
See study-map.yaml for the weakest competencies.
