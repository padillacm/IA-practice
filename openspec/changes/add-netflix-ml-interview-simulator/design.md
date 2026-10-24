# Design

## Context

- The repo is a learning space: notebook courses (`recsys-course/`, `langgraph/`, `langsmith/`…) and a previous multi-agent skill (`.claude/skills/course-builder/`) that uses `Agent` + `SendMessage`. There is no root `.gitignore` or project `.claude/settings.json`.
- The platform is Claude Code, with no application code. A subagent **cannot talk to the user or wait for their reply**: it receives a prompt, works and returns a final message.
  - `SendMessage` to a named agent resumes it from its transcript, but **the reply arrives later as a notification**, not as the tool result. Only the first foreground `Agent` call is synchronous.
  - Messages starting with `/` are interpreted by the CLI as slash commands, and `!` activates bash mode.
- The format of each stage comes from `research.md`. Most relevant for the design:
  - loops vary by team;
  - in SWE/MLE loops an onsite split into VO1 and VO2 with a cut is reported (Medium confidence for other roles);
  - there is no hiring committee: the decision is pass / fail in a live discussion and is made by the HM;
  - culture is evaluated in every round;
  - AI-assisted coding and partnership rounds exist.
- Sessions are local and outside git. In Claude Code on the web the container is ephemeral (`CLAUDE_CODE_REMOTE=true`) and a Stop hook asks to commit untracked files: the real protection is the `.gitignore`.
- The user also runs Claude Code on Windows, so we cannot depend on `date`, `python3` or bash syntax.
- `recsys-course/` has 20 modules (`00_intro` … `19_elite_playbook`); it does not cover coding, SQL or culture.

## Goals / Non-Goals

**Goals:**
- Each interviewer is an agent with its own context, and its evaluation is done by a different agent that only sees facts.
- All state and all deterministic computation live in a stdlib helper, `sim.py`, and in `session.yaml`, not in the conversation memory or in the model's arithmetic. That includes time, question selection, tests, quote verification and the git guard.
- The content (catalog, banks, rubrics, sources) is separate from the prompts, with frozen formats (D10) and automatically validated.
- It works the same on Linux, macOS and Windows.

**Non-Goals:**
- An app with the Agent SDK, a web interface or voice.
- Replicating leaked Netflix questions.
- Syncing history between machines: sessions are local by the user's decision.
- Measuring judge reliability in CI. It is measured with a gold set run by hand (D7); CI only validates structure and content.
- Technically hiding the content from the candidate, because the repo is theirs. A documented honor rule is used (D5).

## Decisions

### D1 · Asynchronous orchestrator ↔ interviewer handoff
The skill (main thread) talks to the candidate. Each stage is an **instance** with id `NN-<stage>@<variant>` (e.g. `04-technical-screen@stats`) and a named agent `iv-<instance>-<session_id>-<attempt>`. The numbered state machine is written in `.claude/skills/netflix-ml-interview/references/relay-protocol.md`:

1. **Opening**: foreground `Agent` with `subagent_type: netflix-<stage>` and the *launch packet* (D10). The response is synchronous: `<say>` is shown and logged.
2. **Candidate turn**: `sim.py turn` logs the candidate's text and returns the time header and the flags (D3). The skill does `SendMessage` to the interviewer with `<orchestrator>…</orchestrator>` + `<candidate>…</candidate>` and **ends its turn with no text for the candidate**.
3. **Notification**: when the response arrives, the skill checks that it comes from the current interviewer. It shows `<say>` exactly as it arrives, logs `<meta>` with `sim.py log` and stops. Notifications from other agents (e.g. the background evaluator) are never shown inside the interview.
4. **Early messages**: if the candidate types before the response arrives, their message is held and sent afterwards.

- **Sanitizing**: the candidate's text goes inside `<candidate>`, and any `<orchestrator>` or `[orchestrator:` markers it contains are removed, so they cannot forge directives.
- **Why this pattern**: it is the only way, within Claude Code, to have an interviewer with an isolated, persistent context.
- **Discarded alternatives**: role-play in the main thread (kept as degraded mode, D9) and one agent per question (breaks the follow-ups).
- **Panel**: `presentation` simulates the panel with a single agent that alternates the two personas declared in its brief.

### D2 · `<say>` / `<meta>` turn contract
Each interviewer prompt literally includes: *"Each turn you MUST end with a final message containing exactly one `<say>…</say>` followed by one `<meta>…</meta>` and nothing after. Never write or guess the candidate's reply. Never call tools after writing `<say>`. Read files only on your first turn; later turns are pure conversation. Reply as your final message, never via SendMessage."*

