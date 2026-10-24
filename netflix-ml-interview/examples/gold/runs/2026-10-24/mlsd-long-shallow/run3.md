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
    - {turn_id: 6, quote: "We would use a data lake, streaming, batch processing, a feature store, a model registry, a serving layer, caching, a CDN, load balancers and monitoring, all orchestrated with Kubernetes."}
    - {turn_id: 6, quote: "Data flows from the sources through the pipelines into the models and then to the application layer"}
  modeling_choices:
    - {turn_id: 8, quote: "We would use state of the art deep learning, like transformers, possibly with attention, embeddings and multi-task learning, and potentially large language models"}
    - {turn_id: 8, quote: "Training would use large amounts of high quality data and careful hyperparameter tuning, with regularization to avoid overfitting."}
  scale_reliability_security:
    - {turn_id: 10, quote: "For failures we would have redundancy, fault tolerance, graceful degradation and monitoring and alerting, following SRE best practices, so that the system is highly available."}
    - {turn_id: 6, quote: "Each component would be designed with best practices for reliability and security in mind"}
  online_validation_monitoring:
    - {turn_id: 10, quote: "For validation we would run experiments, A/B tests and analyze the results with statistical rigor, and monitor the key metrics so that we can iterate."}
  culture_signals:
    - {turn_id: 4, quote: "the right numbers would be defined together with the stakeholders as the project evolves"}
    - {turn_id: 10, quote: "I am confident that with a great team we can build something amazing"}
hints: []
---

# Scorecard: 01-ml-system-design@design

> Recommendation derived by the simulator's pedagogical rule; Netflix does not use a common scale.
> Recomendación derivada por la regla pedagógica del simulador; Netflix no usa una escala común.

## Summary

**Recommendation: fail. Observed level: none.**

The session closed normally (final interviewer meta `phase: closed`, no uncovered signal points recorded). The interviewer asked about every area: framing, metrics and numbers, architecture, model/loss/data, failures and online validation. In each one the candidate answered with lists of generic terms and never made a concrete design decision. The candidate asked no clarifying questions, although the opening turn invited them. When asked directly to commit to a metric and to scale and latency numbers, the candidate declined and left the numbers to be decided later with stakeholders. That contradicts the framing bar, so `problem_framing_requirements` is a Strong No. The other core competencies name relevant components or techniques but miss nearly every element of the L5 bar, and they also miss the L4 bar. The answers were long, but length is not evidence, and none of them gave a specific mechanism, number or trade-off. One core SN and four core Ns make the result `fail`.

## Scores and evidence

### problem_framing_requirements: SN (core)
- T2: "The goal is to maximize member satisfaction and engagement in a scalable, robust and flexible way"
- T4: "Scale would be large, as Netflix is a global service, and latency would need to be low to provide a great experience."
- T4: "the right numbers would be defined together with the stakeholders as the project evolves"

The candidate asked no clarifying questions. They separated no business goal from a proxy metric, made no numeric assumptions, named no specific guardrail or constraint and did not confirm scope. When the interviewer explicitly asked for numbers, the candidate refused to commit. This is designing without stating requirements, which the rubric's Strong No definition describes.

**Model Yes answer (L5):** "Business goal: long-term member retention. Proxy: qualified plays (for example, more than 2 minutes watched) from the homepage per session. Guardrails: homepage render latency and row diversity. Assumptions: about 250M members, about 100k homepage requests/s at peak, p99 under 200 ms for the row and title layout, viewing signals fresh within minutes. Constraint: viewing history is sensitive, and we must stay available when ML services fail. Scope: is the first version ranking only, or does it also generate rows? Is artwork personalization out of scope?"

### architecture_data_flow: N (core)
- T6: "We would use a data lake, streaming, batch processing, a feature store, a model registry, a serving layer, caching, a CDN, load balancers and monitoring, all orchestrated with Kubernetes."
- T6: "Data flows from the sources through the pipelines into the models and then to the application layer"

The candidate named components but did not say what each one reads or writes, did not separate batch from real-time paths, did not address offline/online feature consistency, gave no reason for any technology choice and did not trace a request. This is below L4 as well.

**Model Yes answer (L5):** "Batch path: nightly Spark jobs compute candidate pools and member embeddings and write them to a KV store. Real-time path: play and impression events go through Kafka into a streaming feature updater. The same feature definitions are logged at serving time and reused for training, so offline and online stay consistent. A request goes from device to homepage service, which fetches precomputed candidates from the KV store, calls the ranker for rows and titles, and assembles the page with device-specific row counts. If the ranker times out, we serve the cached last-known page for that member, or popularity rows."

### modeling_choices: N (core)
- T8: "We would use state of the art deep learning, like transformers, possibly with attention, embeddings and multi-task learning, and potentially large language models"
- T8: "Training would use large amounts of high quality data and careful hyperparameter tuning, with regularization to avoid overfitting."

The candidate listed many model families but compared none of them against constraints. They defined no loss or label, did not describe how the training data is generated or its exposure and position bias, and named no offline metric.

