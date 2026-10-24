---
instance_id: 01-ml-system-design@design
stage: ml-system-design
variant: design
level: L5
rubric_version: 1
recommendation: fail
level_observed: none
scores:
  problem_framing_requirements: SN
  architecture_data_flow: N
  modeling_choices: N
  scale_reliability_security: N
  online_validation_monitoring: N
  culture_signals: N
evidence:
  problem_framing_requirements:
    - {turn_id: 2, quote: "The goal is to maximize member satisfaction and engagement in a scalable, robust and flexible way"}
    - {turn_id: 4, quote: "Scale would be large, as Netflix is a global service, and latency would need to be low to provide a great experience."}
    - {turn_id: 4, quote: "the right numbers would be defined together with the stakeholders as the project evolves"}
  architecture_data_flow:
    - {turn_id: 6, quote: "We would use a data lake, streaming, batch processing, a feature store, a model registry, a serving layer, caching, a CDN, load balancers and monitoring"}
    - {turn_id: 6, quote: "Data flows from the sources through the pipelines into the models and then to the application layer"}
  modeling_choices:
    - {turn_id: 8, quote: "We would use state of the art deep learning, like transformers, possibly with attention, embeddings and multi-task learning"}
    - {turn_id: 8, quote: "Training would use large amounts of high quality data and careful hyperparameter tuning, with regularization to avoid overfitting."}
  scale_reliability_security:
    - {turn_id: 10, quote: "For failures we would have redundancy, fault tolerance, graceful degradation and monitoring and alerting, following SRE best practices, so that the system is highly available."}
    - {turn_id: 6, quote: "Each component would be designed with best practices for reliability and security in mind"}
  online_validation_monitoring:
    - {turn_id: 10, quote: "For validation we would run experiments, A/B tests and analyze the results with statistical rigor, and monitor the key metrics so that we can iterate."}
  culture_signals:
    - {turn_id: 4, quote: "the right numbers would be defined together with the stakeholders as the project evolves"}
    - {turn_id: 10, quote: "I am confident that with a great team we can build something amazing."}
hints: []
---

# Scorecard: 01-ml-system-design@design

> Recommendation derived by the simulator's pedagogical rule; Netflix does not use a common scale.
> Recomendación derivada por la regla pedagógica del simulador; Netflix no usa una escala común.

## Summary

**Recommendation: fail. Observed level: none.**

The session ended normally: the final interviewer turn (T11) has `phase: closed` and lists no uncovered signal points. The candidate talked for most of the 46 minutes but never committed to anything concrete. There were no clarifying questions. When asked directly for a metric and numbers, the candidate still gave none. The architecture was a list of technology categories with no request path. The modeling answer was a list of model families with no label, no loss and no offline metric. Failure handling and validation stayed at the level of "best practices" and "A/B tests". Problem framing is scored SN because the candidate designed without stating any requirement, which the rubric names as a contradiction of the bar. The other four core competencies are N. With one core SN and four core N, the fixed rule gives `fail`. No level's Yes bar is met by all core competencies, not even L4's, so the observed level is `none`. No hints were given. The answers were long, but length did not count; content was judged against the bar.

## Scores and evidence

### problem_framing_requirements (core): SN
- T2: "The goal is to maximize member satisfaction and engagement in a scalable, robust and flexible way"
- T4: "Scale would be large, as Netflix is a global service, and latency would need to be low to provide a great experience."
- T4: "the right numbers would be defined together with the stakeholders as the project evolves"

The interviewer invited questions (T1). The candidate asked none, did not restate the problem and did not separate a business goal from a proxy metric. When the interviewer explicitly asked for a metric and scale or latency numbers (T3), the candidate listed metric categories and pushed the numbers to later. That is designing without stating any requirement, which contradicts the bar.

**Model Yes answer (L5):** "Before I design: is this the logged-in homepage on all three devices, and is row order in scope as well as the titles inside each row? The business goal is long-term retention. My proxy is qualified plays per session, meaning plays that pass a short-watch threshold. Guardrails are page latency and the share of sessions with no play. Assumptions: about 250M members and peak load of roughly 100k homepage requests per second. p99 latency is about 200 ms on TV. Recent viewing should show up within a few minutes. The constraint is that viewing history is sensitive data. Does that scope match what you have in mind?"

### architecture_data_flow (core): N
- T6: "We would use a data lake, streaming, batch processing, a feature store, a model registry, a serving layer, caching, a CDN, load balancers and monitoring"
- T6: "Data flows from the sources through the pipelines into the models and then to the application layer"

The candidate named the components but never connected them. There is no statement of what each component reads or writes and no separate batch and real-time paths. Offline/online feature consistency is never mentioned, no request is traced, and no fallback is specified. Some elements are present, so the score is N rather than SN.

**Model Yes answer (L5):** "There are two paths. In batch, every night we compute candidate pools and member embeddings from viewing logs in the warehouse and write them to a key-value store. In real time, play and browse events go through a stream and update session features within seconds. To avoid skew, both paths compute features with the same feature definitions and log them at serving time. One request: the device calls the homepage service. That service pulls candidates per row from the KV store and ranks them with a low-latency model. A second model orders the rows, and dedup rules are applied across rows. If the ranker times out, we serve the precomputed page cached at the edge."

### modeling_choices (core): N
- T8: "We would use state of the art deep learning, like transformers, possibly with attention, embeddings and multi-task learning"
- T8: "Training would use large amounts of high quality data and careful hyperparameter tuning, with regularization to avoid overfitting."

The candidate named model families, but did not tie any of them to a stage (retrieval, ranking, row selection). There is no training label, no loss, no comparison against latency or cold-start constraints, no account of exposure or position bias, and no offline metric.

