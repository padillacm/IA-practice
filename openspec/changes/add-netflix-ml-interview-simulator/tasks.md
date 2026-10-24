# Tasks

Organized into work packages (WP), each with its own files. The D10 formats (design.md) are frozen: no package changes them without first updating the design. No package commits: the implementation orchestrator integrates and commits.

## 1. WP1 · Foundations: repo, catalog, validator and helper

- [x] 1.1 Create the root `.gitignore` with `netflix-ml-interview/sessions/` and `.claude/settings.json` with permissions for `Bash(python netflix-ml-interview/scripts/sim.py:*)`, `Bash(python3 netflix-ml-interview/scripts/sim.py:*)` and `Bash(py netflix-ml-interview/scripts/sim.py:*)`. Verify that `git check-ignore -q netflix-ml-interview/sessions/.probe` returns 0 and that the JSON is valid.
- [x] 1.2 Create `netflix-ml-interview/` with the D6 tree, an English `README.md` and `requirements.txt` (numpy, pandas). The README must cover: usage, `::` commands, `lang`, honor rule, pedagogical scale, extrapolated L4/L6 levels, one phase per conversation and that sessions are local. Verify with `find netflix-ml-interview -maxdepth 2` that the tree matches D6.
- [x] 1.3 Write `catalog.yaml` according to D10, with the 14 stages, the variants, `variant_by_role`, the loops of the 3 roles with their phase per entry, `cut`, `default_domain`, per-role weights, the domains, the personas with style and the competencies with `core`. Also write `sources.md`, with confidence per stage and durations marked as assumptions, based on `research.md`. Verify with 1.5.
- [x] 1.4 Write `templates/session.yaml`, `templates/scorecard.md` and `templates/debrief.md` with the D10 formats and the notice "Recommendation derived by the simulator's pedagogical rule; Netflix does not use a company-wide scale." Verify that `sim.py` (1.6) loads them.
- [x] 1.5 Implement `scripts/check_simulator.py` (stdlib) with these checks:
  - the catalog schema, and that each loop entry is compatible with its role and has a weight;
  - per stage: `brief.md` with sources, `questions.md` according to D10 with a minimum of 2 `main` per applicable role × variant, and `rubric.md` according to D10 (version, 3–6 competencies with unique ids and at least one core, culture with `memo_values`, distinct L4/L5/L6 bars free of blacklisted adjectives);
  - the 17 agents: `name` equal to the file name, tools without Bash/Write and model according to D5;
  - the paths in `study-map.yaml`;
  - in coding, that `tests.py` passes against `reference.py`, skipping with a warning if dependencies are missing;
  - in ai-assisted, that the workspace tests pass and that each `hidden_test` is valid;
  - that the take-home generators are deterministic;
  - the `.gitignore` entry, and that the skill contains no `git add`, `commit` or `push`.

  Verify that it fails with clear messages on the empty tree and that `scripts/test_check_simulator.py` passes.
- [x] 1.6 Implement `scripts/sim.py` (stdlib, with `pathlib` and portable to Windows) with the D6 subcommands: `guard` (D8), `new`, `select`, `turn` (segments, `time_scale` and 80/90/100 % flags), `log`, `pause`, `run-tests`, `apply`, `verify-scorecard`, `rebuild`, `state`, `progress` and `info`. Verify with `scripts/test_sim.py`, which must cover:
  - the guard in a temporary repo: ignored, not ignored, with tracked files and without a repo;
  - empty `git status --porcelain` after creating a session;
  - time computation with pauses;
  - that selection excludes the ids already used;
  - that quote verification detects an invented quote and one that comes from an interviewer turn;
  - that the filter removes `notes_private`;
  - that `progress` groups by stage, variant and competency and flags level and version changes.

## 2. WP2 · Stage content (in English; 2a–2e in parallel, each owning its directories)

- [x] 2.1 (2a) Write `recruiter-screen`, `hm-screen`, `hm-onsite`, `culture` and `partnership` (brief, questions and rubric). They must include:
  - "Why Netflix" and "personal top of market", with the warning not to cite salary as motivation (Low);
  - self-promotion with metrics;
  - questions about the memo, where not having read it "is a fail";
  - the 8 values with their literal text, the keeper test, context not control, informed captain, farming for dissent and disagree then commit, with a sample of 3–4 values;
  - a director with time for the candidate's questions;
  - in `partnership`: collaboration, stakeholders and dependencies, with the option of having a director conduct it;
  - in `hm-onsite`: domain fit, and for L6, cross-team scope.

  Verify with `check_simulator.py`.
