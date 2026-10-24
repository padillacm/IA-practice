# resume and progress

## resume

1. Detect `PY`, run `sim.py guard` (before any write) and `sim.py state --pending`.
2. No pending sessions: say so and offer to start a new session (setup).
3. One pending session: use it. Several: list them (id, role, level, stages, last instance status, date) and ask which, with AskUserQuestion. If the candidate gives a session id, use it.
4. `sim.py state <session>` and show a short status: instances done / in progress / pending, remaining active time of the open instance, mode.
5. Read `references/relay-protocol.md`, load tools (`ToolSearch` query `select:SendMessage,AskUserQuestion`).
6. Instance status:
   - `in_progress` (paused or interrupted mid-stage): `sim.py rebuild <session> <NN>` prints the relaunch prompt (brief, transcript with `<meta>`, remaining time, attempt+1, and the instruction to continue as the same persona without re-introducing). Launch a fresh foreground `Agent` with `subagent_type: netflix-<stage>`, name `iv-<instance>-<sid>-<attempt+1>` and that prompt. Log its `<say>` with `sim.py log` and print it verbatim: it answers the candidate's last message. The clock resumes automatically on the next `sim.py turn`. For ai-assisted-coding, relaunch the ai-pair the same way if needed (rebuild prompt for `ai-...`; otherwise start a fresh one with the repo's launch packet).
   - `pending`: start it normally (`sim.py select`, relay-protocol OPENING). If the previous instance was done but not evaluated, evaluate first (`evaluation.md`).
   - All done but no debrief or cut yet: run the evaluation / barrier / debrief steps of `evaluation.md`.
7. Continue with the standard loop. Same rules apply (pipe only, no help, no leaks).

If `SendMessage` is not available, degraded mode (see SKILL.md).

## progress

1. `sim.py progress` (regenerates `netflix-ml-interview/sessions/PROGRESS.md` from `session.yaml` files and scorecard front-matter).
2. `Read` that file and show it (scores per stage, variant and competency with level and rubric version; practice sessions and no-evidence marked; the trend across repeated stages). If there are no sessions, say so.
3. Starts nothing. Never put these files under version control.