- `<meta>` is YAML with these **factual** fields:
  - `question_id`
  - `phase: intro|main|candidate_questions|closed`
  - `hint {id, level: nudge|substantive, competency}`
  - `culture_probe {value}`
  - `time_warning_given`
  - `uncovered_signal_points[]`
  - `lang_switch`
  - `flaws_triggered[]` and `flaws_detected[]` (only in ai-assisted-coding)
- There is a single private field, `notes_private`, which `sim.py` removes from the copy the evaluator receives. Outside `notes_private`, evaluative language is forbidden.
- **Reformatting**: if `<say>` or `<meta>` is missing, a reformat is requested only once. If it fails again, the raw text is shown and flagged in the transcript.

### D3 · Time computed by `sim.py`
- `session.yaml` stores active time segments per instance. `::pause` closes the open segment and resuming opens a new one.
- `sim.py turn` computes `t = active / time_scale` and emits `[t=23m/60m]` together with these literal flags, which the interviewer obeys without doing any calculations:
  - `[time:80% — give the time warning now]`
  - `[time:90% — move to candidate questions]`
  - `[time:100% — close the stage now]`
- `time_scale` is 1.5 by default, because typing is slower than speaking (`time_scale=1.0` disables it). The catalog durations are assumptions documented in `sources.md`.

### D4 · Catalog, phases and per-role loops (from `research.md`)

| Stage | Min | Variants (default per role) | Persona |
|---|---|---|---|
| recruiter-screen | 30 | — | Recruiter |
| hm-screen | 30 | — | HM (cordial, sells Netflix) |
| technical-screen | 60 | `ml-coding` (MLE), `ml-framing-coding` (RS), `sql` + `stats` (DS); optional `fundamentals-pr-review`, `intern-project-coding`, `oa` | Senior MLE / RS / DS |
| presentation | 45–60 | `research-talk` 45' (RS), `take-home` 60' (DS) | Panel of 2 |
| coding | 60 | `practical` (MLE), `ml-coding` (RS), `sql-pandas` (DS); optional `lc-style` | Senior MLE / DS |
| ai-assisted-coding | 60 | — | Senior engineer |
| ml-fundamentals | 45 | `breadth` (RS); optional `modeling-case` (DS, no direct evidence) | RS / Senior DS |
| ml-system-design | 60 | `design` (MLE), `problem-framing` (RS) | Staff MLE or director |
| experimentation | 45 | `design-case` + `analysis-case` (DS); `design-case` optional for MLE and RS | Senior DS |
| culture | 45 | — | Director ("Dream Team") |
| ml-depth | 45 | — (guided by the domain) | Domain expert |
| project-deep-dive | 45 | — | Senior MLE ("reverse system design") |
| partnership | 45 | — | Manager or director of a partner team |
| hm-onsite | 45 | — | HM (demanding, team fit) |

**Default loops.** The phase belongs to the loop entry, not to the stage:

| Role | screen | VO1 | VO2 | Cut | Default domain |
|---|---|---|---|---|---|
| `mle` ML Engineer | recruiter-screen, hm-screen, technical-screen@ml-coding | coding@practical, ml-system-design@design, culture | ml-depth, project-deep-dive, partnership, hm-onsite | yes | recsys |
| `rs` Research / ML / Applied Scientist | recruiter-screen, hm-screen, technical-screen@ml-framing-coding | presentation@research-talk, ml-system-design@problem-framing, ml-fundamentals@breadth, coding@ml-coding, culture | ml-depth, partnership, hm-onsite | no (optional) | recsys |
| `ds` Data Scientist (experimentation & analytics) | recruiter-screen, hm-screen, technical-screen@sql, technical-screen@stats | presentation@take-home, experimentation@design-case, experimentation@analysis-case, coding@sql-pandas, culture | partnership, hm-onsite | no (optional) | experimentation |

- **Canonical order**: phase first (screen → VO1 → VO2) and, within each phase, the catalog order. A stage chosen outside a loop uses `default_phase` and `variant_by_role`.
- **Domains**: recsys, experimentation, causal-inference, rl-bandits, cv, nlp-llm, ads and ml-platform. The domain guides `ml-depth`, `ml-system-design` and `hm-onsite`.
- **Per-role weights**, in the catalog as `weight: high|normal|low`:
  - MLE: `ml-system-design`, `culture` and `ml-depth` at `high`; `coding` at `low`.
  - RS: `presentation`, `problem-framing`, `ml-depth` and `culture` at `high`.
  - DS: both `experimentation` instances, `stats` and `culture` at `high`.

