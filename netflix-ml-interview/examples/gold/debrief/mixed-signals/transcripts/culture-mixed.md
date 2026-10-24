---
instance_id: 10-culture@default
session_id: gold-culture-mixed
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

Hi, I am Rachel Goldberg, a Director of Engineering. Start with your favorite project, your latest and the one you consider most significant, and tell me what you look for next.

<meta>
question_id: culture-selfpromo-01
phase: intro
</meta>

### T2 · candidate · t=04m

I led the launch of a title similarity service. It improved click-through on the more-like-this row by 3.4% over four weeks against the previous metadata cosine baseline, measured in an A/B test with 5% of members. I chose the embedding model and wrote the rollout plan. Next I want to own ranking quality for a whole surface.

### T3 · interviewer · t=06m

Tell me about a high-stakes decision you made with incomplete data.

<meta>
question_id: culture-judgment-01
phase: main
culture_probe: {value: judgment}
</meta>

### T4 · candidate · t=11m

We had two weeks of data on a new feature that moved clicks but not plays. I had to decide whether to ship. The options were ship, extend the test, or ship to half the regions. I asked the data scientist and the product lead, set the rule that plays had to be non-negative with 95% confidence, and extended the test one week. I was accountable to my director for the delay. I learned to pre-register the decision rule.

### T5 · interviewer · t=13m

Tell me about disagreeing with a more senior person.

<meta>
question_id: culture-candor-01
phase: main
culture_probe: {value: candor}
</meta>

### T6 · candidate · t=18m

My director wanted to reuse the old embeddings for speed. I disagreed and showed an offline gap of 4% recall at 100, and he decided to proceed anyway for one release, so I committed and built the fallback. I also once reported a wrong dashboard number to the team within an hour of noticing it.

### T7 · interviewer · t=20m

Tell me about a time you gave something up for another team, and whether anything in the memo gives you pause.

<meta>
question_id: culture-selflessness-01
phase: main
culture_probe: {value: selflessness}
</meta>

### T8 · candidate · t=25m

Honestly the team did the easy parts and I did the hard parts, and I was promoted because of the launch. I do not really have any reservations about the memo, I think it is all good and I would fit right in.

### T9 · interviewer · t=27m

What questions do you have for me?

<meta>
question_id: culture-candidate-questions
phase: candidate_questions
</meta>

### T10 · candidate · t=30m

What does success look like at this level in the first year? And how do you handle a disagreement with someone on your team when both of you are convinced?

### T11 · interviewer · t=32m

Thank you, that is our time.

<meta>
question_id: culture-candidate-questions
phase: closed
</meta>
