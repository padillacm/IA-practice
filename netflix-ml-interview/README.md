# Netflix ML Interview Simulator

Practice the Netflix interview loop for ML roles inside Claude Code. Each interviewer is a separate agent with its own
context; a different agent scores the stage from facts only; a hiring-manager agent simulates the cut and the final
debrief. Everything deterministic (clock, question selection, tests, quote checks, git guard) lives in
`scripts/sim.py`, not in the model's head.

> The simulated loop is an approximation. Real Netflix loops vary by team and level; confirm the actual structure with
> your recruiter. See `sources.md` for evidence and confidence per stage.

## Quick start

1. Start (or restart) Claude Code in this repository so the agents in `.claude/agents/netflix-*.md` are loaded
   (check with `/agents`).
2. Run `/netflix-ml-interview`. It asks for what is missing, shows a summary and waits for your confirmation.
3. Or pass arguments:

   ```
   /netflix-ml-interview role=mle level=L5 stages=vo1 domain=recsys
   /netflix-ml-interview role=ds stages=experimentation lang=es
   /netflix-ml-interview stages        # list the catalog, starts nothing
   /netflix-ml-interview resume        # continue a pending session
   /netflix-ml-interview progress      # show sessions/PROGRESS.md, starts nothing
   ```

| Setting | Values | Default |
|---|---|---|
| `role` | `mle` ML Engineer, `rs` Research / ML / Applied Scientist, `ds` Data Scientist (experimentation & analytics) | asked |
| `level` | `L4`, `L5`, `L6` | `L5` |
| `lang` | `en`, `es` | `en` |
| `stages` | `full`, `screen`, `vo1`, `vo2`, a stage, or `stage@variant`, comma separated | `full` |
| `domain` | `recsys`, `experimentation`, `causal-inference`, `rl-bandits`, `cv`, `nlp-llm`, `ads`, `ml-platform` | role default |
| `feedback` | `immediate` (scorecard after each stage), `deferred` (shown with the final decision) | `immediate` |
| `time_scale` | number; `1.0` disables the typing allowance | `1.5` |
| `background` | optional CV or projects file | none |

`rs` covers Research Scientist, ML Scientist and Applied Scientist titles; `ds` is the experimentation and analytics track.
A stage without an explicit variant uses the default variant of your role. Invalid values are rejected with the valid options.

## Stages and loops

14 stages in three phases (screen, VO1, VO2). The phase belongs to the loop entry, not to the stage.

| Role | screen | VO1 | VO2 | Cut |
|---|---|---|---|---|
| `mle` | recruiter-screen, hm-screen, technical-screen@ml-coding | coding@practical, ml-system-design@design, culture | ml-depth, project-deep-dive, partnership, hm-onsite | yes |
| `rs` | recruiter-screen, hm-screen, technical-screen@ml-framing-coding | presentation@research-talk, ml-system-design@problem-framing, ml-fundamentals@breadth, coding@ml-coding, culture | ml-depth, partnership, hm-onsite | optional |
| `ds` | recruiter-screen, hm-screen, technical-screen@sql, technical-screen@stats | presentation@take-home, experimentation@design-case, experimentation@analysis-case, coding@sql-pandas, culture | partnership, hm-onsite | optional |

`ai-assisted-coding` and any stage outside your loop are optional additions. `catalog.yaml` is the source of truth (durations,
personas, competencies, weights); edit it and run `scripts/check_simulator.py`.

## Commands during a stage (`::`)

The `::` prefix avoids clashes with CLI slash commands. These go to the orchestrator, never to the interviewer.

| Command | Effect |
|---|---|
| `::time` | Show elapsed active time and the stage budget |
| `::pause` | Stop the clock and save state; resume later in this or a new conversation |
| `::end` | End the stage now (competencies not covered become "no evidence") |
| `::ai <prompt>` | Ask the AI pair (`ai-assisted-coding`); it proposes an explanation and a diff, applying nothing |
| `::apply` | Apply the AI pair's last diff to your session workspace |
| `::help` | List these commands |

Anything else you type is your answer to the interviewer. You can write your solution in the chat, or in the file the
interviewer names inside your session workspace; when you say "done" the orchestrator runs the tests where you can see them.

## Language

English by default for everything: setup, interview, scorecards, debrief, study plan. With `lang=es` all of that is in
Spanish. Standard technical terms and the enums in files (`pass`, `fail`, `SN`, `Y`, ...) stay in English. If you answer
in the other language the interviewer keeps the session language and the switch is noted without penalty.

## Honor rule

The repository is yours, so nothing technically hides the content. While practicing, do not open
`netflix-ml-interview/stages/**`. Copy only `workspace/` or `starter.py` into your session workspace (the helper does it for
you); never `flaws.yaml`, `reference.py`, `questions.md` or `rubric.md`. Reading them spoils the practice.

## Pedagogical scale and decisions

Netflix has no common rating scale and no hiring committee: the decision is pass/fail in a live discussion where the hiring
manager acts as informed captain. The simulator's scale is **a teaching device, not Netflix's**.

- Each competency is scored against an observable "Yes bar" per level: `SN` (Strong No), `N` (No), `Y` (Yes), `SY` (Strong Yes),
  or `no_evidence`. Every score needs verbatim quotes from your own turns; `sim.py verify-scorecard` checks them.
