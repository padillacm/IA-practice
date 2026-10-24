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
    - {turn_id: 4, quote: "Offline and online features come from the same feature definitions, and training uses point-in-time joins to avoid leakage."}
    - {turn_id: 4, quote: "the page service reads precomputed candidate rows from a key-value cache keyed by profile id, fetches online features from a low-latency store"}
    - {turn_id: 4, quote: "If the ranker times out at 150 ms we serve the last good cached page for that profile, and if that is missing a regional popularity page."}
  modeling_choices:
    - {turn_id: 6, quote: "A transformer sequence model over the last 50 plays captures order but costs about 30 ms per batch on GPU and needs more data."}
    - {turn_id: 6, quote: "The loss is listwise with two heads, play-start and watch completion"}
    - {turn_id: 6, quote: "The training data come from logged impressions, which are biased by the old policy's exposure and by position"}
    - {turn_id: 6, quote: "To choose between models offline I use NDCG@10 on a time-based holdout"}
  scale_reliability_security:
    - {turn_id: 8, quote: "Availability target: 99.95% for page loads, with p99 under 300 ms."}
    - {turn_id: 8, quote: "if the online feature store is down, the ranker runs with batch-computed default features from the cache"}
    - {turn_id: 8, quote: "viewing history features are tagged restricted, access is per service and audited"}
    - {turn_id: 8, quote: "The cost driver is GPU inference for the sequence encoder"}
  online_validation_monitoring:
    - {turn_id: 10, quote: "First interleaving, which needs far less traffic and detects ranking preference quickly, but it is a relative measure"}
    - {turn_id: 10, quote: "it tells me which ranker members prefer inside the same list and says nothing about retention."}
    - {turn_id: 10, quote: "Offline and online metrics can disagree because the offline replay is biased by the logging policy and by position"}
    - {turn_id: 10, quote: "Rollback trigger: a guardrail breach or a fallback rate above 5% for ten minutes."}
    - {turn_id: 10, quote: "I keep the epsilon exploration traffic running so the data stay unbiased."}
  culture_signals:
    - {turn_id: 12, quote: "I would not change anything."}
    - {turn_id: 12, quote: "people who do not do ML tend to ask for real-time everywhere without understanding the cost."}
    - {turn_id: 12, quote: "I do not need to measure anything to know the batch approach wins."}
hints: []
---

# Scorecard: 01-ml-system-design@design

> Recommendation derived by the simulator's pedagogical rule; Netflix does not use a common scale.
> Recomendación derivada por la regla pedagógica del simulador; Netflix no usa una escala común.

## Summary
**Recommendation: fail. Observed level: L5.**

On the technical side the candidate met the L5 bar on all five core competencies. The framing separated the goal from the proxy, stated numeric assumptions, named guardrails and a privacy constraint, and confirmed scope. The architecture had batch, nearline and online paths, feature consistency, and a request trace with fallbacks. The modeling compared options against the constraints, named the bias in the training data and the offline metric. The reliability answer had targets, degraded modes, access control and a cost driver. The validation answer covered interleaving followed by an A/B test, explore/exploit and monitors with rollback triggers.

None of these reached the L6 bar. There was no organizational framing, no reusable contracts or 10x analysis, no cross-surface modeling strategy, no design for regional failure, and no program for running many variants at once.

The culture probe (T11-T12) contradicted the culture bar. The candidate refused to name any evidence that would change their mind, dismissed the stakeholder, and rejected measurement outright. Under the fixed rule, a Strong No on a non-core competency gives `fail` even though every core competency is Y. The strong technical answers were not allowed to raise the culture score. No hints were given. The session ended with a normal close (`phase: closed`, no uncovered points).

## Scores and evidence

### problem_framing_requirements: Y (core)
- T2: "I would separate the business goal, long-term member satisfaction measured through retention, from the proxy I can optimize day to day"
- T2: "about 200 million members, a catalog of about 20,000 titles, a p99 budget of 300 ms for the page request"
- T2: "Guardrails: row diversity and play-start rate per profile must not regress, and cost per thousand page requests stays flat."
- T2: "Does that scope match yours, including several profiles per account and TV as the primary device?"

Every element of the L5 bar was present without prompting: goal versus proxy, scale, latency and freshness assumptions, guardrails, a privacy constraint and scope confirmation. It is not SY because the candidate did not place the problem within adjacent surfaces or teams, did not say what they would leave out of v1, and gave no post-launch decision rule.

### architecture_data_flow: Y (core)
- T4: "Offline and online features come from the same feature definitions, and training uses point-in-time joins to avoid leakage."
- T4: "the page service reads precomputed candidate rows from a key-value cache keyed by profile id, fetches online features from a low-latency store"
- T4: "If the ranker times out at 150 ms we serve the last good cached page for that profile, and if that is missing a regional popularity page."

The answer separated batch, nearline and online paths and named a technology class for each hop (ANN index, feature store, Kafka/Flink-class stream, KV cache). It specified feature consistency and traced a request through its fallback chain. It is not SY because there were no versioned contracts or ownership boundaries, no comparison of two end-to-end alternatives, and no answer to which component breaks first at 10x traffic.

