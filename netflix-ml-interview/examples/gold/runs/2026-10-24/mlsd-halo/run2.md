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
    - {turn_id: 2, quote: "about 200 million members, a catalog of about 20,000 titles, a p99 budget of 300 ms for the page request"}
    - {turn_id: 2, quote: "Guardrails: row diversity and play-start rate per profile must not regress, and cost per thousand page requests stays flat."}
    - {turn_id: 2, quote: "Does that scope match yours, including several profiles per account and TV as the primary device?"}
  architecture_data_flow:
    - {turn_id: 4, quote: "Nearline: a stream processor over the play-event log, Kafka plus a Flink-class engine, updates short-horizon features such as the last 20 plays within minutes"}
    - {turn_id: 4, quote: "Offline and online features come from the same feature definitions, and training uses point-in-time joins to avoid leakage."}
    - {turn_id: 4, quote: "If the ranker times out at 150 ms we serve the last good cached page for that profile, and if that is missing a regional popularity page."}
  modeling_choices:
    - {turn_id: 6, quote: "A gradient boosted tree on engineered features is cheap and handles cold start through metadata, but it is weak on viewing order."}
    - {turn_id: 6, quote: "The loss is listwise with two heads, play-start and watch completion, combined with weights I tune against retention in tests."}
    - {turn_id: 6, quote: "so I log the position and the propensity of each impression"}
    - {turn_id: 6, quote: "To choose between models offline I use NDCG@10 on a time-based holdout plus an inverse-propensity replay estimate on the exploration slice."}
  scale_reliability_security:
    - {turn_id: 8, quote: "Availability target: 99.95% for page loads, with p99 under 300 ms."}
    - {turn_id: 8, quote: "if the online feature store is down, the ranker runs with batch-computed default features from the cache, with lower quality but a page"}
    - {turn_id: 8, quote: "viewing history features are tagged restricted, access is per service and audited"}
    - {turn_id: 8, quote: "The cost driver is GPU inference for the sequence encoder"}
  online_validation_monitoring:
    - {turn_id: 10, quote: "it is a relative measure: it tells me which ranker members prefer inside the same list and says nothing about retention"}
    - {turn_id: 10, quote: "Offline and online metrics can disagree because the offline replay is biased by the logging policy and by position"}
    - {turn_id: 10, quote: "Rollback trigger: a guardrail breach or a fallback rate above 5% for ten minutes."}
    - {turn_id: 10, quote: "I keep the epsilon exploration traffic running so the data stay unbiased."}
  culture_signals:
    - {turn_id: 12, quote: "I would not change anything."}
    - {turn_id: 12, quote: "Honestly the product partner is wrong here and I have seen this request many times"}
    - {turn_id: 12, quote: "I do not need to measure anything to know the batch approach wins."}
hints: []
---

# Scorecard: 01-ml-system-design@design

> Recommendation derived by the simulator's pedagogical rule; Netflix does not use a common scale.
> Recomendación derivada por la regla pedagógica del simulador; Netflix no usa una escala común.

## Summary
**Recommendation: fail. Observed level: L5.**

The technical design was strong and met the L5 Yes bar on all five core competencies without any hints. The candidate framed the problem with a separate business goal and proxy metric, gave explicit numbers as assumptions, named guardrails and constraints, and confirmed scope. The design covered batch, nearline and online paths with feature consistency and a fallback chain. On modeling, the candidate compared two models, defined the loss and handled exposure and position bias. The reliability section had targets, degraded modes, access control and a cost mitigation. The validation section had interleaving, then an A/B test, an account of offline/online disagreement, exploration and alerting.

The fail comes from the non-core `culture_signals`, scored Strong No. In the culture probe (T11–T12) the candidate refused to engage with the stakeholder's concern. They named nothing that would change their mind, dismissed measurement, and planned to escalate instead of discussing. That contradicts the L5 bar. Under the fixed rule, any non-core SN gives `fail`.