- Stage recommendation: **fail** if any core competency is SN or two or more core are N; **insufficient_signal** if any core has
  no evidence; otherwise **pass** (no SN anywhere and at most one non-core N).
- Hints cap the affected competency: a `nudge` caps at Y, a `substantive` hint you needed to move forward caps at N.
- Debrief: deterministic provisional outcome (`hire`, `no_hire`, `referred`) weighted by role, then the HM may override only
  by citing scorecards. Culture is aggregated once per memo value across stages. `referred` means "not a fit for this team":
  you can repeat VO2 with another domain.
- Levels **L4 and L6 are extrapolated from L5**, the core senior level. Treat their bars as informed guesses.
- Stage durations are assumptions (see `sources.md`).

## Cost, context, and one phase per conversation

Each turn re-reads the interviewer's transcript, so a full loop is expensive and long. Run **one phase per conversation**
(screen, VO1 or VO2) and use `resume` for the next. After a context compaction the skill re-reads
`.claude/skills/netflix-ml-interview/references/relay-protocol.md` and `sim.py state`.

## Sessions are local, never committed

Sessions live in `netflix-ml-interview/sessions/<YYYY-MM-DD>-<shortid>/` and are git-ignored by the root `.gitignore`.
Every write goes through `sim.py guard`, which requires both that `sessions/.probe` is ignored (`git check-ignore`) and that
no file under `sessions/` is tracked; otherwise nothing is written and it tells you how to fix it. Outside a git repo it writes
with a warning. Nothing in this project stages, commits or pushes session files.

In Claude Code on the web (`CLAUDE_CODE_REMOTE=true`) the container is ephemeral: local history is lost when it recycles.
`sim.py info` and the setup summary warn about this.

Session layout: `session.yaml`, `transcripts/<instance>.md`, `scorecards/<instance>.md`, `work/<instance>/` (your code,
data), `packets/<instance>.md` (interviewer launch packet), `debrief.md`; plus `sessions/PROGRESS.md` (scores per stage,
variant and competency, with level and rubric version, practice sessions and no-evidence marked).

## Windows notes

- Use whichever of `python`, `python3` or `py` works; the setup tries all three and stores the working one in `session.yaml`.
  `.claude/settings.json` pre-approves `sim.py` for all three.
- `sim.py` and `check_simulator.py` use only the standard library and `pathlib`; no `date`, `bash` or shell tricks. Only `git`
  is invoked (and `sys.executable` for tests).
- Files are written as UTF-8 with `\n` newlines. Stage names contain `@`; quote paths in PowerShell (`'01-coding@practical'`).
- Content that needs numpy/pandas declares it in `problem.md`; install with `pip install -r netflix-ml-interview/requirements.txt`.
  The validator skips such problems with a warning when the packages are missing.

## Helper cheat sheet (`scripts/sim.py`)

Options such as `--json`, `--base`, `--now` go after the subcommand. Session arguments accept `latest`, an id or a short id;
instances accept the full id or its `NN` prefix.

```
sim.py info                                   # environment, working python command, CLAUDE_CODE_REMOTE
sim.py guard                                  # exit 0 allowed, 1 refused, 3 git error
sim.py new --role mle --level L5 --lang en --stages vo1 [--domain recsys --feedback immediate --time-scale 1.5]
sim.py select latest 02                       # pick questions/material, print the launch packet
sim.py turn latest 02 --stdin [--note "[tests: 7/8 passed]"]   # record candidate turn, print message for the interviewer
sim.py log latest 02 --file reply.txt         # parse <say>/<meta>, append to transcript (exit 3 if malformed)
sim.py pause latest 02 ; sim.py end latest 02 --reason completed
sim.py run-tests latest 02 [--hidden] ; sim.py apply latest 02 --file change.diff
sim.py transcript latest 02 --for-evaluator   # strips notes_private
sim.py verify-scorecard --session latest --instance 02 [--downgrade]
sim.py rebuild latest 02                      # prompt to relaunch an interviewer after an interruption
sim.py state [latest|--pending] ; sim.py progress ; sim.py set latest cut="{outcome: stop, reason: x}"
```

## Validating and extending the content

```
python netflix-ml-interview/scripts/check_simulator.py              # everything
python netflix-ml-interview/scripts/check_simulator.py --stage coding   # one stage while authoring
python netflix-ml-interview/scripts/check_simulator.py --list           # names for --only
python netflix-ml-interview/scripts/test_sim.py
python netflix-ml-interview/scripts/test_check_simulator.py
```

Formats are frozen in `openspec/changes/add-netflix-ml-interview-simulator/design.md` (D10). Structured files use a small YAML
subset (`scripts/_yamlish.py`): maps, lists, flow lists/maps on one line, quoted strings, comments, `|`/`>` blocks; no
anchors, no multi-line flow collections.

Layout:

```
catalog.yaml  study-map.yaml  sources.md  requirements.txt
stages/<stage>/{brief.md, questions.md, rubric.md}  (+ problems/, prs/, datasets/, repos/, takehomes/ where applicable)
templates/{session.yaml, scorecard.md, debrief.md}
examples/{transcripts/, gold/}     synthetic only, never real sessions
scripts/{sim.py, check_simulator.py, test_*.py, _yamlish.py, _content.py, _testrun.py, _patch.py}
sessions/                          local, git-ignored
```
