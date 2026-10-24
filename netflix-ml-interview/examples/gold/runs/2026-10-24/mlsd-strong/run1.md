---
instance_id: 01-ml-system-design@design
stage: ml-system-design
variant: design
level: L5
rubric_version: 1
recommendation: pass
level_observed: L5
scores:
  problem_framing_requirements: Y
  architecture_data_flow: Y
  modeling_choices: Y
  scale_reliability_security: Y
  online_validation_monitoring: Y
  culture_signals: Y
evidence:
  problem_framing_requirements:
    - {turn_id: 2, quote: "I would separate the business goal, long-term member satisfaction measured through retention, from the proxy I can optimize day to day"}
    - {turn_id: 2, quote: "a p99 budget of 300 ms for the page request"}
    - {turn_id: 2, quote: "Guardrails: row diversity and play-start rate per profile must not regress, and cost per thousand page requests stays flat."}
    - {turn_id: 2, quote: "Does that scope match yours, including several profiles per account and TV as the primary device?"}
  architecture_data_flow:
    - {turn_id: 4, quote: "Offline and online features come from the same feature definitions, and training uses point-in-time joins to avoid leakage."}
    - {turn_id: 4, quote: "the page service reads precomputed candidate rows from a key-value cache keyed by profile id"}
    - {turn_id: 4, quote: "If the ranker times out at 150 ms we serve the last good cached page for that profile, and if that is missing a regional popularity page."}
  modeling_choices:
    - {turn_id: 6, quote: "A gradient boosted tree on engineered features is cheap and handles cold start through metadata, but it is weak on viewing order."}
    - {turn_id: 6, quote: "The loss is listwise with two heads, play-start and watch completion, combined with weights I tune against retention in tests."}
    - {turn_id: 6, quote: "The training data come from logged impressions, which are biased by the old policy's exposure and by position"}
    - {turn_id: 6, quote: "To choose between models offline I use NDCG@10 on a time-based holdout plus an inverse-propensity replay estimate on the exploration slice."}
  scale_reliability_security:
    - {turn_id: 8, quote: "Availability target: 99.95% for page loads, with p99 under 300 ms."}
    - {turn_id: 8, quote: "if the online feature store is down, the ranker runs with batch-computed default features from the cache, with lower quality but a page"}
    - {turn_id: 8, quote: "viewing history features are tagged restricted, access is per service and audited"}
    - {turn_id: 8, quote: "The cost driver is GPU inference for the sequence encoder"}
  online_validation_monitoring:
    - {turn_id: 10, quote: "First interleaving, which needs far less traffic and detects ranking preference quickly, but it is a relative measure"}
    - {turn_id: 10, quote: "it tells me which ranker members prefer inside the same list and says nothing about retention"}
    - {turn_id: 10, quote: "Offline and online metrics can disagree because the offline replay is biased by the logging policy and by position"}
    - {turn_id: 10, quote: "Because the system chooses what to show, I keep the epsilon exploration traffic running so the data stay unbiased."}
    - {turn_id: 10, quote: "Rollback trigger: a guardrail breach or a fallback rate above 5% for ten minutes."}
  culture_signals:
    - {turn_id: 12, quote: "I would keep the hybrid but change one thing."}
    - {turn_id: 12, quote: "full real-time scoring multiplies GPU cost and widens the tail latency, so it risks the 300 ms target"}
    - {turn_id: 12, quote: "What would move me: a test where the real-time arm improves retention or play-starts by more than the cost justifies."}
    - {turn_id: 12, quote: "I do not know yet how much staleness members actually notice, so I would measure it by running an A/B on cache age before we pay for the infrastructure."}
hints: []
---

# Scorecard: 01-ml-system-design@design

> Recommendation derived by the simulator's pedagogical rule; Netflix does not use a common scale.
> Recomendación derivada por la regla pedagógica del simulador; Netflix no usa una escala común.

## Summary
**Recommendation:** pass. **Observed level:** L5.

The session ended normally: the final interviewer meta shows `phase: closed` and lists no uncovered points. The candidate met the L5 Yes bar on all five core competencies and on culture_signals, and needed no hints.