### modeling_choices: Y (core)
- T6: "A transformer sequence model over the last 50 plays captures order but costs about 30 ms per batch on GPU and needs more data."
- T6: "The loss is listwise with two heads, play-start and watch completion"
- T6: "The training data come from logged impressions, which are biased by the old policy's exposure and by position"
- T6: "To choose between models offline I use NDCG@10 on a time-based holdout"

The candidate compared GBDT with a transformer on latency, data volume and cold start, defined the loss, named exposure and position bias and how to correct them, and stated the offline metric. It is not SY because there was no shared-versus-per-task strategy across surfaces, no quantified gain against cost, and no experiment that would falsify the main modeling assumption.

### scale_reliability_security: Y (core)
- T8: "Availability target: 99.95% for page loads, with p99 under 300 ms."
- T8: "if the online feature store is down, the ranker runs with batch-computed default features from the cache"
- T8: "viewing history features are tagged restricted, access is per service and audited"
- T8: "The cost driver is GPU inference for the sequence encoder"

The answer covered targets, three degraded modes, access control for viewing history and unreleased titles, and a cost driver with a mitigation (nearline embedding only for profiles active in the last day). The security model included classification, auditing and retention. It is not SY because the interviewer had already asked about security, and there was no design for regional failure, no owner per failure class, and no numeric comparison of two deployment options.

### online_validation_monitoring: Y (core)
- T10: "First interleaving, which needs far less traffic and detects ranking preference quickly, but it is a relative measure"
- T10: "it tells me which ranker members prefer inside the same list and says nothing about retention."
- T10: "Offline and online metrics can disagree because the offline replay is biased by the logging policy and by position"
- T10: "Rollback trigger: a guardrail breach or a fallback rate above 5% for ten minutes."
- T10: "I keep the epsilon exploration traffic running so the data stay unbiased."

Every L5 element was present, including model-quality and data-drift monitors tied to an alert action. The candidate also set rollback thresholds, which is part of the L6 bar. It is not SY because there was no program for many concurrent variants (pruning, traffic allocation, interference, long-term holdouts) and no plan for auditing offline/online metric alignment over time.

### culture_signals: SN (non-core)
- T12: "I would not change anything."
- T12: "people who do not do ML tend to ask for real-time everywhere without understanding the cost."
- T12: "I do not need to measure anything to know the batch approach wins."

The interviewer's probe pointed at **judgment**, and the answer also showed the **candor** and **courage** values. The answer contradicts the L5 bar:
- The candidate defended the design by authority ("I know what is best") rather than evidence. Their earlier point about minutes-level freshness was in the design but was not used as an argument here.
- They explicitly refused to name what would change their mind and rejected measurement.
- They said nothing about uncertainty.
- The disagreement was direct but not polite: they dismissed the partner's competence and went straight to escalation.

That is the opposite of candor offered with care and of judgment based on data.

**Model Yes answer (L5):** "I'd keep batch plus nearline for most rows. The main 'staleness' complaint is about recent plays, and the nearline path already reflects those within minutes. Real-time scoring everywhere would roughly multiply GPU cost and put the sequence encoder back on the request path. I don't know how much members actually notice staleness, though. I'd look at whether play-starts drop for profiles whose page is older than N minutes. Then I'd run a small A/B where one row, say 'because you watched', is scored in real time. If that lifts retention or play-start beyond a set threshold at an acceptable cost per thousand requests, I'd extend real-time scoring. I'll tell the partner directly that I disagree today and show them what result would change my view."

## Hints
None.

## Uncovered signal points
None. The session ended with a normal close (`phase: closed`) and no uncovered signal points were recorded.

## Strengths and gaps
**Strengths**
- Precise, numeric framing. The business goal was kept separate from the proxy, with guardrails and constraints stated up front.
- A coherent three-path architecture with explicit feature consistency and a layered fallback chain.
- Bias-aware modeling: logged propensities, position neutralization, an exploration slice and IPS replay.
- A mature validation plan: interleaving with its limits stated, an A/B test over two weeks, three monitoring layers with numeric rollback triggers.

**Gaps**
- Handling stakeholder pushback. When challenged, the candidate refused evidence, dismissed the partner and escalated instead of engaging. This one gap fails the stage on its own.
- For L6 growth: organizational scope (adjacent surfaces, what to leave out of v1), reusable contracts and 10x bottlenecks, cross-surface modeling strategy, design for regional failure, and a validation program for many concurrent variants.

## Study plan
1. **culture_signals (cause of the fail):** practice the `culture` stage and reread the [Netflix culture memo: jobs.netflix.com/culture](https://jobs.netflix.com/culture), focusing on judgment, candor and courage. Drill a pushback answer in four steps: state the assumption behind your choice, name the evidence that would change your mind, propose a cheap test, and disagree respectfully.
2. **online_validation_monitoring (to reach L6):** `recsys-course/15_online_experimentation/` and `recsys-course/14_bandits_rl_ope/`. Cover running many concurrent tests, interference, long-term holdouts and auditing offline/online metric alignment.
3. **architecture_data_flow / scale_reliability_security (to reach L6):** `recsys-course/16_production_serving/` and `recsys-course/17_mlops_monitoring/`. Cover versioned contracts, 10x bottleneck analysis, regional failover and numeric comparison of deployment options. Then practice the `ml-system-design` stage again.
