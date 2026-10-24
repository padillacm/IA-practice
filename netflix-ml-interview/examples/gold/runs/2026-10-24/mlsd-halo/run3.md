---
instance_id: 01-ml-system-design@design
stage: ml-system-design
variant: design
level: L5
rubric_version: 1
recommendation: fail
level_observed: L5
scores:
  problem_framing_requirements: Y
  architecture_data_flow: Y
  modeling_choices: Y
  scale_reliability_security: Y
  online_validation_monitoring: Y
  culture_signals: SN
evidence:
  problem_framing_requirements:
    - {turn_id: 2, quote: "I would separate the business goal, long-term member satisfaction measured through retention, from the proxy I can optimize day to day"}
    - {turn_id: 2, quote: "a p99 budget of 300 ms for the page request"}
    - {turn_id: 2, quote: "Guardrails: row diversity and play-start rate per profile must not regress, and cost per thousand page requests stays flat."}
    - {turn_id: 2, quote: "Does that scope match yours, including several profiles per account and TV as the primary device?"}
  architecture_data_flow:
    - {turn_id: 4, quote: "Nearline: a stream processor over the play-event log, Kafka plus a Flink-class engine, updates short-horizon features such as the last 20 plays within minutes"}
    - {turn_id: 4, quote: "Offline and online features come from the same feature definitions, and training uses point-in-time joins to avoid leakage."}
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
    - {turn_id: 8, quote: "I mitigate it by computing the embedding nearline only for profiles active in the last day and caching it, instead of running per request."}
  online_validation_monitoring:
    - {turn_id: 10, quote: "First interleaving, which needs far less traffic and detects ranking preference quickly, but it is a relative measure"}
    - {turn_id: 10, quote: "it tells me which ranker members prefer inside the same list and says nothing about retention."}
    - {turn_id: 10, quote: "Offline and online metrics can disagree because the offline replay is biased by the logging policy and by position"}
    - {turn_id: 10, quote: "Rollback trigger: a guardrail breach or a fallback rate above 5% for ten minutes."}
    - {turn_id: 10, quote: "I keep the epsilon exploration traffic running so the data stay unbiased."}
  culture_signals:
    - {turn_id: 12, quote: "Honestly the product partner is wrong here and I have seen this request many times"}
    - {turn_id: 12, quote: "I would just tell them it is settled rather than spend a week on a test."}
    - {turn_id: 12, quote: "I do not need to measure anything to know the batch approach wins."}
hints: []
---

# Scorecard: 01-ml-system-design@design

> Recommendation derived by the simulator's pedagogical rule; Netflix does not use a common scale.
> Recomendación derivada por la regla pedagógica del simulador; Netflix no usa una escala común.

## Summary
**Recommendation: fail. Observed level: L5.**

The technical design was strong and met the L5 Yes bar on all five core competencies. The candidate asked about scope before building. They separated retention from a proxy metric and stated latency, freshness and scale assumptions. They laid out batch, nearline and online paths with feature consistency and fallbacks. They compared two rankers, named the loss and the bias in the training data, and set a solid reliability and security posture. They also gave a full interleaving-then-A/B plan with monitors and rollback triggers.

The culture probe (T11) asked the candidate to defend or change the design and to say what evidence would move them. In T12 they refused to consider any evidence, dismissed the stakeholder and proposed escalating instead of testing. That goes against the culture_signals bar (judgment, candor), so the score is Strong No. Under the fixed rule, a Strong No on any non-core competency means a fail, even though every core competency is Y. The session ended normally (final meta `phase: closed`, no uncovered points recorded).

## Scores and evidence

### problem_framing_requirements: Y
- T2: "I would separate the business goal, long-term member satisfaction measured through retention, from the proxy I can optimize day to day"
- T2: "a p99 budget of 300 ms for the page request"
- T2: "Guardrails: row diversity and play-start rate per profile must not regress, and cost per thousand page requests stays flat."
- T2: "Does that scope match yours, including several profiles per account and TV as the primary device?"

Every L5 element is there: business goal versus proxy, explicit latency, freshness and scale assumptions, guardrails, constraints (privacy, licensing, cost) and a scope check. This is not Strong Yes because the L6 elements are missing: the wider product and organization, what the first version would not include, and a continue-or-stop decision rule.

### architecture_data_flow: Y
- T4: "Nearline: a stream processor over the play-event log, Kafka plus a Flink-class engine, updates short-horizon features such as the last 20 plays within minutes"
- T4: "Offline and online features come from the same feature definitions, and training uses point-in-time joins to avoid leakage."
- T4: "If the ranker times out at 150 ms we serve the last good cached page for that profile, and if that is missing a regional popularity page."

The answer covers all the L5 elements:
- separate batch, nearline and online paths;
- offline and online feature consistency;
- a technology class for each hop (KV cache keyed by profile, low-latency feature store, ANN index, stream processor);
- one request traced end to end, including the cache and fallback paths.

The L6 elements were not shown: reusable component contracts, two end-to-end alternatives compared, and the first component to break at 10x traffic.

