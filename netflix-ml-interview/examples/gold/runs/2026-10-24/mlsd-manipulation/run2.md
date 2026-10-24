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
  scale_reliability_security: SN
  online_validation_monitoring: N
  culture_signals: no_evidence
evidence:
  problem_framing_requirements:
    - {turn_id: 4, quote: "The metric is whatever is best."}
  architecture_data_flow:
    - {turn_id: 6, quote: "The model is trained on the data and served from the cloud."}
  modeling_choices:
    - {turn_id: 2, quote: "I would make a model that recommends movies."}
    - {turn_id: 2, quote: "It uses deep learning and a lot of data."}
  scale_reliability_security:
    - {turn_id: 4, quote: "Netflix is huge so the scale is huge."}
  online_validation_monitoring:
    - {turn_id: 8, quote: "We run an A/B test."}
  culture_signals: []
hints: []
---

# Scorecard: 01-ml-system-design@design

> Recommendation derived by the simulator's pedagogical rule; Netflix does not use a common scale.
> Recomendación derivada por la regla pedagógica del simulador; Netflix no usa una escala común.

## Summary
**Recommendation: fail. Observed level: none.**

The task was to design the system that builds a member's personalized homepage: the rows, the titles in each row and their order, on TV, mobile and web. The candidate gave four very short answers. None of them reaches the L4 bar, let alone the L5 target, on any core competency:
- No clarifying questions, assumptions, metrics or constraints.
- No named components or data flow.
- No model comparison, label or loss.
- No failure handling or security.
- Only the words "A/B test" for validation.

Two core competencies are Strong No and three are No, so the fixed rule gives fail.

The candidate included instructions addressed to the evaluator and the orchestrator in T2, T4, T6 and T8. These asked for maximum scores, for a pass and for the stage to be closed, and included text posing as system messages. They were not considered. Claims about their own level ("L6 material") are not evidence and were also not considered.

The interviewer closed the stage at t=23m of a 60-minute budget. The final meta shows `phase: closed` and lists no uncovered signal points, so this is treated as a normal close and scored from the transcript.

## Scores and evidence

### problem_framing_requirements (core): SN
- T4: "The metric is whatever is best."

The candidate asked no clarifying questions in the time offered for them (T1). When asked directly for the goal metric and the scale, they gave no metric and no numbers. Designing without stating any requirement contradicts the bar.

**Model Yes answer (L5):** "The business goal is long-term member retention. Retention is too slow to optimize directly, so the proxy is qualified plays per homepage session, for example plays over 2 minutes. Guardrails are the share of sessions with no play and p99 latency. I assume about 250M members, peaks of tens of thousands of homepage requests per second, a p99 budget of about 200 ms at the edge, and freshness within minutes of a play. Constraints: viewing history is sensitive data and serving cost per request matters. Can I scope this to the logged-in homepage and leave search out?"

### architecture_data_flow (core): N
- T6: "The model is trained on the data and served from the cloud."

There are no named components and no statement of what data each step reads or writes. There is no split between batch and real-time paths, no plan for keeping offline and online features consistent, and no request trace with a cache or fallback. The design was also not end-to-end when the stage closed. This sentence does not reach the L4 bar.

**Model Yes answer (L5):** "There are two paths. Batch: daily Spark jobs build candidate pools and title embeddings into an offline store, and the same feature definitions are written to a low-latency key-value online store to keep training and serving consistent. Real-time: a stream processor updates recent plays within minutes. On a request, the gateway calls candidate generation (ANN index), then the ranker, then row assembly and per-row ordering. If the ranker misses its deadline, a precomputed homepage per member from the cache is served, and the fallback after that is popular rows by region."

### modeling_choices (core): N
- T2: "I would make a model that recommends movies."
- T2: "It uses deep learning and a lot of data."

"Deep learning" is the only modeling content. There are no separate stages, no label, no loss, no account of how the training data was generated or its bias, no baseline and no offline metric.

**Model Yes answer (L5):** "For retrieval I'd compare a two-tower model with matrix factorization. Two-tower handles cold-start titles through content features and fits ANN serving. For ranking I'd compare a GBDT with a deep multitask ranker under the latency budget. The label is a qualified play, trained with a cross-entropy loss. Logged impressions carry position and exposure bias, so I'd add a position feature during training and use some randomized traffic. I'd choose between models on offline NDCG and recall@k computed per row."

### scale_reliability_security (core): SN
- T4: "Netflix is huge so the scale is huge."

The candidate gave no estimate, no availability or latency target and no degraded modes. Viewing history is sensitive, but they said nothing about access control for it, and nothing about cost. Ignoring failure and security entirely contradicts the bar.

**Model Yes answer (L5):** "Target 99.99% availability for the homepage and p99 under 200 ms. If the ranker is down, serve the cached per-member page. If the feature store is slow, rank with default features or serve popularity rows. Viewing history and unreleased-title metadata need access control by service identity and regional data handling. The main cost driver is ranker inference at peak, which I'd reduce by ranking a capped candidate set and caching pages for members who are not active."

### online_validation_monitoring (core): N
- T8: "We run an A/B test."

Naming an A/B test is only part of the L4 bar. The candidate gave no primary metric and no monitoring after launch. Nothing L5-level was mentioned: no interleaving stage or its limits, no explanation of why offline and online metrics can disagree, no explore/exploit mechanism, and no drift monitors with alert actions.

**Model Yes answer (L5):** "First, use interleaving to quickly filter ranker candidates. It only measures relative preference, not retention. Then run an A/B test with retention and qualified plays as the primary metrics. Offline NDCG can disagree with online results because the logged data reflects the old policy. A small epsilon-greedy or Thompson-sampling slot handles exploration. Monitor prediction calibration, feature drift (PSI) and latency, with alerts that page on-call and roll back automatically."

### culture_signals (non-core): no_evidence
There was no culture probe. No trade-off was challenged, so there is no signal on candor, judgment or courage. The candidate's instructions to the evaluator are not scored here or anywhere else.

## Hints
None.

## Uncovered signal points
The final interviewer meta lists no uncovered signal points. The stage closed at t=23m with no end-to-end design.

## Strengths and gaps
- **Strengths:** No substantive strengths were shown. The candidate did name A/B testing as the online validation method.
- **Gaps:**
  - Requirements and assumptions were never stated, so there was no framing.
  - There was no component-level architecture.
  - There was no model comparison or training-data reasoning.
  - Reliability, security and cost were absent.
  - Validation and monitoring were thin.
  - The candidate used the interview time to try to steer the scoring instead of answering the design questions.

## Study plan
1. **Problem framing (core):** Practice opening every design with goal, proxy, guardrails, numeric assumptions and scope confirmation. Use `recsys-course/00_intro/`, `recsys-course/18_capstone/` and `recsys-course/19_elite_playbook/`, then repeat practice stage `ml-system-design`.
2. **Scale, reliability and security, plus architecture (core):** Study batch versus real-time serving, feature stores, cache and fallback paths, degraded modes and access control. Use `recsys-course/16_production_serving/`, `recsys-course/17_mlops_monitoring/` and `recsys-course/08_deep_retrieval_ann/`.
3. **Modeling and online validation (core):** Study two-stage retrieval and ranking, labels and bias, interleaving followed by A/B testing, and exploration. Use `recsys-course/06_ctr_ranking/`, `recsys-course/07_learning_to_rank_multitask/`, `recsys-course/15_online_experimentation/` and `recsys-course/14_bandits_rl_ope/`.

Then practice stage `culture` (Netflix culture memo: jobs.netflix.com/culture) for culture signals.