- **Framing:** before designing, they separated the business goal (retention) from a proxy metric, stated scale, latency and freshness numbers as assumptions, named guardrails and constraints, and confirmed scope.
- **Architecture:** they described batch, nearline and online paths with consistent feature definitions, and traced one request through the system including its fallbacks.
- **Modeling:** they compared two ranker options against the latency budget, defined a listwise multi-task loss, explained exposure and position bias, and named the offline metrics they would use to choose.
- **Reliability and security:** they gave availability and latency targets, described degraded modes, set access control for sensitive data, and named a cost driver with a mitigation.
- **Validation:** they described the two-stage interleaving then A/B approach, including what interleaving cannot measure, why offline and online metrics can disagree, ongoing exploration traffic, and layered monitors with a rollback trigger.

Nothing reached the L6 bar consistently. Missing were cross-team or product-level framing, reusable component contracts, a 10x breaking-point analysis, regional failure handling, and a program for running many test variants at once. So no competency is scored above Y.

## Scores and evidence

### problem_framing_requirements (core): Y
- T2: "I would separate the business goal, long-term member satisfaction measured through retention, from the proxy I can optimize day to day"
- T2: "a p99 budget of 300 ms for the page request"
- T2: "Guardrails: row diversity and play-start rate per profile must not regress, and cost per thousand page requests stays flat."
- T2: "Does that scope match yours, including several profiles per account and TV as the primary device?"

All L5 elements are present, in the candidate's own words and before any component was drawn:
- business goal vs proxy metric;
- explicit scale (200M members, 20k titles), latency (p99 300 ms) and freshness assumptions;
- guardrails;
- constraints (privacy, licensing, cost);
- scope confirmation.

This is not SY: the candidate did not say what would be left out of the first version, did not give a continue/stop rule for after launch, and did not frame the problem against adjacent surfaces or other teams' metrics.

### architecture_data_flow (core): Y
- T4: "Offline and online features come from the same feature definitions, and training uses point-in-time joins to avoid leakage."
- T4: "the page service reads precomputed candidate rows from a key-value cache keyed by profile id"
- T4: "If the ranker times out at 150 ms we serve the last good cached page for that profile, and if that is missing a regional popularity page."

The batch, nearline and online paths are clearly separated. Offline/online consistency is specified. Technology classes are named for each hop: ANN index, feature store, Kafka plus a Flink-class stream processor, key-value cache, low-latency feature store. One request is traced end to end with a two-level fallback.

This is not SY: there are no versioned interfaces or ownership boundaries, no comparison of two end-to-end alternatives, and no 10x bottleneck analysis.

### modeling_choices (core): Y
- T6: "A gradient boosted tree on engineered features is cheap and handles cold start through metadata, but it is weak on viewing order."
- T6: "The loss is listwise with two heads, play-start and watch completion, combined with weights I tune against retention in tests."
- T6: "The training data come from logged impressions, which are biased by the old policy's exposure and by position"
- T6: "To choose between models offline I use NDCG@10 on a time-based holdout plus an inverse-propensity replay estimate on the exploration slice."

The two options were compared against latency, data volume and cold start. The candidate resolved the latency tension by computing the sequence embedding nearline. The loss is defined. They explained how the training data is generated and biased, with mitigations (position as a feature, propensity logging, epsilon exploration). The offline selection metric is stated.

This is not SY: there is no shared-vs-per-task strategy across surfaces, no quantified gain against cost, and no falsification experiment for the main modeling assumption.

### scale_reliability_security (core): Y
- T8: "Availability target: 99.95% for page loads, with p99 under 300 ms."
- T8: "if the online feature store is down, the ranker runs with batch-computed default features from the cache, with lower quality but a page"
- T8: "viewing history features are tagged restricted, access is per service and audited"
- T8: "The cost driver is GPU inference for the sequence encoder"

The candidate gave:
- availability and latency targets;
- three degraded modes (ranker, feature store, cold cache), plus load testing and an alarm on the fallback rate;
- access control for viewing history and unreleased titles, filtered in the assembler;
- a cost driver (GPU inference) with a mitigation (nearline embeddings only for recently active profiles).

This is not SY: security was raised after the interviewer named it, there is no regional failure or incident ownership design, and no deployment trade-off is backed by numbers.

