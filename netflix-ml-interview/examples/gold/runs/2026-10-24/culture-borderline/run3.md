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
    - {turn_id: 6, quote: "The week looked positive so I recommended shipping, and I told my director I took responsibility."}
    - {turn_id: 10, quote: "If something goes wrong I fix it quickly."}
  impact_with_metrics:
    - {turn_id: 4, quote: "We measured with an A/B test over two weeks, and play-starts per member went up by about 1.5%, I do not remember the interval."}
    - {turn_id: 4, quote: "The baseline was the previous model, a gradient boosted model."}
    - {turn_id: 2, quote: "Next I would like to work on a larger scale and with more modern techniques."}
  high_stakes_judgment:
    - {turn_id: 6, quote: "The options were to ship or wait."}
    - {turn_id: 6, quote: "I asked my manager and the data scientist."}
    - {turn_id: 6, quote: "The week looked positive so I recommended shipping, and I told my director I took responsibility."}
    - {turn_id: 6, quote: "I learned to check latency earlier."}
  candor_and_disagreement:
    - {turn_id: 8, quote: "Sometimes I mention a concern but I do not like to push too much, I prefer to keep the team harmonious."}
    - {turn_id: 8, quote: "I cannot think of a specific time right now."}
    - {turn_id: 10, quote: "I try not to make mistakes that affect others."}
  candidate_questions:
    - {turn_id: 12, quote: "What are the benefits and the vacation policy?"}
    - {turn_id: 12, quote: "And how big is the team?"}
hints: []
---

# Scorecard: 01-culture@default

> Recommendation derived by the simulator's pedagogical rule; Netflix does not use a common scale.
> Recomendación derivada por la regla pedagógica del simulador; Netflix no usa una escala común.

## Summary
**Recommendation: fail. Observed level: none.**

The session ended normally: the final interviewer meta shows `phase: closed` and lists no uncovered signal points. The candidate's best answer was on high-stakes judgment. They described a specific ship-or-wait decision, the two options, who they consulted, the accountability they took and a lesson learned, which meets the L5 bar. The other core competencies fell short:
- **Impact:** they described one project with a baseline, a number and a measurement method. They did not cover a second project, and their reason for what they want next was thin.
- **Candor:** they gave no specific event of disagreeing with someone more senior. They also gave no real account of a mistake of their own and how they shared it with others. Both answers were general statements.
- **Culture signals:** with no candor event, no link to memo mechanisms and no reservation about the memo, they did not reach the L5 bar.

Three core competencies are N, so the fixed rule gives fail. No level is observed: the L4 bars are not met either for culture_signals (no memo values or terms named) or for candor_and_disagreement (no example of giving or receiving feedback).

## Scores and evidence

### culture_signals: N
The interviewer probed two values in this session: judgment (T5) and candor (T7, T9).
- T6: "The week looked positive so I recommended shipping, and I told my director I took responsibility."
- T10: "If something goes wrong I fix it quickly."

**Judgment:** there is a real event with stakes, and a cost the candidate absorbed (the latency regression).

**Candor:** the candidate gave no event. They described smoothing problems over rather than admitting a mistake and sharing what they learned.

**Memo literacy:** the candidate named no memo values or mechanisms (informed captain, farming for dissent, disagree then commit, context not control, keeper test). They connected no events to the memo and stated no reservation about it.

**Model Yes answer (L5):** for each sampled value, a specific event with stakes, the cost absorbed and what changed afterward. For example: "On the launch decision I acted as the informed captain. I collected dissent from the data scientist first, shipped, then owned the latency regression publicly and added a latency guardrail to our launch checklist." Plus a candor event, such as a mistake shared in a team review and the process that changed after it. At least two events should be tied explicitly to memo mechanisms, and the candidate should state one reservation, for example "farming for dissent can slow small decisions, so I scale it to the stakes."

### impact_with_metrics: N
- T4: "The baseline was the previous model, a gradient boosted model."
- T4: "We measured with an A/B test over two weeks, and play-starts per member went up by about 1.5%, I do not remember the interval."
- T2: "Next I would like to work on a larger scale and with more modern techniques."

The answer meets the L4 bar: a baseline, a number and a personal decision (choosing the transformer for sequence data). It does not meet the L5 bar:
- Only one project was described, although the question asked for the favorite, latest and most significant.
- There was no interval and no guardrails for the result.
- "What I look for next" was generic and gave no reason.

