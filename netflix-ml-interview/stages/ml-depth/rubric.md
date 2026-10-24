---
stage: ml-depth
rubric_version: 1
---

# Rubric: ml-depth

L5 is the anchor level; L4 and L6 bars are extrapolated from it. Netflix publishes no common scale. The rubric applies
to every domain (recsys, experimentation, causal-inference, rl-bandits, cv, nlp-llm, ads, ml-platform); judge depth
against the domain of the session.

## Shared definitions
- **Yes**: the observable behavior in the level's row of the competency table occurs in the candidate's own words,
  without the interviewer supplying the key idea.
- **No**: the candidate partly reaches the bar (some elements present, one or more missing) or reaches it only after
  a nudge.
- **Strong No**: the candidate contradicts the bar (for example states a mechanism that is wrong and defends it,
  stays at slogans after three consecutive follow-ups, or claims work they cannot explain) or needed a substantive
  hint.
- **Strong Yes**: the candidate meets the Yes bar of the next level up, with specific evidence (a derivation, a
  failure they hit, a number they estimated).
- No evidence: the topic never came up for a reason outside the candidate's control.
- Publications are discussion context. Never score a candidate for recalling or missing a figure from a Netflix paper
  or post.

## domain_depth
core: true

| Level | Yes bar |
|---|---|
| L4 | Explains the standard method for the question, its assumptions and one failure mode in correct terms, and answers the first follow-up with a mechanism rather than a name. |
| L5 | Chooses among two or more methods and states the deciding condition for each, answers three consecutive follow-ups on one chain with mechanisms, and cites a limitation of the method that comes from practice or from the literature. |
| L6 | Places the method within the current state of the domain, contrasts it with at least two alternatives on cost, data and risk, identifies an open problem in the area and states how they would investigate it. |

## first_principles_reasoning
core: true

| Level | Yes bar |
|---|---|
| L4 | When the standard recipe does not fit, restates the objective and the data available, and proposes one derived step instead of guessing. |
| L5 | Derives or sketches the result from the objective and the data-generating process (for example variance of an estimator, regret of a policy, memory of a cache), states the assumptions, and checks the result against a limiting case. |
| L6 | Reframes a question whose premise is flawed, derives the trade-off from first principles with a back-of-envelope estimate, and says what measurement would confirm or refute it. |

## connection_to_practice
core: false

| Level | Yes bar |
|---|---|
| L4 | Names one production concern for the method (latency, data freshness, label delay) and one check for it. |
| L5 | Describes how an offline result becomes an online decision (interleaving then A/B, off-policy estimate then ramp), names the guardrail metrics, and gives a rollback trigger. |
| L6 | Defines the validation path and guardrails that several teams would reuse, names the biggest risk in the path (feedback loop, proxy drift, interference) and how it is monitored. |

## architecture_depth
core: false

| Level | Yes bar |
|---|---|
| L4 | Draws the main components of the system they would build (data, training, serving) and states what each passes to the next. |
| L5 | Draws the end-to-end system with interfaces, latency and cost for each stage, and answers one "what if scale grows 10x" question with the component that breaks first. |
| L6 | Defends the architecture across data, training, serving, evaluation and monitoring, states which interface they would let other teams own and the migration path, and explains how disagreements between consuming teams are resolved. |

## culture_signals
core: false
memo_values: [candor, curiosity, courage]

| Level | Yes bar |
|---|---|
| L4 | Says plainly what they have not done or do not know, and asks one question about how the interviewer's team handles the problem. |
| L5 | Disagrees with the interviewer's framing at least once with a reason, separates what they built from what they read, and describes an approach they dropped after evidence against it. |
| L6 | Gives candid, specific criticism of a widely used practice in the domain with an alternative, names a decision where they accepted a risk or opposed a senior view, and states what they learned. |
