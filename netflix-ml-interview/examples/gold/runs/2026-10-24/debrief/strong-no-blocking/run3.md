---
type: final
session_id: unknown (not provided in the packet)
role: mle
target_level: L5
complete: false
provisional_outcome: no_hire
outcome: no_hire
level: none
override: false
culture_verdict: mixed
stages_considered: [05-coding@practical, 08-ml-system-design@design, 10-culture@default]
---

# Debrief

> Outcome derived by the simulator's pedagogical rule; Netflix does not use a common scale or a hiring committee.
> Resultado derivado por la regla pedagógica del simulador; Netflix no usa una escala común ni un hiring committee.

This is a teaching simulation of a Netflix-style debrief led by the hiring manager. It is not a real hiring decision.

## Step 1: deterministic rule

**Instances considered (catalog order, all completed in normal mode):**

| Instance | Weight (role `mle`) | Result | level_observed | Core competencies at SN |
|---|---|---|---|---|
| 05-coding@practical | low (1) | pass | L5 | none |
| 08-ml-system-design@design | high (3) | fail | none | modeling_choices, online_validation_monitoring |
| 10-culture@default | high (3) | pass | L5 | none |

No `sim.py recommend` output was provided, so I used each front-matter `recommendation` and checked it against the scores. Each one matches. 08-ml-system-design@design has two core SN scores and no score above N, which fits `fail`. The other two have only Y and SY scores, which fits `pass`.

**Weighted tally:**
- Sum of passing weights: coding (1) + culture (3) = **4**
- Sum of failing weights: ml-system-design (3) = **3**
- The weighted majority is pass (4 > 3), but blocking conditions apply first. A hire would need no blocking condition and a weighted pass majority.

**Blocking conditions (any one means `no_hire`):**
1. A core competency at SN in a high-weight stage: **yes, met**. 08-ml-system-design@design has `modeling_choices: SN` and `online_validation_monitoring: SN`.
2. A negative culture verdict: **no**. The verdict is `mixed` (see the culture section).
3. A high-weight stage at `fail`: **yes, met**. 08-ml-system-design@design is `fail`.
4. The minimum observed level among high-weight stages is `none`: **yes, met**. MLSD is `none` and culture is L5, so the minimum is `none`.

`referred` does not apply. It needs every high-weight VO1 stage to pass and a positive culture verdict, and here a high-weight VO1 stage (ml-system-design) fails.

**Provisional outcome: `no_hire`.**

**Observed level:** the minimum `level_observed` among the high-weight stages is **none** (ml-system-design = none, culture = L5).

**Culture verdict:** `mixed`. One weakness, in curiosity, is backed by one piece of evidence. It sits next to positive signals and is not resolved.

**Missing items (`complete: false`, so the result is provisional):**
- Screen: recruiter-screen, hm-screen, technical-screen@ml-coding (not run). There are no evaluated screens.
- VO2: ml-depth, project-deep-dive, partnership, hm-onsite (not run).
- The cut was not run.

**Missing signal (`insufficient_signal`):** none.

**Practice-only stages:** none.

## Step 2: panel discussion

**Arjun Mehta (Senior Software Engineer, 05-coding@practical): pass.** "The candidate solved the problem cleanly. In `testing_verification`, T6, they said: 'I will write boundary tests, ties, empty input, the validation errors and a randomized comparison against a brute force oracle.' In `complexity_optimality`, T4, they stated 'O(n) time and O(w) space' without being asked. On culture signals, T8, they pushed back with 'I would not ship it as the implementation, though.' and then accepted the trade-off when it held."

**Elena Vasquez (Staff ML Engineer, 08-ml-system-design@design): fail.** "There were core errors in two competencies. In `modeling_choices`, T6, the candidate said 'we split the logs randomly into train and test sets', and in T8, 'all the other movies in the catalog are negatives'. That stayed the same even after a substantive hint (h1). In `online_validation_monitoring`, T10, the deploy criterion was 'if it is higher than the old one we deploy it', with no online test and no monitoring. Framing was also below the bar: T4, 'Accuracy of the click prediction, I think.'"

**Rachel Goldberg (Director of Engineering, 10-culture@default): pass.** "There were specific events with real stakes. In `high_stakes_judgment`, T4, they said 'set the criterion in advance' and 'I was accountable for the call to my director'. In `candor_and_disagreement`, T6, they said 'I wrote my objection in the decision doc, and once decided I committed'. In `impact_with_metrics`, T2, they gave a result with an interval: 'The treatment lifted them by 2.1% with a 95% interval of 1.4% to 2.8%'."

**Victor Almeida (hiring manager): "Would anyone change their mind?"**

