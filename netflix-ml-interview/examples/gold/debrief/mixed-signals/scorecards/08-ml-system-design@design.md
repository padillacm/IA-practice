---
instance_id: 08-ml-system-design@design
stage: ml-system-design
variant: design
level: L5
rubric_version: 1
recommendation: pass
level_observed: L5
scores:
  problem_framing_requirements: Y
  architecture_data_flow: Y
  modeling_choices: SY
  scale_reliability_security: Y
  online_validation_monitoring: Y
  culture_signals: N
evidence:
  problem_framing_requirements:
    - turn_id: 2
      quote: I would separate the business goal, long-term member satisfaction measured through retention, from the proxy I can optimize day to day
    - turn_id: 2
      quote: a p99 budget of 300 ms for the page request
  architecture_data_flow:
    - turn_id: 4
      quote: Offline and online features come from the same feature definitions, and training uses point-in-time joins to avoid leakage
    - turn_id: 4
      quote: If the ranker times out at 150 ms we serve the last good cached page for that profile
  modeling_choices:
    - turn_id: 6
      quote: I compare two options.
    - turn_id: 6
      quote: reserve a small epsilon of random exploration traffic to get unbiased data
  scale_reliability_security:
    - turn_id: 8
      quote: "Availability target: 99.95% for page loads, with p99 under 300 ms."
    - turn_id: 8
      quote: unreleased titles are only visible to flagged internal profiles
  online_validation_monitoring:
    - turn_id: 10
      quote: "it is a relative measure: it tells me which ranker members prefer inside the same list and says nothing about retention"
    - turn_id: 10
      quote: "Rollback trigger: a guardrail breach or a fallback rate above 5% for ten minutes."
  culture_signals:
    - turn_id: 12
      quote: the product partner is wrong here and I have seen this request many times
    - turn_id: 12
      quote: I do not need to measure anything to know the batch approach wins.
hints: []
---

# Scorecard: 08-ml-system-design@design

> Recommendation derived by the simulator's pedagogical rule; Netflix does not use a common scale.
> Recomendación derivada por la regla pedagógica del simulador; Netflix no usa una escala común.

## Summary
Recommendation pass, observed level L5. Synthetic scorecard for a debrief gold case (source transcript: mlsd-halo.md).

## Scores and evidence
- problem_framing_requirements: Y. Separates goal from proxy, states latency/freshness/scale as assumptions, names guardrails and constraints, confirms scope (L5 bar). No prompting. (identical technical turns to mlsd-strong)
- architecture_data_flow: Y. Batch/nearline/online split, feature consistency, technology class per hop, one traced request with cache and fallback. Meets L5. (identical technical turns to mlsd-strong)
- modeling_choices: SY. Two options against latency/data/cold start, loss defined, training-data bias (position, exposure) and offline metric named. Clean L5; selecting computation off the request path is a strong move (SY possible). (identical technical turns to mlsd-strong)
- scale_reliability_security: Y. Availability target, three degraded modes, access control for viewing history and unreleased content, cost driver with mitigation. (identical technical turns to mlsd-strong)
- online_validation_monitoring: Y. Interleaving then A/B, states interleaving is relative, explains offline/online disagreement, exploration mechanism, model and data monitoring lists. Meets L5, with a debugging order for the flat A/B. (identical technical turns to mlsd-strong)
- culture_signals: N. Dismisses the stakeholder, refuses to name evidence that would change their mind, escalates instead of testing. Strong technical turns T2-T10 must not lift this score.

## Hints
None.

## Uncovered signal points
None recorded.

## Strengths and gaps
See the scores above.

## Study plan
See study-map.yaml for the weakest competencies.