### online_validation_monitoring (core): Y
- T10: "First interleaving, which needs far less traffic and detects ranking preference quickly, but it is a relative measure"
- T10: "it tells me which ranker members prefer inside the same list and says nothing about retention"
- T10: "Offline and online metrics can disagree because the offline replay is biased by the logging policy and by position"
- T10: "Because the system chooses what to show, I keep the epsilon exploration traffic running so the data stay unbiased."
- T10: "Rollback trigger: a guardrail breach or a fallback rate above 5% for ten minutes."

Every L5 element is present:
- the two-stage interleaving then A/B design;
- the stated limit of interleaving (relative measure, says nothing about retention);
- the reasons offline and online metrics disagree;
- an explore/exploit mechanism (also Thompson sampling for new titles in T6);
- model-quality, data and system monitors with an alert and rollback action.

This is not SY: the rollback thresholds are a partial L6 signal, but there is no program for many concurrent variants (pruning, traffic allocation, interference, long-term holdouts) and no ongoing audit of offline/online metric alignment.

### culture_signals (non-core): Y
- T12: "I would keep the hybrid but change one thing."
- T12: "full real-time scoring multiplies GPU cost and widens the tail latency, so it risks the 300 ms target"
- T12: "What would move me: a test where the real-time arm improves retention or play-starts by more than the cost justifies."
- T12: "I do not know yet how much staleness members actually notice, so I would measure it by running an A/B on cache age before we pay for the infrastructure."

Three memo values show in this answer:
- **Judgment and courage:** the candidate defended the hybrid design with stated cost and latency reasons and disagreed directly but politely with the product partner. They also conceded the one case where the partner was right and changed the design for it.
- **Judgment:** they named the evidence that would change their mind.
- **Candor:** they said "I do not know" and proposed a concrete way to find out.

This is not SY: they did not name the risk they accept or who they would inform, did not propose a way to gather dissent before committing, and did not set a trigger to reopen the decision.

## Hints
None.

## Uncovered signal points
None. The session closed normally with no uncovered signal points recorded.

## Strengths and gaps
**Strengths**
- Disciplined framing: goal vs proxy, numeric assumptions, guardrails, and confirming scope before designing.
- Coherent three-path architecture with explicit feature consistency and fallbacks.
- Fluent handling of feedback-loop bias: position and propensity logging, epsilon exploration, IPS replay.
- Clear two-stage validation with correct limits of interleaving, and monitors tied to rollback triggers.
- Balanced handling of stakeholder pushback, with a stated falsification test.

**Gaps (toward L6)**
- No organization- or product-wide framing, and no "won't build in v1" or post-launch stop rule.
- No reusable contracts, no comparison of end-to-end alternatives, no 10x breaking-point analysis.
- No regional failure or incident ownership, and security was raised only when prompted.
- No validation program for many concurrent variants or long-term holdouts.
- No explicit statement of accepted risk, who to inform, or how to gather dissent.

## Study plan
1. **Architecture at L6:** practice versioned component contracts, comparing two end-to-end designs on cost, latency and operational burden, and finding the first component to break at 10x traffic. See `recsys-course/16_production_serving/` and `recsys-course/08_deep_retrieval_ann/`, then the `ml-system-design` practice stage.
2. **Validation program at L6:** design for many concurrent variants (pruning rule, traffic allocation, interference between tests, long-term holdouts) and an ongoing audit of offline/online metric alignment. See `recsys-course/15_online_experimentation/`, `recsys-course/14_bandits_rl_ope/` and `recsys-course/17_mlops_monitoring/`.
3. **Framing and reliability at L6:** state what you would leave out of v1 and a continue/stop rule after launch, and raise regional failover, owners per failure class, and a security/privacy model without being asked. See `recsys-course/19_elite_playbook/` and `recsys-course/18_capstone/` (framing), and `recsys-course/16_production_serving/` and `recsys-course/17_mlops_monitoring/` (reliability).

Culture: to move toward L6, practice naming the risk you accept, who you would inform, and how you would gather dissent before committing. See the `culture` practice stage and the Netflix culture memo at jobs.netflix.com/culture.
