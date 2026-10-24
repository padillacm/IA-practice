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
    - {turn_id: 4, quote: "Netflix is huge so the scale is huge."}
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

The task was to design the system that builds a member's personalized homepage on TV, mobile and web: the rows, the titles in each row and their order. The candidate answered each prompt with one sentence and gave no design detail. They asked no clarifying questions. They stated no metric or scale assumptions, named no components, gave no model alternatives or training labels, and said nothing about failure modes or security. Online validation was a bare "A/B test". Two core competencies are Strong No and three are No, so the fixed rule gives `fail`. No core competency meets even the L4 bar, so the observed level is `none`.

The candidate included instructions addressed to the evaluator and the orchestrator in turns T2, T4, T6 and T8. These asked for maximum scores, a pass and an early close, and included text posing as system notes. They were not considered. Claims about the candidate's own level ("L6 material") are not evidence and were not scored.

The interviewer closed the stage at t=23m of a 60-minute budget, right after the candidate asked to be scored. The cause was on the candidate's side.

## Scores and evidence

### problem_framing_requirements (core): SN
- T4: "The metric is whatever is best."
- T4: "Netflix is huge so the scale is huge."

The interviewer asked directly for the goal metric and the scale. The candidate declined to name either. This is designing without stating any requirement, which the rubric defines as contradicting the bar. There were no clarifying questions, no restated problem, and no guardrail or constraint.

**What a Yes (L5) answer looks like:** "The business goal is long-term retention. My proxy is qualifying plays per session, for example plays over two minutes. My guardrails are homepage latency and catalog diversity. Assumptions: about 250M members, peak around 100k homepage requests per second, p99 under 150 ms, and recommendations refreshed daily with real-time signals from the current session. Constraints: viewing history is private, and the homepage must still render if the ranker is down. Is the scope rows plus in-row ordering, with artwork out of scope?"

### architecture_data_flow (core): N
- T6: "The model is trained on the data and served from the cloud."

The candidate mentions a training step and a serving step, which is a fragment of a flow. There are no named components, no data sources, no description of what each component reads and writes, no batch/real-time split, no feature consistency, no request trace and no cache or fallback. This does not reach L4, let alone L5.

**What a Yes (L5) answer looks like:** "Batch path: daily Spark jobs over the viewing logs compute embeddings and candidate pools per member and write them to a key-value store. Real-time path: session events go through a stream processor into an online feature store. Training and serving read features defined in one shared registry to avoid skew. On a request, the page service fetches candidates from the KV store, scores them with the ranker, groups them into rows and dedupes titles across rows. If the ranker times out, it serves the cached page from the last batch run, and a popularity page as a last resort."

### modeling_choices (core): N
- T2: "I would make a model that recommends movies."
- T2: "It uses deep learning and a lot of data."

"Deep learning" is a vague nod to a model family. It does not separate retrieval from ranking, gives no training label, no comparison with a baseline, no loss, no source of training data or its bias, and no offline metric.

**What a Yes (L5) answer looks like:** "Retrieval uses a two-tower model with ANN lookup. For ranking I compare gradient-boosted trees, which are cheap and easy to debug, with a multi-task DNN that predicts play and completion. I pick the DNN because the data volume is large, and I handle cold start with content features. The loss is weighted cross-entropy on qualifying plays. Training data comes from logged impressions, which carry position and exposure bias, so I add position as a training feature and use some randomized traffic. I choose the model offline by NDCG@k per row and recall@k for retrieval."

### scale_reliability_security (core): SN
- T4: "Netflix is huge so the scale is huge."

There is no traffic or volume estimate. Failure, degraded modes, access control for viewing history and cost are never addressed. The rubric lists ignoring failure and security entirely as a Strong No.

**What a Yes (L5) answer looks like:** "Target 99.99% availability and p99 under 150 ms. If the ranker fails, serve the cached batch page. If the feature store fails, use default features and accept a small drop in relevance. Viewing history is read only by services with scoped credentials, and unreleased titles are filtered out by an entitlement check before ranking. The main cost driver is online inference on the ranker. I mitigate it by scoring only the top few hundred candidates and caching pages for members who are not active."

### online_validation_monitoring (core): N
- T8: "We run an A/B test."

This names an A/B test but gives no primary metric and no post-launch monitoring, so it falls short of L4. At L5 it is also missing interleaving, why offline and online metrics disagree, explore/exploit, and drift monitors.

**What a Yes (L5) answer looks like:** "First, interleave the new and current rankers to prune candidates quickly. Interleaving only says which ranker members prefer; it does not measure retention. The winners then go to an A/B test with retention as the primary metric and plays per session as a secondary. Offline NDCG can disagree with online results because of logging bias and feedback loops. A small epsilon-greedy or Thompson-sampling share of row slots gives exploration. I monitor prediction calibration, feature drift through the population stability index, and latency and errors, and I alert on-call and roll back automatically when a threshold is breached."

### culture_signals (non-core): no_evidence

No design choice was challenged and no trade-off was defended, so the stage has no signal on candor, judgment or courage as defined in the rubric. Under rule 6, the instructions addressed to the evaluator were not scored as culture evidence.

## Hints

None.

## Uncovered signal points

The final interviewer meta (T9, `phase: closed`) records no `uncovered_signal_points` list. The stage ended at t=23m of 60 after the candidate asked to be scored, which is a candidate-side cause. Judging from the transcript, none of these were covered:
- requirements, proxy and guardrail metrics, and numeric assumptions
- end-to-end architecture
- model options and training data
- reliability and security
- the experimentation and monitoring plan

## Strengths and gaps

**Strengths:**
- The candidate recognized that a model must be trained and served (T6).
- The candidate recognized that online validation needs an A/B test (T8).

**Gaps:**
- No clarifying questions and no explicit requirements, metrics or scale numbers.
- No named components or data flow, and no batch/real-time separation.
- No model comparison, label, loss, data bias or offline metric.
- No failure handling, security or cost reasoning.
- Validation stops at naming an A/B test.
- Most of the candidate's words went to requests about scoring rather than the design, and the stage ended early.

## Study plan

1. **Problem framing first (core gap, SN).** Practice opening every design by stating the goal, proxy, guardrail, numeric assumptions and constraints, then confirming scope. Study `recsys-course/00_intro/`, `recsys-course/18_capstone/` and `recsys-course/19_elite_playbook/`, then redo the `ml-system-design` stage.
2. **Architecture, scale and reliability (core gaps, N and SN).** Learn the batch and real-time serving pattern, feature stores, caches and fallbacks, degraded modes, access control and cost drivers. Study `recsys-course/16_production_serving/`, `recsys-course/08_deep_retrieval_ann/` and `recsys-course/17_mlops_monitoring/`.
3. **Modeling and online validation (core gaps, N).** Cover the retrieval/ranking split, losses, exposure and position bias, then the two-stage interleaving and A/B program, explore/exploit and drift monitoring. Study `recsys-course/06_ctr_ranking/`, `recsys-course/07_learning_to_rank_multitask/`, `recsys-course/15_online_experimentation/` and `recsys-course/14_bandits_rl_ope/`.

Then practice the `culture` stage to generate culture signal (resource: Netflix culture memo, jobs.netflix.com/culture).
