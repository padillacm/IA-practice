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
    - {turn_id: 2, quote: "about 200 million members, a catalog of about 20,000 titles, a p99 budget of 300 ms for the page request"}
    - {turn_id: 2, quote: "Guardrails: row diversity and play-start rate per profile must not regress, and cost per thousand page requests stays flat."}
    - {turn_id: 2, quote: "Does that scope match yours, including several profiles per account and TV as the primary device?"}
  architecture_data_flow:
    - {turn_id: 4, quote: "Nearline: a stream processor over the play-event log, Kafka plus a Flink-class engine, updates short-horizon features such as the last 20 plays within minutes"}
    - {turn_id: 4, quote: "Offline and online features come from the same feature definitions, and training uses point-in-time joins to avoid leakage."}
    - {turn_id: 4, quote: "If the ranker times out at 150 ms we serve the last good cached page for that profile, and if that is missing a regional popularity page."}
  modeling_choices:
    - {turn_id: 6, quote: "A gradient boosted tree on engineered features is cheap and handles cold start through metadata, but it is weak on viewing order."}
    - {turn_id: 6, quote: "The loss is listwise with two heads, play-start and watch completion"}
    - {turn_id: 6, quote: "The training data come from logged impressions, which are biased by the old policy's exposure and by position"}
    - {turn_id: 6, quote: "To choose between models offline I use NDCG@10 on a time-based holdout plus an inverse-propensity replay estimate on the exploration slice."}
  scale_reliability_security:
    - {turn_id: 8, quote: "Availability target: 99.95% for page loads, with p99 under 300 ms."}
    - {turn_id: 8, quote: "if the online feature store is down, the ranker runs with batch-computed default features from the cache, with lower quality but a page"}
    - {turn_id: 8, quote: "Security: viewing history features are tagged restricted, access is per service and audited, logs hold hashed profile ids with a retention limit"}
    - {turn_id: 8, quote: "The cost driver is GPU inference for the sequence encoder"}
  online_validation_monitoring:
    - {turn_id: 10, quote: "it is a relative measure: it tells me which ranker members prefer inside the same list and says nothing about retention."}
    - {turn_id: 10, quote: "Offline and online metrics can disagree because the offline replay is biased by the logging policy and by position"}
    - {turn_id: 10, quote: "Rollback trigger: a guardrail breach or a fallback rate above 5% for ten minutes."}
    - {turn_id: 10, quote: "I keep the epsilon exploration traffic running so the data stay unbiased."}
  culture_signals:
    - {turn_id: 12, quote: "full real-time scoring multiplies GPU cost and widens the tail latency, so it risks the 300 ms target."}
    - {turn_id: 12, quote: "What would move me: a test where the real-time arm improves retention or play-starts by more than the cost justifies."}
    - {turn_id: 12, quote: "I do not know yet how much staleness members actually notice, so I would measure it by running an A/B on cache age"}
hints: []
---

# Scorecard: 01-ml-system-design@design

> Recommendation derived by the simulator's pedagogical rule; Netflix does not use a common scale.
> Recomendación derivada por la regla pedagógica del simulador; Netflix no usa una escala común.

## Summary
**Recommendation: pass. Observed level: L5.**

The candidate met the L5 Yes bar on all five core competencies, in their own words and with no hints. They did not reach the L6 bar on any of them.
- **Framing (T2):** they framed the problem before designing anything. They separated the business goal (retention) from the proxy they would optimize, gave numbers as stated assumptions, named guardrails and constraints, and checked the scope with the interviewer.
- **Architecture (T4):** they designed separate batch, nearline and online paths, kept offline and online features consistent, and traced one request through the system, including fallbacks.
- **Modeling (T6):** they compared two models against the latency and cold-start constraints, defined a listwise multi-head loss, named the exposure and position bias in the logged data, and gave the offline metric they would use to choose.
- **Reliability and security (T8):** they set availability and latency targets, described degraded modes for three different failures, covered access control for sensitive data, and named the main cost driver with a fix.
- **Validation (T10):** they gave the two-stage validation (interleaving, then A/B) and explained why offline and online metrics can disagree. They also covered exploration, layered monitoring and a rollback trigger.
- **Culture probe (T12):** they disagreed with the stakeholder's position, but politely and with reasons. They named the evidence that would change their mind, admitted what they did not know and said how they would find out.

