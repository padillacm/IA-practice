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
    - {turn_id: 8, quote: "I cannot think of a specific time right now."}
    - {turn_id: 10, quote: "I try not to make mistakes that affect others. If something goes wrong I fix it quickly."}
  impact_with_metrics:
    - {turn_id: 4, quote: "The baseline was the previous model, a gradient boosted model."}
    - {turn_id: 4, quote: "We measured with an A/B test over two weeks, and play-starts per member went up by about 1.5%, I do not remember the interval."}
    - {turn_id: 2, quote: "Next I would like to work on a larger scale and with more modern techniques."}
  high_stakes_judgment:
    - {turn_id: 6, quote: "We had to decide whether to ship a model before a deadline with only one week of A/B data. The options were to ship or wait."}
    - {turn_id: 6, quote: "I asked my manager and the data scientist."}
    - {turn_id: 6, quote: "The week looked positive so I recommended shipping, and I told my director I took responsibility."}
    - {turn_id: 6, quote: "I learned to check latency earlier."}
  candor_and_disagreement:
    - {turn_id: 8, quote: "When my manager has a different opinion I usually respect it, since they have more context."}
    - {turn_id: 8, quote: "Sometimes I mention a concern but I do not like to push too much, I prefer to keep the team harmonious."}
    - {turn_id: 10, quote: "I try not to make mistakes that affect others. If something goes wrong I fix it quickly. The team knows I am reliable."}
  candidate_questions:
    - {turn_id: 12, quote: "What are the benefits and the vacation policy? And how big is the team?"}
hints: []
---

# Scorecard: 01-culture@default

> Recommendation derived by the simulator's pedagogical rule; Netflix does not use a common scale.
> Recomendación derivada por la regla pedagógica del simulador; Netflix no usa una escala común.

## Summary
**Recommendation: fail. Observed level: none.**

No end reason was recorded. The final interviewer meta shows `phase: closed` and lists no uncovered signal points, so this is treated as a normal close. The candidate gave one solid answer: the high-stakes shipping decision. It had the options, who they consulted, ownership of the outcome and what they learned, which meets the L5 bar. The other core areas fell short.

- **Impact:** the candidate talked about only one project. It had a baseline, a metric and an A/B test, but no confidence interval, and the reason for what they want next was thin.
- **Candor:** the questions on disagreement and on sharing a mistake got general statements instead of events. The answers also leaned toward avoiding disagreement and not admitting mistakes.
- **Memo literacy:** the candidate named no memo mechanism and stated no reservation about the memo.

Three core competencies are at `N`, so the fixed rule gives `fail`. The L4 bar for culture_signals is not met either (no memo values or terms, and no candor event), so the observed level is `none`. The transcript header says `10-culture@default` but the config says `01-culture@default`. The config id is used here.

## Scores and evidence

### culture_signals (core): N
The sampled values were judgment and candor. For judgment, the candidate gave an event with stakes, a cost they absorbed and a change afterward: "It worked out, though we later found a small latency regression that we fixed. I learned to check latency earlier." (T6). For candor, there was no event: "I cannot think of a specific time right now." (T8). The mistake answer avoided admitting one: "I try not to make mistakes that affect others. If something goes wrong I fix it quickly." (T10). The candidate never tied an event to a memo mechanism and stated no reservation about the memo.

**What a Yes answer would look like (L5):** a specific event for each sampled value, each with stakes, a cost absorbed and what changed afterward. For candor, for example: "I told my tech lead in a design review that our offline metric didn't predict online results. I showed three past launches where it diverged. He disagreed at first, then we added an online proxy check, and I learned to bring data before raising a concern." Then link at least two events to memo mechanisms: the shipping call as acting as an informed captain, and the review pushback as farming for dissent. Finally, state one reservation, for example that the keeper test can push people to hide mistakes if it isn't paired with real psychological safety.

### impact_with_metrics (core): N
- T4: "The baseline was the previous model, a gradient boosted model."
- T4: "We measured with an A/B test over two weeks, and play-starts per member went up by about 1.5%, I do not remember the interval."
- T2: "Next I would like to work on a larger scale and with more modern techniques."

The latest project clears the L4 bar: it has a baseline, a number and a personal decision (choosing a transformer for sequence data). The L5 bar asks for two of the favorite, latest and most significant projects, and only one was described. "What next" was stated without a real reason.