The interview closed normally (final meta `phase: closed`, with no uncovered signal points recorded). The transcript header shows instance id `08-ml-system-design@design`, while the config gives `01-ml-system-design@design`. This scorecard uses the config id.

## Scores and evidence

### problem_framing_requirements: Y (core)
- T2: "I would separate the business goal, long-term member satisfaction measured through retention, from the proxy I can optimize day to day"
- T2: "about 200 million members, a catalog of about 20,000 titles, a p99 budget of 300 ms for the page request"
- T2: "Guardrails: row diversity and play-start rate per profile must not regress, and cost per thousand page requests stays flat."
- T2: "Does that scope match yours, including several profiles per account and TV as the primary device?"

Every L5 element was present before any components were discussed:
- business goal separated from the proxy metric
- scale, latency and freshness given as assumptions
- guardrails named
- privacy and licensing constraints named
- scope confirmed with the interviewer

The answer did not reach L6. The candidate did not say what they would leave out of v1, and gave no rule for continuing or stopping after launch.

### architecture_data_flow: Y (core)
- T4: "Nearline: a stream processor over the play-event log, Kafka plus a Flink-class engine, updates short-horizon features such as the last 20 plays within minutes"
- T4: "Offline and online features come from the same feature definitions, and training uses point-in-time joins to avoid leakage."
- T4: "If the ranker times out at 150 ms we serve the last good cached page for that profile, and if that is missing a regional popularity page."

The answer meets the L5 bar:
- batch, nearline and online paths are separated
- offline and online features stay consistent through shared definitions and point-in-time joins
- each hop has a technology class (ANN index, feature store, Kafka/Flink, key-value cache, low-latency store)
- one request is traced end to end, including the fallback chain

There was no L6 evidence: no reusable contracts, no comparison of two end-to-end alternatives, and no answer to what breaks first at 10x traffic.

### modeling_choices: Y (core)
- T6: "A gradient boosted tree on engineered features is cheap and handles cold start through metadata, but it is weak on viewing order."
- T6: "The loss is listwise with two heads, play-start and watch completion, combined with weights I tune against retention in tests."
- T6: "so I log the position and the propensity of each impression"
- T6: "To choose between models offline I use NDCG@10 on a time-based holdout plus an inverse-propensity replay estimate on the exploration slice."

The candidate compared two options against latency, data volume and cold start. They defined a listwise multi-head loss, explained how the training data were generated and how exposure and position bias them, and named the offline selection metric. All L5 elements are met.

### scale_reliability_security: Y (core)
- T8: "Availability target: 99.95% for page loads, with p99 under 300 ms."
- T8: "if the online feature store is down, the ranker runs with batch-computed default features from the cache, with lower quality but a page"
- T8: "viewing history features are tagged restricted, access is per service and audited"
- T8: "The cost driver is GPU inference for the sequence encoder"

The answer meets the L5 bar:
- availability and latency targets are set
- degraded modes are given for three failures (ranker, feature store, cold cache)
- access control covers viewing history and unreleased titles
- a cost driver is named with a mitigation (nearline embeddings only for active profiles)

There are some L6 elements: data classification, auditing and retention. Regional failure, owners per failure class and a deployment trade-off with numbers are missing, so the score stays at Y.

### online_validation_monitoring: Y (core)
- T10: "it is a relative measure: it tells me which ranker members prefer inside the same list and says nothing about retention"
- T10: "Offline and online metrics can disagree because the offline replay is biased by the logging policy and by position"
- T10: "Rollback trigger: a guardrail breach or a fallback rate above 5% for ten minutes."
- T10: "I keep the epsilon exploration traffic running so the data stay unbiased."

All L5 elements are present:
- interleaving first, then an A/B test
- interleaving explained as a relative measure that does not capture retention
- reasons why offline and online metrics disagree
- an exploration mechanism
- three layers of monitors with a rollback action

There was a rollback threshold, which is an L6 element. The rest of the L6 bar (validating many concurrent variants, long-term holdouts, auditing offline/online alignment over time) was absent.

