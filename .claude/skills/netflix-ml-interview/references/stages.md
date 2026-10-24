# Stage-specific procedures

The generic loop is in `relay-protocol.md`. This file adds what changes for coding, ai-assisted-coding and presentation.

## coding (and any stage with a problem and tests)

- `sim.py select` prepares the session workspace: it copies only `starter.py` (and the problem statement the launch packet carries) to `sessions/<id>/work/<instance>/`. Tell the candidate the workspace path and the file to edit. Never copy `reference.py`, `tests.py` hidden parts, `flaws.yaml` or banks yourself.
- The candidate may paste code in chat or edit the file in the workspace. When they say "done" (or the interviewer asks for tests):
  1. Run `sim.py run-tests <session> <instance>` visibly (show its output to the candidate). Use `--timeout` if the candidate's code is slow.
  2. Inject the summary line through the next turn: `sim.py turn <session> <instance> --stdin --note "[tests: 7/8 passed; failing: test_ties]"`, then relay as usual. The interviewer reacts to the result; you do not interpret it.
- If the candidate's solution is only in chat, write it to the workspace file first (Write under the path `sim.py` reported; the guard already passed at session creation).
- SQL stages (`technical-screen@sql`, `coding@sql-pandas`) use the same flow: data comes from the launch packet; run the candidate's query/test with `run-tests` when the packet says so.

## ai-assisted-coding

- Launch the interviewer (`netflix-ai-assisted-coding`) as usual. The workspace is the copied repo `workspace/` (no `flaws.yaml`, no notes).
- Also start a persistent agent for the AI pair: `Agent` foreground, `subagent_type: netflix-ai-pair`, `name: ai-<instance>-<sid>`, prompt = the AI-pair launch packet from `sim.py select` (it includes the private flaws list for this repo: the pair may let those flaws slip into its suggestions; never show the list to the candidate).
- `::ai <prompt>`:
  1. Log the request with `sim.py log ... --role orchestrator --text "::ai <prompt>"`.
  2. `SendMessage` to `ai-<instance>-<sid>` with the prompt (same async pattern: end your turn silently; the answer arrives as a notification). The `iv-` interviewer is not messaged yet.
  3. On the notification (from `ai-...`): log it with `sim.py log --role ai-pair`, then show the candidate the explanation and the unified diff exactly as returned. The pair applies nothing.
  4. Send the interviewer, as a normal relay message, `<orchestrator private>` with a one-paragraph summary of the exchange (what was asked, what was proposed) and the `flaws_triggered` list from the ai-pair `<meta>`. The interviewer "sees the screen" and must not reveal flaws; do not show this message to the candidate. The interviewer's reply is handled as usual (print `<say>` verbatim).
- `::apply`: save the last diff from the ai-pair answer to a scratchpad file and run `sim.py apply <session> <instance> --file <diff>` (add `--check` first if unsure). Show the result. If it fails to apply, say so and let the candidate decide; do not repair the diff.
- At "done": `sim.py run-tests`; also run `sim.py run-tests ... --hidden` at stage close (not shown to the candidate until the scorecard) and give the result to the evaluator as a note for the instance. Visible tests go to the interviewer as above.
- The interviewer `<meta>` fields `flaws_triggered` and `flaws_detected` end up in the transcript for the evaluator.

## presentation

- `presentation@research-talk` (rs): the candidate presents their own research. `presentation@take-home` (ds): the candidate presents an analysis of a generated dataset.
- Materials: `sim.py select` reports the materials step. For take-home it prepares the prompt and runs the generator into `sessions/<id>/work/<instance>/` (dataset + prompt). For research-talk it asks for the candidate's project/paper summary and slide outline instead.
- Show the candidate the prompt and the data path, then **pause**: run `sim.py pause`, tell them to prepare and come back with "ready" (or `/netflix-ml-interview resume`). The clock does not run while preparing. When they return, the panel interviewer (one agent alternating the two personas in its brief) is launched with the opening, and the stage proceeds normally.
- The presentation itself is delivered as text (outline plus the key points of the talk, or the analysis write-up) in one or more messages; each goes through `sim.py turn`.
