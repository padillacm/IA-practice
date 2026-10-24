# Stage close, evaluation, cut and debrief

Rationale: design.md D7. The simulator's scale is a teaching device, not Netflix's.

## 1. Closing an instance

When `meta.phase == closed`, the candidate used `::end`, or the clock hit 100% and the interviewer closed:

1. `sim.py end <session> <instance> --reason <completed|candidate_end|time_up|uncovered|interrupted|skipped>`.
   - `completed`: normal close. `time_up`/`uncovered`: candidate cause (what was missing is scored and listed). `candidate_end`/`interrupted`: external cause (uncovered competencies stay `no_evidence`).
2. For ai-assisted-coding, run the hidden tests (`stages.md`).
3. Evaluate according to the session `feedback` mode (below).

## 2. Evaluator contract

Agent `netflix-evaluator` (no tools beyond Read/Glob/Grep, cannot write). Prompt it with:
- the filtered transcript: `sim.py transcript <session> <instance> --for-evaluator` (strips `notes_private`), saved by `--out <scratchpad file>` or pasted;
- the session config (role, level, lang, domain, instance, end_reason, mode);
- the rubric path `netflix-ml-interview/stages/<stage>/rubric.md` (the evaluator reads it; you do not);
- the scorecard template path `netflix-ml-interview/templates/scorecard.md`;
- the instruction to return the complete scorecard markdown (front-matter + prose in the session language), every score backed by `{turn_id, quote}` from candidate turns only, and to return it as the final message.

### Writing and verifying the scorecard

There is no `sim.py` subcommand that writes a scorecard. The main thread writes the evaluator's markdown unchanged:

1. `sim.py guard` (exit 0), then Write to `netflix-ml-interview/sessions/<session-dir>/scorecards/<instance>.md` (the session directory is the path printed by `sim.py new` / `sim.py state`).
2. `sim.py verify-scorecard --session <session> --instance <NN> --downgrade`.
   - On pass: continue.
   - On quote or rule failures: resume the evaluator once (`SendMessage`) listing the failures, rewrite the file with its corrected version, and verify again. If failures remain, `--downgrade` has already set unverifiable competencies to `no_evidence` and corrected the recommendation; tell the candidate which competencies were downgraded and why.
3. `sim.py set <session> scorecard=scorecards/<instance>.md --instance <NN>`.
4. `sim.py recommend <scorecard path>` to confirm the derived recommendation matches the front-matter.

## 3. Feedback modes

- **immediate**: run `netflix-evaluator` in the **foreground** right after the stage. Show the scorecard (summary table of scores with quotes and prose) in the session language before continuing. Include the line "Recommendation derived by the simulator's pedagogical rule; Netflix does not use a company-wide scale."
- **deferred**: launch the evaluator with `Agent` in the **background** (`run_in_background: true`, name `ev-<instance>-<sid>`), say nothing about scores, and start the next instance. Notifications from the evaluator arrive mid-stage: handle them silently (write + verify the scorecard when the next stage is not running a turn, or at the barrier). Scorecards are shown together with the final decision.
- **Barrier**: before the cut and before the debrief, every needed instance must have a verified scorecard (done instances only; skipped ones are excluded). If background evaluators are pending, wait for them (end your turn, handle the notifications) before proceeding.

## 4. Continue, pause, finish

After each stage offer: continue to the next instance, pause (`sim.py pause` is already closed with the stage; the session stays resumable) or finish. If the candidate finishes with pending instances, mark them: `sim.py end <session> <NN> --reason skipped`. If two or more instances were completed, convene the debrief stating the loop is incomplete (`complete: false`). With one completed instance, the scorecard is the result and no debrief is convened.

## 5. Cut (roles with `cut: yes`, after VO1)

Applies when the session includes VO1 and VO2 for a role with a cut. When the last VO1 instance is evaluated and the barrier is met:

1. `Agent` foreground, `subagent_type: netflix-hm-debrief`, prompt: mode `cut`; session config; paths of the existing scorecards (VO1 and any screens; if no screens were evaluated the debrief says so); the catalog weights; `sim.py recommend` output per scorecard.
2. Write the returned markdown to `sessions/<dir>/debrief.md` after `sim.py guard`; record `sim.py set <session> cut="{outcome: continue|stop, reason: <short>}"`.
3. Show the decision. If `continue`, proceed to VO2. If `stop`, ask: finish, or continue VO2 in **practice mode**. Practice: `sim.py set <session> mode=practice`; tell the candidate the real decision stands and the remaining stages only give feedback (they are marked practice in `PROGRESS.md`).

## 6. Final debrief

With two or more completed instances (or at the end of a full loop), after the barrier:

1. `Agent` foreground `netflix-hm-debrief`, mode `final`. Provide: config, all scorecards in catalog order, catalog weights, `sim.py recommend` per scorecard, the cut result if any, `complete: true|false`, and the study map path `netflix-ml-interview/study-map.yaml` and the template `templates/debrief.md`.
2. The debrief: step 1 deterministic provisional outcome (`hire|no_hire|referred`, level = minimum observed level across high-weight stages), step 2 panel simulation citing only evidence already in scorecards (it says which transcript the HM opens and why), culture aggregated by memo value, HM decision (override only with scorecard citations, `override: true`), and a study plan linking `recsys-course/` modules or alternatives from the study map.
3. Write `debrief.md` (after `sim.py guard`), `sim.py set <session> final="{outcome: hire, level: L5, override: false}"`, show it. In deferred mode, show all scorecards first, then the debrief.
4. Run `sim.py progress` and tell the candidate where `sessions/PROGRESS.md` is.

### Referred

If the final outcome is `referred` ("not a fit for this team, maybe another"), offer to repeat VO2 (`ml-depth` + `hm-onsite`) with a different domain: start a new session with `--stages` for those stages and `--domain <other>`; the earlier scorecards stay as they are.

### Special cases

- Hire below the target level: the debrief states it; show it.
- Good candidate, other team: that is `referred`.
- Single stage or screens only: no hire/no-hire; the debrief (if convened) is provisional and says so.
