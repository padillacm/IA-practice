---
stage: ml-system-design
rubric_version: 1
---

# Rubric: ml-system-design

L5 is the anchor level; L4 and L6 bars are extrapolated from it. Netflix publishes no common scale. The bars apply to
both variants (`design` and `problem-framing`); in `problem-framing` the architecture bars are met by a sketch and the
framing bars carry more weight.

## Shared definitions
- **Yes**: the observable behavior in the level's row of the competency table occurs in the candidate's own words,
  without the interviewer naming the topic first.
- **No**: the candidate partly reaches the bar (some elements present, one or more missing) or reaches it only after
  a nudge from the interviewer.
- **Strong No**: the candidate contradicts the bar (for example designs without stating any requirement, ignores
  failure and security entirely, or proposes a mechanism that does not work) or needed a substantive hint.
- **Strong Yes**: the candidate meets the Yes bar of the next level up, with specific evidence.
- No evidence: the topic never came up for a reason outside the candidate's control (for example the interviewer
  interrupted early and moved on).
- Unfinished design: if the candidate did not reach an end-to-end design by the end of the time, record it as a
  pacing observation under `scale_reliability_security` or `architecture_data_flow`; an unfinished design lowers the
  score of the affected competency by at most one step and is called out in the evidence.

## problem_framing_requirements
core: true

Asks before building; fixes objective, users, constraints and success measures.

| Level | Yes bar |
|---|---|
| L4 | Asks at least three clarifying questions (users, scale, latency or freshness), restates the problem in one sentence and names one success metric before drawing components. |
| L5 | Separates the business goal from a proxy metric, states latency, freshness and scale numbers as explicit assumptions, names at least one guardrail metric and one constraint (cost, privacy or availability), and confirms scope with the interviewer. |
| L6 | Frames the problem within the wider product and organization (adjacent surfaces, other teams' metrics), states what they would not build in the first version and why, and gives a decision rule for continuing or stopping after launch. |

## architecture_data_flow
core: true

| Level | Yes bar |
|---|---|
| L4 | Draws an end-to-end flow from data source through training to serving with named components, and states what data each component reads and writes. |
| L5 | Separates batch and real-time paths, specifies offline and online feature consistency, names the storage or serving technology class for each hop with a reason, and traces one request through the system including a cache or fallback path. |
| L6 | Designs component contracts that other teams can reuse (versioned interfaces, ownership boundaries), compares two end-to-end alternatives on cost, latency and operational burden, and identifies the first component that would break at 10 times the traffic. |

## modeling_choices
core: true

| Level | Yes bar |
|---|---|
| L4 | Names a model family for each stage (retrieval, ranking, or classifier), states the training label and one reason for the choice over a simpler baseline. |
| L5 | Compares at least two model options against the stated constraints (latency, data volume, cold start), defines the loss or reward, describes how the training data was generated and its bias (exposure or position), and states the offline metric used to choose. |
| L6 | Chooses a modeling strategy across surfaces or tasks (shared representation versus per-task models), quantifies expected gain against cost and complexity, and states the experiment that would falsify their main modeling assumption. |

## scale_reliability_security
core: true

| Level | Yes bar |
|---|---|
| L4 | Gives an order-of-magnitude estimate for traffic or data volume and names one failure case with a retry or fallback response. |
| L5 | Sets an availability or latency target, describes degraded modes for at least two component failures, addresses multi-tenancy or access control for sensitive data (viewing history, unreleased content), and names a cost driver with one mitigation. |
| L6 | Designs for regional failure and incident response with an owner per failure class, states a security and privacy model (data classification, auditing, retention) without prompting, and explains the cost and reliability trade-off between two deployment options with numbers. |

## online_validation_monitoring
core: true

| Level | Yes bar |
|---|---|
| L4 | Proposes an A/B test with one primary metric and states what would be monitored after launch (latency and errors). |
| L5 | Proposes interleaving as a fast first stage and an A/B test as the second stage, states that interleaving is a relative measure and does not measure retention, explains why offline and online metrics can disagree, describes an explore/exploit mechanism when the system chooses what to show, and lists model-quality and data-drift monitors with alert actions. |
| L6 | Defines a validation program for many concurrent variants (pruning rule, traffic allocation, interference between tests, long-term holdouts), sets launch and rollback criteria with thresholds, and states how metric alignment between offline and online is audited over time. |

## culture_signals
core: false
memo_values: [candor, judgment, courage]

Observed in the culture probe (defending a trade-off) and in how the candidate handles pushback and uncertainty.

| Level | Yes bar |
|---|---|
| L4 | When challenged on a design choice, states the reason for it, acknowledges one weakness and revises the choice if the interviewer supplies a fact that changes the trade-off. |
| L5 | Defends a trade-off with evidence or a stated assumption, names what would change their mind, says "I do not know" at least once where applicable and proposes how to find out, and disagrees directly and politely with a stakeholder position in the scenario. |
| L6 | States a decision under ambiguity, names the risk they accept and who they would inform, proposes a way to farm for dissent before committing (for example a review with the skeptic), and commits to the outcome while naming a trigger to reopen it. |