- [x] 2.2 (2b) Write `coding` with:
  - at least 6 `practical` problems: row-based homepage dedup, duplicates in viewing history, billboard rotation, weighted random key, sliding window over events and NDCG@K/P@K;
  - 2 `ml-coding`: CF with cosine on a sparse matrix and sparse matrix multiplication;
  - 3 `sql-pandas` on `sqlite3`: window functions, cohort retention and sessionization;
  - 2 `lc-style`.

  Each problem has `problem.md`, `starter.py`, `tests.py`, `reference.py` and `followups.md` (scale and concurrency). Also write `technical-screen` with its variants:
  - `ml-coding`;
  - `ml-framing-coding`;
  - `sql`, with `datasets/*.sql`;
  - `stats` (regression, type I/II, FDR, CLT/t, bootstrap, power/MDE and optional causal);
  - `fundamentals-pr-review`, with 2 feature-pipeline PRs and their `issues.md`;
  - `intern-project-coding`;
  - `oa`.

  Verify that `check_simulator.py` runs the tests against the references and they pass.
- [x] 2.3 (2c) Write `ai-assisted-coding` with at least 3 repos (e.g. a feature service with a cache, an offline evaluation job and a catalog deduplicator). Each has `workspace/` with passing tests, `tasks.md`, `notes.md` and `flaws.yaml` with 0, 1 and 2 bugs respectively, each bug with its `hidden_test`. Verify with `check_simulator.py`.
- [x] 2.4 (2d) Write `ml-fundamentals` with two variants:
  - `breadth`: bias-variance, L1/L2, GBDT and early stopping, co-watch embeddings, cold start, popularity bias, ranking metrics (P@K, R@K, MAP, NDCG, coverage, diversity), CF, trees vs networks, post-deploy monitoring, Bayes, forward pass, KNN, KV cache and attention;
  - `modeling-case`.

  Also write `ml-depth` per domain: recsys (with foundation model, GenRec, semantic IDs and artwork personalization), experimentation, causal-inference, rl-bandits, cv, nlp-llm, ads and ml-platform. Brief with the rule: "GenRec and the other publications are discussion context; figures are never asked." For L6, architecture deep dive. Verify with `check_simulator.py`.
- [x] 2.5 (2d) Write `ml-system-design` with:
  - `design` variant, with at least 10 prompts tagged by domain: homepage rows, artwork personalization, personalized search, search autocomplete, Continue Watching, title cold start, daily retraining, ML job scheduler, compute allocation, ML portal and real-time feature serving;
  - `problem-framing` variant (RS).

  Each prompt has its signal points (including availability, safety and online validation: interleaving → A/B) and L4/L5/L6 expectations. Also write `experimentation`:
  - `design-case`: ad frequency cap, row ordering with overlap and retention, and artwork;
  - `analysis-case`: quantiles, bootstrap, heterogeneous effects, covariate adjustment and FDR;
  - both with interleaving, CUPED, quasi-experiments and peeking.

  Verify with `check_simulator.py`.
- [x] 2.6 (2e) Write:
  - `presentation`: 45' `research-talk` and `take-home` with at least 2 take-homes whose `generate_data.py` uses a seed;
  - `project-deep-dive`, as "reverse system design" with assignable parts of the background.

  Verify with `check_simulator.py`, including determinism.

## 3. WP3 · Agents

- [x] 3.0 Handoff spike in a temporary directory outside `.claude/agents/` (two test agents launched as general-purpose). The following must be confirmed:
  - the asynchronous delivery of `SendMessage` as a notification;
  - what happens with `::time` and `/time` in the prompt;
  - the latency and cost per turn;
  - that the `<say>`/`<meta>` contract is respected over 5 turns.

  Document the results in `.claude/skills/netflix-ml-interview/references/relay-protocol.md` (the D1 state machine) and adjust D1–D3 if anything is not confirmed.
- [x] 3.1 Write a common prompt skeleton for the interviewers. It must include the literal D2 contract, the persona and style from the catalog, pacing control, obedience to the time flags, realism without feedback, leveled hints, the culture log, the language rule, reading the *launch packet* on the first turn and the prohibition on reading `rubric.md`. With that skeleton, generate the 14 `.claude/agents/netflix-<stage>.md`. Verify with `check_simulator.py`.
- [ ] 3.2 Write `.claude/agents/netflix-ai-pair.md`: it returns an explanation plus a diff and triggers the `flaws.yaml` bugs when the prompt touches that zone, reporting it in `<meta>`. Verify by invoking it directly with two fixed prompts on a repo (one touches the zone and the other does not) and applying the `hidden_test`.
- [ ] 3.3 Write `.claude/agents/netflix-evaluator.md`, which implements the D7 pedagogical rule: `{turn_id, quote}` evidence from candidate turns, effect of hints, `end_reason`, "no evidence", model Yes answer and study plan. Also write `.claude/agents/netflix-hm-debrief.md` with its `cut` and `final` modes: deterministic step 1, step 2 with justified override, culture by value, catalog order and no new evidence. Verify with 4.2.

