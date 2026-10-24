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
    - {turn_id: 4, quote: "Nearline: a stream processor over the play-event log, Kafka plus a Flink-class engine, updates short-horizon features such as the last 20 plays within minutes"}
    - {turn_id: 4, quote: "Offline and online features come from the same feature definitions, and training uses point-in-time joins to avoid leakage."}
    - {turn_id: 4, quote: "If the ranker times out at 150 ms we serve the last good cached page for that profile, and if that is missing a regional popularity page."}
  modeling_choices:
    - {turn_id: 6, quote: "A transformer sequence model over the last 50 plays captures order but costs about 30 ms per batch on GPU and needs more data."}
    - {turn_id: 6, quote: "The loss is listwise with two heads, play-start and watch completion, combined with weights I tune against retention in tests."}
    - {turn_id: 6, quote: "The training data come from logged impressions, which are biased by the old policy's exposure and by position"}
    - {turn_id: 6, quote: "To choose between models offline I use NDCG@10 on a time-based holdout plus an inverse-propensity replay estimate on the exploration slice."}
  scale_reliability_security:
    - {turn_id: 8, quote: "Availability target: 99.95% for page loads, with p99 under 300 ms."}
    - {turn_id: 8, quote: "if the online feature store is down, the ranker runs with batch-computed default features from the cache, with lower quality but a page"}
    - {turn_id: 8, quote: "viewing history features are tagged restricted, access is per service and audited"}
    - {turn_id: 8, quote: "The cost driver is GPU inference for the sequence encoder"}
  online_validation_monitoring:
    - {turn_id: 10, quote: "First interleaving, which needs far less traffic and detects ranking preference quickly"}
    - {turn_id: 10, quote: "it is a relative measure: it tells me which ranker members prefer inside the same list and says nothing about retention"}
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
**Recommendation: pass. Observed level: L5.**

The candidate met the L5 Yes bar on all five core competencies and on culture signals. No hints were given. The session ended normally: the final interviewer meta shows `phase: closed` and lists no uncovered points.

- **Framing:** the candidate set the scope before designing anything. They separated the business goal (retention) from the proxy (qualified play-starts), stated scale, latency and freshness numbers as assumptions, named guardrails and constraints, and confirmed scope with the interviewer.
- **Architecture:** the batch, nearline and online paths were separated, and offline/online feature consistency was specified. One request was traced through the system, including cache and fallback paths.
- **Modeling:** two ranker options were compared against latency, data and cold-start constraints. The candidate defined the loss, named the exposure and position bias in the training data, and gave the offline selection metric.
- **Reliability and security:** the candidate set a target, described three degraded modes, covered access control for viewing history and unreleased titles, and named the main cost driver with a mitigation.
- **Validation:** the candidate covered every L5 element.
- **Culture:** in the culture probe the candidate showed judgment and candor.

None of the core competencies clearly reached the L6 bar, so no score is SY. The transcript's front-matter shows the instance id `08-ml-system-design@design`. The config id `01-ml-system-design@design` is used here.

## Scores and evidence

### problem_framing_requirements: Y
- T2: "I would separate the business goal, long-term member satisfaction measured through retention, from the proxy I can optimize day to day"
- T2: "a p99 budget of 300 ms for the page request"
- T2: "Guardrails: row diversity and play-start rate per profile must not regress, and cost per thousand page requests stays flat."
- T2: "Does that scope match yours, including several profiles per account and TV as the primary device?"

Every L5 element was present and unprompted:
- goal separated from proxy;
- explicit scale, latency and freshness assumptions (200M members, 20k titles, 300 ms p99, five-minute freshness);
- guardrails;
- privacy and licensing constraints;
- scope confirmed with the interviewer.

The L6 elements were not shown: no wider product or organization framing, no list of what to leave out of version 1, and no continue/stop decision rule after launch.

### architecture_data_flow: Y
- T4: "Nearline: a stream processor over the play-event log, Kafka plus a Flink-class engine, updates short-horizon features such as the last 20 plays within minutes"
- T4: "Offline and online features come from the same feature definitions, and training uses point-in-time joins to avoid leakage."
- T4: "If the ranker times out at 150 ms we serve the last good cached page for that profile, and if that is missing a regional popularity page."

The candidate:
- separated the batch, nearline and online paths;
- named a technology class for each hop (ANN index, feature store, stream processor, key-value cache, low-latency store);
- addressed feature consistency through shared definitions and point-in-time joins;
- traced a request through the system with latency figures and a two-level fallback.

Not at L6: there were no reusable versioned contracts or ownership boundaries, and no analysis of which component breaks first at 10x traffic.

### modeling_choices: Y
- T6: "A transformer sequence model over the last 50 plays captures order but costs about 30 ms per batch on GPU and needs more data."
- T6: "The loss is listwise with two heads, play-start and watch completion, combined with weights I tune against retention in tests."
- T6: "The training data come from logged impressions, which are biased by the old policy's exposure and by position"
- T6: "To choose between models offline I use NDCG@10 on a time-based holdout plus an inverse-propensity replay estimate on the exploration slice."