**Model Yes answer (L5):** two projects, for example the latest and the most significant. Each should have:
- the metric and the baseline (for example "+1.5% play-starts per member versus the GBDT ranker, 95% CI roughly +0.8% to +2.2%, two-week A/B, latency guardrail held");
- the specific decisions the candidate made and why.

Then a concrete next step tied to those experiences, for example "I want to own sequence models at the scale where the long-term member-satisfaction trade-offs matter, because my last project only optimized short-term engagement."

### high_stakes_judgment: Y
- T6: "The options were to ship or wait."
- T6: "I asked my manager and the data scientist."
- T6: "The week looked positive so I recommended shipping, and I told my director I took responsibility."
- T6: "I learned to check latency earlier."

This is a decision with incomplete data (one week of A/B results before a deadline). The candidate named the options, the people they consulted, their explicit accountability and a lesson. The decision criterion ("the week looked positive") is thin, but it is present. This meets the L5 bar. It is the clearest evidence of the memo's Judgment value in the session: making a decision despite ambiguity and owning the result.

### candor_and_disagreement: N
- T8: "Sometimes I mention a concern but I do not like to push too much, I prefer to keep the team harmonious."
- T8: "I cannot think of a specific time right now."
- T10: "I try not to make mistakes that affect others."

The candidate gave general principles instead of events. They had no example of disagreeing with someone more senior, no example of committing to a decision they opposed, and no mistake of their own shared with others. The stated preference for harmony over pushing a concern runs against the memo's Candor value, but they did not describe avoiding feedback outright, so the score is N rather than SN.

**Model Yes answer (L5):** "My manager wanted to drop the holdout to ship faster. I disagreed and showed that without it we couldn't detect novelty decay. We compromised on a smaller holdout, which I committed to fully even though I'd argued for more. Separately, I once shipped a feature-pipeline bug that skewed a week of training data. I posted the root cause in our team channel, walked through it at the retro, and we added a schema check that has caught two issues since."

### candidate_questions: N
- T12: "What are the benefits and the vacation policy?"
- T12: "And how big is the team?"

The questions were about logistics and did not connect to the conversation. The team-size question is only loosely relevant. Neither the L5 bar nor the L4 bar is met.

**Model Yes answer (L5):** "How do you handle it when someone on your team disagrees with a decision you've made?", "What does a strong L5 look like here after six months?" or "What does the culture memo not capture about how this team works day to day?"

## Hints
None.

## Uncovered signal points
None recorded. The stage closed normally (`phase: closed`), and the final interviewer meta lists no uncovered signal points.

## Strengths and gaps
**Strengths**
- A concrete judgment story: a deadline, one week of data, the options, the people consulted, explicit accountability and a lesson learned.
- The impact story has the right building blocks: a baseline model, an A/B test and a per-member metric with a number.

**Gaps**
- **Candor:** no specific disagreement or mistake stories, and a stated tendency to defer for harmony.
- **Memo literacy:** no memo terms or mechanisms, no events connected to the memo, and no reservation about it.
- **Impact:** only one project, no confidence interval, and a generic, unexplained reason for what they want next.
- **Candidate questions:** about logistics rather than how the team works, disagreement or expectations.

## Study plan
1. **Candor and disagreement (core):** prepare two specific stories. One should show disagreeing with someone more senior and then committing. The other should show a mistake you shared openly and what changed afterward. Use the memo sections on candor, farming for dissent and the informed captain. Study-map entry `culture.candor_and_disagreement`: resource "Netflix culture memo: jobs.netflix.com/culture (candor, farming for dissent, informed captain)"; practice stage: `culture`.
2. **Culture signals and memo literacy (core):** reread the memo. Map each of your stories to a named value and mechanism, and prepare one reasoned reservation about the memo. Study-map entry `culture.culture_signals`: resource "Netflix culture memo: jobs.netflix.com/culture"; practice stage: `culture`.
3. **Impact with metrics (core):** prepare the favorite, latest and most significant projects. For each, cover the metric, baseline, measurement method (with intervals and guardrails), your own decisions, and a reasoned "what next". Study-map entry `culture.impact_with_metrics`: course modules `recsys-course/02_evaluation/` and `recsys-course/15_online_experimentation/`; practice stage: `culture`.

Also, for `culture.candidate_questions`, prepare questions on how the director handles disagreement and what success looks like at your level (practice stage: `culture`).