- **Arjun:** "No. My stage is low-weight, and nothing in my scorecard speaks to system design."
- **Elena:** "No. No scorecard has evidence that offsets the random split or the deploy-on-offline-accuracy criterion. My own scorecard has no counter-example either: in T10 the candidate admits 'not something I have seen before' but proposes no way to find out."
- **Rachel:** "No. My pass stands, but it does not cover the gaps in ML system design."

**Consensus:** the three votes stay as they were: two pass and one fail, with the fail in a high-weight stage that has two core SN scores. The HM did not open any transcript. None was provided, and no quoted evidence needed its context checked.

## Culture (aggregated by memo value)

| Value | Signal | Evidence |
|---|---|---|
| selflessness | positive | 10-culture@default, culture_signals, T8: "I made sure the review named her." |
| judgment | positive | 10-culture@default, high_stakes_judgment, T4: "set the criterion in advance"; 05-coding@practical, culture_signals, T8: "If you tell me the inputs are bounded by a few thousand, I agree the simple version is the better trade" |
| candor | positive | 10-culture@default, candor_and_disagreement, T6: "I wrote my objection in the decision doc, and once decided I committed" and "I told the team in the channel the same day"; culture_signals, T8: "My reservation is the keeper test"; 05-coding@practical, culture_signals, T8: "I would not ship it as the implementation, though." |
| creativity | no signal | (none) |
| courage | positive | 10-culture@default, high_stakes_judgment, T4: "I was accountable for the call to my director" |
| inclusion | no signal | (none) |
| curiosity | mixed (one weakness) | Weak: 08-ml-system-design@design, culture_signals (N), T10: "Honestly, the interviewer's question about the page layout is not something I have seen before." (the scorecard notes they proposed no way to find out). Positive: 10-culture@default, candidate_questions, T10: "what does the memo not say about the team's day-to-day?" |
| resilience | no signal | (none) |

**Verdict: `mixed`.** The culture stage's core `culture_signals` is Y, so the verdict is not negative. One value (curiosity) has a weakness backed by a single piece of evidence from a single stage, alongside positive signals.

## Hiring manager decision (informed captain)

**Decision: `no_hire`** (provisional, because the loop is incomplete). **Level: none.** **Override: false.**

Victor Almeida keeps the provisional outcome. The coding and culture scorecards are strong, but neither has evidence that answers the core gaps in 08-ml-system-design@design (`modeling_choices` T6/T8, `online_validation_monitoring` T10). A high-weight stage failed with two core SN scores, so the rule does not allow a hire, and no scorecard evidence supports an override.

**Provisional: missing items.** None of the screen stages were run (recruiter-screen, hm-screen, technical-screen@ml-coding), and none of the VO2 stages were run (ml-depth, project-deep-dive, partnership, hm-onsite). Running them would not change this outcome, because the blocking conditions come from a VO1 high-weight stage that has already been evaluated.

## Study plan

1. **ml-system-design.modeling_choices** (core SN, high-weight). Work on time-based splits instead of random log splits, choosing negatives from exposure (impressions rather than the whole catalog), comparing candidate models, and handling position and exposure bias. Modules: `recsys-course/06_ctr_ranking/`, `recsys-course/07_learning_to_rank_multitask/`, `recsys-course/08_deep_retrieval_ann/`, `recsys-course/09_sequential/`. Practice stage: `ml-system-design`.
2. **ml-system-design.online_validation_monitoring** (core SN, high-weight). Replace "deploy if offline is higher" with an online A/B test that has guardrails, off-policy evaluation, and post-launch drift monitoring. Modules: `recsys-course/15_online_experimentation/`, `recsys-course/14_bandits_rl_ope/`, `recsys-course/17_mlops_monitoring/`. Practice stage: `ml-system-design`.
3. **ml-system-design.problem_framing_requirements** (core N, high-weight). Separate the business goal from proxy metrics, put numbers on latency and scale, and state guardrails and constraints before designing. Modules: `recsys-course/00_intro/`, `recsys-course/18_capstone/`, `recsys-course/19_elite_playbook/`. Practice stage: `ml-system-design`.

Secondary:
- `ml-system-design.architecture_data_flow` (N): `recsys-course/16_production_serving/`, `recsys-course/08_deep_retrieval_ann/`.
- `ml-system-design.scale_reliability_security` (N): `recsys-course/16_production_serving/`, `recsys-course/17_mlops_monitoring/`.
- `ml-system-design.culture_signals` (N, curiosity): when you hit something you don't know, say how you would find out. Resource: Netflix culture memo, jobs.netflix.com/culture. Practice stage: `culture`.
- Strengths to keep: coding (`testing_verification` SY) and culture (all Y). Then run the missing stages (screen and VO2) to complete the loop.