### D5 · Agents (17) and honor rule

| Agent | tools | model |
|---|---|---|
| `netflix-<stage>` ×14 | Read, Glob, Grep | sonnet; `ml-system-design` and `hm-onsite`: opus |
| `netflix-evaluator` | Read, Glob, Grep | opus |
| `netflix-hm-debrief` (modes `cut` and `final`) | Read, Glob, Grep | opus |
| `netflix-ai-pair` | Read, Glob, Grep | sonnet |

- **No agent has Bash or Write.**
  - Tests are run by the main thread with `sim.py run-tests`, in plain view of the candidate, and the result is injected as `[tests: 7/8 passed; failing: test_ties]`.
  - Agents return markdown and the main thread is the one that writes the files.
- **Agent loading**: the frontmatter `name` matches the file name. Agents are loaded when Claude Code starts, so after creating them you must restart or check `/agents`.
- **ai-pair**:
  - It is a persistent agent per instance (`ai-<instance>-<sid>`) that the candidate uses with `::ai <prompt>`.
  - It returns an explanation and a unified diff, without editing anything. `::apply` applies the diff with `sim.py apply`.
  - Each repo ships a `flaws.yaml` with 0–2 bugs (sometimes none).
  - The skill passes the interviewer, as `<orchestrator private>`, a summary of the exchange and the `flaws_triggered`. The interviewer "sees the screen" of the candidate and must not reveal them.
- **Honor rule** (README): during practice, `netflix-ml-interview/stages/**` is not opened. Only `workspace/` or `starter.py` is copied to the session space; never `flaws.yaml`, `reference.py`, `questions.md` or `rubric.md`.

### D6 · Knowledge base and helper
```
netflix-ml-interview/
  README.md            # English: usage, :: commands, lang, honor rule, pedagogical scale, extrapolated levels
  catalog.yaml  study-map.yaml  sources.md  requirements.txt   # requirements: numpy, pandas (content only)
  stages/<stage>/brief.md  questions.md  rubric.md
  stages/coding/problems/<id>/{problem.md, starter.py, tests.py, reference.py, followups.md}
  stages/technical-screen/prs/<id>/{pr.diff, context.md, issues.md}   datasets/<id>.sql
  stages/ai-assisted-coding/repos/<id>/{workspace/, tasks.md, flaws.yaml, notes.md}
  stages/presentation/takehomes/<id>/{prompt.md, generate_data.py}
  templates/{scorecard.md, debrief.md, session.yaml}
  examples/{transcripts/, gold/}            # synthetic transcripts, never real sessions
  scripts/sim.py  scripts/check_simulator.py  scripts/test_*.py   # stdlib
  sessions/            # IGNORED by git
.claude/skills/netflix-ml-interview/{SKILL.md, references/relay-protocol.md}
.claude/agents/netflix-*.md (17)
.claude/settings.json  # allow: Bash(python netflix-ml-interview/scripts/sim.py:*), Bash(python3 …:*), Bash(py …:*)
```
- **`sim.py` subcommands**:
  - session and environment: `guard`, `new`, `state`, `info` (environment and `CLAUDE_CODE_REMOTE`);
  - each turn: `turn`, `log`, `pause`;
  - preparation: `select` (picks questions or problem without repeating those already used and prepares the *launch packet*);
  - code: `run-tests`, `apply`;
  - evaluation: `verify-scorecard`;
  - recovery: `rebuild`;
  - history: `progress`.
- **Python interpreter**: when configuring, the skill tries `python`, `python3` and `py`, and saves the one that works in `session.yaml`.
- **Language**:
  - The skill, the agents and the knowledge base are in English.
  - Configuration is asked in English, unless `lang=es` is passed.
  - The README is in English (all development artifacts are in English; only runtime session output follows the session language).
- **Dependencies**:
  - `sim.py` and `check_simulator.py` use only stdlib.
  - Problems that need numpy or pandas declare it in `problem.md`. `check_simulator` skips them with a warning if they are missing; CI installs `requirements.txt`.
  - SQL is run on `sqlite3`.

### D7 · Evaluation, cut and debrief (pedagogical rules)
- **Rubric**:
  - Each competency has a stable `id`, `core: true|false`, `memo_values[]` (only the culture one) and an observable "Yes" bar per level (L4/L5/L6).
  - The other scores are defined relative to that bar: Strong No contradicts the bar or has serious errors; No does not reach it; Strong Yes reaches the bar of the next level up.
  - Each rubric carries `rubric_version`.
  - L4 and L6 are extrapolated from L5, and the README says so.