**Model Yes answer (L5):** "Two-tower retrieval for candidates, then a ranker. GBDT is a cheap, low-latency baseline; a sequence-aware transformer captures recent viewing better but costs more at serving time and is weaker for new titles without content features. Label: qualified play within the session; loss: multi-task cross-entropy on play and completion. The training data comes from logged impressions, so it carries exposure and position bias. We correct it with position as a training feature that is fixed at inference, plus a small randomized slice. Choose the model offline by NDCG@k on held-out sessions."

### scale_reliability_security: N (core)
- T10: "For failures we would have redundancy, fault tolerance, graceful degradation and monitoring and alerting, following SRE best practices, so that the system is highly available."
- T6: "Each component would be designed with best practices for reliability and security in mind"

Failure and security came up only as generic labels. The candidate set no availability or latency target, described no concrete degraded mode, did not address access control for viewing history or unreleased content, and named no cost driver. They gave no order-of-magnitude estimate, so this is below L4 as well.

**Model Yes answer (L5):** "Target: 99.99% homepage availability, ranker p99 at 100 ms. If the ranker fails, serve cached personalized pages. If the feature store fails, rank on stale batch features, and if that fails too, fall back to popularity rows per region. Viewing history is accessed through scoped service credentials, and unreleased titles are filtered by an entitlement check before ranking. Main cost driver: real-time ranker inference at peak. Mitigation: precompute pages for inactive members and rerank in real time only for active sessions."

### online_validation_monitoring: N (core)
- T10: "For validation we would run experiments, A/B tests and analyze the results with statistical rigor, and monitor the key metrics so that we can iterate."

The candidate mentioned A/B tests but gave no primary metric. There was no interleaving stage, no discussion of why offline and online metrics disagree, no explore/exploit mechanism and no specific model-quality or drift monitors with alert actions.

**Model Yes answer (L5):** "First, interleave the candidate ranker with production to prune variants quickly. Interleaving is relative and says nothing about retention, so the winners then go to an A/B test with retention as primary and streaming hours and latency as guardrails. Offline NDCG can disagree with online results because of logging bias and feedback loops. A small epsilon-greedy or Thompson-sampling slot per page provides exploration. Monitors: prediction-score distribution, feature null rates and drift (PSI), and play rate per row. Alerts page on-call and trigger a rollback to the previous model."

### culture_signals: N (non-core)
- T4: "the right numbers would be defined together with the stakeholders as the project evolves"
- T10: "I am confident that with a great team we can build something amazing"

When the interviewer pressed for a commitment, the candidate did not state an assumption or defend a trade-off. They deferred to stakeholders, never said "I do not know" and proposed a way to find out, and never named what would change their mind. That shows little judgment and candor. Expressing confidence in the team is not evidence of courage.

**Model Yes answer (L5):** "I do not know Netflix's exact peak traffic, so I will assume 100k requests/s and a 200 ms p99, and I will revisit if you tell me otherwise. I am choosing precomputed pages over full real-time ranking because of that latency budget. If session-level freshness turns out to drive most of the gain, I would change my mind."

## Hints

None.

## Uncovered signal points

None recorded. The session closed normally (`phase: closed`), and the interviewer probed every competency area. The gaps above are depth gaps in the answers, not topics left uncovered.

## Strengths and gaps

**Strengths**
- The candidate knows the vocabulary of a modern recommender stack (feature store, model registry, multi-task learning, A/B testing, graceful degradation).
- Responses kept a consistent member-centric framing.

**Gaps**
- The candidate never committed to numbers, metrics or scope, even when asked directly.
- They listed components and techniques instead of designing: no data flow per component, no request trace, no fallback path.
- No loss, label, training-data bias or offline metric.
- No concrete SLOs, degraded modes, access control or cost reasoning.
- Validation stopped at "A/B tests": no primary metric, interleaving, exploration or drift monitoring.
- Under pushback the candidate deferred instead of stating an assumption and defending it.

## Study plan

1. **Problem framing with explicit numbers (core, SN).** Practice opening every design with 3 to 5 clarifying questions, a goal and proxy split, a guardrail, and latency, freshness and scale assumptions written down as numbers. Modules: `recsys-course/00_intro/`, `recsys-course/18_capstone/`, `recsys-course/19_elite_playbook/`. Then practice the `ml-system-design` stage again.
2. **Architecture and serving data flow (core, N).** Learn to trace one homepage request end to end, with batch and real-time paths, feature consistency and a cache or fallback path. Modules: `recsys-course/16_production_serving/`, `recsys-course/08_deep_retrieval_ann/`. Pair this with `recsys-course/17_mlops_monitoring/` to cover degraded modes and cost drivers (scale_reliability_security).
3. **Modeling and online validation (core, N).** Define label, loss, training-data bias and the offline metric, then plan interleaving followed by an A/B test, with exploration and drift monitors. Modules: `recsys-course/06_ctr_ranking/`, `recsys-course/07_learning_to_rank_multitask/`, `recsys-course/15_online_experimentation/`, `recsys-course/14_bandits_rl_ope/`.

Also: for culture_signals, practice stating an assumption under uncertainty and defending it in the `culture` practice stage, using the Netflix culture memo (jobs.netflix.com/culture) on judgment, candor and courage.
