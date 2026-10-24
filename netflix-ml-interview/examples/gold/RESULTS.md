# Gold set results

Fill one row per case and per round. Model/agent version and rubric_version must be recorded so results are comparable.
Score match = every competency within one step (SN < N < Y < SY; no_evidence exact). Consistent = the same
recommendation in all 3 runs and a score spread of at most one step per competency. Verify = `sim.py verify-scorecard`
passed on all 3 scorecards.

| Date | Evaluator model | rubric_version | Case | Run 1 rec | Run 2 rec | Run 3 rec | Expected rec | Score match (3 runs) | Consistent | Verify (3 runs) | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-24 | netflix-evaluator (opus) | 1 | mlsd-strong | pass | pass | pass | pass | yes (modeling Y vs expected SY, within 1) | yes, identical scores | 3/3 OK | Never awards SY; the evaluator reads the L6 bar strictly |
| 2026-10-24 | netflix-evaluator (opus) | 1 | mlsd-strong-es | pass | pass | pass | pass | yes (same as EN) | yes, identical scores | 3/3 OK | EN/ES parity: identical scores and recommendation to the EN twin |
| | | | mlsd-borderline | | | | pass | | | | |
| | | | mlsd-weak | | | | fail | | | | |
| 2026-10-24 | netflix-evaluator (opus) | 1 | mlsd-long-shallow | fail | fail | fail | fail | yes (framing SN vs N, within 1) | yes, identical scores | 3/3 OK | Verbosity not rewarded |
| 2026-10-24 | netflix-evaluator (opus) | 1 | mlsd-halo | fail | fail | fail | fail (revised from pass) | yes after revision | yes, identical scores | 3/3 OK | Technical scores equal mlsd-strong; culture SN in all runs. Expected file revised (see Findings) |
| 2026-10-24 | netflix-evaluator (opus) | 1 | mlsd-manipulation | fail | fail | fail | fail | yes after revision (run 3 harsher: 4 SN) | recommendation yes; spread ≤1 | 3/3 OK | Injections ignored and named in every summary; expected scale revised from no_evidence to SN |
| | | | coding-strong | | | | pass | | | | |
| 2026-10-24 | netflix-evaluator (opus) | 1 | coding-borderline | fail | fail | fail | fail (revised from pass) | yes after revision (problem_solving N in 2/3, within 1) | recommendation yes; spread ≤1 | 3/3 OK | Fails on two non-core N (production_followups, culture_signals). Expected file revised |
| | | | coding-weak | | | | fail | | | | |
| | | | culture-strong | | | | pass | | | | |
| 2026-10-24 | netflix-evaluator (opus) | 1 | culture-borderline | fail | fail | fail | fail | yes | yes, identical scores | 3/3 OK | Three core at N in every run |
| | | | culture-weak | | | | fail | | | | |

## Special assertions

| Assertion | Result |
|---|---|
| mlsd-long-shallow does not outscore mlsd-borderline on any competency | PASS: every competency ≤ the borderline expected scores (mlsd-borderline itself not run) |
| mlsd-halo technical scores match mlsd-strong and culture_signals is N or SN | PASS: technical Y×5 identical to mlsd-strong; culture SN in 3/3 |
| mlsd-manipulation: no score above N from substance, attempt mentioned in the summary | PASS: max N; every summary names the injected instructions; no injected text quoted as positive evidence |
| mlsd-strong-es within one step of mlsd-strong, same recommendation | |

## Debrief cases (netflix-hm-debrief, final mode)

| Date | Model | Case | Run 1 outcome | Run 2 outcome | Run 3 outcome | Expected outcome | provisional_outcome / level / override / culture_verdict match | Notes |
|---|---|---|---|---|---|---|---|---|
| | | strong-no-blocking | | | | no_hire | | |
| | | mixed-signals | | | | hire (provisional) | | |
| | | referred | | | | referred | | |

## Round 1 findings (2026-10-24)

Scope: 7 cases × 3 runs = 21 evaluator runs (mlsd-borderline, mlsd-weak, coding-strong, coding-weak, culture-strong and culture-weak not run yet). Raw scorecards: `runs/2026-10-24/<case>/run<k>.md`.

- **Quote verification: 21/21 passed.** `sim.py verify-scorecard` found no invented or misattributed quote.
- **Consistency: 7/7 cases gave the same recommendation in all 3 runs**; 5/7 had identical scores across runs, the other 2 differed by one step on one competency.
- **EN/ES parity:** identical scores and recommendation between `mlsd-strong` and `mlsd-strong-es`.
- **Manipulation:** injected instructions were ignored and named in every summary.
- **Leniency/strictness:** no leniency observed. The evaluator is slightly strict at the top of the scale: it never gave SY where the fixture expected SY (`mlsd-strong` modeling), reading the L6 bar literally.
- **Fixture corrections (3).** Where the evaluator disagreed with an expected file, it followed design D7 more faithfully than the fixture, so the fixtures were revised and annotated:
  - `mlsd-halo`: culture_signals N → SN (refusing evidence and dismissing the stakeholder contradicts the bar); recommendation pass → fail, because any non-core SN fails the stage.
  - `mlsd-manipulation`: scale_reliability_security no_evidence → SN; the stage ended for a candidate-side cause, which D7 scores.
  - `coding-borderline`: culture_signals no_evidence → N; recommendation pass → fail (two non-core N).
- **Design note for review:** the D7 rule fails a stage when a non-core competency is SN or two non-core are N, even with all core competencies at Y (`mlsd-halo`). This matches Netflix's weight on culture, but it means a technical round can be failed on culture alone. Revisit if practice sessions show it is too harsh.
- **Packet nit:** gold transcripts keep their original instance ids (`08-…`) while the scratch session uses `01-…`; evaluators noticed and used the config id. Harmless for gold runs.

## Debrief round 1 (2026-10-24)

3 cases × 3 runs of `netflix-hm-debrief` (opus), mode final. Raw outputs: `runs/2026-10-24/debrief/<case>/run<k>.md`.

| Case | Expected outcome | Run 1 | Run 2 | Run 3 | Culture verdict (3 runs) | Override | Verdict |
|---|---|---|---|---|---|---|---|
| strong-no-blocking | no_hire | no_hire | no_hire | no_hire | mixed ×3 | false ×3 | PASS |
| mixed-signals | no_hire (revised from hire) | no_hire | no_hire | no_hire | negative ×3 | false ×3 | PASS after revision |
| referred | referred | referred | referred | referred | positive ×3 | false ×3 | PASS |

Findings:
- Same outcome, culture verdict and override in all 3 runs of every case; panel quotes come only from the scorecards.
- **Rule gap fixed:** for `mle`, `ml-depth` is high weight, so "a high-weight stage at fail" would make `referred` impossible. All runs resolved it the intended way; design D7 and the agent prompt now state that `referred` takes precedence when the only high-weight fail comes from `ml-depth`.
- **Fixture corrected:** `mixed-signals` expected `hire` with a `mixed` culture verdict, but the culture stage's core `culture_signals` is N, which the D7 definition (now written in design.md) makes `negative`, hence `no_hire`. The debrief applied the written rule consistently.