- **Per-stage recommendation**. Recommendation derived by the simulator's pedagogical rule; Netflix does not use a company-wide scale.
  - **fail**: any core at Strong No, or two or more core at No.
  - **insufficient signal**: any core at "no evidence".
  - **pass**: the rest, provided there is no Strong No and at most one non-core is at No.
  - **Observed level**: the highest one whose Yes bar is met by all core competencies.
- **Hints**: a `nudge` caps the affected competency at Yes; a `substantive` one that was needed to move forward caps it at No. They never affect other competencies.
- **Stage end**: stored in `end_reason`.
  - External cause (`::end`, interruption): the competency stays at "no evidence".
  - Candidate cause (ran out of time, or left points uncovered despite redirection): the competency is scored and the points that were missing are listed.
- **Language switch**: it is noted, but not penalized.
- **Evaluator**:
  - With immediate feedback it runs in the foreground; with deferred feedback, in the background.
  - Barrier: before the cut and the debrief, all scorecards must exist.
  - It receives the filtered transcript (without `notes_private`), the config and the rubric.
  - Each piece of evidence is `{turn_id, quote}` from a turn **of the candidate**.
  - `sim.py verify-scorecard` checks that each quote appears literally in its turn. If it fails, the evaluator is resumed once; if it keeps failing, the competency becomes "no evidence" and a warning is given.
- **Debrief** (cut and final), in two steps:
  1. **Deterministic rule** → `provisional_outcome`:
     - **No Hire**: a core at Strong No in a `high` stage, or a negative culture verdict, or a `high` stage at fail.
     - **Referred**: all `high` stages of VO1 at pass, positive culture and fails only in `ml-depth`/`hm-onsite` or due to weak domain fit. When the only `high`-stage fail (and the only `none` level) comes from `ml-depth`, Referred takes precedence over the No Hire triggers "`high` stage at fail" and "minimum level none"; the SN-core and negative-culture triggers always apply.
     - **Hire**: the rest, with a weighted majority at pass.
     - **Level**: the minimum of the observed levels in the `high` stages.
  2. **Override**: the HM, as informed captain, may disagree, but only with a justification that cites scorecards (`override: true`).
- **Culture**: it is aggregated **by memo value** across stages, without summing per stage. Verdict: `negative` if the `culture` stage's core `culture_signals` is N or SN, or one value is weak with evidence in two or more stages; `mixed` if a single value is weak on one piece of evidence; `positive` otherwise. A value with no evidence is "no signal", not weak.
- **Debrief simulation**:
  - It reads the scorecards in catalog order.
  - A simulated interviewer who "changes their mind" can only cite evidence that is already in a scorecard.
  - If the HM opens a transcript, it says which one and why.
- **Cut**: it applies the same rule to the existing scorecards; if there are no evaluated screens, it says so. If the cut is negative, continuing in `practice` mode is offered: the real decision stands and the practice stages only provide feedback.
- **Referred**: repeating VO2 with a different domain (`ml-depth` + `hm-onsite`) is offered.
- **Study plan**: the 1–3 recommendations are the first items of the plan. `study-map.yaml` maps each competency id to a `recsys-course/` module or an alternative (`practice_stage`, `memo`, `resource`).
- **Judge quality**: a gold set in `examples/gold/` with transcripts of strong, borderline and weak cases, a long and shallow one, one with a halo effect, one with a manipulation attempt, and the same one in EN and ES. Each is scored 3 times and recorded in `RESULTS.md`.

### D8 · Local-only sessions
- Root `.gitignore` with `netflix-ml-interview/sessions/`.
- `sim.py guard` is the only write gate. It requires two conditions:
  - `git check-ignore -q netflix-ml-interview/sessions/.probe` returns 0;
  - `git ls-files netflix-ml-interview/sessions` is empty.

  If `git rev-parse` fails (no repo), writing is allowed with a warning. Exit code 128 is an error.
- The skill contains no `git add`, `commit` or `push`. `check_simulator` verifies this, and a test creates a session in a temporary repo and checks that `git status --porcelain` stays empty.
- `sim.py info` detects `CLAUDE_CODE_REMOTE == "true"` to show the ephemeral-environment warning.
- `PROGRESS.md` is regenerated from the `session.yaml` files and the scorecard front-matter.

