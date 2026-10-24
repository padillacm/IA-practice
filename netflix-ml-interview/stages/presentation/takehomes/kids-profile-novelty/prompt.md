---
id: kids-profile-novelty
title: Metric design and readout for a kids-profile feature with a novelty effect
requires: []
---

# Take-home: Metric design for a new kids-profile feature

## Context
A new feature gives households a richer kids profile experience (curated rows, parental controls, a bedtime
mode). It ran for 28 days as a randomized experiment (feature vs holdout, 50/50 at household level). Early dashboards
show a large engagement lift in week 1. Product wants to announce success. You are asked to design the success
metrics and tell the team what the data actually supports.

## Data (generate with `python3 generate_data.py <dir>`)
- `households.csv`: household_id, region, n_kids_profiles_prior, arm (feature / holdout).
- `daily_activity.csv`: household_id, day (1-28), hours_total, hours_kids_content, active.
- `survey.csv`: household_id, parent_satisfaction_1to5 (only a self-selected subset responded).

## Your task
1. Propose a metric framework: one primary metric, supporting metrics, guardrails, and a time horizon. Say what each
   metric is a proxy for.
2. Analyze the daily data. Separate a transient effect from a durable one and estimate the long-run level you would
   expect, with uncertainty.
3. Explain how you would treat the survey (who responded, what bias that creates).
4. Say whether the week-1 lift justifies the announcement, and what experiment or analysis would settle it.
5. Recommend a decision.

## Deliverable
A short deck or notes (5-8 slides or about 2 pages) that you present in 20 minutes.

## Time budget
60 minutes in the simulation: about 5 minutes setup, 20 minutes presenting, about 30 minutes of panel questions,
5 minutes close.

## What the panel probes
- Why the chosen horizon and aggregation (per household, per day, cumulative) fit the question.
- How the novelty effect was identified, for example effect by day since exposure, and what model of decay you assumed.
- Whether kids-content hours are the right outcome or a shortcut for household value.
- Selection bias in the survey and what you would do instead.
- Practical limits: a longer holdout, cost of delaying the decision, and a plan if results disagree between metrics.
