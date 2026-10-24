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
    - {turn_id: 2, quote: "I believe that in order to design this system properly we need to consider many different aspects"}
    - {turn_id: 4, quote: "the right numbers would be defined together with the stakeholders as the project evolves"}
  architecture_data_flow:
    - {turn_id: 6, quote: "We would use a data lake, streaming, batch processing, a feature store, a model registry, a serving layer, caching, a CDN, load balancers and monitoring, all orchestrated with Kubernetes."}
    - {turn_id: 6, quote: "Data flows from the sources through the pipelines into the models and then to the application layer"}
  modeling_choices:
    - {turn_id: 8, quote: "We would use state of the art deep learning, like transformers, possibly with attention, embeddings and multi-task learning, and potentially large language models"}
    - {turn_id: 8, quote: "Training would use large amounts of high quality data and careful hyperparameter tuning, with regularization to avoid overfitting."}
  scale_reliability_security:
    - {turn_id: 4, quote: "Scale would be large, as Netflix is a global service, and latency would need to be low to provide a great experience."}
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

The session closed normally (final interviewer meta shows `phase: closed`, no uncovered points recorded). The candidate answered every prompt, but each answer listed generic concepts and made no concrete design decisions. When invited to ask clarifying questions, they asked none. When asked directly to commit to a metric, scale and latency numbers, they declined and said the numbers would be set later with stakeholders. The architecture, modeling, reliability and validation answers were lists of technologies and practices. None of them gave reasons, data contracts, labels, losses, targets or monitors. No core competency reaches the L5 bar, and most do not reach L4. Problem framing is Strong No: the candidate designed without stating any requirement even after being asked for one. The answers were long but not specific, and length was not credited.

## Scores and evidence

### problem_framing_requirements (core): SN
- T2: "I believe that in order to design this system properly we need to consider many different aspects"
- T4: "the right numbers would be defined together with the stakeholders as the project evolves"

The candidate was invited to ask questions and asked none. They gave no business goal or proxy metric, no guardrail and no constraint. When explicitly asked for numbers, they did not commit. This contradicts the bar: they designed without stating any requirement.

**Model Yes answer (L5):** "The business goal is long-term retention. As a proxy I'd use the fraction of sessions that start a title from the homepage and reach a qualified play, say more than 15 minutes. Guardrails are row diversity and the rate of abandoned plays. Assumptions: about 250M members, peak around 100k homepage renders per second, p99 under 200 ms for the page, and features fresh within minutes for continue-watching. Constraints: viewing history is sensitive, and the homepage must still render if personalization is down. Is the scope rows plus within-row ranking on all three devices, without artwork selection?"

### architecture_data_flow (core): N
- T6: "We would use a data lake, streaming, batch processing, a feature store, a model registry, a serving layer, caching, a CDN, load balancers and monitoring, all orchestrated with Kubernetes."
- T6: "Data flows from the sources through the pipelines into the models and then to the application layer"

The candidate named components, including batch, streaming and caching. They gave no reason for any of them, did not say what each component reads or writes, did not address offline/online feature consistency, and did not trace a request or a fallback path. Some elements are present and most are missing, so the score is N.

**Model Yes answer (L5):** "Batch path: a nightly job computes candidate pools and member embeddings from the play history in the warehouse. Streaming path: play and impression events update session features in a low-latency key-value store. Both paths use the same feature definitions, logged at serving time, so training and serving don't skew. A homepage request goes to the page service, which fetches candidates from an ANN index, scores them with the ranker, and assembles rows under device constraints. If the ranker times out, it serves the precomputed per-member page from a cache, and if that misses it serves a popularity page by region."

### modeling_choices (core): N
- T8: "We would use state of the art deep learning, like transformers, possibly with attention, embeddings and multi-task learning, and potentially large language models"
- T8: "Training would use large amounts of high quality data and careful hyperparameter tuning, with regularization to avoid overfitting."

The candidate listed many model families but did not compare them against any constraint. They gave no label or loss, did not describe how the training data is generated or its exposure/position bias, and named no offline metric.

**Model Yes answer (L5):** "Two-tower retrieval for candidates, plus a ranker that is either GBDT or a multi-task DNN. GBDT is cheaper and easier to serve at our p99. The DNN handles sequence features and cold start better through content embeddings. Label: qualified play within the session, with a secondary completion head. Loss: weighted cross-entropy per head. The training data comes from homepage impressions, so it has exposure and position bias. I'd add position as a training-only feature and use a small randomized slice for debiasing. I choose by NDCG@k on a time-split holdout, with a check on cold-start members."

### scale_reliability_security (core): N
- T4: "Scale would be large, as Netflix is a global service, and latency would need to be low to provide a great experience."
- T10: "For failures we would have redundancy, fault tolerance, graceful degradation and monitoring and alerting, following SRE best practices, so that the system is highly available."
- T6: "Each component would be designed with best practices for reliability and security in mind"