### culture_signals: SN (non-core)
- T12: "I would not change anything."
- T12: "Honestly the product partner is wrong here and I have seen this request many times"
- T12: "I do not need to measure anything to know the batch approach wins."

The probe (T11) asked the candidate to defend or change the design and to say what evidence would change their mind. The candidate:
- offered no evidence or stated assumption for the stakeholder; they relied on authority ("I know what is best for the latency budget")
- explicitly refused to name anything that would change their mind
- rejected measurement
- planned to close the discussion ("tell them it is settled") and escalate instead of engaging

This contradicts the **judgment** value (deciding based on data and reasoning, staying open to evidence). It also contradicts **candor**: the candidate dismissed the partner instead of disagreeing directly and respectfully. It is the opposite of the curiosity the memo expects toward a stakeholder's concern. There was a valid technical defense available, since T4 refreshes features within minutes, but the candidate presented it as settled rather than as an argument.

**What a Yes-level answer would have looked like (L5):** "I'd keep nearline refresh as the default. It already shows a title started five minutes ago on the next page load. Real-time scoring everywhere would put a GPU sequence encoder on every request and threaten the 300 ms p99 at roughly 2-3x the serving cost. I think the partner's concern about staleness is fair, though, and I don't actually know how often members notice it. To find out, I'd measure how often the page changes between sessions and run a small A/B test: real-time re-ranking of only the first row against the current design, with retention and play-start as the metrics. If real-time beats the current design on retention by more than the extra cost justifies, or if staleness complaints line up with drops in engagement, I'd move more rows to real time. I'd share that plan with the partner directly and agree on the decision criteria together."

## Hints
None.

## Uncovered signal points
None. The interview closed normally (`phase: closed`), and no uncovered signal points were recorded in the final interviewer meta.

## Strengths and gaps
**Strengths**
- Precise, quantified framing: the business goal is separated from the proxy, with assumptions, guardrails and constraints, all stated before any design.
- A complete architecture with batch, nearline and online paths, feature consistency and a layered fallback chain.
- Mature modeling reasoning: a model comparison tied to the constraints, an explicit loss, propensity logging, position debiasing, exploration and off-policy evaluation.
- Concrete reliability and security: targets, three degraded modes, data classification, auditing and retention, and filtering unreleased titles at the assembler so a ranker bug cannot leak them.
- A well-structured validation plan that correctly states the limits of interleaving and has explicit rollback triggers.

**Gaps**
- Handling stakeholder pushback (the deciding gap). The candidate closed off discussion, refused to name evidence that would change their mind, rejected measurement, and turned to escalation instead of discussion. At L5 this alone fails the stage even with strong technical work.
- Toward L6 on the technical side: no v1 non-goals or post-launch stop rule; no reusable contracts or comparison of end-to-end alternatives; no regional failure design or owner per failure class; no program for many concurrent experiments or long-term holdouts.

## Study plan
1. **Defending a trade-off with evidence and staying open to change (culture_signals).** Practice the `culture` stage ([study-map: ml-system-design.culture_signals](netflix-ml-interview/study-map.yaml): practice_stage `culture`) and reread the Netflix culture memo (jobs.netflix.com/culture) on judgment, candor and farming for dissent. For every design defense, practice saying three things: the assumption behind the choice, the specific measurement or result that would change it, and an experiment you would offer the stakeholder.
2. **Toward L6 framing and validation (problem_framing_requirements, online_validation_monitoring).** Study `recsys-course/19_elite_playbook/` and `recsys-course/18_capstone/` for v1 non-goals and post-launch decision rules. Study `recsys-course/15_online_experimentation/` for programs with many concurrent variants, long-term holdouts and auditing offline/online alignment over time.
3. **Toward L6 architecture and reliability (architecture_data_flow, scale_reliability_security).** Study `recsys-course/16_production_serving/` and `recsys-course/17_mlops_monitoring/`: versioned component contracts, comparing two end-to-end deployments on cost and latency with numbers, regional failover and incident ownership. Then practice the `ml-system-design` stage again.