The candidate:
- compared GBDT with a sequence transformer against latency, data volume and cold start;
- solved the latency problem by computing the embedding nearline;
- defined a multi-head listwise loss;
- described how the training data was generated and its bias, with mitigations (position feature, propensity logging, epsilon exploration);
- named the offline selection metric.

L6 elements were absent: no strategy for shared versus per-task models across surfaces, and no experiment that would falsify the main modeling assumption.

### scale_reliability_security: Y
- T8: "Availability target: 99.95% for page loads, with p99 under 300 ms."
- T8: "if the online feature store is down, the ranker runs with batch-computed default features from the cache, with lower quality but a page"
- T8: "viewing history features are tagged restricted, access is per service and audited"
- T8: "The cost driver is GPU inference for the sequence encoder"

The candidate:
- set availability and latency targets;
- described degraded modes for three failures (ranker, online feature store, cold cache);
- covered access control for viewing history and filtering of unreleased titles;
- named the GPU cost driver and mitigated it with nearline computation limited to active profiles.

The interviewer raised security, so the classification, auditing and retention points were not unprompted in the L6 sense. Regional failure and incident ownership were not addressed.

### online_validation_monitoring: Y
- T10: "First interleaving, which needs far less traffic and detects ranking preference quickly"
- T10: "it is a relative measure: it tells me which ranker members prefer inside the same list and says nothing about retention"
- T10: "Offline and online metrics can disagree because the offline replay is biased by the logging policy and by position"
- T10: "Because the system chooses what to show, I keep the epsilon exploration traffic running so the data stay unbiased."
- T10: "Rollback trigger: a guardrail breach or a fallback rate above 5% for ten minutes."

Every L5 element was present:
- interleaving as the first stage, then an A/B test;
- the limits of interleaving (relative measure, no retention signal);
- reasons offline and online metrics disagree;
- an explore/exploit mechanism;
- model-quality, data and system monitors with a rollback action.

The rollback threshold touches on L6, but there was no program for many concurrent variants and no plan to audit offline/online metric alignment over time.

### culture_signals: Y
- T12: "I would keep the hybrid but change one thing."
- T12: "full real-time scoring multiplies GPU cost and widens the tail latency, so it risks the 300 ms target"
- T12: "What would move me: a test where the real-time arm improves retention or play-starts by more than the cost justifies."
- T12: "I do not know yet how much staleness members actually notice, so I would measure it by running an A/B on cache age before we pay for the infrastructure."

In the judgment probe the candidate:
- disagreed directly and politely with the product partner;
- defended the trade-off with cost and latency reasoning;
- conceded the partner's valid point and narrowed the change (re-ranking at request time after a recent play);
- named the evidence that would change their mind;
- said "I do not know" and proposed a way to find out.

Memo values shown: judgment, candor and courage. Not at L6: the candidate did not name who to inform, propose farming for dissent, or set a trigger to reopen the decision.

## Hints
None.

## Uncovered signal points
None. The session closed normally with no uncovered points recorded.

## Strengths and gaps
**Strengths**
- Disciplined framing with explicit numerical assumptions and guardrails.
- A coherent batch/nearline/online architecture with layered fallbacks.
- Strong awareness of exposure and position bias, carried through from training to validation.
- A complete two-stage validation plan with concrete rollback triggers.
- A balanced response to stakeholder pushback.

**Gaps (toward L6)**
- No framing across surfaces or teams, and no explicit list of what to leave out of version 1.
- No reusable component contracts, and no analysis of the first component to break at 10x traffic.
- No experiment designed to falsify the main modeling assumption.
- No design for regional failover or incident ownership.
- No program for many concurrent test variants, and no long-term audit of offline/online metric alignment.
- In the culture probe, no mention of who to inform or how to farm for dissent before committing.

## Study plan
1. **Architecture at L6 scale:** work through [recsys-course/16_production_serving/](recsys-course/16_production_serving/) and [recsys-course/08_deep_retrieval_ann/](recsys-course/08_deep_retrieval_ann/). Practice comparing two end-to-end designs on cost, latency and operational burden, and finding the first component that breaks at 10x traffic (study-map `ml-system-design.architecture_data_flow`).
2. **Validation program design:** use [recsys-course/15_online_experimentation/](recsys-course/15_online_experimentation/), [recsys-course/14_bandits_rl_ope/](recsys-course/14_bandits_rl_ope/) and [recsys-course/17_mlops_monitoring/](recsys-course/17_mlops_monitoring/). Cover concurrent variants, pruning rules, interference between tests, long-term holdouts and auditing offline/online metric alignment (study-map `ml-system-design.online_validation_monitoring`).
3. **Reliability and security at L6:** use [recsys-course/16_production_serving/](recsys-course/16_production_serving/) and [recsys-course/17_mlops_monitoring/](recsys-course/17_mlops_monitoring/). Cover regional failover, an owner per failure class, and an unprompted data classification and retention model (study-map `ml-system-design.scale_reliability_security`).

Further practice:
- For framing, use [recsys-course/19_elite_playbook/](recsys-course/19_elite_playbook/) to practice saying what you would not build in version 1 and giving a decision rule after launch.
- For culture, practice the `culture` stage with the Netflix culture memo (jobs.netflix.com/culture), focusing on farming for dissent and on triggers to reopen a decision.
