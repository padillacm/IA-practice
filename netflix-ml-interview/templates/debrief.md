---
type: final                   # cut | final
session_id: YYYY-MM-DD-xxxxxx
role: mle
target_level: L5
complete: true                # false -> provisional (missing stages or only screens)
provisional_outcome: hire     # hire | no_hire | referred (deterministic rule, step 1)
outcome: hire                 # hire | no_hire | referred (cut uses: continue | stop)
level: L5                     # minimum observed level across high-weight stages
override: false               # true only with a justification citing scorecards
culture_verdict: positive     # positive | negative | mixed
stages_considered: []         # instance ids, in catalog order
---

# Debrief

> Outcome derived by the simulator's pedagogical rule; Netflix does not use a common scale or a hiring committee.
> Resultado derivado por la regla pedagógica del simulador; Netflix no usa una escala común ni un hiring committee.

## Step 1: deterministic rule
Weighted tally by role weights, high-weight stage results, culture verdict, observed level.

## Step 2: panel discussion
Scorecards read in catalog order. Each simulated interviewer: pass or fail. "Would anyone change their mind?"
Only evidence already present in a scorecard may be cited. Say which transcript the HM opened and why.

## Culture (aggregated by memo value)
One verdict. A weakness repeated in several stages counts once, backed by all its evidence.

## Hiring manager decision (informed captain)
If different from the provisional outcome: `override: true` and a justification citing scorecards.

## Study plan
Top gaps first, linked to recsys-course modules, practice stages or resources.