**What a Yes answer would look like (L5):** two projects, each with metric, baseline, measurement method and the candidate's own decisions. For example: "Latest: I replaced the GBDT ranker with a sequence transformer because session order carried signal the trees couldn't use. A two-week A/B test showed +1.5% play-starts per member, 95% CI roughly +0.8% to +2.2%, with latency as a guardrail. Most significant: [a second project with the same structure]." Then a forward-looking reason, for example: "Next I want to work on multi-objective ranking at larger scale, because my last launch showed that engagement alone missed long-term retention."

### high_stakes_judgment (core): Y
- T6: "We had to decide whether to ship a model before a deadline with only one week of A/B data. The options were to ship or wait."
- T6: "I asked my manager and the data scientist."
- T6: "The week looked positive so I recommended shipping, and I told my director I took responsibility."
- T6: "I learned to check latency earlier."

This covers the L5 elements: a high-risk decision with incomplete data, named options, who they consulted, ownership of the outcome and a lesson. The criterion ("looked positive") was thin, which keeps this at Y rather than SY. There was no long-term versus short-term trade-off and no description of how the downside was limited.

### candor_and_disagreement (core): N
- T8: "When my manager has a different opinion I usually respect it, since they have more context."
- T8: "Sometimes I mention a concern but I do not like to push too much, I prefer to keep the team harmonious."
- T10: "I try not to make mistakes that affect others. If something goes wrong I fix it quickly. The team knows I am reliable."

These are general principles, not events. There is no example of disagreeing with someone senior, none of disagreeing and then committing, and no mistake the candidate shared with others. The answers lean toward avoiding conflict. This is the rubric's `N` pattern ("gives a general principle instead of an event"). It stops short of `SN` because the candidate did not describe avoiding feedback outright.

**What a Yes answer would look like (L5):** "My director wanted to launch a ranker on offline NDCG alone. I disagreed because our last two offline wins had been flat online, and I showed him the data. He decided to launch anyway with a short holdback. I committed, set up the monitoring and reported the results honestly. Separately, I once shipped a feature with a training-serving skew bug. I posted a write-up in the team channel with the root cause and the check I added, so others wouldn't repeat it."

### candidate_questions (non-core): N
- T12: "What are the benefits and the vacation policy? And how big is the team?"

Benefits and vacation are logistics and don't connect to anything discussed. Team size touches the team only loosely. None of the questions reaches the L5 topics: how the director handles disagreement, what success looks like at this level, or what the memo leaves out about day-to-day work.

**What a Yes answer would look like (L5):** "How do you handle it when someone on your team disagrees with a decision you've already made? What separates a strong L5 from an average one here in the first year? What about the team's day-to-day isn't captured in the culture memo?"

## Hints
None.

## Uncovered signal points
None recorded. The session closed normally (`phase: closed`) and the final interviewer meta lists no `uncovered_signal_points`. The candor gaps are scored above from the candidate's own answers.

## Strengths and gaps
**Strengths**
- A well-structured judgment story: incomplete data, two options, the people consulted, explicit ownership to the director and a concrete lesson (check latency earlier). This shows the memo's judgment value.
- Quantified a result against a named baseline with an online A/B test.

**Gaps**
- **Candor (memo value):** no specific disagreement with a senior person, no disagreeing then committing, and no shared mistake. The answers suggested avoiding conflict and not admitting mistakes, the opposite of what the memo asks for.
- **Memo literacy:** no memo terms (informed captain, farming for dissent, disagree then commit) and no reservation about the memo.
- **Impact framing:** only one project, no confidence interval, and a vague reason for what comes next.
- **Questions:** logistics rather than questions about the team, the level or the culture.

## Study plan
1. **Candor and disagreement (core gap).** Prepare two real stories: one where you disagreed with someone more senior and then committed, and one where you shared a mistake with root cause and lesson. Resource: Netflix culture memo, jobs.netflix.com/culture (candor, farming for dissent, informed captain). Practice stage: `culture` (study map: `culture.candor_and_disagreement`).
2. **Impact with metrics (core gap).** Prepare your favorite, latest and most significant projects, each with metric, baseline, method (including the interval) and your own decisions, plus a reason-backed "what next". Course: `recsys-course/02_evaluation/`, `recsys-course/15_online_experimentation/`. Practice stage: `culture` (study map: `culture.impact_with_metrics`).
3. **Culture signals and memo literacy (core gap).** Map each of your stories to a memo value and mechanism, and write down one honest reservation about the memo. Resource: Netflix culture memo, jobs.netflix.com/culture. Practice stage: `culture` (study map: `culture.culture_signals`). For candidate questions, prepare ones about how disagreement is handled and what success looks like at L5 (study map: `culture.candidate_questions`).
