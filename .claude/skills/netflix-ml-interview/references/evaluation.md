# Stage close, evaluation, cut and debrief

Rationale: design.md D7. The simulator's scale is a teaching device, not Netflix's.

## 1. Closing an instance

When `meta.phase == closed`, the candidate used `::end`, or the clock hit 100% and the interviewer closed:

1. `sim.py end <session> <instance> --reason <completed|candidate_end|time_up|uncovered|interrupted|skipped>`.
   - `completed`: normal close. `time_up`/`uncovered`: candidate cause (what was missing is scored and listed). `candidate_end`/`interrupted`: external cause (uncovered competencies stay `no_evidence`).
2. For ai-assisted-coding, run the hidden tests (`stages.md`).
3. Evaluate according to the session `feedback` mode (below).

## 2. Evaluator contract

Agent `netflix-evaluator` (no tools beyond Read/Glob/Grep, cannot write). Its prompt is exactly the output of `sim.py packet evaluator <session> <instance>` (add `--inline` to embed the transcript, `--note "<line>"` for factual extras such as the hidden-test result). It contains: instance id, stage, variant, target level, role, domain, session language, session mode, `rubric_version`, `end_reason` and its cause, the stage competency list with `core` flags, the absolute paths of the filtered transcript (private notes already removed, saved under `packets/`), the rubric (the evaluator reads it; you do not), `study-map.yaml` and the scorecard template, and the reminders about verbatim candidate quotes and hint caps. Pass it unchanged as the `Agent`/`SendMessage` prompt.

### Writing and verifying the scorecard

Save the evaluator's markdown unchanged by piping it to `sim.py`; never Write the file yourself:

1. `sim.py write-scorecard <session> <NN> --stdin` (or `--file <scratchpad file>`). It runs the guard, validates the front-matter against `templates/scorecard.md` and the D10 enums (ids, level, `rubric_version`, recommendation, `level_observed`, scores, hints), then runs the same checks as `verify-scorecard` (verbatim quotes from candidate turns, hint caps, every competency scored, recommendation equals the rule). It writes `scorecards/<instance>.md` and records the path in `session.yaml` only when everything passes; otherwise it exits non-zero, prints the failing items and keeps nothing (an existing valid scorecard is never overwritten).
2. On failure: resume the evaluator once (`SendMessage`) listing the printed failures, then run `write-scorecard` again with its corrected version.
3. If failures remain, run it a last time with `--downgrade`: unverifiable competencies become `no_evidence`, the recommendation is recomputed and the file is written. Tell the candidate which competencies were downgraded and why. (`--keep-invalid` keeps a failing file for inspection; `verify-scorecard --session ... --instance ...` re-checks a saved one.)
4. Optionally confirm with `sim.py recommend <scorecard path>`.

## 3. Feedback modes

- **immediate**: run `netflix-evaluator` in the **foreground** right after the stage. Show the scorecard (summary table of scores with quotes and prose) in the session language before continuing. Include the line "Recommendation derived by the simulator's pedagogical rule; Netflix does not use a company-wide scale."
- **deferred**: launch the evaluator with `Agent` in the **background** (`run_in_background: true`, name `ev-<instance>-<sid>`), say nothing about scores, and start the next instance. Notifications from the evaluator arrive mid-stage: handle them silently (write + verify the scorecard when the next stage is not running a turn, or at the barrier). Scorecards are shown together with the final decision.
- **Barrier**: before the cut and before the debrief, every needed instance must have a verified scorecard (done instances only; skipped ones are excluded). If background evaluators are pending, wait for them (end your turn, handle the notifications) before proceeding.

## 4. Continue, pause, finish

After each stage offer: continue to the next instance, pause (`sim.py pause` is already closed with the stage; the session stays resumable) or finish. If the candidate finishes with pending instances, mark them: `sim.py end <session> <NN> --reason skipped`. If two or more instances were completed, convene the debrief stating the loop is incomplete (`complete: false`). With one completed instance, the scorecard is the result and no debrief is convened.

## 5. Cut (roles with `cut: yes`, after VO1)

Applies when the session includes VO1 and VO2 for a role with a cut. When the last VO1 instance is evaluated and the barrier is met:

1. `Agent` foreground, `subagent_type: netflix-hm-debrief`, prompt = the output of `sim.py packet debrief <session> --mode cut`: session config and mode, cut result (none yet), completeness, evaluated screens (or an explicit "none"), practice-only and skipped instances, the scorecards of screens and VO1 in catalog order with their `recommend` result, the role weights, and the catalog, study-map and template paths.
2. Save the returned markdown with `sim.py write-debrief <session> --mode cut --stdin --reason "<short>"`. It validates the front-matter (type, session id, role, level, enums, `stages_considered` in catalog order, outcome `continue|stop` consistent with the provisional outcome unless `override: true`), writes `debrief-cut.md` and records `cut: {outcome, reason}` in `session.yaml`. On failure it exits non-zero and writes nothing: send the printed problems back to the debrief agent once.
3. Show the decision. If `continue`, proceed to VO2. If `stop`, ask: finish, or continue VO2 in **practice mode**. Practice: `sim.py set <session> mode=practice`; tell the candidate the real decision stands and the remaining stages only give feedback (they are marked practice in `PROGRESS.md`).

## 6. Final debrief

With two or more completed instances (or at the end of a full loop), after the barrier:

1. `Agent` foreground `netflix-hm-debrief`, prompt = the output of `sim.py packet debrief <session> --mode final`: config, session mode, all scorecards in catalog order with their `recommend` result, role weights, the cut result if any, `complete: true|false`, practice-only and skipped instances, and the catalog, study-map and template paths.
2. The debrief: step 1 deterministic provisional outcome (`hire|no_hire|referred`, level = minimum observed level across high-weight stages), step 2 panel simulation citing only evidence already in scorecards (it says which transcript the HM opens and why), culture aggregated by memo value, HM decision (override only with scorecard citations, `override: true`), and a study plan linking `recsys-course/` modules or alternatives from the study map.
3. Save it with `sim.py write-debrief <session> --mode final --stdin` (same validation; writes `debrief.md` and records `final: {outcome, level, override}` in `session.yaml`) and show it. In deferred mode, show all scorecards first, then the debrief.
4. Run `sim.py progress` and tell the candidate where `sessions/PROGRESS.md` is.

### Referred

If the final outcome is `referred` ("not a fit for this team, maybe another"), offer to repeat VO2 (`ml-depth` + `hm-onsite`) with a different domain: start a new session with `--stages` for those stages and `--domain <other>`; the earlier scorecards stay as they are.

### Special cases

- Hire below the target level: the debrief states it; show it.
- Good candidate, other team: that is `referred`.
- Single stage or screens only: no hire/no-hire; the debrief (if convened) is provisional and says so.
