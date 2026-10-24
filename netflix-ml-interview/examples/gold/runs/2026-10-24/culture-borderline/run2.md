---
instance_id: 01-culture@default
stage: culture
variant: default
level: L5
rubric_version: 1
recommendation: fail
level_observed: none
scores:
  culture_signals: N
  impact_with_metrics: N
  high_stakes_judgment: Y
  candor_and_disagreement: N
  candidate_questions: N
evidence:
  culture_signals:
    - {turn_id: 6, quote: "It worked out, though we later found a small latency regression that we fixed. I learned to check latency earlier."}
    - {turn_id: 8, quote: "Sometimes I mention a concern but I do not like to push too much, I prefer to keep the team harmonious."}
  impact_with_metrics:
    - {turn_id: 4, quote: "We measured with an A/B test over two weeks, and play-starts per member went up by about 1.5%, I do not remember the interval."}
    - {turn_id: 4, quote: "The baseline was the previous model, a gradient boosted model."}
    - {turn_id: 2, quote: "Next I would like to work on a larger scale and with more modern techniques."}
  high_stakes_judgment:
    - {turn_id: 6, quote: "The options were to ship or wait. I asked my manager and the data scientist."}
    - {turn_id: 6, quote: "The week looked positive so I recommended shipping, and I told my director I took responsibility."}
    - {turn_id: 6, quote: "I learned to check latency earlier."}
  candor_and_disagreement:
    - {turn_id: 8, quote: "When my manager has a different opinion I usually respect it, since they have more context."}
    - {turn_id: 8, quote: "I cannot think of a specific time right now."}
    - {turn_id: 10, quote: "I try not to make mistakes that affect others. If something goes wrong I fix it quickly."}
  candidate_questions:
    - {turn_id: 12, quote: "What are the benefits and the vacation policy? And how big is the team?"}
hints: []
---

# Scorecard: 01-culture@default

> Recommendation derived by the simulator's pedagogical rule; Netflix does not use a common scale.
> Recomendación derivada por la regla pedagógica del simulador; Netflix no usa una escala común.

## Summary
**Recommendation: fail. Observed level: none.**

The session closed normally. The final interviewer meta shows `phase: closed` and lists no uncovered signal points. The candidate gave one solid story about a high-stakes decision. They named the options, who they consulted, that they took accountability and what they learned, which meets the L5 bar for high_stakes_judgment.

Three of the four core competencies fall below the L5 bar:
- **impact_with_metrics:** the candidate described only one project. It had a baseline, a metric and a measurement method, but they gave no confidence interval and only a thin reason for what they want next.
- **candor_and_disagreement:** the candidate gave general principles and no specific events. They could not name a time they disagreed with someone more senior, and they did not describe sharing a mistake of their own.
- **culture_signals:** the judgment story is specific, but the candor value had no event behind it. The candidate did not use any memo term, connect a story to a memo mechanism or state a reservation about the memo.

With two or more core competencies at N, the fixed rule gives fail. No level is observed because culture_signals does not meet even the L4 bar, which requires naming memo values and using a memo term.

## Scores and evidence

### culture_signals: N (core)
- T6: "It worked out, though we later found a small latency regression that we fixed. I learned to check latency earlier."
- T8: "Sometimes I mention a concern but I do not like to push too much, I prefer to keep the team harmonious."

The interviewer probed two memo values, **Judgment** and **Candor**.
- **Judgment:** the candidate gave a specific event with stakes (a deadline and only one week of A/B data). They named a cost they absorbed (a latency regression) and a change afterward (checking latency earlier).
- **Candor:** there was no event. The candidate described holding back concerns to keep the team harmonious, which is the opposite of the memo's description of candor.

At no point did the candidate name a memo mechanism (informed captain, farming for dissent, disagree then commit, context not control, keeper test) or state a reservation about the memo.

**What a Yes answer looks like at L5:** a specific event for each probed value.
- For candor, something like: "I told my tech lead in a design review that offline NDCG would not carry over online. I was wrong about the size of the gap, and afterward I added an online check before reviews."
- Link two of the stories to memo mechanisms. For example, the shipping decision was an informed-captain call taken after farming for dissent from the data scientist.
- State one honest reservation, such as how hard it is to keep candor kind when there is deadline pressure.

