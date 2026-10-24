---
stage: ml-fundamentals
rubric_version: 1
---

# Rubric: ml-fundamentals

L5 is the anchor level; L4 and L6 bars are extrapolated from it. Netflix publishes no common scale. Applies to both
variants (`breadth`, `modeling-case`); in `modeling-case`, read "question" as "phase of the case".

## Shared definitions
- **Yes**: the observable behavior in the level's row of the competency table occurs in the candidate's own words,
  without the interviewer supplying the key idea.
- **No**: the candidate partly reaches the bar (some elements present, one or more missing) or reaches it only after
  a nudge.
- **Strong No**: the candidate contradicts the bar (for example states a wrong definition and defends it, picks a
  metric that cannot answer the question, or bluffs a figure) or needed a substantive hint.
- **Strong Yes**: the candidate meets the Yes bar of the next level up, with specific evidence (a worked example,
  a counterexample, a number computed correctly).
- No evidence: the topic never came up for a reason outside the candidate's control.
- Publications are discussion context. Never score a candidate for recalling or missing a figure from a Netflix paper
  or post.

## ml_theory
core: true

| Level | Yes bar |
|---|---|
| L4 | States the definition correctly (for example the bias-variance decomposition, L1 versus L2, how Q, K and V are computed), gives the standard consequence and one standard remedy, and corrects a slip when the interviewer repeats the question. |
| L5 | Explains why the result holds (a prior, a geometric picture, a derivation or a shape calculation), names one assumption it relies on and one case where it fails, and answers an edge-case follow-up without a nudge. |
| L6 | Derives or sketches the result from first principles, identifies a flaw or hidden assumption in the question itself, and relates the idea to a cost at system level (memory, latency, maintenance) with an estimate. |

## metrics_evaluation
core: true

| Level | Yes bar |
|---|---|
| L4 | Computes P@K, R@K or a simple NDCG by hand on a small example, and states which metric suits the stated task. |
| L5 | Selects a metric from the product question, states the failure mode of that metric, adds one complementary metric (coverage, diversity, calibration or a long-term outcome) and says how to check it offline and online. |
| L6 | Defines a metric set across offline, interleaving and A/B stages, states which decision each metric supports and its blind spots, and proposes how teams keep the definitions comparable without gaming. |

## practical_modeling_judgment
core: true

| Level | Yes bar |
|---|---|
| L4 | Proposes a baseline and the first diagnostic check for the stated symptom, and splits the data by time or user rather than at random. |
| L5 | Orders next steps by cost and information gained, names leakage, selection and feedback-loop risks unprompted, and states what monitoring would show a failure after deployment and what would trigger a rollback. |
| L6 | Compares two or more system-level options with their trade-offs (build versus share, one model versus several, learned versus hand-made features), states what evidence would change the choice, and names the maintenance owner. |

## communication_precision
core: false

| Level | Yes bar |
|---|---|
| L4 | Answers the question asked in order, separates training from test and offline from online when relevant, and says "I do not know" when stuck. |
| L5 | Gives the answer in the first two sentences, then justifies it; uses units, shapes or numbers; and restates an interviewer correction in their own words. |
| L6 | Adapts the explanation to a stated audience (for example a partner team), flags what is established versus assumed, and compresses a long topic into three claims that survive a challenge. |

## culture_signals
core: false
memo_values: [candor, curiosity, judgment]

| Level | Yes bar |
|---|---|
| L4 | Admits a knowledge gap plainly, asks one clarifying question about the problem, and accepts a correction without defending the error. |
| L5 | Disagrees with the interviewer's premise at least once with a reason, changes position when given evidence, and shows interest by asking how a technique behaves in a setting they have not seen. |
| L6 | Challenges an assumption that affects several teams, gives candid feedback on a common practice with an alternative, and states a decision they would make with incomplete information and the risk accepted. |