The candidate mentioned failure handling but gave no availability or latency target. They described no specific degraded mode for any component. Security came up only as "best practices", with nothing on access control for viewing history or unreleased content, and they named no cost driver. They did not reach the L4 bar either: no order-of-magnitude estimate and no concrete failure case with a response.

**Model Yes answer (L5):** "Target 99.99% availability for the homepage and p99 under 200 ms. If the feature store is down, rank with cached member features and stale-but-valid embeddings. If the ranker is down, serve the precomputed page, and if the cache is down too, serve regional popularity. Viewing history is read only by the ranking service through a scoped role, and unreleased titles are filtered by a catalog-visibility check before serving. The main cost driver is online ranking compute. I'd mitigate it by ranking only the top few hundred candidates and precomputing pages for inactive members."

### online_validation_monitoring (core): N
- T10: "For validation we would run experiments, A/B tests and analyze the results with statistical rigor, and monitor the key metrics so that we can iterate."

The candidate mentioned A/B tests and monitoring in general terms. They named no primary metric, no interleaving stage, no reason why offline and online metrics can disagree, no explore/exploit mechanism, and no model-quality or drift monitors with alert actions.

**Model Yes answer (L5):** "First, interleave the new ranker against production to quickly prune weak variants. Interleaving only gives a relative preference and does not measure retention, so survivors go to an A/B test with retention as the primary metric and qualified plays as the secondary. Offline NDCG can disagree with online results because of logging bias and feedback loops. To keep learning, a small epsilon-greedy or Thompson-sampling slot in some rows explores new titles. Monitors: score distribution, feature null rates and PSI-based drift, and calibration of the play head. A drift alert pages the on-call engineer and can roll back to the last good model."

### culture_signals (non-core): N
- T4: "the right numbers would be defined together with the stakeholders as the project evolves"
- T10: "I am confident that with a great team we can build something amazing."

This is read against the memo values judgment, candor and courage. When pressed to commit, the candidate deferred to stakeholders instead of stating an assumption. They defended no trade-off, named nothing that would change their mind, never said "I do not know" while proposing how to find out, and expressed no direct disagreement. The closing statement asserts confidence but shows no judgment.

**Model Yes answer (L5):** "I'll assume p99 of 200 ms. If product says the TV clients can tolerate 400 ms, I'd move to the heavier ranker. I don't know the current homepage traffic split by device, so I'd check the request logs before sizing. I'd push back on optimizing raw click-through, because it rewards clickbait artwork, and I'd argue for qualified plays instead."

## Hints

None.

## Uncovered signal points

None recorded. The session ended with a normal close.

## Strengths and gaps

**Strengths**
- Engaged with every prompt and was aware that the problem spans metrics, data, models, infrastructure and experimentation.
- Named the right component categories (batch and streaming, feature store, caching) and mentioned A/B testing and graceful degradation.

**Gaps**
- Made no commitments: no metric, numbers, label, loss, target or monitor, even when asked directly.
- Asked no clarifying questions and confirmed no scope.
- Lists of technologies with no reasons, trade-offs or data flow detail.
- Security, cost, explore/exploit and offline/online metric disagreement were missing.

## Study plan

1. **Problem framing with explicit numbers (core, SN).** Practise opening every design by separating the business goal from a proxy metric, stating scale, latency and freshness assumptions, and naming a guardrail and a constraint. Modules: [recsys-course/00_intro/](recsys-course/00_intro/), [recsys-course/18_capstone/](recsys-course/18_capstone/), [recsys-course/19_elite_playbook/](recsys-course/19_elite_playbook/). Then repeat the `ml-system-design` stage.
2. **Concrete modeling choices (core, N).** For a homepage ranker, write down two candidate models, the label, the loss, the exposure/position bias of the training data and the offline selection metric. Modules: [recsys-course/06_ctr_ranking/](recsys-course/06_ctr_ranking/), [recsys-course/07_learning_to_rank_multitask/](recsys-course/07_learning_to_rank_multitask/), [recsys-course/08_deep_retrieval_ann/](recsys-course/08_deep_retrieval_ann/), [recsys-course/09_sequential/](recsys-course/09_sequential/).
3. **Serving architecture, reliability and online validation (core, N).** Trace one request end to end with fallbacks, set latency and availability targets, and design an interleaving-then-A/B program with drift monitors. Modules: [recsys-course/16_production_serving/](recsys-course/16_production_serving/), [recsys-course/17_mlops_monitoring/](recsys-course/17_mlops_monitoring/), [recsys-course/15_online_experimentation/](recsys-course/15_online_experimentation/), [recsys-course/14_bandits_rl_ope/](recsys-course/14_bandits_rl_ope/).

Additional:
- Culture signals: practise stating assumptions and saying "I do not know, here is how I'd find out". Practice stage: `culture`; resource: Netflix culture memo, jobs.netflix.com/culture.
