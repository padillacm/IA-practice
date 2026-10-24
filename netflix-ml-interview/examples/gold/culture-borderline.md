---
instance_id: 10-culture@default
session_id: gold-culture-borderline
stage: culture
variant: default
phase: vo1
role: mle
level: L5
lang: en
domain: recsys
time_scale: 1.0
budget_minutes: 45
---

### T1 · interviewer · t=00m

Hi, I am Rachel Goldberg, a Director of Engineering. This is a conversation, not a quiz. Start with your favorite project, your latest and the one you consider most significant, and tell me what you look for next.

<meta>
question_id: culture-selfpromo-01
phase: intro
</meta>

### T2 · candidate · t=04m

My latest project was improving the search ranking at my company. We tried a new model and engagement improved a few percent. I decided to use a transformer and I trained it on the click logs. It was a good project for the team. Next I would like to work on a larger scale and with more modern techniques.

### T3 · interviewer · t=06m

What was the baseline and how did you measure the improvement?

<meta>
question_id: culture-selfpromo-01
phase: main
</meta>

### T4 · candidate · t=09m

The baseline was the previous model, a gradient boosted model. We measured with an A/B test over two weeks, and play-starts per member went up by about 1.5%, I do not remember the interval. I chose the transformer over trees because of the sequence data.

### T5 · interviewer · t=11m

Tell me about a high-stakes decision you made with incomplete data.

<meta>
question_id: culture-judgment-01
phase: main
culture_probe: {value: judgment}
</meta>

### T6 · candidate · t=16m

We had to decide whether to ship a model before a deadline with only one week of A/B data. The options were to ship or wait. I asked my manager and the data scientist. The week looked positive so I recommended shipping, and I told my director I took responsibility. It worked out, though we later found a small latency regression that we fixed. I learned to check latency earlier.

### T7 · interviewer · t=18m

Tell me about disagreeing with someone more senior.

<meta>
question_id: culture-candor-01
phase: main
culture_probe: {value: candor}
</meta>

### T8 · candidate · t=22m

I generally get along with everyone. When my manager has a different opinion I usually respect it, since they have more context. Sometimes I mention a concern but I do not like to push too much, I prefer to keep the team harmonious. I cannot think of a specific time right now.

### T9 · interviewer · t=24m

Think about a mistake you made and how you shared it with others.

<meta>
question_id: culture-candor-01
phase: main
culture_probe: {value: candor}
</meta>

### T10 · candidate · t=28m

I try not to make mistakes that affect others. If something goes wrong I fix it quickly. The team knows I am reliable.

### T11 · interviewer · t=30m

Do you have questions for me?

<meta>
question_id: culture-candidate-questions
phase: candidate_questions
</meta>

### T12 · candidate · t=33m

What are the benefits and the vacation policy? And how big is the team?

### T13 · interviewer · t=35m

Thank you, that is our time.

<meta>
question_id: culture-candidate-questions
phase: closed
</meta>
