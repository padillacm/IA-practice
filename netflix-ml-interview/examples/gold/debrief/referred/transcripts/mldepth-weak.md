---
instance_id: 11-ml-depth@default
session_id: gold-mldepth-weak
stage: ml-depth
variant: default
phase: vo2
role: mle
level: L5
lang: en
domain: recsys
time_scale: 1.0
budget_minutes: 45
---

### T1 · interviewer · t=00m

Hi, I am Kavya Raman, a Senior Research Scientist. Imagine a contextual bandit that picks the artwork for a title. How would you evaluate a new policy offline from logged data?

<meta>
question_id: mldepth-ope-01
phase: intro
</meta>

### T2 · candidate · t=04m

I would use importance sampling: weight each logged reward by the new policy probability divided by the logging probability. I think it is unbiased. There is also a doubly robust estimator.

### T3 · interviewer · t=06m

Why is it unbiased, and what goes wrong with its variance?

<meta>
question_id: mldepth-ope-01
phase: main
</meta>

### T4 · candidate · t=10m

It is unbiased when the logging probabilities are known. The variance could be high, I believe, when the weights are large. I do not remember how to derive it.

### T5 · interviewer · t=12m

How does an offline estimate become an online decision?

<meta>
question_id: mldepth-ope-01
phase: main
</meta>

### T6 · candidate · t=16m

After the offline estimate looks good we run an A/B test with a ramp, watching play-starts and a latency guardrail, and we roll back if the guardrail is breached for an hour.

### T7 · interviewer · t=18m

Thank you, that is our time.

<meta>
question_id: mldepth-ope-01
phase: closed
</meta>
