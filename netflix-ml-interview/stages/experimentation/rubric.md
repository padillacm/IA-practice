---
stage: experimentation
rubric_version: 1
---

# Rubric: experimentation

L5 is the anchor level; L4 and L6 bars are extrapolated from it. Netflix publishes no common scale. The bars apply
to both variants (`design-case` and `analysis-case`): in a design case the evidence comes from the candidate's own
design; in an analysis case it comes from the critique and analysis of the numbers given.

## Shared definitions
- **Yes**: the observable behavior in the level's row of the competency table occurs in the candidate's own words,
  without the interviewer naming the technique first.
- **No**: the candidate partly reaches the bar (some elements present, one or more missing) or reaches it only after
  a nudge from the interviewer.
- **Strong No**: the candidate contradicts the bar (for example randomizes on impressions where members are the
  unit, claims significance after repeated unadjusted looks, or computes a sample size that is off by an order of
  magnitude) or needed a substantive hint.
- **Strong Yes**: the candidate meets the Yes bar of the next level up, with specific evidence.
- No evidence: the topic never came up for a reason outside the candidate's control.
- Arithmetic: a sample-size or variance calculation counts only when the candidate performs it with the stated inputs;
  small slips corrected without help do not lower the score.

## experiment_design
core: true

| Level | Yes bar |
|---|---|
| L4 | States a hypothesis and decision, names the randomization unit (member) with one reason, and defines a control and a treatment arm. |
| L5 | Justifies the randomization unit against independence and exposure (device, account, cluster or market), defines triggering and exposure, handles concurrent tests, and names two validity checks (sample ratio mismatch and balance). |
| L6 | Chooses between an A/B test, interleaving then A/B, a geo or switchback design and a quasi-experiment with explicit reasons, designs the sequence of tests as a program, and states what claim each stage can and cannot support. |

## metrics_and_power
core: true

| Level | Yes bar |
|---|---|
| L4 | Names a primary metric tied to the decision and one guardrail, and writes the sample size formula with alpha, power, variance and minimum detectable effect. |
| L5 | Computes the sample size with the given inputs aloud, adjusts for correlation within members or heavy tails, sets the duration to include full weekly cycles, defines a non-inferiority guardrail, and distinguishes short-term proxies from the long-term outcome. |
| L6 | Justifies the minimum detectable effect by business value and cost of error, validates surrogate metrics against the long-term outcome, and sets a decision rule for combinations of primary and guardrail results. |

## analysis_inference
core: true

| Level | Yes bar |
|---|---|
| L4 | Computes or describes a confidence interval and p-value correctly for the primary metric and states the conclusion with the uncertainty. |
| L5 | Chooses the analysis unit and resampling unit correctly, uses a bootstrap or delta method where the metric is a ratio or quantile, corrects for multiple comparisons (FDR or family-wise) and peeking, examines heterogeneity with a validation step, and identifies interference or confounding when present. |
| L6 | Diagnoses an inference failure from the data given (distribution shape, contamination, selection), selects an identification strategy (quantile effects, cluster design, difference-in-differences or synthetic control) with assumptions and a placebo or sensitivity check, and states which claims the evidence supports. |

## variance_reduction_advanced
core: false

| Level | Yes bar |
|---|---|
| L4 | Describes variance reduction in one sentence and names one technique (stratification or a pre-period covariate). |
| L5 | Explains CUPED with the theta formula, states the variance factor 1 - rho^2, requires a pre-treatment covariate, handles members with no history, and validates with an A/A test. |
| L6 | Designs a standardized variance-reduction approach for a platform (shared covariates, regression adjustment or post-stratification choices, regular validation), compares it with a longer run on cost, and states bias risks. |

## decision_communication
core: false

| Level | Yes bar |
|---|---|
| L4 | States a ship or no-ship recommendation with the main number and its interval in plain language. |
| L5 | Gives a recommendation conditional on named risks, states what they would and would not claim, proposes the next experiment, and adapts the explanation for a non-technical stakeholder. |
| L6 | Frames the decision in terms of cost of a wrong call and reversibility, proposes a rollout with a rollback trigger, and describes how to set expectations with stakeholders before results arrive. |

## culture_signals
core: false
memo_values: [candor, judgment, courage]

Observed in the culture probe, where a stakeholder wants to ship on an unreliable result.

| Level | Yes bar |
|---|---|
| L4 | States plainly what the evidence does not show and offers a different way forward without being asked twice. |
| L5 | Disagrees directly with the stakeholder position, supports it with a number from the case, names what would change their mind, and admits one uncertainty in their own analysis. |
| L6 | States a decision under pressure, names the risk accepted and who to inform, seeks dissent from the person who disagrees before committing, and commits while naming a trigger to reopen the decision. |