## 4. WP4 · Evaluation quality

- [ ] 4.1 Write `study-map.yaml`: each `<stage>.<competency_id>` points to a `recsys-course/` module or to an alternative (`practice_stage` or `resource`). Verify with `check_simulator.py`.
- [ ] 4.2 Create a gold set in `netflix-ml-interview/examples/gold/` for `ml-system-design`, `coding` and `culture`. It must have strong, borderline and weak transcripts, long-shallow, with halo, with manipulation and the same one in EN/ES, with the expected scores (±1) and the recommendation. Add 3 debrief cases: blocking Strong No, mixed signals and referred. Verify by scoring each case 3 times, checking with `sim.py verify-scorecard` and recording the results in `RESULTS.md`. The recommendation and the decision must match across all 3 runs.

## 5. WP5 · Orchestrator skill

- [ ] 5.1 Write `.claude/skills/netflix-ml-interview/SKILL.md` (in English), with `allowed-tools` Agent, SendMessage, ToolSearch, AskUserQuestion, Bash, Read, Write, Edit, Glob and Grep. It must cover:
  - the `stages`, `resume` and `progress` subcommands;
  - configuration through arguments or with AskUserQuestion: role (with its title equivalence), level (L5 by default), `lang`, `stages` (phases and `stage@variant`), domain, feedback, `time_scale` and background;
  - validation of the values against the catalog;
  - the variability and ephemeral-environment warnings, and `sim.py guard` before writing.

  Verify:
  - with `stages=foo` and `coding@foo`, that it rejects;
  - with a valid start, that it shows the summary;
  - with the `.gitignore` missing the entry, that it refuses to save.
- [ ] 5.2 Implement the D1–D3 handoff following `relay-protocol.md`:
  - the *launch packet* prepared by `sim.py select`;
  - one `sim.py turn` per turn;
  - sanitizing of `<candidate>`;
  - `<say>` shown unchanged and `<meta>` logged;
  - reformatting with a single retry;
  - held messages;
  - the `::time`, `::pause`, `::end` and `::help` commands;
  - tests run by the main thread with `sim.py run-tests`;
  - the D9 degraded mode.

  Verify with a 6-turn candidate script for `recruiter-screen`. The subsequent check with `sim.py state` and a grep over the transcript must give: as many `<say>` as turns, no rubric term, a time flag with a low `time_scale` and a transcript written after each turn.
- [ ] 5.3 Implement `::ai` and `::apply` with `netflix-ai-pair` (summary and `flaws_triggered` passed to the interviewer as `<orchestrator private>`), and the `presentation` materials with their pause. Verify with an `ai-assisted-coding` repo and a `ds` take-home.
- [ ] 5.4 Implement the instances and their ordering by phases, the transitions, the evaluation according to the feedback mode with a barrier, quote verification, the cut (with practice mode), the final debrief and the offer to repeat VO2 if the result is referred. Verify with an `mle` session of one VO1 stage and one VO2 stage that produces the scorecards, the cut and `debrief.md`.
- [ ] 5.5 Implement `resume` (rebuilding in-progress instances with `sim.py rebuild`, and choosing among several sessions) and `progress`. Verify that a stage paused midway continues in a new conversation without the interviewer introducing themselves again, that repeating a stage makes the trend appear in `PROGRESS.md` and that `git status` stays clean.

## 6. WP6 · Integration

- [ ] 6.1 Add `.github/workflows/verify-netflix-interview.yml`: it installs `requirements.txt` and runs `check_simulator.py`, `test_check_simulator.py` and `test_sim.py`. It is triggered by changes in `netflix-ml-interview/**`, `.claude/agents/netflix-*.md`, `.claude/skills/netflix-ml-interview/**`, `.gitignore` and the workflow itself. Verify that it passes on the PR.
- [ ] 6.2 Link the simulator from the root `README.md` and from `recsys-course/README.md`. Verify that the relative links resolve.
- [ ] 6.3 End-to-end smoke test with three sessions: an `rs` L5 in English (abbreviated VO1), an `mle` with cut and `ai-assisted-coding`, and a standalone `ds` stage with `lang=es`. Check: isolation between stages, absence of live feedback, time flags, verified quotes, decision according to the rule, links to `recsys-course/` and clean `git status`. Record the findings in `netflix-ml-interview/examples/smoke-test.md`, without data from real sessions.

## Workflow follow-up

- Review the artifacts and run `/opsx:apply` to implement.
- When finished and reviewed, run `/opsx:archive` to promote the specs to `openspec/specs/`.