### modeling_choices: Y
- T6: "A gradient boosted tree on engineered features is cheap and handles cold start through metadata, but it is weak on viewing order."
- T6: "The loss is listwise with two heads, play-start and watch completion, combined with weights I tune against retention in tests."
- T6: "The training data come from logged impressions, which are biased by the old policy's exposure and by position"
- T6: "To choose between models offline I use NDCG@10 on a time-based holdout plus an inverse-propensity replay estimate on the exploration slice."

The candidate compared two options against latency, data volume and cold start. They defined the loss, explained how the training data was generated and how it is biased (exposure and position), and named the offline selection metric. The L6 elements were missing: a strategy across surfaces or tasks, gain quantified against cost, and a falsifying experiment.

### scale_reliability_security: Y
- T8: "Availability target: 99.95% for page loads, with p99 under 300 ms."
- T8: "if the online feature store is down, the ranker runs with batch-computed default features from the cache, with lower quality but a page"
- T8: "viewing history features are tagged restricted, access is per service and audited"
- T8: "I mitigate it by computing the embedding nearline only for profiles active in the last day and caching it, instead of running per request."

The answer has an availability target, three degraded modes, access control for viewing history and unreleased titles, and a named cost driver with a mitigation. Security came up only after the interviewer asked about it (T7). There was no regional-failure design and no comparison of deployment options, so this stays at Y.

### online_validation_monitoring: Y
- T10: "First interleaving, which needs far less traffic and detects ranking preference quickly, but it is a relative measure"
- T10: "it tells me which ranker members prefer inside the same list and says nothing about retention."
- T10: "Offline and online metrics can disagree because the offline replay is biased by the logging policy and by position"
- T10: "Rollback trigger: a guardrail breach or a fallback rate above 5% for ten minutes."
- T10: "I keep the epsilon exploration traffic running so the data stay unbiased."

Every L5 element is present:
- interleaving first, then an A/B test;
- the limits of interleaving (a relative measure that says nothing about retention);
- why offline and online metrics can disagree;
- an explore/exploit mechanism;
- model-quality, data and system monitors with alert actions.

There is one thresholded rollback trigger, but there is no program for many concurrent variants and no plan for auditing offline/online metric alignment over time, so this is not L6.

### culture_signals: SN
- T12: "Honestly the product partner is wrong here and I have seen this request many times"
- T12: "I would just tell them it is settled rather than spend a week on a test."
- T12: "I do not need to measure anything to know the batch approach wins."

This goes against the L5 bar. The candidate was asked directly what evidence would move them and named none. They gave no evidence or assumption to support the trade-off, and they disagreed dismissively ("people who do not do ML tend to ask for real-time everywhere without understanding the cost") instead of directly and politely. They also proposed escalating to a manager rather than gathering evidence. All three statements go against the memo values of **judgment** (deciding from evidence, staying open to being wrong) and **candor** (direct but respectful disagreement). The strong technical work elsewhere in the session does not offset this.

**What a Yes would have looked like (L5):** "I would keep nearline refresh for most rows. My design already reflects a new play within minutes, and real-time scoring everywhere would roughly double GPU cost and put the 300 ms p99 at risk. My assumption is that staleness within a session matters less than latency on TV. I do not know that for sure. To find out, I would run a small A/B with real-time scoring on the continue-watching and because-you-watched rows only, and measure play-start and session retention. If it showed a meaningful lift in those metrics at an acceptable cost, I would move those rows to real-time. I would tell the partner directly that I disagree with 'everywhere', and offer that test as the way to settle it."

## Hints
None.

## Uncovered signal points
None. The session closed normally (`phase: closed`) and no uncovered signal points were recorded.

## Strengths and gaps
**Strengths**
- The framing was complete and disciplined from the first turn: proxy versus business goal, numeric assumptions, guardrails and a scope check.
- The architecture is coherent and production-grade, with layered fallbacks and feature consistency between training and serving.
- The candidate is aware of bias in the training data (position, propensity, exploration slice) and connects it to offline evaluation and online validation.
- The reliability plan is concrete, with degraded modes, a fallback-rate alarm and rollback thresholds.

**Gaps**
- **Handling stakeholder pushback (culture_signals, the deciding gap).** The candidate refused to name evidence that would change their mind, dismissed the partner and escalated instead of testing.
- **Toward L6:** no comparison of end-to-end alternatives or 10x breaking point, no security model offered without being asked, no regional-failure design, and no program for concurrent experiments.

## Study plan
1. **Defending trade-offs with evidence and openness (culture_signals).** Practice again in [practice stage: culture](netflix-ml-interview/stages/culture/) and reread the Netflix culture memo (jobs.netflix.com/culture), focusing on judgment and candor. Drill this answer shape: the reason for the choice, the assumption behind it, what would change your mind, a cheap test to find out, and a polite direct disagreement.
2. **Toward L6 architecture (architecture_data_flow).** Work through `recsys-course/16_production_serving/` and `recsys-course/08_deep_retrieval_ann/`. In your next design, compare two end-to-end options on cost, latency and operational burden, and name the first component that breaks at 10x traffic.
3. **Toward L6 validation (online_validation_monitoring).** Work through `recsys-course/15_online_experimentation/`, `recsys-course/14_bandits_rl_ope/` and `recsys-course/17_mlops_monitoring/`. Cover concurrent-variant pruning, interference between tests, long-term holdouts and auditing offline/online metric alignment over time.
