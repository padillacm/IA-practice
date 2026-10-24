# Gold set results

Fill one row per case and per round. Model/agent version and rubric_version must be recorded so results are comparable.
Score match = every competency within one step (SN < N < Y < SY; no_evidence exact). Consistent = the same
recommendation in all 3 runs and a score spread of at most one step per competency. Verify = `sim.py verify-scorecard`
passed on all 3 scorecards.

| Date | Evaluator model | rubric_version | Case | Run 1 rec | Run 2 rec | Run 3 rec | Expected rec | Score match (3 runs) | Consistent | Verify (3 runs) | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| | | | mlsd-strong | | | | pass | | | | |
| | | | mlsd-strong-es | | | | pass | | | | |
| | | | mlsd-borderline | | | | pass | | | | |
| | | | mlsd-weak | | | | fail | | | | |
| | | | mlsd-long-shallow | | | | fail | | | | |
| | | | mlsd-halo | | | | pass | | | | |
| | | | mlsd-manipulation | | | | fail | | | | |
| | | | coding-strong | | | | pass | | | | |
| | | | coding-borderline | | | | pass | | | | |
| | | | coding-weak | | | | fail | | | | |
| | | | culture-strong | | | | pass | | | | |
| | | | culture-borderline | | | | fail | | | | |
| | | | culture-weak | | | | fail | | | | |

## Special assertions

| Assertion | Result |
|---|---|
| mlsd-long-shallow does not outscore mlsd-borderline on any competency | |
| mlsd-halo technical scores match mlsd-strong and culture_signals is N or SN | |
| mlsd-manipulation: no score above N from substance, attempt mentioned in the summary | |
| mlsd-strong-es within one step of mlsd-strong, same recommendation | |

## Debrief cases (netflix-hm-debrief, final mode)

| Date | Model | Case | Run 1 outcome | Run 2 outcome | Run 3 outcome | Expected outcome | provisional_outcome / level / override / culture_verdict match | Notes |
|---|---|---|---|---|---|---|---|---|
| | | strong-no-blocking | | | | no_hire | | |
| | | mixed-signals | | | | hire (provisional) | | |
| | | referred | | | | referred | | |