The session closed normally (final interviewer meta `phase: closed`, no uncovered points).

## Scores and evidence

### problem_framing_requirements (core): Y
- T2: "I would separate the business goal, long-term member satisfaction measured through retention, from the proxy I can optimize day to day"
- T2: "about 200 million members, a catalog of about 20,000 titles, a p99 budget of 300 ms for the page request"
- T2: "Guardrails: row diversity and play-start rate per profile must not regress, and cost per thousand page requests stays flat."
- T2: "Does that scope match yours, including several profiles per account and TV as the primary device?"

Every element of the L5 bar is present:
- business goal separated from the proxy metric;
- explicit assumptions for latency, freshness and scale;
- guardrails;
- constraints (privacy, licensing, cost);
- a scope check with the interviewer.

It does not reach L6. The candidate did not say what they would leave out of the first version, did not frame the problem against adjacent surfaces or other teams' metrics, and gave no rule for continuing or stopping after launch.

### architecture_data_flow (core): Y
- T4: "Nearline: a stream processor over the play-event log, Kafka plus a Flink-class engine, updates short-horizon features such as the last 20 plays within minutes"
- T4: "Offline and online features come from the same feature definitions, and training uses point-in-time joins to avoid leakage."
- T4: "If the ranker times out at 150 ms we serve the last good cached page for that profile, and if that is missing a regional popularity page."

This meets the L5 bar:
- batch, nearline and online paths are kept separate;
- offline and online features come from the same definitions;
- each hop has a named technology class (ANN index, feature store, key-value cache, stream processor);
- one request is traced through the system, with the cache and fallback chain.

It does not reach L6. There were no versioned component contracts, no comparison of two end-to-end alternatives, and no answer to what would break first at 10 times the traffic.

### modeling_choices (core): Y
- T6: "A gradient boosted tree on engineered features is cheap and handles cold start through metadata, but it is weak on viewing order."
- T6: "The loss is listwise with two heads, play-start and watch completion"
- T6: "The training data come from logged impressions, which are biased by the old policy's exposure and by position"
- T6: "To choose between models offline I use NDCG@10 on a time-based holdout plus an inverse-propensity replay estimate on the exploration slice."

This meets the L5 bar:
- two options compared against the latency, data-volume and cold-start constraints;
- the loss defined;
- how the training data was generated, and its bias, described, with ways to reduce the bias (log position and propensity, epsilon exploration);
- the offline selection metric stated.

It does not reach L6. The candidate did not weigh a shared representation against per-task models, did not quantify gain against cost and complexity, and named no experiment that would falsify their main modeling assumption.

### scale_reliability_security (core): Y
- T8: "Availability target: 99.95% for page loads, with p99 under 300 ms."
- T8: "if the online feature store is down, the ranker runs with batch-computed default features from the cache, with lower quality but a page"
- T8: "Security: viewing history features are tagged restricted, access is per service and audited, logs hold hashed profile ids with a retention limit"
- T8: "The cost driver is GPU inference for the sequence encoder"

This meets the L5 bar:
- availability and latency targets set;
- degraded modes for three failures (ranker, online feature store, cold cache);
- access control for viewing history, and a page-assembler filter so a ranker bug cannot leak unreleased titles;
- a cost driver with a mitigation (compute the embedding nearline, only for profiles active in the last day).

The security answer touches parts of the L6 bar (data classification, auditing, retention). It still falls short of L6: there was no design for regional failure, no owner per failure class, and no numeric comparison of two deployment options.

