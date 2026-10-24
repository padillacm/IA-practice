---
instance_id: 08-ml-system-design@design
session_id: gold-mlsd-strong
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

### T2 · candidate · t=03m

Before designing I want to pin down the goal and the constraints. I would separate the business goal, long-term member satisfaction measured through retention, from the proxy I can optimize day to day: play-starts with a minimum watch duration plus completion, because raw clicks reward clickbait artwork. I will state my assumptions explicitly: about 200 million members, a catalog of about 20,000 titles, a p99 budget of 300 ms for the page request, and freshness such that a title started five minutes ago shows up on the next page load, not necessarily in the same session. Guardrails: row diversity and play-start rate per profile must not regress, and cost per thousand page requests stays flat. Constraints: viewing history is sensitive so features are scoped per profile with access control, and regional licensing filters apply. Does that scope match yours, including several profiles per account and TV as the primary device?

### T3 · interviewer · t=05m

That matches. Scale numbers are fine as assumptions. Go ahead with the architecture.

<meta>
question_id: mlsd-design-homepage-rows-01
phase: main
</meta>

### T4 · candidate · t=12m

I would run three paths. Offline batch: daily and hourly jobs build candidate sets per row type (continue watching, because you watched, trending, new releases) with a two-tower retrieval model and an ANN index, and write item embeddings and long-horizon member features to a feature store. Nearline: a stream processor over the play-event log, Kafka plus a Flink-class engine, updates short-horizon features such as the last 20 plays within minutes and invalidates the cached rows of that profile. Online: the page service reads precomputed candidate rows from a key-value cache keyed by profile id, fetches online features from a low-latency store, runs the ranker and then a page assembler that orders rows, deduplicates titles across rows and applies licensing filters. Offline and online features come from the same feature definitions, and training uses point-in-time joins to avoid leakage. Tracing one request: the TV app calls the page service, the cache returns rows in under 20 ms, the ranker scores about 500 candidates, the assembler builds the page. If the ranker times out at 150 ms we serve the last good cached page for that profile, and if that is missing a regional popularity page.

### T5 · interviewer · t=14m

How do you choose the title ranker and train it?

<meta>
question_id: mlsd-design-homepage-rows-01
phase: main
</meta>

### T6 · candidate · t=22m

I compare two options. A gradient boosted tree on engineered features is cheap and handles cold start through metadata, but it is weak on viewing order. A transformer sequence model over the last 50 plays captures order but costs about 30 ms per batch on GPU and needs more data. With a 150 ms budget I would compute the sequence-based member embedding nearline, so the heavy part is off the request path, and keep a small ranking head online. The loss is listwise with two heads, play-start and watch completion, combined with weights I tune against retention in tests. The training data come from logged impressions, which are biased by the old policy's exposure and by position, so I log the position and the propensity of each impression, train with position as a feature that I neutralize at inference, and reserve a small epsilon of random exploration traffic to get unbiased data. To choose between models offline I use NDCG@10 on a time-based holdout plus an inverse-propensity replay estimate on the exploration slice. For new titles I use content embeddings and Thompson sampling with a fixed exploration budget per row.

### T7 · interviewer · t=24m

Now it is 8pm on a Friday and the ranking service degrades. What happens? Also tell me about security and cost.

<meta>
question_id: mlsd-design-homepage-rows-01
phase: main
</meta>

### T8 · candidate · t=33m

Availability target: 99.95% for page loads, with p99 under 300 ms. Degraded modes: if the ranker is down or slow, the page service serves the last good page for the profile from cache; if the online feature store is down, the ranker runs with batch-computed default features from the cache, with lower quality but a page; if the cache is cold for a profile we fall back to a regional popularity page. I would load-test each of those paths and alarm on the fallback rate. Security: viewing history features are tagged restricted, access is per service and audited, logs hold hashed profile ids with a retention limit, and unreleased titles are only visible to flagged internal profiles, filtered in the page assembler so a ranker bug cannot leak them. The cost driver is GPU inference for the sequence encoder; I mitigate it by computing the embedding nearline only for profiles active in the last day and caching it, instead of running per request.

### T9 · interviewer · t=35m

Suppose the new ranker improves NDCG offline but the A/B test is flat. How do you validate, and what do you check?

<meta>
question_id: mlsd-design-homepage-rows-01
phase: main
</meta>

### T10 · candidate · t=44m

I validate in two stages. First interleaving, which needs far less traffic and detects ranking preference quickly, but it is a relative measure: it tells me which ranker members prefer inside the same list and says nothing about retention. So the second stage is an A/B test with retention and hours as primary metrics and play-start and diversity as guardrails, running at least two full weeks to cover weekly cycles. Offline and online metrics can disagree because the offline replay is biased by the logging policy and by position, and because offline cannot see page-level effects or novelty. If NDCG is up and the A/B is flat I first check for training-serving skew by comparing logged online features with recomputed ones, then the exposure bias of the holdout, then whether the gain is concentrated in a segment that is small. Monitoring has three layers: model quality (calibration, score distribution drift, online play-through of top-ranked titles), data (null rates, freshness lag of the nearline pipeline) and system (p99, cache hit rate, fallback rate). Rollback trigger: a guardrail breach or a fallback rate above 5% for ten minutes. Because the system chooses what to show, I keep the epsilon exploration traffic running so the data stay unbiased.

### T11 · interviewer · t=47m

A product partner says members will feel the page is stale and wants real-time scoring everywhere. Defend your choice or change it, and tell me what evidence would move you.

<meta>
question_id: mlsd-design-homepage-rows-01
phase: main
culture_probe: {value: judgment}
</meta>

### T12 · candidate · t=52m

I would keep the hybrid but change one thing. My position: batch candidates plus nearline features already refresh within minutes, and full real-time scoring multiplies GPU cost and widens the tail latency, so it risks the 300 ms target. The partner is right that staleness hurts in one case, right after a member finishes a title, so I would add a request-time re-rank of the top rows when a play event arrived in the last ten minutes. What would move me: a test where the real-time arm improves retention or play-starts by more than the cost justifies. I do not know yet how much staleness members actually notice, so I would measure it by running an A/B on cache age before we pay for the infrastructure.

### T13 · interviewer · t=55m

Thank you, that is our time.

<meta>
question_id: mlsd-design-homepage-rows-01
phase: closed
</meta>