### D9 · Rebuild and degraded mode
- **Rebuild** (`sim.py rebuild`): used when resuming an `in_progress` instance in another conversation, or if `SendMessage` fails. It launches a new agent (`attempt+1`) with:
  - the brief;
  - the transcript with `<meta>`;
  - the remaining time;
  - the instruction *"continue as the same persona; do not re-introduce yourself; respond to the last candidate message"*.
- **Degraded mode**: if `SendMessage` is not available, the stage is conducted in the main thread with the persona. The evaluation is still a separate agent, and `mode: degraded` is recorded.
- **Session choice**: `resume` takes the most recent pending session; if there are several, it lists them.
- **Cost and compaction**: for the full loop, one phase per conversation is recommended. After a compaction, the skill rereads `relay-protocol.md` and `sim.py state`.

### D10 · Frozen formats
- **catalog.yaml**:
  - `version`
  - `domains[]`
  - `roles{mle|rs|ds}{label, cut, default_domain, loop{screen|vo1|vo2: [stage@variant]}, weights{stage: high|normal|low}}`
  - `stages[]{id, order, default_phase, minutes, persona{name, title, style}, agent, variants[]{id, roles[], minutes?, materials?}, variant_by_role{mle|rs|ds}, competencies[]{id, core}}`
- **rubric.md**:
  - front-matter `{stage, rubric_version}`;
  - at the start, a shared section with the definitions of Strong No, No and Strong Yes;
  - one `## <competency_id>` section per competency, with `core: true|false` (plus `memo_values:` in the culture one) and a `| Level | Yes bar |` table with L4, L5 and L6.
- **questions.md**: one `### <id>` section per question, with a YAML block `{roles, levels, variant, domain, kind: main|followup|culture, signal_points[]}`, the statement and the follow-ups. At least 2 `main` questions for each applicable role and variant combination.
- **session.yaml**:
  - `{id, created, role, level, lang, domain, time_scale, python, env_ephemeral}`
  - `feedback: immediate|deferred`
  - `mode: normal|practice|degraded`
  - `background_path?`, `candidate_profile?`
  - `instances[]{instance_id, stage, variant, phase, status: pending|in_progress|done|skipped, end_reason?, segments[], agent_name, attempt, question_ids[], problem_id?, scorecard?}`
  - `cut?{outcome, reason}`, `final?{outcome, level, override}`
- **Transcript**: front-matter with the instance and the config; then, one block per turn `### T<n> · interviewer|candidate|orchestrator|ai-pair · t=MMm` with the literal text and `<meta>` in YAML.
- **Scorecard**: front-matter `{instance_id, stage, variant, level, rubric_version, recommendation: pass|fail|insufficient_signal, level_observed, scores{<comp_id>: SN|N|Y|SY|no_evidence}, evidence{<comp_id>: [{turn_id, quote}]}, hints[]}`, followed by prose in the session language. Enums are always in English.
- **flaws.yaml**: `flaws[]{id, zone, trigger_keywords[], description, hidden_test}`. The `hidden_test` fails with the bug and passes without it.
- **study-map.yaml**: `{<stage>.<competency_id>: {course: [recsys-course/NN_x/], practice_stage?, resource?}}`.
- **Launch packet**: the config, the persona, `brief.md`, the selected questions or problem, `candidate_profile`, the D2 contract and the language rule.

## Risks / Trade-offs

- [The asynchronous handoff is new and fragile] → Mandatory spike (task 3.0) before writing the 17 agents, protocol written in `relay-protocol.md` and rebuild (D9).
- [Cost: each turn rereads the agent's transcript and the cache expires after ~5 min] → Agents on sonnet except the critical ones, brief `<meta>` and one phase per conversation.
- [The judge is lenient or invents quotes] → Literal quote verification, deterministic rules, gold set and "no evidence".
- [Netflix process inaccurate or changing, with much of the evidence coming from SWE loops] → Explicit confidence in `sources.md`, optional cut outside MLE, declared extrapolated levels and an editable catalog.
- [The candidate can see the content] → Honor rule and nothing sensitive in the session space.
- [History loss in ephemeral containers] → Accepted consequence; a warning is given at start.

## Migration Plan

Not applicable: this is a new addition. To undo it, just delete `.claude/skills/netflix-ml-interview/`, `.claude/agents/netflix-*.md` and `netflix-ml-interview/`, and remove the entry from `.gitignore` and the one from `.claude/settings.json`.

## Open Questions

- Should a "simulated candidate" agent be added later to automate the gold set and the smoke tests? It would be a separate change.
