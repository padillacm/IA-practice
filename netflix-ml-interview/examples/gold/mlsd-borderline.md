---
instance_id: 08-ml-system-design@design
session_id: gold-mlsd-borderline
stage: ml-system-design
variant: design
phase: vo1
role: mle
level: L5
lang: en
domain: recsys
time_scale: 1.0
budget_minutes: 60
---

### T1 · interviewer · t=00m

Hi, I am Elena Vasquez, a Staff ML Engineer. Today: design the system that builds a member's personalized homepage, the rows, the titles inside each row and their order, on TV, mobile and web. Take a minute to ask me whatever you need.

<meta>
question_id: mlsd-design-homepage-rows-01
phase: intro
</meta>

### T2 · candidate · t=04m

I would start by asking what we optimize. I would say long-term retention is the goal and play-starts followed by at least two minutes of watching are my proxy, since clicks alone reward misleading artwork. Assumptions: 100 million members, 15,000 titles, page load under 400 ms at p99, and features refreshed hourly is acceptable. Guardrails: diversity of genres on the page and no drop in play-start rate. A constraint is privacy of viewing history, so access to it is limited. Is that scope fine?

### T3 · interviewer · t=06m

Fine. Go on with the architecture.

<meta>
question_id: mlsd-design-homepage-rows-01
phase: main
</meta>

### T4 · candidate · t=13m

There is an offline pipeline that builds candidates per row with a two-tower model and an ANN index, and a feature store with the same feature definitions for training and serving. A nearline job updates recent-play features every few minutes. At request time the page service gets the candidate rows from a cache by profile id, a ranker scores them, and an assembler orders rows and removes duplicate titles. On a request the TV app calls the service, the cache returns the rows, the ranker scores about 300 titles and the page is returned; if the cache misses we compute candidates on the fly.

### T5 · interviewer · t=15m

Which model ranks titles, and how do you train it?

<meta>
question_id: mlsd-design-homepage-rows-01
phase: main
</meta>

### T6 · candidate · t=22m

I would compare gradient boosted trees against a deep model with a sequence encoder. Trees are fast and good with cold start through metadata, the deep model captures viewing order but is slower, so under 400 ms I would take the deep model with nearline embeddings. The loss is a pairwise ranking loss on play-start. The training data are logged impressions with plays as positives; I know the position of the title affects clicks so I would add position as a feature and use NDCG@10 on a time holdout to choose the model.

### T7 · interviewer · t=24m

What happens when something fails, and how do you handle the cost?

<meta>
question_id: mlsd-design-homepage-rows-01
phase: main
time_warning_given: false
</meta>

### T8 · candidate · t=31m

We should have redundancy and good monitoring so that failures are handled. I would run the services in several zones and add autoscaling. Cost would be controlled by using smaller models where possible.

### T9 · interviewer · t=33m

Be concrete: the ranking service is down. What does the member see, and what is the availability target? Also, which data in your system is sensitive?

<meta>
question_id: mlsd-design-homepage-rows-01
phase: main
hint: {id: h1, level: nudge, competency: scale_reliability_security}
</meta>

### T10 · candidate · t=38m

Okay. The target would be 99.9%. If ranking is down we could show the cached page. The viewing history is sensitive.

### T11 · interviewer · t=40m

How would you validate the new ranker before launch?

<meta>
question_id: mlsd-design-homepage-rows-01
phase: main
</meta>

### T12 · candidate · t=47m

I would run interleaving first because it needs less traffic, and then an A/B test. Interleaving only tells me which ranker members prefer in a relative sense, not retention, so the A/B test has retention as the primary metric and play-start as guardrail. Offline and online can disagree because of the logging policy bias. I would monitor feature freshness, score distribution and latency, and roll back if guardrails break.

### T13 · interviewer · t=50m

Thanks, we are at time.

<meta>
question_id: mlsd-design-homepage-rows-01
phase: closed
</meta>
