---
instance_id: 10-culture@default
session_id: gold-culture-strong
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

My most significant project was a rewrite of the continue-watching ranker at my last company. The baseline was a recency heuristic; I proposed a sequence model, ran an 8-week A/B with 6% of members, and measured 7-day play-starts per member. The treatment lifted them by 2.1% with a 95% interval of 1.4% to 2.8%, with p99 latency up 6 ms, which I accepted. Personally I made three decisions: the target (completion-weighted plays, not clicks), dropping a feature that leaked the next play, and shipping behind a flag with a per-region ramp. My latest project is the offline replay tooling that made that evaluation cheap for four other teams, and my favorite was an earlier one that failed: a diversity re-ranker that lost 0.4% plays and that I killed after the second test. What I look for next is owning long-term satisfaction metrics end to end, because I have mostly optimized short-term proxies.

### T3 · interviewer · t=06m

Tell me about a high-stakes decision you made with incomplete data.

<meta>
question_id: culture-judgment-01
phase: main
culture_probe: {value: judgment}
</meta>

### T4 · candidate · t=11m

Two days before a launch, the canary showed a 1.2% drop in play-starts for TV devices only, with 3% of traffic, so the data were too thin to be sure. Options were launch as planned, delay a week, or launch everywhere except TV. I asked the data scientist and the TV client lead for their read, and set the criterion in advance: if I could not rule out a drop larger than 0.5% by Thursday, TV would wait. We shipped to web and mobile and held TV; the extra data on Thursday confirmed a client rendering bug that affected TV only. I was accountable for the call to my director, and the cost was a three-day slip on one platform and an unhappy product partner. What I learned is to agree the decision criterion before the data arrives.

### T5 · interviewer · t=13m

Tell me about disagreeing with someone more senior, and about a decision you opposed but committed to.

<meta>
question_id: culture-candor-01
phase: main
culture_probe: {value: candor}
</meta>

### T6 · candidate · t=19m

A principal engineer wanted to retrain our model daily to fix drift. I thought weekly retraining plus a drift monitor was enough and daily would triple the cost. I showed a plot of the metric over 12 weeks where daily retraining would have changed the metric by 0.1%, and he disagreed with my reading of the plot, so we ran the test and the gain was 0.2%, not worth the cost. In a different case, my manager chose to keep a legacy feature store for another quarter and I opposed it; I wrote my objection in the decision doc, and once decided I committed and built the migration plan for the next quarter. And my own mistake: I once shipped a metric definition that double counted autoplay; I told the team in the channel the same day, with the corrected dashboard, instead of waiting for someone to notice.

### T7 · interviewer · t=21m

Pick a time you gave up something for another team. And is there anything in the culture memo you are unsure about?

<meta>
question_id: culture-selflessness-01
phase: main
culture_probe: {value: selflessness}
</meta>

### T8 · candidate · t=27m

I handed my best features to the search team when their launch was a company priority, even though it delayed my own roadmap by a month; Priya, on that team, did most of the integration work and I made sure the review named her. In the memo I connect with context not control, because I now write decision docs instead of approving every change. My reservation is the keeper test: it can discourage long-term bets that look slow for a year, so I would want to know how the team protects people running them.

### T9 · interviewer · t=29m

What questions do you have for me?

<meta>
question_id: culture-candidate-questions
phase: candidate_questions
</meta>

### T10 · candidate · t=33m

How do you handle a disagreement with someone on your team when both of you are convinced? What does success look like at this level in the first year? And what does the memo not say about the team's day-to-day?

### T11 · interviewer · t=35m

Thank you, that is our time.

<meta>
question_id: culture-candidate-questions
phase: closed
</meta>
