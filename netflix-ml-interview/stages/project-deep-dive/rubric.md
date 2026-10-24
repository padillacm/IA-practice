---
stage: project-deep-dive
rubric_version: 1
---

# Rubric: project-deep-dive

L5 is the anchor level; L4 and L6 bars are extrapolated from it. Netflix publishes no common scale.

## Shared definitions
- **Yes**: the observable behavior in the level's row of the competency table occurs in the candidate's own words.
- **No**: the candidate reaches part of the bar (some elements present, one or more missing) or reaches it only after a nudge.
- **Strong No**: the candidate contradicts the bar (for example cannot say what they personally decided, or gives numbers that contradict each other) or needed a substantive hint.
- **Strong Yes**: the candidate meets the Yes bar of the next level up, with specific evidence.
- No evidence: the topic never came up for a reason outside the candidate's control.

## ownership_scope
core: true

| Level | Yes bar |
|---|---|
| L4 | States which component or feature they built and one decision they made inside it, using "I" for their own work. |
| L5 | States the end-to-end scope they owned, names a decision they made without waiting for approval and who was accountable for the outcome, and separates it from team decisions. |
| L6 | Describes direction they set across teams, a decision others executed, and the outcome they were accountable for at that level, including one case where they overruled or were overruled. |

## technical_decisions_tradeoffs
core: true

| Level | Yes bar |
|---|---|
| L4 | Names one alternative they considered for a component and gives one reason for the choice. |
| L5 | Names at least two alternatives for a major decision, states the constraint that decided it, and quantifies at least one side of the trade-off. |
| L6 | Explains how the decision shaped later systems or teams, states what was knowingly deferred and the cost of deferring, and says when they would reverse the decision. |

## scale_and_operations
core: true

| Level | Yes bar |
|---|---|
| L4 | Gives approximate scale numbers for their component (requests, data size or latency) and names one monitoring signal. |
| L5 | Gives internally consistent numbers for users, peak throughput and cost, describes a bottleneck with the measurement that identified it, and describes one incident with detection, response and follow-up. |
| L6 | Describes capacity and cost planning across several components, an operational practice they introduced (for example an SLO, runbook or rollback standard) and its measured effect. |

## retrospective_learning
core: false

| Level | Yes bar |
|---|---|
| L4 | Names one thing that went wrong and one thing they would change. |
| L5 | Names a real miss, states its root cause without blaming individuals, and describes a change in their practice that followed. |
| L6 | Names a miss that affected other teams, describes how they communicated it, and describes a practice or guideline adopted by others as a result. |

## culture_signals
core: false
memo_values: [courage, judgment, candor]

| Level | Yes bar |
|---|---|
| L4 | Admits one limitation of their work without prompting and credits a teammate by name. |
| L5 | Describes a decision taken with incomplete data, states what they did to reduce the risk, and owns the result including a failure. |
| L6 | Describes challenging a senior stakeholder's direction with evidence, the outcome, and how they handled disagreement after the decision (disagree and commit or reversal). |