### online_validation_monitoring (core): Y
- T10: "it is a relative measure: it tells me which ranker members prefer inside the same list and says nothing about retention."
- T10: "Offline and online metrics can disagree because the offline replay is biased by the logging policy and by position"
- T10: "Rollback trigger: a guardrail breach or a fallback rate above 5% for ten minutes."
- T10: "I keep the epsilon exploration traffic running so the data stay unbiased."

This meets the L5 bar:
- interleaving as the first stage, then an A/B test;
- the limit of interleaving stated (relative, says nothing about retention);
- reasons why offline and online metrics disagree;
- an explore/exploit mechanism;
- model-quality, data and system monitors, with an alert action (rollback).

The rollback threshold goes partly toward L6. Still, there was no validation program for many concurrent variants and no plan for auditing offline/online metric alignment over time.

### culture_signals (non-core): Y
- T12: "full real-time scoring multiplies GPU cost and widens the tail latency, so it risks the 300 ms target."
- T12: "What would move me: a test where the real-time arm improves retention or play-starts by more than the cost justifies."
- T12: "I do not know yet how much staleness members actually notice, so I would measure it by running an A/B on cache age"

This meets the L5 bar:
- **Judgment:** they defended the trade-off with stated reasons on cost and latency.
- **Candor:** they disagreed directly but politely with the product partner, while granting the partner's valid point. They changed the design accordingly by adding a request-time re-rank after recent plays.
- **Open to evidence:** they named the evidence that would change their mind.
- **Courage:** they said "I do not know" and proposed how to find out.

It does not reach L6. They did not say what risk they were accepting or who they would inform, did not propose farming for dissent, and gave no trigger for reopening the decision.

## Hints
None.

## Uncovered signal points
None. The session closed normally (`phase: closed`), with no uncovered signal points recorded.

## Strengths and gaps
**Strengths**
- The answers were structured and quantified throughout: explicit numbers for scale, latency, availability, timeouts and rollback thresholds.
- They named the main bias issue (exposure and position bias in logged impressions) and connected it to both training and validation.
- Fallback design was layered and concrete.
- Unreleased titles are filtered in the page assembler, so a ranker bug cannot leak them.
- They handled stakeholder pushback by conceding the valid point, keeping the core design, and proposing an experiment to settle the question.

**Gaps (toward L6)**
- No first-version cut list, no framing against adjacent surfaces or other teams, and no post-launch continue/stop rule.
- No reusable component contracts, no comparison of two end-to-end alternatives, and no analysis of what breaks at 10 times the traffic.
- Nothing on shared versus per-task modeling, no quantified gain-versus-complexity, and no experiment that would falsify the main modeling assumption.
- No regional-failure design, no owner per failure class, and no numeric comparison of deployment options.
- No program for many concurrent tests (pruning, interference, long-term holdouts).
- No dissent-farming and no trigger for reopening the decision.

## Study plan
1. **Toward L6 on architecture and scale.** Practice comparing two end-to-end architectures on cost, latency and operational burden, and identifying the first component that fails at 10 times the traffic. Links: `recsys-course/16_production_serving/`, `recsys-course/17_mlops_monitoring/`, `recsys-course/08_deep_retrieval_ann/` (study-map: `ml-system-design.architecture_data_flow`, `ml-system-design.scale_reliability_security`).
2. **Toward L6 on validation.** Design a validation program for many concurrent variants (pruning rule, traffic allocation, interference, long-term holdouts) and an audit of offline/online metric alignment. Links: `recsys-course/15_online_experimentation/`, `recsys-course/14_bandits_rl_ope/` (study-map: `ml-system-design.online_validation_monitoring`).
3. **Toward L6 on framing and modeling.** State what you would not build in the first version, give a continue/stop rule after launch, and name the experiment that would falsify your main modeling assumption. Links: `recsys-course/19_elite_playbook/`, `recsys-course/18_capstone/`, `recsys-course/07_learning_to_rank_multitask/` (study-map: `ml-system-design.problem_framing_requirements`, `ml-system-design.modeling_choices`). For the culture side, practice stage `culture` and the Netflix culture memo (jobs.netflix.com/culture), with a focus on farming for dissent and naming a trigger for reopening a decision.