### impact_with_metrics: N (core)
- T4: "We measured with an A/B test over two weeks, and play-starts per member went up by about 1.5%, I do not remember the interval."
- T4: "The baseline was the previous model, a gradient boosted model."
- T2: "Next I would like to work on a larger scale and with more modern techniques."

The candidate covered only one project, the latest one. That project has a baseline (GBM), a metric (play-starts per member, +1.5%), a method (a two-week A/B test) and a personal decision (choosing a transformer because the data was sequential). This meets the L4 bar. The L5 bar asks for at least two of the favorite, latest and most significant projects. The candidate did not give a confidence interval, and their reason for what they want next was generic, with no explanation of why.

**What a Yes answer looks like at L5:** two projects, each with its metric, baseline, how it was measured (A/B test, interval, guardrails) and the decisions the candidate personally made. Then a specific next step with a reason, for example: "I want to own the ranking for a whole surface, because my last project showed that the gains from sequence models depend on how features are served."

### high_stakes_judgment: Y (core)
- T6: "The options were to ship or wait. I asked my manager and the data scientist."
- T6: "The week looked positive so I recommended shipping, and I told my director I took responsibility."
- T6: "I learned to check latency earlier."

This answer covers each part of the L5 bar:
- The decision was high-risk and made with incomplete data: one week of A/B results and a deadline.
- The candidate named the options and who they consulted.
- They took accountability explicitly.
- They described the outcome and what they learned.

The decision criteria are thin ("the week looked positive"). That keeps the answer at Y, not SY.

### candor_and_disagreement: N (core)
- T8: "When my manager has a different opinion I usually respect it, since they have more context."
- T8: "I cannot think of a specific time right now."
- T10: "I try not to make mistakes that affect others. If something goes wrong I fix it quickly."

The candidate gave general principles instead of events:
- They gave no example of disagreeing with someone more senior.
- They gave no example of committing to a decision they had opposed.
- When asked about a mistake, they said how they try to avoid mistakes and did not describe sharing one with others.

**What a Yes answer looks like at L5:**
- A specific time they disagreed with a manager or staff engineer, with the reasoning they gave. For example, arguing for a longer A/B test because of novelty effects.
- How the decision ended up and how they committed to it if it went against them.
- A specific mistake of their own that they told the team about, with what it affected and what changed afterward. For example, a data-leakage bug they reported in the team channel, followed by a new validation check.

### candidate_questions: N (non-core)
- T12: "What are the benefits and the vacation policy? And how big is the team?"

The questions were about logistics and benefits. None connected to the conversation, such as how the director handles disagreement, what success looks like at L5, or how the memo works in daily team life.

**What a Yes answer looks like at L5:** "How do you handle it when someone on your team disagrees with a decision you've made?" or "What separates a strong L5 from an adequate one on this team in the first six months?"

## Hints
None.

## Uncovered signal points
None. The session closed normally (`phase: closed`), and the final interviewer meta lists no uncovered signal points.

## Strengths and gaps
**Strengths**
- A structured, accountable account of a shipping decision made with partial data, including who was consulted and what was learned.
- The project story names a concrete online metric and the A/B test used to measure it.

**Gaps**
- No specific candor or disagreement events. The answers avoided conflict and did not admit a mistake.
- Only one project was described, with no confidence interval and no clear reason for the next step.
- No memo vocabulary, no link from stories to memo mechanisms and no reservation about the memo.
- The questions for the interviewer were about logistics, not culture or expectations at the level.

## Study plan
1. **candor_and_disagreement (core):** prepare two specific stories. One should be a disagreement with someone more senior, ending in disagree-then-commit. The other should be a mistake of yours that you shared openly. Use the memo sections on candor, farming for dissent and informed captain (Netflix culture memo: jobs.netflix.com/culture), then practice the `culture` stage again.
2. **impact_with_metrics (core):** prepare your favorite, latest and most significant projects, each with its metric, baseline, method and interval. Review `recsys-course/02_evaluation/` and `recsys-course/15_online_experimentation/`, then practice the `culture` stage again.
3. **culture_signals (core):** reread the Netflix culture memo (jobs.netflix.com/culture). Link each story to a memo mechanism and prepare one honest reservation about the memo. Practice the `culture` stage again.

Also: for candidate_questions, prepare questions on how the director handles disagreement and what success looks like at L5 (study-map entry `culture.candidate_questions`).
