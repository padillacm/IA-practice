---
id: continue-watching-row
title: Experiment readout for a new "continue watching" row
requires: []
---

# Take-home: "Continue watching" row experiment readout

## Context
A product team added a new row to the home page that surfaces titles a member started but did not finish. It was
launched as a randomized experiment (50/50) across members. The team asks you for a readout and a recommendation:
ship, iterate, or stop, and for whom.

## Data (generate with `python3 generate_data.py <dir>`)
- `users.csv`: user_id, device (tv / mobile / web), plan, tenure_months, `pre_hours` (viewing hours in the 2 weeks
  BEFORE the experiment).
- `assignment.csv`: user_id, variant (control / treatment).
- `outcomes.csv`: user_id, `post_hours` (hours in the 2 weeks after launch), post_sessions, saw_row, clicked_row,
  post_searches, retained_28d.

## Your task
1. Check that the experiment is trustworthy (assignment balance, sample ratio, pre-period balance).
2. Define a primary metric and guardrails, and justify them.
3. Estimate the effect on the primary metric with an interval. Explain how you used the pre-experiment data.
4. Look for heterogeneity (at least device) and say how much you trust each subgroup finding.
5. Recommend a decision and name what you would do next (follow-up test, longer horizon, rollout plan).

## Deliverable
A short deck or notes (5-8 slides or about 2 pages) that you present in 20 minutes, leaving the rest for questions.

## Time budget
60 minutes in the simulation: about 5 minutes setup, 20 minutes presenting, about 30 minutes of panel questions,
5 minutes close. In the simulation you may run Python for the analysis before you present.

## What the panel probes
- Validity checks and what you would do if the checks failed.
- Why the primary metric is right, and what it does not capture (retention, search guardrail, quality of viewing).
- Variance reduction: what you adjusted for, why it is unbiased, how much narrower the interval became.
- Multiple comparisons across device slices and whether the heterogeneity is believable.
- Intent-to-treat versus the members who actually saw or clicked the row.
- How you would explain the decision to a product manager in two sentences.