**Model Yes answer (L5):** "Retrieval uses a two-tower model, chosen for ANN latency. Ranking is gradient-boosted trees as the baseline against a multi-task neural ranker. GBDT is cheap and easy to interpret but weak on sequence signals. The neural ranker handles cold start better through content embeddings. The label is a qualified play from an impression, and the loss is a weighted cross-entropy over play and completion heads. Training data comes only from impressions the old system showed, so it carries exposure and position bias. I correct for that with position as a training feature and propensity weighting. I pick the model on offline NDCG and recall@k measured on a time-based holdout."

### scale_reliability_security (core): N
- T10: "For failures we would have redundancy, fault tolerance, graceful degradation and monitoring and alerting, following SRE best practices, so that the system is highly available."
- T6: "Each component would be designed with best practices for reliability and security in mind"

Failure was mentioned, but only in generic terms. There is no availability or latency target, and no degraded mode for any specific component failure. Access control for viewing history or unreleased content is never discussed, and no cost driver is named.

**Model Yes answer (L5):** "Target: 99.99% availability and p99 under 200 ms. If the ranker fails, we serve the cached nightly page. If the real-time feature store fails, we rank with batch features only and flag the request. Viewing history is only reachable through a scoped service identity, and unreleased titles are filtered by an entitlement check before ranking. GPU inference for the ranker is the main cost driver. I keep it down by ranking only the top few hundred candidates and caching pages for idle members."

### online_validation_monitoring (core): N
- T10: "For validation we would run experiments, A/B tests and analyze the results with statistical rigor, and monitor the key metrics so that we can iterate."

The candidate proposed an A/B test, but with no primary metric. There is no interleaving stage and no explanation of why offline and online metrics can disagree. Explore/exploit is never mentioned, and there are no specific model-quality or drift monitors with alert actions.

**Model Yes answer (L5):** "First, interleave the new ranker against production to screen variants quickly. Interleaving gives a relative preference only and says nothing about retention. Survivors go to an A/B test with streaming hours as the primary metric and retention as a secondary readout. Offline NDCG can disagree with online results because of feedback loops and presentation effects. A small exploration slot in some rows gathers less biased data. Monitors: score distribution, feature drift (PSI) and calibration. On an alert, we roll back to the last model and page the owner."

### culture_signals (non-core): N
- T4: "the right numbers would be defined together with the stakeholders as the project evolves"
- T10: "I am confident that with a great team we can build something amazing."

There was no explicit culture probe, but in T3 the interviewer pressed the candidate to commit. The candidate deferred the decision to stakeholders instead of stating an assumption and defending it. That is the opposite of the judgment and courage values in the memo. The candidate did not say what would change their mind, did not say "I do not know" while proposing a way to find out, and did not disagree with any position. Candor would mean saying plainly what is unknown.

**Model Yes answer (L5):** "I don't know the real peak traffic, so I'll assume 100k requests per second and design for that. If the actual number is ten times higher, I'd change the plan and precompute more pages instead of ranking live. I'd push back on chasing engagement alone: optimizing clicks can hurt retention, so I'd hold the line on a qualified-play metric."

## Hints

None. No hint records appear in the interviewer meta, so no caps apply.

## Uncovered signal points

None recorded. The session closed normally (`phase: closed` in T11), and the final interviewer meta lists no uncovered signal points. The gaps above are content gaps in the candidate's answers, not points left uncovered for lack of time.

## Strengths and gaps

**Strengths**
- The candidate stayed on topic and gave an answer to every question.
- The vocabulary covered the right areas: feature store, batch and streaming, multi-task learning, graceful degradation and A/B testing.

**Gaps**
- No answer committed to anything concrete. There were no numbers, no named metric and no explicit assumption, even after being asked directly.
- There were no clarifying questions before designing.
- No request was traced through the system, and no fallback was specified.
- The model choice was not tied to any stage, label, loss, bias or offline metric.
- There were no specific failure modes, no access-control discussion and no cost driver.
- Validation stopped at "A/B tests": no interleaving, no explore/exploit and no named monitors.
- The candidate deferred decisions to stakeholders instead of stating and defending a trade-off.

## Study plan

1. **Problem framing with explicit numbers (core, SN).** Practice opening every design with three clarifying questions. Then state one business goal, one proxy metric, one guardrail, and latency, freshness and scale numbers as assumptions. Study [recsys-course/00_intro/](recsys-course/00_intro/), [recsys-course/18_capstone/](recsys-course/18_capstone/) and [recsys-course/19_elite_playbook/](recsys-course/19_elite_playbook/), then do the `ml-system-design` practice stage again.
2. **Concrete architecture and modeling (core, N).** Draw the batch and real-time paths for a homepage system and trace one request, including the cache fallback. Then write the label, the loss and the bias correction for each model stage. Study [recsys-course/16_production_serving/](recsys-course/16_production_serving/), [recsys-course/08_deep_retrieval_ann/](recsys-course/08_deep_retrieval_ann/), [recsys-course/06_ctr_ranking/](recsys-course/06_ctr_ranking/) and [recsys-course/07_learning_to_rank_multitask/](recsys-course/07_learning_to_rank_multitask/).
3. **Validation, reliability and monitoring (core, N).** Learn the two-stage interleaving-then-A/B process, explore/exploit, and specific drift monitors with alert actions. Also prepare two degraded modes and one cost mitigation. Study [recsys-course/15_online_experimentation/](recsys-course/15_online_experimentation/), [recsys-course/14_bandits_rl_ope/](recsys-course/14_bandits_rl_ope/) and [recsys-course/17_mlops_monitoring/](recsys-course/17_mlops_monitoring/).

For culture signals, practice the `culture` stage and read the Netflix culture memo at jobs.netflix.com/culture. Focus on judgment and courage: state an assumption, defend it, and name what would change your mind.
