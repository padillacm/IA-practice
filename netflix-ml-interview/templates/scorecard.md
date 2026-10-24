---
instance_id: 01-recruiter-screen@default
stage: recruiter-screen
variant: default
level: L5
rubric_version: 1
recommendation: pass          # pass | fail | insufficient_signal
level_observed: L5            # L4 | L5 | L6 | none
scores:                       # SN | N | Y | SY | no_evidence
  motivation_why_netflix: Y
  background_clarity: Y
  memo_awareness: Y
  role_fit_logistics: Y
  culture_signals: Y
evidence:                     # quotes must appear verbatim in a CANDIDATE turn
  motivation_why_netflix:
    - {turn_id: 3, quote: "exact words the candidate said"}
hints: []                     # [{id: h1, level: nudge|substantive, competency: <id>}]
---

# Scorecard: 01-recruiter-screen@default

> Recommendation derived by the simulator's pedagogical rule; Netflix does not use a common scale.
> Recomendación derivada por la regla pedagógica del simulador; Netflix no usa una escala común.

Write this body in the session language (en by default, es with lang=es). Enums in the header stay in English.

## Summary
Recommendation, observed level, and one paragraph of rationale.

## Scores and evidence
For each competency: score, the quoted evidence with its turn (T<n>), and, when the score is below Y,
what a Yes-level answer would have looked like.

## Hints
Every hint given (nudge or substantive), the competency it affected and the cap applied.

## Uncovered signal points
Points not covered (only when the stage ended for a candidate-side reason).

## Strengths and gaps

## Study plan
1-3 prioritized recommendations first, each linked to a recsys-course module, a practice stage or a resource.
